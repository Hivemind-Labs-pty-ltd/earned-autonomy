# Note for reviewers

*Earned Autonomy v0.7 · confidential review draft · November 2026 · Hivemind Labs*

Thank you for reading this. Please don't share it beyond your own organisation without asking us first.

## What this is

Earned Autonomy (EA) answers one question: **when can an AI agent do a piece of work without a person checking it
first?**

The answer is **evidence, kept per type of work.** Every new type of task starts with every action held for a
person. It moves up only when the judged record passes a published bound for its consequence level. Checking never
stops: random, hidden spot-checks continue at every level. Any incident steps the task type back down at once. Every
decision and judgement goes into a permanent, tamper-evident record, so trust can be read and audited at any time.
The intern analogy is close: minimal scope first, more as trust is earned, and the supervisor's own judgement is
checked too.

EA is a **technical-layer** specification: testable rules for the platform that runs agents. It sits under
enterprise frameworks such as AI6 and ISO/IEC 42001, and is meant to produce the evidence those frameworks ask for.
[CROSSWALKS.md](CROSSWALKS.md) has first-cut mappings to AI6, ISO/IEC 42001 and the NAIC buyer questions, and lists
the gaps. We haven't been able to map the Gradient Institute's Agentic AI Governance Code of Practice. If it's
available to share, we'd value doing that with you.

## What it isn't

- **Not a way to build agents.** How an agent is built and improved is out of scope. EA only states what the agent
  must provide.
- **Not a data-protection standard.** What data an agent uses, where it is stored and whether it trains a model are
  for the provider to answer. EA's record holds references and labels, never customer content.
- **Not a finished methodology or specification.** v0.7 is a working draft: rules will change, some are open
  questions, and the evidence behind them is still being built. That's why we're asking for review now.

## The honest state of the evidence

- 116 rules: 39 Core, 61 Standard, 16 Advanced. Each is marked **Tested**, **Default** (our reasoned choice) or
  **Open** (a question or known gap). The reference engine passes its own conformance tests.
- **"Tested" means tested in simulation, on generated tasks, or by a structural test.** No rule has production
  evidence yet.
- Every study was pre-registered and every failure is published. But the same small team wrote the hypotheses, the
  code, the AI grader and the reports, with AI coding agents, often in one working session. Nothing has been
  independently replicated.
- Details: [Limitations](spec/README.md#limitations), [research/README.md](research/README.md),
  [conflicts of interest](GOVERNANCE.md#conflicts-of-interest). (We sell an agent platform and plan to offer
  certification. That's disclosed there, with what we do about it.)
- The research files are left exactly as committed, including internal platform names, so the pre-registration
  record stays intact.

## What we'd like from you

Any of these, in any form:

1. **Evidence.** What would a sandbox or production pilot have to show before you'd believe the lookup-table
   thresholds? Would you help design one, or run the tests on your own agents?
2. **The bars.** Are the consequence levels (C1 to C4) and error bars (10%, 5%, 2%) sensible? Who should set them:
   the deployer, the provider or a regulator?
3. **Oversight.** People take the path of least resistance. Do random hidden spot-checks, canaries and measuring
   the reviewers add up to *meaningful* human oversight? Which failure modes are we missing?
4. **Two organisations.** When provider and deployer are different parties, where should accountability, access to
   the record, and the pause sit? (EA-6.16 is our open attempt.)
5. **Fit.** Is EA useful as technical-layer evidence for AI6, ISO/IEC 42001 or the Gradient code? Which mapping
   matters most to you, and where is ours wrong?

A paragraph or a 20-minute call is as useful as a marked-up document.

## How to read it (about an hour)

1. [README.md](README.md): the problem and the ten principles (10 minutes)
2. [spec/README.md](spec/README.md): tiers, the eight Core requirements, statuses and limitations
3. [spec/threats.md](spec/threats.md): what could go wrong and how the rules answer it
4. Any rule file in [spec/requirements/](spec/requirements/) that interests you. Open rules are where we most need
   help: EA-3.19 to 3.20, EA-4.14, EA-6.16 and EA-5.2.
5. If you want to check the evidence: [research/README.md](research/README.md) shows how to verify the
   pre-registrations and rerun any study.

## How to respond

Reply by email to whoever sent you this, or to hello@hivemind.au. Comments on any line are welcome. We'll
acknowledge every point, and with your permission we'll credit reviewers in the 1.0 release.
