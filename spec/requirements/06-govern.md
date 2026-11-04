# 6. Govern

Throughout the lifecycle: who is accountable, who may change what, and the permanent record that makes it all checkable.

## EA-6.1 Roles and a named owner
- **Statement:** Every agent MUST have a named AI owner, and implementations MUST distinguish the roles AI owner, policy owner, reviewer, auditor and builder.
- **Status:** Default
- **Tier:** Core
- **Stability:** Development
- **Rationale:** Accountability belongs to a person, never to "the system".
- **Evidence:** none; a governance decision.
- **Implementation:** `governance.py` `Actor`, `GovernanceGuard`
- **Test:** `engine/tests/test_engine.py::test_catalogue_owned_by_ai_owner`
- **Notes:**
  - **AI owner:** a team lead, department head or similar. Owns the agent, its task catalogue and consequence levels.
  - **Policy owner:** sets error bars, caps, tool scope and sample rates.
  - **Reviewer:** judges outcomes.
  - **Auditor:** reads everything and changes nothing.
  - **Builder:** changes agent versions.

## EA-6.2 The AI owner maintains the task catalogue
- **Statement:** The AI owner for an area MUST maintain its task catalogue and assign each task type's consequence level; a tagger MAY propose new task types, which take effect only when the AI owner accepts them.
- **Status:** Default
- **Tier:** Core
- **Stability:** Development
- **Rationale:** The person accountable for the work decides how it is divided and how much proof each part needs.
- **Evidence:** none; an accountability decision.
- **Implementation:** `governance.py` (`add_task_type`, `set_consequence` allowed for the AI owner)
- **Test:** `engine/tests/test_engine.py::test_catalogue_owned_by_ai_owner`

## EA-6.3 Agents can't govern themselves
- **Statement:** An agent MUST NOT be able to change its own trust, tests, checks, policy or trust record, though it MAY read its own record as filtered by EA-3.3.
- **Status:** Tested
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** No self-promotion.
- **Evidence:** All 28 attacks blocked ([research/REPORT.md](../../research/REPORT.md), G4).
- **Implementation:** `governance.py` `GovernanceGuard`
- **Test:** `conformance/test_conformance.py::test_c5_governance_attacks_blocked_and_logged`

## EA-6.4 Separation of duties
- **Statement:** A builder of an agent MUST NOT approve that agent's promotions, change its error bars, caps or sample rates, or edit its tests or checks.
- **Status:** Tested
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Nobody approves their own work.
- **Evidence:** See EA-6.3.
- **Implementation:** `governance.py` `SEPARATION_OF_DUTIES_OPERATIONS`
- **Test:** `conformance/test_conformance.py::test_c5_governance_attacks_blocked_and_logged`

## EA-6.5 Every governance request is logged
- **Statement:** Every request to change policy, trust, tests or checks MUST name the person or system making it and MUST be written to the trust record, whether it is allowed or blocked.
- **Status:** Tested
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Blocked attempts are evidence too.
- **Evidence:** See EA-6.3.
- **Implementation:** `governance.py` `GovernanceGuard.request`
- **Test:** `conformance/test_conformance.py::test_c5_governance_attacks_blocked_and_logged`

## EA-6.6 Policy is versioned and takes effect immediately
- **Statement:** Every policy change MUST create a new policy version that takes effect immediately; a lower error bar MUST be re-evaluated against every affected trust key at once, dropping keys whose bound no longer holds to L1, while a higher error bar MUST only take effect at each key's next outcome.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** A stricter rule protects immediately; a looser one is earned.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.set_policy`, `TrustEngine.set_task_error_bar`; `models.py` `Policy.evolve`
- **Test:** `engine/tests/test_engine.py::test_lowering_error_bar_reevaluates_trusted_keys`
- **Notes:** A newly capped task type also drops to L1.

## EA-6.7 The record is append-only
- **Statement:** The trust record MUST be append-only, with no way to edit or delete an entry.
- **Status:** Default
- **Tier:** Core
- **Stability:** Development
- **Rationale:** It is the agent's whole employment history.
- **Evidence:** none; structural.
- **Implementation:** `record.py` `TrustRecord` (no edit API; SQLite triggers refuse updates and deletes)
- **Test:** `conformance/test_conformance.py::test_c5_record_has_no_edit_api`, `conformance/test_conformance.py::test_sqlite_refuses_update_delete_and_detects_tampering`

## EA-6.8 The record is tamper-evident
- **Statement:** Each record entry MUST include a SHA-256 hash of its canonical JSON and of the previous entry's hash, and verification MUST detect any edited, deleted or reordered entry.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Regulated buyers need history that provably hasn't been altered.
- **Evidence:** none; a cryptographic construction.
- **Implementation:** `record.py` `entry_hash`, `TrustRecord.verify`
- **Test:** `conformance/test_conformance.py::test_sqlite_refuses_update_delete_and_detects_tampering`, `conformance/test_conformance.py::test_tamper_delete_and_reorder_detected`, `conformance/test_conformance.py::test_tamper_edit_detected`, `conformance/test_conformance.py::test_tamper_rehash_one_entry_detected`, `conformance/test_timestamps.py::test_external_rehash_of_the_stored_record_matches_the_chain`

## EA-6.9 State is rebuilt from the record
- **Statement:** Replaying the trust record from empty MUST reproduce every trust state exactly.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** The record is the truth; state is only a cache of it.
- **Evidence:** none; structural.
- **Implementation:** `engine.py` `TrustEngine.rebuild_state`, `TrustEngine.live_state`
- **Test:** `conformance/test_conformance.py::test_c4_replay_reproduces_state_exactly`, `conformance/test_conformance.py::test_c4_replay_sqlite_reopen`, `conformance/test_tool_floor.py::test_tool_floor_decisions_replay_and_keep_args_out_of_the_record`

## EA-6.10 Sequence, not time, orders the record
- **Statement:** The trust record's order MUST be each entry's sequence number in the hash chain, and replay, scans and audits MUST NOT order entries by timestamp.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Clocks drift and servers disagree.
- **Evidence:** none; structural.
- **Implementation:** `record.py` (scans ordered by `sequence`)
- **Test:** `conformance/test_timestamps.py::test_replay_follows_sequence_not_timestamps_under_clock_skew`

## EA-6.11 One exact timestamp format
- **Statement:** Every timestamp in the trust record MUST be ISO 8601 in UTC with exactly three digits of milliseconds and a `Z` suffix (`YYYY-MM-DDTHH:MM:SS.sssZ`), other ISO 8601 forms with a time zone MUST be normalised to it when read, and timestamps with no time zone MUST be rejected.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:**
  - Auditors can read it at a glance.
  - UTC has no daylight-saving ambiguity: Melbourne's local clock repeats an hour each April.
  - One fixed format keeps the hash chain stable, since the same moment always produces the same bytes.
- **Evidence:** none; a format decision.
- **Implementation:** `models.py` `format_timestamp`, `parse_timestamp`, `normalise_timestamp`
- **Test:** `conformance/test_schema.py::test_record_entries_validate_against_the_schema`, `conformance/test_timestamps.py::test_every_record_timestamp_uses_the_canonical_format`, `conformance/test_timestamps.py::test_external_rehash_of_the_stored_record_matches_the_chain`, `conformance/test_timestamps.py::test_format_is_exact_even_at_zero_milliseconds`, `conformance/test_timestamps.py::test_naive_datetimes_and_strings_are_rejected`, `conformance/test_timestamps.py::test_old_forms_normalise_to_the_canonical_string`, `conformance/test_timestamps.py::test_round_trip`
- **Notes:** Products show local time; storage is UTC. A zero-millisecond moment still prints `.000Z`.

## EA-6.12 Epoch time stays at the edges
- **Statement:** Epoch milliseconds MAY be used in interfaces and internal code if the name says so in full (for example `created_at_epoch_milliseconds`), and MUST be converted before anything enters the trust record.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Convenient for maths, unreadable in an audit.
- **Evidence:** none; a format decision.
- **Implementation:** none needed
- **Test:** none yet

## EA-6.13 The record is kept permanently
- **Statement:** The trust record and every decision MUST be retained permanently.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** It is the evidence behind every level, for agents and reviewers alike.
- **Evidence:** none; a governance decision.
- **Implementation:** none needed (no deletion path)
- **Test:** `conformance/test_conformance.py::test_c5_record_has_no_edit_api`

## EA-6.14 References and labels, not customer content
- **Statement:** The trust record MUST hold references, labels and hashes only (action identifiers, task types, outcomes, reason codes, versions, actor identifiers and a payload hash), and MUST NOT hold customer content such as messages, names or amounts.
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** Privacy law (in Australia, Australian Privacy Principle 11.2) requires personal information to be destroyed or de-identified once it's no longer needed. Content stays in the source system under its normal retention; the permanent record loses nothing it needs when that content is deleted.
- **Evidence:** none; a legal and design decision.
- **Implementation:** `models.py` `payload_hash`; `record.py`
- **Test:** `conformance/test_conformance.py::test_record_holds_no_customer_content`, `conformance/test_tool_floor.py::test_tool_floor_decisions_replay_and_keep_args_out_of_the_record`

## EA-6.15 Records follow the schema
- **Statement:** Proposed actions, decisions, outcome events, trust states, policies and record entries MUST validate against the JSON Schemas in [`schema/`](../schema/).
- **Status:** Default
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** One source of truth for the data model, so other implementations interoperate.
- **Evidence:** none; structural.
- **Implementation:** `models.py` (`to_dict` on each model)
- **Test:** `conformance/test_schema.py::test_engine_objects_validate_against_the_schemas`, `conformance/test_schema.py::test_record_entries_validate_against_the_schema`

## EA-6.16 Provider and deployer (known gap)
- **Statement:** When the agent's provider and the organisation deploying it are different parties, the roles in EA-6.1 SHOULD be assigned to a named person in each party in writing, and both parties SHOULD be able to read the record for the agent's actions in the deploying organisation.
- **Status:** Open
- **Tier:** Standard
- **Stability:** Development
- **Rationale:** The specification treats the organisation as one party. In B2B deployments the hardest question is who owns what when an agent acts across both parties' systems; it must be settled before the agent acts, not after an incident.
- **Evidence:** none yet.
- **Implementation:** none yet
- **Test:** none yet
- **Notes:** Open questions: who may pause (EA-3.9), who sets consequence levels, and whether trust earned with one deployer may inform another (EA-1.1 says no).
