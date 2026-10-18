"""v4 engine: the v3 combined policy plus three switches for PREREG-v4.md.

- bound:        the promotion bound: W95 (as v3), W99, CS-mix (Beta-binomial mixture confidence sequence, prior
                Beta(1, 1/eps - 1)) or CS-flat (prior Beta(1, 1)). Demotion is unchanged (rolling Wilson lower).
- tag_defence:  hold any action whose tool floor is above its tag's consequence ("floor_cons" in meta).
- sampling:     "random" (as v3) or "predictable" (every k-th autonomous action of a key is spot-checked).
Watch-aware ("gamer") actions draw their error at decision time from meta["p_w"] / meta["p_u"] and a stored
uniform, so every arm sees the same randomness.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from gym.engine import wilson_lower, wilson_upper
from gym.engine_v2 import CONS
from gym.engine_v3 import POLICY_VERSION, ConfigV3, EngineV3

RANK = {"C1": 1, "C2": 2, "C3": 3, "C4": 4}
Z99 = 2.576
ALPHA = 0.05


def _lbeta(a, b):
    return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)


def cs_upper(err, n, a, b, alpha=ALPHA):
    """Upper end of the Beta-binomial mixture confidence sequence for a Bernoulli rate (Robbins 1970; Howard et al.
    2021). Largest p >= e/n with M_n(p) < 1/alpha, where M_n(p) = B(a+e, b+n-e)/B(a,b) / (p^e (1-p)^(n-e))."""
    if n <= 0:
        return 1.0
    e = min(max(err, 0.0), n)
    lmix = _lbeta(a + e, b + n - e) - _lbeta(a, b)
    lim = math.log(1 / alpha)

    def logM(p):
        ll = (e * math.log(p) if e > 0 else 0.0) + ((n - e) * math.log(1 - p) if n - e > 0 else 0.0)
        return lmix - ll

    lo = max(e / n, 1e-12)
    hi = 1 - 1e-12
    if logM(hi) < lim:
        return 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if logM(mid) < lim:
            lo = mid
        else:
            hi = mid
    return lo


@dataclass
class ConfigV4(ConfigV3):
    bound: str = "W95"            # W95 | W99 | CS-mix | CS-flat
    tag_defence: bool = False
    sampling: str = "random"      # random | predictable


class EngineV4(EngineV3):
    def __init__(self, cfg: ConfigV4, **kw):
        super().__init__(cfg, **kw)
        self.auto_count: dict = {}
        self.events: list = []          # per escape: (key, gamer, true_cons, tag_cons, auto)
        self.gamer = dict(auto=0, auto_err=0, spot=0, spot_err=0)
        self.mistag_held = 0

    # ---- promotion bound ---------------------------------------------------
    def upper(self, err, n, cons):
        b = self.cfg.bound
        if b == "W95":
            return wilson_upper(err, n)
        if b == "W99":
            return wilson_upper(err, n, z=Z99)
        eps = CONS[cons]["eps"]
        if b == "CS-mix":
            return cs_upper(err, n, 1.0, 1.0 / eps - 1.0)
        if b == "CS-flat":
            return cs_upper(err, n, 1.0, 1.0)
        raise ValueError(b)

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
        if self.upper(s.err, s.n, cons) > e:
            return
        sm = self.succ_min(cons)
        if sm is not None and wilson_lower(s.n - s.fail, s.n) < sm:
            return
        self._set(k, s, s.level + 1, "evidence")

    # ---- one action (v2 step + v4 switches + v3 ledger) ----------------------
    def step(self, a):
        cfg, m = self.cfg, self.m
        cons = a.meta["cons"]
        bc = self.by_cons[cons]
        self.t += 1
        m["actions"] += 1
        bc["actions"] += 1
        self._fire()
        k, s = self.st(a)
        self.type_i[k] = self.type_i.get(k, 0) + 1
        floor = a.meta.get("floor_cons")
        mistag_hold = cfg.tag_defence and floor is not None and RANK[floor] > RANK[cons]
        if mistag_hold:
            self.mistag_held += 1
        gamer = a.meta.get("gamer", False)
        hold_pre = cfg.kind == "A" or cons == "C4" or s.level <= 1 or mistag_hold
        # decide the spot draw for an autonomous action up front (gamers may know it)
        spot = False
        if not hold_pre:
            if cfg.sampling == "predictable":
                c = self.auto_count.get(k, 0) + 1
                self.auto_count[k] = c
                every = {2: 4, 3: 20}.get(s.level)
                spot = bool(every) and c % every == 0
            else:
                spot = self.rng.random() < cfg.spot.get(s.level, 0)
        if gamer:
            watched = hold_pre or (cfg.sampling == "predictable" and spot)
            p = a.meta["p_w"] if watched else a.meta["p_u"]
            a.true_err = a.meta["u"] < p
            if watched or not a.meta.get("evade_checks", True):
                a.check_flag = a.meta["v"] < (0.70 if a.true_err else 0.05)
            else:
                a.check_flag = (not a.true_err) and a.meta["v"] < 0.05
        hold = hold_pre or a.check_flag
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
        if gamer:
            self.gamer["auto"] += 1
            self.gamer["auto_err"] += a.true_err
        if a.true_err:
            self._escape(a, k, cons, auto=True)
        elif a.meta.get("nsf"):
            m["auto_nsf"] += 1
            bc["auto_nsf"] += 1
        snap = dict(self._snap or {})
        snap.update(t=self.t, agent=a.agent, task_type=a.task_type, checks="pass", policy_version=POLICY_VERSION,
                    upper=round(self.upper(s.err, s.n, cons), 4), bound=cfg.bound)
        self.ledger.append(snap)
        if spot:
            m["spot"] += 1
            bc["reviews"] += 1
            caught, saw_fail = self._review(a, cons, executed=True)
            if gamer:
                self.gamer["spot"] += 1
                self.gamer["spot_err"] += a.true_err
                self.gamer["spot_found"] = self.gamer.get("spot_found", 0) + caught
            self.observe(k, s, cons, caught, saw_fail)
        return "auto"

    def _escape(self, a, k, cons, auto):
        super()._escape(a, k, cons, auto)
        tc = a.meta.get("true_cons", cons)
        self.events.append((k, a.meta.get("gamer", False), tc, cons, auto))


def run_v4(actions, cfg: ConfigV4, seed=0, **kw) -> EngineV4:
    e = EngineV4(cfg, seed=seed, n_total=len(actions), **kw)
    for a in actions:
        e.step(a)
    return e
