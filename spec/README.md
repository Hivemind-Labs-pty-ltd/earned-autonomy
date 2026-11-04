# Earned Autonomy specification

**Version 0.7, public review draft.** The binding rules any agent platform must follow to give agents autonomy from
evidence. New to the ideas? Read the [primer](../docs/primer.md) first. `engine/` is the reference implementation, and `conformance/` checks a build against
these rules.

## The lifecycle, and what this specification covers

| Stage | Question | In this specification |
|---|---|---|
| Assess | Which work suits an agent, and at what consequence? | Informative only: see [`../docs/`](../docs/). |
| Build | How is the agent made, validated and improved? | **Not covered.** Only what the agent must provide: [7. Agent interface](requirements/07-agent-interface.md). |
| Measure | How much can it be trusted with each task type? | [1. Measure](requirements/01-measure.md), [explainer](measure.md) |
| Decide | Hold or act; how much autonomy; what to do about the agent | [2. Decide](requirements/02-decide.md), [autonomy settings](autonomy.md) |
| Oversee | Who watches, how, and who watches them | [3. Oversee](requirements/03-oversee.md) |
| Learn | What a change to the agent does to its trust | [4. Learn](requirements/04-learn.md) |
| Retire | Narrowing, retiring and bringing back task types | [5. Retire](requirements/05-retire.md) |
| Govern | Who is accountable; the permanent record | [6. Govern](requirements/06-govern.md) |

**The specification covers trust only:** how trust is measured, what it allows, how it is overseen and recorded.
How an agent is built and improved is up to its builders. [Multiple agents](requirements/08-multi-agent.md) is a
preview.

## Conformance tiers

Every rule is tagged **Core**, **Standard** or **Advanced**. Each tier includes the one before it.

### Core: eight requirements

A team can run Core from a printed table, with no statistics code. Core is eight requirements; the rules that make
each one testable are listed beside it.

| # | Requirement | Rules |
|---|---|---|
| 1 | **Trust per task type.** Every action is tagged with a task type from a catalogue, and trust is kept per (organisation, agent, task type). | EA-1.1, EA-7.1, EA-7.5, EA-2.4 |
| 2 | **Start supervised; promote by the lookup table.** New task types start with every action held; they move up when the judged evidence passes the table. Critical work never moves up. | EA-2.13, EA-2.14, EA-2.15, EA-2.9, EA-2.8, EA-2.1, EA-1.2 to EA-1.5 |
| 3 | **A checks result is required, and a failed check is held,** at every level. | EA-7.10, EA-2.6, EA-2.7 |
| 4 | **Tools are declared per task type.** | EA-7.7 |
| 5 | **Random, hidden spot-checks** of the work the agent does alone. | EA-3.1, EA-3.2, EA-3.3, EA-2.23 |
| 6 | **Step down by the table or on any incident,** one level at a time; anyone can report an incident. | EA-2.16, EA-2.17, EA-2.18, EA-3.7 |
| 7 | **A named owner and a permanent record** of every decision and judgement, from which trust can be read at any time; a change to the agent is a new version. | EA-6.1, EA-6.2, EA-6.7, EA-2.12, EA-1.13, EA-4.1, EA-4.7, EA-7.11, EA-3.4, EA-3.5, EA-3.9, EA-2.2 |
| 8 | **Canaries** in review queues, so missed errors show up. | EA-3.11 |

### Standard

Core, plus: the trust score and trust profile; carry-over of trust across versions with hidden tests; tool floors;
reviewer trust; a tamper-evident record; review windows; and the remaining operating rules.

### Advanced

Standard, plus options that need more statistics or are less proven: the Wilson and strict bounds computed directly
(EA-2.19), the dial (EA-2.22), re-entry after a long gap (EA-5.1), multiple agents (EA-8.x), and measured evidence
weights for shadow, replay and test evidence (EA-1.17 to EA-1.20).

An implementation states its tier: "compliant with v0.7 Core". The
[compliance matrix](../conformance/compliance-matrix.md) counts rules by tier.

## What is normative

| Normative (this folder) | Informative (everything else) |
|---|---|
| [`requirements/`](requirements/): the numbered rules | [`../README.md`](../README.md) and [`../docs/`](../docs/): the principles, primer, guide and assessment |
| [`autonomy.md`](autonomy.md): autonomy settings and consequence levels | [`measure.md`](measure.md): how the trust score works (its normative parts are marked) |
| [`terminology.md`](terminology.md): the defined terms | [`examples.md`](examples.md): the worked example and the maths in plain language |
| [`schema/`](schema/): the data model (source of truth) | [`api.md`](api.md): the reference engine's API |
| | [`threats.md`](threats.md): threats and how the rules answer them |
| | [`../research/`](../research/): the pre-registered evidence |

Inside a rule, only the **Statement** (and **Condition**) is normative. Rationale, Evidence and Notes explain it. If a
guide and a rule ever disagree, the rule wins.

## Notation

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**,
**RECOMMENDED**, **NOT RECOMMENDED**, **MAY** and **OPTIONAL** in this specification are to be interpreted as
described in [BCP 14](https://www.rfc-editor.org/info/bcp14) ([RFC 2119](https://www.rfc-editor.org/rfc/rfc2119),
[RFC 8174](https://www.rfc-editor.org/rfc/rfc8174)) when, and only when, they appear in all capitals, as shown here.

## Compliance

An implementation is **compliant at a tier** when it meets **every MUST and MUST NOT** rule of that tier and the
tiers below it. SHOULD rules are not required, but a compliant implementation reports which ones it doesn't follow and
why. MAY rules are options.

The [conformance suite](../conformance/) tests the rules it can. The
[compliance matrix](../conformance/compliance-matrix.md) shows, for every rule, its tier, status, where the reference
engine implements it and which tests check it. [`requirements.json`](requirements.json) is the same list,
machine-readable. Both are generated by `scripts/build_requirements.py`; don't edit them by hand.

## Rule format

Every rule lives in one file under [`requirements/`](requirements/) and has the same fields:

| Field | Meaning |
|---|---|
| **ID** | `EA-<stage>.<number>`: 1 Measure, 2 Decide, 3 Oversee, 4 Learn, 5 Retire, 6 Govern, 7 Agent interface, 8 Multiple agents. Stable once published. Cite with the version: `v0.7-EA-2.14`. v0.6 IDs map to v0.7 in [`../CHANGELOG.md`](../CHANGELOG.md). |
| **Statement** | One testable sentence using the key words above. Normative. |
| **Condition** | Only for conditional rules: the situation the rule applies in. |
| **Status** | How well the rule is evidenced (below). |
| **Tier** | Core, Standard or Advanced (above). |
| **Stability** | How stable the rule is (below). |
| **Rationale** | Why the rule exists. Informative. |
| **Evidence** | The research result behind it, with the effect size and the pre-registration tag. Informative. |
| **Implementation** | Where the reference engine implements it. Informative. |
| **Test** | The conformance or engine test IDs that check it, or "none yet". |
| **Notes** | Anything else. Informative. |

### Status: how well a rule is evidenced

| Status | Meaning |
|---|---|
| **Tested** | Backed by a pre-registered Trust Gym result **in simulation or on generated tasks**, or checked by a test of a structural property; the Evidence field says which. *Tested* does **not** mean tested in production: no rule has production evidence yet (see [Limitations](#limitations)). |
| **Default** | Our recommended choice. Reasoned, but not yet backed by a pre-registered result. |
| **Open** | A research question, a known limitation or an optional practice. Implementations MAY differ. |

### Stability

| Stability | Meaning |
|---|---|
| **Development** | May change in any release. Every rule in v0.7 is Development. |
| **Stable** | Changes only through the versioning policy below. |
| **Deprecated** | Still valid, scheduled for removal; the rule says what replaces it. |

## Versioning

- The specification is versioned `MAJOR.MINOR`. Until 1.0, any release may change any rule.
- From 1.0:
  - Adding a MUST rule to a tier, or changing a rule's meaning, is a **MAJOR** change.
  - Clarifications, new SHOULD or MAY rules, and new informative material are **MINOR**.
- **An autonomy setting's meaning never changes once it is Stable.** A task type "Trusted under v1.0" means the same
  thing for as long as v1.0 exists.
- Rule IDs are never reused within a major version. A removed rule keeps its ID as Deprecated, then disappears in the
  next MAJOR version. (v0.7 renumbered every rule by lifecycle stage; this is the last renumbering before 1.0.)
- Every release is recorded in [`../CHANGELOG.md`](../CHANGELOG.md).

## Contents

- [Terminology](terminology.md)
- [Autonomy settings](autonomy.md): the Core ladder (Supervised, Trusted, Senior), the Advanced dial, and the
  consequence levels C1 to C4
- [Measure explainer](measure.md): the trust score, the trust profile and evidence sources
- Requirements:
  1. [Measure](requirements/01-measure.md)
  2. [Decide](requirements/02-decide.md)
  3. [Oversee](requirements/03-oversee.md)
  4. [Learn](requirements/04-learn.md)
  5. [Retire](requirements/05-retire.md)
  6. [Govern](requirements/06-govern.md)
  7. [Agent interface](requirements/07-agent-interface.md)
  8. [Multiple agents (preview)](requirements/08-multi-agent.md)
- [Threats](threats.md)
- [Schema](schema/)
- [Reference API](api.md)
- [Examples and the maths](examples.md)

## Evidence base

Every Tested rule links to a pre-registered report in [`../research/`](../research/) or to a structural test. All
evidence so far is synthetic; a real-world pilot is next.

## Limitations

Read the evidence with these in mind:

- **No production evidence.** Every study ran on simulated organisations, generated tasks or a public benchmark
  (τ²-bench). Earned autonomy is only meaningful once it is tested where the agent actually works. A sandbox or
  production pilot with a deploying organisation is the next step, and we're looking for partners.
- **One team.** The same team (Hivemind Labs) wrote the hypotheses, the code, the grader and the reports. Nothing has
  been independently replicated.
- **AI-assisted.** Studies and much of this text were written with AI coding agents. An AI model grades outcomes in
  the generated-task studies, and some reviewer behaviour is modelled, not observed (for example the canary result in
  EA-3.11).
- **One study ran on our own platform.** The 10x round ([`../research/REPORT-10x.md`](../research/REPORT-10x.md)) ran
  on Hivemind's commercial agent platform. See the conflict-of-interest note in [`../GOVERNANCE.md`](../GOVERNANCE.md).
- **Known gaps.** A pause that reaches sub-agents (EA-3.19), incident response (EA-3.20), silent model changes
  (EA-4.14) and provider–deployer accountability (EA-6.16) are Open rules, not answers.
- **Thresholds are defaults.** The consequence levels, error bars and lookup tables are reasoned choices, checked in
  simulation. They haven't been validated against real loss data.
