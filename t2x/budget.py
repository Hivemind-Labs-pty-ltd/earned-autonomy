"""Hard stop on OpenRouter spend for a T2-10x run: stop when account usage passes (usage at run start + cap).

Cap from env TRUST_GYM_CAP_USD (default 5). Uses OpenRouter's own usage counter, polled and cached for 20s.
"""
import os

from t2 import budget as _t2

CAP = float(os.environ.get("TRUST_GYM_CAP_USD") or 5.0)
_start = {"usage": None}


class BudgetStop(RuntimeError):
    pass


def start() -> float:
    """TRUST_GYM_BASELINE_USD (if set) pins the start to the experiment's starting usage, so every process shares
    one cap; otherwise the start is the usage when this run began."""
    base = os.environ.get("TRUST_GYM_BASELINE_USD")
    _start["usage"] = float(base) if base else _t2.usage(max_age_s=0)
    return _start["usage"]


def check(stage=""):
    if _start["usage"] is None:
        start()
    u = _t2.usage()
    if u >= _start["usage"] + CAP:
        raise BudgetStop(f"[{stage}] T2-10x cap hit: usage {u:.2f} >= {_start['usage']:.2f} + {CAP:.2f}")
    return u - _start["usage"]


def spent() -> float:
    return _t2.usage(max_age_s=0) - (_start["usage"] or 0.0)
