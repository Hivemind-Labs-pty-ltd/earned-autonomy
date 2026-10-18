"""Behaviour of decide / update / versions / oversight (SPEC §4–§9, §11)."""
import random

import pytest
from helpers import AI_OWNER, AUDITOR, BUILDER, FAIL, OK, POLICY_OWNER, REVIEWER, act, engine, promote_to, run_clean

from earned_autonomy import (L1, L2, L3, ChecksResult, ProposedAction, RuleTagger, TagResult, TrustEngine,
                             is_serious)


def level(e, tt="cs.status.update", agent="cs"):
    s = e.get_state("org", agent, tt)
    return s[0]["level"] if s else L1


# ---- decide order (§6) -------------------------------------------------------------------------------------
def test_new_type_starts_supervised():
    e = engine()
    d = e.decide(act(), OK)
    assert (d.mode, d.why, d.level) == ("hold", "level_L1", L1)


def test_unknown_type_and_low_confidence_hold():
    e = engine()
    assert e.decide(act("cs.unknown.thing"), OK).why == "unknown_type"
    assert e.decide(act(tag_confidence=0.5), OK).why == "low_confidence"


def test_tagger_used_when_type_missing():
    tagger = RuleTagger([(lambda a: a.kind == "tool.call", "cs.status.update")])
    e = engine(tagger=tagger)
    a = ProposedAction("t1", "org", "cs", "v1", "tool.call", {})
    e.decide(a, OK)
    assert a.task_type == "cs.status.update" and a.tag_confidence == 1.0

    class Unsure:
        def tag(self, action):
            return TagResult("cs.status.update", 0.6)

    e2 = engine(tagger=Unsure())
    assert e2.decide(ProposedAction("t2", "org", "cs", "v1", "tool.call", {}), OK).why == "low_confidence"


def test_checks_missing_or_failed_hold_at_every_level():
    e = engine()
    promote_to(e, L2)
    assert e.decide(act(), None).why == "checks_missing"
    assert e.decide(act(), FAIL).why == "check_failed"
    assert e.decide(act(), OK).mode == "act"


def test_promotion_matches_consequence_floor():
    # C1 (ε 10%): first promotion after 35 clean judged actions
    e = engine()
    run_clean(e, 34)
    assert level(e) == L1
    run_clean(e, 1)
    assert level(e) == L2


def test_c4_never_promotes():
    e = engine()
    run_clean(e, 400, "cs.payment.release")
    assert level(e, "cs.payment.release") == L1
    assert e.decide(act("cs.payment.release"), OK).why == "capped"


def test_rolling_bound_steps_down_one_level():
    e = engine()
    promote_to(e, L3)
    for _ in range(200):                         # a burst of serious errors on spot-checks and incidents
        a = act()
        d = e.decide(a, OK)
        if d.allowed:
            e.mark_executed(a.action_id)
            e.record_outcome(a.action_id, "rejected", "wrong_fact", "spot_check", "rev")
        else:
            e.record_outcome(a.action_id, "rejected", "wrong_fact", "pre_review", "rev")
        if level(e) == L2:
            break
    assert level(e) == L2
    whys = [c["why"] for c in e.level_changes()]
    assert "rolling_bound" in whys


def test_cosmetic_and_incomplete_are_not_serious():
    assert not is_serious("cosmetic_edit", "tone")
    assert not is_serious("material_edit", "wording")
    assert not is_serious("incomplete", None)
    assert is_serious("rejected", "wrong_amount")
    e = engine()
    a = act()
    e.decide(a, OK)
    with pytest.raises(ValueError):
        e.record_outcome(a.action_id, "rejected", None, "pre_review", "rev")     # reason code required


def test_success_alert_is_not_a_gate():
    e = engine()
    for _ in range(60):
        a = act()
        e.decide(a, OK)
        e.record_outcome(a.action_id, "incomplete", None, "pre_review", "rev")
    st = e.get_state("org", "cs", "cs.status.update")[0]
    assert "task_success_below_minimum" in st["alerts"]
    assert st["level"] == L2                     # incomplete is harmless: it still earns trust


# ---- re-entry (§7) ------------------------------------------------------------------------------------------
def test_reentry_after_60_days_steps_down():
    e = engine()
    promote_to(e, L2)
    e.test_clock.advance(days=61)
    d = e.decide(act(), OK)
    assert d.level == L1 and d.mode == "hold"
    assert e.level_changes()[-1]["why"] == "reentry_gap"


def test_no_reentry_within_gap():
    e = engine()
    promote_to(e, L2)
    e.test_clock.advance(days=59)
    assert e.decide(act(), OK).mode == "act"


# ---- versions (§8) -----------------------------------------------------------------------------------------
def test_carry_over_keeps_evidence():
    e = engine()
    promote_to(e, L2)
    n_before = e.get_state("org", "cs")[0]["n"]
    e.suites.seed_hidden("cs.status.update", [(f"h{i}", {}) for i in range(12)])
    out = e.on_version_published("cs", "v2", {"cs.status.update": {"hidden_pass": 0.9, "training_pass": 1.0}})
    assert out["cs.status.update"]["carry"] and out["cs.status.update"]["n_hidden"] == 12
    st = e.get_state("org", "cs")[0]
    assert st["n"] == n_before and st["level"] == L2 and st["agent_version"] == "v2"
    assert e.decide(act(version="v2"), OK).mode == "act"


def test_failed_or_small_hidden_suite_discounts():
    e = engine()
    promote_to(e, L2)
    n_before = e.get_state("org", "cs")[0]["n"]
    out = e.on_version_published("cs", "v2", {"cs.status.update": {"hidden_pass": 0.95, "n_hidden": 4}})
    assert not out["cs.status.update"]["carry"]              # fewer than 10 hidden tests
    st = e.get_state("org", "cs")[0]
    assert st["n"] == pytest.approx(n_before * 0.5)
    assert st["level"] == L1                                 # bound no longer holds at half the evidence


def test_unannounced_version_is_discounted():
    e = engine()
    promote_to(e, L2)
    n_before = e.get_state("org", "cs")[0]["n"]
    e.decide(act(version="v9"), OK)
    assert e.get_state("org", "cs")[0]["n"] == pytest.approx(n_before * 0.5)


def test_correction_tests_split_and_seeded_hidden():
    e = engine()
    for i in range(300):
        e.suites.add_correction_test(f"c{i}", "cs.reply.send", {})
    h = e.suites.hidden_count("cs.reply.send")
    assert 60 < h < 140                                      # about a third hidden
    e.suites.seed_hidden("cs.reply.send", [("s1", {}), ("s2", {})])
    assert e.suites.hidden_count("cs.reply.send") == h + 2


# ---- incidents (§7) ----------------------------------------------------------------------------------------
def test_incident_applies_to_the_actions_version():
    e = engine()
    promote_to(e, L2)
    a = act()
    e.decide(a, OK)
    e.mark_executed(a.action_id)
    e.suites.seed_hidden("cs.status.update", [(f"h{i}", {}) for i in range(12)])
    e.on_version_published("cs", "v2", {"cs.status.update": {"hidden_pass": 1.0}})
    inc = e.report_incident(a.action_id, "high", "ops", note="customer complained")
    assert inc["agent_version"] == "v1" and inc["note_hash"].startswith("sha256:")
    assert level(e) == L1


# ---- oversight (§9) ----------------------------------------------------------------------------------------
def test_pause_and_resume_per_type_and_agent():
    e = engine()
    promote_to(e, L2)
    assert e.pause(REVIEWER, "org", "cs", "cs.status.update")
    assert e.decide(act(), OK).why == "paused"
    assert e.resume(AI_OWNER, "org", "cs", "cs.status.update")
    assert e.decide(act(), OK).mode == "act"
    assert e.pause(AI_OWNER, "org", "cs")
    assert e.decide(act("cs.reply.send"), OK).why == "paused"


def test_spot_sampling_rate_and_queue():
    e = engine()
    promote_to(e, L2)
    hits = 0
    for _ in range(2000):
        a = act()
        e.decide(a, OK)
        e.mark_executed(a.action_id)
        if any(q["action_id"] == a.action_id and q["kind"] == "spot_check" for q in e.review_queue()):
            hits += 1
            e.record_outcome(a.action_id, "approved", None, "spot_check", "rev")
        if level(e) != L2:
            break
    assert hits > 0


def test_reviewer_trust_sorts_reviewers():
    e = engine()
    rng = random.Random(1)
    for _ in range(400):
        e.record_second_check("org", "good", "cs.reply.send", found_error=rng.random() < 0.02)
        e.record_second_check("org", "poor", "cs.reply.send", found_error=rng.random() < 0.40)
    assert e.reviewer_level("org", "good", "cs.reply.send") == 2
    assert e.reviewer_level("org", "poor", "cs.reply.send") == 1
    assert e.reviewer_level("org", "nobody", "cs.reply.send") == 1


def test_reviewer_miss_on_incident_after_approval():
    e = engine()
    a = act()
    e.decide(a, OK)
    e.record_outcome(a.action_id, "approved", None, "pre_review", "rex")
    e.mark_executed(a.action_id)
    e.report_incident(a.action_id, "high", "ops")
    rk = "org|rex|review.cs.status.update"
    assert e.live_state()["reviewers"][rk]["err"] == 1


# ---- policy (§7, §10) --------------------------------------------------------------------------------------
def test_eps_can_only_tighten():
    e = engine()
    assert e.set_task_eps(POLICY_OWNER, "cs.reply.send", 0.03)
    with pytest.raises(ValueError):
        e.set_task_eps(POLICY_OWNER, "cs.reply.send", 0.08)


def test_lowering_eps_reevaluates_trusted_keys():
    e = engine()
    promote_to(e, L2, "cs.reply.send")
    assert e.set_task_eps(POLICY_OWNER, "cs.reply.send", 0.005)
    assert level(e, "cs.reply.send") == L1


def test_tools_for_task_type():
    e = engine()
    assert e.tools_for("cs.refund.issue") == ["lookup_order", "issue_refund"]


def test_catalogue_owned_by_ai_owner():
    e = engine()
    assert e.add_task_type(AI_OWNER, "cs.address.update", "C2")
    assert not e.add_task_type(POLICY_OWNER, "cs.other.thing", "C1")
    assert e.set_consequence(AI_OWNER, "cs.address.update", "C3")
    assert e.policy.task_types["cs.address.update"].consequence == "C3"


# ---- multi-agent (§4, §11) ---------------------------------------------------------------------------------
def test_delegation_cap():
    e = engine()
    promote_to(e, L2, agent="billing")
    parent = act(agent="cs")
    e.decide(parent, OK)
    child = act(agent="billing", parent_action_id=parent.action_id)
    d = e.decide(child, OK)
    assert d.mode == "hold" and d.why == "delegation_cap"


def test_bundle_most_restrictive():
    e = engine()
    promote_to(e, L2)
    ds = e.decide_bundle([(act(), OK), (act("cs.payment.release"), OK)])
    assert [d.mode for d in ds] == ["hold", "hold"]
