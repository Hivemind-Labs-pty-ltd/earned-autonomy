"""Bounds (SPEC §7) and the worked example (SPEC §14)."""
from earned_autonomy.stats import WilsonBound, wilson_lower, wilson_upper


def first_promotion(error_bar, errors):
    judged = 1
    while wilson_upper(errors, judged) > error_bar:
        judged += 1
    return judged


def test_reviews_needed_table():
    # SPEC §7 table and the consequence table
    assert [first_promotion(error_bar, 0) for error_bar in (0.10, 0.05, 0.03, 0.02)] == [35, 73, 125, 189]
    assert [first_promotion(error_bar, 1) for error_bar in (0.10, 0.05, 0.03)] == [53, 110, 185]


def test_worked_example_numbers():
    assert round(wilson_upper(1, 112), 4) == 0.0488
    assert round(wilson_upper(1, 170), 4) == 0.0326
    assert wilson_upper(1, 185) <= 0.03 < wilson_upper(1, 184)


def test_edges():
    bound = WilsonBound()
    assert bound.upper(0, 0) == 1.0 and bound.lower(0, 0) == 0.0
    assert 0 <= wilson_lower(3, 10) < 0.3 < wilson_upper(3, 10) <= 1
