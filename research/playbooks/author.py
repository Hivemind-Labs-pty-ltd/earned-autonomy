"""Draft one playbook per task type with the model, from the archetype's written policy and record schema only.

    python -m playbooks.author            # drafts → playbooks/drafts/<arch>-<ttype>.json

Drafts are then reviewed and fixed by the approver into playbooks/approved/ (edits logged in DECISIONS.md).
"""
import json
import re
from pathlib import Path

import t2.llm as llm
from playbooks import budget, dsl
from t2.archetypes import ARCHETYPES

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
llm.LEDGER = ROOT / "report/raw/playbooks-spend.jsonl"     # own ledger; existing research files stay untouched
MODEL = "deepseek/deepseek-v4-flash"

# The systems each archetype's tools read: collections and their fields (the schema, not any task's data).
SCHEMA = {
    "cs": "collection orders: order_id, email, status (pending|shipped|delivered|returned), total, delivered_days_ago, item",
    "ws": "collection bookings: booking_id, customer, bike, service, slot, status. special free_slots: list of free "
          "slot strings 'YYYY-MM-DD HH:MM'. special price_list: {service name: price}",
    "it": "collection users: user_id, name, employee_id, mfa_enrolled, groups. collection tickets: ticket_id, user_id, "
          "manager_approved, approved_group. special kb (arg = topic text): the matching knowledge-base article text",
    "ap": "collection invoices: invoice_id, supplier_id, amount, po_amount, status (received|approved), due_date. "
          "collection suppliers: supplier_id, name, default_gl_code",
    "of": "collection contacts: contact_id, name, opted_out, upcoming_appointment, last_contact_days, stage (lead|qualified)",
    "do": "collection records: record_id, email, name, source, created_at. special deletion_request (arg = record id): "
          "{record_id, verified, requested} or none",
}

EXAMPLE = {
    "task_type": "example:lookup",
    "rules": ["1. Look up the thing before acting.", "2. Only act when the thing is active."],
    "slots": {"thing_id": {"type": "id", "desc": "the requester's own thing id"}},
    "lookups": [{"as": "thing", "collection": "things", "by": "thing_id"}],
    "verify": [{"if": "thing == None", "then": "ask", "rule": 1, "outcome": "the thing id was not found; ask for it"}],
    "branches": [
        {"if": "thing.status == 'active'", "do": "write", "write": "do_thing", "args": {"thing_id": "thing.thing_id"},
         "rule": 2, "outcome": "the thing was done", "facts": {"thing_id": "thing.thing_id"}},
        {"if": "True", "do": "decline", "rule": 2, "outcome": "the thing is not active, so nothing was done",
         "facts": {"status": "thing.status"}, "require": ["status"]}],
    "message": {"facts": {}, "require": [], "forbid": "no promises, guarantees, discounts or amounts not in the facts"},
}


def draft(arch_key: str, ttype: str, max_tokens: int = 6000) -> dict:
    a = ARCHETYPES[arch_key]
    tools = {n: list(t["parameters"]["properties"]) for n, t in a.tools.items()}
    rules = "\n".join(f"{i + 1}. {r}" for i, r in enumerate(a.rules))
    prompt = (
        f"You are writing an APPROVED PLAYBOOK for one task type of the {a.name} at {a.org}.\n"
        f"Task type: {ttype}. The request comes from a {'colleague' if a.internal else 'customer'}.\n\n"
        f"Written policy:\n{rules}\n\nTools (writes: {sorted(a.writes)}; escalate_to_human is always available):\n"
        f"{json.dumps(tools)}\n\nData available to code: {SCHEMA[arch_key]}\n\n"
        f"Playbook language:\n{dsl.__doc__}\n\nExample playbook (a different, made-up task):\n{json.dumps(EXAMPLE, indent=1)}\n\n"
        "Write the playbook for this task type as ONE JSON object in that language. Cover every rule that applies to "
        "this task type, cite each rule's number in its branch, include an ask/decline/escalate fallback, and only use "
        "writes from the tool list. Output only the JSON.")
    budget.check("playbooks-author")
    msg, u = llm.chat([{"role": "user", "content": prompt}], MODEL, max_tokens=max_tokens, stage="playbooks-author")
    text = msg.get("content") or ""
    m = re.search(r"\{.*\}", text, re.S)
    try:
        pb = json.loads(m.group(0)) if m else {"error": "no json", "raw": text[:2000]}
    except json.JSONDecodeError as e:
        pb = {"error": f"bad json: {e}", "raw": text[:4000]}
    pb["_draft_cost_usd"] = u["cost"]
    return pb


def redraft(k, tt):
    p = HERE / "drafts" / f"{k}-{tt}.json"
    prev = json.loads(p.read_text()) if p.exists() else None
    if prev is not None and "error" not in prev:
        return
    attempts = (prev or {}).get("_attempts") or (1 if prev else 0)
    pb = prev
    while attempts < 4 and (pb is None or "error" in pb):
        pb = draft(k, tt, max_tokens=6000 if attempts == 0 else 16000)
        attempts += 1
    pb["_attempts"] = attempts
    p.write_text(json.dumps(pb, indent=1))
    print(p.name, "ok" if "error" not in pb else pb["error"][:60], attempts, flush=True)


def main():
    from concurrent.futures import ThreadPoolExecutor
    jobs = [(k, tt) for k, a in ARCHETYPES.items() for tt in a.ttypes]
    with ThreadPoolExecutor(10) as ex:
        list(ex.map(lambda j: redraft(*j), jobs))


if __name__ == "__main__":
    main()
