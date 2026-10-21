# 1. Measure

How much an agent can be trusted with each task type, measured from the evidence at any time: the trust score, the trust profile and the agent's trust summary. The [Measure explainer](../measure.md) shows the maths.

## EA-1.1 Trust is kept per trust key
- **Statement:** Trust state MUST be kept separately for each trust key (organisation, agent, task type) and MUST NOT be shared between keys.
- **Status:** Tested
- **Tier:** Core
- **Stability:** Development
- **Rationale:** An agent can be reliable at one kind of work and unreliable at another. Trust per agent lets one weak task type hold back all the others.
- **Evidence:** Trust per task type gave 27% automation against 7% for trust per agent, in simulation ([research/REPORT.md](../../research/REPORT.md), rule L3, tag `research/prereg`). Pooling evidence across an agent's task types penalised its good types ([research/REPORT-v1.md](../../research/REPORT-v1.md), V3, tag `research/prereg-v1`).
- **Implementation:** `engine.py` `TrustEngine` (state keyed by `(organisation_id, agent_id, task_type)`)
- **Test:** `engine/tests/test_engine.py::test_new_type_starts_supervised`
- **Notes:** v0 found per-agent trust has fewer escapes per 100 actions (0.55 against 0.60) because it barely automates anything.

## EA-1.2 Only judged actions are evidence
- **Statement:** Only judged actions (pre-review outcomes, spot-check outcomes and incidents) MUST count as evidence, and autonomous actions nobody judged MUST NOT count as evidence of good work.
- **Status:** Default
- **Tier:** Core
- **Stability:** Development
- **Rationale:** Silence isn't approval.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.record_outcome`, `TrustEngine.report_incident`
- **Test:** `conformance/test_evidence_rules.py::test_unjudged_autonomous_actions_are_not_evidence`

## EA-1.3 Pre-review and spot-check outcomes weigh the same
- **Statement:** An outcome from a spot-check MUST carry the same weight as an outcome from a pre-review.
- **Status:** Tested
- **Tier:** Core
- **Stability:** Development
- **Rationale:** Both are a person judging real work.
- **Evidence:** The policy tested in every round weighs them equally ([research/REPORT.md](../../research/REPORT.md); [research/REPORT-v3.md](../../research/REPORT-v3.md)).
- **Implementation:** `engine.py` `TrustEngine.record_outcome`
- **Test:** `conformance/test_evidence_rules.py::test_spot_check_and_pre_review_outcomes_weigh_the_same`

## EA-1.4 What counts as a serious error
- **Statement:** An outcome MUST count as a serious error when it is labelled `material_edit` or `rejected` with a serious reason code, or when it is an incident, and cosmetic edits and `incomplete` outcomes MUST NOT count as serious errors.
- **Status:** Default
- **Tier:** Core
- **Stability:** Development
- **Rationale:** Trust is about consequential mistakes: a wrong or unauthorised action, a made-up fact or amount, a promise the policy doesn't allow, or obeying an instruction hidden in a message. Wording and tone are taste.
- **Evidence:** The definition used in every tier ([research/REPORT.md](../../research/REPORT.md)).
- **Implementation:** `models.py` `is_serious`, `SERIOUS_REASONS`, `COSMETIC_REASONS`
- **Test:** `engine/tests/test_engine.py::test_cosmetic_and_incomplete_are_not_serious`
- **Notes:** Reason codes are listed in EA-3.6.

## EA-1.5 Consequence levels set the error bar
- **Statement:** A task type's error bar MUST be set by its consequence level: 0.10 for C1 Low, 0.05 for C2 Moderate and 0.02 for C3 High, while C4 Critical MUST NOT be promoted.
- **Status:** Tested
- **Tier:** Core
- **Stability:** Development
- **Rationale:** The more a mistake costs, the more proof is needed before the agent acts alone. Judged actions needed with no errors: 35 (C1), 73 (C2) and 189 (C3).
- **Evidence:** The C1 floor freed 45–63% of C1 reviews at 0.60–0.84 escapes per 100 autonomous actions ([research/REPORT-v2.md](../../research/REPORT-v2.md), C2, tag `research/prereg-v2`); the combined policy's reference numbers are in [research/REPORT-v3.md](../../research/REPORT-v3.md).
- **Implementation:** `models.py` `CONSEQUENCE`; `engine.py` `TrustEngine.error_bar_for`
- **Test:** `engine/tests/test_engine.py::test_c4_never_promotes`, `engine/tests/test_engine.py::test_promotion_matches_consequence_floor`, `engine/tests/test_stats.py::test_reviews_needed_table`

## EA-1.6 Error bars can only be tightened
- **Statement:** The policy owner MAY set a task type's error bar below its consequence level's error bar, and MUST NOT set it above.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** An owner can demand more proof than the default; nobody can demand less.
- **Evidence:** none; a governance decision.
- **Implementation:** `engine.py` `TrustEngine.set_task_error_bar`
- **Test:** `engine/tests/test_engine.py::test_error_bar_can_only_tighten`

## EA-1.7 Consequence sets the bar, not the expectation
- **Statement:** A task type's consequence level MUST NOT be used to predict how accurate the agent will be, only to set how much accuracy is required.
- **Status:** Tested
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Measured errors decide whether the agent meets the bar.
- **Evidence:** "Low-risk" task types had the highest error rates (3.8% against 1.3% medium and 1.9% high), so error bars derived from a risk label promoted the most error-prone work ([research/REPORT-v1.md](../../research/REPORT-v1.md), V4, tag `research/prereg-v1`).
- **Implementation:** none (a policy practice)
- **Test:** none yet

## EA-1.8 Evidence doesn't fade with time
- **Statement:** Evidence MUST NOT be discounted because of its age.
- **Status:** Tested
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** At L3 only 5% of actions are judged, so fading evidence demotes good task types on time alone.
- **Evidence:** Fading with a 90- or 180-day half-life cost 3.9–6.0 points of automation ([research/REPORT-v2.md](../../research/REPORT-v2.md), F1, tag `research/prereg-v2`).
- **Implementation:** `engine.py` (no decay)
- **Test:** `conformance/test_evidence_rules.py::test_evidence_does_not_fade_with_time`

## EA-1.9 Serialised updates per trust key
- **Statement:** Updates to one trust key MUST be applied one at a time, and decisions MUST read the latest committed state.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Two simultaneous outcomes mustn't both read a stale count.
- **Evidence:** none; structural.
- **Implementation:** `models.py` `TrustState.state_version`; `engine.py` (single-writer reducer)
- **Test:** none yet

## EA-1.10 Late incidents apply to the original version
- **Statement:** An incident MUST be applied to the trust key and the agent version of the action it refers to, even if the agent has since changed version.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Evidence belongs to the version that earned it.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.report_incident`
- **Test:** `engine/tests/test_engine.py::test_incident_applies_to_the_actions_version`

## EA-1.11 Task success is an alert, not a gate
- **Statement:** Implementations SHOULD alert the AI owner when a task type's task success falls below 85% (C1), 90% (C2) or 95% (C3), and MUST NOT use task success as a condition for promotion.
- **Status:** Tested
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** An agent that does harmless but incomplete work needs attention, not a frozen ladder.
- **Evidence:** As a promotion gate it cost up to 11.8 points of automation for little gain on real agents ([research/REPORT-v2.md](../../research/REPORT-v2.md), C3, tag `research/prereg-v2`).
- **Implementation:** `engine.py` `TrustEngine.get_state` (alerts)
- **Test:** `engine/tests/test_engine.py::test_success_alert_is_not_a_gate`

## EA-1.12 Test passes are not promotion evidence
- **Statement:** Passing tests MUST NOT count as judged actions for promotion.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Tests show the agent changing; spot-checks show the world changing. Only real work earns promotion. Test results may still inform the trust score at a discount (EA-1.18), never the ladder (EA-1.21).
- **Evidence:** none; structural.
- **Implementation:** `engine.py` (tests feed carry-over, and the trust score at their weight, EA-1.18)
- **Test:** `conformance/test_evidence_rules.py::test_passing_tests_is_not_promotion_evidence`, `engine/tests/test_measure.py::test_non_human_evidence_never_changes_the_autonomy_setting`

## EA-1.13 Trust is measurable at any time from the record
- **Statement:** An implementation MUST be able to produce, at any time and from the trust record alone, each trust key's autonomy setting and the human evidence behind it (judged actions and serious errors since its last change).
- **Status:** Tested
- **Tier:** Core
- **Stability:** Development
- **Rationale:** Trust you can't look up isn't accountable. Deriving it from the record means anyone can check it.
- **Evidence:** none; structural (EA-6.9).
- **Implementation:** `engine.py` `TrustEngine.trust_report`, `TrustEngine.get_state`
- **Test:** `engine/tests/test_measure.py::test_trust_report_is_derived_from_the_record`

## EA-1.14 The trust score
- **Statement:** An implementation SHOULD report each trust key's trust score: the posterior probability that its true serious-error rate is below its error bar, `I_ε(a₀ + serious, b₀ + judged − serious)` from a Beta(a₀, b₀) prior (default Beta(1, 1)) and the weighted evidence of EA-1.18. A capped task type scores 0.
- **Status:** Tested
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** One number for "how sure are we this task type is under its bar", comparable across consequence levels.
- **Evidence:** With the flat prior, a score of at least 0.975 reproduces the 95% Wilson promotion rule: at every one of the 33 published table cells the score is 0.975–0.979, and it reaches 0.975 at most 1 (C1), 2 (C2) or 7 (C3) judged actions before Wilson promotes. Agreement with Wilson promotion was 99.9–100% at thresholds 0.976–0.979 ([research/REPORT-calibration.md](../../research/REPORT-calibration.md), CAL2). At 0.95 the score promotes about 20% earlier (58 instead of 73 clean at C2) and does not match.
- **Implementation:** `stats.py` `trust_score`, `regularized_incomplete_beta`; `engine.py` `TrustEngine.trust_score`
- **Test:** `engine/tests/test_measure.py::test_incomplete_beta_matches_closed_forms`, `engine/tests/test_measure.py::test_trust_score_capped_and_prior`, `engine/tests/test_measure.py::test_trust_score_matches_wilson_at_every_promotion_point`
- **Notes:** The score is conservative when evidence is thin and slightly over-confident at the top when agents get worse after promotion (ECE 0.039–0.146, [research/REPORT-calibration.md](../../research/REPORT-calibration.md), CAL1). Step-down (EA-2.17) handles the second. Decisions on the Core ladder use the bound or table (EA-2.14, EA-2.15), not the score.

## EA-1.15 The trust profile
- **Statement:** An implementation SHOULD report a trust profile for each trust key with: the estimated serious-error rate and a 95% interval; the trust score; the effective evidence (weighted judged actions); the evidence by source; freshness (the agent version and when the last evidence arrived); the trend; the autonomy setting and the autonomy the evidence implies; and whether the evidence is still thin (below the clean floor of EA-2.15).
- **Status:** Tested
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** One view of everything that justifies a task type's autonomy. A low score with thin evidence means "not enough evidence yet", not "bad agent".
- **Evidence:** Most of the score's calibration error is in the low-score bin, where evidence is thin ([research/REPORT-calibration.md](../../research/REPORT-calibration.md), CAL1).
- **Implementation:** `engine.py` `TrustEngine.trust_report`
- **Test:** `engine/tests/test_measure.py::test_trust_profile_contents`
- **Notes:** Trend: *slipping* when the Wilson lower bound of the recent window is above the overall rate, *improving* when its upper bound is below it, *stable* otherwise, *insufficient* with fewer than `rolling_window_min` recent judgements.

## EA-1.16 The agent's trust summary
- **Statement:** An implementation SHOULD report, for each agent, the share of its actions at each autonomy setting, its incidents (in total and in the last 30 days) and the trend of its task types.
- **Status:** Tested
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Owners decide about agents, not trust keys (EA-2.21). This is the view they decide from.
- **Evidence:** none; a reporting requirement.
- **Implementation:** `engine.py` `TrustEngine.trust_report` (`summary`)
- **Test:** `engine/tests/test_measure.py::test_agent_trust_summary`

## EA-1.17 Live human judgement is the reference evidence
- **Statement:** Live human judgements (pre-review outcomes, spot-check outcomes and incidents) MUST count at weight 1.0, and every other source's weight MUST be stated relative to them.
- **Status:** Tested
- **Tier:** Advanced
- **Stability:** Development
- **Rationale:** People are the standard the agent is held to. Every other source is calibrated against them.
- **Evidence:** The Trust Gym's promotion results all use live human evidence (EA-2.14).
- **Implementation:** `models.py` `Policy.evidence_weights`; `engine.py` `TrustEngine.record_outcome`
- **Test:** `engine/tests/test_measure.py::test_trust_profile_contents`

## EA-1.18 Other evidence sources are weighted
- **Statement:** An implementation MAY count evidence from other sources in the trust score, each at a named, policy-set weight: `shadow` (the agent's output compared with what a person actually did), `replay` (the agent graded on past human-handled cases) and `test` (pre-deployment tests). Defaults: shadow 1.0, replay 1.0, test 0.75. Test results MUST NOT be the only evidence for an implied autonomy above supervised, and any version discount (EA-4.7) MUST apply to every source.
- **Status:** Open
- **Tier:** Advanced
- **Stability:** Development
- **Rationale:** Evidence that isn't a live review can still say how good an agent is, but it isn't the real work.
- **Evidence:** Calibrated weights, 100 observations per key: shadow and replay were at least as informative as a live review (best weight hit the grid maximum of 2.0, which mostly reflects the flat prior's pessimism); tests needed a discount even when graded perfectly, best at 0.75 ([research/REPORT-calibration.md](../../research/REPORT-calibration.md)). Replay found more real errors, with fewer undeserved promotions (3.8% vs 5.3%), but did not speed up ramp-up (CAL3b); shadow increased ramp-up human minutes (CAL3).
- **Implementation:** `engine.py` `TrustEngine.record_evidence`, `TrustEngine.trust_report`
- **Test:** `engine/tests/test_measure.py::test_non_human_evidence_counts_at_its_weight`, `engine/tests/test_measure.py::test_tests_are_never_the_only_evidence_for_trust`, `engine/tests/test_measure.py::test_version_discount_applies_to_every_source`
- **Notes:** Open until the weights are confirmed against human judgement in production (EA-1.19). Live review flatters agents when reviewers miss errors; canaries (EA-3.11) partly correct this.

## EA-1.19 Evidence weights are calibrated against human judgement
- **Statement:** An implementation that weights non-human evidence SHOULD calibrate each weight by how well that source agreed with human judgement on the same task type, and SHOULD record the calibration.
- **Status:** Open
- **Tier:** Advanced
- **Stability:** Development
- **Rationale:** A weight nobody checked is a guess.
- **Evidence:** Method and first calibration: [research/REPORT-calibration.md](../../research/REPORT-calibration.md).
- **Implementation:** none
- **Test:** none yet
- **Notes:** Candidate method: choose the weight that minimises the expected calibration error of the trust score against a later human-judged sample.

## EA-1.20 Keep a share of human evidence
- **Statement:** An implementation that counts non-human evidence SHOULD alert when weighted human evidence falls below a policy-set share of a trust key's effective evidence (default 20%).
- **Status:** Open
- **Tier:** Advanced
- **Stability:** Development
- **Rationale:** Other sources drift from real work unless people keep checking it.
- **Evidence:** none yet.
- **Implementation:** `engine.py` `TrustEngine.trust_report` (`human_evidence_share_below_minimum` alert)
- **Test:** `engine/tests/test_measure.py::test_alert_when_human_evidence_share_is_too_small`

## EA-1.21 Other evidence never changes the autonomy setting by itself
- **Statement:** Evidence from sources other than live human judgement MUST NOT promote or step down a trust key on the Core ladder; it changes only the trust score and the trust profile.
- **Status:** Tested
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Keeps the Core ladder on the tested footing while other sources are still being calibrated.
- **Evidence:** Promotion results (EA-2.14) use live human evidence only.
- **Implementation:** `engine.py` (`evidence` entries in the reducer)
- **Test:** `engine/tests/test_measure.py::test_non_human_evidence_never_changes_the_autonomy_setting`
