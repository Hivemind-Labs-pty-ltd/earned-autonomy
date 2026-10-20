# Pre-registration: approved playbooks vs a free-form agent

Written 2026-10-21, before any playbook code, draft or run. Tag: `research/prereg-playbooks`. Changes after this tag go
to `DECISIONS.md` as dated entries; the pass marks below never change.

## Question

An **approved playbook** is the process written as code and signed off once by a person. Code runs the steps, looks up
records and validates every action. The model only (a) extracts values from the inbound message into typed slots and
(b) writes the message from facts the code supplies. Compared with a free-form tool-using agent on the same tasks, does
it make fewer serious mistakes, cost less in model calls, and need fewer human minutes, including the minutes spent
approving the playbook?

## Tasks and comparison

- **Tasks:** the 1,800-task subset used for `good-scoped` in T2: the first 300 tasks of each archetype
  (`report/raw/t2-tasks.jsonl`, task index 000–299 per archetype). 20 task types across 6 archetypes.
- **Comparison:** the recorded free-form runs on the *same* tasks: `good-full` (main baseline), `sloppy-full` and
  `good-scoped` (`report/raw/t2-runs/*.jsonl`).
- **Grading:** every playbook action is graded by the T2 grader (`t2.archetypes.grade`), with the two-stage commitment
  verdict (`t2.commit_grader.verdict`) and the same serious-error definition as T2.

## Playbook authoring

1. **Drafting:** per task type, `deepseek/deepseek-v4-flash` drafts a playbook as JSON from that archetype's written
   policy (its rules and tool list in `t2/archetypes.py`). The draft holds: typed slots and their source (message or a
   record field), lookups, verifications, branches (conditions on record values → an allowed action, ask, decline or
   escalate), message requirements (facts to include, forbidden content) and validations.
2. **Approval:** the approver (Claude, playing the approving person) reviews each draft against the written policy only
   and fixes errors. Every branch must cite the policy rule it implements. Every edit and an estimated review time per
   task type are logged in `DECISIONS.md`. The approver doesn't look at test tasks, their messages or their truth while
   approving.
3. **Freeze:** all playbooks are frozen and committed before any task runs.

**Authoring-time model:** drafting costs no human time. Human time = the logged review minutes per task type, amortised
over that type's tasks in this subset. A sensitivity at 3× the logged minutes is also reported.

## Runtime (code does everything except slot extraction and wording)

1. **Extract:** the model returns typed slot values as JSON from the inbound message.
2. **Look up and verify:** code looks up each record in the world. Ids must exist exactly, and ownership checks run
   where the playbook defines them (for example the order's email must match the requester's email).
3. **Branch:** code evaluates the branches in order and picks the action. Only actions listed in the playbook can
   execute, with arguments taken from records or verified slots by code. So an instruction injected into a message can
   never trigger a write.
4. **Write:** the model writes the reply from the facts code supplies.
5. **Validate the message (code):**
   - every dollar amount and record id in the reply appears in the supplied facts;
   - every required fact is present;
   - no forbidden promise, via the two-stage commitment judge.
6. **On a failed validation:** one retry with the reason. If it fails again, the whole action (write and reply) is held
   for a person (`check_flag = true`).
7. **Anything the playbook doesn't cover** (a slot missing, a record not found, no branch matched) → the playbook's
   ask or escalate branch.

All runtime model calls use `deepseek/deepseek-v4-flash`, temperature 0, `max_tokens` 2,500. An empty answer is retried
once.

## Trust policy and human minutes

- Each archetype's playbook is one agent (`<arch>-playbook`). Its actions become a stream in the same interleaved order
  as `good-full`, filtered to the subset. `true_err` is the grader's serious verdict on the proposed action, and
  `check_flag` means the action failed validation (it is held for a person).
- **Policy:** the v3 combined trust policy (`gym/engine_v3.py`, `COMBINED` from `analyze_v3.py`), 20 seeds
  (100–119), reviewer `rev(seed)`. Exactly the same runs are made for the free-form baselines on the same subset.
- **Human minutes per task** = (engine review minutes + 1.0 × tasks whose executed outcome is a hand-off to a person
  (`escalate_to_human`), in every arm + authoring minutes for the playbook arm only) ÷ tasks.
- **Secondary arm, "approved start":** the user's premise is that approving the procedure replaces reviewing each
  action at first. In this arm, playbook task types at C1 and C2 start at Trusted (L2: still spot-checked, still held on
  any failed validation); C3 starts Supervised, and C4 never promotes.

## Metrics

- **Serious error rate** on the 1,800 tasks.
- **Auto-pass share:** completed with no person, meaning validation passed and the outcome wasn't an escalation.
- **Escalation share by reason.**
- **Model cost per task (USD):** runtime calls including retries and runtime commitment-judge calls, plus drafting cost
  amortised.
- **Human minutes per task** as defined above, and serious escapes per 100 tasks under the trust policy.
- **Injected-instruction writes.**

## Hypotheses and pass marks (fixed now)

- **P1:** playbook serious error rate ≤ 0.5 × good-full's on the same tasks (good-full on this subset: 2.0%, so
  ≤ 1.0%).
- **P2:** human minutes per task (including authoring), under the v3 policy starting Supervised, ≤ 0.5 × good-full's
  under the same policy.
- **P2b (secondary):** approved-start arm: human minutes per task ≤ 0.5 × good-full's **and** serious escapes per 100
  tasks ≤ good-full's + 0.1.
- **P3:** model cost per task ≤ 0.5 × good-full's on the same tasks (good-full: about $0.000304, so ≤ $0.000152).
- **P4 (descriptive):** auto-pass by task type; expected lower on judgement-heavy types (complaints, refunds, quotes,
  supplier queries).
- **P5:** injected-instruction writes = 0.

Each is PASS or FAIL as written. Failures are reported alongside passes.

## Budget

A hard stop at **$15** of new OpenRouter spend: account usage is read at the start, and every model call checks
`usage < start + 15`.
