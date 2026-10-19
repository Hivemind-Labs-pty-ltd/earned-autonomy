# Schema

**Normative.** JSON Schema (draft 2020-12) for the data the framework exchanges and records. These files are the
source of truth for field names and shapes (EA-6.14); the reference engine's objects are tested against them
(`conformance/test_schema.py`).

| Schema | What it describes | Rules |
|---|---|---|
| [`proposed-action.schema.json`](proposed-action.schema.json) | An action before it happens | EA-1.8, EA-1.14 |
| [`decision.schema.json`](decision.schema.json) | Hold or act, and why | EA-2.1, EA-2.11 |
| [`outcome-event.schema.json`](outcome-event.schema.json) | One judgement of one action | EA-3.1, EA-3.3, EA-5.2 |
| [`trust-state.schema.json`](trust-state.schema.json) | A trust key's current level and evidence | EA-3.4, EA-6.8 |
| [`policy.schema.json`](policy.schema.json) | The task catalogue, error bars and thresholds | EA-1.1, EA-6.5 |
| [`record-entry.schema.json`](record-entry.schema.json) | One entry of the hash-chained trust record | EA-6.6 to EA-6.10 |

Timestamps use one exact format: ISO 8601 UTC with milliseconds and a `Z` suffix (EA-6.10). Identifiers are `urn:`
names, not web addresses; nothing is fetched.
