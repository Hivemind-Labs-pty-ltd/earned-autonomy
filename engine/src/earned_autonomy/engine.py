"""The trust engine (SPEC §6–§12).

Design: the trust record is the only source of truth. Every change is first appended to the record as an entry,
then applied by a deterministic reducer (`_Reducer.apply`). Live state is therefore always identical to a replay
of the record from empty (SPEC §5, §13.4). Randomness (spot-check sampling, canaries, second checks) happens in
the engine, never in the reducer, and only its outcome is recorded.
"""
from __future__ import annotations

import copy
import secrets
import threading
import uuid
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Callable

from .governance import Actor, GovernanceGuard
from .models import (CONSEQUENCE, COSMETIC_REASONS, L1, L2, L3, LABELS, LEVEL_NAMES, REASON_CODES, ChecksResult,
                     Decision, Policy, ProposedAction, TaskTypePolicy, TrustKey, TrustState, iso, is_serious,
                     parse_iso, payload_hash, utcnow)
from .record import TrustRecord
from .stats import BoundStrategy, WilsonBound
from .suites import SuiteStore
from .tagging import Tagger


def _key(k) -> TrustKey:
    return (k[0], k[1], k[2])


def reviewer_key(org_id: str, reviewer_id: str, task_type: str) -> TrustKey:
    """SPEC §9: a reviewer's trust key is (org, reviewer_id, review.<task_type>)."""
    return (org_id, reviewer_id, f"review.{task_type}")


class _Reducer:
    """All derived state. Built only by applying record entries, in order."""

    def __init__(self, bounds: BoundStrategy):
        self.bounds = bounds
        self.policy: Policy | None = None
        self.policies: dict[int, dict] = {}
        self.states: dict[TrustKey, TrustState] = {}
        self.reviewers: dict[TrustKey, TrustState] = {}
        self.paused: set[tuple] = set()                     # (org, agent, task_type|None)
        self.actions: dict[str, dict] = {}                  # action_id -> index
        self.published: dict[str, set] = {}                 # agent_id -> versions published
        self.queue: dict[str, dict] = {}                    # action_id -> review item (pre_review | spot_check)
        self.level_changes: list[dict] = []

    # ---- helpers -----------------------------------------------------------------------------------------
    def state(self, k: TrustKey) -> TrustState:
        if k not in self.states:
            self.states[k] = TrustState(trust_key=k)
        return self.states[k]

    def rstate(self, k: TrustKey) -> TrustState:
        if k not in self.reviewers:
            self.reviewers[k] = TrustState(trust_key=k)
        return self.reviewers[k]

    def _set_level(self, s: TrustState, to: int, why: str, ts: str):
        frm = s.level
        s.level, s.since_change = to, 0.0
        s.recent = []
        self.level_changes.append({"key": list(s.trust_key), "from": frm, "to": to, "why": why, "ts": ts})

    def _touch(self, s: TrustState, ts: str):
        s.state_version += 1
        s.updated_at = ts

    def _observe(self, s: TrustState, serious: bool, fail: bool, ts: str, eps: float, capped: bool,
                 n_min: int, rolling_n: int, rolling_min: int, top: int = L3):
        """SPEC §7 update: evidence, then demotion first, then promotion."""
        s.n += 1
        s.err += 1 if serious else 0
        s.fail += 1 if fail else 0
        s.since_change += 1
        s.recent.append(1 if serious else 0)
        if len(s.recent) > rolling_n:
            s.recent = s.recent[-rolling_n:]
        if s.level >= L2 and len(s.recent) >= rolling_min and self.bounds.lower(sum(s.recent), len(s.recent)) > eps:
            self._set_level(s, s.level - 1, "rolling_bound", ts)
        elif (not capped and eps > 0 and s.level < top and s.since_change >= n_min
              and self.bounds.upper(s.err, s.n) <= eps):
            self._set_level(s, s.level + 1, "evidence", ts)

    def _discount(self, s: TrustState, eps: float, w: float, ts: str, why: str):
        s.n *= w
        s.err *= w
        s.fail *= w
        if s.level >= L2 and self.bounds.upper(s.err, s.n) > eps:
            self._set_level(s, L1, why, ts)

    # ---- apply -------------------------------------------------------------------------------------------
    def apply(self, e) -> None:
        b, ts = e.body, e.ts
        t = e.type
        p = self.policy
        if t == "policy":
            new = Policy.from_dict(b["policy"])
            self.policy = new
            self.policies[new.policy_version] = b["policy"]
            # SPEC §10: policy changes take effect immediately; a trusted key whose bound no longer holds
            # (or whose type became capped) drops to L1.
            for s in self.states.values():
                tt = s.trust_key[2]
                if s.level >= L2 and (new.is_capped(tt) or self.bounds.upper(s.err, s.n) > new.eps_for(tt)):
                    self._set_level(s, L1, "policy_change", ts)
                    self._touch(s, ts)
        elif t == "decision":
            k = _key(b["trust_key"])
            s = self.state(k)
            if s.agent_version is None:
                s.agent_version = b["agent_version"]
            s.last_activity_at = b["created_at"]
            self._touch(s, ts)
            a = self.actions.setdefault(b["action_id"], {"outcomes": [], "decisions": []})
            a.update(key=k, agent_version=b["agent_version"], decision_id=b["decision_id"], mode=b["mode"],
                     level=b["level"], agent_id=k[1], org_id=k[0], task_type=k[2])
            a["decisions"].append(b["decision_id"])
            if b["mode"] == "hold":
                self.queue[b["action_id"]] = {"action_id": b["action_id"], "kind": "pre_review", "key": list(k),
                                              "why": b["why"], "since": ts}
        elif t == "level_change":
            s = self.state(_key(b["trust_key"]))
            self._set_level(s, b["to"], b["why"], ts)
            self._touch(s, ts)
        elif t == "outcome":
            k = _key(b["trust_key"])
            s = self.state(k)
            tt = k[2]
            self._observe(s, b["serious"], b["label"] == "incomplete", ts, p.eps_for(tt), p.is_capped(tt),
                          p.n_min, p.rolling_n, p.rolling_min)
            self._touch(s, ts)
            a = self.actions.setdefault(b["action_id"], {"outcomes": [], "decisions": []})
            a["outcomes"].append(b["event_id"])
            if b["source"] == "pre_review":
                a["review_label"] = b["label"]
                if b["label"] in ("approved", "cosmetic_edit"):
                    a["approved_by"] = b["actor_id"]
            self.queue.pop(b["action_id"], None)
        elif t == "incident":
            k = _key(b["trust_key"])
            s = self.state(k)
            # SPEC §7: counts as one serious outcome AND steps the key down one level immediately.
            s.n += 1
            s.err += 1
            if s.level >= L2:
                self._set_level(s, s.level - 1, "incident", ts)
            self._touch(s, ts)
        elif t == "executed":
            a = self.actions.setdefault(b["action_id"], {"outcomes": [], "decisions": []})
            a["executed"] = True
            a["executed_at"] = ts
            a["autonomous"] = b["autonomous"]
        elif t == "spot_sample":
            a = self.actions.get(b["action_id"], {})
            self.queue[b["action_id"]] = {"action_id": b["action_id"], "kind": "spot_check",
                                          "key": list(a.get("key", ())), "why": "sampled", "since": ts}
        elif t == "version_published":
            agent = b["agent_id"]
            self.published.setdefault(agent, set()).add(b["version"])
            for s in self.states.values():
                if s.trust_key[1] != agent:
                    continue
                tt = s.trust_key[2]
                r = b["results"].get(tt)
                if not (r and r.get("carry")):
                    self._discount(s, p.eps_for(tt), p.version_discount, ts, "version_change")
                s.agent_version = b["version"]
                self._touch(s, ts)
        elif t == "version_unannounced":
            s = self.state(_key(b["trust_key"]))
            self._discount(s, p.eps_for(s.trust_key[2]), p.version_discount, ts, "version_change")
            s.agent_version = b["version"]
            self._touch(s, ts)
        elif t == "pause":
            self.paused.add((b["org_id"], b["agent_id"], b.get("task_type")))
        elif t == "resume":
            self.paused.discard((b["org_id"], b["agent_id"], b.get("task_type")))
        elif t == "reviewer_evidence":
            s = self.rstate(_key(b["reviewer_key"]))
            self._observe(s, b["miss"], False, ts, p.reviewer_eps, False, p.reviewer_n_min, p.rolling_n,
                          p.rolling_min, top=L2)
            self._touch(s, ts)
        # governance, canary, second_check_sample: log-only entries

    def is_paused(self, org: str, agent: str, task_type: str) -> bool:
        return (org, agent, None) in self.paused or (org, agent, task_type) in self.paused


class TrustEngine:
    """Reference implementation of the Earned Autonomy trust engine (SPEC §12 API)."""

    def __init__(self, policy: Policy | None = None, record: TrustRecord | None = None, tagger: Tagger | None = None,
                 bounds: BoundStrategy | None = None, clock: Callable[[], datetime] = utcnow,
                 sampler=None):
        self.record = record if record is not None else TrustRecord()
        self.tagger = tagger
        self.bounds = bounds or WilsonBound()
        self.clock = clock
        # SPEC §6/§9: sampling must be unpredictable to the agent. Default: the OS CSPRNG.
        self._sampler = sampler or secrets.SystemRandom()
        self._lock = threading.RLock()
        self.governance = GovernanceGuard(self._log)
        self.suites = SuiteStore(self.governance)
        self._r = _Reducer(self.bounds)
        for e in self.record.entries():           # existing record: rebuild from it
            self._r.apply(e)
        if self._r.policy is None:
            self._emit("policy", {"policy": (policy or Policy()).to_dict()})

    # ---- plumbing ----------------------------------------------------------------------------------------
    def _now(self) -> str:
        return iso(self.clock())

    def _emit(self, type_: str, body: dict):
        e = self.record.append(type_, body, self._now())
        self._r.apply(e)
        return e

    def _log(self, type_: str, body: dict):
        self.record.append(type_, body, self._now())

    @property
    def policy(self) -> Policy:
        return self._r.policy

    # ---- tagging (SPEC §4) ---------------------------------------------------------------------------------
    def tag(self, action: ProposedAction):
        if self.tagger is None:
            raise RuntimeError("no tagger configured")
        r = self.tagger.tag(action)
        action.task_type, action.tag_confidence = r.task_type, r.confidence
        return r

    # ---- decide (SPEC §6) ----------------------------------------------------------------------------------
    def decide(self, action: ProposedAction, checks: ChecksResult | None = None) -> Decision:
        """Decide hold or act. Call again at execution time; the newest decision is the one that counts."""
        with self._lock:
            if action.task_type is None and self.tagger is not None:
                self.tag(action)
            if action.task_type is not None and action.tag_confidence is None:
                action.tag_confidence = 1.0             # caller-assigned type
            p = self.policy
            tt = action.task_type or ""
            k = (action.org_id, action.agent_id, tt)
            known = tt in p.task_types
            if known:
                self._maintain(k, action)
            s = self._r.states.get(k) or TrustState(trust_key=k)
            level = s.level
            if action.parent_action_id:                  # delegation cap (SPEC §11)
                parent = self._r.actions.get(action.parent_action_id)
                pk = (action.org_id, parent["agent_id"], tt) if parent else None
                ps = self._r.states.get(pk) if pk else None
                level = min(level, ps.level) if ps else 0

            why, mode = self._rule(action, checks, known, level, p)
            eps = p.eps_for(tt) if known else p.eps
            d = Decision(
                decision_id="dec_" + uuid.uuid4().hex, action_id=action.action_id, trust_key=k, mode=mode, why=why,
                level=s.level, evidence_n=round(s.n, 4), evidence_err=round(s.err, 4),
                upper_bound=round(self.bounds.upper(s.err, s.n), 6), eps=eps,
                consequence=p.task_types[tt].consequence if known else None,
                checks={"passed": list(checks.passed), "failed": list(checks.failed)} if checks else None,
                policy_version=p.policy_version, agent_version=action.agent_version,
                payload_hash=payload_hash(action.payload), created_at=self._now())
            body = d.to_dict()
            body.update(tag_confidence=action.tag_confidence, kind=action.kind,
                        parent_action_id=action.parent_action_id, effective_level=level,
                        bound=self.bounds.name)
            self._emit("decision", body)
            return d

    def _rule(self, action, checks, known, level, p) -> tuple[str, str]:
        if self._r.is_paused(action.org_id, action.agent_id, action.task_type or ""):
            return "paused", "hold"
        if not known:
            return "unknown_type", "hold"
        if action.tag_confidence is None or action.tag_confidence < p.tag_confidence_min:
            return "low_confidence", "hold"
        if checks is None and p.require_checks:
            return "checks_missing", "hold"
        if checks is not None and not checks.ok:
            return "check_failed", "hold"
        if p.is_capped(action.task_type):
            return "capped", "hold"
        if level <= L1:
            return ("delegation_cap" if action.parent_action_id else "level_L1"), "hold"
        return "trusted", "act"

    def _maintain(self, k: TrustKey, action: ProposedAction):
        """State maintenance that must happen before the level is read: unannounced versions and re-entry."""
        s = self._r.states.get(k)
        if s is None:
            return
        published = self._r.published.get(action.agent_id, set())
        if s.agent_version is not None and action.agent_version != s.agent_version \
                and action.agent_version not in published:
            # a version nobody published through on_version_published: treat as untested (discount)
            self._emit("version_unannounced", {"trust_key": list(k), "version": action.agent_version})
        if s.level >= L2 and s.last_activity_at is not None:
            gap = self.clock() - parse_iso(s.last_activity_at)
            if gap > timedelta(days=self.policy.reentry_gap_days):
                # SPEC §7 re-entry rule [tested v3]
                self._emit("level_change", {"trust_key": list(k), "to": s.level - 1, "why": "reentry_gap"})

    def decide_bundle(self, actions: list[tuple[ProposedAction, ChecksResult | None]]) -> list[Decision]:
        """SPEC §4: actions that must happen together get the most restrictive decision."""
        ds = [self.decide(a, c) for a, c in actions]
        if any(not d.allowed for d in ds):
            for d in ds:
                if d.allowed:
                    d.mode, d.why = "hold", "bundle_restricted"
        return ds

    # ---- execution -------------------------------------------------------------------------------------
    def may_execute(self, action_id: str) -> bool:
        a = self._r.actions.get(action_id)
        if a is None:
            return False
        if a.get("mode") == "act":
            return True
        return a.get("review_label") in ("approved", "cosmetic_edit", "material_edit")   # a person approved it

    def mark_executed(self, action_id: str) -> None:
        """Record that an action ran. Autonomous actions are then spot-sampled with an unpredictable RNG; the result
        goes to the review queue and is never returned to the caller (SPEC §6 step 6, §9)."""
        with self._lock:
            if not self.may_execute(action_id):
                raise PermissionError(f"action {action_id} is not allowed to execute")
            a = self._r.actions[action_id]
            autonomous = a.get("mode") == "act" and "review_label" not in a
            self._emit("executed", {"action_id": action_id, "autonomous": autonomous})
            if autonomous:
                rate = self.policy.spot_rate.get(a["level"], 0.0)
                if self._sampler.random() < rate:
                    self._emit("spot_sample", {"action_id": action_id})

    def execute(self, action: ProposedAction, run: Callable[[], Any], checks: ChecksResult | None = None):
        """Convenience: decide, run only if allowed, record execution. Returns (decision, result or None)."""
        d = self.decide(action, checks)
        if not d.allowed:
            return d, None
        result = run()
        self.mark_executed(action.action_id)
        return d, result

    def review_queue(self) -> list[dict]:
        """Held actions awaiting a person, plus sampled autonomous actions awaiting a spot-check. Platform-side only:
        never expose this to agents."""
        return list(self._r.queue.values())

    # ---- outcomes and incidents (SPEC §7) ----------------------------------------------------------------
    def record_outcome(self, action_id: str, label: str, reason_code: str | None, source: str, actor_id: str,
                       diff_ref: str | None = None) -> dict:
        with self._lock:
            if label not in LABELS:
                raise ValueError(f"unknown label {label}")
            if source not in ("pre_review", "spot_check"):
                raise ValueError("outcomes come from pre_review or spot_check; use report_incident / record_canary")
            if label in ("material_edit", "rejected") and reason_code not in REASON_CODES:
                raise ValueError("material_edit and rejected need a reason code (SPEC §9)")
            if reason_code is not None and reason_code not in REASON_CODES:
                raise ValueError(f"unknown reason code {reason_code}")
            a = self._r.actions.get(action_id)
            if a is None:
                raise KeyError(f"no decision recorded for {action_id}")
            body = {"event_id": "out_" + uuid.uuid4().hex, "action_id": action_id, "decision_id": a["decision_id"],
                    "trust_key": list(a["key"]), "agent_version": a["agent_version"], "source": source,
                    "label": label, "reason_code": reason_code, "serious": is_serious(label, reason_code),
                    "actor_id": actor_id, "diff_ref": diff_ref, "created_at": self._now()}
            self._emit("outcome", body)
            return body

    def report_incident(self, action_id: str, severity: str, actor_id: str, note: str | None = None) -> dict:
        """A serious problem found after the fact. Applied to the key and agent version *of that action* (SPEC §7)."""
        with self._lock:
            a = self._r.actions.get(action_id)
            if a is None:
                raise KeyError(f"no decision recorded for {action_id}")
            body = {"incident_id": "inc_" + uuid.uuid4().hex, "action_id": action_id, "trust_key": list(a["key"]),
                    "agent_version": a["agent_version"], "severity": severity, "actor_id": actor_id,
                    "note_hash": payload_hash(note) if note else None}
            self._emit("incident", body)
            reviewer = a.get("approved_by")
            if reviewer:   # SPEC §9: a reviewer whose approval led to an incident gets a miss
                self._emit("reviewer_evidence", {"reviewer_key": list(reviewer_key(a["org_id"], reviewer, a["task_type"])),
                                                 "miss": True, "source": "incident", "action_id": action_id})
            return body

    # ---- versions (SPEC §8) --------------------------------------------------------------------------------
    def on_version_published(self, agent_id: str, version: str, results: dict[str, dict] | None = None,
                             actor: Actor | None = None) -> dict:
        """`results[task_type] = {training_pass, hidden_pass, n_hidden?}`. A task type keeps its evidence when
        hidden_pass ≥ carry_hidden_min with ≥ min_hidden_tests hidden tests; otherwise its evidence is discounted."""
        with self._lock:
            if actor is not None and not self.governance.request(actor, "publish_version", agent_id,
                                                                 {"version": version}):
                raise PermissionError("not allowed to publish this agent")
            p = self.policy
            out = {}
            for tt, r in (results or {}).items():
                n_hidden = r.get("n_hidden", self.suites.hidden_count(tt))
                hp = r.get("hidden_pass")
                carry = hp is not None and n_hidden >= p.min_hidden_tests and hp >= p.carry_hidden_min
                out[tt] = {"training_pass": r.get("training_pass"), "hidden_pass": hp, "n_hidden": n_hidden,
                           "carry": carry}
            self._emit("version_published", {"agent_id": agent_id, "version": version, "results": out})
            return out

    # ---- oversight -----------------------------------------------------------------------------------------
    def pause(self, actor: Actor, org_id: str, agent_id: str, task_type: str | None = None) -> bool:
        with self._lock:
            if not self.governance.request(actor, "pause", agent_id, {"org_id": org_id, "task_type": task_type}):
                return False
            self._emit("pause", {"org_id": org_id, "agent_id": agent_id, "task_type": task_type})
            return True

    def resume(self, actor: Actor, org_id: str, agent_id: str, task_type: str | None = None) -> bool:
        with self._lock:
            if not self.governance.request(actor, "resume", agent_id, {"org_id": org_id, "task_type": task_type}):
                return False
            self._emit("resume", {"org_id": org_id, "agent_id": agent_id, "task_type": task_type})
            return True

    def demote(self, actor: Actor, org_id: str, agent_id: str, task_type: str) -> bool:
        with self._lock:
            if not self.governance.request(actor, "demote", agent_id, {"org_id": org_id, "task_type": task_type}):
                return False
            s = self._r.states.get((org_id, agent_id, task_type))
            if s and s.level > L1:
                self._emit("level_change", {"trust_key": [org_id, agent_id, task_type], "to": s.level - 1,
                                            "why": "manual_demote"})
            return True

    def promote(self, actor: Actor, org_id: str, agent_id: str, task_type: str) -> bool:
        """Manual promotion by the policy owner (never the agent's builder). Capped types never promote."""
        with self._lock:
            if not self.governance.request(actor, "promote", agent_id, {"org_id": org_id, "task_type": task_type}):
                return False
            if self.policy.is_capped(task_type):
                return False
            s = self._r.states.get((org_id, agent_id, task_type))
            level = s.level if s else L1
            if level < L3:
                self._emit("level_change", {"trust_key": [org_id, agent_id, task_type], "to": level + 1,
                                            "why": "manual_promote"})
            return True

    # ---- policy and catalogue (SPEC §4, §10) -------------------------------------------------------------
    def set_policy(self, actor: Actor, op: str = "set_policy", **changes) -> bool:
        """Policy-as-code: every change is a new policy version, logged and applied immediately."""
        with self._lock:
            if not self.governance.request(actor, op, None, {k: str(v) for k, v in changes.items()}):
                return False
            new = self.policy.evolve(**changes)
            self._validate(new)
            self._emit("policy", {"policy": new.to_dict()})
            return True

    def add_task_type(self, actor: Actor, task_type: str, consequence: str, tools: list[str] | None = None) -> bool:
        if consequence not in CONSEQUENCE:
            raise ValueError("consequence must be C1..C4")
        with self._lock:
            if not self.governance.request(actor, "add_task_type", None,
                                           {"task_type": task_type, "consequence": consequence}):
                return False
            tts = dict(self.policy.task_types)
            tts[task_type] = TaskTypePolicy(consequence=consequence, tools=list(tools or []))
            self._emit("policy", {"policy": self.policy.evolve(task_types=tts).to_dict()})
            return True

    def set_consequence(self, actor: Actor, task_type: str, consequence: str) -> bool:
        if consequence not in CONSEQUENCE:
            raise ValueError("consequence must be C1..C4")
        with self._lock:
            if not self.governance.request(actor, "set_consequence", None,
                                           {"task_type": task_type, "consequence": consequence}):
                return False
            tts = dict(self.policy.task_types)
            old = tts[task_type]
            tts[task_type] = TaskTypePolicy(consequence=consequence, eps=old.eps, capped=old.capped, tools=old.tools)
            new = self.policy.evolve(task_types=tts)
            self._validate(new)
            self._emit("policy", {"policy": new.to_dict()})
            return True

    def set_task_eps(self, actor: Actor, task_type: str, eps: float) -> bool:
        """Tighten a type's bar below its consequence level's ε (never loosen; SPEC §7)."""
        with self._lock:
            if not self.governance.request(actor, "set_eps", None, {"task_type": task_type, "eps": eps}):
                return False
            tts = dict(self.policy.task_types)
            old = tts[task_type]
            tts[task_type] = TaskTypePolicy(consequence=old.consequence, eps=eps, capped=old.capped, tools=old.tools)
            new = self.policy.evolve(task_types=tts)
            self._validate(new)
            self._emit("policy", {"policy": new.to_dict()})
            return True

    @staticmethod
    def _validate(p: Policy):
        for tt, tp in p.task_types.items():
            if tp.consequence not in CONSEQUENCE:
                raise ValueError(f"{tt}: unknown consequence {tp.consequence}")
            base = CONSEQUENCE[tp.consequence]["eps"]
            if tp.eps is not None and tp.eps > base:
                raise ValueError(f"{tt}: ε {tp.eps} looser than {tp.consequence}'s {base} (only tightening allowed)")

    def tools_for(self, task_type: str) -> list[str]:
        """Tool scope per task type (SPEC §4, [tested]): offer the agent only these tools."""
        tp = self.policy.type_policy(task_type)
        return list(tp.tools) if tp else []

    # ---- reviewer trust (SPEC §9, [tested v3]) -------------------------------------------------------------
    def reviewer_level(self, org_id: str, reviewer_id: str, task_type: str) -> int:
        s = self._r.reviewers.get(reviewer_key(org_id, reviewer_id, task_type))
        return s.level if s else L1

    def should_insert_canary(self, org_id: str, reviewer_id: str) -> bool:
        """Platform-side: seed a known-bad item into this reviewer's queue at the reviewer canary rate (5%)."""
        hit = self._sampler.random() < self.policy.reviewer_canary_rate
        if hit:
            self._log("canary", {"org_id": org_id, "reviewer_id": reviewer_id})
        return hit

    def record_canary(self, org_id: str, reviewer_id: str, task_type: str, caught: bool) -> None:
        with self._lock:
            self._emit("reviewer_evidence", {"reviewer_key": list(reviewer_key(org_id, reviewer_id, task_type)),
                                             "miss": not caught, "source": "canary"})

    def should_second_check(self, org_id: str, reviewer_id: str, task_type: str) -> bool:
        """R1 reviewers get 25% of decisions second-checked, R2 reviewers 5%."""
        lvl = self.reviewer_level(org_id, reviewer_id, task_type)
        hit = self._sampler.random() < self.policy.second_check_rate.get(min(lvl, L2), 0.0)
        if hit:
            self._log("second_check_sample", {"org_id": org_id, "reviewer_id": reviewer_id, "task_type": task_type})
        return hit

    def record_second_check(self, org_id: str, first_reviewer_id: str, task_type: str, found_error: bool,
                            action_id: str | None = None) -> None:
        """Every second check is evidence about the first reviewer: clean counts as clean (v3), a found error is a miss.
        Record the corrected outcome for the agent separately with record_outcome."""
        with self._lock:
            self._emit("reviewer_evidence",
                       {"reviewer_key": list(reviewer_key(org_id, first_reviewer_id, task_type)),
                        "miss": bool(found_error), "source": "second_check", "action_id": action_id})

    # ---- reading (SPEC §12) --------------------------------------------------------------------------------
    def get_state(self, org_id: str, agent_id: str, task_type: str | None = None) -> list[dict]:
        out = []
        p = self.policy
        for k, s in sorted(self._r.states.items()):
            if k[0] != org_id or k[1] != agent_id or (task_type and k[2] != task_type):
                continue
            tt = k[2]
            eps = p.eps_for(tt)
            upper = self.bounds.upper(s.err, s.n)
            rolling_upper = self.bounds.upper(sum(s.recent), len(s.recent)) if s.recent else None
            alerts = []
            if s.level >= L2 and rolling_upper is not None and len(s.recent) >= p.rolling_min \
                    and rolling_upper > p.alert_fraction * eps:
                alerts.append("rolling_error_near_bar")
            smin = p.success_min(tt)
            if smin is not None and s.n >= p.n_min and self.bounds.lower(s.n - s.fail, s.n) < smin:
                alerts.append("task_success_below_minimum")
            d = s.snapshot()
            d.update(level_name=LEVEL_NAMES[s.level], eps=eps, upper_bound=round(upper, 6),
                     consequence=p.task_types[tt].consequence if tt in p.task_types else None,
                     capped=p.is_capped(tt), paused=self._r.is_paused(org_id, agent_id, tt), alerts=alerts,
                     explanation=self._explain_state(s, eps, upper, p))
            out.append(d)
        return out

    def _explain_state(self, s, eps, upper, p) -> str:
        if p.is_capped(s.trust_key[2]):
            return "Capped task type: always held for a person."
        if s.level >= L3:
            return f"Senior: worst-case error {upper:.1%} ≤ bar {eps:.0%}."
        need = max(0, int(p.n_min - s.since_change))
        return (f"{LEVEL_NAMES[s.level]}: {s.n:.0f} judged, {s.err:.0f} serious; worst-case error {upper:.1%} vs bar "
                f"{eps:.0%}. Promotion needs the worst case under the bar and at least {need} more judged actions.")

    def explain(self, action_id: str) -> dict:
        """Every decision for the action with its evidence snapshot, the outcomes, and the policy it ran under."""
        decisions, outcomes, executed = [], [], None
        for e in self.record.entries():
            if e.body.get("action_id") != action_id:
                continue
            if e.type == "decision":
                decisions.append(e.body)
            elif e.type in ("outcome", "incident"):
                outcomes.append({"type": e.type, **e.body})
            elif e.type == "executed":
                executed = e.body
        pv = decisions[-1]["policy_version"] if decisions else None
        return {"action_id": action_id, "decisions": decisions, "outcomes": outcomes, "executed": executed,
                "policy_version": pv, "policy": self._r.policies.get(pv)}

    # ---- integrity (SPEC §13.4) --------------------------------------------------------------------------
    def rebuild_state(self) -> dict:
        """Replay the record from empty and return the derived state."""
        r = _Reducer(self.bounds)
        for e in self.record.entries():
            r.apply(e)
        return self._dump(r)

    def live_state(self) -> dict:
        return self._dump(self._r)

    @staticmethod
    def _dump(r: _Reducer) -> dict:
        return {"policy": r.policy.to_dict() if r.policy else None,
                "states": {"|".join(k): s.snapshot() for k, s in sorted(r.states.items())},
                "reviewers": {"|".join(k): s.snapshot() for k, s in sorted(r.reviewers.items())},
                "paused": sorted(map(str, r.paused)),
                "queue": copy.deepcopy(r.queue)}

    def level_changes(self) -> list[dict]:
        return list(self._r.level_changes)
