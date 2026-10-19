"""E1b learning loop on the sloppy agent (H5-H7).

Per archetype: tasks are processed in cycles. Version v1 = the sloppy prompt. After each cycle the
serious errors a reviewer caught become corrections. Each correction is assigned (by hash) to the
TRAINING split (2/3) or the HIDDEN split (1/3). Flash proposes <= 3 rules from the training-split
failures only; the rules are appended to the prompt and the version number goes up.

At the end every version is evaluated on all training tests and all hidden tests.

    python -m t2.loop --cycles 6 --cycle-size 100
Outputs: report/raw/t2-loop.jsonl (per version), report/raw/t2-runs/loop-*.jsonl (raw), rules in
report/raw/t2-loop-rules.json
"""
import argparse
import re
import hashlib
import json
import random
from pathlib import Path

from t2 import budget
from t2.archetypes import ARCHETYPES
from t2.llm import chat
from t2.run_agent import MODEL, load_tasks, run_many

ROOT = Path(__file__).resolve().parent.parent
REVIEW_CATCH = 0.9


def split_of(task_id):
    return "hidden" if int(hashlib.sha1(task_id.encode()).hexdigest(), 16) % 3 == 0 else "train"


def describe(task, row):
    exp = task["expected_writes"] or "no write (decline, ask or explain)"
    return (f"- Task type {task['ttype']}. Request: {task['message'][:400]!r}\n"
            f"  Agent did: writes={row['writes']}; reply starts {row['reply'][:200]!r}\n"
            f"  Reviewer: wrong because {', '.join(row['reasons'])}. Correct action was: {exp}.")


def propose_rules(arch, policy_text, failures):
    if not failures:
        return []
    prompt = (f"You maintain the instructions for an AI {ARCHETYPES[arch].name}. Current instructions:\n{policy_text}\n\n"
              f"A reviewer corrected these outputs:\n" + "\n".join(failures[:12]) +
              "\n\nWrite at most 3 new short, general rules (one line each) that would prevent these mistakes in future. "
              "Do not mention specific ids, names or amounts. Output only the rules, one per line, starting with '- '.")
    rules = []
    for _ in range(3):   # flash can use the whole budget on reasoning and return no text; retry
        budget.check("loop-rules")
        msg, _ = chat([{"role": "user", "content": prompt}], MODEL, max_tokens=8000, stage="t2-loop-rules")
        rules = [re.sub(r"^(?:[-*•]|\d+[.)])\s*", "", l.strip()) for l in (msg.get("content") or "").splitlines()
                 if re.match(r"^(?:[-*•]|\d+[.)])\s+\S", l.strip())]
        if rules:
            break
    return rules[:3]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycles", type=int, default=6)
    ap.add_argument("--cycle-size", type=int, default=100)
    ap.add_argument("--arch", required=True)
    args = ap.parse_args()
    tasks = load_tasks()
    by_id = {t["task_id"]: t for t in tasks}
    rules_path = ROOT / f"report/raw/t2-loop-rules-{args.arch}.json"
    state = json.loads(rules_path.read_text()) if rules_path.exists() else {}
    out = []
    for ak in [args.arch]:
        mine = [t for t in tasks if t["arch"] == ak][: args.cycles * args.cycle_size]
        rules: list[str] = []
        versions = state.get(ak, {}).get("versions", {})
        tests = {"train": [], "hidden": []}
        rng = random.Random(f"loop-{ak}")
        for c in range(args.cycles):
            v = f"v{c + 1}"
            if v in versions:
                rules = versions[v]
            else:
                versions[v] = list(rules)
            cyc = mine[c * args.cycle_size:(c + 1) * args.cycle_size]
            rows = run_many(cyc, f"loop-{ak}-{v}", "sloppy", "full", {ak: rules})
            ok = [r for r in rows if "error" not in r]
            err_rate = sum(r["serious"] for r in ok) / max(1, len(ok))
            caught = [r for r in ok if r["serious"] and rng.random() < REVIEW_CATCH]
            new_train = []
            for r in caught:
                s = split_of(r["task_id"])
                tests[s].append(r["task_id"])
                if s == "train":
                    new_train.append(describe(by_id[r["task_id"]], r))
            out.append(dict(arch=ak, version=v, cycle=c + 1, n=len(ok), true_err=err_rate,
                            n_rules=len(rules), caught=len(caught)))
            print(f"{ak} {v}: n={len(ok)} err={err_rate:.3f} rules={len(rules)} caught={len(caught)}", flush=True)
            if c + 1 < args.cycles and f"v{c + 2}" not in versions:
                rules = rules + propose_rules(ak, ARCHETYPES[ak].policy("sloppy", rules), new_train)
        state[ak] = dict(versions=versions, tests=tests)
        rules_path.write_text(json.dumps(state, indent=1))
        # evaluate every version on all training and hidden tests
        for v, vr in versions.items():
            for split in ("train", "hidden"):
                ids = tests[split]
                if not ids:
                    continue
                rows = run_many([by_id[i] for i in ids], f"loop-{ak}-{v}-test-{split}", "sloppy", "full", {ak: vr})
                ok = [r for r in rows if "error" not in r]
                passed = sum((not r["serious"]) for r in ok) / max(1, len(ok))
                for o in out:
                    if o["arch"] == ak and o["version"] == v:
                        o[f"{split}_pass"] = passed
                        o[f"{split}_n"] = len(ok)
    (ROOT / f"report/raw/t2-loop-{args.arch}.jsonl").write_text("\n".join(json.dumps(o) for o in out) + "\n")
    print("wrote t2-loop.jsonl", f"spend ${budget.usage() - budget.BASELINE_USD:.2f}")


if __name__ == "__main__":
    main()
