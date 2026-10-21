"""MEASURE (EA-1.13 to EA-1.21), the Core lookup tables (EA-2.15), review timeouts (EA-3.18), retirement
(EA-5.4 to EA-5.6) and the agent interface additions (EA-7.10, EA-7.11)."""
import json
from pathlib import Path

import pytest
from helpers import AI_OWNER, AGENT, OK, POLICY_OWNER, act, engine, policy, promote_to, run_clean

from earned_autonomy import L1, L2, TrustEngine, TrustRecord
from earned_autonomy.stats import (WilsonBound, posterior_interval, promotion_table, regularized_incomplete_beta,
                                   step_down_threshold, trust_score)

SCHEMA = Path(__file__).resolve().parents[2] / "spec" / "schema"
BARS = {"C1": 0.10, "C2": 0.05, "C3": 0.02}
# research/core/core-tables.md: judged actions needed to promote, by serious mistakes 0..10
PUBLISHED = {
    "C1": (35, 53, 69, 84, 99, 113, 127, 140, 153, 166, 179),
    "C2": (73, 110, 142, 173, 202, 230, 257, 284, 311, 337, 363),
    "C3": (189, 280, 361, 437, 510, 581, 650, 718, 785, 851, 916),
}
STEP_DOWN = {"C1": 10, "C2": 6, "C3": 3}
C1 = "customer_service.status.update"
KEY = ("organisation", "customer_service_agent", C1)


# ---- trust score ------------------------------------------------------------------------------------------
@pytest.mark.covers("EA-1.14")
def test_incomplete_beta_matches_closed_forms():
    # Beta(1, b): I_x = 1 - (1 - x)^b ; Beta(a, 1): I_x = x^a
    for x in (0.01, 0.1, 0.5, 0.9):
        assert regularized_incomplete_beta(x, 1, 40) == pytest.approx(1 - (1 - x) ** 40, abs=1e-12)
        assert regularized_incomplete_beta(x, 7, 1) == pytest.approx(x ** 7, abs=1e-12)
    assert regularized_incomplete_beta(0.3, 4.5, 9.25) + regularized_incomplete_beta(0.7, 9.25, 4.5) == pytest.approx(1.0)


@pytest.mark.covers("EA-1.14", "EA-2.15")
def test_trust_score_matches_wilson_at_every_promotion_point():
    """Uniform prior, threshold 0.975: wherever the 95% Wilson rule promotes, the trust score is at least 0.975
    (0.975 to 0.979 across all 33 table cells); the score reaches 0.975 at most 7 judged actions earlier."""
    for consequence, bar in BARS.items():
        for errors, needed in enumerate(promotion_table(bar)):
            score = trust_score(errors, needed, bar)
            assert 0.975 <= score < 0.98, (consequence, errors, score)
            earliest = errors + 1
            while trust_score(errors, earliest, bar) < 0.975:
                earliest += 1
            assert 0 <= needed - earliest <= {"C1": 1, "C2": 2, "C3": 7}[consequence]


@pytest.mark.covers("EA-1.14")
def test_trust_score_capped_and_prior():
    assert trust_score(0, 10_000, 0.0) == 0.0
    assert trust_score(0, 0, 0.1) == pytest.approx(0.1)            # uniform prior, no evidence: P(p < 0.1) = 0.1
    mean, low, high = posterior_interval(2, 98)
    assert mean == pytest.approx(3 / 100) and low < mean < high
    assert regularized_incomplete_beta(high, 3, 97) == pytest.approx(0.975, abs=1e-9)


# ---- Core lookup tables (EA-2.15) ---------------------------------------------------------------------------
@pytest.mark.covers("EA-2.15")
def test_core_tables_equal_the_published_tables():
    for consequence, bar in BARS.items():
        assert promotion_table(bar) == PUBLISHED[consequence]
        assert step_down_threshold(bar) == STEP_DOWN[consequence]
        bound = WilsonBound()
        for errors, needed in enumerate(PUBLISHED[consequence]):
            assert bound.upper(errors, needed) <= bar < bound.upper(errors, needed - 1)


@pytest.mark.covers("EA-2.15", "EA-2.14", "EA-2.17")
def test_core_table_rule_makes_the_same_decisions_as_the_bound():
    """Same outcome stream, both rules: identical level history while the key has at most 10 serious errors.
    Beyond 10 the Core table holds the level (the published tables stop there) while the bound may still promote."""
    class EverySample:
        def random(self):
            return 0.0

    def history(rule, actions=330):
        trust_engine = engine(policy=policy(promotion_rule=rule), sampler=EverySample())
        for index in range(actions):
            action = act(C1)
            decision = trust_engine.decide(action, OK)
            serious = 200 <= index < 210
            label = "material_edit" if serious else "approved"
            reason = "wrong_fact" if serious else None
            if decision.allowed:
                trust_engine.mark_executed(action.action_id)
                trust_engine.record_outcome(action.action_id, label, reason, "spot_check", "reviewer")
            else:
                trust_engine.record_outcome(action.action_id, label, reason, "pre_review", "reviewer")
        return [(change["to"], change["why"]) for change in trust_engine.level_changes()]
    bound, table = history("bound"), history("core_table")
    assert bound == table and any(why == "evidence" for _, why in bound) and any(why == "rolling_bound" for _, why in bound)
    assert promotion_table(0.10)[-1] == 179 and len(promotion_table(0.10)) == 11       # 0..10 errors, then stay


# ---- trust profile, summary, record (EA-1.13, EA-1.15, EA-1.16) ---------------------------------------------
@pytest.mark.covers("EA-1.15", "EA-1.17")
def test_trust_profile_contents():
    trust_engine = engine()
    run_clean(trust_engine, 40)
    profile = trust_engine.trust_report("organisation", "customer_service_agent", C1)["profiles"][0]
    for field in ("trust_score", "estimated_error_rate", "error_rate_interval", "effective_evidence", "evidence_by_source",
                  "freshness", "trend", "autonomy_setting", "implied_autonomy"):
        assert field in profile
    judged = trust_engine.get_state(*KEY)[0]["judged_count"]
    assert profile["evidence_by_source"]["human"] == {"judged": judged, "serious": 0, "weight": 1.0}
    assert profile["effective_evidence"] == judged
    assert profile["trust_score"] == pytest.approx(trust_score(0, judged, 0.10), abs=1e-6)
    assert profile["thin_evidence"] == (judged < promotion_table(0.10)[0])
    assert profile["autonomy_setting"] == "trusted" and profile["implied_autonomy"] == "trusted_or_above"
    assert profile["freshness"]["agent_version"] == "v1" and profile["freshness"]["last_evidence_at"]
    low, high = profile["error_rate_interval"]
    assert low < profile["estimated_error_rate"] < high
    assert trust_engine.trust_score(*KEY) == pytest.approx(profile["trust_score"], abs=1e-6)


@pytest.mark.covers("EA-1.16")
def test_agent_trust_summary():
    trust_engine = engine()
    promote_to(trust_engine, L2)
    run_clean(trust_engine, 10, "customer_service.reply.send")
    action = act(C1)
    trust_engine.decide(action, OK)
    trust_engine.mark_executed(action.action_id)
    trust_engine.report_incident(action.action_id, "serious", "customer")
    summary = trust_engine.trust_report("organisation", "customer_service_agent")["summary"]
    assert summary["task_types"] == 2 and summary["incidents"] == 1 and summary["incidents_last_30_days"] == 1
    share = summary["share_of_actions_by_setting"]
    assert set(share) == {"supervised"} and share["supervised"] == pytest.approx(1.0)   # the incident stepped C1 down
    assert sum(summary["trends"].values()) == 2


@pytest.mark.covers("EA-1.13")
def test_trust_report_is_derived_from_the_record():
    trust_engine = engine()
    run_clean(trust_engine, 60)
    trust_engine.record_evidence("organisation", "customer_service_agent", C1, "shadow", False, "evaluator")
    rebuilt = TrustEngine(record=trust_engine.record, clock=trust_engine.clock)
    before = trust_engine.trust_report("organisation", "customer_service_agent")
    after = rebuilt.trust_report("organisation", "customer_service_agent")
    assert before["profiles"] == after["profiles"]


# ---- evidence sources (EA-1.17 to EA-1.21) ------------------------------------------------------------------
@pytest.mark.covers("EA-1.18")
def test_non_human_evidence_counts_at_its_weight():
    trust_engine = engine(policy=policy(evidence_weights={"human": 1.0, "shadow": 0.5, "replay": 0.25, "test": 0.0}))
    run_clean(trust_engine, 10)
    for index in range(20):
        trust_engine.record_evidence(*KEY, "shadow", index == 0, "evaluator")
        trust_engine.record_evidence(*KEY, "replay", False, "evaluator")
        trust_engine.record_evidence(*KEY, "test", True, "evaluator")
    profile = trust_engine.trust_report(*KEY[:2], C1)["profiles"][0]
    assert profile["effective_evidence"] == pytest.approx(10 + 20 * 0.5 + 20 * 0.25)
    assert profile["trust_score"] == pytest.approx(trust_score(0.5, 25, 0.10), abs=1e-6)
    assert profile["evidence_by_source"]["test"] == {"judged": 20, "serious": 20, "weight": 0.0}
    with pytest.raises(ValueError):
        trust_engine.record_evidence(*KEY, "human", False, "evaluator")


@pytest.mark.covers("EA-1.18", "EA-4.7")
def test_version_discount_applies_to_every_source():
    trust_engine = engine()
    for _ in range(10):
        trust_engine.record_evidence(*KEY, "replay", False, "evaluator")
    run_clean(trust_engine, 1)
    trust_engine.on_version_published("customer_service_agent", "v2")
    trust_engine.decide(act(C1, version="v2"), OK)
    profile = trust_engine.trust_report(*KEY[:2], C1)["profiles"][0]
    assert profile["evidence_by_source"]["replay"]["judged"] == pytest.approx(5)


@pytest.mark.covers("EA-1.20")
def test_alert_when_human_evidence_share_is_too_small():
    trust_engine = engine(policy=policy(evidence_weights={"human": 1.0, "shadow": 1.0, "replay": 0.5, "test": 0.0}))
    run_clean(trust_engine, 5)
    for _ in range(50):
        trust_engine.record_evidence(*KEY, "shadow", False, "evaluator")
    profile = trust_engine.trust_report(*KEY[:2], C1)["profiles"][0]
    assert "human_evidence_share_below_minimum" in profile["alerts"]


@pytest.mark.covers("EA-1.21", "EA-1.12")
def test_non_human_evidence_never_changes_the_autonomy_setting():
    trust_engine = engine(policy=policy(evidence_weights={"human": 1.0, "shadow": 1.0, "replay": 1.0, "test": 1.0}))
    for _ in range(500):
        trust_engine.record_evidence(*KEY, "replay", False, "evaluator")
    assert trust_engine.get_state(*KEY)[0]["level"] == L1
    assert trust_engine.decide(act(C1), OK).why == "level_L1"
    profile = trust_engine.trust_report(*KEY[:2], C1)["profiles"][0]
    assert profile["implied_autonomy"] == "trusted_or_above" and profile["autonomy_setting"] == "supervised"


# ---- OVERSEE: no action on timeout (EA-3.18) ----------------------------------------------------------------
@pytest.mark.covers("EA-3.18")
def test_held_action_never_runs_without_a_reviewer():
    trust_engine = engine()
    action = act(C1)
    assert not trust_engine.decide(action, OK).allowed
    trust_engine.test_clock.advance(days=365)
    assert not trust_engine.may_execute(action.action_id)
    with pytest.raises(PermissionError):
        trust_engine.mark_executed(action.action_id)


# ---- RETIRE (EA-5.4 to EA-5.6) -----------------------------------------------------------------------------
@pytest.mark.covers("EA-5.4")
def test_retired_task_type_is_held_and_recorded():
    trust_engine = engine()
    promote_to(trust_engine, L2)
    assert not trust_engine.retire(AGENT, *KEY)
    assert trust_engine.retire(AI_OWNER, *KEY, reason="no longer offered")
    assert trust_engine.decide(act(C1), OK).why == "retired"
    assert any(entry.type == "retire" for entry in trust_engine.record.entries())
    assert trust_engine.decide(act("customer_service.reply.send"), OK).why == "level_L1"   # other types unaffected


@pytest.mark.covers("EA-5.5", "EA-2.13")
def test_narrowed_or_split_task_type_starts_supervised():
    trust_engine = engine()
    promote_to(trust_engine, L2)
    assert trust_engine.add_task_type(AI_OWNER, "customer_service.status.update_bulk", "C1")
    assert any(entry.type == "policy" for entry in list(trust_engine.record.entries())[1:])
    assert trust_engine.decide(act("customer_service.status.update_bulk"), OK).why == "level_L1"


@pytest.mark.covers("EA-5.6")
def test_reactivated_task_type_starts_supervised_with_discounted_evidence():
    trust_engine = engine()
    promote_to(trust_engine, L2)
    judged = trust_engine.get_state(*KEY)[0]["judged_count"]
    trust_engine.retire(POLICY_OWNER, *KEY)
    assert trust_engine.reactivate(POLICY_OWNER, *KEY)
    state = trust_engine.get_state(*KEY)[0]
    assert state["level"] == L1 and state["judged_count"] == pytest.approx(judged * 0.5)
    assert trust_engine.decide(act(C1), OK).why == "level_L1"


# ---- agent interface (EA-7.10, EA-7.11) ----------------------------------------------------------------------
@pytest.mark.covers("EA-7.11")
def test_every_proposed_action_carries_a_version():
    schema = json.loads((SCHEMA / "proposed-action.schema.json").read_text())
    assert "agent_version" in schema["required"]
    trust_engine = engine()
    decision = trust_engine.decide(act(C1, version="v7"), OK)
    assert decision.agent_version == "v7"
    assert trust_engine.get_state(*KEY)[0]["agent_version"] == "v7"


def test_record_types_known_to_schema():
    schema = json.loads((SCHEMA / "record-entry.schema.json").read_text())
    trust_engine = engine()
    trust_engine.record_evidence(*KEY, "shadow", False, "evaluator")
    trust_engine.retire(AI_OWNER, *KEY)
    trust_engine.reactivate(AI_OWNER, *KEY)
    assert {entry.type for entry in trust_engine.record.entries()} <= set(schema["properties"]["type"]["enum"])
    assert isinstance(trust_engine.record, TrustRecord)


@pytest.mark.covers("EA-1.18")
def test_tests_are_never_the_only_evidence_for_trust():
    trust_engine = engine()
    for _ in range(200):
        trust_engine.record_evidence(*KEY, "test", False, "evaluator")
    profile = trust_engine.trust_report(*KEY[:2], C1)["profiles"][0]
    assert profile["trust_score"] >= 0.975 and profile["implied_autonomy"] == "supervised"
    trust_engine.record_evidence(*KEY, "replay", False, "evaluator")
    assert trust_engine.trust_report(*KEY[:2], C1)["profiles"][0]["implied_autonomy"] == "trusted_or_above"


@pytest.mark.covers("EA-2.22")
def test_dial_setting_from_the_trust_score():
    from earned_autonomy import dial_spot_rate
    assert dial_spot_rate(1.0) == pytest.approx(0.02)
    assert dial_spot_rate(0.975) == pytest.approx(0.145)
    assert dial_spot_rate(0.5) == 1.0
    trust_engine = engine()
    run_clean(trust_engine, 5)
    assert trust_engine.trust_report(*KEY[:2], C1)["profiles"][0]["dial"] == {"pre_review": True, "spot_check_rate": None}
    run_clean(trust_engine, 80)
    dial = trust_engine.trust_report(*KEY[:2], C1)["profiles"][0]["dial"]
    assert dial["pre_review"] is False and 0.02 <= dial["spot_check_rate"] < 0.145


@pytest.mark.covers("EA-2.21")
def test_every_decision_menu_option_is_recorded():
    trust_engine = engine()
    promote_to(trust_engine, L2)
    before = sum(1 for entry in trust_engine.record.entries() if entry.type == "governance")
    trust_engine.promote(POLICY_OWNER, *KEY)                                       # increase autonomy
    trust_engine.demote(POLICY_OWNER, *KEY)                                        # increase oversight
    trust_engine.add_task_type(AI_OWNER, "customer_service.status.update_eu", "C1")   # narrow scope
    trust_engine.pause(POLICY_OWNER, *KEY)                                         # pause
    trust_engine.resume(POLICY_OWNER, *KEY)
    trust_engine.retire(POLICY_OWNER, *KEY)                                        # retire
    logged = [entry.body for entry in trust_engine.record.entries() if entry.type == "governance"][before:]
    assert [body["operation"] for body in logged] == ["promote", "demote", "add_task_type", "pause", "resume", "retire"]
