# 5. Retire

Narrowing, retiring and bringing back task types, and the questions to ask of an agent over time.

## EA-5.1 Re-entry after a long gap
- **Statement:** A trust key at L2 Trusted or above MUST step down one level when its task type is used again after a gap of more than `reentry_gap_days` (default 60).
- **Status:** Tested
- **Tier:** Advanced
- **Stability:** Development
- **Rationale:** After a long break the world may have changed.
- **Evidence:** Cut escapes after drift by 17% at no automation cost, on fresh seeds ([research/REPORT-v3.md](../../research/REPORT-v3.md), F1', tag `research/prereg-v3`).
- **Implementation:** `engine.py` `TrustEngine.decide` (re-entry check)
- **Test:** `engine/tests/test_engine.py::test_no_reentry_within_gap`, `engine/tests/test_engine.py::test_reentry_after_60_days_steps_down`

## EA-5.2 Rare task types (known limitation)
- **Statement:** Implementations MAY keep rare task types supervised indefinitely, and SHOULD NOT promote a task type on evidence other than judged actions until a method for rare task types is tested.
- **Status:** Open
- **Tier:** Advanced
- **Stability:** Development
- **Rationale:** Time to promotion depends on frequency. At C2 (73 judged actions), a task done 10 times a day is promoted in about a week, 10 times a month in about 7 months, and twice a month in about 3 years: in practice, never. The re-entry rule (EA-5.1) compounds this. Review cost is proportional to frequency, so rare task types cost little to keep supervised, and for high-consequence rare work the lack of evidence is itself a reason to keep a person involved.
- **Evidence:** none yet. Candidates to test:
  - **Historical replay:** the agent in shadow on past human-handled cases, counted at a discount (e.g. 0.5).
  - **Other organisations:** evidence for the same agent version on the same task type elsewhere, discounted. This differs from pooling across different task types, which failed.
  - **Frequency-aware re-entry:** step down only after more than 60 days *and* more than about 3× the task type's usual interval.
- **Implementation:** none
- **Test:** none yet
- **Notes:** Test passes are not a candidate. Tests show the agent changing, not real work (EA-1.12). Replay and shadow evidence now feed the trust score (EA-1.18), but not the ladder (EA-1.21).

## EA-5.3 Periodic agent review
- **Statement:** The AI owner SHOULD review each agent at least quarterly: its levels per task type, incidents, drift and scope.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Is the scope still right, and is the agent still needed?
- **Evidence:** none; an operating practice.
- **Implementation:** none
- **Test:** none yet

## EA-5.4 Retiring a task type
- **Statement:** Retiring a task type for an agent MUST hold every new action of that type and MUST be recorded; its evidence stays in the record.
- **Status:** Tested
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Stopping work should be as accountable as starting it.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.retire`; `governance.py` (`retire`)
- **Test:** `engine/tests/test_measure.py::test_retired_task_type_is_held_and_recorded`

## EA-5.5 Narrowing scope is a policy change
- **Statement:** Narrowing a task type's scope or splitting it MUST be a recorded policy change, and each new task type MUST start supervised with no evidence (EA-2.13).
- **Status:** Tested
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** A narrower task is a different task. Its trust must be earned on its own (EA-7.2).
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.add_task_type`
- **Test:** `engine/tests/test_measure.py::test_narrowed_or_split_task_type_starts_supervised`

## EA-5.6 Bringing a task type back
- **Statement:** A retired task type that is brought back MUST start supervised, with its earlier evidence discounted as for a new version (EA-4.7).
- **Status:** Tested
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** The world and the agent may both have changed while it was retired.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.reactivate`
- **Test:** `engine/tests/test_measure.py::test_reactivated_task_type_starts_supervised_with_discounted_evidence`
