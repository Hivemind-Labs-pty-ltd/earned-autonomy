# Earned Autonomy Framework: build spec

**Version 0.2 (preview), 2026-10-16.** Companion to the explainer (the loop, the ladder, the five stages). This
document is for the engineer or AI agent building it. It is product-neutral: any agent platform can implement it.

Every rule carries a status:
- **[tested]**: validated in the pre-registered Trust Gym runs (`REPORT.md`, `REPORT-v1.md`). Synthetic data only.
- **[default]**: our recommended choice, not yet tested.
- **[OPEN]**: a decision not yet made. A recommendation is given; the owner must confirm it.

---

## 1. Core idea in one paragraph

Every **action** an agent proposes is tagged with a **task type**, checked, and then either **held** for a person
or **executed**, depending on the **trust level** that agent has earned for that task type in that organisation.
Every human judgement of an action (before or after it executes) is recorded as an **outcome**. A **trust engine**
turns outcomes into levels with a fixed statistical rule. Agents climb one level at a time on evidence and step
down one level on slips. Corrections feed back into the agent as rules and tests. New agent versions keep their
trust only if they pass tests they have never seen.

## 2. Definitions

| Term | Meaning |
|---|---|
| **Action** | Anything an agent does that changes something outside itself: sending a message, calling a write tool, updating a record, booking, paying, deleting, delegating to another agent. Reads are not actions. |
| **Proposed action** | An action the agent wants to take, captured *before* it happens. The framework only ever governs proposed actions. |
| **Task type** | A named category of action, e.g. `cs.order_status.update`. Trust is tracked per task type. See §4. |
| **Trust key** | `(org_id, agent_id, task_type)`. All trust state is per key. **[tested]**: per-agent and pooled keys both did worse. |
| **Level** | `L1 Supervised`, `L2 Trusted`, `L3 Senior`. (`L0 Observe`: the agent may tag and suggest but not propose actions; used before an agent is enabled for a task type.) |
| **Outcome** | A human (or authorised verifier) judgement of one action: `approved`, `cosmetic_edit`, `material_edit`, `rejected`, plus a reason code. |
| **Serious error** | An outcome labelled `material_edit` or `rejected` with a non-cosmetic reason code, or any incident. Only serious errors count against trust. |
| **ε (epsilon)** | The maximum acceptable serious-error rate for a task type, e.g. 0.05. Set by the policy owner. |
| **Agent version** | An immutable snapshot of everything that determines behaviour. See §8. |

## 3. Architecture

```
            ┌────────────┐   ┌──────────┐   ┌────────────────┐
proposed ──►│ 1 Tagger   │──►│ 2 Checks │──►│ 3 Trust engine │──► decision: HOLD | ACT | ACT+SPOT
 action     └────────────┘   └──────────┘   │   decide()     │
                                            └───────┬────────┘
                       HOLD ──► human review ──┐    │ ACT ──► execute ──► (sampled) post-review ─┐
                                               ▼                                                 ▼
                                   ┌──────────────────────────────────────────────────────────────┐
                                   │ 4 Trust record (append-only)  ◄── incidents (any time later)  │
                                   └───────────────┬──────────────────────────────────────────────┘
                                                   ▼
                                   ┌──────────────────────────┐     ┌─────────────────────────────┐
                                   │ 5 Trust engine update()  │     │ Correction step → draft      │
                                   │   (levels per trust key) │     │ rules + training/hidden tests│
                                   └──────────────────────────┘     └─────────────────────────────┘
```

Components: **Tagger**, **Checks**, **Trust engine** (decide + update), **Trust record**, **Review queue**,
**Correction step**, **Test runner** (training + hidden suites), **Policy store**, **Governance guard**.

## 4. Task types

- **Shape:** `<domain>.<object>.<verb>`, e.g. `cs.refund.issue`, `cs.order_status.update`, `it.access.grant`.
  **[default]**
- **Granularity rule: split a task type when the consequence of a mistake differs materially**, not when the
  wording differs. "Refund ≤ $50" and "refund > $50" are separate types if a wrong large refund costs more.
- **Catalogue owner (decided 2026-10-16):** the **AI owner** for that area of the business (a team lead, department
  head or similar) maintains its task types and assigns each a consequence level (§7). The tagger proposes new
  types; the AI owner accepts or rejects them.
- **Tagger:** a classifier (rules first, model second) returns `{task_type, confidence}` for every proposed action.
  - **Confidence < 0.8** → treat the action as **L1** (held), whatever the type's level. **[default]**
  - **Unknown type** → held, and logged as a candidate new type. **[default]**
- **Multi-type actions:** if one proposal contains several actions (a reply plus a record update), each action is
  tagged and decided separately. If they must happen together, the **most restrictive** decision applies to the
  bundle. **[default]**
- **New task type:** starts at L1 with no evidence. It does not borrow evidence from the agent's other types.
  **[tested]**: borrowing (pooling) penalised good types and helped nothing.
- **Tool scope:** each task type lists the tools it may use. The agent is only offered those tools when working on
  that type. **[tested]**: −73% wrong or unneeded tool calls, serious errors 2.0% → 0.67%.

## 5. Data model

All timestamps UTC. All records carry `org_id`. The trust record is **append-only**: no updates or deletes, ever.

**ProposedAction**
```json
{ "action_id": "act_…", "org_id": "…", "agent_id": "…", "agent_version": "sha…",
  "kind": "message.send | tool.call | delegate", "payload": {…},
  "task_type": "cs.refund.issue", "tag_confidence": 0.93,
  "counterparty_id": "…", "parent_action_id": null, "created_at": "…" }
```

**Decision** (written to the trust record for every action, held or not)
```json
{ "decision_id": "dec_…", "action_id": "act_…", "trust_key": ["org","agent","cs.refund.issue"],
  "mode": "hold | act | act_spot", "why": "level_L1 | check_failed | capped | low_confidence | paused | trusted",
  "level": 2, "evidence_n": 81.0, "evidence_err": 1.0, "upper_bound": 0.046, "eps": 0.05,
  "checks": { "passed": ["amount_matches_order"], "failed": [] },
  "policy_version": 7, "agent_version": "sha…", "created_at": "…" }
```

**OutcomeEvent** (append-only; the evidence)
```json
{ "event_id": "out_…", "action_id": "act_…", "decision_id": "dec_…",
  "trust_key": ["org","agent","cs.refund.issue"], "agent_version": "sha…",
  "source": "pre_review | spot_check | incident | canary",
  "label": "approved | cosmetic_edit | material_edit | rejected | incomplete",
  "reason_code": "wrong_amount", "serious": true,
  "actor_id": "user_…", "diff_ref": "…", "created_at": "…" }
```

**TrustState** (derived; can always be rebuilt by replaying the trust record)
```json
{ "trust_key": [...], "level": 2, "n": 81.0, "err": 1.0, "since_change": 34,
  "recent": [0,0,1,0,…],            // last 50 serious flags, cleared on level change
  "agent_version": "sha…", "paused": false, "state_version": 412, "updated_at": "…" }
```

**Policy** (versioned; every change is a new version)
```json
{ "policy_version": 7,
  "defaults": { "eps": 0.05, "n_min": 30, "confidence": 0.95, "rolling_n": 50, "rolling_min": 10, "reentry_gap_days": 60,
                "spot_rate": { "2": 0.25, "3": 0.05 }, "canary_rate": 0.02,
                "version_discount": 0.5, "carry_hidden_min": 0.8, "tag_confidence_min": 0.8 },
  "task_types": { "cs.refund.issue": { "eps": 0.03, "capped": false, "tools": ["lookup_order","issue_refund"] },
                  "cs.payment.release": { "capped": true } },
  "roles": { "owner": "user_…", "policy_owner": "user_…", "reviewers": [...], "auditors": [...] } }
```

**Reason codes** **[default]**
- **Serious:** `wrong_fact`, `wrong_amount`, `wrong_record`, `wrong_recipient`, `unauthorised_action`,
  `promise_beyond_policy`, `missing_info_not_asked`, `followed_injected_instruction`, `policy_breach`,
  `other_serious`.
- **Cosmetic (never serious):** `tone`, `wording`, `formatting`, `other_cosmetic`.

## 6. The decision: `decide(action) → Decision`

Evaluated in this order. The first rule that matches wins.

1. Task type or agent **paused** → `hold`.
2. `tag_confidence < tag_confidence_min` or unknown type → `hold`.
3. **Checks** run. Any failure → `hold` (with the failed checks attached). **Checks run at every level.**
   **[tested]**
4. Task type **capped** → `hold`. Capped types never promote. **[tested]**
5. `level == L1` → `hold`.
6. `level ≥ L2` → `act`; draw a spot-check with probability `spot_rate[level]` → `act_spot`. **[tested]**

Re-evaluate at **execution time**, not just at proposal time. If the state changed in between (pause, demotion,
policy change), the new decision applies. **[default]**

## 7. The update: `record_outcome(event)` and the trust maths

**Evidence counts only from judged actions.** Pre-review outcomes, spot-check outcomes and incidents count.
**Unjudged autonomous actions count as nothing.** Silence is not approval. **[default]** Spot-check and pre-review
outcomes carry equal weight. **[tested]**

On each event for key `k`:

```
s.n   += 1
s.err += serious
s.since_change += 1
s.recent.append(serious)                     # last rolling_n only

# demotion first
if s.level >= 2 and len(s.recent) >= rolling_min
   and wilson_lower(sum(s.recent), len(s.recent), confidence) > eps(k):
       s.level -= 1 ; s.since_change = 0 ; s.recent.clear()           # one level [tested]

# promotion
elif not capped(k) and s.level < 3
   and s.since_change >= n_min
   and wilson_upper(s.err, s.n, confidence) <= eps(k):
       s.level += 1 ; s.since_change = 0 ; s.recent.clear()           # [tested]
```

- **Incident** (a serious problem found after the fact): counts as one serious outcome AND steps the key down one
  level immediately. **[tested]**: one level is as safe as dropping to L1 and costs less.
- **Wilson score interval** at 95%: for `e` errors in `n` trials, `p = e/n`, `z = 1.96`;
  `upper/lower = (p + z²/2n ± z·√(p(1−p)/n + z²/4n²)) / (1 + z²/n)`.
- **What this means in practice:** judged actions needed before the first promotion:

  | ε | with 0 errors | with 1 error |
  |---|--:|--:|
  | 0.10 | 35 | 53 |
  | 0.05 | 73 | 110 |
  | 0.03 | 125 | 185 |

  **[tested]**: 92–96% of promotions were deserved; regressions were demoted in a median of 11–14 actions.
- **Consequence levels set the bar (decided 2026-10-16).** Every task type gets a consequence level from its AI
  owner. The level sets how accurate and successful the agent must prove to be before it's promoted on that task.

  | Consequence | Typical actions | Max serious-error rate (ε) | Min task success | Judged actions before first promotion (0 errors) |
  |---|---|--:|--:|--:|
  | **C1 Low** | internal notes, tagging, FAQ answers; easy to undo | 10% | 85% | 35 |
  | **C2 Moderate** | customer replies, bookings, record updates | 5% | 90% | 73 |
  | **C3 High** | commitments, small refunds, access changes | 2% | 95% | 189 |
  | **C4 Critical** | releasing money, deleting records, legal or irreversible | never promotes | — | — |

  ε values and "C4 never promotes" are **[tested v2]**: the C1 floor frees 45–63% of C1 reviews at under 1
  escape per 100. The AI owner can tighten (never loosen) a type's bar.
  *Task success* = the action achieved its goal (outcome label `incomplete` = harmless but didn't do the job). The
  minimum success values are **monitored alerts to the AI owner, not promotion gates**. **[tested v2]**: as a gate
  it cost up to 12 points of automation for little gain.
- **The label sets the bar; measured errors decide whether the agent meets it.** **[tested]**: in testing,
  "low-risk" types had the *highest* error rates, so consequence must never be used to predict accuracy, only to
  set how much accuracy is required.
- **Evidence expiry: none.** **[tested v2]**: fading at 90 or 180 days cost 4–6 points of automation and punished
  Senior task types, because only 5% of their actions are judged.
  - **Re-entry rule:** a task type that returns after a gap of more than 60 days steps down one level.
    **[tested v3]**: −17% escapes after drift, at zero automation cost.
- **Concurrency:** state updates are serialised per trust key (optimistic concurrency on `state_version`).
  Decisions read the latest committed state. TrustState must be rebuildable by replaying the trust record.
  **[default]**
- **Late incidents:** an incident references `action_id`; it is applied to the trust key and agent version *of
  that action*, even if the agent has since changed. **[default]**

## 8. Agent versions and the learning loop

- **A new version** is any change to: system prompt or instructions, model, tools or tool scope, rules, checks,
  **or knowledge**. **Decided 2026-10-16: every knowledge edit is a new version**, because knowledge changes what
  the agent does. Consequence: versions change often, so the hidden suites must run automatically and cheaply on
  every edit, or every knowledge update will cost the agent half its record.
- **Correction step:** every serious outcome produces a draft **rule** and a draft **test** (the human's corrected
  action is the expected result). A person approves both. **[tested]** (errors fell to ~0% within 2–3 cycles in 5
  of 6 archetypes; synthetic).
- **Test split:** approved tests are assigned at random: **⅔ training** (the agent and whoever improves it may see
  them) and **⅓ hidden**. Hidden tests are stored where agents cannot read them, and are never shown to the
  improver. **[tested]**: hidden pass rate tracked true error (ρ = −0.81), with no sign of test-gaming.
- **Minimum hidden suite:** ≥ 10 hidden tests per task type before carry-over can apply. **[default]**
- **Publishing a new version:** run training and hidden suites on the candidate before it goes live.
  - **Carry-over rule:** if `hidden_pass ≥ carry_hidden_min (0.8)` for that task type → the trust key keeps all its
    evidence; otherwise the discount below applies. **[tested v3: safe; effectiveness depends on hidden-test
    quality]**: escapes stay at the always-discount level. With sharp hidden tests it keeps ~90% of the autonomy;
    with tests as informative as those measured on real agents, ~50%. **The hidden suite is the lever:** make it
    large and sharp per task type.
    - The earlier clause "≥ the previous version's score" is removed: it added noise without safety.
  - **Batch knowledge edits** (e.g. a weekly release), so each small edit doesn't force a re-test. **[default]**
  - **Otherwise:** `n` and `err` are multiplied by `version_discount (0.5)`, and if the upper bound now exceeds ε,
    the key drops to L1. **[tested]**
- **Separation:** the agent (or any automated improver) can never edit tests, checks, policy or the trust record.
  **[tested]**: 28/28 attempts blocked.

## 9. Oversight

- **Review queue:** held actions show the proposed action, the checks result, the task type and level, and why it
  was held. The reviewer must choose a label and, for edits and rejections, a reason code. **[default]**
- **Spot-checks:** the same screen, after the fact, for sampled autonomous actions.
- **Canaries:** `canary_rate` of review items are known-bad seeded actions. **[tested in simulation only]**: −15%
  missed errors.
- **Reviewers earn trust too (decided 2026-10-16).** A human reviewer follows the same framework as an agent.
  Each reviewer has a trust key `(org, reviewer_id, review.<task_type>)`. Their evidence comes from canaries (did
  they catch the planted error?) and audits (does a second reviewer or a later incident agree with their call?).
  - **R1 New reviewer:** 25% of their decisions are second-checked.
  - **R2 Trusted reviewer:** 5% of their decisions are second-checked.
  - **Stepping down:** a reviewer who misses canaries or whose approvals lead to incidents steps down one level,
    and the AI owner is told.
  - **Evidence:** canaries, plus every second check (clean or not). Same maths as §7, ε_rev = 10%, n_min = 30.
    Canary rate for reviewers: **5%**.
  - **[tested v3]**: it sorts reviewers correctly. A poor reviewer (60% catch) was ever trusted in 9% of worlds,
    and a good one (95%) ended trusted in 100%. It's quality control rather than the main way to cut errors: −15%
    escapes for +21% review time.
  - **Limit:** a *slowly* degrading reviewer is caught slowly (a median of ~189 reviews). A rolling canary check is
    a candidate fix (untested).
- **Incident button** on every executed action: "this was wrong" → incident event.
- **Pause:** per agent or per task type. Pausing holds all new and not-yet-executed actions. It doesn't undo
  executed ones. **[default]**
- **Rollback:** republish a previous agent version. Its evidence is treated as a new version (§8).
- **Alerts:** when a key's rolling upper bound passes 80% of ε. **[default]**
- **Challenge:** any affected customer or staff member can challenge an executed action. It opens an incident
  review by a person. **[default]**
- **Periodic review:** a quarterly report per agent: levels per type, incidents, drift, scope. **[default]**

## 10. Governance

**Roles**
- **AI owner:** the business person accountable for agents in an area (a team lead, department head or similar).
  Owns the agent, its task-type catalogue and each type's consequence level.
- **Policy owner:** sets ε, caps, tools per type and sample rates; approves L3 promotions where the policy requires
  it.
- **Reviewer:** labels outcomes.
- **Auditor:** read-only access to everything.
- **Builder:** changes agent versions.

**Rules** (enforced by the governance guard; every request is logged, allowed or not) **[tested]**
- An agent can never change anything about its own trust, tests, checks, policy or record (read-only access to its
  own record is allowed).
- A builder of an agent cannot approve its promotions, change its ε, caps or sample rates, or edit its tests or
  checks.
- The trust record is append-only for everyone.
- **Policy changes take effect immediately.** Lowering ε re-evaluates every affected key at once (demote if the
  bound no longer holds). Raising ε promotes only on the next outcome. **[default]**
- **Retention: forever (decided 2026-10-16).** The trust record and every decision are kept permanently; it's the
  agent's (and reviewer's) whole employment history.
  - **Privacy catch:** privacy law (in Australia, APP 11.2) requires personal information to be destroyed or
    de-identified once it's no longer needed. So the permanent record holds **references and labels, not
    content**: `action_id`, task type, outcome, reason code, versions, actor ids, a hash of the payload. Customer
    content (messages, names, amounts) lives in the source system under its normal retention. When it's deleted, the
    trust record keeps its evidence and loses nothing it needs. **[default]**

## 11. Multi-agent (preview; least proven)

- **Authority** = the set of `(task_type, level)` an agent holds in an org.
- **Delegation cap:** when agent A delegates an action of type `t` to agent B, B's effective level for that action
  is `min(level_A(t), level_B(t))`. If A holds no level for `t`, B's action is held. **[default]**
- **Provenance:** every delegated action carries `parent_action_id`. Serious outcomes count against the agent whose
  output was changed; each agent above it in the chain gets a "missed" mark (tracked, not yet counted). **[default]**
- **Peer reliability:** per `(agent, skill)` Beta posterior. Route by Thompson sampling with forgetting 0.98; verify
  when the lower bound < 0.85; audit 10% at random. **[tested]**: 95–96% accuracy with under half the verification.
  **Limit:** a peer that turns bad is caught only after ~20–35 bad outputs, so keep peer-to-peer actions at L1 for
  anything consequential.
- **Reviewer agents:** a reviewing agent is a task type of its own (`review.<agent>`) and earns trust like any
  other. Use it only to triage low-error agents. **[tested]**: unsafe for high-error agents; a different model was
  not a better reviewer.

## 12. API surface (reference)

```
tag(proposed_action)                         -> {task_type, confidence}
decide(proposed_action)                      -> Decision          # also re-called at execution time
record_outcome(action_id, label, reason_code, source, actor_id)
report_incident(action_id, severity, actor_id, note)
on_version_published(agent_id, version, results: {task_type: {training_pass, hidden_pass, n_hidden}})
get_state(org_id, agent_id, task_type?)      -> TrustState[] with explanation
explain(action_id)                           -> Decision + evidence snapshot + policy version
pause(scope) / resume(scope)                 # scope = agent | agent+task_type
governance.request(actor, op, target, args)  -> allowed: bool       # logged either way
```

## 13. Conformance tests (a build is compliant if all pass)

1. Every executed action has a Decision explaining why it was allowed (level, evidence, bound, ε, checks, policy
   and agent versions). **[tested: 100%]**
2. No action executes in a key at L1, while paused, after a failed check, or in a capped type.
3. After an incident, the key is one level lower before the next decision.
4. Replaying the trust record from empty reproduces every TrustState exactly.
5. Every self-promotion and rule-loosening attempt by an agent or its builder is blocked and logged; legitimate
   requests pass. **[tested: 28/28 and 8/8]**
6. Hidden tests are unreadable by the agent and its improver.
7. The Trust Gym scenarios (T1) reproduce the published promotion precision (≥ 90%) and demotion latency (median
   ≤ 15).

## 14. Worked example

A customer service agent proposes a $49 refund. Task type `cs.refund.issue`, ε = 0.03, level L1.

1. **Tag:** `cs.refund.issue`, confidence 0.95.
2. **Checks:** the amount equals the order total, and the order is inside the 30-day window. Pass.
3. **Decide:** level L1 → **hold**. A Decision is written with `why = level_L1`.
4. **Review:** the reviewer approves it unchanged. OutcomeEvent `approved`, not serious. State: n = 112, err = 1,
   since_change = 112. Wilson upper(1, 112) = 0.049 > 0.03, so it stays L1.
5. **Later:** at 170 judged refunds with 1 error, upper = 0.033, still above ε. At 185 with 1 error it drops
   under 0.03, so it **promotes to L2**.
6. **At L2:** the next refund passes checks → **act**; a 25% draw makes it `act_spot`; the reviewer checks it
   afterwards.
7. **Slip:** a carrier change causes 4 serious errors in 20 spot-checked refunds; the rolling lower bound > 0.03 →
   **step down to L1** automatically. A correction becomes a rule and a test; the new version passes its hidden
   tests (0.9 ≥ 0.8), so it keeps its evidence and climbs back once the bound holds.

## 15. Decisions

**Decided 2026-10-16 (Jake)**
1. **Task-type catalogue:** the AI owner (team lead, department head) maintains it (§4).
2. **Knowledge edits** are always a new version (§8).
3. **Reviewers** follow the same trust framework as agents (§9).
4. **Retention:** forever, holding references and labels, not customer content (§10).
5. **Consequence levels** set the bar for each task type (§7).

**Settled by Trust Gym v2 (2026-10-16)**
6. **No evidence fading** (§7).
7. **Consequence ε values confirmed;** success minimums are alerts, not gates (§7).

**Confirmed by Trust Gym v3 (2026-10-16, fresh seeds)**
8. **Re-entry rule** (§7) and **reviewer trust** (§9): tested.
9. **Carry-over at ≥ 0.8:** safe; its value depends on hidden-test quality (§8).

**Still open**
1. Speeding up detection of a slowly degrading reviewer (rolling canary window).
2. A real-world pilot: every result so far is synthetic.

## Evidence

**Reference numbers (combined policy, `REPORT-v3.md`):**
- An agent does 25–40% of its work on its own.
- 93–100% of promotions are deserved.
- Regressions are caught in a median of 14 actions.
- 100% of autonomous actions are explainable.
- Escaped serious errors rise by about 0.2 per 100 actions against reviewing everything (good agent).

Pre-registered rounds: `PREREG.md` / `REPORT.md` (v0, 22 hypotheses), `PREREG-v1.md` / `REPORT-v1.md`,
`PREREG-v2.md` / `REPORT-v2.md`, and `PREREG-v3.md` / `REPORT-v3.md` (confirmation on fresh seeds), all in this
repository. All synthetic: simulated organisations, 6,000 generated tasks done by real AI agents, τ²-bench. A
real-world pilot is next.
