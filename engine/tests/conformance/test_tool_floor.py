"""Tool floor conformance (SPEC §4, §6 step 2b, [tested v4]): a mis-tagged action can't borrow a lower-consequence
task type's trust when it calls a riskier write tool."""
from helpers import OK, act, engine, policy, promote_to

from earned_autonomy import L2, Policy, TaskTypePolicy, lint_shared_write_tools


def test_mis_tagged_refund_as_status_is_held_even_when_status_is_trusted():
    e = engine()
    promote_to(e, L2, "cs.status.update")
    honest = act("cs.status.update")                                  # reads only: acts at L2
    assert e.decide(honest, OK).mode == "act"
    sneaky = act("cs.status.update", write_tools=["issue_refund"])      # tagged C1, but issues a refund (C3)
    d = e.decide(sneaky, OK)
    assert (d.mode, d.why) == ("hold", "tool_floor_mismatch")
    assert d.tool_floor == "C3" and d.consequence == "C3"
    # held actions land in the review queue like any other hold
    assert any(q["action_id"] == sneaky.action_id and q["why"] == "tool_floor_mismatch" for q in e.review_queue())


def test_floor_check_runs_before_checks_and_level():
    e = engine()
    d = e.decide(act("cs.status.update", write_tools=["issue_refund"]), None)
    assert d.why == "tool_floor_mismatch"


def test_floor_at_or_below_tag_does_not_hold():
    e = engine()
    promote_to(e, L2, "cs.refund.issue")
    d = e.decide(act("cs.refund.issue", write_tools=["issue_refund"]), OK)
    assert d.mode == "act" and d.tool_floor == "C3"


def test_unlisted_write_tool_has_floor_c4():
    p = policy()
    assert p.tool_floor("delete_customer") == "C4"
    e = engine()
    d = e.decide(act("cs.refund.issue", write_tools=["delete_customer"]), OK)
    assert (d.why, d.tool_floor, d.consequence) == ("tool_floor_mismatch", "C4", "C4")


def test_tool_listed_by_capped_type_has_floor_c4():
    p = Policy(task_types={"cs.status.update": TaskTypePolicy("C1"),
                           "cs.payment.release": TaskTypePolicy("C4", tools=["release_payment"])})
    assert p.tool_floor("release_payment") == "C4"
    e = engine(policy=p)
    d = e.decide(act("cs.status.update", write_tools=["release_payment"]), OK)
    assert d.why == "tool_floor_mismatch"


def test_explicit_floor_override_and_argument_dependent_hook():
    shared = Policy(task_types={"of.reminder.send": TaskTypePolicy("C1", tools=["send_email"]),
                                "of.offer.send": TaskTypePolicy("C3", tools=["send_email"])})
    assert shared.tool_floor("send_email") == "C3"                    # derived: the highest user
    # without a hook, every reminder is held by the shared tool's C3 floor
    e = engine(policy=shared)
    assert e.decide(act("of.reminder.send", write_tools=["send_email"]), OK).why == "tool_floor_mismatch"

    # explicit override
    lowered = Policy(task_types=shared.task_types, tool_floors={"send_email": "C1"})
    assert lowered.tool_floor("send_email") == "C1"

    # argument-dependent floor: a reminder template is C1, anything else falls back to the policy (C3)
    def floor_fn(tool, args, policy):
        if tool == "send_email" and (args or {}).get("template") == "reminder":
            return "C1"
        return None

    e2 = engine(policy=shared, tool_floor_fn=floor_fn)
    promote_to(e2, L2, "of.reminder.send")
    ok = act("of.reminder.send", write_tools=["send_email"], write_tool_args={"send_email": {"template": "reminder"}})
    assert e2.decide(ok, OK).mode == "act"
    bad = act("of.reminder.send", write_tools=["send_email"], write_tool_args={"send_email": {"template": "offer"}})
    assert e2.decide(bad, OK).why == "tool_floor_mismatch"


def test_shared_write_tool_lint():
    shared = Policy(task_types={"of.reminder.send": TaskTypePolicy("C1", tools=["send_email"]),
                                "of.offer.send": TaskTypePolicy("C3", tools=["send_email"])},
                    write_tools=["send_email"])
    warnings = lint_shared_write_tools(shared)
    assert len(warnings) == 1 and "send_email" in warnings[0] and "of.reminder.send" in warnings[0]
    split = Policy(task_types={"of.reminder.send": TaskTypePolicy("C1", tools=["send_reminder"]),
                               "of.offer.send": TaskTypePolicy("C3", tools=["send_offer"])},
                   write_tools=["send_reminder", "send_offer"])
    assert lint_shared_write_tools(split) == []
    # read tools shared across levels are fine when write_tools is declared
    reads = policy(write_tools=["issue_refund"])
    assert lint_shared_write_tools(reads) == []


def test_tool_floor_decisions_replay_and_keep_args_out_of_the_record():
    e = engine()
    a = act("cs.status.update", write_tools=["issue_refund"],
            write_tool_args={"issue_refund": {"amount": 4242.17, "note": "secret-customer-note"}})
    e.decide(a, OK)
    assert e.rebuild_state() == e.live_state()
    blob = repr([en.body for en in e.record.entries()])
    assert "issue_refund" in blob                                   # tool names are recorded
    assert "secret-customer-note" not in blob and "4242.17" not in blob
