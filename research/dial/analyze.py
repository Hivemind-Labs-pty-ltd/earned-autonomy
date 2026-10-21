"""Score round "dial" -> report/verdicts-dial.json.   python -m dial.analyze"""
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


def collect(rows):
    out = {}
    for arm in ("ladder", "dial"):
        mult = [r[arm]["manual"] / r[arm]["minutes"] for r in rows]
        last = [r[arm]["manual_last_third"] / max(1e-9, r[arm]["minutes_last_third"]) for r in rows]
        g = sum(r[arm]["deserved"][0] for r in rows)
        t = sum(r[arm]["deserved"][1] for r in rows)
        lat = [x for r in rows for x in r[arm].get("latencies", [])]
        spot = [r[arm]["mean_spot_rate"] for r in rows if r[arm]["mean_spot_rate"] is not None]
        out[arm] = dict(multiple=boot(mult), multiple_last_third=boot(last),
                        escapes_per100=boot([r[arm]["escapes_per100"] for r in rows]),
                        automation=boot([r[arm]["automation"] for r in rows]),
                        deserved=(g, t), latency_median=st.median(lat) if lat else None, latency_n=len(lat),
                        mean_spot_rate=st.fmean(spot) if spot else None)
    return out


def main():
    r = json.load(open(RAW / "dial-runs.json"))
    sets = {"T1": collect(r["t1"])}
    for name, rows in r["t2"].items():
        sets[name] = collect(rows)
    d1, d2 = {}, {}
    for name, x in sets.items():
        ratio = x["dial"]["multiple"][0] / x["ladder"]["multiple"][0]
        diff = x["dial"]["escapes_per100"][0] - x["ladder"]["escapes_per100"][0]
        d1[name] = (round(ratio, 4), ratio >= 1.1)
        d2[name] = (round(diff, 4), diff <= 0.1)

    def grade(d):
        ok = [p for _, p in d.values()]
        return "PASS" if all(ok) else ("MIXED" if any(ok) else "FAIL")
    lat_l, lat_d = sets["T1"]["ladder"]["latency_median"], sets["T1"]["dial"]["latency_median"]
    v = dict(DIAL1=dict(value={k: x for k, (x, _) in d1.items()}, verdict=grade(d1)),
             DIAL2=dict(value={k: x for k, (x, _) in d2.items()}, verdict=grade(d2)),
             DIAL3=dict(value=dict(ladder=lat_l, dial=lat_d), verdict="PASS" if lat_d <= lat_l + 5 else "FAIL"))
    (ROOT / "report/verdicts-dial.json").write_text(json.dumps(dict(verdicts=v, sets=sets), indent=1))
    for k, x in v.items():
        print(k, x["verdict"], x["value"])
    for name, x in sets.items():
        for arm, y in x.items():
            print(name, arm, {k: (tuple(round(z, 3) for z in val) if isinstance(val, (list, tuple)) else val) for k, val in y.items()})


if __name__ == "__main__":
    main()
