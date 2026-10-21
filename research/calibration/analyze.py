"""Score round "calibration" -> report/verdicts-calibration.json.   python -m calibration.analyze"""
from __future__ import annotations

import json
import random
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "report/raw"


def boot(xs, n=2000, seed=0):
    rng = random.Random(seed)
    means = sorted(st.fmean(rng.choices(xs, k=len(xs))) for _ in range(n))
    return st.fmean(xs), means[int(.025 * n)], means[int(.975 * n)]


def main():
    r = json.load(open(RAW / "calibration-runs.json"))
    a, b, c = r["part_a"], r["part_b"], r["part_c"]
    v = {}
    eces = {k: x["ece"] for k, x in a.items()}
    passes = [e <= 0.05 for e in eces.values()]
    v["CAL1"] = dict(value={k: round(e, 4) for k, e in eces.items()},
                     verdict="PASS" if all(passes) else ("MIXED" if any(passes) else "FAIL"))
    agree = {k: x["agreement_095"] for k, x in a.items()}
    pooled_n = sum(x["eligible_points"] for x in a.values())
    pooled = sum(x["agreement_095"] * x["eligible_points"] for x in a.values()) / pooled_n
    v["CAL2"] = dict(value=dict(per_set={k: round(x, 4) for k, x in agree.items()}, pooled=round(pooled, 4),
                                best_threshold={k: x["best_threshold"] for k, x in a.items()},
                                best_agreement={k: round(x["best_agreement"], 4) for k, x in a.items()}),
                     verdict="PASS" if pooled >= 0.95 else "FAIL")

    def arm(name, f):
        return [s[name][f] for s in c]

    out_c = {}
    for name in ("L", "SH", "RP"):
        ramp = arm(name, "ramp_minutes")
        mult = [s[name]["manual"] / s[name]["minutes"] for s in c]
        prom = sum(arm(name, "promotions"))
        und = 1 - sum(arm(name, "deserved")) / prom if prom else None
        out_c[name] = dict(ramp_minutes=boot(ramp), multiple=boot(mult), undeserved=und, promotions=prom,
                           escapes_per100=boot(arm(name, "escapes_per100")),
                           human_errors=st.fmean(arm(name, "human_errors")),
                           extra_ramp_minutes=boot([s[name]["ramp_minutes"] - s[name]["manual_in_shadow"] for s in c]))
    base = out_c["L"]
    for key, name in (("CAL3", "SH"), ("CAL3b", "RP")):
        cut = 1 - out_c[name]["ramp_minutes"][0] / base["ramp_minutes"][0]
        d_und = 100 * (out_c[name]["undeserved"] - base["undeserved"])
        v[key] = dict(value=dict(ramp_cut=round(cut, 4), undeserved_change_pts=round(d_und, 2),
                                 extra_ramp_cut=round(1 - out_c[name]["extra_ramp_minutes"][0] /
                                                      base["ramp_minutes"][0], 4)),
                      verdict="PASS" if cut >= 0.5 and d_und <= 1.0 else "FAIL")
    res = dict(verdicts=v, part_a={k: {kk: vv for kk, vv in x.items()} for k, x in a.items()},
               part_b=b, part_c=out_c, weights=r["weights"])
    (ROOT / "report/verdicts-calibration.json").write_text(json.dumps(res, indent=1))
    for k, x in v.items():
        print(k, x["verdict"], x["value"])
    for s, x in b.items():
        print(s, "w*", x["calibrated_weight"], "ece", round(x["calibrated_ece"], 4),
              [(y["weight"], round(y["ece"], 3)) for y in x["by_weight"]])
    for n, x in out_c.items():
        print(n, {k: (tuple(round(z, 3) for z in y) if isinstance(y, (list, tuple)) else (round(y, 4) if isinstance(y, float) else y)) for k, y in x.items()})
    for k, x in a.items():
        print(k, "points", x["points"], "ece", round(x["ece"], 4), "jeffreys", round(x["ece_jeffreys"], 4))
        for row in x["table"]:
            print("   ", row)


if __name__ == "__main__":
    main()
