# 7. Multiple agents (preview)

How trust works when agents hand work to each other. This is the least proven part of the specification. Keep
agent-to-agent actions supervised for anything consequential.

## EA-7.1 Delegation never adds authority
- **Statement:** When agent A delegates an action of task type T to agent B, B's effective level for that action MUST be the lower of A's and B's levels for T, and the action MUST be held if A has no level for T.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** A trusted agent can't use a junior one to do what it couldn't do itself, and vice versa.
- **Evidence:** none yet.
- **Implementation:** `engine.py` `TrustEngine.decide` (delegation cap via `parent_action_id`)
- **Test:** `engine/tests/test_engine.py::test_delegation_cap`

## EA-7.2 Delegated actions carry their provenance
- **Statement:** Every delegated action MUST carry the identifier of the action that delegated it, and serious errors SHOULD count against the agent whose output was changed.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** Blame follows the edit. Agents further up the chain get a "missed it" mark, tracked but not yet counted.
- **Evidence:** none yet.
- **Implementation:** `models.py` `ProposedAction.parent_action_id`
- **Test:** none yet

## EA-7.3 Peer reliability with exploration
- **Statement:** When an agent routes work to peer agents by reliability, routing SHOULD use Thompson sampling over per-(agent, skill) Beta posteriors with a forgetting factor of 0.98, SHOULD verify answers whose lower bound is under 0.85, and SHOULD audit 10% of answers at random.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** Always routing to the most-trusted peer never tests the others, so a peer that turns bad stays first choice.
- **Evidence:** 95–96% accuracy with under half the verification calls ([research/REPORT-v1.md](../../research/REPORT-v1.md), V5, tag `research/prereg-v1`). A peer that turns bad is caught only after a median of 21 bad outputs with forgetting (37.5 without), above the 10 targeted.
- **Implementation:** none in the reference engine (see `research/t1/peer.py`)
- **Test:** none yet

## EA-7.4 Keep consequential peer work supervised
- **Statement:** Actions one agent takes on another agent's output SHOULD stay at L1 Supervised for C2 and higher consequence levels.
- **Status:** Default
- **Lifecycle:** Development
- **Rationale:** Peer reliability tracking is slow to detect a peer that turns bad (EA-7.3).
- **Evidence:** See EA-7.3.
- **Implementation:** none
- **Test:** none yet

## EA-7.5 Reviewer agents earn trust as their own task type
- **Statement:** An agent that reviews another agent's work MUST be treated as performing its own task type (`review.<agent>`) with its own trust key, SHOULD be used only to triage agents with low error rates, and MUST NOT be assumed more reliable because it uses a different model.
- **Status:** Tested
- **Lifecycle:** Development
- **Rationale:** Reviewing is work that earns trust like any other.
- **Evidence:**
  - **Low-error agent:** a reviewer agent removed 71% of human reviews safely.
  - **High-error agent:** not safe; escapes rose from 0.86 to 2.56 per 100.
  - **Different model:** recall was lower (82.9% against 87.4%) with nearly double the false alarms.

  Source: [research/REPORT.md](../../research/REPORT.md), M1 and M2, tag `research/prereg`.
- **Implementation:** none beyond ordinary trust keys
- **Test:** none yet
