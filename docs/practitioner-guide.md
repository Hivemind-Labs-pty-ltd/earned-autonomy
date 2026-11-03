# Practitioner guide

How to run AI agents with Earned Autonomy day to day. For team leads, department heads, operations and compliance
staff. Read the [primer](primer.md) first: this guide builds on its ideas rather than repeating them. Terms are defined
in [terminology](../spec/terminology.md).

## 1. Roles

| Role | Who it usually is | Responsible for |
|---|---|---|
| **AI owner** | A team lead or department head | The agents in their area: which task types they do, each one's consequence level, and whether automation continues |
| **Policy owner** | Operations, risk or compliance lead | The rules: error bars, what's never handed over, spot-check rates, review windows |
| **Reviewer** | Staff who know the work | Judging the agent's actions: approve, fix or reject, and say why |
| **Auditor** | Internal audit, or an external assessor | Reading the record. Changing nothing |
| **Builder** | Whoever configures or changes the agent | New versions of the agent |

One person can hold several roles, but **a builder never approves their own agent's autonomy or loosens its rules.**

## 2. Before go-live: Assess and Build

- **Choose the work** with the [assessment guide](assessment-guide.md). The result is the task catalogue.
- **Give each task type a consequence level.** Your organisation decides what counts as critical.
- **Build the agent any way you like.** It must only declare the tools each task type may use, and supply a checks
  result for every proposed action. The [implementation guide](implementation-guide.md) has advice.

## 3. Measure

For every task type, the system keeps a current **trust measurement**:

| Part | Example |
|---|---|
| **Trust score** | 97% confident the mistake rate is under 5% |
| **Estimated mistake rate** | 1.2%, plausibly 0.3% to 3.9% |
| **Evidence strength** | Equivalent to 140 judged actions |
| **Evidence sources** | Reviews 80 · shadow comparison 50 · past cases 30 |
| **Freshness** | Current version, last evidence 2 days ago |
| **Trend** | Stable, improving or slipping |

Across all its task types, an agent gets a **trust summary**, such as "trusted for 64% of its work; supervised on
refunds and quotes; one incident in 30 days".

### Choosing how to gather evidence

| What you have | Evidence mode | Extra human time |
|---|---|---|
| Staff work leaves a digital trace (an email sent, a record changed) | **Shadow comparison:** staff keep working; the agent drafts in parallel and sends nothing; the system compares the two | None |
| Past cases are recorded | **Historical replay:** test the agent on cases people already handled | None |
| Neither | **Supervised review:** a person approves each draft first | One review per action |

## 4. Decide

**Promote** one level when a task type has enough judged actions for its consequence level and its mistakes so far,
and at least 30 judged actions have passed since its last change:

| Serious mistakes so far | 0 | 1 | 2 | 3 | 4 | 5 |
|---|--:|--:|--:|--:|--:|--:|
| **C1 Low** (bar 10%) | 35 | 53 | 69 | 84 | 99 | 113 |
| **C2 Moderate** (bar 5%) | 73 | 110 | 142 | 173 | 202 | 230 |
| **C3 High** (bar 2%) | 189 | 280 | 361 | 437 | 510 | 581 |

**Step down** one level when serious mistakes in the last 50 judged actions reach **10 (C1), 6 (C2) or 3 (C3)**, or on
any incident. Critical (C4) work never acts alone. Full tables:
[core-tables.md](../research/core/core-tables.md).

At any point the options are: **more autonomy**, **keep it as is**, **check more**, **narrow its scope**, **improve
it** (a new version), **pause it** or **retire it**.

An advanced option replaces the three levels with a dial that sets checking directly from the trust score. It's still
being tested.

## 5. Oversee

- **Random, hidden spot-checks.** The agent never knows which actions are checked. In testing, an agent that could
  predict its reviews looked eighteen times better than it really was.
- **Planted test items (canaries).** A few known mistakes go into review queues to check reviewers are still catching
  things.
- **Alarms.** A complaint, reversal or "this was wrong" report steps that task type down at once.
- **Pause.** The AI owner can pause an agent or one task type in one step.

### When reviewers aren't available

- **Review windows:** clear queues at set times, such as twice a day.
- **Waiting-time limits per task type:** such as customer replies within 2 hours.
- **Batches close on size or time,** such as 20 items or 30 minutes, whichever comes first.
- **Only pre-reviews cause delay.** Spot-checks happen afterwards, so as trust grows, the delay disappears.
- **Nothing acts because nobody reviewed it.** An unreviewed action waits; it never goes ahead on a timeout.

### Critical work with a deadline

For example, a payment due on a long weekend:

1. **See it coming:** flag critical work due inside a reviewer gap before the gap starts.
2. **Approve in advance, with conditions:** "release on Tuesday if the amount and bank details are unchanged".
3. **Name an on-call approver** with one-step approval and full context.
4. **If nobody approves,** the policy owner's fallback applies: escalate, tell the affected party, record the miss.

## 6. Learn

- **Always give a reason** when fixing or rejecting. The reason becomes a rule or a test.
- **Every change to the agent is a new version,** including knowledge edits. It keeps its trust if it passes at least
  80% of its hidden tests; otherwise it loses half its record.
- **Hidden tests stay hidden** from the agent and from whoever improves it.
- **Batch changes into regular releases,** such as weekly, so the agent isn't constantly re-measured.
- **Passing tests never earns autonomy.** Tests catch the agent changing; only judged work shows how it does the job.

## 7. Retire

- **Rare task types stay supervised.** Twice a month would take years to earn trust, but costs only two reviews a
  month to keep checking.
- **Back after a break:** a task type unused for 60 days steps down one level when it returns.
- **Stop when it doesn't pay,** and record why.

## 8. Govern

| Artefact | What it is | Who keeps it |
|---|---|---|
| **Task catalogue** | Every task type, with description, examples, tools and consequence level | AI owner |
| **Policy file** | Error bars, what's never handed over, spot-check rates, review windows. Versioned | Policy owner |
| **Trust record** | Every action, decision, review and incident, permanently. Labels and references, not customer content | The system; auditors read it |
| **Review queue** | Actions waiting for a person, and sampled actions to check afterwards | Reviewers |
| **Test suites** | Tests built from real corrections. Some hidden | The system, approved by the policy owner |

### Rituals

| Ritual | When | Who |
|---|---|---|
| **Review queue** | In review windows, daily | Reviewers |
| **Trust review:** promotions, step-downs, near-misses | Weekly | AI owner |
| **Release review:** batch fixes into one tested release | Weekly | AI owner, builder |
| **Incident review:** what happened and what prevents it again | Within 48 hours | AI owner, policy owner |
| **Agent review:** right scope? still paying back? retire anything? | Quarterly | AI owner, policy owner |

## 9. Common questions

**How long until an agent works hands-off?** About 35 clean judged actions for low-consequence work, 73 for moderate
and 189 for high. Critical work never goes hands-off, and checking never stops.

**Does the AI model matter?** Yes, and so do its instructions. Changing either is a new version, so trust is measured
again.

**Can automated tests replace spot-checks?** No. Tests catch the agent changing; spot-checks catch the world changing.

**Who's accountable when an autonomous action goes wrong?** The AI owner. The record shows exactly why it was allowed:
the task type, its measurement, the evidence, the checks and the rules in force.
