"""Render the numbers section of REPORT-10x.md from report/verdicts-10x.json (prose is written by hand around it).

    python3 make_report_10x.py > report/report-10x-numbers.md
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
V = json.loads((ROOT / "report/verdicts-10x.json").read_text())
d, verdicts = V["detail"], V["verdicts"]


def pct(x, nd=1):
    return "—" if x is None or x != x else f"{100 * x:.{nd}f}%"


def pts(x):
    return "—" if x is None or x != x else f"{100 * x:+.1f}"


print("## Verdicts\n")
print("| # | Result | Verdict |\n|---|---|---|")
for k in ("X1", "X3", "X6", "X8"):
    parts = []
    for v, x in d[k].items():
        if x["n"]:
            parts.append(f"{v}: {pct(x['rate_x'])} → {pct(x['rate_y'])} (diff {pts(x['diff'])} pts, CI "
                         f"{pts(x['lo'])}…{pts(x['hi'])}; n={x['n']})")
    print(f"| {k} | {' · '.join(parts)} | **{verdicts[k]}** |")
for k in ("X2", "X7"):
    parts = [f"{v}: reviews removed {pct(x['removed_lo'])} → {pct(x['removed_hi'])}, escapes/100 "
             f"{x['esc_lo']:.2f} → {x['esc_hi']:.2f}" for v, x in d[k].items()]
    print(f"| {k} | {' · '.join(parts)} | **{verdicts[k]}** |")

print("\n## Trust-policy reference metrics (v3 combined policy, 20 seeds)\n")
print("| Condition | Actions | Promotions deserved | Reviews removed | Done alone | Escapes/100 auto | "
      "Escapes/100 all (vs review-everything) | Cost-weighted/100 | Explained |")
print("|---|--:|--:|--:|--:|--:|--:|--:|--:|")
for k, r in d["reference"].items():
    h = r["h1"]
    print(f"| {k} | {r['n_actions']} | {pct(h[2])} ({h[0]}/{h[1]}) | {pct(r['removed'])} | {pct(r['automation'])} | "
          f"{r['esc100_auto']:.2f} | {r['esc100']:.2f} vs {r['esc100_A']:.2f} | {r['cost100']:.2f} | {pct(r['g2'], 0)} |")

print("\n## Cost and latency per task (X4)\n")
print("| Condition | n | USD / task | p50 s | p95 s | Errored (excluded) |\n|---|--:|--:|--:|--:|--:|")
for k, c in d["X4"].items():
    print(f"| {k} | {c['n']} | ${c['usd_per_task']:.5f} | {c.get('p50_s', '—')} | {c.get('p95_s', '—')} | "
          f"{d['errors'].get(k, '—')} |")

print("\n## Gate behaviour (X5)\n")
print("| Condition | Leak rewrite | Checks rewrite | Checks hold | Checks suppress | Compliance rewrite | "
      "Compliance hold | Repair success | Gate recall | Gate FPR |")
print("|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|")
for k, g in d["X5"].items():
    print(f"| {k} | {pct(g['leak_rewrite'])} | {pct(g['checks_rewrite'])} | {pct(g['checks_hold'])} | "
          f"{pct(g['checks_suppress'])} | {pct(g['compliance_rewrite'])} | {pct(g['compliance_hold'])} | "
          f"{pct(g['repair_success'])} | {pct(g['gate_recall'])} | {pct(g['gate_fpr'])} |")
print("\nA's T2 deterministic checks for comparison: recall 10.0% / FPR 0.7% (good), 27.0% / 0.4% (sloppy).")

print("\n## Knowledge lookup (X8 detail)\n")
print("| Condition | read_knowledge / task | Tasks with no read | Serious-error rate with a read | without |")
print("|---|--:|--:|--:|--:|")
for k, s in d["kb"].items():
    print(f"| {k} | {s['reads_per_task']:.2f} | {pct(s['share_no_read'])} | {pct(s['err_with_read'])} "
          f"(n={s['n_with']}) | {pct(s['err_without_read'])} (n={s['n_without']}) |")

print("\n## D learning loop\n")
print("| Archetype | Versions | Version changes carried over | Last hidden suite (n, pass) | First-cycle → last-cycle error |")
print("|---|--:|--:|--:|--:|")
for k, L in d["D_loop"].items():
    vs = L["versions"]
    changes = [x for n, x in vs.items() if n != "v1"]
    carried = sum(1 for x in changes if x.get("carried"))
    last = changes[-1] if changes else {}
    log = L["log"]
    first, lastc = (log[0]["err"], log[-1]["err"]) if log else (None, None)
    print(f"| {k} | {len(vs)} | {carried}/{len(changes)} | {last.get('suite_n', '—')}, {pct(last.get('hidden_pass'))} | "
          f"{pct(first)} → {pct(lastc)} |")
