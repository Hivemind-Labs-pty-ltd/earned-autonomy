# 2. Decide

What to do with what was measured: hold or act for every proposed action, the autonomy setting of each task type (the Core ladder, or the Advanced dial), and the decisions people make about an agent. See [autonomy settings](../autonomy.md) and the [worked examples](../examples.md).

## EA-2.1 Decision order
- **Statement:** The decision for a proposed action MUST apply these rules in this order, and the first that matches MUST determine the result: paused (EA-2.2), low tag confidence or unknown type (EA-2.3, EA-2.4), tool floor mismatch (EA-2.5), checks missing or failed (EA-2.6, EA-2.7), capped type (EA-2.8), then level (EA-2.9).
- **Status:** Default
- **Tier:** Core
- **Stability:** Development
- **Rationale:** A fixed order makes every decision reproducible and its reason unambiguous.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.decide`
- **Test:** `conformance/test_tool_floor.py::test_floor_check_runs_before_checks_and_level`

## EA-2.2 Paused work is held
- **Statement:** A proposed action MUST be held while its agent or its task type is paused.
- **Status:** Default
- **Tier:** Core
- **Stability:** Development
- **Rationale:** Pause is the owner's stop button (EA-3.9).
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.decide` (`why = paused`); `TrustEngine.pause`, `TrustEngine.resume`
- **Test:** `conformance/test_conformance.py::test_c2_no_autonomous_execution_when_not_allowed`, `engine/tests/test_engine.py::test_pause_and_resume_per_type_and_agent`

## EA-2.3 Low-confidence tags are held
- **Statement:** A proposed action MUST be held when its tag confidence is below the policy's minimum (default 0.8), whatever the task type's level.
- **Condition:** The tagger returns a confidence below `tag_confidence_min`.
- **Status:** Tested
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** A tagger that isn't sure what kind of work this is shouldn't decide which trust applies.
- **Evidence:** A partial defence: it held 4 of 10 adversarial downgrades in v4 study S2b ([research/REPORT-v4.md](../../research/REPORT-v4.md), tag `research/prereg-v4`). The tool floor (EA-2.5) is the main defence.
- **Implementation:** `engine.py` `TrustEngine.decide` (`why = low_confidence`)
- **Test:** `engine/tests/test_engine.py::test_unknown_type_and_low_confidence_hold`

## EA-2.4 Unknown task types are held
- **Statement:** A proposed action tagged with a task type that isn't in the catalogue MUST be held and SHOULD be logged as a candidate new task type.
- **Status:** Default
- **Tier:** Core
- **Stability:** Development
- **Rationale:** Work nobody has defined can't have earned trust.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.decide` (`why = unknown_type`)
- **Test:** `engine/tests/test_engine.py::test_unknown_type_and_low_confidence_hold`
- **Notes:** The reference engine records the `unknown_type` decision; a separate candidate list is not implemented.

## EA-2.5 Floor mismatches are held
- **Statement:** A proposed action MUST be held when the floor of any write tool it will call is above the consequence level of its tagged task type.
- **Condition:** The action declares at least one write tool.
- **Status:** Tested
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Stops a risky action borrowing a low-consequence task type's trust by being tagged, by mistake or on purpose, as that type.
- **Evidence:** Removed 100% of autonomous escapes from deliberately mis-tagged actions in all six scenarios, at 0.3–1.8 points of automation; it held all 8 adversarial downgrades that came with a risky write on a real model-based tagger ([research/REPORT-v4.md](../../research/REPORT-v4.md), S2, tag `research/prereg-v4`).
- **Implementation:** `engine.py` `TrustEngine.decide` (`why = tool_floor_mismatch`)
- **Test:** `conformance/test_tool_floor.py::test_floor_at_or_below_tag_does_not_hold`, `conformance/test_tool_floor.py::test_floor_check_runs_before_checks_and_level`, `conformance/test_tool_floor.py::test_mis_tagged_refund_as_status_is_held_even_when_status_is_trusted`
- **Notes:** The action's effective consequence is the highest of its tag's level and every write tool's floor.

## EA-2.6 Checks run at every level
- **Statement:** Checks MUST run on every proposed action at every trust level, and an action with any failed check MUST be held.
- **Status:** Tested
- **Tier:** Core
- **Stability:** Development
- **Rationale:** Trust is about the agent's record; checks catch the obvious mistake in this particular action.
- **Evidence:** Earned trust plus checks let through 66–69% fewer serious errors than checks alone at the same automation on real agents ([research/REPORT.md](../../research/REPORT.md), H3, tag `research/prereg`); checks are part of every policy tested since.
- **Implementation:** `engine.py` `TrustEngine.decide` (`why = check_failed`)
- **Test:** `conformance/test_conformance.py::test_c2_no_autonomous_execution_when_not_allowed`, `engine/tests/test_engine.py::test_checks_missing_or_failed_hold_at_every_level`

## EA-2.7 A missing checks result is a hold
- **Statement:** A proposed action MUST be held when no checks result is supplied, unless the policy explicitly allows actions without checks.
- **Status:** Default
- **Tier:** Core
- **Stability:** Development
- **Rationale:** "No checks ran" must never be read as "checks passed".
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.decide` (`why = checks_missing`; `require_checks`)
- **Test:** `engine/tests/test_engine.py::test_checks_missing_or_failed_hold_at_every_level`

## EA-2.8 Critical work is always held
- **Statement:** A proposed action whose task type is C4 Critical or otherwise capped MUST be held, and such task types MUST NOT be promoted.
- **Status:** Tested
- **Tier:** Core
- **Stability:** Development
- **Rationale:** Some actions, such as moving money, deleting records or anything legal or irreversible, are never handed over.
- **Evidence:** Consequence levels including "C4 never promotes" were tested in v2 ([research/REPORT-v2.md](../../research/REPORT-v2.md), C2, tag `research/prereg-v2`).
- **Implementation:** `engine.py` `TrustEngine.decide` (`why = capped`); `models.py` `CONSEQUENCE`
- **Test:** `conformance/test_conformance.py::test_c2_no_autonomous_execution_when_not_allowed`, `engine/tests/test_engine.py::test_c4_never_promotes`

## EA-2.9 The level decides the rest
- **Statement:** A proposed action that passes every earlier rule MUST be held if its trust key is at L1 Supervised, and MUST go ahead if its trust key is at L2 Trusted or L3 Senior.
- **Status:** Tested
- **Tier:** Core
- **Stability:** Development
- **Rationale:** The core of the ladder.
- **Evidence:** 92–100% of promotions were deserved across tiers ([research/REPORT-v3.md](../../research/REPORT-v3.md), reference numbers, tag `research/prereg-v3`).
- **Implementation:** `engine.py` `TrustEngine.decide` (`why = level_L1` or `trusted`)
- **Test:** `conformance/test_conformance.py::test_c2_no_autonomous_execution_when_not_allowed`, `engine/tests/test_engine.py::test_new_type_starts_supervised`

## EA-2.10 Bundled actions take the most restrictive decision
- **Statement:** When one proposal contains several actions, each action MUST be tagged and decided separately, and actions that must happen together MUST all be held if any one of them is held.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** A trusted reply mustn't carry an untrusted record update through with it.
- **Evidence:** none yet.
- **Implementation:** `engine.py` `TrustEngine.decide_bundle`
- **Test:** `engine/tests/test_engine.py::test_bundle_most_restrictive`

## EA-2.11 Re-decide at execution time
- **Statement:** A decision SHOULD be re-evaluated when the action is about to execute, and the newer decision MUST apply if the trust state, a pause or the policy has changed since the action was proposed.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** An action approved before a step-down or a pause shouldn't slip through after it.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.decide` (callable again before `mark_executed`); `TrustEngine.execute`
- **Test:** `conformance/test_evidence_rules.py::test_the_newest_decision_applies_at_execution_time`

## EA-2.12 Every decision is recorded and explainable
- **Statement:** Every decision MUST be written to the trust record with its result, its reason, the trust level, the evidence counts, the bound and error bar used, the effective consequence and tool floor, the checks result, and the policy and agent versions.
- **Status:** Tested
- **Tier:** Core
- **Stability:** Development
- **Rationale:** Anyone can see why any action was allowed.
- **Evidence:** 100% of autonomous actions were explainable from the record in every tier ([research/REPORT.md](../../research/REPORT.md), G2; [research/REPORT-10x.md](../../research/REPORT-10x.md)).
- **Implementation:** `engine.py` `TrustEngine.decide`, `TrustEngine.explain`; `models.py` `Decision`
- **Test:** `conformance/test_conformance.py::test_c1_every_autonomous_execution_is_explained`

## EA-2.13 New task types start supervised with no evidence
- **Statement:** A trust key MUST start at L1 Supervised with no evidence, and MUST NOT inherit evidence from the agent's other task types.
- **Status:** Tested
- **Tier:** Core
- **Stability:** Development
- **Rationale:** Earning trust starts from nothing, as it does for a new employee in a new role.
- **Evidence:** Pooled evidence across task types did worse than per-type evidence ([research/REPORT-v1.md](../../research/REPORT-v1.md), V3, tag `research/prereg-v1`).
- **Implementation:** `engine.py` `_Reducer.state`
- **Test:** `engine/tests/test_engine.py::test_new_type_starts_supervised`, `engine/tests/test_measure.py::test_narrowed_or_split_task_type_starts_supervised`

## EA-2.14 Promotion
- **Statement:** A trust key below L3 Senior MUST be promoted one level when it has at least `min_judged` (default 30) judged actions since its last level change and the upper bound of its serious-error rate (95% Wilson score interval by default) is at or below its error bar, and MUST NOT be promoted otherwise.
- **Condition:** The task type is not C4 Critical or otherwise capped (EA-2.8).
- **Status:** Tested
- **Tier:** Core
- **Stability:** Development
- **Rationale:** Promote only when even the plausible worst case is under the bar. With no errors, the worst case is roughly 4 ÷ the number judged.
- **Evidence:** 93.3% of promotions were deserved in simulation and 99.6–100% on real agents, with the combined policy on fresh seeds ([research/REPORT-v3.md](../../research/REPORT-v3.md), H1, tag `research/prereg-v3`). The reference engine reproduces the simulation (93.9%).
- **Implementation:** `engine.py` (promotion in the state reducer); `stats.py` `WilsonBound`
- **Test:** `conformance/test_conformance.py::test_c7_trust_gym_t1_parity`, `engine/tests/test_engine.py::test_promotion_matches_consequence_floor`, `engine/tests/test_measure.py::test_core_table_rule_makes_the_same_decisions_as_the_bound`, `engine/tests/test_stats.py::test_edges`, `engine/tests/test_stats.py::test_reviews_needed_table`, `engine/tests/test_stats.py::test_worked_example_numbers`
- **Notes:** The upper bound uses all of the key's evidence; the 30-action minimum counts only since the last level change.

## EA-2.15 The Core lookup tables
- **Statement:** A Core implementation MAY run promotion and step-down from the published lookup tables instead of computing bounds: promote after the number of judged actions the table gives for the serious errors so far (more than 10: don't promote), and step down when the last 50 judged actions hold at least 10 (C1), 6 (C2) or 3 (C3) serious errors. Tables MUST be derived from the 95% Wilson rule so both give the same decisions.
- **Status:** Tested
- **Tier:** Core
- **Stability:** Development
- **Rationale:** A team can run trust from a printed table, with no statistics code.
- **Evidence:** Judged actions needed by serious errors 0–10: C1 35 53 69 84 99 113 127 140 153 166 179 · C2 73 110 142 173 202 230 257 284 311 337 363 · C3 189 280 361 437 510 581 650 718 785 851 916 ([research/REPORT-core.md](../../research/REPORT-core.md); [research/core/core-tables.md](../../research/core/core-tables.md)).
- **Implementation:** `stats.py` `promotion_table`, `step_down_threshold`; `models.py` `Policy.promotion_rule`
- **Test:** `engine/tests/test_measure.py::test_core_table_rule_makes_the_same_decisions_as_the_bound`, `engine/tests/test_measure.py::test_core_tables_equal_the_published_tables`, `engine/tests/test_measure.py::test_trust_score_matches_wilson_at_every_promotion_point`
- **Notes:** The tables differ from the bound only beyond 10 serious errors (the table holds the level) and in the short first window before 50 judgements (the table counts errors, the bound needs `rolling_window_min`).

## EA-2.16 Step-down before promotion, one level at a time
- **Statement:** On each new outcome, step-down MUST be evaluated before promotion, and a trust key MUST move at most one level per outcome.
- **Status:** Tested
- **Tier:** Core
- **Stability:** Development
- **Rationale:** Dropping all the way to the bottom added nothing over one level, and cost reviews.
- **Evidence:** Hard demotion (straight to L1) cut escapes by only 1% against one-level demotion ([research/REPORT.md](../../research/REPORT.md), L4, tag `research/prereg`); one-level demotion was non-inferior ([research/REPORT-v1.md](../../research/REPORT-v1.md), V2, tag `research/prereg-v1`).
- **Implementation:** `engine.py` (state reducer)
- **Test:** `engine/tests/test_engine.py::test_rolling_bound_steps_down_one_level`

## EA-2.17 Step-down on recent errors
- **Statement:** A trust key at L2 Trusted or above MUST step down one level when at least `rolling_window_min` (default 10) of its last `rolling_window` (default 50) judged actions are available and the lower bound of their serious-error rate is above its error bar.
- **Status:** Tested
- **Tier:** Core
- **Stability:** Development
- **Rationale:** Step down when even the most generous reading of recent work is over the bar. Slow to promote, quick to step down.
- **Evidence:** Regressions were caught in a median of 14 actions, 98% within 50 ([research/REPORT-v3.md](../../research/REPORT-v3.md), H4, tag `research/prereg-v3`).
- **Implementation:** `engine.py` (step-down in the state reducer); `stats.py` `WilsonBound.lower`
- **Test:** `conformance/test_conformance.py::test_c7_trust_gym_t1_parity`, `engine/tests/test_engine.py::test_rolling_bound_steps_down_one_level`, `engine/tests/test_measure.py::test_core_table_rule_makes_the_same_decisions_as_the_bound`, `engine/tests/test_strict.py::test_strict_promotion_still_steps_down_on_errors_and_replays`
- **Notes:** At a 5% bar, 6 serious errors in the last 50 trigger a step-down (the lower bound is 5.6%); 5 do not (4.3%).

## EA-2.18 Incidents step down immediately
- **Statement:** An incident MUST count as one serious error and MUST step the action's trust key down one level before the next decision for that key.
- **Status:** Tested
- **Tier:** Core
- **Stability:** Development
- **Rationale:** A mistake found after the fact is the clearest evidence there is, and a signal the agent can't game.
- **Evidence:** Incidents contained watch-aware agents even when sampling was predictable (median 16 actions) ([research/REPORT-v4.md](../../research/REPORT-v4.md), S3); one level is enough ([research/REPORT-v1.md](../../research/REPORT-v1.md), V2).
- **Implementation:** `engine.py` `TrustEngine.report_incident`
- **Test:** `conformance/test_conformance.py::test_c3_incident_steps_down_before_next_decision`, `engine/tests/test_engine.py::test_incident_applies_to_the_actions_version`
- **Notes:** An incident adds to the totals but not to the rolling window.

## EA-2.19 Strict promotion (optional)
- **Statement:** A policy MAY require strict promotion for chosen consequence levels or task types, in which case promotion MUST use an anytime-valid upper bound (a Beta-binomial mixture confidence sequence with prior Beta(1, 1/ε − 1) and significance 0.05) in place of the Wilson bound.
- **Condition:** The policy lists the task type or its consequence level under `strict_promotion`.
- **Status:** Open
- **Tier:** Advanced
- **Stability:** Development
- **Rationale:** The engine re-checks after every outcome. A bound that stays valid under continuous checking cuts undeserved promotions of steady agents. Recommended for C3 task types and agents with a weak record. Judged actions needed with no errors: 46 (C1), 93 (C2), 236 (C3).
- **Evidence:** On real-agent streams it cut undeserved promotions from 2.0% to 0.2% at 28% more evidence; in simulation it barely helped (−6%), because undeserved promotions there came from agents getting worse after promotion ([research/REPORT-v4.md](../../research/REPORT-v4.md), S1, tag `research/prereg-v4`). A fixed 99% Wilson bound or a flat prior cost more evidence for less benefit.
- **Implementation:** `stats.py` `ConfidenceSequenceBound`; `models.py` `Policy.strict_promotion`
- **Test:** `engine/tests/test_strict.py::test_anytime_validity_under_continuous_monitoring`, `engine/tests/test_strict.py::test_bounds_bracket_the_rate_and_tighten`, `engine/tests/test_strict.py::test_clean_floors_match_report_v4`, `engine/tests/test_strict.py::test_default_is_wilson_everywhere`, `engine/tests/test_strict.py::test_parity_with_trust_gym_v4`, `engine/tests/test_strict.py::test_strict_promotion_still_steps_down_on_errors_and_replays`, `engine/tests/test_strict.py::test_strict_selected_by_consequence_level_delays_promotion`, `engine/tests/test_strict.py::test_strict_selected_by_task_type_only_affects_that_type`
- **Notes:** Step-down keeps the rolling Wilson lower bound (EA-2.17).

## EA-2.20 Approval for Senior
- **Statement:** A policy MAY require the policy owner to approve promotions to L3 Senior.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Some organisations want a person to sign off the highest level of autonomy.
- **Evidence:** none; a governance option.
- **Implementation:** `governance.py` (`promote` operation, policy owner)
- **Test:** none yet

## EA-2.21 The decision menu
- **Statement:** When an owner reviews an agent or a task type (EA-5.3), the decision SHOULD be one of: increase autonomy, keep, increase oversight, narrow scope, improve (a new version), pause, or retire; and it MUST be recorded.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** A short, fixed menu makes decisions comparable and auditable. Each option maps to a rule: promotion (EA-2.14), step-down or `demote` (EA-2.17), narrowing (EA-5.5), versions (EA-4.1), pause (EA-3.9), retirement (EA-5.4).
- **Evidence:** none; an operating practice.
- **Implementation:** Each option is an engine operation: `promote`, `demote`, `set_spot_rate`, `add_task_type`, `on_version_published`, `pause`, `retire`; each is logged by the governance guard.
- **Test:** `engine/tests/test_measure.py::test_every_decision_menu_option_is_recorded`

## EA-2.22 The dial (optional)
- **Statement:** An implementation MAY replace the ladder's fixed levels with a dial: pre-review while the trust score is below 0.975, otherwise spot-check at `clip(5 × (1 − score) + 0.02, 0.02, 1)`. A dial MUST keep the Core step-down and incident rules (EA-2.17, EA-2.18).
- **Status:** Tested
- **Tier:** Advanced
- **Stability:** Development
- **Rationale:** Smooth control: oversight in proportion to uncertainty.
- **Evidence:** As safe as the ladder (escapes within +0.02 per 100; regression demotion 17 vs 17 actions; promotions as deserved or more) but it barely raised the work done per human minute (+1% to +7%) ([research/REPORT-dial.md](../../research/REPORT-dial.md), DIAL1 fail, DIAL2–3 pass). The round used a 0.95 pre-review threshold; 0.975 matches Wilson promotion (EA-1.14).
- **Implementation:** `stats.py` `dial_spot_rate`; `engine.py` `TrustEngine.trust_report` (`dial`). Decisions in the reference engine follow the ladder.
- **Test:** `engine/tests/test_measure.py::test_dial_setting_from_the_trust_score`
- **Notes:** Core keeps the ladder: it's simpler and costs almost nothing.

## EA-2.23 A decision never reveals sampling
- **Statement:** A decision MUST be either hold or act, and MUST NOT indicate whether the action will be spot-checked.
- **Status:** Tested
- **Tier:** Core
- **Stability:** Development
- **Rationale:** An agent that knows when it is watched can behave well only then.
- **Evidence:** See EA-3.2.
- **Implementation:** `models.py` `Decision.mode`
- **Test:** `conformance/test_conformance.py::test_sampling_is_unpredictable_and_hidden_from_the_agent`
