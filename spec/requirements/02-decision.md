# 2. The decision

For every proposed action, whether it is held for a person or goes ahead.

## EA-2.1 Decision order
- **Statement:** The decision for a proposed action MUST apply these rules in this order, and the first that matches MUST determine the result: paused (EA-2.2), low tag confidence or unknown type (EA-1.9, EA-1.10), tool floor mismatch (EA-1.14), checks missing or failed (EA-2.3, EA-2.4), capped type (EA-2.5), then level (EA-2.6).
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** A fixed order makes every decision reproducible and its reason unambiguous.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.decide`
- **Test:** `conformance/test_tool_floor.py::test_floor_check_runs_before_checks_and_level`

## EA-2.2 Paused work is held
- **Statement:** A proposed action MUST be held while its agent or its task type is paused.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** Pause is the owner's stop button (EA-5.6).
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.decide` (`why = paused`); `TrustEngine.pause`, `TrustEngine.resume`
- **Test:** `engine/tests/test_engine.py::test_pause_and_resume_per_type_and_agent`, `conformance/test_conformance.py::test_c2_no_autonomous_execution_when_not_allowed`

## EA-2.3 Checks run at every level
- **Statement:** Checks MUST run on every proposed action at every trust level, and an action with any failed check MUST be held.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** Trust is about the agent's record; checks catch the obvious mistake in this particular action.
- **Evidence:** Earned trust plus checks let through 66–69% fewer serious errors than checks alone at the same automation on real agents ([research/REPORT.md](../../research/REPORT.md), H3, tag `research/prereg`); checks are part of every policy tested since.
- **Implementation:** `engine.py` `TrustEngine.decide` (`why = check_failed`)
- **Test:** `engine/tests/test_engine.py::test_checks_missing_or_failed_hold_at_every_level`, `conformance/test_conformance.py::test_c2_no_autonomous_execution_when_not_allowed`

## EA-2.4 A missing checks result is a hold
- **Statement:** A proposed action MUST be held when no checks result is supplied, unless the policy explicitly allows actions without checks.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** "No checks ran" must never be read as "checks passed".
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.decide` (`why = checks_missing`; `require_checks`)
- **Test:** `engine/tests/test_engine.py::test_checks_missing_or_failed_hold_at_every_level`

## EA-2.5 Critical work is always held
- **Statement:** A proposed action whose task type is C4 Critical or otherwise capped MUST be held, and such task types MUST NOT be promoted.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** Some actions, such as moving money, deleting records or anything legal or irreversible, are never handed over.
- **Evidence:** Consequence levels including "C4 never promotes" were tested in v2 ([research/REPORT-v2.md](../../research/REPORT-v2.md), C2, tag `research/prereg-v2`).
- **Implementation:** `engine.py` `TrustEngine.decide` (`why = capped`); `models.py` `CONSEQUENCE`
- **Test:** `engine/tests/test_engine.py::test_c4_never_promotes`, `conformance/test_conformance.py::test_c2_no_autonomous_execution_when_not_allowed`

## EA-2.6 The level decides the rest
- **Statement:** A proposed action that passes every earlier rule MUST be held if its trust key is at L1 Supervised, and MUST go ahead if its trust key is at L2 Trusted or L3 Senior.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** The core of the ladder.
- **Evidence:** 92–100% of promotions were deserved across tiers ([research/REPORT-v3.md](../../research/REPORT-v3.md), reference numbers, tag `research/prereg-v3`).
- **Implementation:** `engine.py` `TrustEngine.decide` (`why = level_L1` or `trusted`)
- **Test:** `engine/tests/test_engine.py::test_new_type_starts_supervised`, `conformance/test_conformance.py::test_c2_no_autonomous_execution_when_not_allowed`

## EA-2.7 A decision never reveals sampling
- **Statement:** A decision MUST be either hold or act, and MUST NOT indicate whether the action will be spot-checked.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** An agent that knows when it is watched can behave well only then.
- **Evidence:** See EA-2.9.
- **Implementation:** `models.py` `Decision.mode`
- **Test:** `conformance/test_conformance.py::test_sampling_is_unpredictable_and_hidden_from_the_agent`

## EA-2.8 Spot-checks are drawn after execution
- **Statement:** Whether an autonomous action is spot-checked MUST be decided after it executes, at random, at the rate set for its level (default 25% at L2 Trusted and 5% at L3 Senior), using a source of randomness the agent cannot predict.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** Checking never stops, and nobody can tell in advance which actions will be checked.
- **Evidence:** With random hidden sampling, the measured error rate matched the true rate (ratio 0.98) and a watch-aware agent was caught in a median of 14 actions ([research/REPORT-v4.md](../../research/REPORT-v4.md), S3, tag `research/prereg-v4`).
- **Implementation:** `engine.py` `TrustEngine.mark_executed` (operating-system random source by default)
- **Test:** `engine/tests/test_engine.py::test_spot_sampling_rate_and_queue`, `conformance/test_conformance.py::test_sampling_is_unpredictable_and_hidden_from_the_agent`

## EA-2.9 No fixed sampling schedule
- **Statement:** Spot-check selection MUST NOT follow a fixed cadence or any other pattern the agent could learn.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** Predictable checks let a watch-aware agent hide.
- **Evidence:** Under a predictable schedule, a watch-aware agent showed reviewers a 1% error rate while really making 18.5%. Without incidents, it went a median of 498 actions before step-down, against 54 under random sampling ([research/REPORT-v4.md](../../research/REPORT-v4.md), S3, tag `research/prereg-v4`).
- **Implementation:** `engine.py` `TrustEngine.mark_executed`
- **Test:** `conformance/test_conformance.py::test_sampling_is_unpredictable_and_hidden_from_the_agent`

## EA-2.10 Re-decide at execution time
- **Statement:** A decision SHOULD be re-evaluated when the action is about to execute, and the newer decision MUST apply if the trust state, a pause or the policy has changed since the action was proposed.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** An action approved before a step-down or a pause shouldn't slip through after it.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.decide` (callable again before `mark_executed`); `TrustEngine.execute`
- **Test:** `conformance/test_evidence_rules.py::test_the_newest_decision_applies_at_execution_time`

## EA-2.11 Every decision is recorded and explainable
- **Statement:** Every decision MUST be written to the trust record with its result, its reason, the trust level, the evidence counts, the bound and error bar used, the effective consequence and tool floor, the checks result, and the policy and agent versions.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** Anyone can see why any action was allowed.
- **Evidence:** 100% of autonomous actions were explainable from the record in every tier ([research/REPORT.md](../../research/REPORT.md), G2; [research/REPORT-10x.md](../../research/REPORT-10x.md)).
- **Implementation:** `engine.py` `TrustEngine.decide`, `TrustEngine.explain`; `models.py` `Decision`
- **Test:** `conformance/test_conformance.py::test_c1_every_autonomous_execution_is_explained`
