"""Replay a committed Trust Gym T1 stream subset through the engine (rule EA-3.4, EA-3.5: Trust Gym parity).

The fixture holds 12 T1 worlds (seeds 90 000–90 011, the v3 reference seeds) with each action's true error, check
flag, consequence level, true error rate and day. The reviewer model, incident model and metrics are ported from the
Trust Gym (gym/engine.py Reviewer, gym/engine_v2.py incidents, analyze_v3.ref_t1 metrics).
"""
from __future__ import annotations

import gzip
import json
import random
import statistics as statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from earned_autonomy import ChecksResult, Policy, ProposedAction, TaskTypePolicy, TrustEngine

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "t1_worlds.jsonl.gz"
CONSEQUENCE_ERROR_BAR = {"C1": 0.10, "C2": 0.05, "C3": 0.02, "C4": 0.0}
REGRESSIONS = {"bad_update", "defector"}
BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def load_worlds():
    worlds, current_world = [], None
    with gzip.open(FIXTURE, "rt") as f:
        for line in f:
            row = json.loads(line)
            if isinstance(row, dict):
                current_world = {"seed": row["world"], "keys": row["keys"], "actions": []}
                worlds.append(current_world)
            else:
                current_world["actions"].append(row)
    return worlds


class Reviewer:
    """Complacency model from the Trust Gym (catch 0.95 when errors are common, falling toward 0.60)."""

    def __init__(self, random_source, catch_high=0.95, catch_low=0.60, reference_rate=0.05, alpha=0.02):
        self.random_source, self.catch_high, self.catch_low, self.reference_rate, self.alpha = random_source, catch_high, catch_low, reference_rate, alpha
        self.recent_error_rate = reference_rate

    def review(self, is_serious_error: bool) -> bool:
        catch_probability = self.catch_low + (self.catch_high - self.catch_low) * min(1.0, self.recent_error_rate / self.reference_rate)
        caught = is_serious_error and self.random_source.random() < catch_probability
        self.recent_error_rate = (1 - self.alpha) * self.recent_error_rate + self.alpha * (1.0 if caught else 0.0)
        return caught

    def canary(self):
        self.recent_error_rate = (1 - self.alpha) * self.recent_error_rate + self.alpha


def run_world(world, canary_rate=0.05, incident_probability=0.3):
    seed = world["seed"]
    random_source = random.Random(seed * 17 + 3)
    reviewer = Reviewer(random.Random(seed * 31 + 1))
    types = {}
    for action in world["actions"]:
        types[action[1]] = action[4]
    policy = Policy(task_types={task_type: TaskTypePolicy(consequence=c) for task_type, c in types.items()}, canary_rate=canary_rate)
    clock = [BASE]
    trust_engine = TrustEngine(policy, clock=lambda: clock[0], sampler=random.Random(seed))
    rates = defaultdict(list)
    for action in world["actions"]:
        rates[(action[0], action[1])].append(action[5])
    type_i = defaultdict(int)
    pending = []
    promos, seen_changes = [], 0
    level_at = {}                       # key -> level when its regression starts
    regress = {(k.split("|")[0], k.split("|")[1]): v for k, v in world["keys"].items()
               if v["pattern"] in REGRESSIONS and v["i0"] is not None}
    demote_lat = []
    for step, (agent, task_type, is_serious_error, flag, consequence, catch_probability, day) in enumerate(world["actions"]):
        clock[0] = BASE + timedelta(days=day)
        due = [x for x in pending if x[0] <= step]
        pending = [x for x in pending if x[0] > step]
        for _, action_id in due:
            trust_engine.report_incident(action_id, "serious", "sim")
        k = (agent, task_type)
        idx = type_i[k]
        if k in regress and idx == regress[k]["i0"]:
            level_at[k] = trust_engine.get_state("organisation", agent, task_type)[0]["level"] if trust_engine.get_state("organisation", agent, task_type) else 1
        type_i[k] += 1
        action_id = f"world{seed}-{step}"
        act = ProposedAction(action_id, "organisation", agent, "v1", "tool.call", {"t": step}, task_type=task_type)
        checks = ChecksResult(failed=["sim_check"]) if flag else ChecksResult(passed=["sim_check"])
        decision = trust_engine.decide(act, checks)
        if not decision.allowed:
            if canary_rate and random_source.random() < canary_rate:
                reviewer.canary()
            caught = reviewer.review(bool(is_serious_error))
            if caught:
                trust_engine.record_outcome(action_id, "rejected", "other_serious", "pre_review", "reviewer")
            else:
                trust_engine.record_outcome(action_id, "approved", None, "pre_review", "reviewer")
                trust_engine.mark_executed(action_id)
                if is_serious_error:
                    if random_source.random() < incident_probability:
                        pending.append((step + random_source.randint(1, 20), action_id))
        else:
            trust_engine.mark_executed(action_id)
            sampled = any(item["action_id"] == action_id and item["kind"] == "spot_check" for item in trust_engine.review_queue())
            if is_serious_error and random_source.random() < incident_probability:
                pending.append((step + random_source.randint(1, 20), action_id))
            if sampled:
                caught = reviewer.review(bool(is_serious_error))
                trust_engine.record_outcome(action_id, "rejected" if caught else "approved", "other_serious" if caught else None,
                                   "spot_check", "reviewer")
        changes = trust_engine.level_changes()
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
        good += statistics.fmean(nxt) <= CONSEQUENCE_ERROR_BAR[types[ck[1]]]
    return trust_engine, good, total, [x[1] for x in demote_lat]
