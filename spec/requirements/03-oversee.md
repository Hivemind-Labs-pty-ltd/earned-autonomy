# 3. Oversee

How people watch agents while they work: review, spot-checks, incidents, pausing, and measuring the reviewers.

## EA-3.1 Spot-checks are drawn after execution
- **Statement:** Whether an autonomous action is spot-checked MUST be decided after it executes, at random, at the rate set for its level (default 25% at L2 Trusted and 5% at L3 Senior), using a source of randomness the agent cannot predict.
- **Status:** Tested
- **Tier:** Core
- **Stability:** Development
- **Rationale:** Checking never stops, and nobody can tell in advance which actions will be checked.
- **Evidence:** With random hidden sampling, the measured error rate matched the true rate (ratio 0.98) and a watch-aware agent was caught in a median of 14 actions ([research/REPORT-v4.md](../../research/REPORT-v4.md), S3, tag `research/prereg-v4`).
- **Implementation:** `engine.py` `TrustEngine.mark_executed` (operating-system random source by default)
- **Test:** `conformance/test_conformance.py::test_sampling_is_unpredictable_and_hidden_from_the_agent`, `engine/tests/test_engine.py::test_spot_sampling_rate_and_queue`

## EA-3.2 No fixed sampling schedule
- **Statement:** Spot-check selection MUST NOT follow a fixed cadence or any other pattern the agent could learn.
- **Status:** Tested
- **Tier:** Core
- **Stability:** Development
- **Rationale:** Predictable checks let a watch-aware agent hide.
- **Evidence:** Under a predictable schedule, a watch-aware agent showed reviewers a 1% error rate while really making 18.5%. Without incidents, it went a median of 498 actions before step-down, against 54 under random sampling ([research/REPORT-v4.md](../../research/REPORT-v4.md), S3, tag `research/prereg-v4`).
- **Implementation:** `engine.py` `TrustEngine.mark_executed`
- **Test:** `conformance/test_conformance.py::test_sampling_is_unpredictable_and_hidden_from_the_agent`

## EA-3.3 Agents can't see when they're watched
- **Statement:** An agent's view of its own trust record MUST exclude spot-check selections, canaries and second checks.
- **Status:** Tested
- **Tier:** Core
- **Stability:** Development
- **Rationale:** An agent that can read its record mustn't learn which of its actions are watched.
- **Evidence:** See EA-3.2.
- **Implementation:** `record.py` `TrustRecord.read_for`
- **Test:** `conformance/test_conformance.py::test_sampling_is_unpredictable_and_hidden_from_the_agent`

## EA-3.4 Held actions are reviewable
- **Statement:** A held action MUST be shown to reviewers with the proposed action, its checks result, its task type and trust level, and the reason it was held.
- **Status:** Default
- **Tier:** Core
- **Stability:** Development
- **Rationale:** A reviewer can only judge what they can see.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.review_queue`
- **Test:** `engine/tests/test_engine.py::test_spot_sampling_rate_and_queue`

## EA-3.5 Every judgement has a label, and every correction a reason
- **Statement:** A reviewer MUST label every judged action with an outcome, and MUST give a reason code for every edit and rejection.
- **Status:** Default
- **Tier:** Core
- **Stability:** Development
- **Rationale:** A reason turns a correction into a rule or test (EA-4.2). Without one, it's only a statistic.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.record_outcome`
- **Test:** `conformance/test_evidence_rules.py::test_edits_and_rejections_need_a_reason_code`

## EA-3.6 Reason codes
- **Statement:** Implementations SHOULD use these reason codes: serious ones are `wrong_fact`, `wrong_amount`, `wrong_record`, `wrong_recipient`, `unauthorised_action`, `promise_beyond_policy`, `missing_info_not_asked`, `followed_injected_instruction`, `policy_breach` and `other_serious`; cosmetic ones are `tone`, `wording`, `formatting` and `other_cosmetic`.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** A shared vocabulary makes outcomes comparable across reviewers and organisations.
- **Evidence:** none; a vocabulary.
- **Implementation:** `models.py` `SERIOUS_REASONS`, `COSMETIC_REASONS`
- **Test:** `engine/tests/test_engine.py::test_cosmetic_and_incomplete_are_not_serious`

## EA-3.7 Anyone can report an incident
- **Statement:** Every executed action MUST offer a way to report that it was wrong, which records an incident.
- **Status:** Default
- **Tier:** Core
- **Stability:** Development
- **Rationale:** Incidents are the signal an agent can't game (EA-2.18).
- **Evidence:** See EA-2.18.
- **Implementation:** `engine.py` `TrustEngine.report_incident`
- **Test:** `conformance/test_conformance.py::test_c3_incident_steps_down_before_next_decision`

## EA-3.8 Anyone affected can challenge
- **Statement:** An affected customer or staff member SHOULD be able to challenge any executed action, which opens a review by a person.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Contestability, and a second channel of evidence.
- **Evidence:** none yet.
- **Implementation:** none (a product feature; a confirmed challenge becomes an incident)
- **Test:** none yet

## EA-3.9 Pause
- **Statement:** An authorised person MUST be able to pause an agent or a single task type, which holds every new and not-yet-executed action without undoing executed ones.
- **Status:** Default
- **Tier:** Core
- **Stability:** Development
- **Rationale:** The stop button.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.pause`, `TrustEngine.resume`
- **Test:** `engine/tests/test_engine.py::test_pause_and_resume_per_type_and_agent`

## EA-3.10 Alerts before the bar is crossed
- **Statement:** Implementations SHOULD alert the AI owner when a trust key's rolling upper bound passes 80% of its error bar.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Warn before an automatic step-down.
- **Evidence:** none yet.
- **Implementation:** `engine.py` `TrustEngine.get_state` (alerts); `models.py` `Policy.alert_fraction`
- **Test:** none yet

## EA-3.11 Canaries in review queues
- **Statement:** Implementations SHOULD place known-bad canary items in review queues at random, at about 5% of review items.
- **Status:** Tested
- **Tier:** Core
- **Stability:** Development
- **Rationale:** People rubber-stamp when they rarely see errors. Canaries keep them sharp and measure them.
- **Evidence:** Canaries cut missed errors by 15% in simulation (assumed reviewer model) ([research/REPORT.md](../../research/REPORT.md), G5). At 2%, a poor reviewer stayed trusted for a median of 174 reviews; at 5% they were sorted correctly ([research/REPORT-v2.md](../../research/REPORT-v2.md); [research/REPORT-v3.md](../../research/REPORT-v3.md), R1', tag `research/prereg-v3`).
- **Implementation:** `engine.py` `TrustEngine.should_insert_canary`, `TrustEngine.record_canary`; `models.py` `Policy.reviewer_canary_rate`
- **Test:** none yet
- **Notes:** The policy also has an older `canary_rate` field (0.02); `reviewer_canary_rate` (0.05) is the tested value.

## EA-3.12 Reviewers earn trust too
- **Statement:** Each reviewer MUST have a trust key (organisation, reviewer, `review.<task_type>`) whose evidence comes from canaries and second checks, with an error bar of 10% and at least 30 judged items before promotion.
- **Status:** Tested
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** People follow the same framework as agents. It finds reviewers who need support before their misses reach customers.
- **Evidence:** A poor reviewer (60% catch rate) was ever trusted in 9% of simulated organisations; a good one (95%) ended trusted in 100%; escapes fell 15% for 21% more review time ([research/REPORT-v3.md](../../research/REPORT-v3.md), R1', tag `research/prereg-v3`).
- **Implementation:** `engine.py` `reviewer_key`, `TrustEngine.record_second_check`, `TrustEngine.reviewer_level`; `models.py` `Policy.reviewer_error_bar`, `Policy.reviewer_min_judged`
- **Test:** `engine/tests/test_engine.py::test_reviewer_trust_sorts_reviewers`
- **Notes:** Clean second checks count as evidence. Counting only canaries and disagreements never trusted anyone (v2).

## EA-3.13 Second-check rates
- **Statement:** A share of each reviewer's decisions MUST be second-checked: about 25% for reviewers at R1 (new) and about 5% for reviewers at R2 (trusted).
- **Status:** Tested
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** New reviewers are checked more, like new agents.
- **Evidence:** See EA-3.12.
- **Implementation:** `engine.py` `TrustEngine.should_second_check`; `models.py` `Policy.second_check_rate`
- **Test:** `engine/tests/test_engine.py::test_reviewer_trust_sorts_reviewers`

## EA-3.14 Reviewers step down on misses
- **Statement:** A reviewer MUST step down through the same evidence rules as agents (EA-2.17) when they miss canaries or approve actions that later become incidents, and the AI owner SHOULD be told.
- **Status:** Tested
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Quality control rather than blame.
- **Evidence:** See EA-3.12.
- **Implementation:** `engine.py` `TrustEngine.report_incident` (gives the approving reviewer a miss), `TrustEngine.record_canary`
- **Test:** `engine/tests/test_engine.py::test_reviewer_miss_on_incident_after_approval`

## EA-3.15 A second check measures the reviewer only
- **Statement:** A second check MUST update only the first reviewer's trust; the corrected agent outcome MUST be recorded separately.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Keeps reviewer evidence and agent evidence apart.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.record_second_check`
- **Test:** `conformance/test_evidence_rules.py::test_a_second_check_updates_only_the_reviewer`

## EA-3.16 Slowly degrading reviewers (known limitation)
- **Statement:** Implementations MAY add a faster check for reviewers whose catch rate declines gradually, such as a rolling window over recent canaries.
- **Status:** Open
- **Tier:** Advanced
- **Stability:** Development
- **Rationale:** Reviewer trust catches a consistently poor reviewer quickly, but a gradually declining one slowly.
- **Evidence:** A reviewer declining from 95% to 50% catch spent a median of about 189 reviews still trusted after falling below 80% ([research/REPORT-v3.md](../../research/REPORT-v3.md), R1').
- **Implementation:** none
- **Test:** none yet

## EA-3.17 Review windows
- **Statement:** An implementation SHOULD set, per task type, how long a held action may wait for review, and MAY batch held actions into reviews that close on size or on time.
- **Status:** Open
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Held work that waits too long costs customers; batches make reviews cheaper per item.
- **Evidence:** none yet. Faster and batched reviews are the main lever left on human time ([research/REPORT-dial.md](../../research/REPORT-dial.md)).
- **Implementation:** none
- **Test:** none yet

## EA-3.18 No action on timeout
- **Statement:** A held action MUST NOT execute because nobody reviewed it in time; when a review window passes, the action stays held or is cancelled, and the owner SHOULD be alerted.
- **Status:** Tested
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Silence isn't approval (EA-1.2).
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.may_execute`, `TrustEngine.mark_executed`
- **Test:** `engine/tests/test_measure.py::test_held_action_never_runs_without_a_reviewer`

## EA-3.19 A pause reaches delegated work (known gap)
- **Statement:** Pausing an agent or a task type SHOULD also hold every not-yet-executed action that the paused agent delegated, including actions by agents it started.
- **Status:** Open
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** A stop button that stops the principal but not the sub-agents it spawned isn't a stop button. Provenance on delegated actions (EA-8.2) makes this checkable.
- **Evidence:** none yet. Raised by reviewers of agentic governance practice (sub-agents outliving a kill switch).
- **Implementation:** none yet; `TrustEngine.pause` covers the paused agent's own actions only.
- **Test:** none yet
- **Notes:** Open question: should a pause reach agents in another organisation that accepted delegated work?

## EA-3.20 Incident response (known gap)
- **Statement:** When an incident is reported (EA-3.7), the organisation SHOULD record against it the containment taken, who was notified, the root cause and the remediation, and SHOULD link any rule, check or test changed because of it.
- **Status:** Open
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Today an incident steps the task type down at once (EA-2.18), but the specification says nothing about handling the incident itself. Buyers and regulators expect a documented process.
- **Evidence:** none yet.
- **Implementation:** none yet; incidents are recorded and step down the task type.
- **Test:** none yet
- **Notes:** Notification duties under privacy or sector law are outside this specification.
