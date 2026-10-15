"""Print T2 headline raw rates (no hypothesis verdicts; those come from the engine).

    python -m t2.summary > report/t2-raw-summary.txt
"""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "report/raw"


def load(name):
    p = RAW / "t2-runs" / f"{name}.jsonl"
    return [r for r in map(json.loads, p.read_text().splitlines()) if "error" not in r] if p.exists() else []


def rate(rows, f="serious"):
    return sum(bool(r[f]) for r in rows) / max(1, len(rows))


def main():
    print("# T2 raw summary\n")
    for v in ("good-full", "sloppy-full", "good-scoped"):
        R = load(v)
        if not R:
            continue
        s = sum(r["serious"] for r in R)
        tp = sum(r["serious"] and r["check_flag"] for r in R)
        fp = sum((not r["serious"]) and r["check_flag"] for r in R)
        print(f"## {v}  n={len(R)}  cost=${sum(r['cost'] for r in R):.2f}")
        print(f"serious={rate(R):.4f} (strict grader {rate(R, 'serious_strict'):.4f})  task_success={rate(R, 'success'):.3f}"
              f"  followed_injection={sum(r['injected'] for r in R)}  check recall={tp / max(1, s):.3f}"
              f"  check FPR={fp / max(1, len(R) - s):.4f}")
        for f in ("arch", "risk", "counterparty"):
            d = defaultdict(list)
            for r in R:
                d[r[f]].append(r["serious"])
            print(f"  by {f}: " + ", ".join(f"{k} {sum(x) / len(x):.3f} (n={len(x)})" for k, x in sorted(d.items())))
        print()
    # L1: same 1,800 tasks
    G, SC = load("good-full"), load("good-scoped")
    ids = {r["task_id"] for r in SC}
    Gs = [r for r in G if r["task_id"] in ids]
    if SC:
        print("## L1 least scope (same 1,800 tasks, good agent)")
        for nm, R in (("full", Gs), ("scoped", SC)):
            print(f"{nm}: wrong_or_unneeded_tool_calls/task={sum(r['tool_calls_wrong'] for r in R) / len(R):.3f}"
                  f"  calls/task={sum(r['n_calls'] for r in R) / len(R):.2f}  success={rate(R, 'success'):.3f}"
                  f"  serious={rate(R):.4f}")
        print()
    # loop
    rows = []
    for p in sorted(RAW.glob("t2-loop-??.jsonl")):
        rows += [json.loads(l) for l in p.read_text().splitlines()]
    if rows:
        print("## Learning loop (sloppy agent; 100 fresh tasks per version per archetype)")
        print("arch version n_rules true_err train_pass(n) hidden_pass(n)")
        for o in rows:
            print(f"{o['arch']} {o['version']} {o['n_rules']} {o['true_err']:.3f} "
                  f"{o.get('train_pass', float('nan')):.2f}({o.get('train_n', 0)}) "
                  f"{o.get('hidden_pass', float('nan')):.2f}({o.get('hidden_n', 0)})")
        print()
    # reviewers
    p = RAW / "t2-reviewers.jsonl"
    if p.exists():
        R = [json.loads(l) for l in p.read_text().splitlines()]
        print("## Reviewer agents (300 outputs, ~1/3 serious after re-grading)")
        for k in ("same", "different"):
            X = [d for d in R if d["reviewer"] == k]
            pos = [d for d in X if d["truth_serious"]]
            neg = [d for d in X if not d["truth_serious"]]
            print(f"{k} ({X[0]['model']}): n={len(X)} recall={sum(d['flag'] for d in pos) / len(pos):.3f}"
                  f" FPR={sum(d['flag'] for d in neg) / len(neg):.3f} unparsed={sum(not d['parsed'] for d in X)}")
        print()
    spend = sum(json.loads(l)["usd"] for l in (RAW / "t2-spend.jsonl").read_text().splitlines())
    print(f"T2 ledger spend (all calls incl. discarded/restarted runs): ${spend:.2f}")


if __name__ == "__main__":
    main()
