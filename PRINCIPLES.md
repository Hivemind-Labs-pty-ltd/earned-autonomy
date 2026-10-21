# The Earned Autonomy Principles

*Working name. Version 0.7, October 2026. Hivemind Labs.*

AI agents are joining the workforce. We give new employees freedom as they prove themselves, keep an eye on their
work, and change their role as things change. We should do the same for agents. These principles describe a
**lifecycle**: measure how far an agent can be trusted, decide what to do about it, keep watching, keep improving, and
know when to stop.

**We value:**

- **Evidence** over intuition
- **Measuring continuously** over certifying once
- **Narrow scope** over broad capability
- **Checking that never stops** over sign-off once
- **A named person accountable** over "the system decided"

There is value in the items on the right; we value the items on the left more.

## The lifecycle

**Assess → Build → Measure → Decide → Oversee → Learn → Retire**, with **Govern** running through every stage.

## The ten principles

1. **Measure trust continuously.** For every kind of task an agent does, there is a current answer to "how sure are we
   that it's good enough?". The answer updates with every new piece of evidence.

2. **Decide from the measurement.** How much an agent may do alone, and how closely it is watched, follows from the
   measured trust, by a stated rule, not from a feeling, a demo or a vendor's claim.

3. **Trust is earned from evidence, and only from evidence.** There are no shortcuts. Evidence comes from judged work:
   a person's review, a comparison with what staff actually did, or past cases. Signals that only appear after harm
   has happened can raise an alarm, but never earn trust.

4. **Trust is per task, not per agent.** An agent can be trusted with order updates and still be supervised on refunds.

5. **Consequence sets the bar.** The more a mistake would cost, the more proof is needed before the agent acts alone.
   Some actions, like moving money or deleting records, are never handed over.

6. **Checking never stops.** Trusted work is still sampled at random, at a rate that falls as trust grows but never
   reaches zero. The agent never knows which actions are checked.

7. **Every correction is a lesson, and every change is re-measured.** When a person fixes the agent's work, the fix
   becomes a rule or a test. Any change to the agent, including its knowledge, is a new version whose trust is
   measured again.

8. **People earn trust too.** Reviewers are measured the same way agents are. A reviewer who misses mistakes is checked
   more, not trusted blindly.

9. **Someone owns it, and everything is on the record.** Every agent has a named owner. Nobody approves their own
   agent's autonomy. Every action can be explained, and the record is permanent and can't be altered.

10. **Know when to stop.** Some work isn't worth automating: it's rare, critical or too variable. The framework says so,
    and retires automation that no longer pays its way.

---

**The aim:** raise the multiple, meaning the work done per hour of human time compared with doing it by hand, without
letting more serious mistakes through. Trust can't be skipped, but it can be made cheaper to earn.

These principles are backed by pre-registered testing, failures included: see [research/README.md](research/README.md).
The practitioner guide ([docs/guide.md](docs/guide.md)) explains how to apply them.
