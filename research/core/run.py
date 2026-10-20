"""Run every arm of round "core" and save raw per-seed results (PREREG-core.md).

    python -m core.run   (from research/)
"""
from __future__ import annotations

import json
import statistics as st
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from analyze_v2 import rev, t2_actions
from analyze_v3 import BASE, COMBINED
from core.policy_core import EngineCore, core_config
from gym.engine_v2 import CONS
from gym.engine_v3 import ConfigV3, EngineV3
from t1.world import REGRESSIONS
from t1.world_v2 import version_world, world

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "report/raw"
MANUAL_MINUTES = {"C1": 2.0, "C2": 4.0, "C3": 6.0, "C4": 6.0}
SIGMA_CALIBRATED = 0.38
T1_SEEDS = range(120_000, 120_200)
T1_VERSION_SEEDS = range(130_000, 130_100)
T2_SEEDS = range(400, 420)
T2_STREAMS = ("good-full", "sloppy-full", "10x-D-good", "10x-D-sloppy")
ABLATIONS = {"core+canaries": dict(canaries=True), "core+reentry": dict(reentry=True),
             "core+wilson-step-down": dict(wilson_step_down=True), "core+carry-over": dict(carry=True)}


def version_pass_of(actions):
    """As analyze_10x.version_pass_of: hidden pass only when the suite meets the 10-test minimum."""
    passes = {}
    for action in actions:
        hidden, suite = action.meta.get("hidden_pass"), action.meta.get("suite_n") or 0
        passes[(action.agent, action.version, action.task_type)] = hidden if (hidden is not None and suite >= 10) else None
    return passes


def arm_configs(version_pass=None):
    version_pass = version_pass or {}
    arms = {"A": (EngineV3, ConfigV3(kind="A", **BASE)),
            "full": (EngineV3, ConfigV3(**{**COMBINED, "version_pass": version_pass})),
            "core": (EngineCore, core_config(version_pass=version_pass))}
    for name, ablation in ABLATIONS.items():
        arms[name] = (EngineCore, core_config(version_pass=version_pass, **ablation))
    return arms


def run_one(engine_cls, cfg, actions, seed):
    engine = engine_cls(cfg, seed=seed * 17 + 3, n_total=len(actions), reviewer=rev(seed))
    cut = (2 * len(actions)) // 3
    minutes_at_cut = 0.0
    for index, action in enumerate(actions):
        if index == cut:
            minutes_at_cut = engine.m["minutes"]
        engine.step(action)
    manual = [MANUAL_MINUTES[a.meta["cons"]] for a in actions]
    summary = engine.summary()
    return engine, dict(
        minutes=engine.m["minutes"], minutes_last_third=engine.m["minutes"] - minutes_at_cut,
        manual=sum(manual), manual_last_third=sum(manual[cut:]),
        escapes_per100=summary["esc_per100"], automation=summary["automation"], actions=summary["actions"],
        promotions=len([p for p in engine.promotions if p["to"] >= 2]), demotions=len(engine.demotions))


def deserved(engine, future_rates, error_bar_of):
    good = total = 0
    for promotion in engine.promotions:
        if promotion["to"] < 2:
            continue
        rates = future_rates[promotion["key"]][promotion["type_i"]: promotion["type_i"] + 200]
        if len(rates) < 50:
            continue
        total += 1
        good += st.fmean(rates) <= error_bar_of(promotion["key"])
    return good, total


def regression_latencies(engine, keys):
    latencies = []
    for key, info in keys.items():
        if info["pattern"] not in REGRESSIONS or info["i0"] is None:
            continue
        level = 1
        for change in sorted(engine.promotions + engine.demotions, key=lambda r: r["t"]):
            if change["key"] == key and change["type_i"] <= info["i0"]:
                level = change["to"]
        if level < 2:
            continue
        after = [d["type_i"] - info["i0"] for d in engine.demotions if d["key"] == key and d["type_i"] > info["i0"]]
        if after:
            latencies.append(min(after))
    return latencies


def t1_seed(seed):
    actions, keys = world(seed)
    consequence = {}
    for a in actions:
        consequence.setdefault((a.agent, a.task_type), a.meta["cons"])
    rates = {k: info["rates"] for k, info in keys.items()}
    free = 100 * sum(a.true_err for a in actions) / len(actions)
    out = {"free_escapes_per100": free}
    for name, (engine_cls, cfg) in arm_configs().items():
        if name == "core+carry-over":
            continue
        engine, row = run_one(engine_cls, cfg, actions, seed)
        row["deserved"] = deserved(engine, rates, lambda k: CONS[consequence[k]]["eps"])
        row["latencies"] = regression_latencies(engine, keys)
        out[name] = row
    return out


def t1_version_seed(seed):
    actions, version_pass, _ = version_world(seed, noise=SIGMA_CALIBRATED)
    free = 100 * sum(a.true_err for a in actions) / len(actions)
    out = {"free_escapes_per100": free}
    for name, (engine_cls, cfg) in arm_configs(version_pass).items():
        if name in ("core+canaries", "core+reentry", "core+wilson-step-down"):
            continue
        _, row = run_one(engine_cls, cfg, actions, seed)
        out[name] = row
    return out


def t2_stream(name):
    actions = t2_actions(name)
    version_pass = version_pass_of(actions)
    sequences = {}
    for a in actions:
        sequences.setdefault((a.agent, a.task_type), []).append(int(a.true_err))
    consequence = {}
    for a in actions:
        consequence.setdefault((a.agent, a.task_type), a.meta["cons"])
    free = 100 * sum(a.true_err for a in actions) / len(actions)
    versioned = len({a.version for a in actions}) > 1
    seeds = []
    for seed in T2_SEEDS:
        out = {"free_escapes_per100": free}
        for arm, (engine_cls, cfg) in arm_configs(version_pass).items():
            if arm == "core+carry-over" and not versioned:
                continue
            engine, row = run_one(engine_cls, cfg, actions, seed)
            row["deserved"] = deserved(engine, sequences, lambda k: CONS[consequence[k]]["eps"])
            out[arm] = row
        seeds.append(out)
    return name, seeds


def tool_scope():
    scoped = t2_actions("good-scoped")
    ids = [a.meta["task_id"] for a in scoped]
    full = {a.meta["task_id"]: a for a in t2_actions("good-full")}
    full_subset = [full[i] for i in ids if i in full]
    scoped = [a for a in scoped if a.meta["task_id"] in full]
    out = {"n_tasks": len(scoped)}
    for label, actions in (("good-full subset", full_subset), ("good-scoped", scoped)):
        free = 100 * sum(a.true_err for a in actions) / len(actions)
        rows = []
        for seed in T2_SEEDS:
            _, row = run_one(EngineCore, core_config(), actions, seed)
            rows.append(row)
        out[label] = {"free_escapes_per100": free, "seeds": rows}
    return out


def main():
    with ProcessPoolExecutor() as pool:
        t1 = list(pool.map(t1_seed, T1_SEEDS, chunksize=4))
        t1v = list(pool.map(t1_version_seed, T1_VERSION_SEEDS, chunksize=4))
        t2 = dict(pool.map(t2_stream, T2_STREAMS))
    scope = tool_scope()
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "core-runs.json").write_text(json.dumps(dict(t1=t1, t1_versioned=t1v, t2=t2, tool_scope=scope)))
    print("saved", RAW / "core-runs.json")


if __name__ == "__main__":
    main()
