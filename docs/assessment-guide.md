# Assessment guide: choosing what to automate

*Informative. The Assess stage of the Earned Autonomy lifecycle. Version 0.7, October 2026.*

Earning trust takes human effort: documenting the process, reviewing the agent's work until it's trusted, and checking
it afterwards. That effort only pays off for some tasks. This guide helps you decide, **before spending anything**,
which task types are worth automating, how long they'll take to earn trust, and when they'll pay back.

---

## 1. The total cost model

Compare the full cost of automating a task type with the cost of keeping it manual:

| Cost | What it covers | When |
|---|---|---|
| **Setup** | Documenting the process, writing the task catalogue entry, checks and any playbook, and approving them | Once |
| **Ramp-up reviews** | The judged actions needed before the task type earns autonomy | Once, at the start |
| **Ongoing review** | Spot-checks, held actions, critical work that's always reviewed | Every month |
| **Model cost** | Running the AI | Every month |
| **Manual cost** (the alternative) | Doing every task by hand | Every month, forever |

From these:

- **Payback time** = (setup + ramp-up reviews) ÷ (monthly manual cost − monthly ongoing review − monthly model cost)
- **Time to autonomy** = judged actions needed ÷ judged actions per week
- **The multiple** = human time to do the work by hand ÷ human time with the agent

---

## 2. Inputs per task type

| Input | Where it comes from |
|---|---|
| **Volume** per month | System records, email history |
| **Minutes per task by hand** | Staff estimates first, then timed |
| **Consequence level** (C1 to C4) | The AI owner |
| **How rule-based it is:** how much of it follows a fixed procedure | Past cases, or a short shadow run |
| **Whether facts can be checked** against a system of record | The systems in place |
| **Evidence mode available** (shadow comparison, past cases, or supervised review only) | Whether staff work leaves a digital trace, and whether past cases are recorded |
| **Setup effort** | Estimated, then timed |

### Judged actions needed to earn autonomy (no mistakes along the way)

| Consequence | Judged actions |
|---|--:|
| C1 Low | 35 |
| C2 Moderate | 73 |
| C3 High | 189 |
| C4 Critical | Never acts alone |

Each mistake along the way adds more. See the full tables in the [practitioner guide](guide.md).

---

## 3. Verdicts

| Verdict | Typical profile |
|---|---|
| **Automate** | High volume, mostly rule-based, facts checkable, low to moderate consequence, payback in months |
| **Assisted** | The agent prepares the work; a person makes the judgement call. Suits judgement-heavy or high-consequence work with enough volume |
| **Keep manual** | Critical, rare, or too variable to describe |
| **Not yet** | No records to learn from, or no way to check the facts. Revisit once data or checks exist |

---

## 4. Make the forecast real with shadow mode

Estimates are a start, not an answer. Where staff work leaves a digital trace, run the agent in **shadow mode** for a
couple of weeks on the real work: staff keep working as normal, the agent drafts in parallel, nothing is sent, and the
system compares the agent's decisions and facts with what staff actually did. There's no risk and no extra review time.

The measured agreement per task type replaces guesses with data. For example: "invoice queries: 96% agreement; trusted
in about 3 weeks; payback in about 6 weeks. Complaints: 61% agreement; keep manual."

---

## 5. Worked example

*Illustrative numbers, not measurements.* One process, for example answering supplier invoice queries:

| Item | Hours |
|---|--:|
| Manual: 500 tasks a month × 4 minutes | about 33 per month, every month |
| Setup: documenting the process, catalogue entry, checks | 8 to 16, once |
| Ramp-up: 5 task types × about 75 judged actions × 1 minute | about 6, once |
| Ongoing: about 0.8 minutes per task × 500 | about 7 per month |
| **Saving** | **about 26 hours per month; payback in about the first month** |

It stops paying off when:

- **volume is low:** rare tasks never earn back their setup;
- **much of the work is high-consequence:** about 189 judged actions to earn trust, and critical work is reviewed
  forever;
- **the process is messy:** setup grows and fewer actions follow a fixed procedure.

---

## 6. What the research says

From the pre-registered Trust Gym rounds ([research/README.md](../research/README.md)):

- **The multiple from trust rules is about 4.4 to 6.3 times over a whole run,** up to about 7.9 times once tasks have
  earned trust. Reviewing everything already gives about 3.6 to 4 times, because reviewing is quicker than doing.
- **Trust rules alone don't reach ten times.** Getting further needs cheaper evidence (shadow comparison, replay),
  faster reviews (batch review by exception) and better agents (see the [implementation guide](implementation-guide.md)).
- **Rare tasks don't pay back.** Keep them supervised or manual.
- **Judgement-heavy work escalates by design.** Complaints, compensation and unusual cases go to people; plan for that
  in the forecast rather than counting them as automated.
- **The manual times above are assumptions.** The multiple depends on them, so time real work before quoting a number.

---

## 7. Cutting setup cost

- **Have the AI draft the process documentation** from existing emails, notes and past cases; people correct and
  approve it.
- **Reuse catalogue entries** across organisations doing the same work: the second firm starts from the first one's
  templates.
- **Start with the task types the assessment ranks highest,** and add others once the first ones pay back.
