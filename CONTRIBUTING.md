# Contributing

*Version 0.7, invite-only review draft. Contributions are currently from Hivemind Labs and invited reviewers and collaborators.*

> [!IMPORTANT]
> **Help wanted: mapping EA to the standards.** [CROSSWALKS.md](CROSSWALKS.md) has first-cut mappings that need expert
> eyes:
>
> - **ISO/IEC 42001** — mapped without the purchased text; every row is unverified.
> - **ISO/IEC TR 24028** (trustworthiness in AI) — not mapped yet. It leaves *levels* of trustworthiness out of scope,
>   which is the part EA tries to supply.
> - **AI6 (Guidance for AI Adoption)** and the **NAIC buyer questions** — first cut, not reviewed.
> - **Gradient Institute's Agentic AI Governance Code of Practice** — not mapped; we couldn't find a public copy.
>
> If you work with any of these, a correction, a missing clause or "this row is wrong" is exactly what we need. Open an
> issue, or email hello@hivemind.au.

## Proposing a rule change

Every rule in the specification follows the same template. A proposal fills it in:

| Field | What to write |
|---|---|
| **ID** | `EA-<stage>.<n>`: the lifecycle stage (01 Measure, 02 Decide, 03 Oversee, 04 Learn, 05 Retire, 06 Govern, 07 Agent interface, 08 Multi-agent) and the next free number in it |
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

## Where a change belongs

- **A rule about measuring, deciding, overseeing, learning, retiring or governing** goes in the specification, under its
  lifecycle stage.
- **Advice on choosing what to automate** goes in the [assessment guide](docs/assessment-guide.md).
- **Advice on building agents** goes in the [implementation guide](docs/implementation-guide.md). It is outside the
  standard: the framework must work for any agent, however it's built.
- **Platform-neutral wording only.** Don't name or describe a specific agent platform in the specification or guides.

## Adding a research round

1. Decide whether it is a **trust** round (tests the framework) or an **implementation** round (tests a way of building
   agents), and say so in the pre-registration.
2. Write `PREREG-<round>.md` in `research/`: questions, metrics, pass thresholds, data and seeds.
3. **Commit and tag it before writing any code for the round:** `research/prereg-<round>`.
4. Log every decision the pre-registration didn't settle in `research/DECISIONS.md` before seeing the results it
   affects.
5. Write `REPORT-<round>.md` with every verdict, including failures, and label anything decided after seeing results
   as *exploratory*.
6. Never edit a pre-registration or report afterwards. Add a dated correction to the decisions log instead.

## Style

- **Plain language.** Write for a team lead, not a statistician, except in the specification's formulas.
- **No abbreviations** in prose, names, fields or code. Write `customer_service`, not `cs`; `error_bar`, not `eps`.
  Standard acronyms (AI, API, ID, UTC) and the level labels (C1–C4, L1–L3) are fine.
- **One testable sentence per rule.**
- **Numbers come with their source:** link the report they came from.
