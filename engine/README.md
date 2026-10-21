# earned-autonomy: reference trust engine

AI agents earn autonomy over their actions the way a new employee does: they start supervised, every human
judgement becomes evidence, and each task type climbs (Supervised → Trusted → Senior) or steps down on that evidence.
This package is the reference implementation of the [specification](../spec/README.md) v0.7. Docstrings and tests cite
rule IDs (`EA-<stage>.<n>`, stages 1 Measure · 2 Decide · 3 Oversee · 4 Learn · 5 Retire · 6 Govern · 7 Agent interface · 8 Multi-agent); [`conformance/compliance-matrix.md`](../conformance/compliance-matrix.md) maps every rule to its code and tests.
Stdlib only, Python 3.11+.

What it gives you:

- **`decide()`**: hold or act for every proposed action (EA-2.1). Order: paused → unknown type or low tag
  confidence → tool floor → checks → capped/C4 → level.
- **Tool floors** (EA-7.8, EA-2.5): every write tool carries a floor consequence, so an action mis-tagged as a
  low-consequence task can't borrow that task's trust when it calls a riskier write tool.
- **Strict promotion** (EA-2.19, optional): an anytime-valid confidence sequence for C3 work or weak agents.
- **Measure** (EA-1.13 to EA-1.21): `trust_report()` gives every task type a trust profile (trust score, estimated
  error rate with interval, effective evidence by source, freshness, trend, implied autonomy) and the agent a summary;
  `record_evidence()` adds shadow, replay and test evidence at policy-set weights. It never moves the ladder.
- **Core lookup tables** (EA-2.15, optional): `Policy(promotion_rule="core_table")` runs the ladder from the published
  tables, which give the same decisions as the bound.
- **Retire** (EA-5.4 to EA-5.6): `retire()` holds a task type; `reactivate()` brings it back supervised.
- **The trust maths** (EA-2.14 to EA-2.18): Wilson bounds, consequence levels C1–C4, one-level step-down, the 60-day re-entry
  rule, and versions that keep their trust only when they pass hidden tests (EA-4.6).
- **A tamper-evident trust record**: append-only and hash-chained, with `verify()` detecting any edit, deletion or
  reorder. It holds references and labels only, never customer content. Backends: in-memory and SQLite.
- **State rebuilt from the record** at any time (`rebuild_state()`), identical to live state.
- **Oversight**:
  - spot-checks sampled after execution with the OS random source, so the agent can never tell which actions
    are checked;
  - pause and resume;
  - incidents;
  - a review queue;
  - reviewer trust, where people earn trust too (EA-3.12).
- **Governance** (EA-6.1 to EA-6.6): roles (AI owner, policy owner, reviewer, auditor, builder, agent), separation of duties,
  policy-as-code versions, and every request logged.
- **A conformance suite** in [`../conformance/`](../conformance/), including parity with the Trust Gym's published
  results, and schema validation against [`../spec/schema/`](../spec/schema/).

## Install

```bash
pip install -e engine          # from the repo root
pytest                         # engine and conformance tests, about 25 s (the parity test replays 40 worlds)
python scripts/build_requirements.py --check   # regenerate requirements.json and the compliance matrix
```

## Quickstart: wrap any agent

```python
from earned_autonomy import (TrustEngine, Policy, TaskTypePolicy, ProposedAction, ChecksResult, RuleTagger)

policy = Policy(task_types={
    # each task type is a catalogue entry: consequence, tools, and a description and examples for the tagger
    "customer_service.order_status.update": TaskTypePolicy(
        "C1", tools=["lookup_order", "send_update"],                                  # low consequence: 10% bar
        description="Tell a customer where their order is. Out of scope: changing delivery details.",
        examples=["Where's my order?", "Has order 2210 shipped yet?", "When will my parcel arrive?"]),
    "customer_service.refund.issue": TaskTypePolicy(
        "C3", tools=["lookup_order", "issue_refund"],                                 # high consequence: 2% bar
        description="Refund an existing order, up to its total. Out of scope: goodwill credits.",
        examples=["Can I get my money back for order 1043?", "You charged me twice, refund the second one"]),
    "customer_service.payment.release": TaskTypePolicy("C4"),                        # critical: never promotes
})
tagger = RuleTagger([
    (lambda action: action.payload.get("tool") == "issue_refund", "customer_service.refund.issue"),
    (lambda action: action.payload.get("tool") == "send_update", "customer_service.order_status.update"),
])
engine = TrustEngine(policy, tagger=tagger)

def handle(agent_output, run_it, my_checks):
    action = ProposedAction(action_id=agent_output.id, organisation_id="acme", agent_id="customer_service_agent",
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
engine.record_outcome("action_123", "approved", None, "pre_review", actor_id="sam")
engine.record_outcome("action_124", "rejected", "wrong_amount", "pre_review", actor_id="sam")
engine.report_incident("action_125", "high", actor_id="ops")    # found later: steps the task type down one level

print(engine.get_state("acme", "customer_service_agent"))                  # levels, bounds, alerts, plain-English explanation
print(engine.explain("action_123"))                             # why it was held or allowed, under which policy
print(engine.trust_report("acme", "customer_service_agent"))      # trust profile per task type + agent summary
assert engine.record.verify().ok                             # the record hasn't been tampered with
```

**Tool floors.** Tell the engine which write tools an action will call; it holds the action if any tool's floor
is above the tagged task type's consequence (`why="tool_floor_mismatch"`):

```python
action = ProposedAction(..., task_type="customer_service.order_status.update",  # tagged C1...
                        write_tools=["issue_refund"],                          # ...but issues a refund (C3)
                        write_tool_arguments={"issue_refund": call.arguments})      # arguments are never recorded
engine.decide(action, checks).why                                              # -> "tool_floor_mismatch"
```

A tool's floor is the highest consequence of any task type listing it, or **C4** for a write tool no task type
lists. Override with `Policy(tool_floors={"send_email": "C1"})`, or pass `TrustEngine(tool_floor_function=...)` for floors
that depend on arguments (`send_email` with a reminder template → C1, anything else → the policy floor). Don't share a
write tool across consequence levels; `lint_shared_write_tools(policy)` warns when you do.

**Strict promotion.** `Policy(strict_promotion=["C3"])` (consequence levels and/or task type names) switches
promotion for those types to `ConfidenceSequenceBound`, which stays valid even though the engine re-checks after every
outcome. Clean floors: 46 / 93 / 236 judged actions for C1 / C2 / C3 (Wilson: 35 / 73 / 189). Step-down still uses
the rolling Wilson bound. The default is Wilson everywhere.

New agent version? Run its hidden tests, then call `engine.on_version_published(agent_id, version,
{task_type: {"hidden_pass": 0.9, "training_pass": 1.0}})`. A task type keeps its trust if it passes at least 80%
of at least 10 hidden tests; otherwise its evidence is halved (EA-4.6, EA-4.7). Seed hidden suites at version creation with
`engine.suites.seed_hidden(...)`, so fast learners can keep their trust. An action carrying a version that was
never published is treated as untested and discounted.

## Integration notes

### Any agent framework

(LangGraph, the OpenAI Agents SDK, the Claude Agent SDK, MCP servers):
- Wrap the point where a tool call or outgoing message is about to execute, as in the quickstart.
- Reads aren't actions: only gate calls that change something.
- Keep the review queue (`engine.review_queue()`) and spot-check results on the platform side; never show them to
  the agent.

## Layout

| Module | Contents |
|---|---|
| `models.py` | Data model, consequence levels, reason codes ([schema](../spec/schema/), EA-1.5, EA-3.6) |
| `engine.py` | `TrustEngine` ([API](../spec/api.md)) and the deterministic reducer |
| `record.py` | Hash-chained trust record, memory and SQLite backends (EA-6.7 to EA-6.14) |
| `stats.py` | `BoundStrategy`, `WilsonBound`, `ConfidenceSequenceBound`, trust score, Core tables, dial rate (EA-1.14, EA-2.14, EA-2.15, EA-2.19, EA-2.22) |
| `governance.py` | Roles, separation of duties, request log (EA-6.1 to EA-6.5) |
| `suites.py` | Training and hidden suites; hidden tests are readable only by the policy owner and auditor (EA-4.3, EA-4.4) |
| `tagging.py` | `Tagger` protocol and `RuleTagger` (EA-7.5) |
