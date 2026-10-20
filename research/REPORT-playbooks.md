# Approved playbooks vs a free-form agent: results

Run 2026-10-21. Pre-registered in `PREREG-playbooks.md` (tag `research/prereg-playbooks`) before any code, draft or run.
Approval edits and runtime choices are logged in `DECISIONS.md` and `playbooks/approved/_review_log.json` before any task
ran. **New spend: about $0.67** (cap $15): drafting $0.11, runtime $0.56.

**Question:** an approved playbook is the process as code, signed off once by a person. Code looks up records, verifies
values, picks the branch, executes only listed actions and validates the message. The model only extracts slot values
and writes the reply. Against a free-form tool-using agent on the same 1,800 tasks, is it safer, cheaper and lighter on
human time?

## Verdicts

| # | Hypothesis | Result | Verdict |
|---|---|---|---|
| P1 | Serious errors ≤ 0.5 × free-form (good-full) | **0.00%** (0 of 1,800) vs 2.00% | **PASS** |
| P2 | Human minutes/task (incl. approval) ≤ 0.5 × free-form, starting Supervised | 1.09 vs 1.16 (ratio 0.94); 1.27 if approval took 3× as long | **FAIL** |
| P2b | Approved start (C1/C2 begin Trusted): minutes ≤ 0.5 × and escapes ≤ free-form + 0.1 | 0.80 min/task (ratio **0.69**); escapes **0.00** vs 0.36 per 100 | **FAIL** (minutes) |
| P3 | Model cost/task ≤ 0.5 × free-form | $0.000373 vs $0.000304 (ratio 1.22) | **FAIL** |
| P4 | Auto-pass by task type (descriptive) | see below | reported |
| P5 | Injected-instruction writes = 0 | **0** (of 246 tasks with an injection) vs 29 for free-form | **PASS** |

**Tally:** 2 PASS · 3 FAIL · 1 descriptive.

## Main numbers (same 1,800 tasks, same grader, same v3 trust policy, 20 seeds)

| Agent | Serious errors | Task success | Injected writes | Model cost/task | Human min/task | Escapes /100 | Done without a person |
|---|--:|--:|--:|--:|--:|--:|--:|
| Free-form, good prompt (good-full) | 2.00% | 96.2% | 29 | $0.000304 | 1.16 | 0.36 | 16.5% |
| Free-form, weak prompt (sloppy-full) | 13.06% | 80.8% | 20 | $0.000304 | 1.11 | 0.72 | 16.0% |
| Free-form, scoped tools (good-scoped) | 0.67% | 95.6% | 10 | $0.000304 | 1.13 | 0.06 | 24.1% |
| **Approved playbook** | **0.00%** | **97.3%** | **0** | $0.000373 | 1.09 | **0.00** | 25.1% |
| **Approved playbook, approved start** | 0.00% | 97.3% | 0 | $0.000373 | **0.80** | **0.00** | **61.1%** |

## What happened

- **Safety: the clear win.** No serious errors and no injected writes across all 20 task types. Every write came from
  code, with arguments taken from verified records, so a hostile message had nothing to steer. The 2.7% of tasks that
  failed failed *safely*: a quote escalated because the model extracted "a wheel true" rather than "wheel true", or an
  ownership check asked again because an email was extracted truncated.
- **Validation rarely fired:** only 31 replies (1.7%) needed a retry, mostly on production-change and password replies,
  and none was still failing after the retry.
- **Auto-pass by task type:** 100% on 14 of 20 types. The rest were deliberate hand-offs the policy requires, not
  failures:
  - complaints, 1%: compensation demands go to a person;
  - production changes, 0%;
  - unverified deletions, 55%;
  - unapproved or mismatched payments, 57%;
  - supplier queries, 76%: bank-detail changes escalate;
  - quotes, 78%: unlisted services, plus the extraction misses above.

  Judgement-heavy work didn't contract worse. It *escalated by design*, which is where it belongs.
- **Human minutes didn't halve under the normal trust policy (P2).** Both agents start Supervised, and each task type
  has to clear the same evidence floor (73 clean reviews at C2, 189 at C3). With only 75–100 tasks per type in this
  subset, most of every stream is the ramp-up in both arms. A safer agent can't climb faster than the floor allows.
- **Approving the procedure once and starting C1/C2 work at Trusted (P2b)** cut human minutes by 31% and took the share
  done without a person from 17% to 61%, with no serious escapes. It missed the 50% bar. The remaining minutes are
  spot-checks, C3 ramp-up and the policy's required hand-offs.
- **Cost didn't fall (P3).** Both arms use the same model. The playbook makes about 2 model calls per task (extraction and
  writing, about $0.00031 between them) against the free-form agent's 2.6 shorter ones (about $0.00030). Drafting adds
  $0.00006 per task over this subset. The writing call is two thirds of the runtime cost.

## How this fits with earlier findings

- **Fits:** "deterministic checks beat model judgement", now taken to its end point. With the decision and the facts in
  code, the measured serious error rate on this benchmark went to zero, and injection lost its target (free-form agents
  followed 29 injected instructions; scoped tools cut that to 10; playbooks to 0).
- **Fits the earlier contracts round:** there, contracts *learned from the agent's behaviour* copied its bad habits.
  Here, playbooks *approved from the written policy* don't. The approval step is what makes the code trustworthy.
- **New:** the trust evidence floor, not the agent's quality, is now the bottleneck on human time. Promotion is
  per-action evidence; a playbook earns its safety differently, by approval plus validation. **Starting approved
  playbooks higher on the ladder (P2b) is the lever,** and its safety held here.

## Limits

- **The approver wasn't blind to the task generator** (disclosed before the run). The approval used only the written
  policy, and every branch cites its rule, but an approver who knows how tasks are built is a bias toward this arm. A
  blind approver is the obvious replication.
- **The generated tasks are clean and structured.** Every needed value is in the message or the record. Real requests
  with ambiguous or missing values would escalate more.
- **The approval time (157 minutes for 20 task types) is an estimate,** not a timed human review. The 3× sensitivity is
  reported.
- **The subset is short** (75–100 tasks per type), so ramp-up dominates the minutes in every arm. On longer streams the
  approval cost amortises further, and the gap in time spent at Trusted and Senior would show more.
- **Both arms use one model.** The playbook doesn't yet use cheaper extraction (rules, a small model) or templated wording
  for routine replies, which is where its cost advantage would come from.
- **Review minutes per held or spot-checked action are 1.0 in every arm.** Checking a validated playbook action is
  likely faster than checking a free-form one, but that wasn't measured.

## Recommended next step

Keep approved playbooks as the default shape for recurring work, and make the trust ladder treat an approved, validated
playbook differently from a free-form agent:

1. **Pre-register an "approved start" rule:** approved playbooks begin C1/C2 task types at Trusted, with spot-checks and
   validation holds. Then test it on longer streams and with a blind approver.
2. **Cut cost where it is:** templated wording for routine informational replies, and rule- or small-model extraction for
   structured fields. Measure model cost per task again.
3. **Time real approvals** to replace the 157-minute estimate.
