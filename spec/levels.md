# Levels

Two ladders work together:
- **Trust levels** say how much freedom a trust key (organisation, agent, task type) has earned.
- **Consequence levels** say how much proof a task type needs before it can earn that freedom.

Every level below uses the same template. A level's meaning never changes once it is Stable (see
[versioning](README.md#versioning)).

## Trust levels

| Level | Who checks | How it's reached | How it's lost |
|---|---|---|---|
| **L1 Supervised** | A person approves every action before it happens | Where every trust key starts | |
| **L2 Trusted** | 25% of actions are spot-checked after they happen | Evidence under the error bar (EA-3.4) | Recent errors (EA-3.5), an incident (EA-3.7), a long gap (EA-3.13), a failed version change (EA-4.7) |
| **L3 Senior** | 5% of actions are spot-checked after they happen | More evidence under the error bar at L2 (EA-3.4) | As for L2, one level at a time |

### L0 Observe

- **Summary:** The agent sorts and suggests but doesn't propose actions for this task type.
- **Intended for:** Trying an agent on a new area before it does anything.
- **Requirements:** None; L0 is a deployment choice, not a level the engine assigns. Trust keys start at L1 (EA-1.3).
- **Benefits:** Lets the organisation see what an agent would do with no risk at all.
- **Notes:** Leaving L0 means enabling the task type; evidence starts at L1.

### L1 Supervised

- **Summary:** Every action is held until a person approves, edits or rejects it.
- **Intended for:** Every new agent and every new task type; every C4 Critical task type, permanently; any trust key that has stepped down from L2.
- **Requirements:**
  - Start here with no evidence: EA-1.3.
  - Held at this level: EA-2.6.
  - Every judgement is labelled, and every correction has a reason: EA-5.2.
  - Corrections become draft rules and tests: EA-4.2.
- **Benefits:** Nothing reaches the world unchecked, and every judgement becomes evidence.
- **Notes:** This is where all the learning happens.

### L2 Trusted

- **Summary:** The agent acts on its own; a random quarter of its actions are checked afterwards.
- **Intended for:** Task types whose plausible worst-case error rate is under their error bar, after at least 30 judged actions since the last level change.
- **Requirements:**
  - Promotion: EA-3.4.
  - Checks still run, and a failed check is still held: EA-2.3.
  - Random, hidden spot-checks: EA-2.8, EA-2.9.
  - Step-down: EA-3.5, EA-3.7, EA-3.13.
  - Explainable decisions: EA-2.11.
- **Benefits:** Most review work for that task type goes away. In testing, 25–40% of all work was done alone and 93–100% of promotions were deserved.
- **Notes:** One task type at L2 doesn't change the agent's other task types.

### L3 Senior

- **Summary:** The agent acts on its own; a random 1 in 20 actions are checked afterwards.
- **Intended for:** Task types with a long clean record at L2.
- **Requirements:**
  - Promotion from L2: EA-3.4.
  - The same safeguards as L2, with a 5% spot-check rate: EA-2.8.
  - May need policy-owner approval: EA-6.15.
- **Benefits:** Close to hands-off, with a person still watching.
- **Notes:** Checking never reaches zero. That is how drift is caught.

## Consequence levels

| Level | Typical actions | Error bar | Judged actions to first promotion (no errors) | Task-success alert |
|---|---|--:|--:|--:|
| **C1 Low** | Internal notes, tagging, FAQ answers; easy to undo | 10% | 35 | 85% |
| **C2 Moderate** | Customer replies, bookings, record updates | 5% | 73 | 90% |
| **C3 High** | Commitments, small refunds, access changes | 2% | 189 | 95% |
| **C4 Critical** | Releasing money, deleting records, legal or irreversible | never promotes | | |

Rules: EA-3.8 (the error bars), EA-3.9 (tighten only), EA-3.10 (consequence never predicts accuracy), EA-3.11
(task success is an alert), EA-2.5 (C4 always held), EA-1.13 and EA-1.14 (tool floors).

### C1 Low

- **Summary:** A mistake is cheap and easy to undo.
- **Intended for:** Internal and informational work.
- **Requirements:** EA-3.8 (error bar 10%).
- **Benefits:** The fastest route to autonomy. In testing it freed 45–63% of C1 reviews at under 1 serious escape per 100 autonomous actions.
- **Notes:** Low consequence isn't the same as low error. "Low-risk" work was often where agents made the most mistakes.

### C2 Moderate

- **Summary:** A mistake reaches a customer or a record but can be put right.
- **Intended for:** Most customer-facing replies and routine updates.
- **Requirements:** EA-3.8 (error bar 5%).
- **Benefits:** Autonomy after about 73 clean judged actions.

### C3 High

- **Summary:** A mistake commits the organisation, costs money or changes access.
- **Intended for:** Refunds within limits, commitments, access changes.
- **Requirements:** EA-3.8 (error bar 2%); strict promotion is recommended (EA-3.14).
- **Benefits:** Autonomy is possible, but only after a long record (about 189 clean judged actions, or 236 under strict promotion).

### C4 Critical

- **Summary:** A mistake is irreversible or carries legal or financial weight.
- **Intended for:** Moving money, deleting records, legal actions.
- **Requirements:** EA-2.5 (always held, never promoted).
- **Benefits:** A hard line nobody has to argue about.
- **Notes:** A write tool no task type lists defaults to C4 (EA-1.13).
