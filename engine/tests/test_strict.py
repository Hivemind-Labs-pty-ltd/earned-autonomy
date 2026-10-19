"""Strict promotion (SPEC §7, [exploratory v4]): the Beta-binomial mixture confidence sequence."""
import random
import sys
from pathlib import Path

import pytest
from helpers import FAIL, OK, act, engine, policy, promote_to, run_clean

from earned_autonomy import L1, L2, ConfidenceSequenceBound, WilsonBound, clean_floor

GYM = Path.home() / "Sites/hivemind-trust-gym"


def level(trust_engine, task_type="customer_service.status.update"):
    state = trust_engine.get_state("organisation", "customer_service_agent", task_type)
    return state[0]["level"] if state else L1


def test_clean_floors_match_report_v4():
    assert [clean_floor(ConfidenceSequenceBound(error_bar), error_bar) for error_bar in (0.10, 0.05, 0.02)] == [46, 93, 236]
    assert [clean_floor(WilsonBound(), error_bar) for error_bar in (0.10, 0.05, 0.02)] == [35, 73, 189]


def test_bounds_bracket_the_rate_and_tighten():
    confidence_sequence = ConfidenceSequenceBound(0.05)
    assert confidence_sequence.lower(5, 100) < 0.05 < confidence_sequence.upper(5, 100)
    assert confidence_sequence.upper(5, 100) > confidence_sequence.upper(50, 1000) > 0.05            # more evidence, tighter
    assert confidence_sequence.upper(0, 0) == 1.0 and confidence_sequence.lower(0, 0) == 0.0
    world = WilsonBound()
    assert confidence_sequence.upper(1, 200) > world.upper(1, 200)                      # stricter than Wilson at the same evidence
    with pytest.raises(ValueError):
        ConfidenceSequenceBound(0.0)


@pytest.mark.skipif(not (GYM / "gym/engine_v4.py").exists(), reason="Trust Gym not present")
def test_parity_with_trust_gym_v4():
    sys.path.insert(0, str(GYM))
    from gym.engine_v4 import cs_upper
    for error_bar in (0.10, 0.05, 0.02):
        confidence_sequence = ConfidenceSequenceBound(error_bar)
        for n in (5, 30, 46, 93, 236, 500, 2000):
            for err in (0, 1, 2, 5, 20):
                if err <= n:
                    assert confidence_sequence.upper(err, n) == pytest.approx(cs_upper(err, n, 1.0, 1.0 / error_bar - 1.0), abs=1e-9)


def test_strict_selected_by_consequence_level_delays_promotion():
    trust_engine = engine(policy=policy(strict_promotion=["C1"]))
    run_clean(trust_engine, 45)
    assert level(trust_engine) == L1
    run_clean(trust_engine, 1)
    assert level(trust_engine) == L2                                           # 46, not Wilson's 35
    state_rows = trust_engine.get_state("organisation", "customer_service_agent", "customer_service.status.update")[0]
    assert state_rows["bound"] == "confidence_sequence"


def test_strict_selected_by_task_type_only_affects_that_type():
    trust_engine = engine(policy=policy(strict_promotion=["customer_service.status.update"]))
    assert trust_engine.policy.is_strict("customer_service.status.update") and not trust_engine.policy.is_strict("customer_service.reply.send")
    run_clean(trust_engine, 35)
    assert level(trust_engine) == L1                                           # Wilson would have promoted at 35
    decision = trust_engine.decide(act("customer_service.reply.send"), OK)
    assert decision.upper_bound == pytest.approx(WilsonBound().upper(0, 0))


def test_default_is_wilson_everywhere():
    trust_engine = engine()
    run_clean(trust_engine, 35)
    assert level(trust_engine) == L2
    assert trust_engine.get_state("organisation", "customer_service_agent", "customer_service.status.update")[0]["bound"] == "wilson"


def test_strict_promotion_still_steps_down_on_errors_and_replays():
    trust_engine = engine(policy=policy(strict_promotion=["C1"]))
    promote_to(trust_engine, L2)
    for _ in range(40):
        action = act()
        decision = trust_engine.decide(action, OK)
        if decision.allowed:
            trust_engine.mark_executed(action.action_id)
        source = "spot_check" if decision.allowed else "pre_review"
        trust_engine.record_outcome(action.action_id, "rejected", "wrong_fact", source, "reviewer")
        if level(trust_engine) == L1:
            break
    assert level(trust_engine) == L1
    assert trust_engine.rebuild_state() == trust_engine.live_state()


def test_anytime_validity_under_continuous_monitoring():
    """An agent whose true error rate is above the bar should almost never be promoted, even though the bound is
    re-checked after every outcome. With the confidence sequence that probability is ≤ α (0.05)."""
    error_bar, p_true, runs, steps = 0.05, 0.065, 200, 1500
    confidence_sequence = ConfidenceSequenceBound(error_bar)
    random_source = random.Random(7)
    promoted = 0
    for _ in range(runs):
        trust_engine = 0
        for n in range(1, steps + 1):
            trust_engine += random_source.random() < p_true
            if n >= 30 and trust_engine / n < error_bar and confidence_sequence.upper(trust_engine, n) <= error_bar:
                promoted += 1
                break
    assert promoted / runs <= 0.08
