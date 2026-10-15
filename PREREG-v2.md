# Trust Gym v2: pre-registration

Written 2026-10-16, **before any v2 code**. Tagged `prereg-v2`. Corrections go in `DECISIONS.md` as dated entries.
New LLM spend: **$0** (offline only: T1 simulation and the committed T2 streams).

**Base policy** = the recommended v1 policy (REPORT-v1 "Recommended v1 policy"): per agent × task type, no pooling,
start L1, checks always on, promotion at ≥ 30 observations since the last change with the 95% Wilson upper bound
≤ ε, spot-checks 25% (L2) / 5% (L3), canaries 2%, one-level demotion (rolling Wilson lower bound over the last 50 > ε,
or an incident), version carry-over when hidden-test pass ≥ 0.8 and ≥ the previous version's, otherwise discount ½.

This round tests the decisions taken on 2026-10-16 (SPEC.md §7–§9, §15) before they are published as defaults.

## Definitions

- **Consequence level** per task type. T1 mapping: `low → C1`, `med → C2`, `high → C3`, `capped → C4`. T2 mapping:
  `meta.risk` `low/med/high/capped → C1/C2/C3/C4`.
- **Consequence bars** (SPEC §7 defaults): C1 ε 0.10, min success 0.85 · C2 ε 0.05, min success 0.90 · C3 ε 0.02,
  min success 0.95 · C4 never promotes.
- **Per-error cost** for cost-weighted escapes: C1 = 1, C2 = 3, C3 = 10, C4 = 30.
- **Task success.** *SPEC §7 currently defines success as "approved as-is or cosmetic", which equals "not serious"
  and would make the success bar redundant.* For v2, **success = the action achieved its goal**. A **non-serious
  failure** is an action that is not a serious error but did not achieve its goal (harmless but didn't do the job).
  - **T2:** `meta.task_success`. In the streams, every serious error also has `task_success = false`.
  - **T1:** each key gets a hidden non-serious failure probability `q ~ U(0.02, 0.15)`, independent of its error
    pattern; an action is a non-serious failure with probability `q` when it is not a serious error.
  - **Observation:** a reviewer who judges an action sees a non-serious failure with probability 0.95.
- **Success criterion:** promotion additionally needs the Wilson **lower** bound of the observed success rate ≥ the
  minimum.
- **Flat policy** (the comparison for C1): ε = 0.05 for every non-capped type, no success criterion, capped types
  (C4) never promote.
- **Reviews removed** = 1 − (pre-reviews + spot-checks + canaries) / (reviews under hold-everything).
- **Serious escapes per 100 auto actions** as in v0.
- **Cost-weighted escapes per 100 actions** = 100 × Σ(cost of each escaped serious error) / actions.

## Hypotheses and pass thresholds

**C1 Consequence bars beat a flat bar.** On T1 (200 worlds) and T2 good-full and sloppy-full (20 seeds each):
cost-weighted escapes per 100 actions ≤ the flat policy's, **and** reviews removed ≥ the flat policy's − 2 points.
PASS only if all three streams pass; MIXED if some do.

**C2 The C1 floor frees real work.** Restricted to C1 task types: ≥ 40% of reviews removed (C1 reviews vs C1
actions) **and** ≤ 1.0 serious escapes per 100 auto-executed C1 actions. T1 and T2 good-full + sloppy-full.

**C3 The success criterion adds value.** Consequence bars with vs without the success criterion: non-serious
failures among auto-executed actions fall ≥ 30%, at an automation cost ≤ 5 points. T1 and T2 good-full +
sloppy-full.

**F1 Evidence fading.** T1 with time: each world spans 365 days and actions are spread evenly over it. Two new
key patterns are added to every fading world, for one extra agent:
- **rare-then-drift:** 300 actions in days 0–60 at a 1% error rate, no actions in days 60–240, then 200 actions in
  days 240–365 at a 25% error rate;
- **steady-rare:** 150 actions spread evenly over the year at a 1% error rate.

Fading = before each decision and observation, evidence `n`, `err` (and success counts) are multiplied by
`0.5^(Δdays / half_life)` since that key's last update. If a key at L2+ then has upper bound > ε, it steps down one
level ("stale evidence"). Arms: no fading, half-life 90 days, half-life 180 days. **PASS for a setting** if serious
escapes on rare-then-drift keys fall ≥ 30% vs no fading **and** automation on the original T1 portfolio (same
worlds, excluding the two added keys) drops ≤ 3 points. 100 worlds. Adopt the setting that passes with the lower
automation cost. If none passes, keep no fading.

**R1 Reviewer trust.** T1 (100 worlds) with a pool of four human reviewers, each review assigned at random:
- A, catch 0.95;
- B, catch 0.85;
- C, catch 0.60;
- D, catch 0.95 falling linearly to 0.50 over the world.

There is no complacency model in R1 (fixed catch probabilities), to isolate the mechanism.
- **No reviewer trust:** single review.
- **Reviewer trust (SPEC §9):**
  - **Levels:** each reviewer starts at R1 (25% of their approvals get a second check by another randomly chosen
    reviewer at R2, or any reviewer if none is at R2). At R2 that drops to 5%.
  - **Evidence:** canaries (2% of their reviews; a miss is an error) plus second-check disagreements (the second
    reviewer catches a serious error the first missed: a miss for the first, and the action is blocked if not yet
    executed) plus incidents traced to their approval.
  - **Bar:** ε_rev = 0.10, n_min = 30, the same Wilson rules; one-level step-down.
- Agent policy = consequence bars in both arms.

**PASS** if total serious escapes fall ≥ 25% vs no reviewer trust, **and** review minutes (including second checks
and canaries) rise ≤ 15%, **and** the median number of reviews a bad reviewer performs at R2 while its true catch
rate is < 0.80 (C throughout; D after its crossing point) is ≤ 60.

**K1 Knowledge edits as versions.** T1 (100 worlds, steady patterns): each agent publishes a new version every
~50 of its actions (geometric, mean 50). At each version the agent's true error rates are multiplied by
`U(0.7, 1.0)` with probability 0.8 (an improvement or no change) or `U(2, 5)` with probability 0.2 (worse), capped
at 0.5.

Each (version, task type) gets a hidden-test pass rate `clip(1 − 3·rate + N(0, 0.04), 0, 1)`. Its Spearman ρ with
the true rate is measured and reported. The target is ρ ≈ −0.8, matching T2; the noise is fixed before running and
not tuned.

Arms: carry-over rule, always discount ½, always keep. **PASS** if carry-over's automation ≥ 80% of always-keep's
**and** carry-over's serious escapes ≤ 1.10 × always-discount's.

## Statistics and verdicts

Means over worlds/seeds with 95% bootstrap CIs where useful. Each hypothesis is PASS / FAIL / MIXED (across
streams). No threshold changes after the tag; post-hoc analyses are labelled exploratory.
