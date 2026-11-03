# Implementation guide: building agents that earn trust fast

What our research found about building agents that make fewer mistakes, and so earn trust faster and cheaper.

The standard asks only two things of an agent: **declare the tools each task type may use**, and **supply a checks
result for every proposed action**. Everything else here is advice.

---

## 1. Give each task only the tools it needs

Offer the agent only the tools a task type actually requires, not everything it could ever use.

- **Evidence:** on the same 1,800 tasks, narrow tools cut serious mistakes by 65% and raised the multiple by 6%
  ([REPORT-core.md](../research/REPORT-core.md)). In the first round they cut wrong or unnecessary tool calls by 73%
  ([REPORT.md](../research/REPORT.md)).
- **Why it works:** many mistakes, including obeying instructions hidden in a customer's message, need a tool the task
  shouldn't have. If the tool isn't there, the mistake can't happen.
- **Don't share a risky tool across tasks of different consequence.** One "send email" tool used for both reminders and
  offers drags the reminders up to the offer's consequence level. Split it into separate tools.

---

## 2. Make checks precise

Automatic checks before an action goes out (right amount, right record, no promise the policy doesn't allow) are the
cheapest safety there is. But a check that fires when nothing is wrong wastes a person's time.

- **Evidence:** on a production agent harness, the checks caught far more real problems than simple checks did, but
  raised false alarms on 32–39% of the actions they held, and held about a third of all actions. Most of that review
  time was wasted ([REPORT-10x.md](../research/REPORT-10x.md)).
- **Measure each check's false-alarm rate before relying on it.** Fix or auto-correct trivial issues rather than
  holding the whole action.
- **Prefer exact checks against the system of record** (the amount on the invoice, the order's real status) over
  judgement calls.

---

## 3. Approved playbooks for recurring work

An **approved playbook** is the process written as code and signed off once by a person, like a staff procedure. Code
looks up the records, checks every value against them, picks the next step from the allowed options, and carries out
only the actions the playbook lists. The AI only does two things: pulls the values it needs out of the request, and
writes the message from facts the code supplies. Code then checks the message too.

- **Evidence:** on 1,800 tasks, playbooks made **zero serious mistakes** (against 2% for a free-form agent) and **zero
  actions triggered by hidden instructions** (against 29) ([REPORT-playbooks.md](../research/REPORT-playbooks.md)).
  When something went wrong, it failed safely: the case went to a person.
- **Judgement-heavy work escalates by design.** Complaints, compensation, unverified deletions and unapproved payments
  went to people, which is where they belong.
- **The costs are real:**
  - **Authoring and approval.** AI drafts needed genuine policy fixes before approval. Approval time is part of setup.
  - **Model cost didn't fall** in our test, because the same model did the extraction and the writing. Savings need
    templated wording for routine replies and cheaper extraction (below).
- **Playbooks must be approved from the written policy, not learned from the agent's behaviour.** Rules learned from
  what an agent did copied its bad habits when promoted on agreement alone
  ([REPORT-contracts.md](../research/REPORT-contracts.md)).
- **Approved playbooks make agents safer, but they don't earn trust on their own.** The agent is still measured from
  evidence. Whether an approved playbook should change where a task type *starts* is an open question in the
  specification.

---

## 4. A learning loop, and a training camp before go-live

- **Turn every correction into a rule or a test.** In testing, two or three cycles of corrections took error rates from
  double digits to near zero, where the agent's instructions were the main problem ([REPORT.md](../research/REPORT.md)).
- **Train before going live.** Run the agent through hundreds of generated and past cases, with checks as the automatic
  grader, and feed every failure back as a lesson. That compresses weeks of live corrections into hours.
- **Keep hidden tests the agent never trains on,** so improvements are real and not just learning to pass the tests.
  Hidden test scores tracked real error rates closely in testing.
- **Learning faster isn't the same as being trusted faster.** Fewer early mistakes mean the agent reaches the minimum
  number of judged actions without setbacks. The minimum still applies.

---

## 5. Cut model cost

- **Templated wording** for routine replies, with the AI only filling in values.
- **Rules or a small model for pulling out structured values** (invoice numbers, dates, amounts), with a larger model
  only where the language is genuinely open-ended.
- **Code for every step that doesn't need judgement,** as in a playbook.

These weren't tested as a package yet; the playbook round showed where the cost sits (the writing call was about two
thirds of it).

---

## 6. Make reviews fast

Human time is the number of reviews times the time per review. Most effort goes into cutting the number; the time per
review matters just as much. In our cost model, halving it roughly doubles the multiple.

- **Review by exception, in batches:** show many similar actions on one screen, with the checked facts highlighted, and
  let the reviewer flag only the odd one out.
- **Facts first:** show what was checked and why the action was held, not the whole conversation.
- **One-step approval on a phone,** with reasons pre-filled.
- **Daily approval windows for critical work,** plus pre-approval with conditions.

These are recommendations, not yet measured. Measure real seconds per review in any pilot.

---

## 7. Where to start

1. Narrow tools per task type and precise checks: cheap, and the biggest proven gains.
2. Approved playbooks for the highest-volume, most rule-based task types.
3. A training camp and learning loop before go-live, with hidden tests.
4. A fast review experience.
5. Cheaper models and templated wording once the work is stable.
