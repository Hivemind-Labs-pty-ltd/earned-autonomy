"""Turn T2 run files into engine streams (report/raw/t2-stream-<variant>.jsonl).

One row per action, in an interleaved "organisation's day" order (seeded shuffle across archetypes,
each archetype's tasks kept in their own order). Each archetype is a separate agent.

    python -m t2.streams
"""
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "report/raw/t2-runs"
TASKS = ROOT / "report/raw/t2-tasks.jsonl"


def day_order(task_ids):
    """Interleave archetypes: draw the next task from a random archetype, keeping each archetype's order."""
    by_arch = {}
    for tid in task_ids:
        by_arch.setdefault(tid.split("-")[0], []).append(tid)
    for v in by_arch.values():
        v.sort()
    rng = random.Random(1015)
    out = []
    while any(by_arch.values()):
        arch = rng.choice([a for a, v in by_arch.items() if v])
        out.append(by_arch[arch].pop(0))
    return out


def row(r, agent, version, cycle=None):
    return dict(agent=agent, task_type=f"{r['arch']}:{r['ttype']}", true_err=bool(r["serious"]),
                check_flag=bool(r["check_flag"]), version=version, capped=bool(r["capped"]),
                counterparty=r["counterparty"],
                meta=dict(task_id=r["task_id"], reasons=r["reasons"], tool_calls_wrong=r["tool_calls_wrong"],
                          n_calls=r["n_calls"], task_success=r["success"], cycle=cycle, risk=r["risk"],
                          traps=r["traps"]))


def load(name):
    p = RUNS / f"{name}.jsonl"
    if not p.exists():
        return {}
    out = {}
    for l in p.read_text().splitlines():
        r = json.loads(l)
        if "error" not in r:
            out[r["task_id"]] = r
    return out


def write(name, rows):
    p = ROOT / f"report/raw/t2-stream-{name}.jsonl"
    p.write_text("\n".join(json.dumps(x) for x in rows) + "\n")
    print(f"{p.name}: {len(rows)} rows, err rate {sum(x['true_err'] for x in rows) / max(1, len(rows)):.3f}")


def main():
    for variant in ("good-full", "sloppy-full", "good-scoped"):
        runs = load(variant)
        if runs:
            write(variant, [row(runs[t], f"{runs[t]['arch']}-{variant}", "v1") for t in day_order(list(runs))])
    # learning loop: per-archetype cycle files, version per cycle
    loop = {}
    for p in sorted(RUNS.glob("loop-*-v*.jsonl")):
        if "-test-" in p.stem:
            continue
        _, arch, v = p.stem.split("-")
        for tid, r in load(p.stem).items():
            loop[tid] = (r, v)
    if loop:
        write("loop", [row(loop[t][0], f"{loop[t][0]['arch']}-loop", loop[t][1], int(loop[t][1][1:]))
                       for t in day_order(list(loop))])
        # the frozen comparison on exactly the same tasks
        frozen = load("sloppy-full")
        write("noloop", [row(frozen[t], f"{frozen[t]['arch']}-noloop", "v1") for t in day_order(list(loop)) if t in frozen])


if __name__ == "__main__":
    main()
