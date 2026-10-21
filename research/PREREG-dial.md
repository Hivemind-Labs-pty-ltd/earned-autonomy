# Pre-registration: round "dial" (a continuous autonomy setting)

Written 2026-10-21, before any code for this round. Tagged `research/prereg-dial`. Nothing here changes after the tag;
corrections go in `DECISIONS.md`. New LLM spend: **$0** (offline).

## Question

In the lifecycle, the DECIDE step can set autonomy as discrete levels (the Core ladder) or as a continuous **dial**:
oversight in proportion to uncertainty. Does the dial raise **the multiple** (completed tasks per human hour against
doing the work by hand) without letting more serious mistakes through or detecting regressions more slowly?

## Arms

Both arms use identical evidence rules: judged outcomes (pre-review and spot-check verdicts from the same reviewer
model), canaries at 5% of reviews, incidents adding a serious error, the Core step-down trigger (serious mistakes in the
last 50 judged reach C1 10 · C2 6 · C3 3), at least 30 judged since the last change before acting again, checks-flagged
actions always held, C4 always held.

- **Ladder:** Core + canaries (`core.policy_core.core_config(canaries=True)`): promotion by the lookup table, Supervised →
  Trusted (25% spot-checks) → Senior (5%).
- **Dial:** trust score `s = BetaCDF(bar; 1 + errors, 1 + judged − errors)` on the same counts.
  - **Hold for pre-review** while s < 0.95, or within 30 judged of the last change.
  - **When acting,** spot-check with probability `clip(k × (1 − s) + floor, floor, 1)`, with **k = 5** and
    **floor = 0.02**. At s = 0.95 that's 27%, about the ladder's 25%; at 0.99, 7%; at 0.999, 2.5%.
  - **Step-down** by the same trigger, or on an incident, back to pre-review. Counts are kept, as in the ladder.

## Data and metrics

- **Data:** T1 main worlds, seeds 150 000–150 199 (new). T2 good-full and sloppy-full streams, seeds 600–619.
- **The multiple** = total manual minutes / total human minutes. Manual minutes: C1 2 · C2 4 · C3 6 · C4 6. Every review
  (pre-review, spot-check, canary) is 1.0 minute. Reported over the whole stream and over the last third.
- **Serious escapes per 100 actions.**
- **Median actions to demote a regression (T1):** from the regression point to the first step-down, for keys acting
  alone when it hits. Same definition as the core round.
- **Also reported:** the share done without a person, undeserved promotions, and the mean spot-check rate.

## Hypotheses (pass marks fixed now)

- **DIAL1:** dial's multiple ≥ 1.1 × the ladder's (whole stream).
- **DIAL2:** dial's serious escapes ≤ ladder + 0.1 per 100.
- **DIAL3:** dial's median regression demotion ≤ ladder + 5 actions (T1).

DIAL1 and DIAL2 are graded on T1 and both T2 streams: PASS if they hold on all three, MIXED if on some, FAIL if on none.
DIAL3 is graded on T1 only. Every result is reported, including failures.
