# Reference API

**Informative.** The Python interface of the reference engine (`engine/`, package `earned_autonomy`). Another
implementation may expose any interface, as long as it meets the [requirements](requirements/). Data shapes are
defined in [`schema/`](schema/).

## Lifecycle of one action

```python
engine.tag(action)                               # EA-1.8: sets task_type and tag_confidence
decision = engine.decide(action, checks)         # EA-2.1: hold or act, written to the record
if decision.allowed:
    run_the_action()
    engine.mark_executed(action.action_id)       # EA-2.8: the spot-check draw happens here, hidden from the agent
else:
    ...                                          # held: shows up in engine.review_queue()
engine.record_outcome(action.action_id, label, reason_code, source, actor_id)   # EA-3.1: the evidence
```

## TrustEngine

```python
TrustEngine(policy=None, record=None, tagger=None, bounds=None, clock=utcnow, sampler=None,
            tool_floor_function=None)
```

| Argument | Meaning |
|---|---|
| `policy` | The starting `Policy`, used only for a new, empty record. An existing record carries its own policy. |
| `record` | A `TrustRecord` (memory or SQLite backend). Opening an existing record rebuilds all state from it (EA-6.8). |
| `tagger` | A `Tagger`; used when a proposed action has no task type (EA-1.8). |
| `bounds` | A `BoundStrategy`; `WilsonBound` by default (EA-3.4). |
| `clock` | Returns the current time as a timezone-aware datetime (EA-6.10). |
| `sampler` | The random source for spot-checks, canaries and second checks. Defaults to the operating system's cryptographic source (EA-2.8). Override only in tests. |
| `tool_floor_function` | `(tool, arguments, policy) -> "C1".."C4" or None`, for argument-dependent floors (EA-1.13). |

### Actions

| Method | Returns | Rules |
|---|---|---|
| `tag(action)` | the tag result | EA-1.8 |
| `decide(action, checks=None)` | `Decision` | EA-2.1 to EA-2.11, EA-1.9 to EA-1.14 |
| `decide_bundle([(action, checks), ...])` | list of `Decision` | EA-1.11 |
| `tool_floor(action)` | the highest floor among its write tools | EA-1.13 |
| `may_execute(action_id)` | whether the latest decision allows it now | EA-2.10 |
| `execute(action, run, checks=None)` | `run()`'s result, if allowed | EA-2.10 |
| `mark_executed(action_id)` | | EA-2.8 |
| `tools_for(task_type)` | the task type's tools | EA-1.12 |

### Evidence

| Method | Rules |
|---|---|
| `record_outcome(action_id, label, reason_code, source, actor_id, diff_reference=None)` | EA-3.1 to EA-3.6, EA-5.2 |
| `report_incident(action_id, severity, actor_id, note=None)` | EA-3.7, EA-3.16, EA-5.4, EA-5.12 |
| `review_queue()` | EA-5.1 |
| `on_version_published(agent_id, version, results=None, actor=None)` with `results = {task_type: {"hidden_pass": ..., "training_pass": ..., "hidden_test_count": ...}}` | EA-4.5 to EA-4.9 |
| `suites.add_correction_test(...)`, `suites.seed_hidden(...)`, `suites.hidden(actor, task_type)`, `suites.run_hidden(task_type, runner)` | EA-4.3, EA-4.4, EA-4.10 |

### Reviewers

| Method | Rules |
|---|---|
| `should_insert_canary(organisation_id, reviewer_id)`, `record_canary(organisation_id, reviewer_id, task_type, caught)` | EA-5.9 |
| `should_second_check(organisation_id, reviewer_id, task_type)`, `record_second_check(organisation_id, first_reviewer_id, task_type, found_error, ...)` | EA-5.10, EA-5.11, EA-5.13 |
| `reviewer_level(organisation_id, reviewer_id, task_type)` | EA-5.10 |

### Governance (every call names an actor and is logged)

| Method | Rules |
|---|---|
| `pause(actor, organisation_id, agent_id, task_type=None)`, `resume(...)` | EA-2.2, EA-5.6 |
| `promote(actor, organisation_id, agent_id, task_type)`, `demote(...)` | EA-6.3, EA-6.15 |
| `set_policy(actor, **changes)` | EA-6.5 |
| `add_task_type(actor, task_type, consequence, tools=None, description=..., examples=...)` | EA-1.1, EA-1.7 |
| `set_consequence(actor, task_type, consequence)` | EA-1.7, EA-3.8 |
| `set_task_error_bar(actor, task_type, error_bar)` | EA-3.9, EA-6.5 |

### Reading state

| Method | Returns | Rules |
|---|---|---|
| `get_state(organisation_id, agent_id, task_type=None)` | trust states with bounds, alerts and an explanation | EA-3.11, EA-5.7 |
| `explain(action_id)` | the decision, the evidence at the time and the policy version | EA-2.11 |
| `rebuild_state()`, `live_state()` | identical dictionaries | EA-6.8 |
| `record.verify()` | `VerifyResult` | EA-6.7 |
| `record.read_for("agent")` | the agent's filtered view | EA-5.14 |

## Supporting types

- `Policy`, `TaskTypePolicy`, `ProposedAction`, `ChecksResult`, `Decision`, `OutcomeEvent`, `TrustState`: see
  [`schema/`](schema/).
- `TrustRecord`, `MemoryBackend`, `SQLiteBackend`: the record (EA-6.6 to EA-6.10).
- `BoundStrategy`, `WilsonBound`, `ConfidenceSequenceBound`, `clean_floor`: the statistics (EA-3.4, EA-3.14).
- `Actor`, `GovernanceGuard`: roles and separation of duties (EA-6.1 to EA-6.4).
- `Tagger`, `RuleTagger`: tagging (EA-1.8).
- `format_timestamp`, `parse_timestamp`, `normalise_timestamp`: timestamps (EA-6.10).
- `lint_shared_write_tools`: EA-1.15.
