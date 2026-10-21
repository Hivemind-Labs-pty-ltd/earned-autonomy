# Earned Autonomy specification

The specification lives in [`spec/`](spec/README.md). Start with [`spec/README.md`](spec/README.md).

From v0.7 the rules are grouped by lifecycle stage (Measure, Decide, Oversee, Learn, Retire, Govern, plus the agent
interface and multiple agents) and renumbered `EA-<stage>.<n>`. The v0.6 → v0.7 ID mapping is in
[`CHANGELOG.md`](CHANGELOG.md).

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

`research/SPEC.md` is the historical v0.2 copy kept with the Trust Gym's history; it is not current.
