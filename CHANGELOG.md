# Changelog

Changes to the Earned Autonomy specification and its reference engine. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Specification versions are `MAJOR.MINOR`
(see [`spec/README.md`](spec/README.md#versioning)); the engine package follows the specification's version.
Research results behind each change are in [`research/`](research/README.md).

## [Unreleased]

### Added
- **Expert review pack.** [`REVIEWERS.md`](REVIEWERS.md): what EA is and isn't, the state of the evidence, five
  questions for reviewers, and a reading path.
- **[Limitations](spec/README.md#limitations)** in the specification, and a **conflict-of-interest** section in
  [`GOVERNANCE.md`](GOVERNANCE.md).
- **Open rules for known gaps:** EA-3.19 a pause reaches delegated work, EA-3.20 incident response, EA-4.14 upstream
  model changes are new versions, EA-6.16 provider and deployer. All Open, Standard, SHOULD.
- Threats: sub-agents outliving a pause; silent model changes.

### Changed
- **Status "Tested" is defined more strictly:** simulation, generated tasks or a structural test, never production.
- `research/README.md` explains why pre-registration, code and report commits are minutes apart, and that the check
  shows order, not independence.
- **Docs simplified for non-technical readers.** The README now holds the problem and the principles
  (`PRINCIPLES.md` folded in). Each idea lives in one place: concepts and results in the primer, day-to-day practice in
  the practitioner guide, rules and versioning in the specification. `docs/guide.md` is now
  [`docs/practitioner-guide.md`](docs/practitioner-guide.md).
- Added licences (`LICENSE` Apache-2.0 for code, `LICENSE-docs` CC BY 4.0 for docs), a code of conduct, a security
  policy and automated tests on every pull request.

### Removed
- **The top-level `SPEC.md` pointer.** Older research reports cite its sections; they map to the current
  specification as follows:

| Was (SPEC.md v0.5) | Now |
|---|---|
| §1–3 Core idea, definitions, architecture | [`spec/README.md`](spec/README.md), [`spec/terminology.md`](spec/terminology.md) |
| §4 Task types | [`spec/requirements/07-agent-interface.md`](spec/requirements/07-agent-interface.md), [`spec/requirements/01-measure.md`](spec/requirements/01-measure.md) |
| §5 Data model | [`spec/schema/`](spec/schema/), rules EA-6.7 to EA-6.15 |
| §6 The decision | [`spec/requirements/02-decide.md`](spec/requirements/02-decide.md) |
| §7 Trust calculation | [`spec/requirements/01-measure.md`](spec/requirements/01-measure.md), [`spec/requirements/02-decide.md`](spec/requirements/02-decide.md), [`spec/autonomy.md`](spec/autonomy.md), [`spec/measure.md`](spec/measure.md) |
| §8 Versions and learning | [`spec/requirements/04-learn.md`](spec/requirements/04-learn.md) |
| §9 Oversight | [`spec/requirements/03-oversee.md`](spec/requirements/03-oversee.md) |
| §10 Governance | [`spec/requirements/06-govern.md`](spec/requirements/06-govern.md) |
| §11 Multi-agent | [`spec/requirements/08-multi-agent.md`](spec/requirements/08-multi-agent.md) |
| §12 API | [`spec/api.md`](spec/api.md) |
| §13 Conformance | [`conformance/`](conformance/), [`conformance/compliance-matrix.md`](conformance/compliance-matrix.md) |
| §14 Worked example | [`spec/examples.md`](spec/examples.md) |
| §15–16 Decisions and clarifications | Folded into the rules; history in [`CHANGELOG.md`](CHANGELOG.md) |

## [0.7] - 2026-10-21 · Public review draft (private)

### Changed
- **Rules are grouped by lifecycle stage and renumbered** `EA-<stage>.<n>`: 1 Measure, 2 Decide, 3 Oversee, 4 Learn,
  5 Retire, 6 Govern, 7 Agent interface, 8 Multiple agents (preview). Every v0.6 rule keeps its statement, status,
  evidence and tests; only its ID (and, for some, its stage) changed. The full mapping is below.
- **The specification covers trust only.** How agents are built and improved (Assess, Build) is informative and
  lives in [`docs/`](docs/). The spec states only what the agent must provide (7. Agent interface).
- **Conformance tiers:** every rule is tagged Core, Standard or Advanced. Core is eight requirements a team can run
  from a printed lookup table ([`spec/README.md`](spec/README.md#conformance-tiers)).
- **Rule fields:** `Lifecycle` is renamed `Stability` (it no longer clashes with the lifecycle stages), and a `Tier`
  field is added. `scripts/build_requirements.py` validates both and counts rules by tier.
- **`spec/levels.md` is now [`spec/autonomy.md`](spec/autonomy.md):** the ladder as Core's autonomy setting, with its
  lookup tables, the Advanced dial and the decision menu.
- **Evidence weights** default to human 1.0, shadow 1.0, replay 1.0, test 0.75, from the calibration round
  ([`research/REPORT-calibration.md`](research/REPORT-calibration.md)). Status Open.
- **Engine 0.7.0.** `decide` and the record behave as in 0.6 unless the new options are used.

### Added
- **Measure:** the trust score, the posterior probability that the true serious-error rate is under the error bar
  (flat Beta(1, 1) prior, weighted evidence). At a threshold of 0.975 it reproduces the 95% Wilson promotion rule:
  the score is 0.975–0.979 at every published table cell, and reaches 0.975 at most 1 / 2 / 7 judged actions earlier
  at C1 / C2 / C3. See [`spec/measure.md`](spec/measure.md).
- **Trust profile and agent trust summary** (`TrustEngine.trust_report`), evidence from other sources
  (`TrustEngine.record_evidence`; never moves the ladder), and the Core lookup tables as a policy option
  (`Policy(promotion_rule="core_table")`, same decisions as the bound up to 10 serious errors).
- **Retire:** `TrustEngine.retire` and `TrustEngine.reactivate`, with governance roles.
- **The dial** (Advanced, Tested as safe in [`research/REPORT-dial.md`](research/REPORT-dial.md)): reported in each
  profile; decisions in the reference engine still follow the ladder.
- New rules:
  - EA-1.13 Trust is measurable at any time from the record (Core)
  - EA-1.14 The trust score (Standard)
  - EA-1.15 The trust profile (Standard)
  - EA-1.16 The agent's trust summary (Standard)
  - EA-1.17 Live human judgement is the reference evidence (Advanced)
  - EA-1.18 Other evidence sources are weighted (Advanced)
  - EA-1.19 Evidence weights are calibrated against human judgement (Advanced)
  - EA-1.20 Keep a share of human evidence (Advanced)
  - EA-1.21 Other evidence never changes the autonomy setting by itself (Standard)
  - EA-2.15 The Core lookup tables (Core)
  - EA-2.21 The decision menu (Standard)
  - EA-2.22 The dial (optional) (Advanced)
  - EA-3.17 Review windows (Standard)
  - EA-3.18 No action on timeout (Standard)
  - EA-5.4 Retiring a task type (Standard)
  - EA-5.5 Narrowing scope is a policy change (Standard)
  - EA-5.6 Bringing a task type back (Standard)
  - EA-7.10 Every action comes with a checks result (Core)
  - EA-7.11 Every action carries a version (Core)

### Rule ID mapping, v0.6 → v0.7

| v0.6 | v0.7 | Rule | Tier |
|---|---|---|---|
| EA-1.1 | EA-7.1 | Task types are catalogue entries | Core |
| EA-1.2 | EA-1.1 | Trust is kept per trust key | Core |
| EA-1.3 | EA-2.13 | New task types start supervised with no evidence | Core |
| EA-1.4 | EA-7.2 | Split task types only when consequence or error rate differs | Standard |
| EA-1.5 | EA-7.3 | Task-type names are keys only | Standard |
| EA-1.6 | EA-7.4 | No parameters in task-type names | Standard |
| EA-1.7 | EA-6.2 | The AI owner maintains the task catalogue | Core |
| EA-1.8 | EA-7.5 | Every proposed action is tagged | Core |
| EA-1.9 | EA-2.3 | Low-confidence tags are held | Standard |
| EA-1.10 | EA-2.4 | Unknown task types are held | Core |
| EA-1.11 | EA-2.10 | Bundled actions take the most restrictive decision | Standard |
| EA-1.12 | EA-7.7 | Tool scope per task type | Core |
| EA-1.13 | EA-7.8 | Every write tool has a floor consequence | Standard |
| EA-1.14 | EA-2.5 | Floor mismatches are held | Standard |
| EA-1.15 | EA-7.9 | Don't share write tools across consequence levels | Standard |
| EA-1.16 | EA-7.6 | Tag from descriptions and examples | Advanced |
| EA-2.1 | EA-2.1 | Decision order | Core |
| EA-2.2 | EA-2.2 | Paused work is held | Core |
| EA-2.3 | EA-2.6 | Checks run at every level | Core |
| EA-2.4 | EA-2.7 | A missing checks result is a hold | Core |
| EA-2.5 | EA-2.8 | Critical work is always held | Core |
| EA-2.6 | EA-2.9 | The level decides the rest | Core |
| EA-2.7 | EA-2.23 | A decision never reveals sampling | Core |
| EA-2.8 | EA-3.1 | Spot-checks are drawn after execution | Core |
| EA-2.9 | EA-3.2 | No fixed sampling schedule | Core |
| EA-2.10 | EA-2.11 | Re-decide at execution time | Standard |
| EA-2.11 | EA-2.12 | Every decision is recorded and explainable | Core |
| EA-3.1 | EA-1.2 | Only judged actions are evidence | Core |
| EA-3.2 | EA-1.3 | Pre-review and spot-check outcomes weigh the same | Core |
| EA-3.3 | EA-1.4 | What counts as a serious error | Core |
| EA-3.4 | EA-2.14 | Promotion | Core |
| EA-3.5 | EA-2.17 | Step-down on recent errors | Core |
| EA-3.6 | EA-2.16 | Step-down before promotion, one level at a time | Core |
| EA-3.7 | EA-2.18 | Incidents step down immediately | Core |
| EA-3.8 | EA-1.5 | Consequence levels set the error bar | Core |
| EA-3.9 | EA-1.6 | Error bars can only be tightened | Standard |
| EA-3.10 | EA-1.7 | Consequence sets the bar, not the expectation | Standard |
| EA-3.11 | EA-1.11 | Task success is an alert, not a gate | Standard |
| EA-3.12 | EA-1.8 | Evidence doesn't fade with time | Standard |
| EA-3.13 | EA-5.1 | Re-entry after a long gap | Advanced |
| EA-3.14 | EA-2.19 | Strict promotion (optional) | Advanced |
| EA-3.15 | EA-1.9 | Serialised updates per trust key | Standard |
| EA-3.16 | EA-1.10 | Late incidents apply to the original version | Standard |
| EA-3.17 | EA-5.2 | Rare task types (known limitation) | Advanced |
| EA-4.1 | EA-4.1 | Any change is a new version | Core |
| EA-4.2 | EA-4.2 | Corrections become draft rules and tests | Standard |
| EA-4.3 | EA-4.3 | Training and hidden split | Standard |
| EA-4.4 | EA-4.4 | Hidden tests stay hidden | Standard |
| EA-4.5 | EA-4.5 | New versions are tested before going live | Standard |
| EA-4.6 | EA-4.6 | Carry-over | Standard |
| EA-4.7 | EA-4.7 | Version discount | Core |
| EA-4.8 | EA-4.8 | Unannounced versions are untested | Standard |
| EA-4.9 | EA-4.9 | Version results apply per agent | Standard |
| EA-4.10 | EA-4.10 | Seeded hidden tests per version (optional) | Advanced |
| EA-4.11 | EA-4.11 | Batch changes into releases | Standard |
| EA-4.12 | EA-1.12 | Test passes are not promotion evidence | Standard |
| EA-4.13 | EA-4.12 | Rollback is a new version | Standard |
| EA-4.14 | EA-4.13 | The agent can't change what it's judged by | Standard |
| EA-5.1 | EA-3.4 | Held actions are reviewable | Core |
| EA-5.2 | EA-3.5 | Every judgement has a label, and every correction a reason | Core |
| EA-5.3 | EA-3.6 | Reason codes | Standard |
| EA-5.4 | EA-3.7 | Anyone can report an incident | Core |
| EA-5.5 | EA-3.8 | Anyone affected can challenge | Standard |
| EA-5.6 | EA-3.9 | Pause | Core |
| EA-5.7 | EA-3.10 | Alerts before the bar is crossed | Standard |
| EA-5.8 | EA-5.3 | Periodic agent review | Standard |
| EA-5.9 | EA-3.11 | Canaries in review queues | Core |
| EA-5.10 | EA-3.12 | Reviewers earn trust too | Standard |
| EA-5.11 | EA-3.13 | Second-check rates | Standard |
| EA-5.12 | EA-3.14 | Reviewers step down on misses | Standard |
| EA-5.13 | EA-3.15 | A second check measures the reviewer only | Standard |
| EA-5.14 | EA-3.3 | Agents can't see when they're watched | Core |
| EA-5.15 | EA-3.16 | Slowly degrading reviewers (known limitation) | Advanced |
| EA-6.1 | EA-6.1 | Roles and a named owner | Core |
| EA-6.2 | EA-6.3 | Agents can't govern themselves | Standard |
| EA-6.3 | EA-6.4 | Separation of duties | Standard |
| EA-6.4 | EA-6.5 | Every governance request is logged | Standard |
| EA-6.5 | EA-6.6 | Policy is versioned and takes effect immediately | Standard |
| EA-6.6 | EA-6.7 | The record is append-only | Core |
| EA-6.7 | EA-6.8 | The record is tamper-evident | Standard |
| EA-6.8 | EA-6.9 | State is rebuilt from the record | Standard |
| EA-6.9 | EA-6.10 | Sequence, not time, orders the record | Standard |
| EA-6.10 | EA-6.11 | One exact timestamp format | Standard |
| EA-6.11 | EA-6.12 | Epoch time stays at the edges | Standard |
| EA-6.12 | EA-6.13 | The record is kept permanently | Standard |
| EA-6.13 | EA-6.14 | References and labels, not customer content | Standard |
| EA-6.14 | EA-6.15 | Records follow the schema | Standard |
| EA-6.15 | EA-2.20 | Approval for Senior | Standard |
| EA-7.1 | EA-8.1 | Delegation never adds authority | Advanced |
| EA-7.2 | EA-8.2 | Delegated actions carry their provenance | Advanced |
| EA-7.3 | EA-8.3 | Peer reliability with exploration | Advanced |
| EA-7.4 | EA-8.4 | Keep consequential peer work supervised | Advanced |
| EA-7.5 | EA-8.5 | Reviewer agents earn trust as their own task type | Advanced |

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
