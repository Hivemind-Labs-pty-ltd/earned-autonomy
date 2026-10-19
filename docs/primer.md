# Primer

*Informative. Start here if you're new to Earned Autonomy.*

## The problem

AI agents now answer customers, process refunds, update records and book appointments. Every business that deploys
one faces the same question: **when can this agent act without a person checking first?**

Most teams answer it once, by gut feel, for the whole agent: either everything is checked forever, which is safe but
slow, or the agent is switched to "automatic", which is fast but risky. Neither answer changes as the agent gets better
or worse.

Earned Autonomy answers it the way we answer it for people: **trust is earned from a record of good work, one kind of
task at a time, and it can be lost.**

## Core concepts

**Action.** Anything an agent does that changes something: sending a reply, issuing a refund, updating a record,
booking a time. Reading information isn't an action. The framework governs actions before they happen.

**Task type.** A named kind of action, such as `customer_service.refund.issue`. Each task type is an entry in a
**catalogue** with a description, a few example requests, the tools it may use, and a consequence level. Trust is
tracked per task type, so an agent can be trusted with one kind of work and supervised on another.

**Consequence level.** How much a mistake on that task type would cost. It sets how much proof is needed before the
agent acts alone:

| Level | Typical work | Maximum serious-mistake rate |
|---|---|---|
| Low (C1) | Internal notes, tagging, answers to common questions | 10% |
| Moderate (C2) | Customer replies, bookings, record updates | 5% |
| High (C3) | Commitments, small refunds, access changes | 2% |
| Critical (C4) | Money, deletions, legal or irreversible actions | Never acts alone |

**The ladder.** Each task type moves between three levels:

- **Supervised:** a person approves every action before it happens. Everything starts here.
- **Trusted:** the agent acts alone; one in four actions is checked afterwards.
- **Senior:** the agent acts alone; one in twenty actions is checked afterwards.

**The trust loop.** Every proposed action goes through the same steps: tag its task type, run the automatic checks,
look up the task type's level, then act or hold it for a person. Every judgement is recorded, and the record updates
the level.

**Earned, overseen, governed.** Trust has three parts. *Earned*: evidence decides the level. *Overseen*: spot-checks,
pausing and an explanation for every action. *Governed*: named owners, clear roles, and a permanent record nobody can
alter.

**AI owner.** The business person accountable for the agents in an area, usually a team lead or department head. They
own the catalogue of task types and each type's consequence level.

## Why worst-case evidence?

If an agent handles five refunds correctly, its error rate so far is zero, but five is too few to know anything: it
could really be getting one in three wrong and have been lucky. So the framework doesn't ask "what's the error rate?".
It asks: **"what's the highest error rate that could still plausibly explain what we've seen?"**

That worst case shrinks as clean work builds up. A useful rule of thumb: with no mistakes, the worst case is roughly
**4 ÷ the number of judged actions**. To be confident the error rate is under 5%, an agent needs about **73 clean
judged actions**. One mistake along the way raises that to about 110.

Promotion and step-down use opposite questions:

- **Promote when even the worst case looks good.**
- **Step down when even the best case looks bad.** For example, six serious mistakes in the last fifty judged actions.

So trust is slow to gain and quick to lose, and checking never stops.

## What the evidence shows

Four rounds of pre-registered experiments, plus a run on a commercial agent platform, tested the rules using simulated
organisations, 6,000 generated tasks done by real AI agents, and a public customer-service benchmark. Compared with
letting an agent act freely, the framework let through **83–94% fewer serious mistakes**. **93–100% of promotions were
deserved**, slips were caught within about **14 actions**, and **every autonomous action could be explained**.
Some recommendations failed their tests and were dropped; the reports say which.

All of this is synthetic so far. A real-world pilot is the next step. Details: [research/README.md](../research/README.md).

## Where to go next

- A full worked example, one action from proposal to promotion: [spec/examples.md](../spec/examples.md)
- Running agents day to day: [the practitioner guide](guide.md)
- Building it: [the specification](../spec/README.md) and the [reference engine](../engine/README.md)
