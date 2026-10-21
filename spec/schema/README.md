# Schema

**Normative.** JSON Schema (draft 2020-12) for the data the framework exchanges and records. These files are the
source of truth for field names and shapes (EA-6.15); the reference engine's objects are tested against them
(`conformance/test_schema.py`).

| Schema | What it describes | Rules |
|---|---|---|
| [`proposed-action.schema.json`](proposed-action.schema.json) | An action before it happens | EA-7.5, EA-7.11, EA-2.5 |
| [`decision.schema.json`](decision.schema.json) | Hold or act, and why | EA-2.1, EA-2.12 |
| [`outcome-event.schema.json`](outcome-event.schema.json) | One judgement of one action | EA-1.2, EA-1.4, EA-3.5 |
| [`trust-state.schema.json`](trust-state.schema.json) | A trust key's current level and evidence, by source | EA-2.14, EA-1.18, EA-6.9 |
| [`policy.schema.json`](policy.schema.json) | The task catalogue, error bars, thresholds and evidence weights | EA-7.1, EA-6.6, EA-1.14, EA-1.18, EA-2.15 |
| [`record-entry.schema.json`](record-entry.schema.json) | One entry of the hash-chained trust record | EA-6.7 to EA-6.11 |

Timestamps use one exact format: ISO 8601 UTC with milliseconds and a `Z` suffix (EA-6.11). Identifiers are `urn:`
names, not web addresses; nothing is fetched.
