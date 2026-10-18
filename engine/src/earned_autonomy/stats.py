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


def wilson_upper(err: float, n: float) -> float:
    return WilsonBound().upper(err, n)


def wilson_lower(err: float, n: float) -> float:
    return WilsonBound().lower(err, n)
