"""Trust engine: policies, trust state, ledger, simulated reviewer.

One engine serves every tier. A tier supplies a stream of actions; each action says
which agent did which task type, whether it was truly a serious error (hidden from
the policy), and whether the checks flagged it. The engine decides hold / auto /
spot-check, simulates the reviewer, and records everything in the ledger.

Policies only ever see observed evidence: reviewer verdicts (which can miss errors),
spot-check verdicts and incidents. Never `true_err`.
"""
from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass, field

POLICY_VERSION = "v0-2026-10-15"


def wilson_upper(err: float, n: float, z: float = 1.96) -> float:
    if n <= 0:
        return 1.0
    p = err / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    a = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return min(1.0, (c + a) / d)


def wilson_lower(err: float, n: float, z: float = 1.96) -> float:
    if n <= 0:
        return 0.0
    p = err / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    a = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (c - a) / d)


@dataclass
class Action:
    agent: str
    task_type: str
    true_err: bool
    check_flag: bool
    version: str = "v1"
    capped: bool = False
    counterparty: str = "new"
    meta: dict = field(default_factory=dict)


@dataclass
class PolicyConfig:
    kind: str = "D"              # A | B | Bm | C | D
    granularity: str = "type"    # type | agent
    start_level: int = 1
    n_min: int = 30
    eps: float = 0.05
    spot: dict = field(default_factory=lambda: {2: 0.25, 3: 0.05})
    hard_demotion: bool = True
    rolling_n: int = 50
    version_w: float = 0.5
    hold_p: float = 0.0          # Bm: random hold probability
    canary_rate: float = 0.02    # share of reviews that are canaries (0 disables)


class Reviewer:
    """Simulated human reviewer with a complacency model (an assumption, swept)."""

    def __init__(self, rng: random.Random, p_hi=0.95, p_lo=0.60, ref=0.05, alpha=0.02):
        self.rng, self.p_hi, self.p_lo, self.ref, self.alpha = rng, p_hi, p_lo, ref, alpha
        self.ema = ref  # recently seen error rate
        self.minutes = 0.0
        self.canary_seen = 0
        self.canary_caught = 0
        self.real_err_seen = 0
        self.real_err_caught = 0

    def p_catch(self) -> float:
        return self.p_lo + (self.p_hi - self.p_lo) * min(1.0, self.ema / self.ref)

    def _see(self, was_err: bool):
        self.ema = (1 - self.alpha) * self.ema + self.alpha * (1.0 if was_err else 0.0)

    def review(self, true_err: bool) -> bool:
        """Returns True if the reviewer flags an error."""
        self.minutes += 1.0
        caught = true_err and self.rng.random() < self.p_catch()
        if true_err:
            self.real_err_seen += 1
            self.real_err_caught += caught
        self._see(caught)
        return caught

    def canary(self):
        self.minutes += 1.0
        caught = self.rng.random() < self.p_catch()
        self.canary_seen += 1
        self.canary_caught += caught
        # A caught or missed canary is revealed afterwards, so it always resets attention.
        self._see(True)


class TrustState:
    def __init__(self, level: int):
        self.level = level
        self.n = 0.0
        self.err = 0.0
        self.since_change = 0.0
        self.recent: deque = deque(maxlen=50)
        self.version = None


class Engine:
    def __init__(self, cfg: PolicyConfig, seed: int = 0, reviewer: Reviewer | None = None,
                 incident_p: float = 0.3, incident_delay=(1, 20)):
        self.cfg = cfg
        self.rng = random.Random(seed)
        self.reviewer = reviewer or Reviewer(random.Random(seed + 7919))
        self.state: dict = {}
        self.ledger: list[dict] = []
        self.pending_incidents: list[tuple[int, tuple]] = []
        self.incident_p, self.incident_delay = incident_p, incident_delay
        self.t = 0
        self.m = dict(actions=0, auto=0, pre_reviews=0, spot_reviews=0, canaries=0,
                      escapes=0, escapes_auto=0, incidents=0, errors=0, blocked=0)
        self.promotions: list[dict] = []
        self.demotions: list[dict] = []
        self.type_counts: dict = {}

    # ---- trust state -------------------------------------------------------
    def key(self, a: Action):
        return (a.agent,) if self.cfg.granularity == "agent" else (a.agent, a.task_type)

    def st(self, a: Action) -> TrustState:
        k = self.key(a)
        if k not in self.state:
            self.state[k] = TrustState(self.cfg.start_level)
            self.state[k].version = a.version
        s = self.state[k]
        if s.version != a.version:          # agent changed: new hire with a CV
            s.n *= self.cfg.version_w
            s.err *= self.cfg.version_w
            s.version = a.version
            if s.level >= 2 and wilson_upper(s.err, s.n) > self.cfg.eps:
                self._set_level(k, s, 1, "version_change")
        return s

    def _set_level(self, k, s: TrustState, lvl: int, why: str):
        old = s.level
        s.level = lvl
        s.since_change = 0.0
        s.recent.clear()
        rec = dict(t=self.t, key=k, frm=old, to=lvl, why=why, type_i=self.type_counts.get(k, 0))
        (self.promotions if lvl > old else self.demotions).append(rec)

    def observe(self, k, s: TrustState, err: bool):
        s.n += 1
        s.err += err
        s.since_change += 1
        s.recent.append(err)
        cfg = self.cfg
        # demotion on a confidently bad rolling window
        if s.level >= 2 and len(s.recent) >= 10:
            r_err = sum(s.recent)
            if wilson_lower(r_err, len(s.recent)) > cfg.eps:
                self._set_level(k, s, s.level - 1, "rolling_bound")
                return
        # promotion
        if s.level < 3 and s.since_change >= cfg.n_min and wilson_upper(s.err, s.n) <= cfg.eps:
            self._set_level(k, s, s.level + 1, "evidence")

    def incident(self, k):
        s = self.state.get(k)
        self.m["incidents"] += 1
        if s is None:
            return
        s.n += 1
        s.err += 1
        if s.level >= 2:
            self._set_level(k, s, 1 if self.cfg.hard_demotion else s.level - 1, "incident")

    # ---- one action --------------------------------------------------------
    def step(self, a: Action) -> str:
        cfg, m = self.cfg, self.m
        self.t += 1
        m["actions"] += 1
        m["errors"] += a.true_err
        k_type = (a.agent, a.task_type)
        self.type_counts[k_type] = self.type_counts.get(k_type, 0) + 1
        self._fire_incidents()

        if cfg.kind == "A":
            mode = "review"
        elif cfg.kind == "B":
            mode = "review" if a.check_flag else "auto"
        elif cfg.kind == "Bm":
            mode = "review" if (a.check_flag or self.rng.random() < cfg.hold_p) else "auto"
        else:  # C or D
            s = self.st(a)
            k = self.key(a)
            if self.cfg.granularity == "agent":
                self.type_counts[k] = self.type_counts.get(k, 0) + 1
            flagged = a.check_flag and cfg.kind == "D"
            if a.capped or s.level <= 1 or flagged:
                mode = "review"
            else:
                mode = "auto"

        if mode == "review":
            m["pre_reviews"] += 1
            if cfg.canary_rate and self.rng.random() < cfg.canary_rate:
                m["canaries"] += 1
                self.reviewer.canary()
            caught = self.reviewer.review(a.true_err)
            if caught:
                m["blocked"] += 1
            elif a.true_err:
                m["escapes"] += 1
                self._maybe_incident(a)
            if cfg.kind in ("C", "D"):
                self.observe(self.key(a), self.st(a), caught)
            return "review"

        # auto-execute
        m["auto"] += 1
        if a.true_err:
            m["escapes"] += 1
            m["escapes_auto"] += 1
            self._maybe_incident(a)
        if cfg.kind in ("C", "D"):
            s = self.st(a)
            k = self.key(a)
            self.ledger.append(dict(t=self.t, agent=a.agent, task_type=a.task_type, key=k, level=s.level,
                                    n=round(s.n, 2), err=round(s.err, 2),
                                    upper=round(wilson_upper(s.err, s.n), 4), version=a.version,
                                    checks="pass" if not a.check_flag else "n/a",
                                    policy_version=POLICY_VERSION, eps=cfg.eps))
            if self.rng.random() < cfg.spot.get(s.level, 0):
                m["spot_reviews"] += 1
                caught = self.reviewer.review(a.true_err)
                self.observe(k, s, caught)
        else:
            self.ledger.append(dict(t=self.t, agent=a.agent, task_type=a.task_type, key=None, level=None,
                                    n=None, err=None, upper=None, version=a.version,
                                    checks="pass", policy_version=POLICY_VERSION, eps=None))
        return "auto"

    def _maybe_incident(self, a: Action):
        if self.rng.random() < self.incident_p:
            d = self.rng.randint(*self.incident_delay)
            self.pending_incidents.append((self.t + d, self.key(a) if self.cfg.kind in ("C", "D") else None))

    def _fire_incidents(self):
        due = [p for p in self.pending_incidents if p[0] <= self.t]
        if not due:
            return
        self.pending_incidents = [p for p in self.pending_incidents if p[0] > self.t]
        for _, k in due:
            if k is None:
                self.m["incidents"] += 1
            else:
                self.incident(k)

    # ---- summary -----------------------------------------------------------
    def summary(self) -> dict:
        m = dict(self.m)
        n = max(1, m["actions"])
        m["automation"] = m["auto"] / n
        m["reviews"] = m["pre_reviews"] + m["spot_reviews"] + m["canaries"]
        m["review_minutes"] = self.reviewer.minutes
        m["esc_per100_auto"] = 100 * m["escapes_auto"] / max(1, m["auto"])
        m["esc_per100"] = 100 * m["escapes"] / n
        r = self.reviewer
        m["reviewer_catch"] = r.real_err_caught / r.real_err_seen if r.real_err_seen else None
        return m


def run_stream(actions, cfg: PolicyConfig, seed=0, **kw) -> Engine:
    e = Engine(cfg, seed=seed, **kw)
    for a in actions:
        e.step(a)
    return e


def ledger_complete(engine: Engine) -> float:
    """G2: share of auto-executed actions under C/D whose ledger row explains why it was allowed."""
    need = ("t", "agent", "task_type", "key", "level", "n", "err", "upper", "version", "checks",
            "policy_version", "eps")
    rows = [r for r in engine.ledger if r["key"] is not None]
    if not rows:
        return 1.0
    ok = sum(all(r.get(f) is not None for f in need) and r["level"] >= 2 for r in rows)
    return ok / len(rows)


def no_auto_after_incident(engine: Engine) -> int:
    """G3: count auto-executed actions in a key between an incident demotion to L1 and its next promotion."""
    violations = 0
    for d in engine.demotions:
        if d["why"] != "incident" or d["to"] != 1:
            continue
        nxt = [p["t"] for p in engine.promotions if p["key"] == d["key"] and p["t"] > d["t"]]
        end = min(nxt) if nxt else float("inf")
        violations += sum(1 for r in engine.ledger if r["key"] == d["key"] and d["t"] < r["t"] <= end
                          and not (nxt and r["t"] == end))
    return violations
