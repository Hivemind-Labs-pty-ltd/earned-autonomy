"""Round "dial" (PREREG-dial.md): discrete ladder vs oversight in proportion to uncertainty.

    python -m dial.run   (from research/)  -> report/raw/dial-runs.json
"""
from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from scipy.stats import beta

from analyze_v2 import rev, t2_actions
from core.policy_core import ERROR_BARS, STEP_DOWN, EngineCore, core_config
from core.run import deserved, regression_latencies, run_one
from gym.engine_v2 import CONS
from t1.world_v2 import world

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "report/raw"
T1_SEEDS = range(150_000, 150_200)
T2_SEEDS = range(600, 620)
THRESHOLD, K, FLOOR = 0.95, 5.0, 0.02


def score(errors, judged, bar):
    return float(beta.cdf(bar, 1 + errors, 1 + judged - errors))


class DialEngine(EngineCore):
    """Levels 1 (held) and 2 (acting). Promote on score >= 0.95; spot-check rate from the score."""

    def __init__(self, cfg, **kw):
        super().__init__(cfg, **kw)
        self.spot_rates = []

    def observe(self, key, state, consequence, error, failure):
        state.n += 1
        state.err += error
        state.fail += failure
        state.since += 1
        state.recent.append(error)
        if consequence not in ERROR_BARS:
            return
        if state.level >= 2 and sum(state.recent) >= STEP_DOWN[consequence]:
            self._set(key, state, 1, "step_down_table")
            return
        if state.level == 1 and state.since >= self.cfg.n_min and \
                score(state.err, state.n, ERROR_BARS[consequence]) >= THRESHOLD:
            self._set(key, state, 2, "score")

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
        hold = a.check_flag or cons == "C4" or cons not in ERROR_BARS or s.level <= 1
        if hold:
            m["pre"] += 1
            bc["reviews"] += 1
            if cfg.canary_rate and self.rng.random() < cfg.canary_rate:
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
        rate = min(1.0, max(FLOOR, K * (1 - score(s.err, s.n, ERROR_BARS[cons])) + FLOOR))
        self.spot_rates.append(rate)
        if self.rng.random() < rate:
            m["spot"] += 1
            bc["reviews"] += 1
            caught, saw_fail = self._review(a, cons, executed=True)
            self.observe(k, s, cons, caught, saw_fail)
        return "auto"


def arms():
    return {"ladder": (EngineCore, core_config(canaries=True)), "dial": (DialEngine, core_config(canaries=True))}


def summarise(engine, row, rates_or_seq, cons_of, keys=None):
    row["deserved"] = deserved(engine, rates_or_seq, lambda k: CONS[cons_of[k]]["eps"])
    if keys is not None:
        row["latencies"] = regression_latencies(engine, keys)
    row["mean_spot_rate"] = (sum(engine.spot_rates) / len(engine.spot_rates)) if getattr(engine, "spot_rates", None) \
        else None
    return row


def t1_seed(seed):
    actions, keys = world(seed)
    cons_of = {}
    for a in actions:
        cons_of.setdefault((a.agent, a.task_type), a.meta["cons"])
    rates = {k: info["rates"] for k, info in keys.items()}
    out = {}
    for name, (cls, cfg) in arms().items():
        engine, row = run_one(cls, cfg, actions, seed)
        out[name] = summarise(engine, row, rates, cons_of, keys)
    return out


def t2_stream(name):
    actions = t2_actions(name)
    seqs, cons_of = {}, {}
    for a in actions:
        seqs.setdefault((a.agent, a.task_type), []).append(int(a.true_err))
        cons_of.setdefault((a.agent, a.task_type), a.meta["cons"])
    rows = []
    for seed in T2_SEEDS:
        out = {}
        for arm, (cls, cfg) in arms().items():
            engine, row = run_one(cls, cfg, actions, seed)
            out[arm] = summarise(engine, row, seqs, cons_of)
        rows.append(out)
    return name, rows


def main():
    with ProcessPoolExecutor() as pool:
        t1 = list(pool.map(t1_seed, T1_SEEDS, chunksize=4))
        t2 = dict(pool.map(t2_stream, ("good-full", "sloppy-full")))
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "dial-runs.json").write_text(json.dumps(dict(t1=t1, t2=t2)))
    print("saved")


if __name__ == "__main__":
    main()
