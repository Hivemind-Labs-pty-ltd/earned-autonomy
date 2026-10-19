"""Behaviour of decide / update / versions / oversight (SPEC §4–§9, §11)."""
import random

import pytest
from helpers import AI_OWNER, AUDITOR, BUILDER, FAIL, OK, POLICY_OWNER, REVIEWER, act, engine, promote_to, run_clean

from earned_autonomy import (L1, L2, L3, ChecksResult, ProposedAction, RuleTagger, TagResult, TrustEngine,
                             is_serious)


def level(trust_engine, task_type="customer_service.status.update", agent="customer_service_agent"):
    state = trust_engine.get_state("organisation", agent, task_type)
    return state[0]["level"] if state else L1


# ---- decide order (§6) -------------------------------------------------------------------------------------
def test_new_type_starts_supervised():
    trust_engine = engine()
    decision = trust_engine.decide(act(), OK)
    assert (decision.mode, decision.why, decision.level) == ("hold", "level_L1", L1)


def test_unknown_type_and_low_confidence_hold():
    trust_engine = engine()
    assert trust_engine.decide(act("customer_service.unknown.thing"), OK).why == "unknown_type"
    assert trust_engine.decide(act(tag_confidence=0.5), OK).why == "low_confidence"


def test_tagger_used_when_type_missing():
    tagger = RuleTagger([(lambda action: action.kind == "tool.call", "customer_service.status.update")])
    trust_engine = engine(tagger=tagger)
    action = ProposedAction("t1", "organisation", "customer_service_agent", "v1", "tool.call", {})
    trust_engine.decide(action, OK)
    assert action.task_type == "customer_service.status.update" and action.tag_confidence == 1.0

    class Unsure:
        def tag(self, action):
            return TagResult("customer_service.status.update", 0.6)

    e2 = engine(tagger=Unsure())
    assert e2.decide(ProposedAction("t2", "organisation", "customer_service_agent", "v1", "tool.call", {}), OK).why == "low_confidence"


def test_checks_missing_or_failed_hold_at_every_level():
    trust_engine = engine()
    promote_to(trust_engine, L2)
    assert trust_engine.decide(act(), None).why == "checks_missing"
    assert trust_engine.decide(act(), FAIL).why == "check_failed"
    assert trust_engine.decide(act(), OK).mode == "act"


def test_promotion_matches_consequence_floor():
    # C1 (ε 10%): first promotion after 35 clean judged actions
    trust_engine = engine()
    run_clean(trust_engine, 34)
    assert level(trust_engine) == L1
    run_clean(trust_engine, 1)
    assert level(trust_engine) == L2


def test_c4_never_promotes():
    trust_engine = engine()
    run_clean(trust_engine, 400, "customer_service.payment.release")
    assert level(trust_engine, "customer_service.payment.release") == L1
    assert trust_engine.decide(act("customer_service.payment.release"), OK).why == "capped"


def test_rolling_bound_steps_down_one_level():
    trust_engine = engine()
    promote_to(trust_engine, L3)
    for _ in range(200):                         # a burst of serious errors on spot-checks and incidents
        action = act()
        decision = trust_engine.decide(action, OK)
        if decision.allowed:
            trust_engine.mark_executed(action.action_id)
            trust_engine.record_outcome(action.action_id, "rejected", "wrong_fact", "spot_check", "reviewer")
        else:
            trust_engine.record_outcome(action.action_id, "rejected", "wrong_fact", "pre_review", "reviewer")
        if level(trust_engine) == L2:
            break
    assert level(trust_engine) == L2
    whys = [c["why"] for c in trust_engine.level_changes()]
    assert "rolling_bound" in whys


def test_cosmetic_and_incomplete_are_not_serious():
    assert not is_serious("cosmetic_edit", "tone")
    assert not is_serious("material_edit", "wording")
    assert not is_serious("incomplete", None)
    assert is_serious("rejected", "wrong_amount")
    trust_engine = engine()
    action = act()
    trust_engine.decide(action, OK)
    with pytest.raises(ValueError):
        trust_engine.record_outcome(action.action_id, "rejected", None, "pre_review", "reviewer")     # reason code required


def test_success_alert_is_not_a_gate():
    trust_engine = engine()
    for _ in range(60):
        action = act()
        trust_engine.decide(action, OK)
        trust_engine.record_outcome(action.action_id, "incomplete", None, "pre_review", "reviewer")
    state_rows = trust_engine.get_state("organisation", "customer_service_agent", "customer_service.status.update")[0]
    assert "task_success_below_minimum" in state_rows["alerts"]
    assert state_rows["level"] == L2                     # incomplete is harmless: it still earns trust


# ---- re-entry (§7) ------------------------------------------------------------------------------------------
def test_reentry_after_60_days_steps_down():
    trust_engine = engine()
    promote_to(trust_engine, L2)
    trust_engine.test_clock.advance(days=61)
    decision = trust_engine.decide(act(), OK)
    assert decision.level == L1 and decision.mode == "hold"
    assert trust_engine.level_changes()[-1]["why"] == "reentry_gap"


def test_no_reentry_within_gap():
    trust_engine = engine()
    promote_to(trust_engine, L2)
    trust_engine.test_clock.advance(days=59)
    assert trust_engine.decide(act(), OK).mode == "act"


# ---- versions (§8) -----------------------------------------------------------------------------------------
def test_carry_over_keeps_evidence():
    trust_engine = engine()
    promote_to(trust_engine, L2)
    n_before = trust_engine.get_state("organisation", "customer_service_agent")[0]["judged_count"]
    trust_engine.suites.seed_hidden("customer_service.status.update", [(f"h{i}", {}) for i in range(12)])
    out = trust_engine.on_version_published("customer_service_agent", "v2", {"customer_service.status.update": {"hidden_pass": 0.9, "training_pass": 1.0}})
    assert out["customer_service.status.update"]["carry"] and out["customer_service.status.update"]["hidden_test_count"] == 12
    state_rows = trust_engine.get_state("organisation", "customer_service_agent")[0]
    assert state_rows["judged_count"] == n_before and state_rows["level"] == L2 and state_rows["agent_version"] == "v2"
    assert trust_engine.decide(act(version="v2"), OK).mode == "act"


def test_failed_or_small_hidden_suite_discounts():
    trust_engine = engine()
    promote_to(trust_engine, L2)
    n_before = trust_engine.get_state("organisation", "customer_service_agent")[0]["judged_count"]
    out = trust_engine.on_version_published("customer_service_agent", "v2", {"customer_service.status.update": {"hidden_pass": 0.95, "hidden_test_count": 4}})
    assert not out["customer_service.status.update"]["carry"]              # fewer than 10 hidden tests
    state_rows = trust_engine.get_state("organisation", "customer_service_agent")[0]
    assert state_rows["judged_count"] == pytest.approx(n_before * 0.5)
    assert state_rows["level"] == L1                                 # bound no longer holds at half the evidence


def test_unannounced_version_is_discounted():
    trust_engine = engine()
    promote_to(trust_engine, L2)
    n_before = trust_engine.get_state("organisation", "customer_service_agent")[0]["judged_count"]
    trust_engine.decide(act(version="v9"), OK)
    assert trust_engine.get_state("organisation", "customer_service_agent")[0]["judged_count"] == pytest.approx(n_before * 0.5)


def test_correction_tests_split_and_seeded_hidden():
    trust_engine = engine()
    for i in range(300):
        trust_engine.suites.add_correction_test(f"c{i}", "customer_service.reply.send", {})
    h = trust_engine.suites.hidden_count("customer_service.reply.send")
    assert 60 < h < 140                                      # about a third hidden
    trust_engine.suites.seed_hidden("customer_service.reply.send", [("s1", {}), ("s2", {})])
    assert trust_engine.suites.hidden_count("customer_service.reply.send") == h + 2


# ---- incidents (§7) ----------------------------------------------------------------------------------------
def test_incident_applies_to_the_actions_version():
    trust_engine = engine()
    promote_to(trust_engine, L2)
    action = act()
    trust_engine.decide(action, OK)
    trust_engine.mark_executed(action.action_id)
    trust_engine.suites.seed_hidden("customer_service.status.update", [(f"h{i}", {}) for i in range(12)])
    trust_engine.on_version_published("customer_service_agent", "v2", {"customer_service.status.update": {"hidden_pass": 1.0}})
    inc = trust_engine.report_incident(action.action_id, "high", "ops", note="customer complained")
    assert inc["agent_version"] == "v1" and inc["note_hash"].startswith("sha256:")
    assert level(trust_engine) == L1


# ---- oversight (§9) ----------------------------------------------------------------------------------------
def test_pause_and_resume_per_type_and_agent():
    trust_engine = engine()
    promote_to(trust_engine, L2)
    assert trust_engine.pause(REVIEWER, "organisation", "customer_service_agent", "customer_service.status.update")
    assert trust_engine.decide(act(), OK).why == "paused"
    assert trust_engine.resume(AI_OWNER, "organisation", "customer_service_agent", "customer_service.status.update")
    assert trust_engine.decide(act(), OK).mode == "act"
    assert trust_engine.pause(AI_OWNER, "organisation", "customer_service_agent")
    assert trust_engine.decide(act("customer_service.reply.send"), OK).why == "paused"


def test_spot_sampling_rate_and_queue():
    trust_engine = engine()
    promote_to(trust_engine, L2)
    hits = 0
    for _ in range(2000):
        action = act()
        trust_engine.decide(action, OK)
        trust_engine.mark_executed(action.action_id)
        if any(item["action_id"] == action.action_id and item["kind"] == "spot_check" for item in trust_engine.review_queue()):
            hits += 1
            trust_engine.record_outcome(action.action_id, "approved", None, "spot_check", "reviewer")
        if level(trust_engine) != L2:
            break
    assert hits > 0


def test_reviewer_trust_sorts_reviewers():
    trust_engine = engine()
    random_source = random.Random(1)
    for _ in range(400):
        trust_engine.record_second_check("organisation", "good", "customer_service.reply.send", found_error=random_source.random() < 0.02)
        trust_engine.record_second_check("organisation", "poor", "customer_service.reply.send", found_error=random_source.random() < 0.40)
    assert trust_engine.reviewer_level("organisation", "good", "customer_service.reply.send") == 2
    assert trust_engine.reviewer_level("organisation", "poor", "customer_service.reply.send") == 1
    assert trust_engine.reviewer_level("organisation", "nobody", "customer_service.reply.send") == 1


def test_reviewer_miss_on_incident_after_approval():
    trust_engine = engine()
    action = act()
    trust_engine.decide(action, OK)
    trust_engine.record_outcome(action.action_id, "approved", None, "pre_review", "rex")
    trust_engine.mark_executed(action.action_id)
    trust_engine.report_incident(action.action_id, "high", "ops")
    reviewer_trust_key = "organisation|rex|review.customer_service.status.update"
    assert trust_engine.live_state()["reviewers"][reviewer_trust_key]["serious_error_count"] == 1


# ---- policy (§7, §10) --------------------------------------------------------------------------------------
def test_error_bar_can_only_tighten():
    trust_engine = engine()
    assert trust_engine.set_task_error_bar(POLICY_OWNER, "customer_service.reply.send", 0.03)
    with pytest.raises(ValueError):
        trust_engine.set_task_error_bar(POLICY_OWNER, "customer_service.reply.send", 0.08)


def test_lowering_error_bar_reevaluates_trusted_keys():
    trust_engine = engine()
    promote_to(trust_engine, L2, "customer_service.reply.send")
    assert trust_engine.set_task_error_bar(POLICY_OWNER, "customer_service.reply.send", 0.005)
    assert level(trust_engine, "customer_service.reply.send") == L1


def test_tools_for_task_type():
    trust_engine = engine()
    assert trust_engine.tools_for("customer_service.refund.issue") == ["lookup_order", "issue_refund"]


def test_catalogue_owned_by_ai_owner():
    trust_engine = engine()
    assert trust_engine.add_task_type(AI_OWNER, "customer_service.address.update", "C2")
    assert not trust_engine.add_task_type(POLICY_OWNER, "customer_service.other.thing", "C1")
    assert trust_engine.set_consequence(AI_OWNER, "customer_service.address.update", "C3")
    assert trust_engine.policy.task_types["customer_service.address.update"].consequence == "C3"


# ---- multi-agent (§4, §11) ---------------------------------------------------------------------------------
def test_delegation_cap():
    trust_engine = engine()
    promote_to(trust_engine, L2, agent="billing")
    parent = act(agent="customer_service_agent")
    trust_engine.decide(parent, OK)
    child = act(agent="billing", parent_action_id=parent.action_id)
    decision = trust_engine.decide(child, OK)
    assert decision.mode == "hold" and decision.why == "delegation_cap"


def test_bundle_most_restrictive():
    trust_engine = engine()
    promote_to(trust_engine, L2)
    decisions = trust_engine.decide_bundle([(act(), OK), (act("customer_service.payment.release"), OK)])
    assert [decision.mode for decision in decisions] == ["hold", "hold"]


def test_task_type_catalogue_entry_keeps_description_and_examples():
    """SPEC §4: a task type is a catalogue entry. Description and examples survive policy versioning."""
    trust_engine = engine()
    assert trust_engine.add_task_type(
        AI_OWNER, "customer_service.address.update", "C2", tools=["update_address"],
        description="Change the delivery address on an order that hasn't shipped. Out of scope: billing details.",
        examples=["Please send my order to my work address", "I moved, update my address for order 88"])
    version = trust_engine.policy.policy_version
    assert trust_engine.set_consequence(AI_OWNER, "customer_service.address.update", "C3")
    assert trust_engine.set_task_error_bar(POLICY_OWNER, "customer_service.address.update", 0.01)
    entry = trust_engine.policy.task_types["customer_service.address.update"]
    assert trust_engine.policy.policy_version == version + 2
    assert entry.consequence == "C3" and entry.error_bar == 0.01 and entry.tools == ["update_address"]
    assert entry.description.startswith("Change the delivery address")
    assert entry.examples == ["Please send my order to my work address", "I moved, update my address for order 88"]
    # the entry is in the record, so a replay rebuilds it exactly
    assert trust_engine.rebuild_state() == trust_engine.live_state()
