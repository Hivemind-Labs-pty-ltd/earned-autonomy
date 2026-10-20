"""Score round "core" (PREREG-core.md). Writes report/verdicts-core.json.

    python -m core.analyze   (from research/)
"""
from __future__ import annotations

import json
import random
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "report/raw"
ARMS = ("A", "full", "core", "core+canaries", "core+reentry", "core+wilson-step-down", "core+carry-over")
ABLATIONS = ("core+canaries", "core+reentry", "core+wilson-step-down", "core+carry-over")


def boot(values, n=2000, seed=0):
    rng = random.Random(seed)
    means = sorted(st.fmean(rng.choices(values, k=len(values))) for _ in range(n))
    return st.fmean(values), means[int(.025 * n)], means[int(.975 * n)]


def summarise(seeds):
    """seeds: list of per-seed dicts {arm: row, 'free_escapes_per100': x}."""
    out = {"free_escapes_per100": st.fmean(s["free_escapes_per100"] for s in seeds)}
    for arm in ARMS:
        rows = [s[arm] for s in seeds if arm in s]
        if not rows:
            continue
        good = sum(r["deserved"][0] for r in rows if "deserved" in r)
        total = sum(r["deserved"][1] for r in rows if "deserved" in r)
        latencies = [x for r in rows for x in r.get("latencies", [])]
        out[arm] = dict(
            multiple=boot([r["manual"] / r["minutes"] for r in rows]),
            multiple_steady=boot([r["manual_last_third"] / max(1e-9, r["minutes_last_third"]) for r in rows]),
            human_minutes_per_task=st.fmean(r["minutes"] / r["actions"] for r in rows),
            escapes_per100=boot([r["escapes_per100"] for r in rows]),
            automation=st.fmean(r["automation"] for r in rows),
            deserved=(good, total, good / total if total else None),
            regression_latency_median=st.median(latencies) if latencies else None,
            regression_n=len(latencies))
    return out


def tri(values):
    return "PASS" if all(values) else ("FAIL" if not any(values) else "MIXED")


def main():
    raw = json.loads((RAW / "core-runs.json").read_text())
    streams = {"T1": summarise(raw["t1"]), "T1 versioned": summarise(raw["t1_versioned"])}
    for name, seeds in raw["t2"].items():
        streams[f"T2 {name}"] = summarise(seeds)
    scored = [s for s in streams if s != "T1 versioned"]

    q1, q2, q3, detail = [], [], [], {}
    for name in scored:
        s = streams[name]
        full, core, free = s["full"], s["core"], s["free_escapes_per100"]
        ok1 = core["escapes_per100"][0] <= full["escapes_per100"][0] + 0.1
        ratio = core["multiple"][0] / full["multiple"][0]
        ok2 = ratio >= 0.9
        reduction_full = free - full["escapes_per100"][0]
        reduction_core = free - core["escapes_per100"][0]
        kept = reduction_core / reduction_full if reduction_full else float("nan")
        ok3 = reduction_core >= 0.9 * reduction_full
        q1.append(ok1), q2.append(ok2), q3.append(ok3)
        detail[name] = dict(q1=ok1, q2=ok2, q3=ok3, multiple_ratio=ratio, reduction_kept=kept,
                            escapes_core=core["escapes_per100"][0], escapes_full=full["escapes_per100"][0],
                            multiple_core=core["multiple"][0], multiple_full=full["multiple"][0], free=free)

    # Q4: ablations vs Core, per stream (carry-over on versioned streams only)
    ablation = {}
    for name, s in streams.items():
        core = s["core"]
        for arm in ABLATIONS:
            if arm not in s:
                continue
            ablation.setdefault(arm, {})[name] = dict(
                multiple_change=s[arm]["multiple"][0] / core["multiple"][0] - 1,
                escapes_change=s[arm]["escapes_per100"][0] - core["escapes_per100"][0],
                escapes_change_rel=(s[arm]["escapes_per100"][0] / core["escapes_per100"][0] - 1)
                if core["escapes_per100"][0] else None)

    # tool scope (rule 4)
    scope = raw["tool_scope"]
    scope_summary = {}
    for label in ("good-full subset", "good-scoped"):
        rows = scope[label]["seeds"]
        scope_summary[label] = dict(free_escapes_per100=scope[label]["free_escapes_per100"],
                                    multiple=boot([r["manual"] / r["minutes"] for r in rows]),
                                    escapes_per100=boot([r["escapes_per100"] for r in rows]),
                                    automation=st.fmean(r["automation"] for r in rows))

    # recommendation rule (pre-registered): Core if removing it fails Q1 anywhere or costs > 10% of the multiple;
    # Standard if it moves escapes or the multiple by > 5% somewhere; else Advanced.
    placement = {}
    for arm, per_stream in ablation.items():
        core_needed = standard = False
        for name, d in per_stream.items():
            s = streams[name]
            with_feature = s[arm]["escapes_per100"][0]
            if s["core"]["escapes_per100"][0] > with_feature + 0.1 or d["multiple_change"] > 0.10:
                core_needed = True
            rel = d["escapes_change_rel"]
            if abs(d["multiple_change"]) > 0.05 or (rel is not None and abs(rel) > 0.05):
                standard = True
        placement[arm] = "Core" if core_needed else ("Standard" if standard else "Advanced")

    out = dict(verdicts={"Q1": tri(q1), "Q2": tri(q2), "Q3": tri(q3)}, detail=detail, streams=streams,
               ablation=ablation, tool_scope=dict(n_tasks=scope["n_tasks"], **scope_summary), placement=placement)
    (ROOT / "report/verdicts-core.json").write_text(json.dumps(out, indent=1, default=str))

    print("VERDICTS", out["verdicts"])
    for name, d in detail.items():
        print(f"{name:20} Q1 {d['q1']!s:5} esc core {d['escapes_core']:.3f} full {d['escapes_full']:.3f} free {d['free']:.2f}"
              f" | Q2 {d['q2']!s:5} multiple core {d['multiple_core']:.2f} full {d['multiple_full']:.2f} ratio {d['multiple_ratio']:.3f}"
              f" | Q3 {d['q3']!s:5} kept {d['reduction_kept']:.3f}")
    for name, s in streams.items():
        print(name, {arm: (round(s[arm]["multiple"][0], 2), round(s[arm]["multiple_steady"][0], 2),
                           round(s[arm]["escapes_per100"][0], 3), round(s[arm]["automation"], 3),
                           s[arm]["deserved"][2] and round(s[arm]["deserved"][2], 3), s[arm]["regression_latency_median"])
                     for arm in ARMS if arm in s})
    for arm, per in ablation.items():
        print(arm, placement[arm], {k: (round(v["multiple_change"], 3), round(v["escapes_change"], 3)) for k, v in per.items()})
    print("TOOL SCOPE", {k: (round(v["multiple"][0], 2), round(v["escapes_per100"][0], 3), round(v["automation"], 3),
                             round(v["free_escapes_per100"], 2)) for k, v in scope_summary.items()})


if __name__ == "__main__":
    main()
