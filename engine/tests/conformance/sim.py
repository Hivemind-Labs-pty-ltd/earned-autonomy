"""Replay a committed Trust Gym T1 stream subset through the engine (SPEC §13.7 parity).

The fixture holds 12 T1 worlds (seeds 90 000–90 011, the v3 reference seeds) with each action's true error, check
flag, consequence level, true error rate and day. The reviewer model, incident model and metrics are ported from the
Trust Gym (gym/engine.py Reviewer, gym/engine_v2.py incidents, analyze_v3.ref_t1 metrics).
"""
from __future__ import annotations

import gzip
import json
import random
import statistics as st
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from earned_autonomy import ChecksResult, Policy, ProposedAction, TaskTypePolicy, TrustEngine

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "t1_worlds.jsonl.gz"
CONS_EPS = {"C1": 0.10, "C2": 0.05, "C3": 0.02, "C4": 0.0}
REGRESSIONS = {"bad_update", "defector"}
BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def load_worlds():
    worlds, cur = [], None
    with gzip.open(FIXTURE, "rt") as f:
        for line in f:
            row = json.loads(line)
            if isinstance(row, dict):
                cur = {"seed": row["world"], "keys": row["keys"], "actions": []}
                worlds.append(cur)
            else:
                cur["actions"].append(row)
    return worlds


class Reviewer:
    """Complacency model from the Trust Gym (catch 0.95 when errors are common, falling toward 0.60)."""

    def __init__(self, rng, p_hi=0.95, p_lo=0.60, ref=0.05, alpha=0.02):
        self.rng, self.p_hi, self.p_lo, self.ref, self.alpha = rng, p_hi, p_lo, ref, alpha
        self.ema = ref

    def review(self, err: bool) -> bool:
        p = self.p_lo + (self.p_hi - self.p_lo) * min(1.0, self.ema / self.ref)
        caught = err and self.rng.random() < p
        self.ema = (1 - self.alpha) * self.ema + self.alpha * (1.0 if caught else 0.0)
        return caught

    def canary(self):
        self.ema = (1 - self.alpha) * self.ema + self.alpha


def run_world(w, canary_rate=0.05, incident_p=0.3):
    seed = w["seed"]
    rng = random.Random(seed * 17 + 3)
    reviewer = Reviewer(random.Random(seed * 31 + 1))
    types = {}
    for a in w["actions"]:
        types[a[1]] = a[4]
    policy = Policy(task_types={tt: TaskTypePolicy(consequence=c) for tt, c in types.items()}, canary_rate=canary_rate)
    clock = [BASE]
    eng = TrustEngine(policy, clock=lambda: clock[0], sampler=random.Random(seed))
    rates = defaultdict(list)
    for a in w["actions"]:
        rates[(a[0], a[1])].append(a[5])
    type_i = defaultdict(int)
    pending = []
    promos, seen_changes = [], 0
    level_at = {}                       # key -> level when its regression starts
    regress = {(k.split("|")[0], k.split("|")[1]): v for k, v in w["keys"].items()
               if v["pattern"] in REGRESSIONS and v["i0"] is not None}
    demote_lat = []
    for t, (agent, tt, err, flag, cons, p, day) in enumerate(w["actions"]):
        clock[0] = BASE + timedelta(days=day)
        due = [x for x in pending if x[0] <= t]
        pending = [x for x in pending if x[0] > t]
        for _, aid in due:
            eng.report_incident(aid, "serious", "sim")
        k = (agent, tt)
        idx = type_i[k]
        if k in regress and idx == regress[k]["i0"]:
            level_at[k] = eng.get_state("org", agent, tt)[0]["level"] if eng.get_state("org", agent, tt) else 1
        type_i[k] += 1
        aid = f"w{seed}-{t}"
        act = ProposedAction(aid, "org", agent, "v1", "tool.call", {"t": t}, task_type=tt)
        checks = ChecksResult(failed=["sim_check"]) if flag else ChecksResult(passed=["sim_check"])
        d = eng.decide(act, checks)
        if not d.allowed:
            if canary_rate and rng.random() < canary_rate:
                reviewer.canary()
            caught = reviewer.review(bool(err))
            if caught:
                eng.record_outcome(aid, "rejected", "other_serious", "pre_review", "rev")
            else:
                eng.record_outcome(aid, "approved", None, "pre_review", "rev")
                eng.mark_executed(aid)
                if err:
                    if rng.random() < incident_p:
                        pending.append((t + rng.randint(1, 20), aid))
        else:
            eng.mark_executed(aid)
            sampled = any(q["action_id"] == aid and q["kind"] == "spot_check" for q in eng.review_queue())
            if err and rng.random() < incident_p:
                pending.append((t + rng.randint(1, 20), aid))
            if sampled:
                caught = reviewer.review(bool(err))
                eng.record_outcome(aid, "rejected" if caught else "approved", "other_serious" if caught else None,
                                   "spot_check", "rev")
        changes = eng.level_changes()
        for c in changes[seen_changes:]:
            ck = (c["key"][1], c["key"][2])
            c["type_i"] = type_i[ck]
            if c["to"] > c["from"] and c["to"] >= 2 and c["why"] == "evidence":
                promos.append((ck, type_i[ck]))
            if c["to"] < c["from"] and ck in regress and ck in level_at and level_at[ck] >= 2 \
                    and type_i[ck] > regress[ck]["i0"] and ck not in {x[0] for x in demote_lat}:
                demote_lat.append((ck, type_i[ck] - regress[ck]["i0"]))
        seen_changes = len(changes)
    good = total = 0
    for ck, i in promos:
        nxt = rates[ck][i: i + 200]
        if len(nxt) < 50:
            continue
        total += 1
        good += st.fmean(nxt) <= CONS_EPS[types[ck[1]]]
    return eng, good, total, [x[1] for x in demote_lat]
