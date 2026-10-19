# 5. Oversight and reviewers

How people watch agents, stop them, and are themselves measured.

## EA-5.1 Held actions are reviewable
- **Statement:** A held action MUST be shown to reviewers with the proposed action, its checks result, its task type and trust level, and the reason it was held.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** A reviewer can only judge what they can see.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.review_queue`
- **Test:** `engine/tests/test_engine.py::test_spot_sampling_rate_and_queue`

## EA-5.2 Every judgement has a label, and every correction a reason
- **Statement:** A reviewer MUST label every judged action with an outcome, and MUST give a reason code for every edit and rejection.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** A reason turns a correction into a rule or test (EA-4.2). Without one, it's only a statistic.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.record_outcome`
- **Test:** `conformance/test_evidence_rules.py::test_edits_and_rejections_need_a_reason_code`

## EA-5.3 Reason codes
- **Statement:** Implementations SHOULD use these reason codes: serious ones are `wrong_fact`, `wrong_amount`, `wrong_record`, `wrong_recipient`, `unauthorised_action`, `promise_beyond_policy`, `missing_info_not_asked`, `followed_injected_instruction`, `policy_breach` and `other_serious`; cosmetic ones are `tone`, `wording`, `formatting` and `other_cosmetic`.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** A shared vocabulary makes outcomes comparable across reviewers and organisations.
- **Evidence:** none; a vocabulary.
- **Implementation:** `models.py` `SERIOUS_REASONS`, `COSMETIC_REASONS`
- **Test:** `engine/tests/test_engine.py::test_cosmetic_and_incomplete_are_not_serious`

## EA-5.4 Anyone can report an incident
- **Statement:** Every executed action MUST offer a way to report that it was wrong, which records an incident.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** Incidents are the signal an agent can't game (EA-3.7).
- **Evidence:** See EA-3.7.
- **Implementation:** `engine.py` `TrustEngine.report_incident`
- **Test:** `conformance/test_conformance.py::test_c3_incident_steps_down_before_next_decision`

## EA-5.5 Anyone affected can challenge
- **Statement:** An affected customer or staff member SHOULD be able to challenge any executed action, which opens a review by a person.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** Contestability, and a second channel of evidence.
- **Evidence:** none yet.
- **Implementation:** none (a product feature; a confirmed challenge becomes an incident)
- **Test:** none yet

## EA-5.6 Pause
- **Statement:** An authorised person MUST be able to pause an agent or a single task type, which holds every new and not-yet-executed action without undoing executed ones.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** The stop button.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.pause`, `TrustEngine.resume`
- **Test:** `engine/tests/test_engine.py::test_pause_and_resume_per_type_and_agent`

## EA-5.7 Alerts before the bar is crossed
- **Statement:** Implementations SHOULD alert the AI owner when a trust key's rolling upper bound passes 80% of its error bar.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** Warn before an automatic step-down.
- **Evidence:** none yet.
- **Implementation:** `engine.py` `TrustEngine.get_state` (alerts); `models.py` `Policy.alert_fraction`
- **Test:** none yet

## EA-5.8 Periodic agent review
- **Statement:** The AI owner SHOULD review each agent at least quarterly: its levels per task type, incidents, drift and scope.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** Is the scope still right, and is the agent still needed?
- **Evidence:** none; an operating practice.
- **Implementation:** none
- **Test:** none yet

## EA-5.9 Canaries in review queues
- **Statement:** Implementations SHOULD place known-bad canary items in review queues at random, at about 5% of review items.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** People rubber-stamp when they rarely see errors. Canaries keep them sharp and measure them.
- **Evidence:** Canaries cut missed errors by 15% in simulation (assumed reviewer model) ([research/REPORT.md](../../research/REPORT.md), G5). At 2%, a poor reviewer stayed trusted for a median of 174 reviews; at 5% they were sorted correctly ([research/REPORT-v2.md](../../research/REPORT-v2.md); [research/REPORT-v3.md](../../research/REPORT-v3.md), R1', tag `research/prereg-v3`).
- **Implementation:** `engine.py` `TrustEngine.should_insert_canary`, `TrustEngine.record_canary`; `models.py` `Policy.reviewer_canary_rate`
- **Test:** none yet
- **Notes:** The policy also has an older `canary_rate` field (0.02); `reviewer_canary_rate` (0.05) is the tested value.

## EA-5.10 Reviewers earn trust too
- **Statement:** Each reviewer MUST have a trust key (organisation, reviewer, `review.<task_type>`) whose evidence comes from canaries and second checks, with an error bar of 10% and at least 30 judged items before promotion.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** People follow the same framework as agents. It finds reviewers who need support before their misses reach customers.
- **Evidence:** A poor reviewer (60% catch rate) was ever trusted in 9% of simulated organisations; a good one (95%) ended trusted in 100%; escapes fell 15% for 21% more review time ([research/REPORT-v3.md](../../research/REPORT-v3.md), R1', tag `research/prereg-v3`).
- **Implementation:** `engine.py` `reviewer_key`, `TrustEngine.record_second_check`, `TrustEngine.reviewer_level`; `models.py` `Policy.reviewer_error_bar`, `Policy.reviewer_min_judged`
- **Test:** `engine/tests/test_engine.py::test_reviewer_trust_sorts_reviewers`
- **Notes:** Clean second checks count as evidence. Counting only canaries and disagreements never trusted anyone (v2).

## EA-5.11 Second-check rates
- **Statement:** A share of each reviewer's decisions MUST be second-checked: about 25% for reviewers at R1 (new) and about 5% for reviewers at R2 (trusted).
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** New reviewers are checked more, like new agents.
- **Evidence:** See EA-5.10.
- **Implementation:** `engine.py` `TrustEngine.should_second_check`; `models.py` `Policy.second_check_rate`
- **Test:** `engine/tests/test_engine.py::test_reviewer_trust_sorts_reviewers`

## EA-5.12 Reviewers step down on misses
- **Statement:** A reviewer MUST step down through the same evidence rules as agents (EA-3.5) when they miss canaries or approve actions that later become incidents, and the AI owner SHOULD be told.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** Quality control rather than blame.
- **Evidence:** See EA-5.10.
- **Implementation:** `engine.py` `TrustEngine.report_incident` (gives the approving reviewer a miss), `TrustEngine.record_canary`
- **Test:** `engine/tests/test_engine.py::test_reviewer_miss_on_incident_after_approval`

## EA-5.13 A second check measures the reviewer only
- **Statement:** A second check MUST update only the first reviewer's trust; the corrected agent outcome MUST be recorded separately.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** Keeps reviewer evidence and agent evidence apart.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.record_second_check`
- **Test:** `conformance/test_evidence_rules.py::test_a_second_check_updates_only_the_reviewer`

## EA-5.14 Agents can't see when they're watched
- **Statement:** An agent's view of its own trust record MUST exclude spot-check selections, canaries and second checks.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** An agent that can read its record mustn't learn which of its actions are watched.
- **Evidence:** See EA-2.9.
- **Implementation:** `record.py` `TrustRecord.read_for`
- **Test:** `conformance/test_conformance.py::test_sampling_is_unpredictable_and_hidden_from_the_agent`

## EA-5.15 Slowly degrading reviewers (known limitation)
- **Statement:** Implementations MAY add a faster check for reviewers whose catch rate declines gradually, such as a rolling window over recent canaries.
- **Status:** Open
- **Lifecycle:** Development
- **Rationale:** Reviewer trust catches a consistently poor reviewer quickly, but a gradually declining one slowly.
- **Evidence:** A reviewer declining from 95% to 50% catch spent a median of about 189 reviews still trusted after falling below 80% ([research/REPORT-v3.md](../../research/REPORT-v3.md), R1').
- **Implementation:** none
- **Test:** none yet
