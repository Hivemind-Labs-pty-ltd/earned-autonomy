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

Earned Autonomy can supply operational evidence for an AI management system: documented roles and responsibilities,
risk-based controls per task type, monitoring and measurement, incident handling, and continual improvement through the
learning loop. Mapping to specific clauses: to do.

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
testing, human oversight, transparency, record keeping and contestability. Earned Autonomy provides practices for each:
named AI owners, consequence levels, pre-registered testing and hidden tests, levels with human checking, explanations,
a permanent record, and a challenge route. Mapping to the current named practices: to do.
