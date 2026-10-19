"""v3 engine: the v2 engine plus the three fixes confirmed in PREREG-v3.md, each behind its own switch.

Logic is moved unchanged from analyze_v2_explore.py:
- carry_no_prev: on a version change, keep evidence if hidden pass >= carry_min (no ">= previous version" clause)
- reentry_gap:   when a task type is acted on after a gap > reentry_gap days, step down one level (no fading)
- rev_clean:     reviewer trust where a clean second check counts as clean evidence
Also adds a decision ledger (one explanation row per auto-executed action) for G2.
"""
from __future__ import annotations

from dataclasses import dataclass

from gym.engine import wilson_upper
from gym.engine_v2 import ConfigV2, EngineV2

POLICY_VERSION = "v3-2026-10-16"


@dataclass
class ConfigV3(ConfigV2):
    carry_no_prev: bool = False
    reentry_gap: float | None = None
    rev_clean: bool = False


class EngineV3(EngineV2):
    def __init__(self, cfg: ConfigV3, **kw):
        super().__init__(cfg, **kw)
        self.ledger: list[dict] = []
        self._snap = None

    # carry-over without ">= previous"
    def st(self, a):
        k = (a.agent, a.task_type)
        cfg = self.cfg
        if cfg.carry_no_prev and cfg.version_mode == "carry" and k in self.state and self.state[k].version != a.version:
            s = self.state[k]
            hp = cfg.version_pass.get((a.agent, a.version, a.task_type))
            if hp is not None and hp >= cfg.carry_min:
                s.version = a.version
                s.last_hidden = hp
        k, s = super().st(a)
        cons = a.meta["cons"]
        self._snap = dict(key=k, level=s.level, n=round(s.n, 2), err=round(s.err, 2),
                          upper=round(wilson_upper(s.err, s.n), 4), eps=self.eps(cons), cons=cons,
                          version=a.version)
        return k, s

    # re-entry step-down instead of fading
    def _fade(self, k, s, day, cons):
        if self.cfg.reentry_gap is None:
            return super()._fade(k, s, day, cons)
        if day is None:
            return
        if s.last_day is not None and day - s.last_day > self.cfg.reentry_gap and s.level >= 2:
            self._set(k, s, s.level - 1, "reentry_gap")
        s.last_day = day

    # reviewer trust: clean second checks count as clean evidence
    def _review(self, a, cons, executed):
        if self.pool is None or not (self.cfg.reviewer_trust and self.cfg.rev_clean):
            return super()._review(a, cons, executed)
        progress = self.t / self.n_total
        r = self.rng.choice(self.pool)
        r.reviews += 1
        self.m["minutes"] += 1
        if r.st.level >= 2 and r.catch_p(progress) < 0.80:
            r.bad_reviews_at_r2 += 1
        caught = a.true_err and self.rng.random() < r.catch_p(progress)
        if self.rng.random() < self.cfg.canary_rate:
            self.m["canary"] += 1
            self.m["minutes"] += 1
            self._rev_observe(r, not (self.rng.random() < r.catch_p(progress)))
        if not caught and self.rng.random() < self.cfg.second_check[min(2, r.st.level)]:
            others = [x for x in self.pool if x is not r]
            r2 = self.rng.choice([x for x in others if x.st.level >= 2] or others)
            self.m["second"] += 1
            self.m["minutes"] += 1
            found = a.true_err and self.rng.random() < r2.catch_p(progress)
            if found:
                caught = True
            self._rev_observe(r, found)
        a.meta["_reviewer"] = r
        saw_fail = caught or (a.meta.get("nsf", False) and self.rng.random() < 0.95)
        return caught, saw_fail

    def _rev_observe(self, r, miss):
        super()._rev_observe(r, miss)
        if r.st.level >= 2:
            r.ever_r2 = True

    def step(self, a):
        mode = super().step(a)
        if mode == "auto":
            snap = dict(self._snap or {})
            snap.update(t=self.t, agent=a.agent, task_type=a.task_type,
                        checks="pass" if not a.check_flag else None, policy_version=POLICY_VERSION)
            self.ledger.append(snap)
        return mode


def ledger_complete(e: EngineV3) -> float:
    need = ("t", "agent", "task_type", "key", "level", "n", "err", "upper", "eps", "cons", "version", "checks",
            "policy_version")
    if not e.ledger:
        return 1.0
    ok = sum(all(r.get(f) is not None for f in need) and r["level"] >= 2 and r["cons"] != "C4" for r in e.ledger)
    return ok / len(e.ledger)


def run_v3(actions, cfg: ConfigV3, seed=0, **kw) -> EngineV3:
    e = EngineV3(cfg, seed=seed, n_total=len(actions), **kw)
    for a in actions:
        e.step(a)
    return e
