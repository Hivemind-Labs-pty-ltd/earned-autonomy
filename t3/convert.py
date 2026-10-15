"""T3 public anchor: turn the 2026-09-11 τ²-bench retail runs into Trust Gym action streams.

No model calls. Reuses hivemind-memory-bench report/raw/gates-tau2 (A = prompt-only, Cy = 9 gates with the
corrected confirmation gate v2, reasoned repair; flash 30 tasks x 3 trials, Haiku 30 x 1).

One row per conversation:
  true_err    reward < 1 OR a policy violation was sent (the 9 corrected gates re-run offline over every
              assistant message that went out, exactly as gates/tau2_violations.py scores it)
  check_flag  A runs: the same 9 gates fire on the sent trajectory (a check run after the fact).
              Cy runs: any gate fired on any attempt during the run (logged in attempts-Cy-*.jsonl, before repair).
  task_type   from the task's expected write actions (evaluation_criteria.actions):
              cancel_pending_order -> cancel; modify_pending_order_items -> modify;
              modify_pending_order_address / modify_pending_order_payment / modify_user_address -> address-or-payment;
              return_delivered_order_items -> return; exchange_delivered_order_items -> exchange;
              no write (reads / transfer only) -> info-only; two or more of these categories -> multi.

Run with the tau2 venv:
  PYTHONPATH=$HOME/Sites/hivemind-memory-bench ~/Sites/hivemind-memory-bench/.venv-tau2/bin/python t3/convert.py
"""
import collections
import json
import os
import random
from pathlib import Path

os.environ.setdefault("TAU2_DATA_DIR", str(Path.home() / "Sites/tau2-bench/data"))
os.environ["GATES_EXCLUDE"] = "one_tool_call_at_a_time"
from tau2.data_model.message import AssistantMessage  # noqa: E402
from tau2.data_model.simulation import Results  # noqa: E402

from gates.tau2_gates import run_gates  # noqa: E402

RAW = Path.home() / "Sites/hivemind-memory-bench/report/raw/gates-tau2"
TASKS = Path.home() / "Sites/tau2-bench/data/tau2/domains/retail/tasks.json"
OUT = Path(__file__).resolve().parent.parent / "report" / "raw"
RUNS = {"flash-A": "A-flash", "flash-Cy": "Cy-flash", "haiku-A": "A-haiku", "haiku-Cy": "Cy-haiku"}

WRITE_CAT = {
    "cancel_pending_order": "cancel",
    "modify_pending_order_items": "modify",
    "modify_pending_order_address": "address-or-payment",
    "modify_pending_order_payment": "address-or-payment",
    "modify_user_address": "address-or-payment",
    "return_delivered_order_items": "return",
    "exchange_delivered_order_items": "exchange",
}


def task_types() -> dict:
    out = {}
    for t in json.load(open(TASKS)):
        acts = (t.get("evaluation_criteria") or {}).get("actions") or []
        cats = {WRITE_CAT[a["name"]] for a in acts if a["name"] in WRITE_CAT}
        out[str(t["id"])] = "info-only" if not cats else (cats.pop() if len(cats) == 1 else "multi")
    return out


def load(d: Path):
    return Results.load(d / "results.json") if hasattr(Results, "load") \
        else Results.model_validate(json.load(open(d / "results.json")))


def sent_violations(sim) -> list:
    hist, names = [], []
    for m in sim.messages:
        if isinstance(m, AssistantMessage):
            names += [g["name"] for g in run_gates(m, hist) if not g["pass"]]
        hist.append(m)
    return names


def attempt_fired(cond_dir: str, sims) -> dict:
    """Map sim.id -> did any gate fire during the run. Attempts are keyed by their own run_id, so link them to
    simulations by the sequence of sent actions (final attempt per turn), skipping tau2's scripted greeting."""
    att = collections.defaultdict(list)
    for line in open(RAW / f"attempts-{cond_dir}.jsonl"):
        r = json.loads(line)
        att[r["run_id"]].append(r)

    def asig(rs):
        last = {}
        for r in rs:
            last[r["turn"]] = r
        return tuple(last[t]["tool"] or "text" for t in sorted(last))

    def ssig(sim):
        out = []
        for m in sim.messages:
            if isinstance(m, AssistantMessage):
                out.append(m.tool_calls[0].name if m.tool_calls else "text")
        return tuple(out[1:])

    by_task = collections.defaultdict(list)
    for k, rs in att.items():
        by_task[str(rs[0]["task_id"])].append((k, asig(rs)))
    fired = {}
    for sim in sims:
        cands = [k for k, sg in by_task[str(sim.task_id)] if sg == ssig(sim)]
        vals = {any(r["failed"] for r in att[k]) for k in cands}
        if len(vals) != 1:
            raise RuntimeError(f"cannot link sim {sim.id} task {sim.task_id}: {len(cands)} candidates, {vals}")
        fired[sim.id] = vals.pop()
    return fired


def main():
    types = task_types()
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {}
    for agent, d in RUNS.items():
        res = load(RAW / d)
        sims = sorted(res.simulations, key=lambda s: (s.trial, int(s.task_id)))
        fired = attempt_fired(d, sims) if agent.endswith("Cy") else None
        rows = []
        for s in sims:
            reward = s.reward_info.reward if s.reward_info else 0.0
            viol = sent_violations(s)
            rows.append(dict(
                agent=agent, task_type=types[str(s.task_id)],
                true_err=bool(reward < 1 or viol),
                check_flag=bool(fired[s.id]) if fired is not None else bool(viol),
                version="v1", capped=False, counterparty="new",
                meta=dict(task_id=str(s.task_id), trial=s.trial, reward=reward, violations=viol)))
        with open(OUT / f"t3-stream-{agent}.jsonl", "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        shuf = rows[:]
        random.Random(0).shuffle(shuf)
        with open(OUT / f"t3-stream-{agent}-shuffled.jsonl", "w") as f:
            for r in shuf:
                f.write(json.dumps(r) + "\n")
        summary[agent] = rows
    report(summary)


def report(summary):
    for agent, rows in summary.items():
        n = len(rows)
        avg = sum(r["meta"]["reward"] for r in rows) / n
        vio = 100 * sum(bool(r["meta"]["violations"]) for r in rows) / n
        err = [r for r in rows if r["true_err"]]
        ok = [r for r in rows if not r["true_err"]]
        rec = sum(r["check_flag"] for r in err) / len(err) if err else float("nan")
        fpr = sum(r["check_flag"] for r in ok) / len(ok) if ok else float("nan")
        tc = collections.Counter(r["task_type"] for r in rows)
        te = collections.Counter(r["task_type"] for r in err)
        print(f"{agent}: n={n} avg_reward={avg:.3f} violation_sims={vio:.1f}% serious_err={len(err)/n:.3f} "
              f"check_recall={rec:.2f} check_fpr={fpr:.2f}")
        print("   types:", {k: f"{te[k]}/{v}" for k, v in sorted(tc.items())})


if __name__ == "__main__":
    main()
