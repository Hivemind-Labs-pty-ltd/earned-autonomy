# Autonomy settings

The DECIDE stage turns what was measured into an **autonomy setting** for each trust key (organisation, agent, task
type): how much the agent may do alone, and how much a person checks.

- **Core: the ladder.** Three fixed settings (Supervised, Trusted, Senior), moved one step at a time by the lookup
  tables (EA-2.15) or the equivalent bound (EA-2.14).
- **Advanced: the dial.** A continuous setting computed from the trust score (EA-2.22).
- **Consequence levels** say how much proof a task type needs before it can earn any autonomy.

Every setting below uses the same template. A setting's meaning never changes once it is Stable (see
[versioning](README.md#versioning)).

## The Core ladder

| Level | Who checks | How it's reached | How it's lost |
|---|---|---|---|
| **L1 Supervised** | A person approves every action before it happens | Where every trust key starts | |
| **L2 Trusted** | 25% of actions are spot-checked after they happen | Evidence passes the lookup table (EA-2.15, EA-2.14) | Recent errors (EA-2.17), an incident (EA-2.18), a long gap (EA-5.1), a failed version change (EA-4.7) |
| **L3 Senior** | 5% of actions are spot-checked after they happen | More evidence under the error bar at L2 (EA-2.14) | As for L2, one level at a time |

### When the ladder moves

| Consequence | Judged actions needed to promote, by serious errors so far (0, 1, 2, … 10) | Step down when the last 50 judged hold |
|---|---|--:|
| C1 Low | 35, 53, 69, 84, 99, 113, 127, 140, 153, 166, 179 | 10 serious errors |
| C2 Moderate | 73, 110, 142, 173, 202, 230, 257, 284, 311, 337, 363 | 6 |
| C3 High | 189, 280, 361, 437, 510, 581, 650, 718, 785, 851, 916 | 3 |
| C4 Critical | never | |

- Promotion also needs at least 30 judged actions since the last change. More than 10 serious errors: don't promote.
- Any incident steps the trust key down one level at once (EA-2.18).
- The tables are the 95% Wilson rule written out, so a team without statistics code makes the same decisions
  (EA-2.15).

### L0 Observe

- **Summary:** The agent sorts and suggests but doesn't propose actions for this task type.
- **Intended for:** Trying an agent on a new area before it does anything.
- **Requirements:** None; L0 is a deployment choice, not a level the engine assigns. Trust keys start at L1 (EA-2.13).
- **Benefits:** Lets the organisation see what an agent would do with no risk at all.
- **Notes:** Leaving L0 means enabling the task type; evidence starts at L1.

### L1 Supervised

- **Summary:** Every action is held until a person approves, edits or rejects it.
- **Intended for:** Every new agent and every new task type; every C4 Critical task type, permanently; any trust key that has stepped down from L2.
- **Requirements:**
  - Start here with no evidence: EA-2.13.
  - Held at this level: EA-2.9.
  - Every judgement is labelled, and every correction has a reason: EA-3.5.
- **Benefits:** Nothing reaches the world unchecked, and every judgement becomes evidence.
- **Notes:** This is where all the learning happens.

### L2 Trusted

- **Summary:** The agent acts on its own; a random quarter of its actions are checked afterwards.
- **Intended for:** Task types whose plausible worst-case error rate is under their error bar, after at least 30 judged actions since the last level change.
- **Requirements:**
  - Promotion: EA-2.14.
  - Checks still run, and a failed check is still held: EA-2.6.
  - Random, hidden spot-checks: EA-3.1, EA-3.2.
  - Step-down: EA-2.17, EA-2.18, EA-5.1.
  - Explainable decisions: EA-2.12.
- **Benefits:** Most review work for that task type goes away. In testing, 25–40% of all work was done alone and 93–100% of promotions were deserved.
- **Notes:** One task type at L2 doesn't change the agent's other task types.

### L3 Senior

- **Summary:** The agent acts on its own; a random 1 in 20 actions are checked afterwards.
- **Intended for:** Task types with a long clean record at L2.
- **Requirements:**
  - Promotion from L2: EA-2.14.
  - The same safeguards as L2, with a 5% spot-check rate: EA-3.1.
  - May need policy-owner approval: EA-2.20.
- **Benefits:** Close to hands-off, with a person still watching.
- **Notes:** Checking never reaches zero. That is how drift is caught.

## The Advanced dial

- **Summary:** Instead of three fixed settings, oversight follows the trust score continuously.
- **Requirements:** EA-2.22. Pre-review every action while the trust score is below 0.975; above it, spot-check a
  share `clip(5 × (1 − score) + 0.02, 0.02, 1)` of actions (2% at a score of 1, 14.5% at 0.975). The Core step-down and
  incident rules still apply.
- **Benefits:** Smooth control. In simulation it was as safe as the ladder and caught regressions as fast, but saved
  only 1–7% more human time.
- **Notes:** Status Tested as safe; Core keeps the ladder because it's simpler and costs almost nothing.

## Decisions about an agent

When an owner reviews an agent or one of its task types (EA-5.3), the decision is one of (EA-2.21):

| Decision | What happens |
|---|---|
| Increase autonomy | Manual promotion by the policy owner (never the agent's builder) |
| Keep | Nothing changes; the review is recorded |
| Increase oversight | Step down, or raise the spot-check rate |
| Narrow scope | Split or narrow the task type; new task types start supervised (EA-5.5) |
| Improve | A new agent version (EA-4.1); its trust follows the Learn rules |
| Pause | Hold everything for the agent or task type (EA-3.9) |
| Retire | Stop the task type; every new action is held (EA-5.4) |

## Consequence levels

| Level | Typical actions | Error bar | Judged actions to first promotion (no errors) | Task-success alert |
|---|---|--:|--:|--:|
| **C1 Low** | Internal notes, tagging, FAQ answers; easy to undo | 10% | 35 | 85% |
| **C2 Moderate** | Customer replies, bookings, record updates | 5% | 73 | 90% |
| **C3 High** | Commitments, small refunds, access changes | 2% | 189 | 95% |
| **C4 Critical** | Releasing money, deleting records, legal or irreversible | never promotes | | |

Rules: EA-1.5 (the error bars), EA-1.6 (tighten only), EA-1.7 (consequence never predicts accuracy), EA-1.11
(task success is an alert), EA-2.8 (C4 always held), EA-7.8 and EA-2.5 (tool floors).

### C1 Low

- **Summary:** A mistake is cheap and easy to undo.
- **Intended for:** Internal and informational work.
- **Requirements:** EA-1.5 (error bar 10%).
- **Benefits:** The fastest route to autonomy. In testing it freed 45–63% of C1 reviews at under 1 serious escape per 100 autonomous actions.
- **Notes:** Low consequence isn't the same as low error. "Low-risk" work was often where agents made the most mistakes.

### C2 Moderate

- **Summary:** A mistake reaches a customer or a record but can be put right.
- **Intended for:** Most customer-facing replies and routine updates.
- **Requirements:** EA-1.5 (error bar 5%).
- **Benefits:** Autonomy after about 73 clean judged actions.

### C3 High

- **Summary:** A mistake commits the organisation, costs money or changes access.
- **Intended for:** Refunds within limits, commitments, access changes.
- **Requirements:** EA-1.5 (error bar 2%); strict promotion is recommended (EA-2.19).
- **Benefits:** Autonomy is possible, but only after a long record (about 189 clean judged actions, or 236 under strict promotion).

### C4 Critical

- **Summary:** A mistake is irreversible or carries legal or financial weight.
- **Intended for:** Moving money, deleting records, legal actions.
- **Requirements:** EA-2.8 (always held, never promoted).
- **Benefits:** A hard line nobody has to argue about.
- **Notes:** A write tool no task type lists defaults to C4 (EA-7.8).
