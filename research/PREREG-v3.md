# Trust Gym v3: pre-registration (confirmation round)

Written 2026-10-16, **before any v3 code**. Tagged `prereg-v3`. Nothing here changes after the tag; corrections go in
`DECISIONS.md` as dated superseding entries.

**Purpose.** v2 found three exploratory fixes after its pre-registered tests failed (`REPORT-v2.md`, `analyze_v2_explore.py`).
Post-hoc results can't be marked [tested] in SPEC.md. This round re-tests each fix **on seeds never used before**, with
thresholds fixed here, and produces the reference numbers for the published framework.

**Spend:** $0 (T1 simulation + committed T2 streams; no LLM calls).

## Base policy for every arm ("v3 policy")

The recommended v1 policy (per task type, no pooling, one-level demotion, start L1, checks always on, spot-checks
25% / 5%) plus the v2 consequence bars (C1 ε 10%, C2 5%, C3 2%, C4 never promotes), with:
- **success criterion OFF** (task success becomes an alert, not a promotion gate: v2 C3 failed);
- **no evidence fading** (v2 F1 failed);
- **canaries 5%** of reviews;
- engine: `gym/engine_v2.py` (`EngineV2`) with each fix implemented as in `analyze_v2_explore.py`, moved into a v3
  module unchanged in logic.

Each confirmation arm switches on **only its own fix** relative to the base, except the combined run.

## Seeds (all new)

| Use | Seeds |
|---|---|
| K1' hidden-test noise calibration | T1 version worlds 59 000–59 049 (used only to fix σ; not scored) |
| K1' scored | 60 000–60 099 |
| R1' | 70 000–70 099 |
| F1' | 80 000–80 099 |
| Combined v3 policy, T1 | 90 000–90 199 |
| Combined v3 policy, T2 good-full / sloppy-full | reviewer/engine seeds 100–119 |

Previously used: 0–199, 10 000+, 20 000+, 30 000+, 40 000+, 50 000+ (v0–v2). None reused.

## Hypotheses

**K1' Carry-over without "≥ previous".** On a version change, a task type keeps all its evidence if that version's
hidden-test pass rate ≥ 0.8; otherwise evidence is halved (and the type drops to L1 if its bound no longer holds).
Arms: carry (this rule), always-keep, always-discount. Worlds: `t1.world_v2.version_world` (new version every ~50
actions per agent; 20% of versions make the agent 2–5× worse).
- Two hidden-test models: (a) **as v2** (σ = 0.04, ρ ≈ −0.97); (b) **calibrated**: σ chosen on the calibration
  seeds so that the pooled Spearman ρ(hidden pass, true error rate) over all versions is −0.80 ± 0.03 (T2 measured
  −0.81). σ is searched over a grid (0.04–0.40, step 0.01), the first σ within the band is fixed and logged in
  DECISIONS.md before the scored run.
- **PASS** if, on the **calibrated** model, carry's mean automation ≥ 80% of always-keep's AND carry's mean escapes ≤
  1.10 × always-discount's. Model (a) is reported but does not decide the verdict.

**R1' Reviewer trust as quality control.** Pool of four reviewers per world: A catch 0.95, B 0.85, C 0.60, D degrading
0.95 → 0.50 over the world. Reviewer evidence = canaries (5% of reviews), second checks (clean second check = clean
evidence; a found error = a miss), and incidents traced to the reviewer's approval. ε_rev 10%, n_min 30, second
checks 25% at R1 and 5% at R2, same Wilson maths as agents. Comparison: the same pool with no reviewer trust (no
canaries, no second checks).
- **The v2 "escapes −25%" bar is deliberately dropped.** Reviewer trust is positioned as quality control (finding bad
  reviewers), not as an escape reducer, so the test is that it sorts reviewers correctly without making things worse.
- **PASS** if all three hold: (1) the bad reviewer C **ever** reaches R2 in ≤ 10% of worlds; (2) the good reviewer A is
  **at R2 at the end** of the world in ≥ 80% of worlds; (3) mean total escapes ≤ the no-reviewer-trust arm's.
- Also reported (no threshold): B and D outcomes, review minutes, D's reviews spent at R2 after its catch rate falls
  below 0.80.

**F1' Re-entry rule.** When a task type is acted on again after a gap of more than 60 days, it steps down one level
(if at L2+). No fading otherwise. Worlds: `t1.world_v2.fading_world` (main portfolio + a rare-then-drift C2 key + a
steady-rare C2 key over 365 days). Comparison: base (no re-entry rule).
- **PASS** if escapes on the rare-then-drift key fall ≥ 10% AND main-portfolio automation (the world without the extra
  agent) drops by ≤ 1.0 point.

## Combined v3 policy: reference numbers (no pass/fail)

Base + all three fixes (carry-over ≥ 0.8, reviewer trust where a reviewer pool exists, 60-day re-entry), on T1 main
worlds (`t1.world_v2.world`, single complacency reviewer as in v0, canaries 5%) and the T2 good-full and sloppy-full
streams (consequence from risk: low→C1, med→C2, high→C3, capped→C4). Each run is compared with arm A (hold everything)
on the same seeds. Reported with the v0 definitions:
- **H1 promotion precision:** share of promotions to L2+ whose true error over the key's next 200 own actions ≤ that
  key's ε (T1: true rate function; T2: empirical next 200 rows, needs ≥ 50).
- **H2 reviews removed** vs A (reviews include spot-checks and canaries), and escapes per 100 auto-executed actions.
- **H4 demotion latency:** median own-actions from the regression point to the first demotion, for regression keys
  (bad update, defector) at L2+ when the regression hits (T1 only).
- **Escapes per 100 actions** and **cost-weighted escapes per 100 actions** (C1 1, C2 3, C3 10, C4 30).
- **G2 ledger completeness:** share of auto-executed actions with a complete explanation row (level, evidence n and
  err, upper bound, ε, consequence, version, checks, policy version), level ≥ 2, not C4, checks passed.

## Statistics

Means over worlds (T1) or seeds (T2), with 95% bootstrap CIs for headline numbers. Each hypothesis gets PASS or FAIL.
Results are reported whether they pass or fail.
