# earned-autonomy: reference trust engine

AI agents earn autonomy over their actions the way a new employee does: they start supervised, every human
judgement becomes evidence, and each task type climbs (Supervised → Trusted → Senior) or steps down on that evidence.
This package is the reference implementation of [SPEC.md](../SPEC.md) v0.2. Stdlib only, Python 3.11+.

What it gives you:

- **`decide()`**: hold or act for every proposed action (SPEC §6). Order: paused → tag confidence → checks →
  capped/C4 → level.
- **The trust maths** (§7): Wilson bounds, consequence levels C1–C4, one-level step-down, the 60-day re-entry
  rule, and versions that keep their trust only when they pass hidden tests (§8).
- **A tamper-evident trust record**: append-only and hash-chained, with `verify()` detecting any edit, deletion or
  reorder. It holds references and labels only, never customer content. Backends: in-memory and SQLite.
- **State rebuilt from the record** at any time (`rebuild_state()`), identical to live state.
- **Oversight**:
  - spot-checks sampled after execution with the OS random source, so the agent can never tell which actions
    are checked;
  - pause and resume;
  - incidents;
  - a review queue;
  - reviewer trust, where people earn trust too (§9).
- **Governance** (§10): roles (AI owner, policy owner, reviewer, auditor, builder, agent), separation of duties,
  policy-as-code versions, and every request logged.
- **A conformance suite** (§13), including parity with the Trust Gym's published results.

## Install

```bash
pip install -e engine          # from the repo root
pytest engine                  # 45 tests, about 20 s (the Trust Gym parity test replays 40 worlds)
```

## Quickstart: wrap any agent

```python
from earned_autonomy import (TrustEngine, Policy, TaskTypePolicy, ProposedAction, ChecksResult, RuleTagger)

policy = Policy(task_types={
    "cs.order_status.update": TaskTypePolicy("C1", tools=["lookup_order"]),         # low consequence: 10% bar
    "cs.refund.issue":        TaskTypePolicy("C3", tools=["lookup_order", "issue_refund"]),  # high: 2% bar
    "cs.payment.release":     TaskTypePolicy("C4"),                                  # critical: never promotes
})
tagger = RuleTagger([(lambda a: a.payload.get("tool") == "issue_refund", "cs.refund.issue"),
                     (lambda a: a.payload.get("tool") == "send_update", "cs.order_status.update")])
engine = TrustEngine(policy, tagger=tagger)

def handle(agent_output, run_it, my_checks):
    action = ProposedAction(action_id=agent_output.id, org_id="acme", agent_id="cs-agent",
                            agent_version=agent_output.version, kind="tool.call", payload=agent_output.call)
    engine.tag(action)                                       # 1 tag (also offers only engine.tools_for(type))
    checks = my_checks(action)                               # 2 your pre-send checks -> ChecksResult
    decision = engine.decide(action, checks)                 # 3 hold or act
    if decision.allowed:
        run_it()                                             # 4 act
        engine.mark_executed(action.action_id)               #   may be spot-checked later; the agent never knows
    else:
        send_to_review_queue(action, decision.why)           # 4 hold: a person approves, edits or rejects

# 5 record every human judgement; this is the evidence trust is built from
engine.record_outcome("act_123", "approved", None, "pre_review", actor_id="sam")
engine.record_outcome("act_124", "rejected", "wrong_amount", "pre_review", actor_id="sam")
engine.report_incident("act_125", "high", actor_id="ops")    # found later: steps the task type down one level

print(engine.get_state("acme", "cs-agent"))                  # levels, bounds, alerts, plain-English explanation
print(engine.explain("act_123"))                             # why it was held or allowed, under which policy
assert engine.record.verify().ok                             # the record hasn't been tampered with
```

New agent version? Run its hidden tests, then call `engine.on_version_published(agent_id, version,
{task_type: {"hidden_pass": 0.9, "training_pass": 1.0}})`. A task type keeps its trust if it passes at least 80%
of at least 10 hidden tests; otherwise its evidence is halved. Seed hidden suites at version creation with
`engine.suites.seed_hidden(...)`, so fast learners can keep their trust. An action carrying a version that was
never published is treated as untested and discounted.

## Integration notes

**10x (hivemind) platform** (description only; nothing in 10x is changed by this package):
- The natural hook is post-generation routing (`Services/post_generation_routing.route_response`), after the
  pre-send checks (`message_checks.run_checks` → `ChecksResult`) and before delivery. `decide()` replaces the
  per-agent `response_mode` switch with a per-task-type decision. `hold` maps to the existing pending-approval path
  (`set_pending_approval` / approval items). `act` maps to send.
- The approve, edit and reject handlers (`approve_invocation`, `reject_invocation`, `action_item`) call
  `record_outcome`. They need a reason code on reject and edit; today reject takes no reason.
- Bundle publishes (`agent_definitions.publish_version`) call `on_version_published` with the test runner's
  training and hidden pass rates. Knowledge edits count as new versions (SPEC §8).
- Tool scope: filter the bundle's tool grants with `engine.tools_for(task_type)`. This is what `ToolGrant.when`
  intends; it isn't enforced today.
- 10x has no task-type key yet. A tagging step (rules first, a named LLM call second) is the first thing to add.

**Any agent framework** (LangGraph, the OpenAI Agents SDK, the Claude Agent SDK, MCP servers):
- Wrap the point where a tool call or outgoing message is about to execute, as in the quickstart.
- Reads aren't actions: only gate calls that change something.
- Keep the review queue (`engine.review_queue()`) and spot-check results on the platform side; never show them to
  the agent.

## Layout

| Module | Contents |
|---|---|
| `models.py` | Data model, consequence levels, reason codes (§5, §7) |
| `engine.py` | `TrustEngine` (§6–§12) and the deterministic reducer |
| `record.py` | Hash-chained trust record, memory and SQLite backends (§5, §10) |
| `stats.py` | `BoundStrategy` interface and `WilsonBound`. Swap in an anytime-valid confidence sequence here |
| `governance.py` | Roles, separation of duties, request log (§10) |
| `suites.py` | Training and hidden suites; hidden tests are readable only by the policy owner and auditor (§8) |
| `tagging.py` | `Tagger` protocol and `RuleTagger` (§4) |
