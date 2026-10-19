"""v2 engine: the recommended v1 policy plus the 2026-10-16 decisions (PREREG-v2.md).

Self-contained so v0 (engine.py) and v1 (engine_v1.py) stay reproducible.

Adds, per task type:
- consequence bars (C1-C4: epsilon + minimum task success; C4 never promotes) or a flat bar
- a task-success dimension (non-serious failures), with an optional success criterion for promotion
- cost-weighted escapes and per-consequence metrics
- evidence fading by calendar time (half-life), with a stale-evidence step-down
- version carry-over keyed per (agent, version, task type) with carry / discount / keep modes
- an optional pool of human reviewers who earn trust themselves (SPEC section 9)
"""
from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field

from gym.engine import Action, Reviewer, wilson_lower, wilson_upper

CONS = {
    "C1": dict(eps=0.10, succ=0.85, cost=1),
    "C2": dict(eps=0.05, succ=0.90, cost=3),
    "C3": dict(eps=0.02, succ=0.95, cost=10),
    "C4": dict(eps=0.0, succ=None, cost=30),
}
OBS_FAIL_P = 0.95        # reviewer sees a non-serious failure


@dataclass
class ConfigV2:
    kind: str = "D"                  # A | D
    bars: str = "consequence"        # consequence | flat
    flat_eps: float = 0.05
    success_criterion: bool = True
    n_min: int = 30
    spot: dict = field(default_factory=lambda: {2: 0.25, 3: 0.05})
    canary_rate: float = 0.02
    rolling_n: int = 50
    version_mode: str = "carry"      # carry | discount | keep
    version_w: float = 0.5
    carry_min: float = 0.8
    version_pass: dict = field(default_factory=dict)   # (agent, version, task_type) -> hidden pass rate
    half_life: float | None = None   # days; None = no fading
    reviewer_trust: bool = False
    eps_rev: float = 0.10
    second_check: dict = field(default_factory=lambda: {1: 0.25, 2: 0.05})


class State:
    def __init__(self):
        self.level = 1
        self.n = 0.0
        self.err = 0.0
        self.fail = 0.0
        self.since = 0.0
        self.recent: deque = deque(maxlen=50)
        self.version = None
        self.last_day = None
        self.last_hidden = None


class PoolReviewer:
    """A human reviewer with a fixed catch probability that may change over the world (no complacency)."""

    def __init__(self, name, catch_fn, rng):
        self.name, self.catch_fn, self.rng = name, catch_fn, rng
        self.st = State()
        self.reviews = 0
        self.bad_reviews_at_r2 = 0

    def catch_p(self, progress):
        return self.catch_fn(progress)


class EngineV2:
    def __init__(self, cfg: ConfigV2, seed=0, reviewer: Reviewer | None = None, pool: list | None = None,
                 n_total: int | None = None, incident_p=0.3, incident_delay=(1, 20)):
        self.cfg = cfg
        self.rng = random.Random(seed)
        self.reviewer = reviewer or Reviewer(random.Random(seed + 7919))
        self.pool = pool
        self.n_total = n_total or 1
        self.state: dict = {}
        self.t = 0
        self.pending: list = []
        self.incident_p, self.incident_delay = incident_p, incident_delay
        self.m = dict(actions=0, auto=0, pre=0, spot=0, canary=0, second=0, escapes=0, escapes_auto=0,
                      cost=0.0, auto_nsf=0, blocked=0, minutes=0.0)
        self.by_cons = {c: dict(actions=0, reviews=0, auto=0, escapes_auto=0, escapes=0, cost=0.0, auto_nsf=0)
                        for c in CONS}
        self.by_key_escapes: dict = {}
        self.promotions: list = []
        self.demotions: list = []
        self.type_i: dict = {}

    # ---- bars --------------------------------------------------------------
    def eps(self, cons):
        if cons == "C4":
            return 0.0
        return CONS[cons]["eps"] if self.cfg.bars == "consequence" else self.cfg.flat_eps

    def succ_min(self, cons):
        if self.cfg.bars != "consequence" or not self.cfg.success_criterion:
            return None
        return CONS[cons]["succ"]

    # ---- state -------------------------------------------------------------
    def _set(self, k, s, lvl, why):
        old = s.level
        s.level, s.since = lvl, 0.0
        s.recent.clear()
        rec = dict(t=self.t, key=k, frm=old, to=lvl, why=why, type_i=self.type_i.get(k, 0))
        (self.promotions if lvl > old else self.demotions).append(rec)

    def _fade(self, k, s, day, cons):
        hl = self.cfg.half_life
        if hl is None or day is None:
            return
        if s.last_day is not None and day > s.last_day:
            f = 0.5 ** ((day - s.last_day) / hl)
            s.n *= f
            s.err *= f
            s.fail *= f
        s.last_day = day
        if s.level >= 2 and wilson_upper(s.err, s.n) > self.eps(cons):
            self._set(k, s, s.level - 1, "stale")

    def st(self, a: Action):
        k = (a.agent, a.task_type)
        cons = a.meta["cons"]
        if k not in self.state:
            self.state[k] = State()
            self.state[k].version = a.version
            self.state[k].last_day = a.meta.get("day")
        s = self.state[k]
        if s.version != a.version:
            hp = self.cfg.version_pass.get((a.agent, a.version, a.task_type))
            mode = self.cfg.version_mode
            if mode == "keep":
                keep = True
            elif mode == "discount":
                keep = False
            else:
                keep = hp is not None and hp >= self.cfg.carry_min and (s.last_hidden is None or hp >= s.last_hidden)
            if not keep:
                s.n *= self.cfg.version_w
                s.err *= self.cfg.version_w
                s.fail *= self.cfg.version_w
                if s.level >= 2 and wilson_upper(s.err, s.n) > self.eps(cons):
                    self._set(k, s, 1, "version_change")
            s.version = a.version
            if hp is not None:
                s.last_hidden = hp
        self._fade(k, s, a.meta.get("day"), cons)
        return k, s

    def observe(self, k, s, cons, err, fail):
        s.n += 1
        s.err += err
        s.fail += fail
        s.since += 1
        s.recent.append(err)
        e = self.eps(cons)
        if s.level >= 2 and len(s.recent) >= 10 and wilson_lower(sum(s.recent), len(s.recent)) > e:
            self._set(k, s, s.level - 1, "rolling_bound")
            return
        if cons == "C4" or e <= 0 or s.level >= 3 or s.since < self.cfg.n_min:
            return
        if wilson_upper(s.err, s.n) > e:
            return
        sm = self.succ_min(cons)
        if sm is not None and wilson_lower(s.n - s.fail, s.n) < sm:
            return
        self._set(k, s, s.level + 1, "evidence")

    # ---- reviewing ---------------------------------------------------------
    def _review(self, a: Action, cons, executed: bool):
        """Judge one action. Returns (caught_serious, saw_fail). executed=True for spot-checks."""
        progress = self.t / self.n_total
        if self.pool is None:
            self.m["minutes"] += 1
            caught = self.reviewer.review(a.true_err)
        else:
            r = self.rng.choice(self.pool)
            r.reviews += 1
            self.m["minutes"] += 1
            if r.st.level >= 2 and r.catch_p(progress) < 0.80:
                r.bad_reviews_at_r2 += 1
            caught = a.true_err and self.rng.random() < r.catch_p(progress)
            if self.cfg.reviewer_trust:
                # canary for this reviewer
                if self.rng.random() < self.cfg.canary_rate:
                    self.m["canary"] += 1
                    self.m["minutes"] += 1
                    hit = self.rng.random() < r.catch_p(progress)
                    self._rev_observe(r, not hit)
                # second check on approvals
                if not caught and self.rng.random() < self.cfg.second_check[min(2, r.st.level)]:
                    others = [x for x in self.pool if x is not r]
                    trusted = [x for x in others if x.st.level >= 2] or others
                    r2 = self.rng.choice(trusted)
                    self.m["second"] += 1
                    self.m["minutes"] += 1
                    if a.true_err and self.rng.random() < r2.catch_p(progress):
                        caught = True          # blocked (pre) or found (spot)
                        self._rev_observe(r, True)
            a.meta["_reviewer"] = r
        saw_fail = caught or (a.meta.get("nsf", False) and self.rng.random() < OBS_FAIL_P)
        return caught, saw_fail

    def _rev_observe(self, r: PoolReviewer, miss: bool):
        s = r.st
        s.n += 1
        s.err += miss
        s.since += 1
        s.recent.append(miss)
        e = self.cfg.eps_rev
        if s.level >= 2 and len(s.recent) >= 10 and wilson_lower(sum(s.recent), len(s.recent)) > e:
            s.level, s.since = 1, 0.0
            s.recent.clear()
            return
        if s.level < 2 and s.since >= self.cfg.n_min and wilson_upper(s.err, s.n) <= e:
            s.level, s.since = 2, 0.0
            s.recent.clear()

    # ---- one action --------------------------------------------------------
    def step(self, a: Action) -> str:
        cfg, m = self.cfg, self.m
        cons = a.meta["cons"]
        bc = self.by_cons[cons]
        self.t += 1
        m["actions"] += 1
        bc["actions"] += 1
        self._fire()
        k, s = self.st(a)
        self.type_i[k] = self.type_i.get(k, 0) + 1
        hold = cfg.kind == "A" or a.check_flag or cons == "C4" or s.level <= 1
        if hold:
            m["pre"] += 1
            bc["reviews"] += 1
            if self.pool is None and cfg.canary_rate and self.rng.random() < cfg.canary_rate:
                m["canary"] += 1
                m["minutes"] += 1
                bc["reviews"] += 1
                self.reviewer.canary()
            caught, saw_fail = self._review(a, cons, executed=False)
            if caught:
                m["blocked"] += 1
            elif a.true_err:
                self._escape(a, k, cons, auto=False)
            self.observe(k, s, cons, caught, saw_fail)
            return "review"
        m["auto"] += 1
        bc["auto"] += 1
        if a.true_err:
            self._escape(a, k, cons, auto=True)
        elif a.meta.get("nsf"):
            m["auto_nsf"] += 1
            bc["auto_nsf"] += 1
        if self.rng.random() < cfg.spot.get(s.level, 0):
            m["spot"] += 1
            bc["reviews"] += 1
            caught, saw_fail = self._review(a, cons, executed=True)
            self.observe(k, s, cons, caught, saw_fail)
        return "auto"

    def _escape(self, a, k, cons, auto):
        m, bc = self.m, self.by_cons[cons]
        m["escapes"] += 1
        bc["escapes"] += 1
        c = CONS[cons]["cost"]
        m["cost"] += c
        bc["cost"] += c
        if auto:
            m["escapes_auto"] += 1
            bc["escapes_auto"] += 1
        self.by_key_escapes[k] = self.by_key_escapes.get(k, 0) + 1
        if self.rng.random() < self.incident_p:
            r = a.meta.get("_reviewer") if not auto else None
            self.pending.append((self.t + self.rng.randint(*self.incident_delay), k, cons, r))

    def _fire(self):
        due = [p for p in self.pending if p[0] <= self.t]
        if not due:
            return
        self.pending = [p for p in self.pending if p[0] > self.t]
        for _, k, cons, r in due:
            s = self.state.get(k)
            if s is None:
                continue
            s.n += 1
            s.err += 1
            if s.level >= 2:
                self._set(k, s, s.level - 1, "incident")
            if r is not None and self.cfg.reviewer_trust:
                self._rev_observe(r, True)

    def summary(self):
        m = dict(self.m)
        n = max(1, m["actions"])
        m["automation"] = m["auto"] / n
        m["reviews"] = m["pre"] + m["spot"] + m["canary"] + m["second"]
        m["esc_per100"] = 100 * m["escapes"] / n
        m["esc_per100_auto"] = 100 * m["escapes_auto"] / max(1, m["auto"])
        m["cost_per100"] = 100 * m["cost"] / n
        m["by_cons"] = self.by_cons
        return m


def run_v2(actions, cfg: ConfigV2, seed=0, **kw) -> EngineV2:
    e = EngineV2(cfg, seed=seed, n_total=len(actions), **kw)
    for a in actions:
        e.step(a)
    return e
