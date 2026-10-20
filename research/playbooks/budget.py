"""Hard stop for the playbooks round: $15 of new OpenRouter spend above the usage recorded when the round started.

The start usage is written once to report/raw/playbooks-budget.json, so every process shares one cap.
"""
import json
from pathlib import Path

from t2 import budget as _t2

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "report/raw/playbooks-budget.json"
CAP_USD = 15.0


class BudgetStop(RuntimeError):
    pass


def start_usage() -> float:
    if STATE.exists():
        return json.loads(STATE.read_text())["start_usage"]
    u = _t2.usage(max_age_s=0)
    STATE.write_text(json.dumps({"start_usage": u, "cap_usd": CAP_USD}))
    return u


def check(stage=""):
    s = start_usage()
    u = _t2.usage()
    if u >= s + CAP_USD:
        raise BudgetStop(f"[{stage}] playbooks cap hit: usage {u:.2f} >= {s:.2f} + {CAP_USD:.2f}")
    return u - s


def spent() -> float:
    return _t2.usage(max_age_s=0) - start_usage()
