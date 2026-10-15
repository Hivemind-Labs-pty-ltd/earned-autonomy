"""Score PREREG-v1 hypotheses. Writes report/verdicts-v1.json.

    python analyze_v1.py
"""
from __future__ import annotations

import json
import random
import statistics as st
from pathlib import Path

from analyze import load_stream
from gym.engine import PolicyConfig, Reviewer, ledger_complete, no_auto_after_incident, run_stream
from gym.engine_v1 import EPS_BY_RISK, PolicyConfigV1, run_stream_v1, v1_config
from t1 import peer
from t1.run import regression_metrics
from t1.world import make_world

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "report/raw"
T2_SEEDS = range(20)

V1_ARMS = {
    "V2-soft": dict(kind="D", hard_demotion=False),
    "V3-pooled": dict(kind="D", pooled_k=20),
    "V4-riskeps": dict(kind="D", eps_by_risk=dict(EPS_BY_RISK)),
    "V6-v1": dict(kind="D", hard_demotion=False, pooled_k=20, eps_by_risk=dict(EPS_BY_RISK)),
}
V0_ARMS = {"A": dict(kind="A"), "D": dict(kind="D"), "D-agent": dict(kind="D", granularity="agent")}


def verdict(ok):
    return "PASS" if ok else "FAIL"


def combine(vs):
    if all(v == "PASS" for v in vs):
        return "PASS"
    if all(v == "FAIL" for v in vs):
        return "FAIL"
    return "MIXED"


def summ(e):
    s = e.summary()
    s["promotions"] = e.promotions
    return s


def run_all(actions, seed_reviewer, seed_engine, keys=None):
    out = {}
    for n, kw in V0_ARMS.items():
        e = run_stream(actions, PolicyConfig(**kw), seed=seed_engine, reviewer=Reviewer(random.Random(seed_reviewer)))
        out[n] = summ(e)
        if n == "D":
            out[n]["ledger_complete"] = ledger_complete(e)
    for n, kw in V1_ARMS.items():
        e = run_stream_v1(actions, PolicyConfigV1(**kw), seed=seed_engine,
                          reviewer=Reviewer(random.Random(seed_reviewer)))
        out[n] = summ(e)
        if n == "V6-v1":
            out[n]["ledger_complete"] = ledger_complete(e)
            out[n]["auto_after_incident_L1"] = no_auto_after_incident(e)
            out[n]["incidents_left_autonomous"] = sum(1 for d in e.demotions if d["why"] == "incident" and d["to"] >= 2)
            if keys is not None:
                out[n].update(regression_metrics(e, keys))
                good = total = 0
                for p in e.promotions:
                    if p["to"] < 2:
                        continue
                    rates = keys[p["key"]]["rates"][p["type_i"]: p["type_i"] + 200]
                    if len(rates) < 50:
                        continue
                    total += 1
                    good += st.fmean(rates) <= e.eps_for(p["key"])
                out[n]["h1"] = (good, total)
    # B-matched to v1 automation
    flag_rate = sum(a.check_flag for a in actions) / len(actions)
    hold = max(0.0, 1 - out["V6-v1"]["automation"] / max(1e-9, 1 - flag_rate))
    e = run_stream(actions, PolicyConfig(kind="Bm", hold_p=hold), seed=seed_engine,
                   reviewer=Reviewer(random.Random(seed_reviewer)))
    out["B-matched-v1"] = e.summary()
    return out


def mean_arms(runs):
    agg = {}
    for arm in runs[0]:
        rows = [r[arm] for r in runs]
        agg[arm] = {f: st.fmean(r[f] for r in rows) for f in
                    ("automation", "reviews", "escapes", "esc_per100", "esc_per100_auto")}
        for f in ("ledger_complete", "auto_after_incident_L1", "incidents_left_autonomous"):
            if f in rows[0]:
                agg[arm][f] = st.fmean(r[f] for r in rows)
        if "h1" in rows[0]:
            agg[arm]["h1"] = (sum(r["h1"][0] for r in rows), sum(r["h1"][1] for r in rows))
            lats = [l for r in rows for l in r["reg_latencies"]]
            agg[arm]["reg_latency_median"] = st.median(lats) if lats else None
            agg[arm]["reg_eligible"] = sum(r["reg_eligible"] for r in rows)
            agg[arm]["reg_detected50"] = sum(r["reg_detected50"] for r in rows)
    return agg


def t1():
    runs = []
    for s in range(200):
        actions, keys = make_world(s)
        runs.append(run_all(actions, s * 31 + 1, s * 17 + 3, keys))
    return mean_arms(runs)


def t2(name):
    acts = load_stream(RAW / f"t2-stream-{name}.jsonl")
    return mean_arms([run_all(acts, s + 101, s) for s in T2_SEEDS])


def version_pass():
    vp = {}
    for arch in ("ap", "cs", "do", "it", "of", "ws"):
        rows = [json.loads(l) for l in open(RAW / f"t2-loop-{arch}.jsonl")]
        for prev, cur in zip(rows, rows[1:]):
            vp[(f"{arch}-loop", cur["version"])] = cur["hidden_pass"] >= 0.8 and cur["hidden_pass"] >= prev["hidden_pass"]
    return vp


def v1_carryover():
    acts = load_stream(RAW / "t2-stream-loop.jsonl")
    seq = {}
    for a in acts:
        seq.setdefault((a.agent, a.task_type), []).append(a.true_err)
    vp = version_pass()
    res = {}
    for label, use_v1 in (("v0", False), ("v1", True)):
        promoted = keyruns = auto = esc_auto = good = total = 0
        for s in T2_SEEDS:
            rv = Reviewer(random.Random(s + 101))
            if use_v1:
                e = run_stream_v1(acts, PolicyConfigV1(kind="D", version_pass=vp), seed=s, reviewer=rv)
            else:
                e = run_stream(acts, PolicyConfig(kind="D"), seed=s, reviewer=rv)
            keyruns += len(seq)
            promoted += len({p["key"] for p in e.promotions if p["to"] >= 2})
            m = e.summary()
            auto += m["auto"]
            esc_auto += m["escapes_auto"]
            for p in e.promotions:
                if p["to"] < 2:
                    continue
                nxt = seq[p["key"]][p["type_i"]: p["type_i"] + 200]
                if len(nxt) < 30:
                    continue
                total += 1
                good += st.fmean(nxt) <= 0.05
        res[label] = dict(promoted=promoted, keyruns=keyruns, esc_per100_auto=100 * esc_auto / max(1, auto),
                          h1=(good, total), passed_versions=sum(vp.values()), versions=len(vp))
    return res


def main():
    v = {}
    T1 = t1()
    T2 = {n: t2(n) for n in ("good-full", "sloppy-full")}
    tiers = {"T1": T1, **{f"T2 {n}": a for n, a in T2.items()}}

    # V1
    co = v1_carryover()
    p0, p1, kr = co["v0"]["promoted"], co["v1"]["promoted"], co["v1"]["keyruns"]
    bar = (p1 >= 0.10 * kr) if p0 == 0 else (p1 >= 1.5 * p0)
    g, t = co["v1"]["h1"]
    prec = g / t if t else 0.0
    v["V1 carry-over"] = dict(value=f"promoted key-runs {p0}/{kr} (v0) → {p1}/{kr} (v1); escapes "
                                    f"{co['v1']['esc_per100_auto']:.2f}/100 auto; H1 {g}/{t}"
                                    f"{f' = {prec:.0%}' if t else ''}; {co['v1']['passed_versions']}/"
                                    f"{co['v1']['versions']} version changes passed hidden tests",
                              verdict=verdict(bar and co["v1"]["esc_per100_auto"] <= 1.0 and prec >= .8))
    # V2
    vs, txt = [], []
    for tn, a in tiers.items():
        ok = a["V2-soft"]["esc_per100"] <= a["D"]["esc_per100"] * 1.05 and a["V2-soft"]["automation"] >= a["D"]["automation"]
        vs.append(verdict(ok))
        txt.append(f"{tn}: esc/100 {a['D']['esc_per100']:.3f}→{a['V2-soft']['esc_per100']:.3f}, automation "
                   f"{a['D']['automation']:.1%}→{a['V2-soft']['automation']:.1%}")
    v["V2 one-level demotion"] = dict(value="; ".join(txt), verdict=combine(vs))
    # V3
    vs, txt = [], []
    for tn, a in tiers.items():
        mx = max(a["D"]["automation"], a["D-agent"]["automation"])
        mn = min(a["D"]["esc_per100"], a["D-agent"]["esc_per100"])
        ok = a["V3-pooled"]["automation"] >= mx - .02 and a["V3-pooled"]["esc_per100"] <= mn + .05
        vs.append(verdict(ok))
        txt.append(f"{tn}: automation {a['V3-pooled']['automation']:.1%} vs best {mx:.1%}; esc/100 "
                   f"{a['V3-pooled']['esc_per100']:.3f} vs best {mn:.3f}")
    v["V3 pooled trust"] = dict(value="; ".join(txt), verdict=combine(vs))
    # V4
    vs, txt = [], []
    for tn in ("T1", "T2 good-full"):
        a = tiers[tn]
        rem = 1 - a["V4-riskeps"]["reviews"] / a["A"]["reviews"]
        ok = rem >= .4 and a["V4-riskeps"]["esc_per100_auto"] <= 1.0
        vs.append(verdict(ok))
        txt.append(f"{tn}: reviews removed {rem:.1%} (flat ε {1 - a['D']['reviews'] / a['A']['reviews']:.1%}); "
                   f"esc {a['V4-riskeps']['esc_per100_auto']:.2f}/100 auto")
    v["V4 ε by risk"] = dict(value="; ".join(txt), verdict=combine(vs))
    # V5
    p = peer.main(out="t1-peer-v1.json")
    eq, vf = p["equal"], p["verify"]
    for arm in ("trust-ts", "trust-drift"):
        x = p[arm]
        r1 = x["acc"] >= eq["acc"] + .05 and x["calls"] <= .5 * vf["calls"]
        r3 = x["r3_median_bad_outputs"] is not None and x["r3_median_bad_outputs"] <= 10
        v[f"V5 peer {arm} R1"] = dict(value=f"accuracy {x['acc']:.1%} (equal {eq['acc']:.1%}); calls {x['calls']:.0f} "
                                           f"(verify-all {vf['calls']:.0f})", verdict=verdict(r1))
        v[f"V5 peer {arm} R3"] = dict(value=f"rerouted in {x['r3_caught_share']:.0%} of runs; median "
                                           f"{x['r3_median_bad_outputs']} bad outputs first; "
                                           f"{x['defector_bad_unverified']:.1f} unverified bad outputs",
                                     verdict=verdict(r3))
    # V6
    vs, txt = [], []
    for tn, a in tiers.items():
        ok = a["V6-v1"]["automation"] > a["D"]["automation"] and a["V6-v1"]["esc_per100"] <= a["D"]["esc_per100"] * 1.05
        vs.append(verdict(ok))
        txt.append(f"{tn}: automation {a['D']['automation']:.1%}→{a['V6-v1']['automation']:.1%}, esc/100 "
                   f"{a['D']['esc_per100']:.3f}→{a['V6-v1']['esc_per100']:.3f}, reviews removed "
                   f"{1 - a['V6-v1']['reviews'] / a['A']['reviews']:.1%}")
    v["V6 combined v1"] = dict(value="; ".join(txt), verdict=combine(vs))

    # v1 re-report of H1-H4, G1-G3 on T1
    a = T1["V6-v1"]
    g, t = a["h1"]
    rem = 1 - a["reviews"] / T1["A"]["reviews"]
    rep = {
        "H1": f"{g}/{t} = {g / t:.1%} promotions good" + (" PASS" if g / t >= .8 else " FAIL"),
        "H2": f"reviews removed {rem:.1%}; esc {a['esc_per100_auto']:.2f}/100 auto" +
              (" PASS" if rem >= .4 and a["esc_per100_auto"] <= 1 else " FAIL"),
        "H3": f"v1/B-matched escapes = {a['escapes'] / T1['B-matched-v1']['escapes']:.2f}" +
              (" PASS" if a["escapes"] / T1["B-matched-v1"]["escapes"] <= .5 else " FAIL"),
        "H4": f"median {a['reg_latency_median']} actions ({a['reg_detected50']}/{a['reg_eligible']} ≤50)" +
              (" PASS" if (a["reg_latency_median"] or 99) <= 20 else " FAIL"),
        "G1": f"review minutes −{rem:.1%}; detected ≤50 {a['reg_detected50'] / max(1, a['reg_eligible']):.0%}" +
              (" PASS" if rem >= .4 and a["reg_detected50"] / max(1, a["reg_eligible"]) >= .9 else " FAIL"),
        "G2": f"ledger complete {a['ledger_complete']:.0%}" + (" PASS" if a["ledger_complete"] == 1 else " FAIL"),
        "G3": f"auto after L1-incident {a['auto_after_incident_L1']:.0f}; incidents leaving the type autonomous "
              f"(L3→L2) {a['incidents_left_autonomous']:.2f}/world" + (" PASS" if a["auto_after_incident_L1"] == 0 else " FAIL"),
    }
    out = dict(verdicts=v, v1_rereport_T1=rep, tiers=tiers, carryover=co)
    (ROOT / "report/verdicts-v1.json").write_text(json.dumps(out, indent=1, default=str))
    for k, x in v.items():
        print(f"{k:24} {x['verdict']:7} {x['value']}")
    print("--- v1 on T1:")
    for k, x in rep.items():
        print(f"  {k}: {x}")


if __name__ == "__main__":
    main()
