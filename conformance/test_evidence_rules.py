"""Conformance tests for evidence, versions and oversight rules not covered elsewhere.

Each test names the spec rules it checks with `@pytest.mark.covers`.
"""
import pytest
from helpers import OK, REVIEWER, act, engine, promote_to, run_clean

from earned_autonomy import L1, L2, TaskTypePolicy, Policy


class NeverSample:
    """A sampler that never selects anything, so no autonomous action is spot-checked (test use only)."""

    def random(self):
        return 0.999999


def state_of(trust_engine, task_type="customer_service.status.update", organisation="organisation",
             agent="customer_service_agent"):
    rows = [row for row in trust_engine.get_state(organisation, agent, task_type)]
    return rows[0]


@pytest.mark.covers("EA-1.2")
def test_unjudged_autonomous_actions_are_not_evidence():
    trust_engine = engine(sampler=NeverSample())
    promote_to(trust_engine, L2)
    before = state_of(trust_engine)["judged_count"]
    for _ in range(40):
        action = act()
        assert trust_engine.decide(action, OK).allowed
        trust_engine.mark_executed(action.action_id)
    assert state_of(trust_engine)["judged_count"] == before


@pytest.mark.covers("EA-1.3")
def test_spot_check_and_pre_review_outcomes_weigh_the_same():
    trust_engine = engine()
    held = act()
    assert not trust_engine.decide(held, OK).allowed
    before = state_of(trust_engine)["judged_count"]
    trust_engine.record_outcome(held.action_id, "approved", None, "pre_review", "reviewer")
    pre_review_step = state_of(trust_engine)["judged_count"] - before

    promoted = engine()
    promote_to(promoted, L2)
    while True:
        action = act()
        assert promoted.decide(action, OK).allowed
        promoted.mark_executed(action.action_id)
        if any(item["action_id"] == action.action_id for item in promoted.review_queue()):
            break
    before = state_of(promoted)["judged_count"]
    promoted.record_outcome(action.action_id, "approved", None, "spot_check", "reviewer")
    assert state_of(promoted)["judged_count"] - before == pre_review_step == 1


@pytest.mark.covers("EA-1.8")
def test_evidence_does_not_fade_with_time():
    trust_engine = engine()
    run_clean(trust_engine, 50, "customer_service.reply.send")
    before = state_of(trust_engine, "customer_service.reply.send")
    trust_engine.test_clock.advance(days=400)
    decision = trust_engine.decide(act("customer_service.reply.send"), OK)
    after = state_of(trust_engine, "customer_service.reply.send")
    assert decision.judged_count == before["judged_count"] == after["judged_count"] == 50
    assert after["serious_error_count"] == before["serious_error_count"]


@pytest.mark.covers("EA-3.5")
def test_edits_and_rejections_need_a_reason_code():
    trust_engine = engine()
    for label in ("rejected", "material_edit"):
        action = act()
        trust_engine.decide(action, OK)
        with pytest.raises(ValueError):
            trust_engine.record_outcome(action.action_id, label, None, "pre_review", "reviewer")
    action = act()
    trust_engine.decide(action, OK)
    trust_engine.record_outcome(action.action_id, "rejected", "wrong_fact", "pre_review", "reviewer")


@pytest.mark.covers("EA-2.11")
def test_the_newest_decision_applies_at_execution_time():
    trust_engine = engine()
    promote_to(trust_engine, L2)
    action = act()
    assert trust_engine.decide(action, OK).allowed
    trust_engine.pause(REVIEWER, "organisation", "customer_service_agent", "customer_service.status.update")
    assert not trust_engine.decide(action, OK).allowed           # re-decided before running
    assert not trust_engine.may_execute(action.action_id)
    with pytest.raises(PermissionError):
        trust_engine.mark_executed(action.action_id)


@pytest.mark.covers("EA-7.3")
def test_the_task_type_name_has_no_effect_on_the_maths():
    def run(name):
        trust_engine = engine(policy=Policy(task_types={name: TaskTypePolicy("C2")}))
        for index in range(160):
            action = act(name)
            decision = trust_engine.decide(action, OK)
            if decision.allowed:
                trust_engine.mark_executed(action.action_id)
                continue
            bad = index % 37 == 0
            trust_engine.record_outcome(action.action_id, "rejected" if bad else "approved",
                                        "wrong_fact" if bad else None, "pre_review", "reviewer")
        row = state_of(trust_engine, name)
        return row["level"], row["judged_count"], row["serious_error_count"]

    assert run("customer_service.reply.send") == run("x") == run("a.very.different.name")


@pytest.mark.covers("EA-4.1", "EA-4.9", "EA-4.12")
def test_version_changes_apply_per_agent_across_organisations_including_rollback():
    trust_engine = engine()
    for organisation in ("organisation", "second_organisation"):
        for _ in range(120):
            action = act("customer_service.reply.send", organisation=organisation)
            if not trust_engine.decide(action, OK).allowed:
                trust_engine.record_outcome(action.action_id, "approved", None, "pre_review", "reviewer")
    counts = {org: state_of(trust_engine, "customer_service.reply.send", org)["judged_count"]
              for org in ("organisation", "second_organisation")}
    # v2 has results only for another task type: reply.send is missing, so it is discounted in both organisations
    trust_engine.on_version_published("customer_service_agent", "v2", {"customer_service.status.update": {"hidden_pass": 1.0,
                                                                                                         "hidden_test_count": 20}})
    for org, before in counts.items():
        assert state_of(trust_engine, "customer_service.reply.send", org)["judged_count"] == pytest.approx(before * 0.5)
    # rolling back to v1 is a version change too
    halved = state_of(trust_engine, "customer_service.reply.send")["judged_count"]
    trust_engine.on_version_published("customer_service_agent", "v1", {})
    assert state_of(trust_engine, "customer_service.reply.send")["judged_count"] == pytest.approx(halved * 0.5)


@pytest.mark.covers("EA-1.12")
def test_passing_tests_is_not_promotion_evidence():
    trust_engine = engine()
    run_clean(trust_engine, 20, "customer_service.reply.send")
    before = state_of(trust_engine, "customer_service.reply.send")
    trust_engine.suites.seed_hidden("customer_service.reply.send", [(f"hidden_{i}", {}) for i in range(30)])
    trust_engine.on_version_published("customer_service_agent", "v2", {"customer_service.reply.send": {"hidden_pass": 1.0,
                                                                                                      "training_pass": 1.0}})
    after = state_of(trust_engine, "customer_service.reply.send")
    assert after["judged_count"] == before["judged_count"]
    assert after["level"] == before["level"] == L1


@pytest.mark.covers("EA-3.15")
def test_a_second_check_updates_only_the_reviewer():
    trust_engine = engine()
    run_clean(trust_engine, 10, "customer_service.reply.send")
    agent_states = trust_engine.live_state()["states"]
    reviewers_before = trust_engine.live_state()["reviewers"]
    trust_engine.record_second_check("organisation", "reviewer", "customer_service.reply.send", found_error=True)
    after = trust_engine.live_state()
    assert after["states"] == agent_states
    assert after["reviewers"] != reviewers_before
