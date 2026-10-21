"""Tool floor conformance (EA-7.8 to EA-7.9): a mis-tagged action can't borrow a lower-consequence
task type's trust when it calls a riskier write tool."""
import pytest
from helpers import OK, act, engine, policy, promote_to

from earned_autonomy import L2, Policy, TaskTypePolicy, lint_shared_write_tools


@pytest.mark.covers("EA-2.5")
def test_mis_tagged_refund_as_status_is_held_even_when_status_is_trusted():
    trust_engine = engine()
    promote_to(trust_engine, L2, "customer_service.status.update")
    honest = act("customer_service.status.update")                                  # reads only: acts at L2
    assert trust_engine.decide(honest, OK).mode == "act"
    sneaky = act("customer_service.status.update", write_tools=["issue_refund"])      # tagged C1, but issues a refund (C3)
    decision = trust_engine.decide(sneaky, OK)
    assert (decision.mode, decision.why) == ("hold", "tool_floor_mismatch")
    assert decision.tool_floor == "C3" and decision.consequence == "C3"
    # held actions land in the review queue like any other hold
    assert any(item["action_id"] == sneaky.action_id and item["why"] == "tool_floor_mismatch" for item in trust_engine.review_queue())


@pytest.mark.covers("EA-2.5", "EA-2.1")
def test_floor_check_runs_before_checks_and_level():
    trust_engine = engine()
    decision = trust_engine.decide(act("customer_service.status.update", write_tools=["issue_refund"]), None)
    assert decision.why == "tool_floor_mismatch"


@pytest.mark.covers("EA-2.5")
def test_floor_at_or_below_tag_does_not_hold():
    trust_engine = engine()
    promote_to(trust_engine, L2, "customer_service.refund.issue")
    decision = trust_engine.decide(act("customer_service.refund.issue", write_tools=["issue_refund"]), OK)
    assert decision.mode == "act" and decision.tool_floor == "C3"


@pytest.mark.covers("EA-7.8")
def test_unlisted_write_tool_has_floor_c4():
    p = policy()
    assert p.tool_floor("delete_customer") == "C4"
    trust_engine = engine()
    decision = trust_engine.decide(act("customer_service.refund.issue", write_tools=["delete_customer"]), OK)
    assert (decision.why, decision.tool_floor, decision.consequence) == ("tool_floor_mismatch", "C4", "C4")


@pytest.mark.covers("EA-7.8")
def test_tool_listed_by_capped_type_has_floor_c4():
    p = Policy(task_types={"customer_service.status.update": TaskTypePolicy("C1"),
                           "customer_service.payment.release": TaskTypePolicy("C4", tools=["release_payment"])})
    assert p.tool_floor("release_payment") == "C4"
    trust_engine = engine(policy=p)
    decision = trust_engine.decide(act("customer_service.status.update", write_tools=["release_payment"]), OK)
    assert decision.why == "tool_floor_mismatch"


@pytest.mark.covers("EA-7.4", "EA-7.8")
def test_explicit_floor_override_and_argument_dependent_hook():
    shared = Policy(task_types={"outbound_follow_up.reminder.send": TaskTypePolicy("C1", tools=["send_email"]),
                                "outbound_follow_up.offer.send": TaskTypePolicy("C3", tools=["send_email"])})
    assert shared.tool_floor("send_email") == "C3"                    # derived: the highest user
    # without a hook, every reminder is held by the shared tool's C3 floor
    trust_engine = engine(policy=shared)
    assert trust_engine.decide(act("outbound_follow_up.reminder.send", write_tools=["send_email"]), OK).why == "tool_floor_mismatch"

    # explicit override
    lowered = Policy(task_types=shared.task_types, tool_floors={"send_email": "C1"})
    assert lowered.tool_floor("send_email") == "C1"

    # argument-dependent floor: a reminder template is C1, anything else falls back to the policy (C3)
    def floor_fn(tool, arguments, policy):
        if tool == "send_email" and (arguments or {}).get("template") == "reminder":
            return "C1"
        return None

    e2 = engine(policy=shared, tool_floor_function=floor_fn)
    promote_to(e2, L2, "outbound_follow_up.reminder.send")
    ok = act("outbound_follow_up.reminder.send", write_tools=["send_email"], write_tool_arguments={"send_email": {"template": "reminder"}})
    assert e2.decide(ok, OK).mode == "act"
    bad = act("outbound_follow_up.reminder.send", write_tools=["send_email"], write_tool_arguments={"send_email": {"template": "offer"}})
    assert e2.decide(bad, OK).why == "tool_floor_mismatch"


@pytest.mark.covers("EA-7.9")
def test_shared_write_tool_lint():
    shared = Policy(task_types={"outbound_follow_up.reminder.send": TaskTypePolicy("C1", tools=["send_email"]),
                                "outbound_follow_up.offer.send": TaskTypePolicy("C3", tools=["send_email"])},
                    write_tools=["send_email"])
    warnings = lint_shared_write_tools(shared)
    assert len(warnings) == 1 and "send_email" in warnings[0] and "outbound_follow_up.reminder.send" in warnings[0]
    split = Policy(task_types={"outbound_follow_up.reminder.send": TaskTypePolicy("C1", tools=["send_reminder"]),
                               "outbound_follow_up.offer.send": TaskTypePolicy("C3", tools=["send_offer"])},
                   write_tools=["send_reminder", "send_offer"])
    assert lint_shared_write_tools(split) == []
    # read tools shared across levels are fine when write_tools is declared
    reads = policy(write_tools=["issue_refund"])
    assert lint_shared_write_tools(reads) == []


@pytest.mark.covers("EA-6.9", "EA-6.14")
def test_tool_floor_decisions_replay_and_keep_args_out_of_the_record():
    trust_engine = engine()
    action = act("customer_service.status.update", write_tools=["issue_refund"],
            write_tool_arguments={"issue_refund": {"amount": 4242.17, "note": "secret-customer-note"}})
    trust_engine.decide(action, OK)
    assert trust_engine.rebuild_state() == trust_engine.live_state()
    blob = repr([en.body for en in trust_engine.record.entries()])
    assert "issue_refund" in blob                                   # tool names are recorded
    assert "secret-customer-note" not in blob and "4242.17" not in blob
