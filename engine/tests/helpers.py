from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from earned_autonomy import Actor, ChecksResult, Policy, ProposedAction, TaskTypePolicy, TrustEngine

START = datetime(2026, 1, 1, tzinfo=timezone.utc)
OK = ChecksResult(passed=["amount_matches_order"])
FAIL = ChecksResult(failed=["amount_matches_order"])

POLICY_OWNER = Actor("pat", {"policy_owner"})
AI_OWNER = Actor("ola", {"ai_owner"})
REVIEWER = Actor("rex", {"reviewer"})
AUDITOR = Actor("aud", {"auditor"})
BUILDER = Actor("bea", {"builder"}, builds={"customer_service_agent"})
AGENT = Actor("customer_service_agent", {"agent"}, agent_id="customer_service_agent")


class Clock:
    def __init__(self, now=START):
        self.t = now

    def __call__(self):
        return self.t

    def advance(self, **options):
        self.t = self.t + timedelta(**options)


def policy(**options):
    return Policy(task_types={
        "customer_service.status.update": TaskTypePolicy("C1", tools=["lookup_order"]),
        "customer_service.reply.send": TaskTypePolicy("C2"),
        "customer_service.refund.issue": TaskTypePolicy("C3", tools=["lookup_order", "issue_refund"]),
        "customer_service.payment.release": TaskTypePolicy("C4"),
    }, **options)


def engine(**options):
    clock = options.pop("clock", Clock())
    trust_engine = TrustEngine(options.pop("policy", policy()), clock=clock, sampler=options.pop("sampler", random.Random(0)), **options)
    trust_engine.test_clock = clock
    return trust_engine


_counter = [0]


def act(task_type="customer_service.status.update", agent="customer_service_agent", version="v1", organisation="organisation", **options):
    _counter[0] += 1
    return ProposedAction(f"action_{_counter[0]}", organisation, agent, version, "tool.call", options.pop("payload", {"x": _counter[0]}),
                          task_type=task_type, **options)


def run_clean(trust_engine, count, task_type="customer_service.status.update", agent="customer_service_agent", version="v1"):
    """n judged clean actions: held ones approved, autonomous ones spot-checked clean when sampled."""
    for _ in range(count):
        action = act(task_type, agent, version)
        decision = trust_engine.decide(action, OK)
        if decision.allowed:
            trust_engine.mark_executed(action.action_id)
            if any(item["action_id"] == action.action_id for item in trust_engine.review_queue()):
                trust_engine.record_outcome(action.action_id, "approved", None, "spot_check", "reviewer")
        else:
            trust_engine.record_outcome(action.action_id, "approved", None, "pre_review", "reviewer")


def promote_to(trust_engine, level, task_type="customer_service.status.update", agent="customer_service_agent", version="v1"):
    for _ in range(5000):
        state_rows = trust_engine.get_state("organisation", agent, task_type)
        if state_rows and state_rows[0]["level"] >= level:
            return
        run_clean(trust_engine, 1, task_type, agent, version)
    raise AssertionError("never promoted")
