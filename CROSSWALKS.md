# Crosswalks

*Informative. Version 0.7. **Draft: every mapping here is to be verified before launch.** These map concepts between Earned
Autonomy and other frameworks. They are not claims that using Earned Autonomy makes anyone compliant with anything.*

## Cloud Security Alliance Agentic Trust Framework

The closest related framework. It assigns maturity levels to whole agents and describes zero-trust controls for them.
Earned Autonomy instead measures trust continuously per task type and sets autonomy from that measurement; its simple
(Core) setting uses three levels, mapped below.

| Agentic Trust Framework | Earned Autonomy | Note |
|---|---|---|
| Intern (observe and report) | Supervised, or an agent not yet enabled for a task type | Ours applies per task type |
| Junior (recommend; a human approves) | Supervised | |
| Senior (act, then notify) | Trusted | |
| Principal (autonomous, strategic oversight) | Senior | Ours still spot-checks 1 in 20 |
| Critical incident → back to Intern | Incident → that task type steps down one level | Tested: dropping to the bottom added nothing |

**Deliberate differences:**

- **Per task type, not per agent.** In testing, trust per agent gave 7% automation against 27% per task type.
- **Evidence-backed thresholds.** Its promotion gates are described as illustrative; ours come from statistics and
  pre-registered tests.
- **Scoped step-down.** A slip affects one task type, one level.
- **A lifecycle, not a one-way ladder.** Trust is measured continuously and can lead to more autonomy, more oversight,
  improvement, a pause or retirement.
- **Runnable.** Ours ships a reference engine and conformance tests.

## NIST AI Risk Management Framework

| NIST function | Earned Autonomy lifecycle stage |
|---|---|
| Govern | **Govern** (throughout): roles (AI owner, policy owner, reviewer, auditor), separation of duties, versioned policy, permanent record |
| Map | **Assess**: task-type catalogue, consequence levels, allowed tools per task type, the cost model |
| Measure | **Measure**: trust score and profile per task type, judged outcomes, reason codes, hidden tests, reviewer trust |
| Manage | **Decide, Oversee, Learn, Retire**: autonomy settings, spot-checks, alarms, pause, the learning loop, retiring automation |

## ISO/IEC 42001 (AI management systems)

*First cut, not reviewed. Clause titles are from the standard's public structure; we have not checked this against the
purchased text, so treat every row as (unverified). Source: [ISO/IEC 42001:2023](https://www.iso.org/standard/81230.html).*

Earned Autonomy can supply operational evidence for an AI management system. It is not a management system itself:
scope, policy, objectives, competence and internal audit stay with the organisation.

| Clause or Annex A area | Earned Autonomy | Coverage |
|---|---|---|
| 4 Context of the organisation | Task-type catalogue and consequence levels describe what the agent does (EA-6.2, EA-7.1, EA-1.5) | Partial |
| 5 Leadership | Named AI owner and roles (EA-6.1); separation of duties (EA-6.4). AI policy and top-management commitment are not covered | Partial |
| 6 Planning (risk and impact assessment) | Consequence levels set the error bar (EA-1.5, EA-1.6); tool floors (EA-7.8). The assessment itself is informative only (`docs/`) | Partial |
| 7 Support (resources, competence, documentation) | The permanent record (EA-6.7, EA-6.13); reviewer trust measures reviewer competence in practice (EA-3.12) | Partial |
| 8 Operation | Decision rules (EA-2.1 to EA-2.23); tool scope (EA-7.7); version testing (EA-4.5) | Full for runtime control of autonomy |
| 9 Performance evaluation | Trust score and profile (EA-1.14, EA-1.15); spot-checks (EA-3.1); alerts (EA-3.10, EA-1.11); periodic review (EA-5.3). Internal audit and management review: not covered | Partial |
| 10 Improvement | Incidents (EA-3.7, EA-2.18); corrections become rules and tests (EA-4.2); rollback (EA-4.12) | Partial |
| A.2 to A.4 Policies, internal organisation, resources | Roles (EA-6.1); versioned policy (EA-6.6) | Partial |
| A.5 Impact assessment | Consequence levels only. Impact on people and society: Gap | Gap |
| A.6 AI system life cycle | Versions and testing (EA-4.1, EA-4.5, EA-4.11); retirement (EA-5.4, EA-5.6). Design and build: not in scope | Partial |
| A.7 Data for AI systems | Not in scope. The record holds no customer content (EA-6.14) | Not in scope |
| A.8 Information for interested parties | Explainable decisions (EA-2.12); incident and challenge routes (EA-3.7, EA-3.8). Disclosure to users: Gap | Partial |
| A.9 Use of AI systems | Autonomy per task type (EA-2.9); held actions (EA-3.4); pause (EA-3.9) | Full for autonomy and oversight |
| A.10 Third-party relationships | Multi-agent delegation (EA-8.1, EA-8.2), preview only. Supplier contracts: not in scope | Partial |

## EU AI Act, Article 14 (human oversight)

| Oversight need | Earned Autonomy |
|---|---|
| People can understand the system's capacities and limits | Per-task-type levels with the evidence behind them; explanation for every action |
| People can monitor operation and detect problems | Spot-checks, alerts, incidents, reviewer trust |
| People can decide not to use the output, or override it | Held actions, rejection with reasons, the challenge route |
| People can intervene or stop the system | Pause per agent or per task type, rollback |

Whether a given deployment falls under the Act, and which obligations apply, is outside this framework.

## Australia's AI guidance

Australia's Voluntary AI Safety Standard and the Guidance for AI Adoption emphasise accountability, risk management,
testing, human oversight, transparency, record keeping and contestability. The sections below map the current
guidance. Earned Autonomy is the technical layer: how much one agent may do alone, and the evidence for it. The
guidance is mostly the enterprise layer: policy, registers, disclosure, training and supply chains.

### Guidance for AI Adoption (AI6), National AI Centre

*First cut for review. Practice names and numbered actions are from the Foundations document (October 2025):
[ai.gov.au PDF](https://www.ai.gov.au/sites/default/files/2026-07/Guidance-for-AI-adoption-foundations_2.pdf);
overview at [industry.gov.au](https://www.industry.gov.au/publications/guidance-for-ai-adoption).*

| Essential practice | Earned Autonomy rules | Coverage |
|---|---|---|
| 1. Decide who is accountable | Named AI owner per agent (EA-6.1, matches 1.3); owner keeps the catalogue (EA-6.2); agents can't govern themselves (EA-6.3, EA-6.4). Senior governance owner, AI policy, training (1.1, 1.2, 1.4, 1.6): enterprise layer. Supply chain (1.5): EA-8.2 for agent-to-agent only | Partial |
| 2. Understand impacts and plan accordingly | Contestability channels (2.2): incident reports and challenges (EA-3.7, EA-3.8). Patterns of feedback (2.4): reason codes (EA-3.6). Stakeholder impact assessment (2.1, 2.3) | Partial. Impact assessment: Gap |
| 3. Measure and manage risks | Controls by risk level (3.4): consequence levels and error bars (EA-1.5, EA-1.6), tool floors (EA-7.8), critical work always held (EA-2.8). Incidents and lessons (3.5): EA-3.7, EA-2.18, EA-4.2. Risk screening (3.1): informative only (`docs/`) | Partial |
| 4. Share essential information | Explain outcomes (4.5): every decision explainable (EA-2.12). Capabilities and limits (4.3): trust profile per task type (EA-1.15). AI register and disclosure (4.1, 4.2): enterprise layer | Partial. Disclosure of AI use: Gap |
| 5. Test and monitor | Test before deploying (5.2): EA-4.5, hidden tests (EA-4.3, EA-4.4). Monitor after (5.3): spot-checks (EA-3.1 to EA-3.3), alerts (EA-3.10), canaries (EA-3.11). Data governance and cybersecurity (5.4), stress tests (5.5), independent testing (5.6): not in scope | Partial |
| 6. Maintain human control | Oversight matched to autonomy and stakes (6.1): this is EA's core (EA-2.9, EA-2.15, EA-1.5). Override points (6.2): held actions (EA-3.4), pause (EA-3.9), rollback (EA-4.12), retire (EA-5.4). Training (6.3) and alternative pathways (6.4): enterprise layer | Full for 6.1 and 6.2 |

### Questions for buyers of agentic AI (NAIC)

*First cut for review. The National AI Centre says buyers should ask "What can it access? What can it do? What
authority has it been given? Who remains accountable?"
([NAIC blog, 29 September 2026](https://www.ai.gov.au/news-and-insights/blog/five-takeaways-industry-discussions-agentic-ai-and-risk)),
and it publishes [Questions to ask AI suppliers](https://www.ai.gov.au/sites/default/files/2026-07/Questions-to-ask-AI-suppliers.pdf).
We could not find a published NAIC list with exactly the ten questions below; the wording is ours, drawn from those two
sources (unverified as an official list).*

| Question | Earned Autonomy answer |
|---|---|
| What information will the AI use? | Out of scope for EA. The provider must answer. EA's own record holds references and labels only, never customer content (EA-6.14) |
| Where is data stored? | Out of scope for EA. The provider must answer |
| Will our data train the AI? | Out of scope for EA. The provider must answer |
| What systems can it access? | Tools are declared per task type, and the agent is offered only those (EA-7.7); each write tool has a floor consequence (EA-7.8). Access below the tool layer (credentials, networks) is the provider's |
| What actions can it take? | Only tagged actions of catalogued task types (EA-7.1, EA-7.5); unknown types are held (EA-2.4); critical work is always held (EA-2.8); delegation never adds authority (EA-8.1) |
| Can we limit it? | Yes: per task type autonomy levels (EA-2.9), error bars can only be tightened (EA-1.6), narrowing scope (EA-5.5), retiring a task type (EA-5.4) |
| Can we see logs? | Every decision is recorded with its reason and evidence (EA-2.12) in an append-only, tamper-evident, permanent record (EA-6.7, EA-6.8, EA-6.13); trust is readable from it at any time (EA-1.13). Raw content logs are the provider's |
| Can we pause or turn it off? | Pause an agent or a single task type (EA-3.9); paused work is held (EA-2.2); no action on review timeout (EA-3.18) |
| What happens if it makes a mistake? | Anyone can report an incident (EA-3.7); affected people can challenge (EA-3.8); the task type steps down at once (EA-2.18); corrections become rules and tests (EA-4.2). Remedy for the affected person: the deployer's |
| Who is responsible? | A named AI owner per agent and separated roles (EA-6.1, EA-6.4). Legal liability between buyer and provider: out of scope for EA |

### Gradient Institute, Agentic AI Governance Code of Practice

*First cut for review. Not mapped yet. We could not find this code published on
[gradientinstitute.org](https://www.gradientinstitute.org/research-publications) or elsewhere as of 2026-11-04
(unverified: it may be unreleased or under another title). We will not paraphrase obligations we have not read.*

What we could verify from Gradient Institute:

- Gradient developed the AI6 essential practices with the NAIC
  ([Impact Report 2025](https://www.gradientinstitute.org/impact/2025)). The AI6 mapping above therefore covers
  Gradient's published governance practices.
- Gradient wrote the Australian AI Safety Institute's first report, on risks and controls for AI agents that interact
  across organisational boundaries
  ([Gradient, 11 August 2026](https://www.gradientinstitute.org/research-publications/new-report-examines-risks-and-controls-for-ai-agents-interacting-across-organisational-boundaries)).
  Its point that "a system made up of individually safe and reliable agents is not necessarily a safe and reliable
  system" matches EA's multi-agent preview: delegation never adds authority (EA-8.1), provenance (EA-8.2), and keeping
  consequential peer work supervised (EA-8.4). Controls across organisations: Gap. EA covers agents under one
  organisation's policy only.

To do: once the code's text is available, map each obligation to EA rule IDs here, marking "Gap" where EA has no rule.
