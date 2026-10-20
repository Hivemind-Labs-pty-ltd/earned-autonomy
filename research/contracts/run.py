"""Run the shadow-contracts arms (A, B, C) on the T2 frozen streams. Writes report/raw/contracts-runs.json.

    cd research && python -m contracts.run
"""
from __future__ import annotations

import json
import math
import random
from collections import deque
from pathlib import Path

from analyze_v2 import rev, t2_actions
from analyze_v3 import COMBINED
from contracts.induce import TRAIN_SHARE, Contract, contract_correct, writes_agree, wording_ok
from gym.engine import wilson_upper
from gym.engine_v2 import CONS
from gym.engine_v3 import ConfigV3, EngineV3

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "report/raw"
SEEDS = range(100, 120)
WINDOW, WINDOW_MIN_AGREE = 30, 29
JUDGED_MIN, JUDGED_SAMPLE = 30, 0.25
SPOT_RATE, INCIDENT_P = 0.05, 0.3
SIGNOFF_MIN = 5.0
MANUAL_MIN = {"C1": 2.0, "C2": 4.0, "C3": 6.0, "C4": 6.0}
EPISODE_MIN = 10


def load(name):
    acts = t2_actions(name)
    tasks = {}
    for line in open(RAW / "t2-tasks.jsonl"):
        t = json.loads(line)
        tasks[t["task_id"]] = t
    runs = {}
    for line in open(RAW / f"t2-runs/{name}.jsonl"):
        r = json.loads(line)
        runs[r["task_id"]] = r
    return acts, tasks, runs


def build_contracts(acts, tasks, runs):
    """Train per task type on the first 30% of that type's tasks, in stream order."""
    by_type = {}
    for i, a in enumerate(acts):
        by_type.setdefault(a.task_type, []).append(i)
    train_cut, contracts = {}, {}
    for tt, idx in by_type.items():
        cut = math.ceil(TRAIN_SHARE * len(idx))
        train_cut[tt] = set(idx[:cut])
        cons = acts[idx[0]].meta["cons"]
        if cons == "C4":
            continue
        tr = [acts[i].meta["task_id"] for i in idx[:cut]]
        contracts[tt] = Contract([tasks[t] for t in tr], [runs[t]["writes"] for t in tr])
    return contracts, train_cut, by_type


class Clause:
    def __init__(self):
        self.window = deque(maxlen=WINDOW)
        self.promoted = False
        self.judged_n = 0
        self.judged_err = 0
        self.episode = None

    def reset(self):
        self.window.clear()
        self.judged_n = self.judged_err = 0


def run_arm(arm, seed, acts, tasks, runs, contracts, train_cut):
    engine = EngineV3(ConfigV3(**COMBINED), seed=seed * 17 + 3, reviewer=rev(seed), n_total=len(acts))
    rng = random.Random(seed * 7 + 11)
    clauses, episodes = {}, []
    extra = dict(minutes=0.0, auto=0, escapes=0, signoffs=0, contract_exec=0, contract_held=0,
                 judged_extra=0, promotions=0, demotions=0)
    exec_by_type = {}

    def close(cl, why):
        if cl.episode is not None:
            episodes.append(cl.episode)
            cl.episode = None
        cl.promoted = False
        cl.reset()
        extra["demotions"] += why != "end"

    for i, a in enumerate(acts):
        tid = a.meta["task_id"]
        task, run = tasks[tid], runs[tid]
        tt = a.task_type
        contract = contracts.get(tt) if arm != "A" else None
        if contract is None or i in train_cut[tt]:
            engine.step(a)
            continue
        leaf, pred = contract.predict(task)
        if leaf is None:
            engine.step(a)
            continue
        cl = clauses.setdefault((tt, leaf), Clause())
        agree = writes_agree(pred, run["writes"])
        if cl.promoted:
            cl.episode["tasks"] += 1
            cl.episode["contract_wrong"] += not contract_correct(task, pred)
            if agree and wording_ok(run.get("reply"), task, pred):
                extra["auto"] += 1
                extra["contract_exec"] += 1
                exec_by_type[tt] = exec_by_type.get(tt, 0) + 1
                demote = False
                if a.true_err:
                    extra["escapes"] += 1
                    demote = rng.random() < INCIDENT_P
                if rng.random() < SPOT_RATE:
                    extra["minutes"] += 1
                    if engine.reviewer.review(a.true_err):
                        demote = True
                if demote:
                    close(cl, "demote")
            else:
                extra["contract_held"] += 1
                extra["minutes"] += 1
                caught = engine.reviewer.review(a.true_err)
                if a.true_err and not caught:
                    extra["escapes"] += 1
            continue
        # shadow: the base policy handles the task; the contract only predicts
        blocked_before = engine.m["blocked"]
        mode = engine.step(a)
        cl.window.append(agree)
        if arm == "C" and agree:
            if mode == "review":
                cl.judged_n += 1
                cl.judged_err += engine.m["blocked"] > blocked_before
            elif rng.random() < JUDGED_SAMPLE:
                extra["minutes"] += 1
                extra["judged_extra"] += 1
                cl.judged_n += 1
                cl.judged_err += engine.reviewer.review(a.true_err)
        ok = len(cl.window) == WINDOW and sum(cl.window) >= WINDOW_MIN_AGREE
        if ok and arm == "C":
            eps = CONS[a.meta["cons"]]["eps"]
            ok = cl.judged_n >= JUDGED_MIN and wilson_upper(cl.judged_err, cl.judged_n) <= eps
        if ok:
            cl.promoted = True
            extra["minutes"] += SIGNOFF_MIN
            extra["signoffs"] += 1
            extra["promotions"] += 1
            cl.episode = dict(type=tt, leaf=leaf, cons=a.meta["cons"], start=i, tasks=0, contract_wrong=0)
    for cl in clauses.values():
        close(cl, "end")

    m = engine.m
    n = len(acts)
    scored = [e for e in episodes if e["tasks"] >= EPISODE_MIN]
    locked = [e for e in scored if e["contract_wrong"] / e["tasks"] > CONS[e["cons"]]["eps"]]
    return dict(
        minutes_per_task=(m["minutes"] + extra["minutes"]) / n,
        manual_minutes_per_task=sum(MANUAL_MIN[a.meta["cons"]] for a in acts) / n,
        without_person=(m["auto"] + extra["auto"]) / n,
        escapes_per100=100 * (m["escapes"] + extra["escapes"]) / n,
        promotions=extra["promotions"], demotions=extra["demotions"],
        episodes_scored=len(scored), episodes_locked=len(locked),
        contract_exec=extra["contract_exec"], contract_held=extra["contract_held"],
        judged_extra=extra["judged_extra"], signoffs=extra["signoffs"],
        exec_by_type=exec_by_type,
        locked_detail=[dict(type=e["type"], leaf=e["leaf"], tasks=e["tasks"], wrong=e["contract_wrong"]) for e in locked],
    )


def main():
    out = {}
    for name in ("good-full", "sloppy-full"):
        acts, tasks, runs = load(name)
        contracts, train_cut, by_type = build_contracts(acts, tasks, runs)
        post = {tt: len(idx) - len(train_cut[tt]) for tt, idx in by_type.items()}
        info = {tt: dict(clauses=len(c.clauses), leaves=int(c.tree.get_n_leaves()), post_training_tasks=post[tt])
                for tt, c in contracts.items()}
        out[name] = dict(contracts=info, post_training=post,
                         arms={arm: [run_arm(arm, s, acts, tasks, runs, contracts, train_cut) for s in SEEDS]
                               for arm in ("A", "B", "C")})
    (RAW / "contracts-runs.json").write_text(json.dumps(out, indent=1, default=str))
    return out


if __name__ == "__main__":
    main()
