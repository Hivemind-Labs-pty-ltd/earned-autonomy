"""T1: run every policy over seeded simulated worlds and score against the true errors.

    python -m t1.run [n_worlds]   -> report/raw/t1-results.json
"""
from __future__ import annotations

import json
import random
import statistics as st
import sys
from pathlib import Path

from gym.engine import PolicyConfig, Reviewer, ledger_complete, no_auto_after_incident, run_stream
from t1.world import REGRESSIONS, make_world

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "report/raw"

ARMS = {
    "A": dict(kind="A"),
    "B": dict(kind="B"),
    "C": dict(kind="C"),
    "D": dict(kind="D"),
    "D-agent": dict(kind="D", granularity="agent"),
    "D-startL2": dict(kind="D", start_level=2),
    "D-soft": dict(kind="D", hard_demotion=False),
    "D-nocanary": dict(kind="D", canary_rate=0.0),
}


def boot_ci(xs, n=2000, seed=0):
    xs = [x for x in xs if x is not None]
    if not xs:
        return (None, None, None)
    rng = random.Random(seed)
    means = sorted(st.fmean(rng.choices(xs, k=len(xs))) for _ in range(n))
    return (st.fmean(xs), means[int(.025 * n)], means[int(.975 * n)])


def run_world(seed: int, world_kw=None, reviewer_kw=None, arms=ARMS, cfg_over=None):
    actions, keys = make_world(seed, **(world_kw or {}))
    out = {}
    for name, kw in arms.items():
        cfg = PolicyConfig(**{**kw, **(cfg_over or {})})
        rv = Reviewer(random.Random(seed * 31 + 1), **(reviewer_kw or {}))
        e = run_stream(actions, cfg, seed=seed * 17 + 3, reviewer=rv)
        s = e.summary()
        s["ledger_complete"] = ledger_complete(e) if cfg.kind in ("C", "D") else None
        s["auto_after_incident"] = no_auto_after_incident(e) if cfg.kind in ("C", "D") else None
        if name == "D":
            s.update(promotion_metrics(e, keys, cfg.eps))
        if name in ("D", "D-soft"):
            s.update(regression_metrics(e, keys))
        out[name] = s
    # B-matched: same automation as D
    flag_rate = sum(a.check_flag for a in actions) / len(actions)
    a_d = out["D"]["automation"]
    hold = max(0.0, 1 - a_d / max(1e-9, 1 - flag_rate))
    rv = Reviewer(random.Random(seed * 31 + 1), **(reviewer_kw or {}))
    e = run_stream(actions, PolicyConfig(kind="Bm", hold_p=hold, **(cfg_over or {})), seed=seed * 17 + 3,
                   reviewer=rv)
    out["B-matched"] = e.summary()
    return out


def promotion_metrics(e, keys, eps):
    """H1: true error rate over the key's next 200 own actions after each promotion to L2+."""
    good, total = 0, 0
    for p in e.promotions:
        if p["to"] < 2:
            continue
        rates = keys[p["key"]]["rates"][p["type_i"]: p["type_i"] + 200]
        if len(rates) < 50:
            continue
        total += 1
        good += st.fmean(rates) <= eps
    return {"h1_promotions": total, "h1_good": good}


def regression_metrics(e, keys):
    """H4 / G1: from the regression point (key's own index) to the first demotion, for keys at L2+ then."""
    lat = []
    detected, eligible = 0, 0
    for k, ks in keys.items():
        if ks["pattern"] not in REGRESSIONS or ks["i0"] is None:
            continue
        # level at the regression point = last level change before it
        changes = sorted(e.promotions + e.demotions, key=lambda r: r["t"])
        lvl = 1
        for c in changes:
            if c["key"] == k and c["type_i"] <= ks["i0"]:
                lvl = c["to"]
        if lvl < 2:
            continue
        eligible += 1
        after = [d["type_i"] - ks["i0"] for d in e.demotions if d["key"] == k and d["type_i"] > ks["i0"]]
        if after:
            lat.append(min(after))
            detected += min(after) <= 50
    return {"reg_eligible": eligible, "reg_detected50": detected, "reg_latencies": lat}


def aggregate(worlds):
    arms = worlds[0].keys()
    agg = {}
    for a in arms:
        rows = [w[a] for w in worlds]
        r = {}
        for f in ("automation", "reviews", "review_minutes", "escapes", "esc_per100", "esc_per100_auto",
                  "incidents", "reviewer_catch", "ledger_complete", "auto_after_incident"):
            vals = [x.get(f) for x in rows]
            if any(v is not None for v in vals):
                r[f] = boot_ci(vals)
        if a == "D":
            r["h1"] = (sum(x["h1_good"] for x in rows), sum(x["h1_promotions"] for x in rows))
        if a in ("D", "D-soft"):
            lats = [l for x in rows for l in x["reg_latencies"]]
            r["reg_eligible"] = sum(x["reg_eligible"] for x in rows)
            r["reg_detected50"] = sum(x["reg_detected50"] for x in rows)
            r["reg_latency_median"] = st.median(lats) if lats else None
            r["reg_n_demoted"] = len(lats)
        agg[a] = r
    return agg


def main(n=200):
    worlds = [run_world(s) for s in range(n)]
    res = {"main": aggregate(worlds)}
    # sensitivity sweeps (smaller n)
    sweeps = {
        "reviewer_lo_0.8": dict(reviewer_kw=dict(p_lo=0.80)),
        "checks_recall_0.5": dict(world_kw=dict(check_recall=0.5)),
        "checks_recall_0.9": dict(world_kw=dict(check_recall=0.9)),
        "eps_0.02": dict(cfg_over=dict(eps=0.02)),
        "eps_0.10": dict(cfg_over=dict(eps=0.10)),
        "n_min_60": dict(cfg_over=dict(n_min=60)),
    }
    res["sweeps"] = {}
    for name, kw in sweeps.items():
        ws = [run_world(10_000 + s, **kw) for s in range(min(n, 100))]
        res["sweeps"][name] = aggregate(ws)
    # forced-pattern worlds: does the supervised start pay when errors cluster early, and on steady agents?
    res["forced"] = {}
    for pat in ("early", "steady", "bad_update", "defector"):
        ws = [run_world(20_000 + s, world_kw=dict(force_pattern=pat)) for s in range(min(n, 100))]
        res["forced"][pat] = aggregate(ws)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "t1-results.json").write_text(json.dumps(res, indent=1, default=str))
    return res


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 200)
