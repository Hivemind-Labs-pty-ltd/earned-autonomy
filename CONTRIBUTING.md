# Contributing

*Private draft. Contributions are currently from Hivemind Labs only.*

## Proposing a rule change

Every rule in the specification follows the same template. A proposal fills it in:

| Field | What to write |
|---|---|
| **ID** | The rule's number (for a new rule, the next free number in its section) |
| **Statement** | One testable sentence using MUST, SHOULD or MAY |
| **Status** | Tested, Default or Open |
| **Rationale** | Why the rule exists, in plain words (not normative) |
| **Evidence** | Link to the research report and result that support it, or "none yet" |
| **Test** | The conformance test that checks it, or "to add" |

A rule can only be marked *Tested* with a link to a pre-registered result. See [GOVERNANCE.md](GOVERNANCE.md) for how
changes are decided and versioned.

## Running the tests

From the repository root:

```bash
pytest
```

The conformance suite is keyed to rule IDs; [conformance/compliance-matrix.md](conformance/compliance-matrix.md) shows
which rules are covered.

## Adding a research round

1. Write `PREREG-<round>.md` in `research/`: questions, metrics, pass thresholds, data and seeds.
2. **Commit and tag it before writing any code for the round:** `research/prereg-<round>`.
3. Log every decision the pre-registration didn't settle in `research/DECISIONS.md` before seeing the results it
   affects.
4. Write `REPORT-<round>.md` with every verdict, including failures, and label anything decided after seeing results
   as *exploratory*.
5. Never edit a pre-registration or report afterwards. Add a dated correction to the decisions log instead.

## Style

- **Plain language.** Write for a team lead, not a statistician, except in the specification's formulas.
- **No abbreviations** in prose, names, fields or code. Write `customer_service`, not `cs`; `error_bar`, not `eps`.
  Standard acronyms (AI, API, ID, UTC) and the level labels (C1–C4, L1–L3) are fine.
- **One testable sentence per rule.**
- **Numbers come with their source:** link the report they came from.
