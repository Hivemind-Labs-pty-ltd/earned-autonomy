# Earned Autonomy

[![tests](https://github.com/Hivemind-Labs-pty-ltd/earned-autonomy/actions/workflows/tests.yml/badge.svg)](https://github.com/Hivemind-Labs-pty-ltd/earned-autonomy/actions/workflows/tests.yml)
[![spec](https://img.shields.io/badge/spec-v0.7-blue)](spec/README.md)
[![licence](https://img.shields.io/badge/licence-CC%20BY%204.0%20%2B%20Apache--2.0-lightgrey)](#licence)
[![status](https://img.shields.io/badge/status-draft-orange)](CHANGELOG.md)
[![python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](engine/README.md)

**A methodology for deciding how much freedom to give AI agents, and when.**

> Reviewing v0.7? Start with the [note for reviewers](REVIEWERS.md).

## When can an AI agent work without a person checking?

AI agents now answer customers, issue refunds and update records. Guardrails stop the mistakes you can predict, but
they can't answer this question. So most teams pick one setting and never change it:

- **Check everything:** Safe, but the agent saves little time.
- **Switch to automatic:** Fast, but mistakes reach customers.

**The better way is how we treat new staff:** freedom is earned by trust, and lost when mistakes creep in.

## The principles

Earned Autonomy is a way of working, not just a piece of technology. These ten principles are the heart of it: every tool, rule and decision follows from them.

| # | Principle |
|:-:|---|
| 1 | **A named person is responsible**<br>Every agent has an owner, nobody approves their own agent, and every action is recorded permanently. |
| 2 | **Keep measuring trust**<br>For each kind of task, always know how sure you are that the agent does it well enough. Every reviewed piece of work updates that answer. |
| 3 | **Let the measurement decide**<br>How much the agent may do alone follows a clear rule based on that measurement, not on a feeling, a demo or a sales pitch. |
| 4 | **Trust comes only from checked work**<br>Reviews, staff comparisons and past cases count. Complaints come too late: they can lower trust, never raise it. |
| 5 | **Trust is per task, not per agent**<br>An agent can be trusted to update orders and still need approval for refunds. |
| 6 | **The bigger the risk, the higher the bar**<br>Costly mistakes need more proof first. Some actions may never be handed over. |
| 7 | **Checking never stops**<br>Even trusted work is spot-checked at random. Checks get rarer as trust grows, but never stop, and the agent never knows which work is checked. |
| 8 | **Learn from feedback**<br>Have a clear, simple way to turn corrections into better instructions. Any change means trust is measured again. |
| 9 | **Reviewers earn trust too**<br>People who check the agent's work are measured the same way. A reviewer who misses mistakes gets checked more. |
| 10 | **Know when to stop**<br>Some work is too rare, too risky or too varied to be worth automating. Switch off automation that no longer pays its way. |

**The goal:** get more work done for each hour of people's time, without letting more serious mistakes through.

## Common questions

- **Who is it for?** Anyone running AI agents in a business: owners, team leads and the people who build them.
- **Does it replace our safety controls?** No. It works alongside them and decides when they're enough.
- **Do we need special software?** No. It works with any agent, built any way. A [reference engine](engine/README.md)
  is there if you want one.
- **Does it work?** It has been tested in simulated experiments, failures included. A real-world pilot is next.
  [See the research](research/README.md).
- **How does it fit with other frameworks?** It maps onto standards like the NIST AI RMF and ISO 42001.
  [See the crosswalks](CROSSWALKS.md).

## Next

- **New to the idea?** Read the [primer](docs/primer.md). It takes about ten minutes.
- **Building an agent?** Read the [implementation guide](docs/implementation-guide.md).

Going deeper: the [practitioner guide](docs/practitioner-guide.md) for running agents day to day, the
[assessment guide](docs/assessment-guide.md) for choosing what to automate, the [specification](spec/README.md) for
engineers, and the [research](research/README.md) behind it all. Want to help? See [CONTRIBUTING.md](CONTRIBUTING.md).

---

<a id="licence"></a>Maintained by Hivemind Labs. The methodology and docs are licensed under [CC BY 4.0](LICENSE-docs); the code
(`engine/`, `conformance/`, `research/` code and `scripts/`) under [Apache-2.0](LICENSE). Please read our
[code of conduct](CODE_OF_CONDUCT.md) and [security policy](SECURITY.md).
Private working draft, version 0.7. "Earned Autonomy" is a working name.
