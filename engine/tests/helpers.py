from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from earned_autonomy import Actor, ChecksResult, Policy, ProposedAction, TaskTypePolicy, TrustEngine

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
OK = ChecksResult(passed=["amount_matches_order"])
FAIL = ChecksResult(failed=["amount_matches_order"])

POLICY_OWNER = Actor("pat", {"policy_owner"})
AI_OWNER = Actor("ola", {"ai_owner"})
REVIEWER = Actor("rex", {"reviewer"})
AUDITOR = Actor("aud", {"auditor"})
BUILDER = Actor("bea", {"builder"}, builds={"cs"})
AGENT = Actor("cs", {"agent"}, agent_id="cs")


class Clock:
    def __init__(self, t=T0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, **kw):
        self.t = self.t + timedelta(**kw)


def policy(**kw):
    return Policy(task_types={
        "cs.status.update": TaskTypePolicy("C1", tools=["lookup_order"]),
        "cs.reply.send": TaskTypePolicy("C2"),
        "cs.refund.issue": TaskTypePolicy("C3", tools=["lookup_order", "issue_refund"]),
        "cs.payment.release": TaskTypePolicy("C4"),
    }, **kw)


def engine(**kw):
    clock = kw.pop("clock", Clock())
    e = TrustEngine(kw.pop("policy", policy()), clock=clock, sampler=kw.pop("sampler", random.Random(0)), **kw)
    e.test_clock = clock
    return e


_n = [0]


def act(task_type="cs.status.update", agent="cs", version="v1", org="org", **kw):
    _n[0] += 1
    return ProposedAction(f"act_{_n[0]}", org, agent, version, "tool.call", kw.pop("payload", {"x": _n[0]}),
                          task_type=task_type, **kw)


def run_clean(e, n, task_type="cs.status.update", agent="cs", version="v1"):
    """n judged clean actions: held ones approved, autonomous ones spot-checked clean when sampled."""
    for _ in range(n):
        a = act(task_type, agent, version)
        d = e.decide(a, OK)
        if d.allowed:
            e.mark_executed(a.action_id)
            if any(q["action_id"] == a.action_id for q in e.review_queue()):
                e.record_outcome(a.action_id, "approved", None, "spot_check", "rev")
        else:
            e.record_outcome(a.action_id, "approved", None, "pre_review", "rev")


def promote_to(e, level, task_type="cs.status.update", agent="cs", version="v1"):
    for _ in range(5000):
        st = e.get_state("org", agent, task_type)
        if st and st[0]["level"] >= level:
            return
        run_clean(e, 1, task_type, agent, version)
    raise AssertionError("never promoted")
