"""EXPLORATORY (post-hoc, 2026-10-21; not pre-registered): ramp-up minutes counted only until a key's FIRST promotion,
for keys that promote in the live baseline. The pre-registered "ramp-up minutes" also counts keys that never promote in
any arm, which dominates the total.     python -m calibration.explore
"""
from __future__ import annotations

import json
import statistics as st
from concurrent.futures import ProcessPoolExecutor

from analyze_v2 import rev
from calibration.run import RAW, T1_SEEDS, RampCore
from core.policy_core import ERROR_BARS, core_config
from t1.world_v2 import world


class FirstRamp(RampCore):
    def __init__(self, cfg, **kw):
        super().__init__(cfg, **kw)
        self.first = {}
        self.promoted = set()

    def _set(self, key, state, level, why):
        if level >= 2:
            self.promoted.add(key)
        super()._set(key, state, level, why)

    def step(self, action):
        key = (action.agent, action.task_type)
        before = self.m["minutes"]
        mode = super().step(action)
        if key not in self.promoted or (key in self.promoted and key not in self.first):
            self.first[key] = self.first.get(key, 0.0) + self.m["minutes"] - before
        return mode


def seed_run(args):
    seed, weights = args
    actions, keys = world(seed)
    cons_of = {}
    for a in actions:
        cons_of.setdefault((a.agent, a.task_type), a.meta["cons"])
    engines = {}
    for arm in ("L", "SH", "RP"):
        e = FirstRamp(core_config(canaries=True), arm=arm, weight=weights.get(arm, 1.0), seed=seed * 17 + 3,
                      n_total=len(actions), reviewer=rev(seed))
        for a in actions:
            e.step(a)
        engines[arm] = e
    promote_keys = [k for k in engines["L"].promoted if cons_of.get(k) in ERROR_BARS]
    return {arm: sum(e.first.get(k, 0.0) for k in promote_keys) for arm, e in engines.items()}


def main():
    weights = json.load(open(RAW / "calibration-runs.json"))["weights"]
    with ProcessPoolExecutor() as pool:
        rows = list(pool.map(seed_run, [(s, weights) for s in T1_SEEDS], chunksize=4))
    out = {arm: st.fmean(r[arm] for r in rows) for arm in ("L", "SH", "RP")}
    out["RP_cut_vs_L"] = 1 - out["RP"] / out["L"]
    out["SH_cut_vs_L"] = 1 - out["SH"] / out["L"]
    (RAW / "calibration-explore.json").write_text(json.dumps(out, indent=1))
    print(out)


if __name__ == "__main__":
    main()


def by_pattern_seed(args):
    """EXPLORATORY: first-promotion ramp minutes by T1 pattern, live (L) vs replay pre-load (RP)."""
    seed, weights = args
    actions, keys = world(seed)
    cons_of = {}
    for a in actions:
        cons_of.setdefault((a.agent, a.task_type), a.meta["cons"])
    engines = {}
    for arm in ("L", "RP"):
        e = FirstRamp(core_config(canaries=True), arm=arm, weight=weights.get(arm, 1.0), seed=seed * 17 + 3,
                      n_total=len(actions), reviewer=rev(seed))
        for a in actions:
            e.step(a)
        engines[arm] = e
    out = {}
    for k in engines["L"].promoted:
        if cons_of.get(k) not in ERROR_BARS:
            continue
        row = out.setdefault(keys[k]["pattern"], [0.0, 0.0, 0])
        row[0] += engines["L"].first.get(k, 0.0)
        row[1] += engines["RP"].first.get(k, 0.0)
        row[2] += 1
    return out


def by_pattern():
    weights = json.load(open(RAW / "calibration-runs.json"))["weights"]
    with ProcessPoolExecutor() as pool:
        rows = list(pool.map(by_pattern_seed, [(s, weights) for s in T1_SEEDS], chunksize=4))
    total = {}
    for r in rows:
        for p, (l, rp, n) in r.items():
            t = total.setdefault(p, [0.0, 0.0, 0])
            t[0] += l
            t[1] += rp
            t[2] += n
    res = {p: dict(L=v[0] / v[2], RP=v[1] / v[2], keys=v[2], cut=1 - v[1] / v[0]) for p, v in total.items()}
    (RAW / "calibration-explore-by-pattern.json").write_text(json.dumps(res, indent=1))
    print({p: {k: round(x, 3) if isinstance(x, float) else x for k, x in d.items()} for p, d in res.items()})
