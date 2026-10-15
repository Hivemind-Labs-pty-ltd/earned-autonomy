"""Score PREREG-v3 (confirmation round) and compute the v3 reference numbers. Writes report/verdicts-v3.json.

    python analyze_v3.py
"""
from __future__ import annotations

import json
import random
import statistics as st
from pathlib import Path

from scipy.stats import spearmanr

from analyze_v2 import rev, t2_actions
from gym.engine_v2 import CONS, PoolReviewer
from gym.engine_v3 import ConfigV3, EngineV3, ledger_complete, run_v3
from t1.world import REGRESSIONS
from t1.world_v2 import fading_world, version_world, world

ROOT = Path(__file__).resolve().parent
SIGMA_CAL = 0.38          # fixed in DECISIONS.md before scoring
BASE = dict(success_criterion=False, canary_rate=0.05)


def verdict(ok):
    return "PASS" if ok else "FAIL"


def boot(xs, n=2000, seed=0):
    rng = random.Random(seed)
    ms = sorted(st.fmean(rng.choices(xs, k=len(xs))) for _ in range(n))
    return st.fmean(xs), ms[int(.025 * n)], ms[int(.975 * n)]


# ---- K1' ----------------------------------------------------------------------
def k1():
    res = {}
    for label, sigma in (("a_sigma0.04", 0.04), ("b_calibrated", SIGMA_CAL)):
        rows, allv = [], []
        for s in range(60_000, 60_100):
            acts, vpass, vrows = version_world(s, noise=sigma)
            allv += vrows
            out = {}
            for arm, kw in (("carry", dict(version_mode="carry", carry_no_prev=True)),
                            ("keep", dict(version_mode="keep")), ("discount", dict(version_mode="discount"))):
                e = run_v3(acts, ConfigV3(version_pass=vpass, **BASE, **kw), seed=s * 17 + 3, reviewer=rev(s))
                sm = e.summary()
                out[arm] = (sm["automation"], sm["escapes"])
            rows.append(out)
        a = {arm: dict(automation=st.fmean(r[arm][0] for r in rows), escapes=st.fmean(r[arm][1] for r in rows))
             for arm in ("carry", "keep", "discount")}
        rho = spearmanr([x for x, _ in allv], [y for _, y in allv])[0]
        ok = a["carry"]["automation"] >= .8 * a["keep"]["automation"] and \
            a["carry"]["escapes"] <= 1.10 * a["discount"]["escapes"]
        res[label] = dict(arms=a, rho=rho, ok=ok,
                          keep_share=a["carry"]["automation"] / a["keep"]["automation"],
                          esc_ratio=a["carry"]["escapes"] / a["discount"]["escapes"])
    b = res["b_calibrated"]
    val = "; ".join(f"{lbl}: ρ {r['rho']:.2f}, carry automation {r['arms']['carry']['automation']:.1%} = "
                    f"{r['keep_share']:.0%} of keep ({r['arms']['keep']['automation']:.1%}); escapes "
                    f"{r['arms']['carry']['escapes']:.1f} = {r['esc_ratio']:.2f}× discount "
                    f"({r['arms']['discount']['escapes']:.1f}) → {verdict(r['ok'])}" for lbl, r in res.items())
    return dict(value=val, verdict=verdict(b["ok"]), detail=res)


# ---- R1' ----------------------------------------------------------------------
def pool(seed):
    rng = random.Random(seed * 101 + 9)
    p = [PoolReviewer("A", lambda x: 0.95, rng), PoolReviewer("B", lambda x: 0.85, rng),
         PoolReviewer("C", lambda x: 0.60, rng), PoolReviewer("D", lambda x: 0.95 - 0.45 * x, rng)]
    for r in p:
        r.ever_r2 = False
    return p


def r1():
    rows = []
    for s in range(70_000, 70_100):
        acts, _ = world(s)
        out = {}
        for arm, kw in (("no-trust", dict(reviewer_trust=False)), ("trust", dict(reviewer_trust=True, rev_clean=True))):
            p = pool(s)
            e = run_v3(acts, ConfigV3(**BASE, **kw), seed=s * 17 + 3, pool=p)
            sm = e.summary()
            out[arm] = dict(escapes=sm["escapes"], minutes=sm["minutes"],
                            ever_r2=[r.ever_r2 for r in p], end_r2=[r.st.level >= 2 for r in p],
                            d_bad_at_r2=p[3].bad_reviews_at_r2, c_bad_at_r2=p[2].bad_reviews_at_r2)
        rows.append(out)
    t = [r["trust"] for r in rows]
    c_ever = st.fmean(x["ever_r2"][2] for x in t)
    a_end = st.fmean(x["end_r2"][0] for x in t)
    esc_n, esc_t = st.fmean(r["no-trust"]["escapes"] for r in rows), st.fmean(x["escapes"] for x in t)
    min_n, min_t = st.fmean(r["no-trust"]["minutes"] for r in rows), st.fmean(x["minutes"] for x in t)
    ok = c_ever <= .10 and a_end >= .80 and esc_t <= esc_n
    end = [st.fmean(x["end_r2"][i] for x in t) for i in range(4)]
    ever = [st.fmean(x["ever_r2"][i] for x in t) for i in range(4)]
    val = (f"C (0.60) ever at R2 in {c_ever:.0%} of worlds; A (0.95) at R2 at end in {a_end:.0%}; escapes "
           f"{esc_t:.1f} vs {esc_n:.1f} without reviewer trust ({esc_t / esc_n - 1:+.0%}); review minutes "
           f"{min_t / min_n - 1:+.0%}. End at R2 A/B/C/D = " + "/".join(f"{x:.0%}" for x in end)
           + "; ever at R2 = " + "/".join(f"{x:.0%}" for x in ever)
           + f"; D median reviews at R2 after falling below 0.80 = {st.median(x['d_bad_at_r2'] for x in t)}")
    return dict(value=val, verdict=verdict(ok),
                detail=dict(c_ever=c_ever, a_end=a_end, esc_no=esc_n, esc_trust=esc_t, min_no=min_n, min_trust=min_t,
                            end_r2=end, ever_r2=ever))


# ---- F1' ----------------------------------------------------------------------
def f1():
    rows = []
    for s in range(80_000, 80_100):
        acts, _ = fading_world(s)
        main = [a for a in acts if a.agent != "agX"]
        r = {}
        for arm, kw in (("base", {}), ("reentry60", dict(reentry_gap=60.0))):
            e = run_v3(acts, ConfigV3(**BASE, **kw), seed=s * 17 + 3, reviewer=rev(s))
            e2 = run_v3(main, ConfigV3(**BASE, **kw), seed=s * 17 + 3, reviewer=rev(s))
            r[arm] = (e.by_key_escapes.get(("agX", "rare_drift"), 0), e2.summary()["automation"])
        rows.append(r)
    d = {arm: dict(drift_escapes=st.fmean(x[arm][0] for x in rows), main_automation=st.fmean(x[arm][1] for x in rows))
         for arm in ("base", "reentry60")}
    cut = 1 - d["reentry60"]["drift_escapes"] / d["base"]["drift_escapes"]
    cost = 100 * (d["base"]["main_automation"] - d["reentry60"]["main_automation"])
    ok = cut >= .10 and cost <= 1.0
    val = (f"rare-then-drift escapes {d['base']['drift_escapes']:.2f} → {d['reentry60']['drift_escapes']:.2f} "
           f"(−{cut:.0%}); main automation {d['base']['main_automation']:.1%} → "
           f"{d['reentry60']['main_automation']:.1%} ({-cost:+.1f} pts)")
    return dict(value=val, verdict=verdict(ok), detail=d)


# ---- combined reference numbers ---------------------------------------------------
COMBINED = dict(**BASE, version_mode="carry", carry_no_prev=True, reentry_gap=60.0)


def ref_t1():
    runs = []
    for s in range(90_000, 90_200):
        acts, keys = world(s)
        e = run_v3(acts, ConfigV3(**COMBINED), seed=s * 17 + 3, reviewer=rev(s))
        a = run_v3(acts, ConfigV3(kind="A", **BASE), seed=s * 17 + 3, reviewer=rev(s))
        sm, sa = e.summary(), a.summary()
        good = total = 0
        for p in e.promotions:
            if p["to"] < 2:
                continue
            cons = acts_cons(acts, p["key"])
            rates = keys[p["key"]]["rates"][p["type_i"]: p["type_i"] + 200]
            if len(rates) < 50:
                continue
            total += 1
            good += st.fmean(rates) <= CONS[cons]["eps"]
        lat = []
        for k, ks in keys.items():
            if ks["pattern"] not in REGRESSIONS or ks["i0"] is None:
                continue
            lvl = 1
            for c in sorted(e.promotions + e.demotions, key=lambda r: r["t"]):
                if c["key"] == k and c["type_i"] <= ks["i0"]:
                    lvl = c["to"]
            if lvl < 2:
                continue
            after = [d["type_i"] - ks["i0"] for d in e.demotions if d["key"] == k and d["type_i"] > ks["i0"]]
            if after:
                lat.append(min(after))
        runs.append(dict(removed=1 - sm["reviews"] / sa["reviews"], automation=sm["automation"],
                         esc100=sm["esc_per100"], esc100_auto=sm["esc_per100_auto"], cost100=sm["cost_per100"],
                         esc100_A=sa["esc_per100"], cost100_A=sa["cost_per100"], h1=(good, total), lat=lat,
                         g2=ledger_complete(e)))
    return summarise(runs, with_lat=True)


def acts_cons(acts, key, _cache={}):
    if key not in _cache:
        _cache[key] = next(a.meta["cons"] for a in acts if (a.agent, a.task_type) == key)
    return _cache[key]


def ref_t2(name):
    acts = t2_actions(name)
    seq = {}
    for a in acts:
        seq.setdefault((a.agent, a.task_type), []).append(a.true_err)
    runs = []
    for s in range(100, 120):
        e = run_v3(acts, ConfigV3(**COMBINED), seed=s * 17 + 3, reviewer=rev(s))
        a = run_v3(acts, ConfigV3(kind="A", **BASE), seed=s * 17 + 3, reviewer=rev(s))
        sm, sa = e.summary(), a.summary()
        good = total = 0
        for p in e.promotions:
            if p["to"] < 2:
                continue
            nxt = seq[p["key"]][p["type_i"]: p["type_i"] + 200]
            if len(nxt) < 50:
                continue
            total += 1
            good += st.fmean(nxt) <= CONS[acts_cons(acts, p["key"])]["eps"]
        runs.append(dict(removed=1 - sm["reviews"] / sa["reviews"], automation=sm["automation"],
                         esc100=sm["esc_per100"], esc100_auto=sm["esc_per100_auto"], cost100=sm["cost_per100"],
                         esc100_A=sa["esc_per100"], cost100_A=sa["cost_per100"], h1=(good, total), lat=[],
                         g2=ledger_complete(e)))
    return summarise(runs, with_lat=False)


def summarise(runs, with_lat):
    out = {}
    for f in ("removed", "automation", "esc100", "esc100_auto", "cost100", "esc100_A", "cost100_A", "g2"):
        out[f] = boot([r[f] for r in runs])
    g, t = sum(r["h1"][0] for r in runs), sum(r["h1"][1] for r in runs)
    out["h1"] = (g, t, g / t if t else None)
    if with_lat:
        lats = [l for r in runs for l in r["lat"]]
        out["h4_median"] = st.median(lats) if lats else None
        out["h4_n"] = len(lats)
    return out


def main():
    v = {"K1'": k1(), "R1'": r1(), "F1'": f1()}
    ref = {"T1": ref_t1(), "T2 good-full": ref_t2("good-full"), "T2 sloppy-full": ref_t2("sloppy-full")}
    (ROOT / "report/verdicts-v3.json").write_text(json.dumps(dict(verdicts=v, reference=ref), indent=1, default=str))
    for k, x in v.items():
        print(f"{k:4} {x['verdict']:5} {x['value']}")
    for n, r in ref.items():
        print(n, {k: (tuple(round(y, 4) for y in val) if isinstance(val, tuple) and all(isinstance(y, float) for y in val)
                      else val) for k, val in r.items()})


if __name__ == "__main__":
    main()
