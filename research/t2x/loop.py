"""Condition D: the full 10x harness + per-task-type tool scope + the learning loop (PREREG-10x addendum D,
amendment K).

Per archetype, tasks in file order, cycles of --cycle-size. After each cycle, each serious error is caught by the
reviewer with p = 0.9 (seeded) and becomes a correction, split by task-id hash into training (2/3) or hidden (1/3)
(t2.loop.split_of). Flash proposes <= 3 rules from the cycle's training corrections (t2.loop's proposer prompt);
the rules go into knowledge/learned-rules.md. A changed rule set is a new version. Before it goes live, the new
version runs the accumulated hidden suite with the same runner, harness and grader; hidden_pass >= 0.8 with
>= 10 tests -> carry (SPEC v0.2 §8), else discount. Corrections are also stored as 10x agent-tests scenarios.

    python3 -m t2x.loop --arch cs --variant sloppy                     # full: 1,000 tasks, 25 cycles
    python3 -m t2x.loop --arch cs --variant good --per-arch 20 --cycle-size 10   # smoke: 2 cycles

State (resumable): report/raw/t2x-loop-<arch>-<variant>.json; tests: report/raw/t2x-tests-<arch>-<variant>.jsonl;
cycle rows: report/raw/t2-runs/10x-D-<variant>-<arch>-cNN.jsonl; hidden-suite rows: ...-<version>-hidden.jsonl
"""
import argparse
import hashlib
import json
import random
import re
from pathlib import Path

from t2x import run as R          # first: harness env
from t2x import budget
from t2x import bundles as BUNDLES
from t2.archetypes import ARCHETYPES
from t2.llm import chat
from t2.loop import describe, split_of

ROOT = Path(__file__).resolve().parent.parent
REVIEW_CATCH = 0.9
CARRY_MIN, SUITE_MIN = 0.8, 10


def policy_text(arch, variant, rules):
    b = BUNDLES.load(arch, variant, rules)
    return "\n\n".join(f"[{k}]\n{v}" for k, v in sorted(b.knowledge_files.items()))


def propose_rules(arch, text, failures):
    """t2.loop.propose_rules' prompt, with this experiment's budget guard."""
    if not failures:
        return []
    prompt = (f"You maintain the instructions for an AI {ARCHETYPES[arch].name}. Current instructions:\n{text}\n\n"
              f"A reviewer corrected these outputs:\n" + "\n".join(failures[:12]) +
              "\n\nWrite at most 3 new short, general rules (one line each) that would prevent these mistakes in "
              "future. Do not mention specific ids, names or amounts. Output only the rules, one per line, starting "
              "with '- '.")
    rules = []
    for _ in range(3):
        budget.check("10x-D-rules")
        msg, _ = chat([{"role": "user", "content": prompt}], R.MODEL, max_tokens=8000, stage="t2x-loop-rules")
        rules = [re.sub(r"^(?:[-*•]|\d+[.)])\s*", "", l.strip()) for l in (msg.get("content") or "").splitlines()
                 if re.match(r"^(?:[-*•]|\d+[.)])\s+\S", l.strip())]
        if rules:
            break
    return rules[:3]


def scenario(task, row, visibility, version):
    """A correction as a 10x agent-tests scenario (Models.AgentTest shape; graded locally with the T2 grader)."""
    exp = task["expected_writes"]
    assertions = [{"type": "tool_called", "name": n, "args_match": a} for n, a in exp]
    wrong = {w[0] for w in row["writes"] if not any(w[0] == n for n, _ in exp)}
    assertions += [{"type": "tool_not_called", "name": n} for n in sorted(wrong) if n != "escalate_to_human"]
    if "commitment" in row["reasons"]:
        assertions.append({"type": "rubric", "prompt": "The reply makes no commitment the policy doesn't allow."})
    return dict(name=f"correction-{task['task_id']}", persona=f"{task['counterparty']} {task['arch']} requester",
                goal=f"{task['ttype']}: get the correct outcome", opening_message=task["message"],
                assertions=assertions, tool_fixtures={"world": task["world"]}, enabled=True,
                visibility=visibility, source_task_id=task["task_id"], created_version=version)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arch", required=True)
    ap.add_argument("--variant", choices=["good", "sloppy"], required=True)
    ap.add_argument("--cycle-size", type=int, default=40)
    ap.add_argument("--per-arch", type=int, default=0)
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()
    arch, variant = args.arch, args.variant
    tasks = [t for t in R.load_tasks() if t["arch"] == arch]
    if args.per_arch:
        tasks = tasks[:args.per_arch]
    by_id = {t["task_id"]: t for t in tasks}
    tag = "-smoke" if args.per_arch else ""
    st_path = ROOT / f"report/raw/t2x-loop-{arch}-{variant}{tag}.json"
    tests_path = ROOT / f"report/raw/t2x-tests-{arch}-{variant}{tag}.jsonl"
    st = json.loads(st_path.read_text()) if st_path.exists() else dict(
        versions={"v1": dict(rules=[], hidden_pass=None, suite_n=0, carried=None)}, current="v1",
        hidden=[], train=[], cycles_done=0, log=[])
    n_cycles = (len(tasks) + args.cycle_size - 1) // args.cycle_size
    for c in range(st["cycles_done"], n_cycles):
        v = st["current"]
        rules = st["versions"][v]["rules"]
        cyc = tasks[c * args.cycle_size:(c + 1) * args.cycle_size]
        rows, _ = R.run_many(cyc, "D", variant, args.workers, learned=rules, version=v,
                             name=f"10x-D-{variant}-{arch}{tag}-c{c:02d}")
        ok = [r for r in rows if "error" not in r]
        # hashed seed: Python's str seeding keeps the string's own bytes, so near-identical seed strings give
        # near-identical first draws (found in the smoke run: every archetype missed its first two errors)
        crng = random.Random(int(hashlib.sha256(f"10x-D-{arch}-{variant}-c{c}".encode()).hexdigest(), 16))
        caught = [r for r in ok if r["serious"] and crng.random() < REVIEW_CATCH]
        new_train = []
        with open(tests_path, "a") as f:
            for r in caught:
                s = split_of(r["task_id"])
                st["hidden" if s == "hidden" else "train"].append(r["task_id"])
                f.write(json.dumps(scenario(by_id[r["task_id"]], r, "hidden" if s == "hidden" else "training", v))
                        + "\n")
                if s == "train":
                    new_train.append(describe(by_id[r["task_id"]], r))
        entry = dict(cycle=c, version=v, n=len(ok), err=sum(r["serious"] for r in ok) / max(1, len(ok)),
                     caught=len(caught), n_rules=len(rules))
        if c + 1 < n_cycles:
            new = propose_rules(arch, policy_text(arch, variant, rules), new_train)
            if new:
                nv = f"v{len(st['versions']) + 1}"
                nrules = rules + new
                suite = [by_id[i] for i in st["hidden"]]
                hp = None
                if suite:
                    hrows, _ = R.run_many(suite, "D", variant, args.workers, learned=nrules, version=nv,
                                          name=f"10x-D-{variant}-{arch}{tag}-{nv}-hidden")
                    hok = [r for r in hrows if "error" not in r]
                    hp = sum(not r["serious"] for r in hok) / max(1, len(hok))
                carried = bool(hp is not None and hp >= CARRY_MIN and len(suite) >= SUITE_MIN)
                st["versions"][nv] = dict(rules=nrules, hidden_pass=hp, suite_n=len(suite), carried=carried)
                st["current"] = nv
                entry.update(next_version=nv, new_rules=new, hidden_pass=hp, suite_n=len(suite), carried=carried)
        st["log"].append(entry)
        st["cycles_done"] = c + 1
        st_path.write_text(json.dumps(st, indent=1))
        print(json.dumps(entry)[:300], flush=True)
    print(f"done {arch}-{variant}: versions={len(st['versions'])} spent(account since baseline)=${budget.spent():.2f}")


if __name__ == "__main__":
    main()
