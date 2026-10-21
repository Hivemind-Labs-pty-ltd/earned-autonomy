# Reference API

**Informative.** The Python interface of the reference engine (`engine/`, package `earned_autonomy`). Another
implementation may expose any interface, as long as it meets the [requirements](requirements/). Data shapes are
defined in [`schema/`](schema/).

## Lifecycle of one action

```python
engine.tag(action)                               # EA-7.5: sets task_type and tag_confidence
decision = engine.decide(action, checks)         # EA-2.1: hold or act, written to the record
if decision.allowed:
    run_the_action()
    engine.mark_executed(action.action_id)       # EA-3.1: the spot-check draw happens here, hidden from the agent
else:
    ...                                          # held: shows up in engine.review_queue()
engine.record_outcome(action.action_id, label, reason_code, source, actor_id)   # EA-1.2: the evidence
```

## TrustEngine

```python
TrustEngine(policy=None, record=None, tagger=None, bounds=None, clock=utcnow, sampler=None,
            tool_floor_function=None)
```

| Argument | Meaning |
|---|---|
| `policy` | The starting `Policy`, used only for a new, empty record. An existing record carries its own policy. |
| `record` | A `TrustRecord` (memory or SQLite backend). Opening an existing record rebuilds all state from it (EA-6.9). |
| `tagger` | A `Tagger`; used when a proposed action has no task type (EA-7.5). |
| `bounds` | A `BoundStrategy`; `WilsonBound` by default (EA-2.14). |
| `clock` | Returns the current time as a timezone-aware datetime (EA-6.11). |
| `sampler` | The random source for spot-checks, canaries and second checks. Defaults to the operating system's cryptographic source (EA-3.1). Override only in tests. |
| `tool_floor_function` | `(tool, arguments, policy) -> "C1".."C4" or None`, for argument-dependent floors (EA-7.8). |

### Actions

| Method | Returns | Rules |
|---|---|---|
| `tag(action)` | the tag result | EA-7.5 |
| `decide(action, checks=None)` | `Decision` | EA-2.1 to EA-2.12, EA-2.3 to EA-2.5 |
| `decide_bundle([(action, checks), ...])` | list of `Decision` | EA-2.10 |
| `tool_floor(action)` | the highest floor among its write tools | EA-7.8 |
| `may_execute(action_id)` | whether the latest decision allows it now | EA-2.11 |
| `execute(action, run, checks=None)` | `run()`'s result, if allowed | EA-2.11 |
| `mark_executed(action_id)` | | EA-3.1 |
| `tools_for(task_type)` | the task type's tools | EA-7.7 |

### Evidence

| Method | Rules |
|---|---|
| `record_outcome(action_id, label, reason_code, source, actor_id, diff_reference=None)` | EA-1.2 to EA-1.4, EA-2.14 to EA-2.17, EA-3.5 |
| `record_evidence(organisation_id, agent_id, task_type, source, serious, actor_id, agent_version=None, reference=None)`: `source` is `shadow`, `replay` or `test` | EA-1.18, EA-1.21 |
| `report_incident(action_id, severity, actor_id, note=None)` | EA-2.18, EA-1.10, EA-3.7, EA-3.14 |
| `review_queue()` | EA-3.4 |
| `on_version_published(agent_id, version, results=None, actor=None)` with `results = {task_type: {"hidden_pass": ..., "training_pass": ..., "hidden_test_count": ...}}` | EA-4.5 to EA-4.9 |
| `suites.add_correction_test(...)`, `suites.seed_hidden(...)`, `suites.hidden(actor, task_type)`, `suites.run_hidden(task_type, runner)` | EA-4.3, EA-4.4, EA-4.10 |

### Measure

| Method | Returns | Rules |
|---|---|---|
| `trust_score(organisation_id, agent_id, task_type)` | the trust score, 0 to 1 | EA-1.14 |
| `trust_report(organisation_id, agent_id, task_type=None)` | `{"profiles": [...], "summary": {...}}`: a trust profile per task type and the agent's trust summary | EA-1.13, EA-1.15, EA-1.16, EA-1.20, EA-2.22 |

A profile holds `trust_score`, `thin_evidence`, `estimated_error_rate`, `error_rate_interval`, `effective_evidence`,
`evidence_by_source`, `human_evidence_share`, `freshness`, `trend`, `autonomy_setting`, `implied_autonomy`, `dial`,
`actions` and `alerts`. The summary holds `share_of_actions_by_setting`, `incidents`, `incidents_last_30_days` and
`trends`. See [measure](measure.md).

Policy parameters: `trust_prior` (default `[1, 1]`), `trust_score_threshold` (0.975), `evidence_weights` (human 1.0,
shadow 1.0, replay 1.0, test 0.75), `human_evidence_min_share` (0.2), `promotion_rule` (`"bound"` or `"core_table"`,
EA-2.15), `dial_gain` (5) and `dial_floor` (0.02).

### Reviewers

| Method | Rules |
|---|---|
| `should_insert_canary(organisation_id, reviewer_id)`, `record_canary(organisation_id, reviewer_id, task_type, caught)` | EA-3.11 |
| `should_second_check(organisation_id, reviewer_id, task_type)`, `record_second_check(organisation_id, first_reviewer_id, task_type, found_error, ...)` | EA-3.12, EA-3.13, EA-3.15 |
| `reviewer_level(organisation_id, reviewer_id, task_type)` | EA-3.12 |

### Governance (every call names an actor and is logged)

| Method | Rules |
|---|---|
| `pause(actor, organisation_id, agent_id, task_type=None)`, `resume(...)` | EA-2.2, EA-3.9 |
| `promote(actor, organisation_id, agent_id, task_type)`, `demote(...)` | EA-6.4, EA-2.20 |
| `set_policy(actor, **changes)` | EA-6.6 |
| `add_task_type(actor, task_type, consequence, tools=None, description=..., examples=...)` | EA-7.1, EA-6.2 |
| `set_consequence(actor, task_type, consequence)` | EA-6.2, EA-1.5 |
| `set_task_error_bar(actor, task_type, error_bar)` | EA-1.6, EA-6.6 |
| `retire(actor, organisation_id, agent_id, task_type, reason=None)` | EA-5.4 |
| `reactivate(actor, organisation_id, agent_id, task_type)` | EA-5.6 |

### Reading state

| Method | Returns | Rules |
|---|---|---|
| `get_state(organisation_id, agent_id, task_type=None)` | trust states with bounds, alerts and an explanation | EA-1.11, EA-3.10 |
| `explain(action_id)` | the decision, the evidence at the time and the policy version | EA-2.12 |
| `rebuild_state()`, `live_state()` | identical dictionaries | EA-6.9 |
| `record.verify()` | `VerifyResult` | EA-6.8 |
| `record.read_for("agent")` | the agent's filtered view | EA-3.3 |

## Supporting types

- `Policy`, `TaskTypePolicy`, `ProposedAction`, `ChecksResult`, `Decision`, `OutcomeEvent`, `TrustState`: see
  [`schema/`](schema/).
- `TrustRecord`, `MemoryBackend`, `SQLiteBackend`: the record (EA-6.7 to EA-6.11).
- `BoundStrategy`, `WilsonBound`, `ConfidenceSequenceBound`, `clean_floor`: the bounds (EA-2.14, EA-2.19).
- `trust_score`, `posterior_interval`, `regularized_incomplete_beta`, `beta_quantile`: the trust score (EA-1.14, EA-1.15).
- `promotion_table`, `step_down_threshold`: the Core lookup tables (EA-2.15). `dial_spot_rate`: the dial (EA-2.22).
- `Actor`, `GovernanceGuard`: roles and separation of duties (EA-6.1 to EA-6.5).
- `Tagger`, `RuleTagger`: tagging (EA-7.5).
- `format_timestamp`, `parse_timestamp`, `normalise_timestamp`: timestamps (EA-6.11).
- `lint_shared_write_tools`: EA-7.9.
