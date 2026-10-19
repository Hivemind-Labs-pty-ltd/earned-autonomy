"""Account-level hard stop for T2: OpenRouter's own usage counter, polled (cached 20s)."""
import json
import time
import urllib.request

from t2.llm import api_key

BASELINE_USD = 129.35   # total_usage at Trust Gym start (2026-10-15)
STOP_AT_USD = 147.35    # $18 for T2
_cache = {"at": 0.0, "usage": None}


class BudgetStop(RuntimeError):
    pass


def usage(max_age_s=20.0) -> float:
    now = time.time()
    if _cache["usage"] is not None and now - _cache["at"] < max_age_s:
        return _cache["usage"]
    req = urllib.request.Request("https://openrouter.ai/api/v1/credits",
                                 headers={"Authorization": f"Bearer {api_key()}"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                _cache.update(at=now, usage=float(json.load(r)["data"]["total_usage"]))
            return _cache["usage"]
        except OSError:
            time.sleep(2 * (attempt + 1))
    if _cache["usage"] is not None:      # network blip: keep the last known value rather than crash a run
        return _cache["usage"]
    raise BudgetStop("cannot read OpenRouter usage")


def check(stage=""):
    u = usage()
    if u >= STOP_AT_USD:
        raise BudgetStop(f"[{stage}] T2 budget hit: usage {u:.2f} >= {STOP_AT_USD}")
    return u - BASELINE_USD


if __name__ == "__main__":
    print(f"T2 spent so far (account-wide since baseline): ${usage() - BASELINE_USD:.2f}")
