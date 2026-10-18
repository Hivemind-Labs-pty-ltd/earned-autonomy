"""Bounds used to decide promotion and step-down (SPEC §7).

The engine only talks to a `BoundStrategy`. Wilson score bounds are the default and the tested choice. An
anytime-valid strategy (a confidence sequence, safe under continuous monitoring) can be swapped in by
implementing the same two methods.
"""
from __future__ import annotations

import math
from typing import Protocol


class BoundStrategy(Protocol):
    """Interval on a serious-error rate from `err` errors in `n` judged actions."""

    name: str

    def upper(self, err: float, n: float) -> float:
        """Worst-case (upper) error rate. Promotion needs upper ≤ ε (SPEC §7)."""
        ...

    def lower(self, err: float, n: float) -> float:
        """Best-case (lower) error rate. Step-down fires when the rolling lower > ε (SPEC §7)."""
        ...


class WilsonBound:
    """Wilson score interval (SPEC §7). Default confidence 95% (z = 1.96). [tested]"""

    name = "wilson"

    def __init__(self, z: float = 1.96):
        self.z = z

    def _parts(self, err: float, n: float):
        z = self.z
        p = err / n
        d = 1 + z * z / n
        c = p + z * z / (2 * n)
        a = z * math.sqrt(max(0.0, p * (1 - p) / n + z * z / (4 * n * n)))
        return c, a, d

    def upper(self, err: float, n: float) -> float:
        if n <= 0:
            return 1.0
        c, a, d = self._parts(err, n)
        return min(1.0, (c + a) / d)

    def lower(self, err: float, n: float) -> float:
        if n <= 0:
            return 0.0
        c, a, d = self._parts(err, n)
        return max(0.0, (c - a) / d)


def _lbeta(a: float, b: float) -> float:
    return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)


class ConfidenceSequenceBound:
    """Strict promotion (SPEC §7, [exploratory v4]): a Beta-binomial mixture confidence sequence for a Bernoulli
    error rate (Robbins 1970; Howard et al. 2021). It stays valid under continuous monitoring, so re-checking after
    every outcome doesn't inflate false promotions.

    Prior Beta(a, b) with a = 1, b = 1/ε − 1 (mean ε, tuned to the bar), α = 0.05. The interval is every p with
    M_n(p) = B(a+e, b+n−e) / B(a, b) / (p^e (1−p)^(n−e)) < 1/α. Clean floors (0 errors): ε 10% → 46,
    5% → 93, 2% → 236 judged actions (Wilson: 35 / 73 / 189).

    Used only for the promotion side (`upper`). Step-down keeps the rolling Wilson lower bound (SPEC §7).
    """

    name = "cs-mix"

    def __init__(self, eps: float, alpha: float = 0.05):
        if not 0 < eps < 1:
            raise ValueError("eps must be in (0, 1)")
        self.eps, self.alpha = eps, alpha
        self.a, self.b = 1.0, 1.0 / eps - 1.0

    def _log_m(self, e: float, n: float, p: float) -> float:
        lmix = _lbeta(self.a + e, self.b + n - e) - _lbeta(self.a, self.b)
        ll = (e * math.log(p) if e > 0 else 0.0) + ((n - e) * math.log(1 - p) if n - e > 0 else 0.0)
        return lmix - ll

    def _edge(self, err: float, n: float, upper: bool) -> float:
        e = min(max(err, 0.0), n)
        lim = math.log(1 / self.alpha)
        centre = min(max(e / n, 1e-12), 1 - 1e-12)
        far = 1 - 1e-12 if upper else 1e-12
        if self._log_m(e, n, far) < lim:
            return 1.0 if upper else 0.0
        inside, outside = centre, far
        for _ in range(60):
            mid = (inside + outside) / 2
            if self._log_m(e, n, mid) < lim:
                inside = mid
            else:
                outside = mid
        return inside

    def upper(self, err: float, n: float) -> float:
        if n <= 0:
            return 1.0
        return min(1.0, self._edge(err, n, True))

    def lower(self, err: float, n: float) -> float:
        if n <= 0:
            return 0.0
        return max(0.0, self._edge(err, n, False))


def clean_floor(bound: BoundStrategy, eps: float, limit: int = 100_000) -> int:
    """Judged actions needed with no errors before upper ≤ ε (SPEC §7 table)."""
    n = 1
    while bound.upper(0, n) > eps:
        n += 1
        if n > limit:
            raise ValueError("no floor under limit")
    return n


def wilson_upper(err: float, n: float) -> float:
    return WilsonBound().upper(err, n)


def wilson_lower(err: float, n: float) -> float:
    return WilsonBound().lower(err, n)
