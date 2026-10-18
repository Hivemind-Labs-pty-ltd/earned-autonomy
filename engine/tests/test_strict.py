"""Strict promotion (SPEC §7, [exploratory v4]): the Beta-binomial mixture confidence sequence."""
import random
import sys
from pathlib import Path

import pytest
from helpers import FAIL, OK, act, engine, policy, promote_to, run_clean

from earned_autonomy import L1, L2, ConfidenceSequenceBound, WilsonBound, clean_floor

GYM = Path.home() / "Sites/hivemind-trust-gym"


def level(e, tt="cs.status.update"):
    s = e.get_state("org", "cs", tt)
    return s[0]["level"] if s else L1


def test_clean_floors_match_report_v4():
    assert [clean_floor(ConfidenceSequenceBound(eps), eps) for eps in (0.10, 0.05, 0.02)] == [46, 93, 236]
    assert [clean_floor(WilsonBound(), eps) for eps in (0.10, 0.05, 0.02)] == [35, 73, 189]


def test_bounds_bracket_the_rate_and_tighten():
    cs = ConfidenceSequenceBound(0.05)
    assert cs.lower(5, 100) < 0.05 < cs.upper(5, 100)
    assert cs.upper(5, 100) > cs.upper(50, 1000) > 0.05            # more evidence, tighter
    assert cs.upper(0, 0) == 1.0 and cs.lower(0, 0) == 0.0
    w = WilsonBound()
    assert cs.upper(1, 200) > w.upper(1, 200)                      # stricter than Wilson at the same evidence
    with pytest.raises(ValueError):
        ConfidenceSequenceBound(0.0)


@pytest.mark.skipif(not (GYM / "gym/engine_v4.py").exists(), reason="Trust Gym not present")
def test_parity_with_trust_gym_v4():
    sys.path.insert(0, str(GYM))
    from gym.engine_v4 import cs_upper
    for eps in (0.10, 0.05, 0.02):
        cs = ConfidenceSequenceBound(eps)
        for n in (5, 30, 46, 93, 236, 500, 2000):
            for err in (0, 1, 2, 5, 20):
                if err <= n:
                    assert cs.upper(err, n) == pytest.approx(cs_upper(err, n, 1.0, 1.0 / eps - 1.0), abs=1e-9)


def test_strict_selected_by_consequence_level_delays_promotion():
    e = engine(policy=policy(strict_promotion=["C1"]))
    run_clean(e, 45)
    assert level(e) == L1
    run_clean(e, 1)
    assert level(e) == L2                                           # 46, not Wilson's 35
    st = e.get_state("org", "cs", "cs.status.update")[0]
    assert st["bound"] == "cs-mix"


def test_strict_selected_by_task_type_only_affects_that_type():
    e = engine(policy=policy(strict_promotion=["cs.status.update"]))
    assert e.policy.is_strict("cs.status.update") and not e.policy.is_strict("cs.reply.send")
    run_clean(e, 35)
    assert level(e) == L1                                           # Wilson would have promoted at 35
    d = e.decide(act("cs.reply.send"), OK)
    assert d.upper_bound == pytest.approx(WilsonBound().upper(0, 0))


def test_default_is_wilson_everywhere():
    e = engine()
    run_clean(e, 35)
    assert level(e) == L2
    assert e.get_state("org", "cs", "cs.status.update")[0]["bound"] == "wilson"


def test_strict_promotion_still_steps_down_on_errors_and_replays():
    e = engine(policy=policy(strict_promotion=["C1"]))
    promote_to(e, L2)
    for _ in range(40):
        a = act()
        d = e.decide(a, OK)
        if d.allowed:
            e.mark_executed(a.action_id)
        src = "spot_check" if d.allowed else "pre_review"
        e.record_outcome(a.action_id, "rejected", "wrong_fact", src, "rev")
        if level(e) == L1:
            break
    assert level(e) == L1
    assert e.rebuild_state() == e.live_state()


def test_anytime_validity_under_continuous_monitoring():
    """An agent whose true error rate is above the bar should almost never be promoted, even though the bound is
    re-checked after every outcome. With the confidence sequence that probability is ≤ α (0.05)."""
    eps, p_true, runs, steps = 0.05, 0.065, 200, 1500
    cs = ConfidenceSequenceBound(eps)
    rng = random.Random(7)
    promoted = 0
    for _ in range(runs):
        e = 0
        for n in range(1, steps + 1):
            e += rng.random() < p_true
            if n >= 30 and e / n < eps and cs.upper(e, n) <= eps:
                promoted += 1
                break
    assert promoted / runs <= 0.08
