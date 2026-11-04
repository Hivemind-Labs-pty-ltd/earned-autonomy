# Earned Autonomy specification

**Version 0.7, invite-only review draft.**

These are the rules an agent platform follows to give an agent autonomy from evidence, one task type at a time. New
to the ideas? Start with the [primer](../docs/primer.md). The reference implementation is in [`engine/`](../engine/),
and [`conformance/`](../conformance/) checks a build against these rules.

## What it covers

The specification covers **trust only**: how it is measured, what it allows, how it is overseen and how it is
recorded. How an agent is built is up to its builders.

| Stage | The question | Rules |
|---|---|---|
| Measure | How much can the agent be trusted with this task type? | [1. Measure](requirements/01-measure.md) · [explainer](measure.md) |
| Decide | Hold or act, and how much autonomy? | [2. Decide](requirements/02-decide.md) · [autonomy settings](autonomy.md) |
| Oversee | Who checks the work, and who checks them? | [3. Oversee](requirements/03-oversee.md) |
| Learn | What does a change to the agent do to its trust? | [4. Learn](requirements/04-learn.md) |
| Retire | How are task types narrowed, retired and brought back? | [5. Retire](requirements/05-retire.md) |
| Govern | Who is accountable, and what is recorded? | [6. Govern](requirements/06-govern.md) |
| Agent interface | What must the agent itself provide? | [7. Agent interface](requirements/07-agent-interface.md) |
| Multiple agents | What changes when agents delegate to each other? (preview) | [8. Multiple agents](requirements/08-multi-agent.md) |

Also normative: [terminology](terminology.md), [autonomy settings](autonomy.md) and the [schema](schema/).
Everything else is explanation: [threats](threats.md), [worked examples](examples.md), the [API](api.md), the
[guides](../docs/) and the [research](../research/). If an explanation and a rule disagree, the rule wins.

## Conformance tiers

Every rule is tagged **Core**, **Standard** or **Advanced**, and each tier includes the one before it. An
implementation states its tier, for example "compliant with v0.7 Core".

**Core** is eight requirements a team can run from a printed table, with no statistics code:

| # | Requirement | Rules |
|---|---|---|
| 1 | **Trust per task type.** Every action is tagged with a task type, and trust is kept per organisation, agent and task type. | EA-1.1, EA-7.1, EA-7.5, EA-2.4 |
| 2 | **Start supervised; move up by the lookup table.** New task types start with every action held. Critical work never moves up. | EA-2.13, EA-2.14, EA-2.15, EA-2.9, EA-2.8, EA-2.1, EA-1.2 to EA-1.5 |
| 3 | **Every action carries a checks result, and a failed check is held,** at every level. | EA-7.10, EA-2.6, EA-2.7 |
| 4 | **Tools are declared per task type.** | EA-7.7 |
| 5 | **Random, hidden spot-checks** of the work the agent does alone. | EA-3.1, EA-3.2, EA-3.3, EA-2.23 |
| 6 | **Step down by the table or on any incident,** one level at a time. Anyone can report an incident. | EA-2.16, EA-2.17, EA-2.18, EA-3.7 |
| 7 | **A named owner and a permanent record** of every decision and judgement. A change to the agent is a new version. | EA-6.1, EA-6.2, EA-6.7, EA-2.12, EA-1.13, EA-4.1, EA-4.7, EA-7.11, EA-3.4, EA-3.5, EA-3.9, EA-2.2 |
| 8 | **Canaries** in review queues, so missed errors show up. | EA-3.11 |

**Standard** adds the trust score and profile, trust carried across versions with hidden tests, tool floors, reviewer
trust, a tamper-evident record and review windows.

**Advanced** adds options that need more statistics or are less proven: the bounds computed directly (EA-2.19), the
dial (EA-2.22), re-entry after a long gap (EA-5.1), multiple agents (EA-8.x) and measured weights for shadow, replay
and test evidence (EA-1.17 to EA-1.20).

## Reading a rule

Each rule has an ID (`EA-<stage>.<number>`, cited with the version, for example `v0.7-EA-2.14`) and a one-sentence
**Statement**. Only the Statement, and a Condition where there is one, is binding. The other fields explain it:
Rationale, Evidence, Implementation, Test and Notes.

Each rule also carries:

- **Status:** **Tested** (backed by a pre-registered study or a structural test), **Default** (our reasoned choice,
  not yet tested) or **Open** (a question or a known gap). *Tested* means tested in simulation or on generated tasks,
  never yet in production; see [Limitations](#limitations).
- **Tier:** Core, Standard or Advanced.
- **Stability:** every rule in v0.7 is *Development*, meaning it may still change.

**MUST**, **SHOULD**, **MAY** and the other key words mean what [BCP 14](https://www.rfc-editor.org/info/bcp14) says,
and only when they are in capitals. An implementation is **compliant at a tier** when it meets every MUST and MUST NOT
in that tier and the tiers below. It reports any SHOULD it doesn't follow, and why.

The [compliance matrix](../conformance/compliance-matrix.md) lists every rule with its tier, status, implementation
and tests, and [`requirements.json`](requirements.json) is the same list for machines. Both are generated by
`scripts/build_requirements.py`, so don't edit them by hand.

## Versioning

- Versions are `MAJOR.MINOR`. Until 1.0, any release may change any rule.
- From 1.0, adding a MUST to a tier or changing what a rule means is a **MAJOR** change. Clarifications and new SHOULD
  or MAY rules are **MINOR**.
- Once a version is stable, what an autonomy level means never changes: "Trusted under v1.0" means the same thing for
  as long as v1.0 exists.
- Rule IDs are never reused within a major version. v0.7 renumbered the rules by lifecycle stage, the last renumbering before 1.0; the
  [changelog](../CHANGELOG.md) maps old IDs to new ones.

## Limitations

- **No production evidence.** Every study ran on simulated organisations, generated tasks or a public benchmark
  (τ²-bench). Earned autonomy only means something once it's tested where the agent actually works. A pilot is
  next: see [what we're researching next](../research/README.md#what-were-researching-next).
- **One team.** The same team wrote the hypotheses, the code, the grader and the reports. Nothing has been
  independently replicated.
- **AI-assisted.** Studies and much of this text were written with AI coding agents. An AI model grades outcomes in
  the generated-task studies, and some reviewer behaviour is modelled, not observed (for example EA-3.11).
- **One study ran on our own platform** ([`REPORT-10x`](../research/REPORT-10x.md)). See the conflict-of-interest note
  in [`GOVERNANCE.md`](../GOVERNANCE.md).
- **Known gaps** are Open rules, not answers: a pause that reaches sub-agents (EA-3.19), incident response (EA-3.20),
  silent model changes (EA-4.14) and accountability between provider and deployer (EA-6.16).
- **The thresholds are defaults.** Consequence levels, error bars and lookup tables were checked in simulation, not
  against real losses.
