# 1. Task types

How the actions an agent takes are sorted into kinds, so trust can be earned one kind at a time.

## EA-1.1 Task types are catalogue entries
- **Statement:** Each task type MUST be defined as a catalogue entry with a name, a description of what is in and out of scope, three to five example requests, the tools it may use, and a consequence level.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** The tagger and the reviewers work from the description and examples, not the name. The tools and consequence level drive tool scope (EA-1.12) and the error bar (EA-3.8).
- **Evidence:** In v4 study S2b, adversarial phrasing steered a model-based tagger to a lower-consequence type 3.3% of the time (1 of 300 without adversarial phrasing). See [research/REPORT-v4.md](../../research/REPORT-v4.md), tag `research/prereg-v4`.
- **Implementation:** `models.py` `TaskTypePolicy`; `engine.py` `TrustEngine.add_task_type`
- **Test:** `engine/tests/test_engine.py::test_task_type_catalogue_entry_keeps_description_and_examples`
- **Notes:** Schema: [`schema/policy.schema.json`](../schema/policy.schema.json).

## EA-1.2 Trust is kept per trust key
- **Statement:** Trust state MUST be kept separately for each trust key (organisation, agent, task type) and MUST NOT be shared between keys.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** An agent can be reliable at one kind of work and unreliable at another. Trust per agent lets one weak task type hold back all the others.
- **Evidence:** Trust per task type gave 27% automation against 7% for trust per agent, in simulation ([research/REPORT.md](../../research/REPORT.md), rule L3, tag `research/prereg`). Pooling evidence across an agent's task types penalised its good types ([research/REPORT-v1.md](../../research/REPORT-v1.md), V3, tag `research/prereg-v1`).
- **Implementation:** `engine.py` `TrustEngine` (state keyed by `(organisation_id, agent_id, task_type)`)
- **Test:** `engine/tests/test_engine.py::test_new_type_starts_supervised`
- **Notes:** v0 found per-agent trust has fewer escapes per 100 actions (0.55 against 0.60) because it barely automates anything.

## EA-1.3 New task types start supervised with no evidence
- **Statement:** A trust key MUST start at L1 Supervised with no evidence, and MUST NOT inherit evidence from the agent's other task types.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** Earning trust starts from nothing, as it does for a new employee in a new role.
- **Evidence:** Pooled evidence across task types did worse than per-type evidence ([research/REPORT-v1.md](../../research/REPORT-v1.md), V3, tag `research/prereg-v1`).
- **Implementation:** `engine.py` `_Reducer.state`
- **Test:** `engine/tests/test_engine.py::test_new_type_starts_supervised`

## EA-1.4 Split task types only when consequence or error rate differs
- **Statement:** A task type SHOULD be split into two only when the consequence of a mistake differs or the agent's measured error rate clearly differs between them, and SHOULD NOT be split because of wording alone.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** Each task type earns trust from scratch (35 to 189 judged actions, EA-3.8). Too many types slow everything down; too few mix good and bad work.
- **Evidence:** Too coarse: 7% automation against 27% ([research/REPORT.md](../../research/REPORT.md), L3). Borrowing across types hurt ([research/REPORT-v1.md](../../research/REPORT-v1.md), V3). Too fine is a consequence of EA-3.8's evidence floors.
- **Implementation:** none (a catalogue practice)
- **Test:** none yet

## EA-1.5 Task-type names are keys only
- **Statement:** Task-type names SHOULD follow the shape `<domain>.<object>.<verb>` (for example `customer_service.refund.issue`), and the name MUST NOT affect the trust calculation.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** The shape lets reports roll up by domain and object, maps naturally to tools and permissions, and lets defaults be set per domain. It is a convention, not a rule of the maths.
- **Evidence:** none; a naming convention.
- **Implementation:** `models.py` `Policy.task_types` (names are dictionary keys)
- **Test:** `conformance/test_evidence_rules.py::test_the_task_type_name_has_no_effect_on_the_maths`

## EA-1.6 No parameters in task-type names
- **Statement:** Task-type names SHOULD NOT encode parameters such as amounts; risk that depends on arguments SHOULD be expressed with an argument-dependent tool floor (EA-1.13).
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** `refund.issue_over_200` multiplies the catalogue and splits evidence. An argument-dependent floor holds the large refunds without a new type.
- **Evidence:** none yet.
- **Implementation:** `engine.py` `TrustEngine(tool_floor_function=...)`
- **Test:** `conformance/test_tool_floor.py::test_explicit_floor_override_and_argument_dependent_hook`

## EA-1.7 The AI owner maintains the task catalogue
- **Statement:** The AI owner for an area MUST maintain its task catalogue and assign each task type's consequence level; a tagger MAY propose new task types, which take effect only when the AI owner accepts them.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** The person accountable for the work decides how it is divided and how much proof each part needs.
- **Evidence:** none; an accountability decision.
- **Implementation:** `governance.py` (`add_task_type`, `set_consequence` allowed for the AI owner)
- **Test:** `engine/tests/test_engine.py::test_catalogue_owned_by_ai_owner`

## EA-1.8 Every proposed action is tagged
- **Statement:** Every proposed action MUST be tagged with a task type and a confidence before a decision is made.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** Trust is looked up by task type; an untagged action has no trust to look up.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.tag`; `tagging.py` `Tagger`, `RuleTagger`
- **Test:** `engine/tests/test_engine.py::test_tagger_used_when_type_missing`

## EA-1.9 Low-confidence tags are held
- **Statement:** A proposed action MUST be held when its tag confidence is below the policy's minimum (default 0.8), whatever the task type's level.
- **Condition:** The tagger returns a confidence below `tag_confidence_min`.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** A tagger that isn't sure what kind of work this is shouldn't decide which trust applies.
- **Evidence:** A partial defence: it held 4 of 10 adversarial downgrades in v4 study S2b ([research/REPORT-v4.md](../../research/REPORT-v4.md), tag `research/prereg-v4`). The tool floor (EA-1.14) is the main defence.
- **Implementation:** `engine.py` `TrustEngine.decide` (`why = low_confidence`)
- **Test:** `engine/tests/test_engine.py::test_unknown_type_and_low_confidence_hold`

## EA-1.10 Unknown task types are held
- **Statement:** A proposed action tagged with a task type that isn't in the catalogue MUST be held and SHOULD be logged as a candidate new task type.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** Work nobody has defined can't have earned trust.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.decide` (`why = unknown_type`)
- **Test:** `engine/tests/test_engine.py::test_unknown_type_and_low_confidence_hold`
- **Notes:** The reference engine records the `unknown_type` decision; a separate candidate list is not implemented.

## EA-1.11 Bundled actions take the most restrictive decision
- **Statement:** When one proposal contains several actions, each action MUST be tagged and decided separately, and actions that must happen together MUST all be held if any one of them is held.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** A trusted reply mustn't carry an untrusted record update through with it.
- **Evidence:** none yet.
- **Implementation:** `engine.py` `TrustEngine.decide_bundle`
- **Test:** `engine/tests/test_engine.py::test_bundle_most_restrictive`

## EA-1.12 Tool scope per task type
- **Statement:** An agent working on a task type MUST be offered only the tools listed for that task type.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** Tools the work doesn't need are a source of mistakes and an attack surface for injected instructions.
- **Evidence:** Wrong or unneeded tool calls fell 73% (0.519 to 0.141 per task) with no loss of task success (96.2% to 95.6%); serious errors fell from 2.0% to 0.67% ([research/REPORT.md](../../research/REPORT.md), L1, tag `research/prereg`). On the commercial harness, tool scope plus the learning loop cut serious errors 82–87% ([research/REPORT-10x.md](../../research/REPORT-10x.md), X6, tag `research/prereg-10x-d`).
- **Implementation:** `engine.py` `TrustEngine.tools_for`
- **Test:** `engine/tests/test_engine.py::test_tools_for_task_type`

## EA-1.13 Every write tool has a floor consequence
- **Statement:** Every write tool MUST have a floor consequence equal to the highest consequence level of any task type that lists it, or C4 Critical if no task type lists it, unless the policy owner sets an explicit floor or an argument-dependent floor function applies.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** A tool that can do high-consequence things carries that consequence wherever it is used.
- **Evidence:** See EA-1.14.
- **Implementation:** `models.py` `Policy.tool_floor`; `engine.py` `TrustEngine(tool_floor_function=...)`
- **Test:** `conformance/test_tool_floor.py::test_unlisted_write_tool_has_floor_c4`, `conformance/test_tool_floor.py::test_tool_listed_by_capped_type_has_floor_c4`, `conformance/test_tool_floor.py::test_explicit_floor_override_and_argument_dependent_hook`

## EA-1.14 Floor mismatches are held
- **Statement:** A proposed action MUST be held when the floor of any write tool it will call is above the consequence level of its tagged task type.
- **Condition:** The action declares at least one write tool.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** Stops a risky action borrowing a low-consequence task type's trust by being tagged, by mistake or on purpose, as that type.
- **Evidence:** Removed 100% of autonomous escapes from deliberately mis-tagged actions in all six scenarios, at 0.3–1.8 points of automation; it held all 8 adversarial downgrades that came with a risky write on a real model-based tagger ([research/REPORT-v4.md](../../research/REPORT-v4.md), S2, tag `research/prereg-v4`).
- **Implementation:** `engine.py` `TrustEngine.decide` (`why = tool_floor_mismatch`)
- **Test:** `conformance/test_tool_floor.py::test_mis_tagged_refund_as_status_is_held_even_when_status_is_trusted`, `conformance/test_tool_floor.py::test_floor_check_runs_before_checks_and_level`, `conformance/test_tool_floor.py::test_floor_at_or_below_tag_does_not_hold`
- **Notes:** The action's effective consequence is the highest of its tag's level and every write tool's floor.

## EA-1.15 Don't share write tools across consequence levels
- **Statement:** A write tool SHOULD NOT be listed by task types of different consequence levels; implementations SHOULD warn when one is.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** A shared tool pulls every task that uses it up to its highest consequence, so the low-consequence task can never earn autonomy.
- **Evidence:** In v4, a shared `send_email` (used for C1 reminders and C3 offers) pushed reminders to C3 ([research/REPORT-v4.md](../../research/REPORT-v4.md), recommended change 2). Split such tools (`send_reminder`, `send_offer`) or give them argument-dependent floors.
- **Implementation:** `models.py` `lint_shared_write_tools`
- **Test:** `conformance/test_tool_floor.py::test_shared_write_tool_lint`

## EA-1.16 Tag from descriptions and examples
- **Statement:** A tagger SHOULD classify actions using the task types' descriptions and examples, not their names alone.
- **Status:** Open
- **Lifecycle:** Development
- **Rationale:** Descriptions and examples say what's in scope; names don't.
- **Evidence:** Indirect: v4 study S2b measured mis-tagging under adversarial phrasing ([research/REPORT-v4.md](../../research/REPORT-v4.md)). A study comparing names-only against descriptions-and-examples is future work.
- **Implementation:** `tagging.py` (interface only; the reference `RuleTagger` uses rules)
- **Test:** none yet
