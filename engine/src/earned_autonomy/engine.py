"""The trust engine (spec/requirements/, reference API in spec/api.md).

Design: the trust record is the only source of truth. Every change is first appended to the record as an entry,
then applied by a deterministic reducer (`_Reducer.apply`). Live state is therefore always identical to a replay
of the record from empty (EA-6.9). Randomness (spot-check sampling, canaries, second checks) happens in
the engine, never in the reducer, and only its outcome is recorded.
"""
from __future__ import annotations

import copy
import dataclasses
import math
import secrets
import threading
import uuid
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Callable

from .governance import Actor, GovernanceGuard
from .models import (CONSEQUENCE, COSMETIC_REASONS, EVIDENCE_SOURCES, L1, L2, L3, LABELS, LEVEL_NAMES, RANK, REASON_CODES,
                     ChecksResult, Decision, Policy, ProposedAction, TaskTypePolicy, TrustKey, TrustState, format_timestamp,
                     is_serious, max_consequence, parse_timestamp, payload_hash, utcnow)
from .record import TrustRecord
from .stats import (BoundStrategy, ConfidenceSequenceBound, WilsonBound, dial_spot_rate, posterior_interval, promotion_table,
                    step_down_threshold, trust_score)
from .suites import SuiteStore
from .tagging import Tagger


def _key(key) -> TrustKey:
    return (key[0], key[1], key[2])


def reviewer_key(organisation_id: str, reviewer_id: str, task_type: str) -> TrustKey:
    """EA-3.12: a reviewer's trust key is (organisation, reviewer_id, review.<task_type>)."""
    return (organisation_id, reviewer_id, f"review.{task_type}")


class _Reducer:
    """All derived state. Built only by applying record entries, in order."""

    def __init__(self, bounds: BoundStrategy):
        self.bounds = bounds
        self.policy: Policy | None = None
        self.policies: dict[int, dict] = {}
        self.states: dict[TrustKey, TrustState] = {}
        self.reviewers: dict[TrustKey, TrustState] = {}
        self.paused: set[tuple] = set()                     # (organisation, agent, task_type|None)
        self.actions: dict[str, dict] = {}                  # action_id -> index
        self.published: dict[str, set] = {}                 # agent_id -> versions published
        self.queue: dict[str, dict] = {}                    # action_id -> review item (pre_review | spot_check)
        self.level_changes: list[dict] = []
        self.retired: set[tuple] = set()                    # (organisation, agent, task_type) (EA-5.4)
        self.incidents: list[dict] = []                     # {key, timestamp} (EA-1.16 summary)

    # ---- helpers -----------------------------------------------------------------------------------------
    def state(self, key: TrustKey) -> TrustState:
        if key not in self.states:
            self.states[key] = TrustState(trust_key=key)
        return self.states[key]

    def reviewer_state(self, key: TrustKey) -> TrustState:
        if key not in self.reviewers:
            self.reviewers[key] = TrustState(trust_key=key)
        return self.reviewers[key]

    def promotion_upper_bound(self, policy: Policy | None, task_type: str, serious_errors: float, judged: float,
                              error_bar: float) -> float:
        """Upper bound used for promotion and for "does the bound still hold" (EA-2.14, EA-2.19). Strict promotion types use
        the anytime-valid confidence sequence; everything else uses the engine's default bound (Wilson)."""
        if policy is not None and error_bar > 0 and policy.is_strict(task_type):
            return ConfidenceSequenceBound(error_bar).upper(serious_errors, judged)
        return self.bounds.upper(serious_errors, judged)

    def _set_level(self, state: TrustState, to: int, why: str, timestamp: str):
        from_level = state.level
        state.level, state.since_change = to, 0.0
        state.recent = []
        self.level_changes.append({"key": list(state.trust_key), "from": from_level, "to": to, "why": why, "timestamp": timestamp})

    def _touch(self, state: TrustState, timestamp: str):
        state.state_version += 1
        state.updated_at = timestamp

    def _observe(self, state: TrustState, serious: bool, fail: bool, timestamp: str, error_bar: float, capped: bool,
                 min_judged: int, rolling_window: int, rolling_window_min: int, top: int = L3, rule: str = "bound"):
        """EA-2.14 to EA-2.17: evidence, then step-down first, then promotion. `rule` = "core_table" applies the
        published lookup tables (EA-2.15) instead of computing bounds; strict types always use their bound."""
        state.judged_count += 1
        state.serious_error_count += 1 if serious else 0
        state.incomplete_count += 1 if fail else 0
        state.since_change += 1
        state.recent.append(1 if serious else 0)
        if len(state.recent) > rolling_window:
            state.recent = state.recent[-rolling_window:]
        table = rule == "core_table" and not (self.policy is not None and self.policy.is_strict(state.trust_key[2]))
        if table:
            threshold = step_down_threshold(error_bar, rolling_window)
            step_down = state.level >= L2 and threshold is not None and sum(state.recent) >= threshold
        else:
            step_down = (state.level >= L2 and len(state.recent) >= rolling_window_min
                         and self.bounds.lower(sum(state.recent), len(state.recent)) > error_bar)
        if step_down:
            self._set_level(state, state.level - 1, "rolling_bound", timestamp)
        elif not capped and error_bar > 0 and state.level < top and state.since_change >= min_judged:
            if table:
                needed = promotion_table(error_bar)
                errors = math.ceil(state.serious_error_count - 1e-9)
                earned = errors < len(needed) and state.judged_count >= needed[errors]
            else:
                earned = self.promotion_upper_bound(self.policy, state.trust_key[2], state.serious_error_count,
                                                    state.judged_count, error_bar) <= error_bar
            if earned:
                self._set_level(state, state.level + 1, "evidence", timestamp)

    def _discount(self, state: TrustState, error_bar: float, weight: float, timestamp: str, why: str):
        state.judged_count *= weight
        state.serious_error_count *= weight
        state.incomplete_count *= weight
        for tally in state.evidence.values():      # EA-4.7 applies to every evidence source
            tally[0] *= weight
            tally[1] *= weight
        if state.level >= L2 and self.promotion_upper_bound(self.policy, state.trust_key[2], state.serious_error_count, state.judged_count, error_bar) > error_bar:
            self._set_level(state, L1, why, timestamp)

    # ---- apply -------------------------------------------------------------------------------------------
    def apply(self, entry) -> None:
        body, timestamp = entry.body, entry.timestamp
        entry_type = entry.type
        policy = self.policy
        if entry_type == "policy":
            new = Policy.from_dict(body["policy"])
            self.policy = new
            self.policies[new.policy_version] = body["policy"]
            # EA-6.6: policy changes take effect immediately; a trusted key whose bound no longer holds
            # (or whose type became capped) drops to L1.
            for state in self.states.values():
                task_type = state.trust_key[2]
                if state.level >= L2 and (new.is_capped(task_type) or
                                      self.promotion_upper_bound(new, task_type, state.serious_error_count, state.judged_count, new.error_bar_for(task_type)) > new.error_bar_for(task_type)):
                    self._set_level(state, L1, "policy_change", timestamp)
                    self._touch(state, timestamp)
        elif entry_type == "decision":
            key = _key(body["trust_key"])
            state = self.state(key)
            if state.agent_version is None:
                state.agent_version = body["agent_version"]
            state.last_activity_at = body["created_at"]
            self._touch(state, timestamp)
            action_record = self.actions.setdefault(body["action_id"], {"outcomes": [], "decisions": []})
            action_record.update(key=key, agent_version=body["agent_version"], decision_id=body["decision_id"], mode=body["mode"],
                     level=body["level"], agent_id=key[1], organisation_id=key[0], task_type=key[2])
            action_record["decisions"].append(body["decision_id"])
            if body["mode"] == "hold":
                self.queue[body["action_id"]] = {"action_id": body["action_id"], "kind": "pre_review", "key": list(key),
                                              "why": body["why"], "since": timestamp}
        elif entry_type == "level_change":
            state = self.state(_key(body["trust_key"]))
            self._set_level(state, body["to"], body["why"], timestamp)
            self._touch(state, timestamp)
        elif entry_type == "outcome":
            key = _key(body["trust_key"])
            state = self.state(key)
            task_type = key[2]
            self._observe(state, body["serious"], body["label"] == "incomplete", timestamp, policy.error_bar_for(task_type), policy.is_capped(task_type),
                          policy.min_judged, policy.rolling_window, policy.rolling_window_min, rule=policy.promotion_rule)
            state.last_evidence_at = timestamp
            self._touch(state, timestamp)
            action_record = self.actions.setdefault(body["action_id"], {"outcomes": [], "decisions": []})
            action_record["outcomes"].append(body["event_id"])
            if body["source"] == "pre_review":
                action_record["review_label"] = body["label"]
                if body["label"] in ("approved", "cosmetic_edit"):
                    action_record["approved_by"] = body["actor_id"]
            self.queue.pop(body["action_id"], None)
        elif entry_type == "incident":
            key = _key(body["trust_key"])
            state = self.state(key)
            # EA-2.18: counts as one serious outcome AND steps the key down one level immediately.
            state.judged_count += 1
            state.serious_error_count += 1
            state.last_evidence_at = timestamp
            self.incidents.append({"key": list(key), "timestamp": timestamp})
            if state.level >= L2:
                self._set_level(state, state.level - 1, "incident", timestamp)
            self._touch(state, timestamp)
        elif entry_type == "evidence":
            # EA-1.18: non-human evidence (shadow, replay, test). Trust score only; never a level change (EA-1.21).
            state = self.state(_key(body["trust_key"]))
            tally = state.evidence.setdefault(body["source"], [0.0, 0.0])
            tally[0] += 1
            tally[1] += 1 if body["serious"] else 0
            state.last_evidence_at = timestamp
            self._touch(state, timestamp)
        elif entry_type == "retire":
            self.retired.add((body["organisation_id"], body["agent_id"], body["task_type"]))
        elif entry_type == "reactivate":
            # EA-5.6: a reactivated task type starts again from Supervised, with its old evidence discounted
            key = _key((body["organisation_id"], body["agent_id"], body["task_type"]))
            self.retired.discard(key)
            state = self.state(key)
            self._discount(state, policy.error_bar_for(key[2]), policy.version_discount, timestamp, "reactivated")
            if state.level > L1:
                self._set_level(state, L1, "reactivated", timestamp)
            self._touch(state, timestamp)
        elif entry_type == "executed":
            action_record = self.actions.setdefault(body["action_id"], {"outcomes": [], "decisions": []})
            action_record["executed"] = True
            action_record["executed_at"] = timestamp
            action_record["autonomous"] = body["autonomous"]
        elif entry_type == "spot_sample":
            action_record = self.actions.get(body["action_id"], {})
            self.queue[body["action_id"]] = {"action_id": body["action_id"], "kind": "spot_check",
                                          "key": list(action_record.get("key", ())), "why": "sampled", "since": timestamp}
        elif entry_type == "version_published":
            agent = body["agent_id"]
            self.published.setdefault(agent, set()).add(body["version"])
            for state in self.states.values():
                if state.trust_key[1] != agent:
                    continue
                task_type = state.trust_key[2]
                result = body["results"].get(task_type)
                if not (result and result.get("carry")):
                    self._discount(state, policy.error_bar_for(task_type), policy.version_discount, timestamp, "version_change")
                state.agent_version = body["version"]
                self._touch(state, timestamp)
        elif entry_type == "version_unannounced":
            state = self.state(_key(body["trust_key"]))
            self._discount(state, policy.error_bar_for(state.trust_key[2]), policy.version_discount, timestamp, "version_change")
            state.agent_version = body["version"]
            self._touch(state, timestamp)
        elif entry_type == "pause":
            self.paused.add((body["organisation_id"], body["agent_id"], body.get("task_type")))
        elif entry_type == "resume":
            self.paused.discard((body["organisation_id"], body["agent_id"], body.get("task_type")))
        elif entry_type == "reviewer_evidence":
            state = self.reviewer_state(_key(body["reviewer_key"]))
            self._observe(state, body["miss"], False, timestamp, policy.reviewer_error_bar, False, policy.reviewer_min_judged, policy.rolling_window,
                          policy.rolling_window_min, top=L2)
            self._touch(state, timestamp)
        # governance, canary, second_check_sample: log-only entries

    def is_paused(self, organisation: str, agent: str, task_type: str) -> bool:
        return (organisation, agent, None) in self.paused or (organisation, agent, task_type) in self.paused

    def is_retired(self, organisation: str, agent: str, task_type: str) -> bool:
        return (organisation, agent, task_type) in self.retired


class TrustEngine:
    """Reference implementation of the Earned Autonomy trust engine (spec/api.md)."""

    def __init__(self, policy: Policy | None = None, record: TrustRecord | None = None, tagger: Tagger | None = None,
                 bounds: BoundStrategy | None = None, clock: Callable[[], datetime] = utcnow,
                 sampler=None, tool_floor_function: Callable[[str, Any, Policy], str | None] | None = None):
        self.record = record if record is not None else TrustRecord()
        self.tagger = tagger
        self.bounds = bounds or WilsonBound()
        self.clock = clock
        # EA-7.8: optional argument-dependent tool floors, e.g. send_email -> C1 for a reminder, C3 for an offer.
        # Returns a consequence level, or None to fall back to the policy's floor for that tool.
        self.tool_floor_function = tool_floor_function
        # EA-3.1, EA-3.2: sampling must be unpredictable to the agent. Default: the OS CSPRNG.
        self._sampler = sampler or secrets.SystemRandom()
        self._lock = threading.RLock()
        self.governance = GovernanceGuard(self._log)
        self.suites = SuiteStore(self.governance)
        self._reducer = _Reducer(self.bounds)
        for entry in self.record.entries():           # existing record: rebuild from it
            self._reducer.apply(entry)
        if self._reducer.policy is None:
            self._emit("policy", {"policy": (policy or Policy()).to_dict()})

    # ---- plumbing ----------------------------------------------------------------------------------------
    def _now(self) -> str:
        return format_timestamp(self.clock())

    def _emit(self, entry_type: str, body: dict):
        entry = self.record.append(entry_type, body, self._now())
        self._reducer.apply(entry)
        return entry

    def _log(self, entry_type: str, body: dict):
        self.record.append(entry_type, body, self._now())

    @property
    def policy(self) -> Policy:
        return self._reducer.policy

    # ---- tagging (EA-7.5) ----------------------------------------------------------------------------------
    def tag(self, action: ProposedAction):
        if self.tagger is None:
            raise RuntimeError("no tagger configured")
        result = self.tagger.tag(action)
        action.task_type, action.tag_confidence = result.task_type, result.confidence
        return result

    # ---- decide (EA-2.1) -----------------------------------------------------------------------------------
    def decide(self, action: ProposedAction, checks: ChecksResult | None = None) -> Decision:
        """Decide hold or act. Call again at execution time; the newest decision is the one that counts."""
        with self._lock:
            if action.task_type is None and self.tagger is not None:
                self.tag(action)
            if action.task_type is not None and action.tag_confidence is None:
                action.tag_confidence = 1.0             # caller-assigned type
            policy = self.policy
            task_type = action.task_type or ""
            key = (action.organisation_id, action.agent_id, task_type)
            known = task_type in policy.task_types
            if known:
                self._maintain(key, action)
            state = self._reducer.states.get(key) or TrustState(trust_key=key)
            level = state.level
            if action.parent_action_id:                  # delegation cap (EA-8.1)
                parent = self._reducer.actions.get(action.parent_action_id)
                parent_key = (action.organisation_id, parent["agent_id"], task_type) if parent else None
                parent_state = self._reducer.states.get(parent_key) if parent_key else None
                level = min(level, parent_state.level) if parent_state else 0

            floor = self.tool_floor(action) if known else None
            why, mode = self._rule(action, checks, known, level, policy, floor)
            error_bar = policy.error_bar_for(task_type) if known else policy.error_bar
            decision = Decision(
                decision_id="decision_" + uuid.uuid4().hex, action_id=action.action_id, trust_key=key, mode=mode, why=why,
                level=state.level, judged_count=round(state.judged_count, 4), serious_error_count=round(state.serious_error_count, 4),
                upper_bound=round(self._reducer.promotion_upper_bound(policy, task_type, state.serious_error_count, state.judged_count, error_bar), 6), error_bar=error_bar,
                consequence=max_consequence(policy.task_types[task_type].consequence, floor) if known else None,
                tool_floor=floor,
                checks={"passed": list(checks.passed), "failed": list(checks.failed)} if checks else None,
                policy_version=policy.policy_version, agent_version=action.agent_version,
                payload_hash=payload_hash(action.payload), created_at=self._now())
            body = decision.to_dict()
            body.update(tag_confidence=action.tag_confidence, kind=action.kind,
                        parent_action_id=action.parent_action_id, effective_level=level,
                        write_tools=list(action.write_tools),
                        bound="confidence_sequence" if known and policy.is_strict(task_type) and error_bar > 0 else self.bounds.name)
            self._emit("decision", body)
            return decision

    def tool_floor(self, action: ProposedAction) -> str | None:
        """EA-7.8: the highest floor among the action's write tools (hook first, then the policy's floor)."""
        policy = self.policy
        levels = []
        for tool in action.write_tools:
            floor_level = self.tool_floor_function(tool, action.write_tool_arguments.get(tool), policy) if self.tool_floor_function else None
            if floor_level is not None and floor_level not in RANK:
                raise ValueError(f"tool_floor_function returned {floor_level!r} for {tool}; expected C1..C4")
            levels.append(floor_level or policy.tool_floor(tool))
        return max_consequence(*levels)

    def _rule(self, action, checks, known, level, policy, floor=None) -> tuple[str, str]:
        if self._reducer.is_paused(action.organisation_id, action.agent_id, action.task_type or ""):
            return "paused", "hold"
        if self._reducer.is_retired(action.organisation_id, action.agent_id, action.task_type or ""):
            return "retired", "hold"                     # EA-5.4
        if not known:
            return "unknown_type", "hold"
        if action.tag_confidence is None or action.tag_confidence < policy.tag_confidence_min:
            return "low_confidence", "hold"
        if floor is not None and RANK[floor] > RANK[policy.task_types[action.task_type].consequence]:
            return "tool_floor_mismatch", "hold"          # EA-2.5
        if checks is None and policy.require_checks:
            return "checks_missing", "hold"
        if checks is not None and not checks.ok:
            return "check_failed", "hold"
        if policy.is_capped(action.task_type):
            return "capped", "hold"
        if level <= L1:
            return ("delegation_cap" if action.parent_action_id else "level_L1"), "hold"
        return "trusted", "act"

    def _maintain(self, key: TrustKey, action: ProposedAction):
        """State maintenance that must happen before the level is read: unannounced versions and re-entry."""
        state = self._reducer.states.get(key)
        if state is None:
            return
        published = self._reducer.published.get(action.agent_id, set())
        if state.agent_version is not None and action.agent_version != state.agent_version \
                and action.agent_version not in published:
            # a version nobody published through on_version_published: treat as untested (discount)
            self._emit("version_unannounced", {"trust_key": list(key), "version": action.agent_version})
        if state.level >= L2 and state.last_activity_at is not None:
            gap = self.clock() - parse_timestamp(state.last_activity_at)
            if gap > timedelta(days=self.policy.reentry_gap_days):
                # EA-5.1 re-entry rule
                self._emit("level_change", {"trust_key": list(key), "to": state.level - 1, "why": "reentry_gap"})

    def decide_bundle(self, actions: list[tuple[ProposedAction, ChecksResult | None]]) -> list[Decision]:
        """EA-2.10: actions that must happen together get the most restrictive decision."""
        decisions = [self.decide(action, checks) for action, checks in actions]
        if any(not decision.allowed for decision in decisions):
            for decision in decisions:
                if decision.allowed:
                    decision.mode, decision.why = "hold", "bundle_restricted"
        return decisions

    # ---- execution -------------------------------------------------------------------------------------
    def may_execute(self, action_id: str) -> bool:
        action_record = self._reducer.actions.get(action_id)
        if action_record is None:
            return False
        if action_record.get("mode") == "act":
            return True
        return action_record.get("review_label") in ("approved", "cosmetic_edit", "material_edit")   # a person approved it

    def mark_executed(self, action_id: str) -> None:
        """Record that an action ran. Autonomous actions are then spot-sampled with an unpredictable RNG; the result
        goes to the review queue and is never returned to the caller (EA-3.1, EA-3.3)."""
        with self._lock:
            if not self.may_execute(action_id):
                raise PermissionError(f"action {action_id} is not allowed to execute")
            action_record = self._reducer.actions[action_id]
            autonomous = action_record.get("mode") == "act" and "review_label" not in action_record
            self._emit("executed", {"action_id": action_id, "autonomous": autonomous})
            if autonomous:
                rate = self.policy.spot_rate.get(action_record["level"], 0.0)
                if self._sampler.random() < rate:
                    self._emit("spot_sample", {"action_id": action_id})

    def execute(self, action: ProposedAction, run: Callable[[], Any], checks: ChecksResult | None = None):
        """Convenience: decide, run only if allowed, record execution. Returns (decision, result or None)."""
        decision = self.decide(action, checks)
        if not decision.allowed:
            return decision, None
        result = run()
        self.mark_executed(action.action_id)
        return decision, result

    def review_queue(self) -> list[dict]:
        """Held actions awaiting a person, plus sampled autonomous actions awaiting a spot-check. Platform-side only:
        never expose this to agents."""
        return list(self._reducer.queue.values())

    # ---- outcomes and incidents (EA-1.2 to EA-1.4, EA-2.14 to EA-2.18)------------------------------------------------------------
    def record_outcome(self, action_id: str, label: str, reason_code: str | None, source: str, actor_id: str,
                       diff_reference: str | None = None) -> dict:
        with self._lock:
            if label not in LABELS:
                raise ValueError(f"unknown label {label}")
            if source not in ("pre_review", "spot_check"):
                raise ValueError("outcomes come from pre_review or spot_check; use report_incident / record_canary")
            if label in ("material_edit", "rejected") and reason_code not in REASON_CODES:
                raise ValueError("material_edit and rejected need a reason code (EA-3.5)")
            if reason_code is not None and reason_code not in REASON_CODES:
                raise ValueError(f"unknown reason code {reason_code}")
            action_record = self._reducer.actions.get(action_id)
            if action_record is None:
                raise KeyError(f"no decision recorded for {action_id}")
            body = {"event_id": "outcome_" + uuid.uuid4().hex, "action_id": action_id, "decision_id": action_record["decision_id"],
                    "trust_key": list(action_record["key"]), "agent_version": action_record["agent_version"], "source": source,
                    "label": label, "reason_code": reason_code, "serious": is_serious(label, reason_code),
                    "actor_id": actor_id, "diff_reference": diff_reference, "created_at": self._now()}
            self._emit("outcome", body)
            return body

    def report_incident(self, action_id: str, severity: str, actor_id: str, note: str | None = None) -> dict:
        """A serious problem found after the fact. Applied to the key and agent version *of that action* (EA-1.10)."""
        with self._lock:
            action_record = self._reducer.actions.get(action_id)
            if action_record is None:
                raise KeyError(f"no decision recorded for {action_id}")
            body = {"incident_id": "incident_" + uuid.uuid4().hex, "action_id": action_id, "trust_key": list(action_record["key"]),
                    "agent_version": action_record["agent_version"], "severity": severity, "actor_id": actor_id,
                    "note_hash": payload_hash(note) if note else None}
            self._emit("incident", body)
            reviewer = action_record.get("approved_by")
            if reviewer:   # EA-3.14: a reviewer whose approval led to an incident gets a miss
                self._emit("reviewer_evidence", {"reviewer_key": list(reviewer_key(action_record["organisation_id"], reviewer, action_record["task_type"])),
                                                 "miss": True, "source": "incident", "action_id": action_id})
            return body

    # ---- versions (EA-4.5 to EA-4.9)----------------------------------------------------------------------------
    def on_version_published(self, agent_id: str, version: str, results: dict[str, dict] | None = None,
                             actor: Actor | None = None) -> dict:
        """`results[task_type] = {training_pass, hidden_pass, hidden_test_count?}`. A task type keeps its evidence when
        hidden_pass ≥ carry_hidden_min with ≥ min_hidden_tests hidden tests; otherwise its evidence is discounted."""
        with self._lock:
            if actor is not None and not self.governance.request(actor, "publish_version", agent_id,
                                                                 {"version": version}):
                raise PermissionError("not allowed to publish this agent")
            policy = self.policy
            out = {}
            for task_type, result in (results or {}).items():
                hidden_test_count = result.get("hidden_test_count", self.suites.hidden_count(task_type))
                hidden_pass = result.get("hidden_pass")
                carry = hidden_pass is not None and hidden_test_count >= policy.min_hidden_tests and hidden_pass >= policy.carry_hidden_min
                out[task_type] = {"training_pass": result.get("training_pass"), "hidden_pass": hidden_pass, "hidden_test_count": hidden_test_count,
                           "carry": carry}
            self._emit("version_published", {"agent_id": agent_id, "version": version, "results": out})
            return out

    # ---- oversight -----------------------------------------------------------------------------------------
    def pause(self, actor: Actor, organisation_id: str, agent_id: str, task_type: str | None = None) -> bool:
        with self._lock:
            if not self.governance.request(actor, "pause", agent_id, {"organisation_id": organisation_id, "task_type": task_type}):
                return False
            self._emit("pause", {"organisation_id": organisation_id, "agent_id": agent_id, "task_type": task_type})
            return True

    def resume(self, actor: Actor, organisation_id: str, agent_id: str, task_type: str | None = None) -> bool:
        with self._lock:
            if not self.governance.request(actor, "resume", agent_id, {"organisation_id": organisation_id, "task_type": task_type}):
                return False
            self._emit("resume", {"organisation_id": organisation_id, "agent_id": agent_id, "task_type": task_type})
            return True

    def demote(self, actor: Actor, organisation_id: str, agent_id: str, task_type: str) -> bool:
        with self._lock:
            if not self.governance.request(actor, "demote", agent_id, {"organisation_id": organisation_id, "task_type": task_type}):
                return False
            state = self._reducer.states.get((organisation_id, agent_id, task_type))
            if state and state.level > L1:
                self._emit("level_change", {"trust_key": [organisation_id, agent_id, task_type], "to": state.level - 1,
                                            "why": "manual_demote"})
            return True

    def promote(self, actor: Actor, organisation_id: str, agent_id: str, task_type: str) -> bool:
        """Manual promotion by the policy owner (never the agent's builder). Capped types never promote."""
        with self._lock:
            if not self.governance.request(actor, "promote", agent_id, {"organisation_id": organisation_id, "task_type": task_type}):
                return False
            if self.policy.is_capped(task_type):
                return False
            state = self._reducer.states.get((organisation_id, agent_id, task_type))
            level = state.level if state else L1
            if level < L3:
                self._emit("level_change", {"trust_key": [organisation_id, agent_id, task_type], "to": level + 1,
                                            "why": "manual_promote"})
            return True

    # ---- policy and catalogue (EA-6.2, EA-6.6) ------------------------------------------------------------
    def set_policy(self, actor: Actor, operation: str = "set_policy", **changes) -> bool:
        """Policy-as-code: every change is a new policy version, logged and applied immediately."""
        with self._lock:
            if not self.governance.request(actor, operation, None, {key: str(v) for key, v in changes.items()}):
                return False
            new = self.policy.evolve(**changes)
            self._validate(new)
            self._emit("policy", {"policy": new.to_dict()})
            return True

    def add_task_type(self, actor: Actor, task_type: str, consequence: str, tools: list[str] | None = None,
                      description: str = "", examples: list[str] | None = None) -> bool:
        """Add a catalogue entry (EA-7.1): name, consequence, tools, and the description and examples the tagger
        and reviewers work from."""
        if consequence not in CONSEQUENCE:
            raise ValueError("consequence must be C1..C4")
        with self._lock:
            if not self.governance.request(actor, "add_task_type", None,
                                           {"task_type": task_type, "consequence": consequence}):
                return False
            task_types = dict(self.policy.task_types)
            task_types[task_type] = TaskTypePolicy(consequence=consequence, tools=list(tools or []),
                                                   description=description, examples=list(examples or []))
            self._emit("policy", {"policy": self.policy.evolve(task_types=task_types).to_dict()})
            return True

    def set_consequence(self, actor: Actor, task_type: str, consequence: str) -> bool:
        if consequence not in CONSEQUENCE:
            raise ValueError("consequence must be C1..C4")
        with self._lock:
            if not self.governance.request(actor, "set_consequence", None,
                                           {"task_type": task_type, "consequence": consequence}):
                return False
            task_types = dict(self.policy.task_types)
            old = task_types[task_type]
            task_types[task_type] = dataclasses.replace(old, consequence=consequence)
            new = self.policy.evolve(task_types=task_types)
            self._validate(new)
            self._emit("policy", {"policy": new.to_dict()})
            return True

    def set_task_error_bar(self, actor: Actor, task_type: str, error_bar: float) -> bool:
        """Tighten a type's bar below its consequence level's ε (never loosen; EA-1.6)."""
        with self._lock:
            if not self.governance.request(actor, "set_error_bar", None, {"task_type": task_type, "error_bar": error_bar}):
                return False
            task_types = dict(self.policy.task_types)
            old = task_types[task_type]
            task_types[task_type] = dataclasses.replace(old, error_bar=error_bar)
            new = self.policy.evolve(task_types=task_types)
            self._validate(new)
            self._emit("policy", {"policy": new.to_dict()})
            return True

    @staticmethod
    def _validate(policy: Policy):
        for task_type, type_policy in policy.task_types.items():
            if type_policy.consequence not in CONSEQUENCE:
                raise ValueError(f"{task_type}: unknown consequence {type_policy.consequence}")
            base = CONSEQUENCE[type_policy.consequence]["error_bar"]
            if type_policy.error_bar is not None and type_policy.error_bar > base:
                raise ValueError(f"{task_type}: error bar {type_policy.error_bar} looser than {type_policy.consequence}'s {base} (only tightening allowed)")

    def tools_for(self, task_type: str) -> list[str]:
        """Tool scope per task type (EA-7.7): offer the agent only these tools."""
        type_policy = self.policy.type_policy(task_type)
        return list(type_policy.tools) if type_policy else []

    # ---- reviewer trust (EA-3.11 to EA-3.15) -------------------------------------------------------------
    def reviewer_level(self, organisation_id: str, reviewer_id: str, task_type: str) -> int:
        state = self._reducer.reviewers.get(reviewer_key(organisation_id, reviewer_id, task_type))
        return state.level if state else L1

    def should_insert_canary(self, organisation_id: str, reviewer_id: str) -> bool:
        """Platform-side: seed a known-bad item into this reviewer's queue at the reviewer canary rate (5%)."""
        hit = self._sampler.random() < self.policy.reviewer_canary_rate
        if hit:
            self._log("canary", {"organisation_id": organisation_id, "reviewer_id": reviewer_id})
        return hit

    def record_canary(self, organisation_id: str, reviewer_id: str, task_type: str, caught: bool) -> None:
        with self._lock:
            self._emit("reviewer_evidence", {"reviewer_key": list(reviewer_key(organisation_id, reviewer_id, task_type)),
                                             "miss": not caught, "source": "canary"})

    def should_second_check(self, organisation_id: str, reviewer_id: str, task_type: str) -> bool:
        """R1 reviewers get 25% of decisions second-checked, R2 reviewers 5%."""
        current_level = self.reviewer_level(organisation_id, reviewer_id, task_type)
        hit = self._sampler.random() < self.policy.second_check_rate.get(min(current_level, L2), 0.0)
        if hit:
            self._log("second_check_sample", {"organisation_id": organisation_id, "reviewer_id": reviewer_id, "task_type": task_type})
        return hit

    def record_second_check(self, organisation_id: str, first_reviewer_id: str, task_type: str, found_error: bool,
                            action_id: str | None = None) -> None:
        """Every second check is evidence about the first reviewer: clean counts as clean (v3), a found error is a miss.
        Record the corrected outcome for the agent separately with record_outcome."""
        with self._lock:
            self._emit("reviewer_evidence",
                       {"reviewer_key": list(reviewer_key(organisation_id, first_reviewer_id, task_type)),
                        "miss": bool(found_error), "source": "second_check", "action_id": action_id})

    # ---- reading (spec/api.md) -----------------------------------------------------------------------------
    def get_state(self, organisation_id: str, agent_id: str, task_type: str | None = None) -> list[dict]:
        out = []
        policy = self.policy
        for key, state in sorted(self._reducer.states.items()):
            if key[0] != organisation_id or key[1] != agent_id or (task_type and key[2] != task_type):
                continue
            task_type = key[2]
            error_bar = policy.error_bar_for(task_type)
            upper = self._reducer.promotion_upper_bound(policy, task_type, state.serious_error_count, state.judged_count, error_bar)
            rolling_upper = self.bounds.upper(sum(state.recent), len(state.recent)) if state.recent else None
            alerts = []
            if state.level >= L2 and rolling_upper is not None and len(state.recent) >= policy.rolling_window_min \
                    and rolling_upper > policy.alert_fraction * error_bar:
                alerts.append("rolling_error_near_bar")
            success_minimum = policy.success_min(task_type)
            if success_minimum is not None and state.judged_count >= policy.min_judged and self.bounds.lower(state.judged_count - state.incomplete_count, state.judged_count) < success_minimum:
                alerts.append("task_success_below_minimum")
            row = state.snapshot()
            row.update(level_name=LEVEL_NAMES[state.level], error_bar=error_bar, upper_bound=round(upper, 6),
                     bound="confidence_sequence" if policy.is_strict(task_type) and error_bar > 0 else self.bounds.name,
                     consequence=policy.task_types[task_type].consequence if task_type in policy.task_types else None,
                     capped=policy.is_capped(task_type), paused=self._reducer.is_paused(organisation_id, agent_id, task_type), alerts=alerts,
                     explanation=self._explain_state(state, error_bar, upper, policy))
            out.append(row)
        return out

    # ---- MEASURE (EA-1.13 to EA-1.21) ------------------------------------------------------------------------
    def record_evidence(self, organisation_id: str, agent_id: str, task_type: str, source: str, serious: bool,
                        actor_id: str, agent_version: str | None = None, reference: Any = None) -> dict:
        """Evidence from a source other than live human judgement (EA-1.18): `shadow` (the agent's draft compared
        with what a person actually did), `replay` (graded against past human-handled cases) or `test`
        (pre-deployment tests). It feeds the trust score at the source's weight and never changes the trust
        key's autonomy setting (EA-1.21). Only a hash of `reference` enters the record (EA-6.14)."""
        with self._lock:
            if source not in EVIDENCE_SOURCES or source == "human":
                raise ValueError("source must be shadow, replay or test; human judgements go through record_outcome")
            body = {"evidence_id": "evidence_" + uuid.uuid4().hex,
                    "trust_key": [organisation_id, agent_id, task_type], "source": source, "serious": bool(serious),
                    "actor_id": actor_id, "agent_version": agent_version,
                    "reference_hash": payload_hash(reference) if reference is not None else None}
            self._emit("evidence", body)
            return body

    def _weighted_evidence(self, state: TrustState, policy: Policy) -> tuple[float, float, dict]:
        weights = policy.evidence_weights
        by_source = {"human": {"judged": round(state.judged_count, 4), "serious": round(state.serious_error_count, 4),
                               "weight": weights.get("human", 1.0)}}
        for source, (judged, serious) in sorted(state.evidence.items()):
            by_source[source] = {"judged": round(judged, 4), "serious": round(serious, 4), "weight": weights.get(source, 0.0)}
        judged = sum(entry["judged"] * entry["weight"] for entry in by_source.values())
        serious = sum(entry["serious"] * entry["weight"] for entry in by_source.values())
        return judged, serious, by_source

    def trust_score(self, organisation_id: str, agent_id: str, task_type: str) -> float:
        """EA-1.14: posterior probability that the trust key's true serious-error rate is below its error bar."""
        policy = self.policy
        state = self._reducer.states.get((organisation_id, agent_id, task_type)) or TrustState(
            trust_key=(organisation_id, agent_id, task_type))
        judged, serious, _ = self._weighted_evidence(state, policy)
        error_bar = 0.0 if policy.is_capped(task_type) else policy.error_bar_for(task_type)
        return trust_score(serious, judged, error_bar, tuple(policy.trust_prior))

    def _trend(self, state: TrustState, policy: Policy) -> str:
        if len(state.recent) < policy.rolling_window_min or state.judged_count <= 0:
            return "insufficient"
        overall = state.serious_error_count / state.judged_count
        recent_errors, recent_judged = sum(state.recent), len(state.recent)
        if self.bounds.lower(recent_errors, recent_judged) > overall:
            return "slipping"
        if self.bounds.upper(recent_errors, recent_judged) < overall:
            return "improving"
        return "stable"

    def trust_report(self, organisation_id: str, agent_id: str, task_type: str | None = None) -> dict:
        """EA-1.13, EA-1.15, EA-1.16: the trust profile of each of the agent's task types, measurable at any time,
        and a summary for the agent. Derived entirely from the trust record."""
        with self._lock:
            policy = self.policy
            states = {key: state for key, state in self._reducer.states.items()
                      if key[0] == organisation_id and key[1] == agent_id and (task_type is None or key[2] == task_type)}
            volume: dict = {}
            for action_record in self._reducer.actions.values():
                key = action_record.get("key")
                if key in states:
                    volume[key] = volume.get(key, 0) + 1
            alerts_by_key = {tuple(row["trust_key"]): row["alerts"] for row in self.get_state(organisation_id, agent_id, task_type)}
            profiles = []
            for key, state in sorted(states.items()):
                name = key[2]
                capped = policy.is_capped(name)
                error_bar = 0.0 if capped else policy.error_bar_for(name)
                judged, serious, by_source = self._weighted_evidence(state, policy)
                prior = tuple(policy.trust_prior)
                score = trust_score(serious, judged, error_bar, prior)
                mean, low, high = posterior_interval(serious, judged, prior)
                human_weighted = by_source["human"]["judged"] * by_source["human"]["weight"]
                human_share = human_weighted / judged if judged > 0 else None
                alerts = list(alerts_by_key.get(key, []))
                if human_share is not None and human_share < policy.human_evidence_min_share:
                    alerts.append("human_evidence_share_below_minimum")
                retired = self._reducer.is_retired(*key)
                paused = self._reducer.is_paused(*key)
                # EA-1.18: pre-deployment tests are never the only evidence for trust
                tests_only = judged > 0 and judged == by_source.get("test", {"judged": 0})["judged"] * by_source.get("test", {"weight": 0})["weight"]
                if capped:
                    implied = "capped"
                elif score >= policy.trust_score_threshold and not tests_only:
                    implied = "trusted_or_above"
                else:
                    implied = "supervised"
                setting = ("retired" if retired else "paused" if paused else "capped" if capped
                           else LEVEL_NAMES[state.level].lower())
                profiles.append({
                    "trust_key": list(key), "task_type": name,
                    "consequence": policy.task_types[name].consequence if name in policy.task_types else None,
                    "error_bar": error_bar, "autonomy_setting": setting, "implied_autonomy": implied,
                    "trust_score": round(score, 6),
                    # EA-1.15: a low score mostly means "not enough evidence yet" until the clean floor is reached
                    "thin_evidence": judged < (promotion_table(error_bar)[0] if error_bar > 0 else math.inf),
                    "estimated_error_rate": round(mean, 6),
                    "error_rate_interval": [round(low, 6), round(high, 6)],
                    "effective_evidence": round(judged, 4), "evidence_by_source": by_source,
                    "human_evidence_share": round(human_share, 4) if human_share is not None else None,
                    "freshness": {"agent_version": state.agent_version, "last_evidence_at": state.last_evidence_at},
                    "trend": self._trend(state, policy), "actions": volume.get(key, 0), "alerts": alerts,
                    # EA-2.22: what the Advanced dial would set (decisions still follow the ladder)
                    "dial": None if capped else {
                        "pre_review": implied != "trusted_or_above",
                        "spot_check_rate": None if implied != "trusted_or_above"
                        else round(dial_spot_rate(score, policy.dial_gain, policy.dial_floor), 4)}})
            total = sum(profile["actions"] for profile in profiles)
            share: dict = {}
            for profile in profiles:
                share[profile["autonomy_setting"]] = share.get(profile["autonomy_setting"], 0) + profile["actions"]
            now = self.clock()
            incidents = [incident for incident in self._reducer.incidents
                         if incident["key"][0] == organisation_id and incident["key"][1] == agent_id
                         and (task_type is None or incident["key"][2] == task_type)]
            recent_incidents = [incident for incident in incidents
                                if now - parse_timestamp(incident["timestamp"]) <= timedelta(days=30)]
            trends: dict = {}
            for profile in profiles:
                trends[profile["trend"]] = trends.get(profile["trend"], 0) + 1
            summary = {"task_types": len(profiles), "actions": total,
                       "share_of_actions_by_setting": {setting: round(count / total, 4) for setting, count in sorted(share.items())} if total else {},
                       "incidents": len(incidents), "incidents_last_30_days": len(recent_incidents), "trends": trends}
            return {"organisation_id": organisation_id, "agent_id": agent_id, "generated_at": self._now(),
                    "policy_version": policy.policy_version, "profiles": profiles, "summary": summary}

    # ---- RETIRE (EA-5.4 to EA-5.6) ------------------------------------------------------------------------
    def retire(self, actor: Actor, organisation_id: str, agent_id: str, task_type: str, reason: str | None = None) -> bool:
        """Stop an agent doing a task type: every new action is held (why = retired). The record keeps everything."""
        with self._lock:
            if not self.governance.request(actor, "retire", agent_id, {"organisation_id": organisation_id, "task_type": task_type}):
                return False
            self._emit("retire", {"organisation_id": organisation_id, "agent_id": agent_id, "task_type": task_type,
                                  "reason_hash": payload_hash(reason) if reason else None})
            return True

    def reactivate(self, actor: Actor, organisation_id: str, agent_id: str, task_type: str) -> bool:
        """Bring a retired task type back: it starts from Supervised with its old evidence discounted (EA-5.6)."""
        with self._lock:
            if not self.governance.request(actor, "reactivate", agent_id, {"organisation_id": organisation_id, "task_type": task_type}):
                return False
            self._emit("reactivate", {"organisation_id": organisation_id, "agent_id": agent_id, "task_type": task_type})
            return True

    def _explain_state(self, state, error_bar, upper, policy) -> str:
        if policy.is_capped(state.trust_key[2]):
            return "Capped task type: always held for a person."
        if state.level >= L3:
            return f"Senior: worst-case error {upper:.1%} ≤ bar {error_bar:.0%}."
        need = max(0, int(policy.min_judged - state.since_change))
        return (f"{LEVEL_NAMES[state.level]}: {state.judged_count:.0f} judged, {state.serious_error_count:.0f} serious; worst-case error {upper:.1%} vs bar "
                f"{error_bar:.0%}. Promotion needs the worst case under the bar and at least {need} more judged actions.")

    def explain(self, action_id: str) -> dict:
        """Every decision for the action with its evidence snapshot, the outcomes, and the policy it ran under."""
        decisions, outcomes, executed = [], [], None
        for entry in self.record.entries():
            if entry.body.get("action_id") != action_id:
                continue
            if entry.type == "decision":
                decisions.append(entry.body)
            elif entry.type in ("outcome", "incident"):
                outcomes.append({"type": entry.type, **entry.body})
            elif entry.type == "executed":
                executed = entry.body
        policy_version = decisions[-1]["policy_version"] if decisions else None
        return {"action_id": action_id, "decisions": decisions, "outcomes": outcomes, "executed": executed,
                "policy_version": policy_version, "policy": self._reducer.policies.get(policy_version)}

    # ---- integrity (EA-6.9) -------------------------------------------------------------------------------
    def rebuild_state(self) -> dict:
        """Replay the record from empty and return the derived state."""
        reducer = _Reducer(self.bounds)
        for entry in self.record.entries():
            reducer.apply(entry)
        return self._dump(reducer)

    def live_state(self) -> dict:
        return self._dump(self._reducer)

    @staticmethod
    def _dump(reducer: _Reducer) -> dict:
        return {"policy": reducer.policy.to_dict() if reducer.policy else None,
                "states": {"|".join(key): state.snapshot() for key, state in sorted(reducer.states.items())},
                "reviewers": {"|".join(key): state.snapshot() for key, state in sorted(reducer.reviewers.items())},
                "paused": sorted(map(str, reducer.paused)),
                "retired": sorted(map(str, reducer.retired)),
                "queue": copy.deepcopy(reducer.queue)}

    def level_changes(self) -> list[dict]:
        return list(self._reducer.level_changes)
