"""Score PREREG-contracts (K1–K4). Writes report/verdicts-contracts.json.

    cd research && python -m contracts.analyze
"""
from __future__ import annotations

import json
import random
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ("minutes_per_task", "without_person", "escapes_per100", "manual_minutes_per_task",
          "promotions", "demotions", "episodes_scored", "episodes_locked", "contract_exec", "contract_held",
          "judged_extra", "signoffs")


def boot(xs, n=2000, seed=0):
    rng = random.Random(seed)
    ms = sorted(st.fmean(rng.choices(xs, k=len(xs))) for _ in range(n))
    return [st.fmean(xs), ms[int(.025 * n)], ms[int(.975 * n)]]


def agg(rows):
    out = {f: boot([r[f] for r in rows]) for f in FIELDS}
    sc, lk = sum(r["episodes_scored"] for r in rows), sum(r["episodes_locked"] for r in rows)
    out["locked_share"] = lk / sc if sc else None
    out["locked_examples"] = [d for r in rows for d in r["locked_detail"]][:10]
    types = {}
    for r in rows:
        for tt, c in r["exec_by_type"].items():
            types[tt] = types.get(tt, 0) + c / len(rows)
    out["exec_by_type_mean"] = types
    return out


def both(vs):
    return "PASS" if all(v == "PASS" for v in vs) else ("FAIL" if all(v == "FAIL" for v in vs) else "MIXED")


def main():
    runs = json.loads((ROOT / "report/raw/contracts-runs.json").read_text())
    res, ks = {}, {k: [] for k in ("K1", "K2", "K3", "K4")}
    vals = {k: [] for k in ks}
    for name, d in runs.items():
        a = {arm: agg(rows) for arm, rows in d["arms"].items()}
        post = d["post_training"]
        cov = {tt: a["C"]["exec_by_type_mean"].get(tt, 0) / n for tt, n in post.items()}
        res[name] = dict(arms=a, contracts=d["contracts"], coverage_C=cov)
        A, B, C = a["A"], a["B"], a["C"]
        k1 = C["escapes_per100"][0] <= A["escapes_per100"][0] + 0.1
        k2 = C["minutes_per_task"][0] <= 0.7 * A["minutes_per_task"][0]
        lc, lb = C["locked_share"], B["locked_share"]
        k3a = lc is not None and lc < 0.05
        k3b = (lb is not None and lc is not None and (lb >= 2 * lc if lc > 0 else lb > 0))
        k3 = k3a and k3b
        k4 = C["without_person"][0] >= A["without_person"][0] + 0.10
        for k, ok in (("K1", k1), ("K2", k2), ("K3", k3), ("K4", k4)):
            ks[k].append("PASS" if ok else "FAIL")
        vals["K1"].append(f"{name}: escapes/100 A {A['escapes_per100'][0]:.2f} · B {B['escapes_per100'][0]:.2f} · C {C['escapes_per100'][0]:.2f}")
        vals["K2"].append(f"{name}: minutes/task A {A['minutes_per_task'][0]:.3f} · B {B['minutes_per_task'][0]:.3f} · C {C['minutes_per_task'][0]:.3f} (C/A {C['minutes_per_task'][0] / A['minutes_per_task'][0]:.2f}); manual {A['manual_minutes_per_task'][0]:.2f}")
        vals["K3"].append(f"{name}: locked-in share B {lb if lb is None else round(lb, 3)} ({B['episodes_locked'][0]:.1f}/{B['episodes_scored'][0]:.1f} per seed) · C {lc if lc is None else round(lc, 3)} ({C['episodes_locked'][0]:.1f}/{C['episodes_scored'][0]:.1f})")
        vals["K4"].append(f"{name}: without a person A {A['without_person'][0]:.1%} · B {B['without_person'][0]:.1%} · C {C['without_person'][0]:.1%}")
    verdicts = {k: dict(verdict=both(ks[k]), per_stream=ks[k], value=" | ".join(vals[k])) for k in ks}
    out = dict(verdicts=verdicts, streams=res)
    (ROOT / "report/verdicts-contracts.json").write_text(json.dumps(out, indent=1, default=str))
    for k, v in verdicts.items():
        print(k, v["verdict"], v["per_stream"], "\n   ", v["value"])
    return out


if __name__ == "__main__":
    main()
