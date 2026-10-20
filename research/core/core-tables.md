# Core lookup tables

Derived from the 95% Wilson bounds, so a team can apply the Earned Autonomy rules with counting alone. Source:
`core/policy_core.py` (`promotion_table`, `step_down_threshold`). Round: `PREREG-core.md`.

## Promotion: judged actions needed, by serious mistakes so far

A task type moves up one level when its total judged actions reach the number for its total serious mistakes, and at
least 30 judged actions have passed since its last level change. Critical (C4) work never promotes.

| Serious mistakes so far | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| **C1 Low** (bar 10%) | 35 | 53 | 69 | 84 | 99 | 113 | 127 | 140 | 153 | 166 | 179 |
| **C2 Moderate** (bar 5%) | 73 | 110 | 142 | 173 | 202 | 230 | 257 | 284 | 311 | 337 | 363 |
| **C3 High** (bar 2%) | 189 | 280 | 361 | 437 | 510 | 581 | 650 | 718 | 785 | 851 | 916 |

More than 10 serious mistakes: stay at the current level.

## Step down: mistakes that trigger it

Count serious mistakes among the judged actions since the task type's last level change (at most the last 50). Step
down one level when the count reaches:

| Consequence | Mistakes in the last 50 judged |
|---|--:|
| **C1 Low** | 10 |
| **C2 Moderate** | 6 |
| **C3 High** | 3 |

Any incident also steps the task type down one level straight away.
