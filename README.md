# Earned Autonomy

> **Status:** private working draft, version 0.7. "Earned Autonomy" is a working name.

## The problem

AI agents now answer customers, issue refunds and update records. Most businesses using one already have safety
controls: guardrails, filters, an approval step. Those stop the mistakes you can predict. They don't answer the
question that decides whether the agent is worth having:

> [!IMPORTANT]
> ## When can an AI agent work without a person checking?

Without a real answer, teams decide once, on gut feel. Either a person approves everything forever, which is safe but
saves little time, or the agent is switched to "automatic" and the guardrails are left to catch mistakes they were
never built for, like a reply that's polite and follows the rules but is simply wrong. Neither choice changes as the
agent gets better or worse.

We already know a better way, because it's how we treat new staff: give them more freedom as they prove themselves,
keep an eye on their work, and pull back when things slip. Earned Autonomy does the same for AI agents.

## The principles

1. **Keep measuring trust.** For each kind of task, always know how sure you are that the agent does it well enough.
   Every reviewed piece of work updates that answer.

2. **Let the measurement decide.** How much the agent may do alone follows a clear rule based on that measurement,
   not on a feeling, a demo or a sales pitch.

3. **Trust comes only from checked work.** A person's review, a comparison with what staff actually did, or past
   cases. Complaints show up after the damage is done, so they can lower trust but never raise it.

4. **Trust is per task, not per agent.** An agent can be trusted to update orders and still need approval for refunds.

5. **The bigger the risk, the higher the bar.** Costly mistakes need more proof first. Some actions, like moving money
   or deleting records, are never handed over.

6. **Checking never stops.** Even trusted work is spot-checked at random. Checks get rarer as trust grows, but never
   stop, and the agent never knows which work is checked.

7. **Every fix is a lesson.** When a person corrects the agent, the fix becomes a rule or a test. Any change to the
   agent means its trust is measured again.

8. **Reviewers earn trust too.** People who check the agent's work are measured the same way. A reviewer who misses
   mistakes gets checked more.

9. **A named person is responsible.** Every agent has an owner, nobody approves their own agent, and every action is
   recorded permanently.

10. **Know when to stop.** Some work is too rare, too risky or too varied to be worth automating. Say so, and switch
    off automation that no longer pays its way.

**The goal:** get more work done for each hour of people's time, without letting more serious mistakes through.

## Next

- **New to the idea?** Read the [primer](docs/primer.md). It takes about ten minutes.
- **Building an agent?** Read the [implementation guide](docs/implementation-guide.md).

Going deeper: the [practitioner guide](docs/guide.md) for running agents day to day, the
[assessment guide](docs/assessment-guide.md) for choosing what to automate, the [specification](spec/README.md) for
engineers, and the [research](research/README.md) behind it all. Want to help? See [CONTRIBUTING.md](CONTRIBUTING.md).

---

Maintained by Hivemind Labs. Private until launch.
