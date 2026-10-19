"""Run an agent variant over T2 tasks, grade against seeded truth, run checks.

    python -m t2.run_agent --variant good --scope full
    python -m t2.run_agent --variant sloppy --scope full

Raw rows are cached in report/raw/t2-runs/<run_name>.jsonl keyed by task_id, so reruns resume.
"""
import argparse
import json
import random
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from t2 import budget
from t2.archetypes import ARCHETYPES, distractors_for, grade, run_checks
from t2.commit_grader import verdict as commit_verdict
from t2.llm import chat

ROOT = Path(__file__).resolve().parent.parent
TASKS = ROOT / "report/raw/t2-tasks.jsonl"
RUNS = ROOT / "report/raw/t2-runs"
MODEL = "deepseek/deepseek-v4-flash"
MAX_ROUNDS = 6
_lock = threading.Lock()


def load_tasks():
    return [json.loads(l) for l in TASKS.read_text().splitlines() if l.strip()]


def run_one(task, variant, scope, extra_rules=(), model=MODEL):
    a = ARCHETYPES[task["arch"]]
    rng = random.Random(task["task_id"])
    tools = a.tool_schemas(task["ttype"], scope, distractors_for(task["arch"], rng))
    exposed = {t["function"]["name"] for t in tools}
    needed = set(a.ttypes[task["ttype"]][2]) | {"escalate_to_human"}
    msgs = [{"role": "system", "content": a.policy(variant, extra_rules)},
            {"role": "user", "content": task["message"]}]
    writes, calls, cost = [], [], 0.0
    reply = ""
    for _ in range(MAX_ROUNDS):
        msg, u = chat(msgs, model, tools=tools, max_tokens=2500, stage=f"t2-{variant}-{scope}")
        cost += u["cost"]
        tcs = msg.get("tool_calls") or []
        if not tcs:
            reply = msg.get("content") or ""
            if not reply.strip():
                # flash sometimes stops after a tool round with no text; ask once for the reply
                msgs.append({"role": "user", "content": "Please write your final reply now."})
                msg, u = chat(msgs, model, max_tokens=2500, stage=f"t2-{variant}-{scope}")
                cost += u["cost"]
                reply = msg.get("content") or ""
            break
        msgs.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": tcs})
        for tc in tcs:
            name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            calls.append([name, args])
            if name not in exposed:
                res = {"error": "unknown tool"}
            elif name not in a.tools and name != "escalate_to_human":
                # distractor tool from another archetype: exists but does nothing useful here
                res = {"error": "this tool is not connected to this workspace"}
            else:
                res = a.execute(task, name, args, writes)
            msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(res)})
    else:
        reply = "(no final reply: tool round limit)"
    g = grade(task, writes, reply, commit_verdict=commit_verdict(reply))
    fired = run_checks(task, writes, reply)
    wrong = sum(1 for n, _ in calls if n not in needed) + sum(1 for r in g["reasons"] if r.startswith("unauthorised"))
    return dict(task_id=task["task_id"], arch=task["arch"], ttype=task["ttype"], risk=task["risk"], capped=task["capped"],
                counterparty=task["counterparty"], traps=task["traps"], variant=variant, scope=scope,
                n_extra_rules=len(extra_rules), writes=writes, calls=calls, reply=reply,
                serious=g["serious"], reasons=g["reasons"], success=g["success"], injected=g["injected"],
                checks=fired, check_flag=bool(fired), tool_calls_wrong=wrong, n_calls=len(calls), cost=cost)


def run_many(tasks, run_name, variant, scope, extra_rules_by_arch=None, workers=40):
    RUNS.mkdir(parents=True, exist_ok=True)
    path = RUNS / f"{run_name}.jsonl"
    done = {}
    if path.exists():
        for l in path.read_text().splitlines():
            r = json.loads(l)
            done[r["task_id"]] = r
    todo = [t for t in tasks if t["task_id"] not in done]

    def one(t):
        budget.check(run_name)
        extra = (extra_rules_by_arch or {}).get(t["arch"], ())
        try:
            r = run_one(t, variant, scope, extra)
        except budget.BudgetStop:
            raise
        except Exception as e:  # noqa: BLE001  record and move on; a crash is reported, not hidden
            r = dict(task_id=t["task_id"], error=str(e)[:300])
        with _lock:
            with open(path, "a") as f:
                f.write(json.dumps(r) + "\n")
        return r

    with ThreadPoolExecutor(workers) as ex:
        for r in ex.map(one, todo):
            done[r["task_id"]] = r
    return [done[t["task_id"]] for t in tasks if t["task_id"] in done]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="good")
    ap.add_argument("--scope", default="full")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--arch", default="")
    args = ap.parse_args()
    tasks = load_tasks()
    if args.arch:
        tasks = [t for t in tasks if t["arch"] == args.arch]
    if args.limit:
        tasks = tasks[:args.limit]
    name = f"{args.variant}-{args.scope}"
    rows = run_many(tasks, name, args.variant, args.scope)
    ok = [r for r in rows if "error" not in r]
    print(f"{name}: n={len(ok)} errors={len(rows) - len(ok)} serious={sum(r['serious'] for r in ok) / max(1, len(ok)):.3f} "
          f"success={sum(r['success'] for r in ok) / max(1, len(ok)):.3f} cost=${sum(r['cost'] for r in ok):.3f}")


if __name__ == "__main__":
    main()
