"""Bounds used to decide promotion and step-down (SPEC §7).

The engine only talks to a `BoundStrategy`. Wilson score bounds are the default and the tested choice. An
anytime-valid strategy (a confidence sequence, safe under continuous monitoring) can be swapped in by
implementing the same two methods.
"""
from __future__ import annotations

import math
from typing import Protocol


class BoundStrategy(Protocol):
    """Interval on a serious-error rate from `serious_errors` serious errors in `judged` judged actions."""

    name: str

    def upper(self, serious_errors: float, judged: float) -> float:
        """Worst-case (upper) error rate. Promotion needs upper ≤ the error bar (SPEC §7)."""
        ...

    def lower(self, serious_errors: float, judged: float) -> float:
        """Best-case (lower) error rate. Step-down fires when the rolling lower > the error bar (SPEC §7)."""
        ...


class WilsonBound:
    """Wilson score interval (SPEC §7). Default confidence 95% (z = 1.96). [tested]"""

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
    """Strict promotion (SPEC §7, [exploratory v4]): a Beta-binomial mixture confidence sequence for a Bernoulli
    error rate (Robbins 1970; Howard et al. 2021). It stays valid under continuous monitoring, so re-checking after
    every outcome doesn't inflate false promotions.

    Prior Beta(prior_errors, prior_clean) with prior_errors = 1 and prior_clean = 1/error_bar − 1 (mean = the error
    bar), significance 0.05. The interval is every rate p with
    M(p) = B(a+e, b+n−e) / B(a, b) / (p^e (1−p)^(n−e)) < 1/significance, where e = serious errors and n = judged.
    Clean floors (0 errors): 10% → 46, 5% → 93, 2% → 236 judged actions (Wilson: 35 / 73 / 189).

    Used only for the promotion side (`upper`). Step-down keeps the rolling Wilson lower bound (SPEC §7).
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
    """Judged actions needed with no errors before upper ≤ the error bar (SPEC §7 table)."""
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
