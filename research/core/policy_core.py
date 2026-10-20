"""Core: the seven-rule policy, driven by lookup tables instead of statistics (PREREG-core.md).

Built on the v3 engine so the reviewer, spot-check and incident models are identical across arms; only the trust
rules differ. Ablation switches add Full features back one at a time.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from gym.engine import wilson_lower, wilson_upper
from gym.engine_v3 import ConfigV3, EngineV3

ERROR_BARS = {"C1": 0.10, "C2": 0.05, "C3": 0.02}
MAX_TABLE_ERRORS = 10
WINDOW = 50


def promotion_table(error_bar: float, max_errors: int = MAX_TABLE_ERRORS) -> list[int]:
    """Judged actions needed to promote with k serious mistakes so far (k = 0..max_errors).

    The smallest total for which the 95% Wilson upper bound is at or under the error bar, so on integer counts the
    table reproduces the Full promotion rule exactly."""
    table = []
    for errors in range(max_errors + 1):
        judged = max(errors, 1)
        while wilson_upper(errors, judged) > error_bar:
            judged += 1
        table.append(judged)
    return table


def step_down_threshold(error_bar: float, window: int = WINDOW) -> int:
    """Fewest serious mistakes in a full window whose 95% Wilson lower bound exceeds the error bar."""
    return next(t for t in range(window + 1) if wilson_lower(t, window) > error_bar)


PROMOTION = {consequence: promotion_table(bar) for consequence, bar in ERROR_BARS.items()}
STEP_DOWN = {consequence: step_down_threshold(bar) for consequence, bar in ERROR_BARS.items()}


@dataclass
class ConfigCore(ConfigV3):
    wilson_step_down: bool = False     # ablation: Full's rolling Wilson lower bound instead of the fixed threshold
    carry: bool = False                # ablation: Full's version rule (carry-over at hidden pass >= 0.8)


def core_config(**ablation) -> ConfigCore:
    """Core as pre-registered: no canaries, no re-entry, no carry-over, table rules."""
    base = dict(success_criterion=False, canary_rate=0.0, reentry_gap=None, version_mode="discount",
                carry_no_prev=False)
    if ablation.pop("canaries", False):
        base["canary_rate"] = 0.05
    if ablation.pop("reentry", False):
        base["reentry_gap"] = 60.0
    carry = ablation.pop("carry", False)
    if carry:
        base.update(version_mode="carry", carry_no_prev=True)
    return ConfigCore(carry=carry, **base, **ablation)


class EngineCore(EngineV3):
    def table_met(self, state, consequence) -> bool:
        if consequence not in PROMOTION:
            return False
        errors = int(state.err)
        return errors <= MAX_TABLE_ERRORS and state.n >= PROMOTION[consequence][errors]

    def st(self, action):
        key = (action.agent, action.task_type)
        if not self.cfg.carry and key in self.state and self.state[key].version != action.version:
            state = self.state[key]
            state.n = math.floor(state.n / 2)
            state.err = math.floor(state.err / 2)
            state.fail = math.floor(state.fail / 2)
            if state.level >= 2 and not self.table_met(state, action.meta["cons"]):
                self._set(key, state, 1, "version_change")
            state.version = action.version
        return super().st(action)

    def observe(self, key, state, consequence, error, failure):
        state.n += 1
        state.err += error
        state.fail += failure
        state.since += 1
        state.recent.append(error)
        if state.level >= 2 and consequence in ERROR_BARS:
            if self.cfg.wilson_step_down:
                if len(state.recent) >= 10 and wilson_lower(sum(state.recent), len(state.recent)) > \
                        ERROR_BARS[consequence]:
                    self._set(key, state, state.level - 1, "rolling_bound")
                    return
            elif sum(state.recent) >= STEP_DOWN[consequence]:
                self._set(key, state, state.level - 1, "step_down_table")
                return
        if consequence == "C4" or consequence not in ERROR_BARS or state.level >= 3 or state.since < self.cfg.n_min:
            return
        if self.table_met(state, consequence):
            self._set(key, state, state.level + 1, "table")
