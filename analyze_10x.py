"""Score PREREG-10x (X1-X8) and the v3 trust-policy reference metrics per condition. Writes report/verdicts-10x.json.

    python3 analyze_10x.py [--smoke]
"""
from __future__ import annotations

import argparse
import json
import random
import statistics as st
from pathlib import Path

from analyze_v2 import rev, t2_actions
from analyze_v3 import COMBINED, BASE
from gym.engine_v2 import CONS
from gym.engine_v3 import ConfigV3, ledger_complete, run_v3

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "report/raw/t2-runs"
ARCHS = ("cs", "ws", "it", "ap", "of", "do")
SEEDS = range(100, 120)
A_CHECKS = {"good": (0.10, 0.007), "sloppy": (0.27, 0.004)}   # T2 recall / FPR, PREREG-10x X5


def rows_of(path):
    out = {}
    if path.exists():
        for l in path.read_text().splitlines():
            r = json.loads(l)
            if "error" not in r:
                out[r["task_id"]] = r
    return out


def load_cond(cond, v, tag=""):
    if cond == "A":
        return rows_of(RUNS / f"{v}-full.jsonl")
    if cond in ("B", "C"):
        return rows_of(RUNS / f"10x-{cond}-{v}.jsonl")
    out = {}
    for arch in ARCHS:
        for p in sorted(RUNS.glob(f"10x-D-{v}-{arch}{tag}-c*.jsonl")):
            out.update(rows_of(p))
    return out


def errors_all(cond, v, tag=""):
    """Rows that errored (turn failed / exception) — reported, not scored."""
    n = 0
    paths = ([RUNS / f"10x-{cond}-{v}.jsonl"] if cond in ("B", "C")
             else [p for a in ARCHS for p in RUNS.glob(f"10x-D-{v}-{a}{tag}-c*.jsonl")])
    for p in paths:
        if p.exists():
            ids_ok = set(rows_of(p))
            errs = {json.loads(l)["task_id"] for l in p.read_text().splitlines() if "error" in json.loads(l)}
            n += len(errs - ids_ok)
    return n


def paired(x, y, n=2000, seed=0):
    """x, y: dicts task_id -> row. Returns rate_x, rate_y, diff (y-x) mean and 95% CI, n paired."""
    ids = sorted(set(x) & set(y))
    d = [int(y[i]["serious"]) - int(x[i]["serious"]) for i in ids]
    rx = st.fmean(int(x[i]["serious"]) for i in ids) if ids else float("nan")
    ry = st.fmean(int(y[i]["serious"]) for i in ids) if ids else float("nan")
    if not d:
        nan = float("nan")
        return dict(rate_x=nan, rate_y=nan, diff=nan, lo=nan, hi=nan, n=0, rel=nan)
    rng = random.Random(seed)
    ms = sorted(st.fmean(rng.choices(d, k=len(d))) for _ in range(n))
    return dict(rate_x=rx, rate_y=ry, diff=st.fmean(d), lo=ms[int(.025 * n)], hi=ms[int(.975 * n)], n=len(ids),
                rel=(1 - ry / rx) if rx else float("nan"))


def three(vs):
    if not vs:
        return "INCONCLUSIVE"
    return "PASS" if all(vs) else ("FAIL" if not any(vs) else "MIXED")


def version_pass_of(acts):
    """(agent, version, task_type) -> hidden pass, None when the suite is under the SPEC minimum (=> discount)."""
    vp = {}
    for a in acts:
        hp, n = a.meta.get("hidden_pass"), a.meta.get("suite_n") or 0
        vp[(a.agent, a.version, a.task_type)] = hp if (hp is not None and n >= 10) else None
    return vp


def ref(stream):
    """v3 combined policy vs review-everything on one stream (REPORT-v3 reference table metrics)."""
    acts = t2_actions(stream)
    vp = version_pass_of(acts)
    seq = {}
    for a in acts:
        seq.setdefault((a.agent, a.task_type), []).append(a.true_err)
    runs = []
    for s in SEEDS:
        e = run_v3(acts, ConfigV3(**{**COMBINED, "version_pass": vp}), seed=s * 17 + 3, reviewer=rev(s))
        a0 = run_v3(acts, ConfigV3(kind="A", **BASE), seed=s * 17 + 3, reviewer=rev(s))
        sm, sa = e.summary(), a0.summary()
        good = total = 0
        for p in e.promotions:
            if p["to"] < 2:
                continue
            nxt = seq[p["key"]][p["type_i"]: p["type_i"] + 200]
            if len(nxt) < 50:
                continue
            cons = next(x.meta["cons"] for x in acts if (x.agent, x.task_type) == p["key"])
            total += 1
            good += st.fmean(nxt) <= CONS[cons]["eps"]
        runs.append(dict(removed=1 - sm["reviews"] / sa["reviews"], automation=sm["automation"],
                         esc100=sm["esc_per100"], esc100_auto=sm["esc_per100_auto"], cost100=sm["cost_per100"],
                         esc100_A=sa["esc_per100"], g2=ledger_complete(e), h1=(good, total)))
    out = {f: st.fmean(r[f] for r in runs) for f in ("removed", "automation", "esc100", "esc100_auto", "cost100",
                                                       "esc100_A", "g2")}
    g, t = sum(r["h1"][0] for r in runs), sum(r["h1"][1] for r in runs)
    out["h1"] = [g, t, g / t if t else None]
    out["n_actions"] = len(acts)
    return out


def gate_stats(rows, v):
    rs = list(rows.values())
    n = max(1, len(rs))
    first = [r["attempts"][0] for r in rs if r.get("attempts")]
    def rate(pred):
        return sum(1 for a in first if pred(a)) / n
    rewritten = [r for r in rs if any(a["route"] == "rewrite" for a in r.get("attempts") or [])]
    pos = [r for r in rs if r["serious"]]
    neg = [r for r in rs if not r["serious"]]
    return dict(
        leak_rewrite=rate(lambda a: a["stage"] == "leak_gate"),
        checks_rewrite=rate(lambda a: a["stage"] == "checks" and a["route"] == "rewrite"),
        checks_hold=rate(lambda a: a["stage"] == "checks" and a["route"] == "hold"),
        checks_suppress=rate(lambda a: a["stage"] == "checks" and a["route"] == "suppress"),
        compliance_rewrite=rate(lambda a: a["stage"] == "compliance" and a["route"] == "rewrite"),
        compliance_hold=rate(lambda a: a["stage"] == "compliance" and a["route"] == "hold"),
        any_rewrite=len(rewritten) / n,
        repair_success=(sum(r["final_route"] == "send" for r in rewritten) / len(rewritten)) if rewritten else None,
        final_send=sum(r["final_route"] == "send" for r in rs) / n,
        gate_recall=(sum(r["check_flag"] for r in pos) / len(pos)) if pos else None,
        gate_fpr=(sum(r["check_flag"] for r in neg) / len(neg)) if neg else None,
        a_t2_checks_recall_fpr=A_CHECKS[v])


def kb_stats(rows):
    rs = list(rows.values())
    reads = [len(r.get("kb_reads") or []) for r in rs]
    no = [r for r in rs if not r.get("kb_reads")]
    yes = [r for r in rs if r.get("kb_reads")]
    return dict(reads_per_task=st.fmean(reads) if reads else None, share_no_read=len(no) / max(1, len(rs)),
                err_with_read=st.fmean(r["serious"] for r in yes) if yes else None,
                err_without_read=st.fmean(r["serious"] for r in no) if no else None, n_with=len(yes), n_without=len(no))


def cost_latency(rows):
    rs = list(rows.values())
    if not rs:
        return {}
    secs = sorted(r["seconds"] for r in rs if r.get("seconds") is not None)
    out = dict(usd_per_task=st.fmean(r.get("cost", 0) for r in rs), n=len(rs))
    if secs:
        out.update(p50_s=secs[len(secs) // 2], p95_s=secs[int(.95 * (len(secs) - 1))])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    tag = "-smoke" if args.smoke else ""
    data = {(c, v): load_cond(c, v, tag) for c in "ABCD" for v in ("good", "sloppy")}
    if args.smoke:      # restrict A/B/C to the tasks the smoke covered
        for v in ("good", "sloppy"):
            ids = set(data[("D", v)]) | set(data[("C", v)]) | set(data[("B", v)])
            data[("A", v)] = {k: r for k, r in data[("A", v)].items() if k in ids}
    V, detail = {}, {}
    # X1: C vs A
    x1 = {v: paired(data[("A", v)], data[("C", v)]) for v in ("good", "sloppy")}
    V["X1"] = three([x["rel"] >= .25 and x["hi"] < 0 for x in x1.values() if x["n"]])
    # X3: B vs A equivalence
    x3 = {v: paired(data[("A", v)], data[("B", v)]) for v in ("good", "sloppy")}
    m3 = {"good": .015, "sloppy": .03}
    V["X3"] = three([x3[v]["lo"] >= -m3[v] and x3[v]["hi"] <= m3[v] for v in x3 if x3[v]["n"]])
    # X6: D vs C
    x6 = {v: paired(data[("C", v)], data[("D", v)]) for v in ("good", "sloppy")}
    V["X6"] = three([x["rel"] >= .25 and x["hi"] < 0 for x in x6.values() if x["n"]])
    # X8: C not higher than A
    m8 = {"good": .01, "sloppy": .02}
    V["X8"] = three([x1[v]["hi"] <= m8[v] for v in x1 if x1[v]["n"]])
    detail.update(X1=x1, X3=x3, X6=x6, X8={v: dict(x1[v], margin=m8[v]) for v in x1})
    # trust-policy reference metrics per condition (streams must exist)
    refs = {}
    names = {"A": "{v}-full", "B": "10x-B-{v}" + tag, "C": "10x-C-{v}" + tag, "D": "10x-D-{v}" + tag}
    for c, pat in names.items():
        for v in ("good", "sloppy"):
            stream = pat.format(v=v)
            if (ROOT / f"report/raw/t2-stream-{stream}.jsonl").exists():
                refs[f"{c}-{v}"] = ref(stream)
    detail["reference"] = refs
    # X2 (C vs A) and X7 (D vs C) under the trust policy
    def trust_cmp(lo, hi):
        out, oks = {}, []
        for v in ("good", "sloppy"):
            a, b = refs.get(f"{lo}-{v}"), refs.get(f"{hi}-{v}")
            if not a or not b:
                continue
            d_removed = b["removed"] - a["removed"]
            ok = d_removed >= .05 and b["esc100"] <= a["esc100"] + .05
            out[v] = dict(removed_lo=a["removed"], removed_hi=b["removed"], d_removed=d_removed,
                          esc_lo=a["esc100"], esc_hi=b["esc100"], ok=ok)
            oks.append(ok)
        return out, (three(oks) if oks else "INCONCLUSIVE")
    detail["X2"], V["X2"] = trust_cmp("A", "C")
    detail["X7"], V["X7"] = trust_cmp("C", "D")
    # X4 cost + latency, X5 gate, kb
    detail["X4"] = {f"{c}-{v}": cost_latency(data[(c, v)]) for c in "ABCD" for v in ("good", "sloppy") if data[(c, v)]}
    detail["X5"] = {f"{c}-{v}": gate_stats(data[(c, v)], v) for c in "CD" for v in ("good", "sloppy") if data[(c, v)]}
    detail["kb"] = {f"{c}-{v}": kb_stats(data[(c, v)]) for c in "CD" for v in ("good", "sloppy") if data[(c, v)]}
    detail["errors"] = {f"{c}-{v}": errors_all(c, v, tag) for c in "BCD" for v in ("good", "sloppy")}
    detail["n"] = {f"{c}-{v}": len(data[(c, v)]) for c in "ABCD" for v in ("good", "sloppy")}
    # D loop per-version log
    loops = {}
    for v in ("good", "sloppy"):
        for arch in ARCHS:
            p = ROOT / f"report/raw/t2x-loop-{arch}-{v}{tag}.json"
            if p.exists():
                s = json.loads(p.read_text())
                loops[f"{arch}-{v}"] = dict(versions={k: {kk: vv for kk, vv in i.items() if kk != "rules"}
                                                      | {"n_rules": len(i["rules"])} for k, i in s["versions"].items()},
                                            log=s["log"])
    detail["D_loop"] = loops
    out = dict(verdicts=V, detail=detail)
    (ROOT / f"report/verdicts-10x{tag}.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(V))
    for k in ("X1", "X3", "X6"):
        for v, x in detail[k].items():
            print(k, v, f"n={x['n']} rate_lo={x['rate_x']:.3f} rate_hi={x['rate_y']:.3f} diff={x['diff']:+.3f} "
                        f"[{x['lo']:+.3f},{x['hi']:+.3f}] rel={x['rel']:.2f}")
    for k, r in refs.items():
        print("ref", k, {f: (round(x, 3) if isinstance(x, float) else x) for f, x in r.items()})


if __name__ == "__main__":
    main()
