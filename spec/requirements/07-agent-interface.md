# 7. Agent interface

What any agent must provide so the trust rules can work: tagged actions from a task catalogue, declared tools, a checks result and a version on every action. How the agent is built is not part of this specification.

## EA-7.1 Task types are catalogue entries
- **Statement:** Each task type MUST be defined as a catalogue entry with a name, a description of what is in and out of scope, three to five example requests, the tools it may use, and a consequence level.
- **Status:** Default
- **Tier:** Core
- **Stability:** Development
- **Rationale:** The tagger and the reviewers work from the description and examples, not the name. The tools and consequence level drive tool scope (EA-7.7) and the error bar (EA-1.5).
- **Evidence:** In v4 study S2b, adversarial phrasing steered a model-based tagger to a lower-consequence type 3.3% of the time (1 of 300 without adversarial phrasing). See [research/REPORT-v4.md](../../research/REPORT-v4.md), tag `research/prereg-v4`.
- **Implementation:** `models.py` `TaskTypePolicy`; `engine.py` `TrustEngine.add_task_type`
- **Test:** `engine/tests/test_engine.py::test_task_type_catalogue_entry_keeps_description_and_examples`
- **Notes:** Schema: [`schema/policy.schema.json`](../schema/policy.schema.json).

## EA-7.2 Split task types only when consequence or error rate differs
- **Statement:** A task type SHOULD be split into two only when the consequence of a mistake differs or the agent's measured error rate clearly differs between them, and SHOULD NOT be split because of wording alone.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Each task type earns trust from scratch (35 to 189 judged actions, EA-1.5). Too many types slow everything down; too few mix good and bad work.
- **Evidence:** Too coarse: 7% automation against 27% ([research/REPORT.md](../../research/REPORT.md), L3). Borrowing across types hurt ([research/REPORT-v1.md](../../research/REPORT-v1.md), V3). Too fine is a consequence of EA-1.5's evidence floors.
- **Implementation:** none (a catalogue practice)
- **Test:** none yet

## EA-7.3 Task-type names are keys only
- **Statement:** Task-type names SHOULD follow the shape `<domain>.<object>.<verb>` (for example `customer_service.refund.issue`), and the name MUST NOT affect the trust calculation.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** The shape lets reports roll up by domain and object, maps naturally to tools and permissions, and lets defaults be set per domain. It is a convention, not a rule of the maths.
- **Evidence:** none; a naming convention.
- **Implementation:** `models.py` `Policy.task_types` (names are dictionary keys)
- **Test:** `conformance/test_evidence_rules.py::test_the_task_type_name_has_no_effect_on_the_maths`

## EA-7.4 No parameters in task-type names
- **Statement:** Task-type names SHOULD NOT encode parameters such as amounts; risk that depends on arguments SHOULD be expressed with an argument-dependent tool floor (EA-7.8).
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** `refund.issue_over_200` multiplies the catalogue and splits evidence. An argument-dependent floor holds the large refunds without a new type.
- **Evidence:** none yet.
- **Implementation:** `engine.py` `TrustEngine(tool_floor_function=...)`
- **Test:** `conformance/test_tool_floor.py::test_explicit_floor_override_and_argument_dependent_hook`

## EA-7.5 Every proposed action is tagged
- **Statement:** Every proposed action MUST be tagged with a task type and a confidence before a decision is made.
- **Status:** Default
- **Tier:** Core
- **Stability:** Development
- **Rationale:** Trust is looked up by task type; an untagged action has no trust to look up.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.tag`; `tagging.py` `Tagger`, `RuleTagger`
- **Test:** `engine/tests/test_engine.py::test_tagger_used_when_type_missing`

## EA-7.6 Tag from descriptions and examples
- **Statement:** A tagger SHOULD classify actions using the task types' descriptions and examples, not their names alone.
- **Status:** Open
- **Tier:** Advanced
- **Stability:** Development
- **Rationale:** Descriptions and examples say what's in scope; names don't.
- **Evidence:** Indirect: v4 study S2b measured mis-tagging under adversarial phrasing ([research/REPORT-v4.md](../../research/REPORT-v4.md)). A study comparing names-only against descriptions-and-examples is future work.
- **Implementation:** `tagging.py` (interface only; the reference `RuleTagger` uses rules)
- **Test:** none yet

## EA-7.7 Tool scope per task type
- **Statement:** An agent working on a task type MUST be offered only the tools listed for that task type.
- **Status:** Tested
- **Tier:** Core
- **Stability:** Development
- **Rationale:** Tools the work doesn't need are a source of mistakes and an attack surface for injected instructions.
- **Evidence:** Wrong or unneeded tool calls fell 73% (0.519 to 0.141 per task) with no loss of task success (96.2% to 95.6%); serious errors fell from 2.0% to 0.67% ([research/REPORT.md](../../research/REPORT.md), L1, tag `research/prereg`). On the commercial harness, tool scope plus the learning loop cut serious errors 82–87% ([research/REPORT-10x.md](../../research/REPORT-10x.md), X6, tag `research/prereg-10x-d`).
- **Implementation:** `engine.py` `TrustEngine.tools_for`
- **Test:** `engine/tests/test_engine.py::test_tools_for_task_type`

## EA-7.8 Every write tool has a floor consequence
- **Statement:** Every write tool MUST have a floor consequence equal to the highest consequence level of any task type that lists it, or C4 Critical if no task type lists it, unless the policy owner sets an explicit floor or an argument-dependent floor function applies.
- **Status:** Tested
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** A tool that can do high-consequence things carries that consequence wherever it is used.
- **Evidence:** See EA-2.5.
- **Implementation:** `models.py` `Policy.tool_floor`; `engine.py` `TrustEngine(tool_floor_function=...)`
- **Test:** `conformance/test_tool_floor.py::test_explicit_floor_override_and_argument_dependent_hook`, `conformance/test_tool_floor.py::test_tool_listed_by_capped_type_has_floor_c4`, `conformance/test_tool_floor.py::test_unlisted_write_tool_has_floor_c4`

## EA-7.9 Don't share write tools across consequence levels
- **Statement:** A write tool SHOULD NOT be listed by task types of different consequence levels; implementations SHOULD warn when one is.
- **Status:** Tested
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** A shared tool pulls every task that uses it up to its highest consequence, so the low-consequence task can never earn autonomy.
- **Evidence:** In v4, a shared `send_email` (used for C1 reminders and C3 offers) pushed reminders to C3 ([research/REPORT-v4.md](../../research/REPORT-v4.md), recommended change 2). Split such tools (`send_reminder`, `send_offer`) or give them argument-dependent floors.
- **Implementation:** `models.py` `lint_shared_write_tools`
- **Test:** `conformance/test_tool_floor.py::test_shared_write_tool_lint`

## EA-7.10 Every action comes with a checks result
- **Statement:** The agent's platform MUST supply the result of its checks with every proposed action; a missing result MUST be treated as a failed check (EA-2.7).
- **Status:** Tested
- **Tier:** Core
- **Stability:** Development
- **Rationale:** Checks are the agent's own acceptance criteria. Which checks to run is up to its builders; that a result exists is not.
- **Evidence:** See EA-2.6.
- **Implementation:** `engine.py` `TrustEngine.decide` (`checks_missing`)
- **Test:** `engine/tests/test_engine.py::test_checks_missing_or_failed_hold_at_every_level`

## EA-7.11 Every action carries a version
- **Statement:** Every proposed action MUST carry the identifier of the agent version that produced it.
- **Status:** Tested
- **Tier:** Core
- **Stability:** Development
- **Rationale:** Trust follows the version (EA-4.1, EA-4.7). Without a version, no change can be detected.
- **Evidence:** none; structural.
- **Implementation:** `models.py` `ProposedAction.agent_version`; [schema](../schema/proposed-action.schema.json)
- **Test:** `engine/tests/test_measure.py::test_every_proposed_action_carries_a_version`
