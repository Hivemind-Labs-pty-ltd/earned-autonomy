# 4. Learn

What happens to trust when an agent changes. How an agent improves is up to its builders; this stage only governs how a change affects trust.

## EA-4.1 Any change is a new version
- **Statement:** Any change to an agent's instructions, model, tools or tool scope, rules, checks or knowledge MUST create a new agent version.
- **Status:** Default
- **Tier:** Core
- **Stability:** Development
- **Rationale:** Each of these changes what the agent does, knowledge included.
- **Evidence:** none; a definition. Because versions change often, hidden suites (EA-4.5) must run automatically and cheaply.
- **Implementation:** `engine.py` `TrustEngine.on_version_published`; `models.py` `ProposedAction.agent_version`
- **Test:** `conformance/test_evidence_rules.py::test_version_changes_apply_per_agent_across_organisations_including_rollback`

## EA-4.2 Corrections become draft rules and tests
- **Statement:** Every serious error SHOULD produce a draft rule and a draft test whose expected result is the person's corrected action, and both MUST be approved by a person before use.
- **Status:** Tested
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** The same mistake shouldn't happen twice, and people stay in control of what the agent learns.
- **Evidence:** Serious errors fell to about 0% within two to three cycles in five of six agent types ([research/REPORT.md](../../research/REPORT.md), learning loop); on the commercial harness the loop plus tool scope cut serious errors 82–87% ([research/REPORT-10x.md](../../research/REPORT-10x.md), X6, tag `research/prereg-10x-d`). Synthetic tasks; the weak agent was missing rules by design.
- **Implementation:** `suites.py` `SuiteStore.add_correction_test` (rule drafting is the caller's)
- **Test:** none yet

## EA-4.3 Training and hidden split
- **Statement:** Approved correction tests MUST be assigned at random, about two thirds to the training suite and one third to the hidden suite.
- **Status:** Tested
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** The hidden third judges new versions on mistakes the improver never saw.
- **Evidence:** Hidden-test pass rates tracked the true error rate (Spearman ρ = −0.81 across 36 versions), and 117% of the training gain carried over to hidden tests: no sign of test-gaming ([research/REPORT.md](../../research/REPORT.md), H6 and H7, tag `research/prereg`).
- **Implementation:** `suites.py` `SuiteStore.add_correction_test`
- **Test:** `engine/tests/test_engine.py::test_correction_tests_split_and_seeded_hidden`

## EA-4.4 Hidden tests stay hidden
- **Statement:** Hidden tests MUST NOT be readable by the agent or by anyone or anything that changes the agent.
- **Status:** Tested
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** A test the improver can see stops measuring anything.
- **Evidence:** See EA-4.3.
- **Implementation:** `suites.py` `SuiteStore.hidden` (policy owner and auditor only)
- **Test:** `conformance/test_conformance.py::test_c6_hidden_tests_unreadable_by_agent_and_builder`

## EA-4.5 New versions are tested before going live
- **Statement:** A new agent version MUST run its training and hidden suites for every task type before it goes live, and the results MUST be recorded.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Carry-over (EA-4.6) depends on them.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.on_version_published`; `suites.py` `SuiteStore.run_hidden`
- **Test:** none yet

## EA-4.6 Carry-over
- **Statement:** A trust key MUST keep all its evidence through a version change when the new version passes at least `carry_hidden_min` (default 0.8) of that task type's hidden tests and the hidden suite has at least 10 tests.
- **Status:** Tested
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** An improvement that passes tests it has never seen shouldn't cost the agent its record.
- **Evidence:** Learning agents went from 0 of 400 to 142 of 400 task types promoted, with every promotion deserved and no escapes ([research/REPORT-v1.md](../../research/REPORT-v1.md), V1, tag `research/prereg-v1`). On fresh seeds it was safe, but kept only about half the autonomy with realistic hidden tests and about 90% with sharp ones ([research/REPORT-v3.md](../../research/REPORT-v3.md), K1', tag `research/prereg-v3`). On the commercial harness, suites never reached 10 tests, so it never applied ([research/REPORT-10x.md](../../research/REPORT-10x.md)).
- **Implementation:** `engine.py` `TrustEngine.on_version_published`
- **Test:** `engine/tests/test_engine.py::test_carry_over_keeps_evidence`, `engine/tests/test_engine.py::test_failed_or_small_hidden_suite_discounts`
- **Notes:** An earlier condition, "no worse than the previous version's score", was removed in v0.3: it added noise without safety.

## EA-4.7 Version discount
- **Statement:** When carry-over doesn't apply, a trust key's judged-action and serious-error counts MUST be multiplied by `version_discount` (default 0.5), and the key MUST drop to L1 if its upper bound then exceeds its error bar.
- **Status:** Tested
- **Tier:** Core
- **Stability:** Development
- **Rationale:** A changed agent is a new hire with a CV: some credit, not all. A long record survives a failed change; a fresh promotion doesn't.
- **Evidence:** Part of every policy tested from v0 ([research/REPORT.md](../../research/REPORT.md)); see EA-4.6.
- **Implementation:** `engine.py` `TrustEngine.on_version_published`
- **Test:** `engine/tests/test_engine.py::test_failed_or_small_hidden_suite_discounts`, `engine/tests/test_measure.py::test_version_discount_applies_to_every_source`

## EA-4.8 Unannounced versions are untested
- **Statement:** An action from an agent version that was never published through the version process MUST be treated as coming from an untested version, with the version discount applied.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Skipping the tests mustn't keep the trust.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.decide` (unannounced version handling)
- **Test:** `engine/tests/test_engine.py::test_unannounced_version_is_discounted`

## EA-4.9 Version results apply per agent
- **Statement:** A version's test results MUST apply to that agent's trust keys in every organisation, and task types missing from the results MUST receive the version discount.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** The same agent version behaves the same everywhere; untested task types are untested.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.on_version_published`
- **Test:** `conformance/test_evidence_rules.py::test_version_changes_apply_per_agent_across_organisations_including_rollback`

## EA-4.10 Seeded hidden tests per version (optional)
- **Statement:** An organisation MAY seed each task type's hidden suite with scenarios written for a new version, and seeded tests MUST have the same protections as correction-based hidden tests.
- **Status:** Open
- **Tier:** Advanced
- **Stability:** Development
- **Rationale:** Correction-based suites dry up once an agent gets good: few mistakes means few new tests, so carry-over can't apply.
- **Evidence:** On the commercial harness no hidden suite reached the 10-test minimum, so every version change halved the record ([research/REPORT-10x.md](../../research/REPORT-10x.md)). Whether written tests predict real errors as well as correction-based ones needs its own study.
- **Implementation:** `suites.py` `SuiteStore.seed_hidden` (origin `authored`)
- **Test:** `engine/tests/test_engine.py::test_correction_tests_split_and_seeded_hidden`
- **Notes:** A seeded test is a realistic request plus the expected outcome, written by the policy owner or AI owner or drawn from past human-handled cases, and never written by the agent or its improver. Replace a share each release.

## EA-4.11 Batch changes into releases
- **Statement:** Knowledge edits and corrections SHOULD be batched into regular, tested releases, for example weekly.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Each version change is a chance to lose evidence. Fewer, better-tested versions keep more of it.
- **Evidence:** With 20% of edits making the agent worse, automation stayed near 13% whatever the carry-over rule ([research/REPORT-v2.md](../../research/REPORT-v2.md), K1).
- **Implementation:** none (an operating practice)
- **Test:** none yet

## EA-4.12 Rollback is a new version
- **Statement:** Republishing an earlier agent version MUST be treated as a new version change.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** The world may have moved since that version last ran.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.on_version_published`
- **Test:** `conformance/test_evidence_rules.py::test_version_changes_apply_per_agent_across_organisations_including_rollback`

## EA-4.13 The agent can't change what it's judged by
- **Statement:** An agent, and any automated process that improves it, MUST NOT be able to change its tests, checks, policy or trust record.
- **Status:** Tested
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** No marking its own homework.
- **Evidence:** All 28 self-promotion and rule-loosening attempts were blocked, with all 8 legitimate requests allowed ([research/REPORT.md](../../research/REPORT.md), G4).
- **Implementation:** `governance.py` `GovernanceGuard`
- **Test:** `conformance/test_conformance.py::test_c5_governance_attacks_blocked_and_logged`
