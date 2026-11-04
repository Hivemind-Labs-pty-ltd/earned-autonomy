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
   Implementation rounds update the implementation guide instead of the specification.

Exploratory findings can suggest a change, but a rule only becomes *Tested* after a pre-registered confirmation.

## Conflicts of interest

Hivemind Labs maintains this specification **and** has a commercial interest in it:

- We build and sell an agent platform (10xAgent) that implements these rules, and one research round ran on it
  ([`research/REPORT-10x.md`](research/REPORT-10x.md)).
- We intend to offer training and certification against the specification.

What we do about it:

- The methodology is open: CC BY 4.0 for the documents and Apache-2.0 for the reference engine. Anyone may implement
  it, and no rule requires our products.
- Rule status is set by pre-registered evidence, with failures published (above), not by what suits our platform.
- Before 1.0 we want independent reviewers and replication, and we will consider moving stewardship of the
  specification to a neutral body once others depend on it.

Reviewers who see a rule that favours our platform over other implementations: please tell us. We'll treat it as a
defect.

## Scope and versioning

What the standard covers, what's binding, and how versions work are set out once, in the
[specification](spec/README.md#versioning). The reference engine follows the specification's version.
