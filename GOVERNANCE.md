# Governance

*Private draft.*

## Maintainers

Earned Autonomy is maintained by **Hivemind Labs**. The maintainers decide what goes into the specification, the
reference engine and the methodology documents.

## How decisions are made

- **Specification changes** need a written proposal (see [CONTRIBUTING.md](CONTRIBUTING.md)) and maintainer approval.
- **A rule's status is decided by evidence.** A rule is *Tested* only when a pre-registered study supports it, *Default*
  when it's our recommendation without that evidence, and *Open* when it's an unanswered question.
- **Disagreements** are settled by evidence where possible: if a question can be tested, the answer is to pre-register
  a study rather than argue.

## How research changes the specification

1. Pre-register the question, metrics and pass thresholds, then commit and tag the pre-registration.
2. Run the study, logging every unplanned decision before seeing the results it affects.
3. Publish the report with every verdict, including failures.
4. Update the affected rules' status and evidence links, and record the change in the [CHANGELOG](CHANGELOG.md).

Exploratory findings can suggest a change, but a rule only becomes *Tested* after a pre-registered confirmation.

## Versioning

- The **specification** and the **reference engine** use semantic versioning (major.minor.patch).
- **Adding a requirement to an existing level, or tightening one, is a major change.** Organisations that met a level
  must not silently stop meeting it.
- **A level's meaning never changes once the specification is Stable.** A level can be retired and replaced, not
  redefined.
- **Clarifications** that don't change what a compliant build must do are patch changes.
- Until version 1.0 the specification is a public review draft, and breaking changes may happen in minor versions.
