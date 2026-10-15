"""Score PREREG-v2 hypotheses. Writes report/verdicts-v2.json.

    python analyze_v2.py
"""
from __future__ import annotations

import json
import random
import statistics as st
from pathlib import Path

from scipy.stats import spearmanr

from analyze import load_stream
from gym.engine import Reviewer
from gym.engine_v2 import ConfigV2, PoolReviewer, run_v2
from t1.world_v2 import CONS_OF, fading_world, version_world, world

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "report/raw"
T2_CONS = {"low": "C1", "med": "C2", "high": "C3", "capped": "C4"}


def verdict(ok):
    return "PASS" if ok else "FAIL"


def combine(vs):
    return "PASS" if all(v == "PASS" for v in vs) else ("FAIL" if all(v == "FAIL" for v in vs) else "MIXED")


def rev(seed):
    return Reviewer(random.Random(seed * 31 + 1))


def mean(rows, f):
    return st.fmean(r[f] for r in rows)


def c1_metrics(s):
    b = s["by_cons"]["C1"]
    return dict(c1_removed=1 - b["reviews"] / max(1, b["actions"]),
                c1_esc_auto=100 * b["escapes_auto"] / max(1, b["auto"]), c1_auto=b["auto"])


def run_arms(actions, seed):
    out = {}
    arms = {"A": ConfigV2(kind="A"), "flat": ConfigV2(bars="flat"),
            "cons": ConfigV2(), "cons-nosucc": ConfigV2(success_criterion=False)}
    for n, cfg in arms.items():
        e = run_v2(actions, cfg, seed=seed * 17 + 3, reviewer=rev(seed))
        s = e.summary()
        s.update(c1_metrics(s))
        out[n] = s
    for n in ("flat", "cons", "cons-nosucc"):
        out[n]["removed"] = 1 - out[n]["reviews"] / out["A"]["reviews"]
    return out


def agg(runs):
    keys = ("automation", "removed", "cost_per100", "esc_per100", "esc_per100_auto", "auto_nsf", "reviews",
            "c1_removed", "c1_esc_auto")
    return {arm: {k: st.fmean(r[arm][k] for r in runs) for k in keys if k in runs[0][arm]}
            for arm in runs[0]}


def t2_actions(name):
    acts = load_stream(RAW / f"t2-stream-{name}.jsonl")
    for a in acts:
        a.meta["cons"] = T2_CONS[a.meta["risk"]]
        a.meta["nsf"] = (not a.true_err) and (not a.meta.get("task_success", True))
    return acts


def main():
    res, v = {}, {}
    # ---- C1 / C2 / C3 --------------------------------------------------------
    t1_runs = []
    for s in range(200):
        acts, _ = world(s)
        t1_runs.append(run_arms(acts, s))
    streams = {"T1": agg(t1_runs)}
    for name in ("good-full", "sloppy-full"):
        acts = t2_actions(name)
        streams[f"T2 {name}"] = agg([run_arms(acts, s) for s in range(20)])
    res["c_streams"] = streams

    c1v, c1s, c2v, c2s, c3v, c3s = [], [], [], [], [], []
    for n, g in streams.items():
        ok = g["cons"]["cost_per100"] <= g["flat"]["cost_per100"] and g["cons"]["removed"] >= g["flat"]["removed"] - .02
        c1v.append(verdict(ok))
        c1s.append(f"{n}: cost/100 {g['cons']['cost_per100']:.2f} vs flat {g['flat']['cost_per100']:.2f}; removed "
                   f"{g['cons']['removed']:.0%} vs {g['flat']['removed']:.0%}")
        ok2 = g["cons"]["c1_removed"] >= .4 and g["cons"]["c1_esc_auto"] <= 1.0
        c2v.append(verdict(ok2))
        c2s.append(f"{n}: C1 reviews removed {g['cons']['c1_removed']:.0%}, {g['cons']['c1_esc_auto']:.2f} "
                   f"escapes/100 auto")
        a, b = g["cons"], g["cons-nosucc"]
        cut = 1 - a["auto_nsf"] / b["auto_nsf"] if b["auto_nsf"] else 0.0
        cost = 100 * (b["automation"] - a["automation"])
        c3v.append(verdict(cut >= .3 and cost <= 5))
        c3s.append(f"{n}: non-serious failures auto-executed −{cut:.0%} ({b['auto_nsf']:.1f}→{a['auto_nsf']:.1f}); "
                   f"automation −{cost:.1f} pts")
    v["C1"] = dict(value="; ".join(c1s), verdict=combine(c1v))
    v["C2"] = dict(value="; ".join(c2s), verdict=combine(c2v))
    v["C3"] = dict(value="; ".join(c3s), verdict=combine(c3v))

    # ---- F1 fading ---------------------------------------------------------------
    f_res = {}
    for hl in (None, 90, 180):
        rows = []
        for s in range(100):
            acts, _ = fading_world(30_000 + s)
            e = run_v2(acts, ConfigV2(half_life=hl), seed=s * 17 + 3, reviewer=rev(30_000 + s))
            drift = e.by_key_escapes.get(("agX", "rare_drift"), 0)
            main = [a for a in acts if a.agent != "agX"]
            auto_main = sum(1 for a in main if a.meta.get("_auto"))
            rows.append(dict(drift=drift))
            # main-portfolio automation: rerun on main only with identical config (same fading)
            e2 = run_v2(main, ConfigV2(half_life=hl), seed=s * 17 + 3, reviewer=rev(30_000 + s))
            rows[-1]["main_auto"] = e2.summary()["automation"]
            rows[-1]["steady_rare_auto"] = None
        f_res[str(hl)] = dict(drift_escapes=mean(rows, "drift"), main_automation=mean(rows, "main_auto"))
    base = f_res["None"]
    fs, best = [], None
    for hl in ("90", "180"):
        r = f_res[hl]
        cut = 1 - r["drift_escapes"] / base["drift_escapes"] if base["drift_escapes"] else 0
        cost = 100 * (base["main_automation"] - r["main_automation"])
        ok = cut >= .3 and cost <= 3
        fs.append(f"half-life {hl}d: rare-then-drift escapes −{cut:.0%} ({base['drift_escapes']:.1f}→"
                  f"{r['drift_escapes']:.1f}); main automation −{cost:.1f} pts → {verdict(ok)}")
        if ok and (best is None or cost < best[1]):
            best = (hl, cost)
    res["f1"] = f_res
    v["F1"] = dict(value="; ".join(fs) + f" (no fading: main automation {base['main_automation']:.1%})",
                   verdict="PASS" if best else "FAIL", adopt=best[0] if best else None)

    # ---- R1 reviewer trust -------------------------------------------------------
    def pool(seed):
        rng = random.Random(seed * 101 + 9)
        return [PoolReviewer("A", lambda p: 0.95, rng), PoolReviewer("B", lambda p: 0.85, rng),
                PoolReviewer("C", lambda p: 0.60, rng), PoolReviewer("D", lambda p: 0.95 - 0.45 * p, rng)]
    r_rows = []
    for s in range(100):
        acts, _ = world(40_000 + s)
        out = {}
        for arm, trust in (("no-trust", False), ("trust", True)):
            p = pool(40_000 + s)
            e = run_v2(acts, ConfigV2(reviewer_trust=trust, canary_rate=0.02), seed=s * 17 + 3, pool=p)
            sm = e.summary()
            out[arm] = dict(escapes=sm["escapes"], minutes=sm["minutes"],
                            bad_at_r2_C=p[2].bad_reviews_at_r2, bad_at_r2_D=p[3].bad_reviews_at_r2,
                            levels=[x.st.level for x in p], rev_n=[round(x.st.n, 1) for x in p])
        r_rows.append(out)
    esc_n, esc_t = mean([r["no-trust"] for r in r_rows], "escapes"), mean([r["trust"] for r in r_rows], "escapes")
    min_n, min_t = mean([r["no-trust"] for r in r_rows], "minutes"), mean([r["trust"] for r in r_rows], "minutes")
    bad = [r["trust"]["bad_at_r2_C"] for r in r_rows] + [r["trust"]["bad_at_r2_D"] for r in r_rows]
    med_bad = st.median(bad)
    cut = 1 - esc_t / esc_n
    rise = min_t / min_n - 1
    lv = [r["trust"]["levels"] for r in r_rows]
    share_r2 = [st.fmean(l[i] >= 2 for l in lv) for i in range(4)]
    rn = [st.fmean(r["trust"]["rev_n"][i] for r in r_rows) for i in range(4)]
    res["r1"] = dict(esc_no=esc_n, esc_trust=esc_t, minutes_no=min_n, minutes_trust=min_t, median_bad_at_r2=med_bad,
                     end_share_r2=dict(zip("ABCD", share_r2)), mean_evidence_n=dict(zip("ABCD", rn)))
    v["R1"] = dict(value=f"escapes −{cut:.0%} ({esc_n:.1f}→{esc_t:.1f}); review minutes +{rise:.0%}; median "
                         f"bad-reviewer reviews at R2 = {med_bad}; share ending at R2 A/B/C/D = "
                         + "/".join(f"{x:.0%}" for x in share_r2) + "; mean evidence per reviewer "
                         + "/".join(f"{x:.0f}" for x in rn),
                   verdict=verdict(cut >= .25 and rise <= .15 and med_bad <= 60))

    # ---- K1 knowledge edits as versions -------------------------------------------
    k_rows, allv = [], []
    for s in range(100):
        acts, vpass, vrows = version_world(50_000 + s)
        allv += vrows
        out = {}
        for mode in ("carry", "discount", "keep"):
            e = run_v2(acts, ConfigV2(version_mode=mode, version_pass=vpass), seed=s * 17 + 3,
                       reviewer=rev(50_000 + s))
            sm = e.summary()
            out[mode] = dict(automation=sm["automation"], escapes=sm["escapes"])
        k_rows.append(out)
    rho = spearmanr([x for x, _ in allv], [y for _, y in allv])[0]
    ka = {m: dict(automation=st.fmean(r[m]["automation"] for r in k_rows),
                  escapes=st.fmean(r[m]["escapes"] for r in k_rows)) for m in ("carry", "discount", "keep")}
    res["k1"] = dict(arms=ka, rho=rho, n_versions=len(allv))
    ok = ka["carry"]["automation"] >= .8 * ka["keep"]["automation"] and \
        ka["carry"]["escapes"] <= 1.10 * ka["discount"]["escapes"]
    v["K1"] = dict(value=f"automation carry {ka['carry']['automation']:.1%} / keep {ka['keep']['automation']:.1%} / "
                         f"discount {ka['discount']['automation']:.1%}; escapes carry {ka['carry']['escapes']:.1f} / "
                         f"keep {ka['keep']['escapes']:.1f} / discount {ka['discount']['escapes']:.1f}; "
                         f"hidden-test ρ = {rho:.2f} over {len(allv)} versions",
                   verdict=verdict(ok))

    out = dict(verdicts=v, results=res)
    (ROOT / "report/verdicts-v2.json").write_text(json.dumps(out, indent=1, default=str))
    for k, x in v.items():
        print(f"{k:4} {x['verdict']:6} {x['value']}")
    print(json.dumps({n: {a: {k: round(val, 4) for k, val in d.items()} for a, d in g.items()}
                      for n, g in streams.items()}, indent=1))
    print(json.dumps(res["r1"], indent=1, default=str))


if __name__ == "__main__":
    main()
