# Changelog

Changes to the Earned Autonomy specification and its reference engine. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Specification versions are `MAJOR.MINOR`
(see [`spec/README.md`](spec/README.md#versioning)); the engine package follows the specification's version.
Research results behind each change are in [`research/`](research/README.md).

## [0.6] - 2026-10-19 · Public review draft (private)

### Changed
- **The specification is restructured into [`spec/`](spec/README.md):**
  - normative rules in [`spec/requirements/`](spec/requirements/), each with an ID (`EA-<area>.<n>`), a one-sentence statement using RFC 2119 key words, an evidence status (Tested, Default or Open), a lifecycle label, a rationale, an evidence link and its tests;
  - separate pages for terminology, levels (with a fixed per-level template), threats, the reference API and worked examples.
- **Decision history** moved out of the normative text into this changelog.
- **JSON Schemas** in [`spec/schema/`](spec/schema/) are now the source of truth for the data model. Engine objects are tested against them (EA-6.14).
- **The conformance suite** moved to [`conformance/`](conformance/). Every test declares the rules it covers, and `scripts/build_requirements.py` generates [`spec/requirements.json`](spec/requirements.json) and the [compliance matrix](conformance/compliance-matrix.md).
- **The worked refund example** uses its C3 error bar (2%) throughout. The previous example used 3%, which its consequence level doesn't allow.
- **Engine 0.6.0:** docstrings cite rule IDs; `ProposedAction.to_dict()` added for interchange.
- **The Trust Gym research history** is merged into [`research/`](research/README.md) with its pre-registration tags (`research/prereg*`).

### Added
- Conformance tests for evidence weighting, no evidence fading, required reason codes, execution-time re-decisions, task-type names having no effect, version changes across organisations and rollback, test passes not counting as evidence, and second checks (EA-1.5, EA-2.10, EA-3.1, EA-3.2, EA-3.12, EA-4.1, EA-4.9, EA-4.12, EA-4.13, EA-5.2, EA-5.13).

## [0.5] - 2026-10-19

### Added
- **Timestamps:** one exact UTC format (`YYYY-MM-DDTHH:MM:SS.sssZ`). Older ISO 8601 forms are normalised on read, timestamps with no time zone are rejected, and the record is ordered by sequence number, never by timestamp (EA-6.9, EA-6.10).
- **Task types are catalogue entries:** name, description, examples, tools and consequence level (EA-1.1). The naming shape is a convention with no effect on the maths (EA-1.5), split only on consequence or error rate (EA-1.4), and parameters stay out of names (EA-1.6).
- **Rare task types** documented as a known limitation: they stay supervised by design (EA-3.17).
- **Seeded hidden tests per version** added as an option (EA-4.10).

### Changed
- **Abbreviations replaced with full words** throughout the specification, engine and tests. For example: `cs.*` → `customer_service.*`, `eps` → `error_bar`, `n` / `err` → `judged_count` / `serious_error_count`.

## [0.4] - 2026-10-18

### Added
- **Tool floors:** every write tool carries a floor consequence, and an action whose tool floor is above its tag's level is held (EA-1.13, EA-1.14). Shared write tools trigger a warning (EA-1.15). From Trust Gym v4.
- **Optional strict promotion** with an anytime-valid confidence sequence (EA-3.14). From Trust Gym v4.

### Changed
- **Spot-check sampling** must be random and hidden from the agent, never on a fixed cadence (EA-2.8, EA-2.9). Now tested.

## [0.3] - 2026-10-18

### Changed
- **Spot-checks are drawn after execution;** there is no "act and spot-check" decision mode (EA-2.7, EA-2.8).
- **Thirteen clarifications** from building the reference engine, covering:
  - the agent's view of its own record (EA-5.14);
  - re-evaluation when an error bar is lowered (EA-6.5);
  - missing checks results (EA-2.4);
  - unknown types vs low confidence (EA-1.9, EA-1.10);
  - unannounced versions (EA-4.8);
  - versions applying per agent (EA-4.9);
  - incident maths (EA-3.7);
  - reviewer step-down (EA-5.12);
  - second checks (EA-5.13);
  - L0 Observe (levels);
  - error-bar overrides (EA-3.9);
  - actors on governance operations (EA-6.4).

### Added
- **The reference trust engine** (`engine/`) with a conformance suite and Trust Gym parity.

## [0.2] - 2026-10-16

### Added
- **The first build specification**, covering:
  - consequence levels C1 to C4 setting each task type's error bar (EA-3.8);
  - task success as an alert, not a gate (EA-3.11);
  - no evidence fading (EA-3.12);
  - a 60-day re-entry rule (EA-3.13);
  - carry-over at a hidden-test pass rate of at least 0.8, without the earlier "no worse than the previous version" clause (EA-4.6);
  - reviewers earning trust like agents (EA-5.10);
  - permanent retention with references and labels only (EA-6.12, EA-6.13);
  - the AI owner as a business role (EA-1.7, EA-6.1);
  - knowledge edits as new versions (EA-4.1).
- **Methodology:** the principles one-pager and the practitioner guide.
