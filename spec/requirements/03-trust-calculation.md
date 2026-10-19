# 3. Trust calculation

How judged actions become a trust level: what counts as evidence, when a task type climbs, and when it steps down.
The [examples page](../examples.md) walks through the maths in plain language.

## EA-3.1 Only judged actions are evidence
- **Statement:** Only judged actions (pre-review outcomes, spot-check outcomes and incidents) MUST count as evidence, and autonomous actions nobody judged MUST NOT count as evidence of good work.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** Silence isn't approval.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.record_outcome`, `TrustEngine.report_incident`
- **Test:** `conformance/test_evidence_rules.py::test_unjudged_autonomous_actions_are_not_evidence`

## EA-3.2 Pre-review and spot-check outcomes weigh the same
- **Statement:** An outcome from a spot-check MUST carry the same weight as an outcome from a pre-review.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** Both are a person judging real work.
- **Evidence:** The policy tested in every round weighs them equally ([research/REPORT.md](../../research/REPORT.md); [research/REPORT-v3.md](../../research/REPORT-v3.md)).
- **Implementation:** `engine.py` `TrustEngine.record_outcome`
- **Test:** `conformance/test_evidence_rules.py::test_spot_check_and_pre_review_outcomes_weigh_the_same`

## EA-3.3 What counts as a serious error
- **Statement:** An outcome MUST count as a serious error when it is labelled `material_edit` or `rejected` with a serious reason code, or when it is an incident, and cosmetic edits and `incomplete` outcomes MUST NOT count as serious errors.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** Trust is about consequential mistakes: a wrong or unauthorised action, a made-up fact or amount, a promise the policy doesn't allow, or obeying an instruction hidden in a message. Wording and tone are taste.
- **Evidence:** The definition used in every tier ([research/REPORT.md](../../research/REPORT.md)).
- **Implementation:** `models.py` `is_serious`, `SERIOUS_REASONS`, `COSMETIC_REASONS`
- **Test:** `engine/tests/test_engine.py::test_cosmetic_and_incomplete_are_not_serious`
- **Notes:** Reason codes are listed in EA-5.3.

## EA-3.4 Promotion
- **Statement:** A trust key below L3 Senior MUST be promoted one level when it has at least `min_judged` (default 30) judged actions since its last level change and the upper bound of its serious-error rate (95% Wilson score interval by default) is at or below its error bar, and MUST NOT be promoted otherwise.
- **Condition:** The task type is not C4 Critical or otherwise capped (EA-2.5).
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** Promote only when even the plausible worst case is under the bar. With no errors, the worst case is roughly 4 ÷ the number judged.
- **Evidence:** 93.3% of promotions were deserved in simulation and 99.6–100% on real agents, with the combined policy on fresh seeds ([research/REPORT-v3.md](../../research/REPORT-v3.md), H1, tag `research/prereg-v3`). The reference engine reproduces the simulation (93.9%).
- **Implementation:** `engine.py` (promotion in the state reducer); `stats.py` `WilsonBound`
- **Test:** `engine/tests/test_engine.py::test_promotion_matches_consequence_floor`, `engine/tests/test_stats.py::test_reviews_needed_table`, `engine/tests/test_stats.py::test_worked_example_numbers`, `engine/tests/test_stats.py::test_edges`, `conformance/test_conformance.py::test_c7_trust_gym_t1_parity`
- **Notes:** The upper bound uses all of the key's evidence; the 30-action minimum counts only since the last level change.

## EA-3.5 Step-down on recent errors
- **Statement:** A trust key at L2 Trusted or above MUST step down one level when at least `rolling_window_min` (default 10) of its last `rolling_window` (default 50) judged actions are available and the lower bound of their serious-error rate is above its error bar.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** Step down when even the most generous reading of recent work is over the bar. Slow to promote, quick to step down.
- **Evidence:** Regressions were caught in a median of 14 actions, 98% within 50 ([research/REPORT-v3.md](../../research/REPORT-v3.md), H4, tag `research/prereg-v3`).
- **Implementation:** `engine.py` (step-down in the state reducer); `stats.py` `WilsonBound.lower`
- **Test:** `engine/tests/test_engine.py::test_rolling_bound_steps_down_one_level`, `engine/tests/test_strict.py::test_strict_promotion_still_steps_down_on_errors_and_replays`, `conformance/test_conformance.py::test_c7_trust_gym_t1_parity`
- **Notes:** At a 5% bar, 6 serious errors in the last 50 trigger a step-down (the lower bound is 5.6%); 5 do not (4.3%).

## EA-3.6 Step-down before promotion, one level at a time
- **Statement:** On each new outcome, step-down MUST be evaluated before promotion, and a trust key MUST move at most one level per outcome.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** Dropping all the way to the bottom added nothing over one level, and cost reviews.
- **Evidence:** Hard demotion (straight to L1) cut escapes by only 1% against one-level demotion ([research/REPORT.md](../../research/REPORT.md), L4, tag `research/prereg`); one-level demotion was non-inferior ([research/REPORT-v1.md](../../research/REPORT-v1.md), V2, tag `research/prereg-v1`).
- **Implementation:** `engine.py` (state reducer)
- **Test:** `engine/tests/test_engine.py::test_rolling_bound_steps_down_one_level`

## EA-3.7 Incidents step down immediately
- **Statement:** An incident MUST count as one serious error and MUST step the action's trust key down one level before the next decision for that key.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** A mistake found after the fact is the clearest evidence there is, and a signal the agent can't game.
- **Evidence:** Incidents contained watch-aware agents even when sampling was predictable (median 16 actions) ([research/REPORT-v4.md](../../research/REPORT-v4.md), S3); one level is enough ([research/REPORT-v1.md](../../research/REPORT-v1.md), V2).
- **Implementation:** `engine.py` `TrustEngine.report_incident`
- **Test:** `conformance/test_conformance.py::test_c3_incident_steps_down_before_next_decision`, `engine/tests/test_engine.py::test_incident_applies_to_the_actions_version`
- **Notes:** An incident adds to the totals but not to the rolling window.

## EA-3.8 Consequence levels set the error bar
- **Statement:** A task type's error bar MUST be set by its consequence level: 0.10 for C1 Low, 0.05 for C2 Moderate and 0.02 for C3 High, while C4 Critical MUST NOT be promoted.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** The more a mistake costs, the more proof is needed before the agent acts alone. Judged actions needed with no errors: 35 (C1), 73 (C2) and 189 (C3).
- **Evidence:** The C1 floor freed 45–63% of C1 reviews at 0.60–0.84 escapes per 100 autonomous actions ([research/REPORT-v2.md](../../research/REPORT-v2.md), C2, tag `research/prereg-v2`); the combined policy's reference numbers are in [research/REPORT-v3.md](../../research/REPORT-v3.md).
- **Implementation:** `models.py` `CONSEQUENCE`; `engine.py` `TrustEngine.error_bar_for`
- **Test:** `engine/tests/test_engine.py::test_promotion_matches_consequence_floor`, `engine/tests/test_engine.py::test_c4_never_promotes`, `engine/tests/test_stats.py::test_reviews_needed_table`

## EA-3.9 Error bars can only be tightened
- **Statement:** The policy owner MAY set a task type's error bar below its consequence level's error bar, and MUST NOT set it above.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** An owner can demand more proof than the default; nobody can demand less.
- **Evidence:** none; a governance decision.
- **Implementation:** `engine.py` `TrustEngine.set_task_error_bar`
- **Test:** `engine/tests/test_engine.py::test_error_bar_can_only_tighten`

## EA-3.10 Consequence sets the bar, not the expectation
- **Statement:** A task type's consequence level MUST NOT be used to predict how accurate the agent will be, only to set how much accuracy is required.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** Measured errors decide whether the agent meets the bar.
- **Evidence:** "Low-risk" task types had the highest error rates (3.8% against 1.3% medium and 1.9% high), so error bars derived from a risk label promoted the most error-prone work ([research/REPORT-v1.md](../../research/REPORT-v1.md), V4, tag `research/prereg-v1`).
- **Implementation:** none (a policy practice)
- **Test:** none yet

## EA-3.11 Task success is an alert, not a gate
- **Statement:** Implementations SHOULD alert the AI owner when a task type's task success falls below 85% (C1), 90% (C2) or 95% (C3), and MUST NOT use task success as a condition for promotion.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** An agent that does harmless but incomplete work needs attention, not a frozen ladder.
- **Evidence:** As a promotion gate it cost up to 11.8 points of automation for little gain on real agents ([research/REPORT-v2.md](../../research/REPORT-v2.md), C3, tag `research/prereg-v2`).
- **Implementation:** `engine.py` `TrustEngine.get_state` (alerts)
- **Test:** `engine/tests/test_engine.py::test_success_alert_is_not_a_gate`

## EA-3.12 Evidence doesn't fade with time
- **Statement:** Evidence MUST NOT be discounted because of its age.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** At L3 only 5% of actions are judged, so fading evidence demotes good task types on time alone.
- **Evidence:** Fading with a 90- or 180-day half-life cost 3.9–6.0 points of automation ([research/REPORT-v2.md](../../research/REPORT-v2.md), F1, tag `research/prereg-v2`).
- **Implementation:** `engine.py` (no decay)
- **Test:** `conformance/test_evidence_rules.py::test_evidence_does_not_fade_with_time`

## EA-3.13 Re-entry after a long gap
- **Statement:** A trust key at L2 Trusted or above MUST step down one level when its task type is used again after a gap of more than `reentry_gap_days` (default 60).
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** After a long break the world may have changed.
- **Evidence:** Cut escapes after drift by 17% at no automation cost, on fresh seeds ([research/REPORT-v3.md](../../research/REPORT-v3.md), F1', tag `research/prereg-v3`).
- **Implementation:** `engine.py` `TrustEngine.decide` (re-entry check)
- **Test:** `engine/tests/test_engine.py::test_reentry_after_60_days_steps_down`, `engine/tests/test_engine.py::test_no_reentry_within_gap`

## EA-3.14 Strict promotion (optional)
- **Statement:** A policy MAY require strict promotion for chosen consequence levels or task types, in which case promotion MUST use an anytime-valid upper bound (a Beta-binomial mixture confidence sequence with prior Beta(1, 1/ε − 1) and significance 0.05) in place of the Wilson bound.
- **Condition:** The policy lists the task type or its consequence level under `strict_promotion`.
- **Status:** Open
- **Lifecycle:** Development
- **Rationale:** The engine re-checks after every outcome. A bound that stays valid under continuous checking cuts undeserved promotions of steady agents. Recommended for C3 task types and agents with a weak record. Judged actions needed with no errors: 46 (C1), 93 (C2), 236 (C3).
- **Evidence:** On real-agent streams it cut undeserved promotions from 2.0% to 0.2% at 28% more evidence; in simulation it barely helped (−6%), because undeserved promotions there came from agents getting worse after promotion ([research/REPORT-v4.md](../../research/REPORT-v4.md), S1, tag `research/prereg-v4`). A fixed 99% Wilson bound or a flat prior cost more evidence for less benefit.
- **Implementation:** `stats.py` `ConfidenceSequenceBound`; `models.py` `Policy.strict_promotion`
- **Test:** `engine/tests/test_strict.py::test_clean_floors_match_report_v4`, `engine/tests/test_strict.py::test_bounds_bracket_the_rate_and_tighten`, `engine/tests/test_strict.py::test_parity_with_trust_gym_v4`, `engine/tests/test_strict.py::test_strict_selected_by_consequence_level_delays_promotion`, `engine/tests/test_strict.py::test_strict_selected_by_task_type_only_affects_that_type`, `engine/tests/test_strict.py::test_default_is_wilson_everywhere`, `engine/tests/test_strict.py::test_strict_promotion_still_steps_down_on_errors_and_replays`, `engine/tests/test_strict.py::test_anytime_validity_under_continuous_monitoring`
- **Notes:** Step-down keeps the rolling Wilson lower bound (EA-3.5).

## EA-3.15 Serialised updates per trust key
- **Statement:** Updates to one trust key MUST be applied one at a time, and decisions MUST read the latest committed state.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** Two simultaneous outcomes mustn't both read a stale count.
- **Evidence:** none; structural.
- **Implementation:** `models.py` `TrustState.state_version`; `engine.py` (single-writer reducer)
- **Test:** none yet

## EA-3.16 Late incidents apply to the original version
- **Statement:** An incident MUST be applied to the trust key and the agent version of the action it refers to, even if the agent has since changed version.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** Evidence belongs to the version that earned it.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.report_incident`
- **Test:** `engine/tests/test_engine.py::test_incident_applies_to_the_actions_version`

## EA-3.17 Rare task types (known limitation)
- **Statement:** Implementations MAY keep rare task types supervised indefinitely, and SHOULD NOT promote a task type on evidence other than judged actions until a method for rare task types is tested.
- **Status:** Open
- **Lifecycle:** Development
- **Rationale:** Time to promotion depends on frequency. At C2 (73 judged actions), a task done 10 times a day is promoted in about a week, 10 times a month in about 7 months, and twice a month in about 3 years: in practice, never. The re-entry rule (EA-3.13) compounds this. Review cost is proportional to frequency, so rare task types cost little to keep supervised, and for high-consequence rare work the lack of evidence is itself a reason to keep a person involved.
- **Evidence:** none yet. Candidates to test:
  - **Historical replay:** the agent in shadow on past human-handled cases, counted at a discount (e.g. 0.5).
  - **Other organisations:** evidence for the same agent version on the same task type elsewhere, discounted. This differs from pooling across different task types, which failed.
  - **Frequency-aware re-entry:** step down only after more than 60 days *and* more than about 3× the task type's usual interval.
- **Implementation:** none
- **Test:** none yet
- **Notes:** Test passes are not a candidate. Tests show the agent changing, not real work (EA-4.12).
