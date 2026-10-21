"""Round "calibration" (PREREG-calibration.md): is the trust score calibrated, and what is non-review evidence worth?

    python -m calibration.run   (from research/)  -> report/raw/calibration-runs.json
"""
from __future__ import annotations

import json
import random
import statistics as st
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from scipy.stats import beta

from analyze_v2 import rev, t2_actions
from core.policy_core import ERROR_BARS, EngineCore, core_config
from gym.engine import wilson_upper
from t1.world_v2 import world

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "report/raw"
MANUAL = {"C1": 2.0, "C2": 4.0, "C3": 6.0, "C4": 6.0}
T1_SEEDS = range(140_000, 140_200)
T2_SEEDS = range(500, 520)
WEIGHTS = (0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0)
HUMAN_ERR, SAME_WRONG, ADJUDICATION = 0.03, 0.3, 0.95
N_SOURCE = 100


def score(errors, judged, bar, prior=(1.0, 1.0)):
    return float(beta.cdf(bar, prior[0] + errors, prior[1] + judged - errors))


# ---- Part A: record the evidence process ---------------------------------------------------------------------
class RecordingCore(EngineCore):
    def __init__(self, cfg, **kw):
        super().__init__(cfg, **kw)
        self.points = []

    def observe(self, key, state, consequence, error, failure):
        super().observe(key, state, consequence, error, failure)
        if consequence in ERROR_BARS:
            self.points.append((key, consequence, state.n, state.err, state.since, self.type_i.get(key, 0)))


def part_a_points(actions, seed, future):
    """future(key, index) -> list of rates/outcomes for the key's next actions."""
    engine = RecordingCore(core_config(canaries=True), seed=seed * 17 + 3, n_total=len(actions), reviewer=rev(seed))
    for action in actions:
        engine.step(action)
    rows, eligible = [], []
    counter = {}
    for key, cons, judged, errors, since, index in engine.points:
        bar = ERROR_BARS[cons]
        window = future(key, index)
        if len(window) < 50:
            continue
        truly_under = st.fmean(window) <= bar
        s1 = score(errors, judged, bar)
        if since >= 30:
            eligible.append((s1 >= 0.95, wilson_upper(errors, judged) <= bar, s1))
        counter[key] = counter.get(key, 0) + 1
        if counter[key] % 5 == 0:
            rows.append((s1, score(errors, judged, bar, (0.5, 0.5)), truly_under))
    return rows, eligible


def t1_part_a(seed):
    actions, keys = world(seed)
    return part_a_points(actions, seed, lambda key, i: keys[key]["rates"][i:i + 200])


def t2_part_a(name):
    actions = t2_actions(name)
    sequences = {}
    for a in actions:
        sequences.setdefault((a.agent, a.task_type), []).append(int(a.true_err))
    rows, eligible = [], []
    for seed in T2_SEEDS:
        r, e = part_a_points(actions, seed, lambda key, i: sequences[key][i:i + 200])
        rows += r
        eligible += e
    return name, rows, eligible


# ---- Part B: evidence sources --------------------------------------------------------------------------------
def comparison_observation(rng, agent_wrong):
    """Shadow or replay: compare with a person's decision. Returns (error verdict, adjudication minutes)."""
    human_wrong = rng.random() < HUMAN_ERR
    if agent_wrong and human_wrong and rng.random() < SAME_WRONG:
        return 0, 0.0                                   # false agreement
    if not agent_wrong and not human_wrong:
        return 0, 0.0                                   # agreement
    # disagreement: a person adjudicates
    if agent_wrong:
        return int(rng.random() < ADJUDICATION), 1.0
    return int(rng.random() > ADJUDICATION), 1.0


def source_observations(source, rates, rng):
    shift = rng.uniform(0.3, 1.0)
    out = []
    for i in range(N_SOURCE):
        if source == "shadow":
            p = rates[min(i, len(rates) - 1)]
            out.append(comparison_observation(rng, rng.random() < p))
        elif source == "replay":
            out.append(comparison_observation(rng, rng.random() < rates[0]))
        else:   # tests: perfectly graded, easier than live
            out.append((int(rng.random() < rates[0] * shift), 0.0))
    return out


def t1_part_b(seed):
    actions, keys = world(seed)
    cons_of = {}
    for a in actions:
        cons_of.setdefault((a.agent, a.task_type), a.meta["cons"])
    rows = {src: [] for src in ("shadow", "replay", "tests")}
    for idx, src in enumerate(rows):
        rng = random.Random(seed * 101 + idx)
        for key, info in keys.items():
            cons = cons_of.get(key)
            if cons not in ERROR_BARS or len(info["rates"]) < 50:
                continue
            bar = ERROR_BARS[cons]
            truly_under = st.fmean(info["rates"][:200]) <= bar
            obs = source_observations(src, info["rates"], rng)
            errors = sum(e for e, _ in obs)
            rows[src].append(([score(w * errors, w * N_SOURCE, bar) for w in WEIGHTS], truly_under))
    return rows


# ---- Part C: ramp-up minutes per arm -------------------------------------------------------------------------
class RampCore(EngineCore):
    """Core + canaries, with per-key ramp-up minutes; arm SH (shadow ramp-up) or RP (replay pre-load)."""

    def __init__(self, cfg, arm="L", weight=1.0, **kw):
        super().__init__(cfg, **kw)
        self.arm, self.weight = arm, weight
        self.ramp = {}
        self.human_errors = 0
        self.shadow_manual = 0.0
        self.src_rng = random.Random(kw.get("seed", 0) * 7 + 11)

    def _weighted(self, key, state, cons, error):
        w = self.weight
        state.n += w
        state.err += w * error
        state.since += w
        state.recent.append(error)
        if cons in ERROR_BARS and state.level < 3 and state.since >= self.cfg.n_min and self.table_met(state, cons):
            self._set(key, state, state.level + 1, "table")

    def st(self, action):
        key = (action.agent, action.task_type)
        new = key not in self.state
        result = super().st(action)
        if new and self.arm == "RP" and action.meta["cons"] in ERROR_BARS:
            _, state = result
            rate0 = action.meta.get("p", 0.0)
            for _ in range(N_SOURCE):
                error, minutes = comparison_observation(self.src_rng, self.src_rng.random() < rate0)
                self.m["minutes"] += minutes
                self.ramp[key] = self.ramp.get(key, 0.0) + minutes
                self._weighted(key, state, action.meta["cons"], error)
        return result

    def step(self, action):
        key = (action.agent, action.task_type)
        cons = action.meta["cons"]
        level = self.state[key].level if key in self.state else 1
        before = self.m["minutes"]
        if self.arm == "SH" and level <= 1 and cons in ERROR_BARS:
            self.t += 1
            self.m["actions"] += 1
            self.by_cons[cons]["actions"] += 1
            self._fire()
            k, state = self.st(action)
            self.type_i[k] = self.type_i.get(k, 0) + 1
            self.m["minutes"] += MANUAL[cons]
            self.shadow_manual += MANUAL[cons]
            error, minutes = comparison_observation(self.src_rng, action.true_err)
            if self.src_rng.random() < HUMAN_ERR:
                self.human_errors += 1
            self.m["minutes"] += minutes
            self._weighted(k, state, cons, error)
            mode = "shadow"
        else:
            mode = super().step(action)
        if level <= 1:
            self.ramp[key] = self.ramp.get(key, 0.0) + self.m["minutes"] - before
        return mode


def t1_part_c(args):
    seed, weights = args
    actions, keys = world(seed)
    cons_of = {}
    for a in actions:
        cons_of.setdefault((a.agent, a.task_type), a.meta["cons"])
    out = {}
    for arm in ("L", "SH", "RP"):
        w = weights.get(arm, 1.0)
        engine = RampCore(core_config(canaries=True), arm=arm, weight=w, seed=seed * 17 + 3, n_total=len(actions),
                          reviewer=rev(seed))
        for a in actions:
            engine.step(a)
        good = total = 0
        for p in engine.promotions:
            if p["to"] < 2:
                continue
            rates = keys[p["key"]]["rates"][p["type_i"]: p["type_i"] + 200]
            if len(rates) < 50 or cons_of[p["key"]] not in ERROR_BARS:
                continue
            total += 1
            good += st.fmean(rates) <= ERROR_BARS[cons_of[p["key"]]]
        ramp = sum(v for k, v in engine.ramp.items() if cons_of.get(k) in ERROR_BARS)
        manual_total = sum(MANUAL[a.meta["cons"]] for a in actions)
        out[arm] = dict(ramp_minutes=ramp, minutes=engine.m["minutes"], manual=manual_total,
                        escapes_per100=100 * engine.m["escapes"] / len(actions), human_errors=engine.human_errors,
                        promotions=total, deserved=good, reviews=engine.m["pre"] + engine.m["spot"] + engine.m["canary"],
                        manual_in_shadow=engine.shadow_manual)
    return out


def ece(pairs, bins=(0, .5, .6, .7, .8, .9, .95, .99, 1.0000001)):
    table, n, total = [], len(pairs), 0.0
    for lo, hi in zip(bins, bins[1:]):
        inside = [(s, y) for s, y in pairs if lo <= s < hi]
        if not inside:
            table.append(dict(bin=f"{lo:.2f}-{min(hi, 1):.2f}", n=0))
            continue
        mean_s = st.fmean(s for s, _ in inside)
        frac = st.fmean(y for _, y in inside)
        total += len(inside) / n * abs(mean_s - frac)
        table.append(dict(bin=f"{lo:.2f}-{min(hi, 1):.2f}", n=len(inside), mean_score=mean_s, share_under=frac))
    return total, table


def main():
    with ProcessPoolExecutor() as pool:
        t1a = list(pool.map(t1_part_a, T1_SEEDS, chunksize=4))
        t2a = list(pool.map(t2_part_a, ("good-full", "sloppy-full")))
        t1b = list(pool.map(t1_part_b, T1_SEEDS, chunksize=4))
    # Part A summaries
    part_a = {}
    t1_rows = [r for rows, _ in t1a for r in rows]
    t1_elig = [e for _, el in t1a for e in el]
    sets = {"T1": (t1_rows, t1_elig)}
    for name, rows, elig in t2a:
        sets[name] = (rows, elig)
    for name, (rows, elig) in sets.items():
        e1, table = ece([(s, y) for s, _, y in rows])
        ej, _ = ece([(sj, y) for _, sj, y in rows])
        agree = st.fmean(a == b for a, b, _ in elig) if elig else None
        best = max((st.fmean((s >= th) == b for _, b, s in elig), th) for th in
                   [x / 1000 for x in range(900, 1000)]) if elig else None
        part_a[name] = dict(points=len(rows), ece=e1, ece_jeffreys=ej, table=table, eligible_points=len(elig),
                            agreement_095=agree, best_threshold=best[1] if best else None,
                            best_agreement=best[0] if best else None)
    # Part B: calibrated weights
    part_b = {}
    for src in ("shadow", "replay", "tests"):
        rows = [r for world_rows in t1b for r in world_rows[src]]
        results = []
        for wi, w in enumerate(WEIGHTS):
            e, table = ece([(scores[wi], y) for scores, y in rows])
            results.append(dict(weight=w, ece=e, table=table))
        best = min(results, key=lambda r: (round(r["ece"], 6), r["weight"]))
        part_b[src] = dict(keys=len(rows), by_weight=[dict(weight=r["weight"], ece=r["ece"]) for r in results],
                           calibrated_weight=best["weight"], calibrated_ece=best["ece"], table=best["table"])
    weights = {"SH": part_b["shadow"]["calibrated_weight"], "RP": part_b["replay"]["calibrated_weight"]}
    with ProcessPoolExecutor() as pool:
        t1c = list(pool.map(t1_part_c, [(s, weights) for s in T1_SEEDS], chunksize=4))
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "calibration-runs.json").write_text(json.dumps(dict(part_a=part_a, part_b=part_b, part_c=t1c,
                                                               weights=weights)))
    print("saved")


if __name__ == "__main__":
    main()
