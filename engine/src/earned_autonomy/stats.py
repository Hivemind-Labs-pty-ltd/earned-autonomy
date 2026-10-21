"""Bounds used to decide promotion and step-down (EA-2.14, EA-2.17, EA-2.19).

The engine only talks to a `BoundStrategy`. Wilson score bounds are the default and the tested choice. An
anytime-valid strategy (a confidence sequence, safe under continuous monitoring) can be swapped in by
implementing the same two methods.
"""
from __future__ import annotations

import functools
import math
from typing import Protocol


class BoundStrategy(Protocol):
    """Interval on a serious-error rate from `serious_errors` serious errors in `judged` judged actions."""

    name: str

    def upper(self, serious_errors: float, judged: float) -> float:
        """Worst-case (upper) error rate. Promotion needs upper ≤ the error bar (EA-2.14)."""
        ...

    def lower(self, serious_errors: float, judged: float) -> float:
        """Best-case (lower) error rate. Step-down fires when the rolling lower > the error bar (EA-2.17)."""
        ...


class WilsonBound:
    """Wilson score interval (EA-2.14). Default confidence 95% (z = 1.96). [tested]"""

    name = "wilson"

    def __init__(self, z: float = 1.96):
        self.z = z

    def _parts(self, serious_errors: float, judged: float):
        z = self.z
        rate = serious_errors / judged
        denominator = 1 + z * z / judged
        centre = rate + z * z / (2 * judged)
        half_width = z * math.sqrt(max(0.0, rate * (1 - rate) / judged + z * z / (4 * judged * judged)))
        return centre, half_width, denominator

    def upper(self, serious_errors: float, judged: float) -> float:
        if judged <= 0:
            return 1.0
        centre, half_width, denominator = self._parts(serious_errors, judged)
        return min(1.0, (centre + half_width) / denominator)

    def lower(self, serious_errors: float, judged: float) -> float:
        if judged <= 0:
            return 0.0
        centre, half_width, denominator = self._parts(serious_errors, judged)
        return max(0.0, (centre - half_width) / denominator)


def _log_beta(first: float, second: float) -> float:
    return math.lgamma(first) + math.lgamma(second) - math.lgamma(first + second)


class ConfidenceSequenceBound:
    """Strict promotion (EA-2.19): a Beta-binomial mixture confidence sequence for a Bernoulli
    error rate (Robbins 1970; Howard et al. 2021). It stays valid under continuous monitoring, so re-checking after
    every outcome doesn't inflate false promotions.

    Prior Beta(prior_errors, prior_clean) with prior_errors = 1 and prior_clean = 1/error_bar − 1 (mean = the error
    bar), significance 0.05. The interval is every rate p with
    M(p) = B(a+e, b+n−e) / B(a, b) / (p^e (1−p)^(n−e)) < 1/significance, where e = serious errors and n = judged.
    Clean floors (0 errors): 10% → 46, 5% → 93, 2% → 236 judged actions (Wilson: 35 / 73 / 189).

    Used only for the promotion side (`upper`). Step-down keeps the rolling Wilson lower bound (EA-2.17).
    """

    name = "confidence_sequence"

    def __init__(self, error_bar: float, significance: float = 0.05):
        if not 0 < error_bar < 1:
            raise ValueError("error_bar must be in (0, 1)")
        self.error_bar, self.significance = error_bar, significance
        self.prior_errors, self.prior_clean = 1.0, 1.0 / error_bar - 1.0

    def _log_martingale(self, serious_errors: float, judged: float, rate: float) -> float:
        log_mixture = (_log_beta(self.prior_errors + serious_errors, self.prior_clean + judged - serious_errors)
                       - _log_beta(self.prior_errors, self.prior_clean))
        clean = judged - serious_errors
        log_likelihood = ((serious_errors * math.log(rate) if serious_errors > 0 else 0.0)
                          + (clean * math.log(1 - rate) if clean > 0 else 0.0))
        return log_mixture - log_likelihood

    def _edge(self, serious_errors: float, judged: float, upper: bool) -> float:
        errors = min(max(serious_errors, 0.0), judged)
        log_limit = math.log(1 / self.significance)
        centre = min(max(errors / judged, 1e-12), 1 - 1e-12)
        far = 1 - 1e-12 if upper else 1e-12
        if self._log_martingale(errors, judged, far) < log_limit:
            return 1.0 if upper else 0.0
        inside, outside = centre, far
        for _ in range(60):
            middle = (inside + outside) / 2
            if self._log_martingale(errors, judged, middle) < log_limit:
                inside = middle
            else:
                outside = middle
        return inside

    def upper(self, serious_errors: float, judged: float) -> float:
        if judged <= 0:
            return 1.0
        return min(1.0, self._edge(serious_errors, judged, True))

    def lower(self, serious_errors: float, judged: float) -> float:
        if judged <= 0:
            return 0.0
        return max(0.0, self._edge(serious_errors, judged, False))


def clean_floor(bound: BoundStrategy, error_bar: float, limit: int = 100_000) -> int:
    """Judged actions needed with no errors before upper ≤ the error bar (EA-1.5; spec/examples.md)."""
    judged = 1
    while bound.upper(0, judged) > error_bar:
        judged += 1
        if judged > limit:
            raise ValueError("no floor under limit")
    return judged


def wilson_upper(serious_errors: float, judged: float) -> float:
    return WilsonBound().upper(serious_errors, judged)


def wilson_lower(serious_errors: float, judged: float) -> float:
    return WilsonBound().lower(serious_errors, judged)


# ---- trust score (EA-1.14) and Core lookup tables (EA-2.15) ------------------------------------------------------


def _beta_continued_fraction(first: float, second: float, x: float) -> float:
    """Continued fraction for the regularised incomplete beta function (modified Lentz)."""
    tiny, epsilon = 1e-300, 3e-16
    total, plus, minus = first + second, first + 1.0, first - 1.0
    c, d = 1.0, 1.0 - total * x / plus
    d = 1.0 / (d if abs(d) > tiny else tiny)
    result = d
    for step in range(1, 10_000):
        double = 2 * step
        numerator = step * (second - step) * x / ((minus + double) * (first + double))
        d = 1.0 + numerator * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + numerator / c
        c = c if abs(c) > tiny else tiny
        result *= d * c
        numerator = -(first + step) * (total + step) * x / ((first + double) * (plus + double))
        d = 1.0 + numerator * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + numerator / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        result *= delta
        if abs(delta - 1.0) < epsilon:
            break
    return result


def regularized_incomplete_beta(x: float, first: float, second: float) -> float:
    """I_x(first, second): the Beta(first, second) cumulative probability at x."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = math.exp(math.lgamma(first + second) - math.lgamma(first) - math.lgamma(second)
                     + first * math.log(x) + second * math.log(1.0 - x))
    if x < (first + 1.0) / (first + second + 2.0):
        return front * _beta_continued_fraction(first, second, x) / first
    return 1.0 - front * _beta_continued_fraction(second, first, 1.0 - x) / second


def beta_quantile(probability: float, first: float, second: float) -> float:
    """The x with I_x(first, second) = probability (bisection)."""
    low, high = 0.0, 1.0
    for _ in range(80):
        middle = (low + high) / 2
        if regularized_incomplete_beta(middle, first, second) < probability:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def trust_score(serious_errors: float, judged: float, error_bar: float, prior: tuple[float, float] = (1.0, 1.0)) -> float:
    """EA-1.14: the posterior probability that the true serious-error rate is below the error bar, from a
    Beta(prior) prior and (weighted) evidence. With the default uniform prior, a score of at least 0.975 matches
    the 95% Wilson promotion rule to within 0-7 judged actions (spec/measure.md). A capped type (bar 0) scores 0."""
    if error_bar <= 0:
        return 0.0
    first = prior[0] + max(serious_errors, 0.0)
    second = prior[1] + max(judged - serious_errors, 0.0)
    return regularized_incomplete_beta(error_bar, first, second)


def posterior_interval(serious_errors: float, judged: float, prior: tuple[float, float] = (1.0, 1.0),
                       level: float = 0.95) -> tuple[float, float, float]:
    """(posterior mean, lower, upper) of the serious-error rate (EA-1.15)."""
    first = prior[0] + max(serious_errors, 0.0)
    second = prior[1] + max(judged - serious_errors, 0.0)
    tail = (1 - level) / 2
    return first / (first + second), beta_quantile(tail, first, second), beta_quantile(1 - tail, first, second)


def dial_spot_rate(score: float, gain: float = 5.0, floor: float = 0.02) -> float:
    """EA-2.22: the dial's spot-check rate once the trust score clears the threshold."""
    return min(max(gain * (1.0 - score) + floor, floor), 1.0)


@functools.lru_cache(maxsize=None)
def promotion_table(error_bar: float, max_errors: int = 10) -> tuple[int, ...]:
    """EA-2.15: judged actions needed to promote, by serious errors so far (0..max_errors), from the 95% Wilson
    upper bound. The Core lookup table. More than max_errors errors: no promotion from the table."""
    if error_bar <= 0:
        return ()
    bound, table = WilsonBound(), []
    for errors in range(max_errors + 1):
        judged = max(errors, 1)
        while bound.upper(errors, judged) > error_bar:
            judged += 1
        table.append(judged)
    return tuple(table)


@functools.lru_cache(maxsize=None)
def step_down_threshold(error_bar: float, window: int = 50) -> int | None:
    """EA-2.17 (Core form): the serious-error count in the last `window` judged actions at which the 95% Wilson
    lower bound first exceeds the error bar. C1 10, C2 6, C3 3."""
    if error_bar <= 0:
        return None
    bound = WilsonBound()
    for errors in range(window + 1):
        if bound.lower(errors, window) > error_bar:
            return errors
    return None
