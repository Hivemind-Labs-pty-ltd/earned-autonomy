# Earned Autonomy: practitioner guide

*Working name. Version 0.6, October 2026. Hivemind Labs.*

This guide is for the people who run AI agents in a business: team leads, department heads, operations and compliance
staff. It explains how to apply the [principles](../PRINCIPLES.md) day to day. It doesn't depend on any particular agent
platform. Engineers building the machinery should read the [specification](../spec/README.md) instead.

This guide is informative. Where it describes a rule, the binding wording is in the specification, cited by its
number, for example (EA-3.8). If the two ever disagree, the specification wins.

---

## 1. The idea in one paragraph

An agent earns freedom the way a new employee does. Every kind of work it does starts supervised: a person approves
each action. As its record of good work grows, that kind of work is promoted, first to acting alone with one in four
actions checked afterwards, then to one in twenty. If mistakes creep in, it steps down a level automatically. Every
correction becomes a lesson, every change to the agent is re-tested, and a named person is accountable throughout.

Trust has three parts, and you need all three:

| Part | Question it answers |
|---|---|
| **Earned** | How much freedom has this agent earned, for this kind of work? |
| **Overseen** | Who is watching it now, and can they stop it? |
| **Governed** | Who sets the rules, who is accountable, and how do the rules change? |

---

## 2. Roles

| Role | Who it usually is | Responsible for |
|---|---|---|
| **AI owner** | A team lead or department head | The agents in their area: which kinds of work they do (task types), how much each matters (consequence level), and whether they keep their place |
| **Policy owner** | Operations, risk or compliance lead | The rules: error bars, which work can never be handed over, how much gets spot-checked |
| **Reviewer** | Staff who know the work | Judging the agent's actions: approve, fix or reject, and say why |
| **Auditor** | Internal audit, or an external assessor | Reading the record. Changing nothing |
| **Builder** | Whoever configures or changes the agent | New versions of the agent. Never approves its own agent's promotion |

One person can hold several roles, except that **a builder never approves their own agent's promotion or loosens its
rules.**

---

## 3. Artefacts

| Artefact | What it is | Who keeps it |
|---|---|---|
| **Task catalogue** | Every kind of work the agent does, e.g. "send order update", "issue refund", each with a consequence level | AI owner |
| **Policy file** | The error bar per consequence level, what never gets handed over, spot-check rates. Versioned; every change logged | Policy owner |
| **Trust record** | Every action, decision, review, correction and incident, permanently. Labels and references, not customer content | The system; auditors read it |
| **Review queue** | Actions waiting for a person, and sampled actions to check afterwards | Reviewers |
| **Test suites** | Tests built from real corrections. Some are hidden: the agent never sees them | The system, approved by the policy owner |

---

## 4. The trust loop: what happens to every action

An **action** is anything an agent does that changes something: sending a reply, issuing a refund, updating a record,
booking a time. Before any action happens:

1. **Tag it.** What kind of task is this? If the system isn't sure, a person reviews it.
2. **Check it.** Run the automatic checks: right amount, right record, no promise it can't keep, nothing it isn't
   allowed to do. A failed check always goes to a person.
3. **Look up its trust.** Has this agent earned this kind of work? If not, a person approves it.
4. **Act, or hold.** Trusted work goes ahead. A random share is reviewed afterwards. The agent never knows which, and
   checks never follow a fixed schedule. In testing, an agent that could predict its reviews behaved well only when
   watched and looked eighteen times better than it really was.
5. **Record and learn.** Every judgement is recorded with a reason. The record updates the agent's standing, and
   real mistakes become new rules and tests.

Rules: tagging EA-1.8 to EA-1.10 · checks EA-2.3 · trust lookup EA-2.6 · random spot-checks EA-2.8 and EA-2.9 ·
reasons on every review EA-5.2.

---

## 5. The ladder

Each **task type** climbs on its own. An agent can be Senior at one task and Supervised at another.

| Level | What happens | How it's reached |
|---|---|---|
| **Supervised** | A person approves every action before it happens | Where every new agent and every new task type starts |
| **Trusted** | Acts on its own; 1 in 4 actions reviewed afterwards | Enough reviewed actions with errors under the bar |
| **Senior** | Acts on its own; 1 in 20 reviewed afterwards; regular summary | A further stretch of clean spot-checks |

**Moving down:** if recent mistakes rise above the bar, or a real incident happens, the task drops **one level**,
automatically. A task type that hasn't been used for more than 60 days also drops one level when it returns.

**Never climbs:** work with critical consequences, such as releasing money, deleting records, or anything legal or
irreversible.

Rules: start supervised EA-1.3 · promotion EA-3.4 · step down EA-3.5 to EA-3.7 · back after a break EA-3.13 · never
climbs EA-2.5. Each level is described in [spec/levels.md](../spec/levels.md).

---

## 6. Consequence levels

The AI owner gives every task type a consequence level. It sets how good the agent must prove to be before it acts on
that task alone. It never predicts how good the agent *is*: in testing, "low-risk" work was often where agents made the
most mistakes.

| Level | Typical work | Max serious mistakes | Reviews needed before the first promotion (with no mistakes) |
|---|---|---|---|
| **C1 Low** | Internal notes, tagging, FAQ answers; easy to undo | 10% | about 35 |
| **C2 Moderate** | Customer replies, bookings, record updates | 5% | about 75 |
| **C3 High** | Commitments, small refunds, access changes | 2% | about 190 |
| **C4 Critical** | Money, deletions, legal, irreversible | never promotes | |

The bar is measured cautiously: "even in the worst case, the error rate is under the limit". So the numbers of reviews
above are minimums, and one mistake along the way raises them. An AI owner can make a task's bar stricter, never
looser.

**What counts as a serious mistake:** a wrong or unauthorised action, a made-up fact or amount, a promise the policy
doesn't allow, or obeying an instruction hidden in a message. Changes to wording or tone don't count. "Incomplete"
(harmless, but didn't get the job done) is tracked separately, as a warning sign.

Rules: EA-3.3 and EA-3.8 to EA-3.10. The maths, with worked numbers, is in [spec/examples.md](../spec/examples.md).

---

## 7. Getting started: five stages

Move to the next stage only when the current one passes its gate. Stages 1 to 3 change nothing customers see.

| Stage | What you set up | Move on when | Typical time |
|---|---|---|---|
| **1. Record everything** | The task catalogue with consequence levels; an AI owner; reasons on every review; the trust record | Every action has a task type, and every review has an outcome and reason | 1–2 weeks |
| **2. Trust in shadow mode** | The trust engine calculates levels and marks what it *would* have let the agent do, while people still approve everything | For 3–4 weeks, what it would have let through stayed within the bar, judged by people's real decisions | 3–4 weeks |
| **3. Learning** | Corrections become rules and tests; hidden tests; new versions are tested before they go live | Hidden-test scores rise and fall with the real error rate | alongside stage 2 |
| **4. One task type goes live** | One low-consequence task type acts alone once it earns Trusted; spot-checks; an "this was wrong" button; pause per task type | 4+ weeks with mistakes under the bar, review time down, the business happy | 1–2 months |
| **5. Expand** | More task types; the Senior level; regular reviews; a way to challenge any decision; later, agents working with agents | Ongoing | |

**Tip:** choose a narrow set of tools for each task type from day one. In testing, giving the agent only the tools a
task needs cut wrong actions by about three quarters. Don't share a tool that changes things across tasks of different
consequence, for example one "send email" tool for both reminders and offers. A risky tool always pulls an action up
to its own consequence level, so the low-consequence task could never earn its freedom. Split it into separate tools
(EA-1.12 to EA-1.15).

---

## 8. Rituals

| Ritual | When | Who | What happens |
|---|---|---|---|
| **Review queue** | Daily | Reviewers | Approve, fix or reject held actions, always with a reason; check sampled actions |
| **Trust review** | Weekly | AI owner | Look at promotions, step-downs and near-misses per task type; approve any manual changes |
| **Release review** | Weekly | AI owner, builder | Batch the week's corrections and knowledge edits into one tested release, not a stream of small changes |
| **Incident review** | Within 48 hours of an incident | AI owner, policy owner | What happened, why it got through, what rule or test prevents it again |
| **Agent review** | Quarterly | AI owner, policy owner | Each agent's levels, incidents and drift. Is the scope still right? Is the agent still needed? |

---

## 9. Making corrections count

- **Always give a reason** when fixing or rejecting. A reason turns a correction into a rule or test. Without one,
  it's only a statistic.
- **Expect rules, not retraining.** In testing, two or three cycles of corrections took error rates from double
  digits to near zero, provided the agent's instructions were the main problem.
- **Every change to the agent is a new version,** including knowledge edits, because knowledge changes what the agent
  does. A new version keeps its standing only if it passes at least 80% of its hidden tests. So batch changes into
  regular releases, and keep the hidden tests well stocked.
- **Hidden tests stay hidden.** Neither the agent nor the person improving it should ever see them. Otherwise they
  stop measuring anything.

Rules: EA-4.1 to EA-4.7 and EA-4.11. Seeding hidden tests for each new version is optional (EA-4.10).

---

## 10. Reviewers earn trust too

Reviewers follow the same ladder as agents. A few known mistakes are planted in the queue (about 1 in 20 items). A
share of each reviewer's decisions is double-checked: a quarter for new reviewers, 1 in 20 for trusted ones. Reviewers
who miss mistakes are checked more closely, and their AI owner is told. This is quality control, not surveillance. It
finds reviewers who need support before their misses reach customers (EA-5.9 to EA-5.12).

---

## 11. Agents working with agents (preview)

When one agent hands work to another, the receiving agent never gets more freedom than the one delegating. The
platform tracks each agent's reliability per skill, keeps trying alternatives, and stops routing work to an agent
that turns unreliable. This part is the least proven. Keep agent-to-agent work supervised for anything consequential
(EA-7.1 and EA-7.4).

---

## 12. What to expect

From four rounds of pre-registered testing (simulated organisations, 6,000 tasks done by real AI agents, a public
benchmark):

| Compared with | What Earned Autonomy does |
|---|---|
| Letting the agent act freely | 83–94% fewer serious mistakes |
| Automatic checks only | 77–91% fewer serious mistakes |
| A person checking everything | About the same safety, with a fifth to a third less review work, falling further as the agent improves |

- **Promotions are deserved** 93–100% of the time.
- **Slips are caught** within about 14 actions.
- **Every autonomous action can be explained.**
- **Review load falls over time:** for a good agent, from about 85% of actions to about 45%. It stays higher for
  critical work, which never goes hands-off.
- **Weak agents stay supervised** until they improve. That's the point.

**Not yet proven:** results with real customers and real reviewers (a pilot is the next step), and agents trusting
agents. Every result, with its pre-registration, is in [research/README.md](../research/README.md).

---

## 13. Common questions

**How long until an agent works hands-off?** It depends on the task. A low-consequence task needs about 35 clean
reviewed actions; a moderate one about 75; a high one about 190. Critical work never goes fully hands-off, and nothing
goes to zero checking.

**What about tasks that rarely happen?** They stay supervised, usually for good. A task done twice a month would take years to build a record, but it also costs only two reviews a month to keep checking. That's rarely worth automating.

**Which tasks are safe to hand over?** You can't tell in advance. In testing, some "simple" tasks were where agents
failed most. The framework finds out per task, from evidence.

**Does the AI model matter?** Yes, and so do its instructions: the same model with weaker instructions made seven
times as many mistakes. Changing the model counts as a new version, so trust is re-earned.

**Can automated tests replace spot-checks?** No. Tests catch the agent changing; spot-checks catch the world changing,
such as a supplier's new process. Passing tests never counts as evidence for promotion (EA-4.12).

**What if we edit the agent's knowledge?** It's a new version. It keeps its standing if it passes its hidden tests.
Batch edits into regular releases.

**Who's accountable when an autonomous action goes wrong?** The AI owner for that area. The record shows exactly why
the action was allowed: the task type, its level, the evidence, the checks and the rules in force.

---

## 14. Glossary

The one glossary for the framework is in [spec/terminology.md](../spec/terminology.md).
