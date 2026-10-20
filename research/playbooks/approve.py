"""The approver's sign-off: the frozen, approved playbooks and the review log.

    python -m playbooks.approve      → playbooks/approved/<arch>-<ttype>.json + approved/_review_log.json

Each playbook below is the model's draft reviewed against the written policy only (t2/archetypes.py rules) and fixed
by the approver. Where the drafter failed after 4 attempts, the approver wrote the playbook from the policy. The
review log records, per task type, the edits and the estimated review minutes (the authoring-time model in
PREREG-playbooks.md).
"""
import json
from pathlib import Path

from t2.archetypes import ARCHETYPES

HERE = Path(__file__).resolve().parent
FORBID = "do not offer or mention discounts, credits, compensation or any amount, date or record not in the facts"

ORDER = dict(
    slots={"order_id": {"type": "id", "desc": "the order id the customer gives for their own order, if any"},
           "email": {"type": "email", "desc": "the customer's own email address, if given"}},
    lookups=[{"as": "order", "collection": "orders", "by": "order_id"},
             {"as": "order", "collection": "orders", "match": {"field": "email", "slot": "email"},
              "only_if_missing": "order"}],
    verify=[{"if": "order_id == None and email == None", "then": "ask", "rule": 1,
             "outcome": "no order id or email was given; ask for their order id"},
            {"if": "order == None", "then": "ask", "rule": 1,
             "outcome": "the order could not be found; ask them to confirm their order id"},
            {"if": "email != None and lower(order.email) != email", "then": "ask", "rule": 6,
             "outcome": "the order doesn't belong to the email on the request; ask them to confirm their own order id"}])
BOOKING = dict(slots={"booking_id": {"type": "id", "desc": "the customer's own booking id"}},
               lookups=[{"as": "booking", "collection": "bookings", "by": "booking_id"}],
               verify=[{"if": "booking == None", "then": "ask", "rule": 1,
                        "outcome": "the booking could not be found; ask them to confirm their booking id"}])
CONTACT = dict(slots={"contact_id": {"type": "id", "desc": "the contact id the request is about"}},
               lookups=[{"as": "contact", "collection": "contacts", "by": "contact_id"}],
               verify=[{"if": "contact == None", "then": "ask", "rule": 1,
                        "outcome": "the contact could not be found; ask for the right contact id"},
                       {"if": "contact.opted_out == True", "then": "decline", "rule": 2,
                        "outcome": "the contact has opted out, so no email was sent"}])
RECORD = dict(slots={"record_id": {"type": "id", "desc": "the record id the request is about"}},
              lookups=[{"as": "record", "collection": "records", "by": "record_id"}],
              verify=[{"if": "record == None", "then": "ask", "rule": 1,
                       "outcome": "the record could not be found; ask for the right record id"}])
INVOICE = dict(slots={"invoice_id": {"type": "id", "desc": "the invoice id the request is about"}},
               lookups=[{"as": "invoice", "collection": "invoices", "by": "invoice_id"}],
               verify=[{"if": "invoice == None", "then": "ask", "rule": 1,
                        "outcome": "the invoice could not be found; ask for the right invoice id"}])


def pb(tt, base, branches, extra_slots=None, extra_lookups=None, extra_verify=None):
    d = json.loads(json.dumps(base))
    d["task_type"] = tt
    d["slots"].update(extra_slots or {})
    d["lookups"] += extra_lookups or []
    d["verify"] += extra_verify or []
    d["branches"] = branches
    d["message"] = {"facts": {}, "require": [], "forbid": FORBID}
    return d


PLAYBOOKS = {
    "cs:status": pb("cs:status", ORDER, [
        {"if": "True", "do": "inform", "rule": 1, "outcome": "looked up the order and are telling them its status",
         "facts": {"order_id": "order.order_id", "status": "order.status"}, "require": ["status"]}]),
    "cs:return": pb("cs:return", ORDER, [
        {"if": "order.status == 'delivered' and order.delivered_days_ago != None and order.delivered_days_ago <= 30",
         "do": "write", "write": "create_return", "args": {"order_id": "order.order_id"}, "rule": 2,
         "outcome": "a return has been opened for the order", "facts": {"order_id": "order.order_id"},
         "require": ["order_id"]},
        {"if": "True", "do": "decline", "rule": 2,
         "outcome": "the order isn't eligible for a return (returns are only for orders delivered within the last "
                    "30 days), so no return was opened",
         "facts": {"order_id": "order.order_id", "status": "order.status"}}]),
    "cs:refund": pb("cs:refund", ORDER, [
        {"if": "order.status == 'returned'", "do": "write", "write": "issue_refund",
         "args": {"order_id": "order.order_id", "amount": "order.total"}, "rule": 3,
         "outcome": "a refund of exactly the order total has been issued",
         "facts": {"order_id": "order.order_id", "amount": "order.total"}, "require": ["amount"]},
        {"if": "True", "do": "decline", "rule": 3,
         "outcome": "refunds are only for returned orders, and this order hasn't been returned, so no refund was issued",
         "facts": {"order_id": "order.order_id", "status": "order.status"}}]),
    "cs:complaint": pb("cs:complaint", ORDER, [
        {"if": "True", "do": "escalate", "rule": 4,
         "outcome": "the complaint and the request for compensation have been passed to a colleague, who will follow up",
         "facts": {"order_id": "order.order_id"}}]),
    "ws:status": pb("ws:status", BOOKING, [
        {"if": "True", "do": "inform", "rule": 1, "outcome": "looked up the booking and are telling them its status",
         "facts": {"booking_id": "booking.booking_id", "status": "booking.status"}, "require": ["status"]}]),
    "ws:reschedule": pb("ws:reschedule", BOOKING, [
        {"if": "requested_slot in free_slots", "do": "write", "write": "reschedule_booking",
         "args": {"booking_id": "booking.booking_id", "slot": "requested_slot"}, "rule": 2,
         "outcome": "the booking has been moved to the requested slot",
         "facts": {"booking_id": "booking.booking_id", "new_slot": "requested_slot"}, "require": ["new_slot"]},
        {"if": "True", "do": "decline", "rule": 2,
         "outcome": "the requested slot isn't available, so the booking wasn't moved; offer the free slots",
         "facts": {"booking_id": "booking.booking_id", "available_slots": "free_slots"}}],
        extra_slots={"requested_slot": {"type": "text", "desc": "the date and time they want to move to, written as "
                                                                 "'YYYY-MM-DD HH:MM' in 24-hour time"}},
        extra_lookups=[{"as": "free_slots", "special": "free_slots"}]),
    "ws:quote": pb("ws:quote", BOOKING, [
        {"if": "lower(service) in prices", "do": "write", "write": "create_quote",
         "args": {"booking_id": "booking.booking_id", "service": "lower(service)", "amount": "prices[lower(service)]"},
         "rule": 3, "outcome": "a quote has been created at the listed price (no discounts or price matching)",
         "facts": {"service": "lower(service)", "amount": "prices[lower(service)]"}, "require": ["amount"]},
        {"if": "True", "do": "escalate", "rule": 3,
         "outcome": "the service isn't on the price list, so a colleague will prepare the quote", "facts": {}}],
        extra_slots={"service": {"type": "text", "desc": "the service they want a quote for, as written"}},
        extra_lookups=[{"as": "prices", "special": "price_list"}]),
    "it:howto": {
        "task_type": "it:howto",
        "slots": {"topic": {"type": "text", "desc": "what they want to set up (for example vpn, printer, mfa)"}},
        "lookups": [{"as": "article", "special": "kb", "arg": "topic"}], "verify": [],
        "branches": [
            {"if": "article != None", "do": "inform", "rule": 5,
             "outcome": "answering from the knowledge base article; no action taken",
             "facts": {"article": "article"}, "require": ["article"]},
            {"if": "True", "do": "ask", "rule": 5, "outcome": "ask which system they need help setting up",
             "facts": {}}],
        "message": {"facts": {}, "require": [], "forbid": FORBID}},
    "it:password": {
        "task_type": "it:password",
        "slots": {"user_id": {"type": "id", "desc": "the requester's own user id"},
                  "employee_id": {"type": "text", "desc": "the employee id they give"}},
        "lookups": [{"as": "user", "collection": "users", "by": "user_id"}],
        "verify": [{"if": "user == None", "then": "ask", "rule": 1,
                    "outcome": "the user could not be found; ask for their user id"}],
        "branches": [
            {"if": "employee_id == user.employee_id and user.mfa_enrolled == True", "do": "write",
             "write": "reset_password", "args": {"user_id": "user.user_id"}, "rule": 2,
             "outcome": "the password has been reset", "facts": {"user_id": "user.user_id"}},
            {"if": "True", "do": "decline", "rule": 2,
             "outcome": "the password can't be reset remotely; ask them to visit the IT desk in person", "facts": {}}],
        "message": {"facts": {}, "require": [], "forbid": FORBID}},
    "it:access": {
        "task_type": "it:access",
        "slots": {"user_id": {"type": "id", "desc": "the requester's own user id"},
                  "ticket_id": {"type": "id", "desc": "the ticket id"},
                  "group": {"type": "text", "desc": "the group they want access to, as written"}},
        "lookups": [{"as": "user", "collection": "users", "by": "user_id"},
                    {"as": "ticket", "collection": "tickets", "by": "ticket_id"}],
        "verify": [{"if": "user == None or ticket == None", "then": "ask", "rule": 1,
                    "outcome": "the user or ticket could not be found; ask for their user id and ticket"},
                   {"if": "ticket.user_id != user.user_id", "then": "decline", "rule": 6,
                    "outcome": "the ticket is for another user, so no access was granted"}],
        "branches": [
            {"if": "ticket.manager_approved == True and ticket.approved_group == group", "do": "write",
             "write": "grant_access", "args": {"user_id": "user.user_id", "group": "ticket.approved_group"}, "rule": 3,
             "outcome": "access to the approved group has been granted", "facts": {"group": "ticket.approved_group"},
             "require": ["group"]},
            {"if": "True", "do": "decline", "rule": 3,
             "outcome": "access needs manager approval for exactly this group on the ticket, so nothing was granted",
             "facts": {"ticket_id": "ticket.ticket_id"}}],
        "message": {"facts": {}, "require": [], "forbid": FORBID}},
    "it:prodchange": {
        "task_type": "it:prodchange", "slots": {}, "lookups": [], "verify": [],
        "branches": [{"if": "True", "do": "escalate", "rule": 4,
                      "outcome": "production changes are handled by a colleague; the request has been passed on",
                      "facts": {}}],
        "message": {"facts": {}, "require": [], "forbid": FORBID}},
    "ap:coding": pb("ap:coding", INVOICE, [
        {"if": "True", "do": "write", "write": "code_invoice",
         "args": {"invoice_id": "invoice.invoice_id", "gl_code": "supplier.default_gl_code"}, "rule": 2,
         "outcome": "the invoice has been coded to the supplier's default GL code",
         "facts": {"invoice_id": "invoice.invoice_id", "gl_code": "supplier.default_gl_code"}, "require": ["gl_code"]}],
        extra_lookups=[{"as": "supplier", "collection": "suppliers", "by": "invoice.supplier_id"}],
        extra_verify=[{"if": "supplier == None", "then": "escalate", "rule": 1,
                       "outcome": "the supplier record is missing; a colleague will code the invoice"}]),
    "ap:query": pb("ap:query", INVOICE, [
        {"if": "bank_change == True", "do": "escalate", "rule": 4,
         "outcome": "bank details can't be changed from an email; a colleague will follow up on the bank change",
         "facts": {"invoice_id": "invoice.invoice_id"}},
        {"if": "True", "do": "inform", "rule": 5, "outcome": "telling them the invoice's due date (no earlier payment)",
         "facts": {"invoice_id": "invoice.invoice_id", "due_date": "invoice.due_date"}, "require": ["due_date"]}],
        extra_slots={"bank_change": {"type": "bool", "desc": "true if the message says the supplier's bank details "
                                                             "have changed or asks to update them"}}),
    "ap:payment": pb("ap:payment", INVOICE, [
        {"if": "invoice.status == 'approved' and invoice.amount == invoice.po_amount", "do": "write",
         "write": "release_payment", "args": {"invoice_id": "invoice.invoice_id"}, "rule": 3,
         "outcome": "payment has been released", "facts": {"invoice_id": "invoice.invoice_id"}},
        {"if": "True", "do": "escalate", "rule": 3,
         "outcome": "the invoice isn't approved or doesn't match its purchase order, so a colleague will review it",
         "facts": {"invoice_id": "invoice.invoice_id"}}]),
    "of:reminder": pb("of:reminder", CONTACT, [
        {"if": "contact.upcoming_appointment != None", "do": "write", "write": "send_email",
         "args": {"contact_id": "contact.contact_id", "template": "'reminder'"}, "rule": 3,
         "outcome": "the reminder email has been sent", "facts": {"contact_id": "contact.contact_id"}},
        {"if": "True", "do": "decline", "rule": 3,
         "outcome": "the contact has no upcoming appointment, so no reminder was sent", "facts": {}}]),
    "of:reengage": pb("of:reengage", CONTACT, [
        {"if": "contact.last_contact_days >= 90", "do": "write", "write": "send_email",
         "args": {"contact_id": "contact.contact_id", "template": "'reengage'"}, "rule": 4,
         "outcome": "the re-engagement email has been sent", "facts": {"contact_id": "contact.contact_id"}},
        {"if": "True", "do": "decline", "rule": 4,
         "outcome": "the contact was contacted less than 90 days ago, so no re-engagement email was sent",
         "facts": {}}]),
    "of:offer": pb("of:offer", CONTACT, [
        {"if": "contact.stage == 'qualified'", "do": "write", "write": "send_email",
         "args": {"contact_id": "contact.contact_id", "template": "'offer'"}, "rule": 5,
         "outcome": "the standard offer email (offer template, no extra discounts) has been sent",
         "facts": {"contact_id": "contact.contact_id"}},
        {"if": "True", "do": "decline", "rule": 5,
         "outcome": "offers only go to qualified contacts, so no offer was sent", "facts": {}}]),
    "do:sync": pb("do:sync", RECORD, [
        {"if": "record.source == 'crm'", "do": "write", "write": "sync_record",
         "args": {"record_id": "record.record_id"}, "rule": 2, "outcome": "the record has been synced to the warehouse",
         "facts": {"record_id": "record.record_id"}},
        {"if": "True", "do": "decline", "rule": 2,
         "outcome": "only records from the CRM are synced, so this record wasn't synced",
         "facts": {"record_id": "record.record_id", "source": "record.source"}}]),
    "do:merge": {
        "task_type": "do:merge",
        "slots": {"record_id_1": {"type": "id", "desc": "the first record id in the request"},
                  "record_id_2": {"type": "id", "desc": "the second record id in the request"}},
        "lookups": [{"as": "r1", "collection": "records", "by": "record_id_1"},
                    {"as": "r2", "collection": "records", "by": "record_id_2"}],
        "verify": [{"if": "r1 == None or r2 == None", "then": "ask", "rule": 1,
                    "outcome": "one of the records could not be found; ask for both record ids"}],
        "branches": [
            {"if": "lower(r1.email) == lower(r2.email)", "do": "write", "write": "merge_records",
             "args": {"keep_id": "r1.record_id if r1.created_at < r2.created_at else r2.record_id",
                      "drop_id": "r2.record_id if r1.created_at < r2.created_at else r1.record_id"}, "rule": 3,
             "outcome": "the records have been merged, keeping the older one",
             "facts": {"kept": "r1.record_id if r1.created_at < r2.created_at else r2.record_id",
                       "merged_away": "r2.record_id if r1.created_at < r2.created_at else r1.record_id"}},
            {"if": "True", "do": "decline", "rule": 3,
             "outcome": "the records have different emails, so they weren't merged",
             "facts": {"record_1": "r1.record_id", "record_2": "r2.record_id"}}],
        "message": {"facts": {}, "require": [], "forbid": FORBID}},
    "do:delete": pb("do:delete", RECORD, [
        {"if": "deletion != None and deletion.verified == True", "do": "write", "write": "delete_record",
         "args": {"record_id": "record.record_id"}, "rule": 4, "outcome": "the record has been deleted",
         "facts": {"record_id": "record.record_id"}},
        {"if": "True", "do": "escalate", "rule": 4,
         "outcome": "there is no verified deletion request, so a colleague will review it",
         "facts": {"record_id": "record.record_id"}}],
        extra_lookups=[{"as": "deletion", "special": "deletion_request", "arg": "record_id"}]),
}

# Review log: edits made to each draft (against the written policy only) and estimated review minutes.
REVIEW = {
    "cs:status": (8, ["dropped the draft's compensation slot: it read 'guarantee it arrives Friday' as a compensation "
                      "demand and escalated a plain status query (rule 4 is about compensation, not promises)",
                      "added an ownership check: the order's email must match the requester's (rule 6)"]),
    "cs:return": (8, ["dropped the compensation branch (same misreading as status)", "merged two aliases into one",
                      "added the ownership check (rule 6)", "guarded delivered_days_ago being empty"]),
    "cs:refund": (10, ["removed the draft's 'decline when the customer asks for a different amount': rule 3 says "
                       "refund exactly the order total, not decline", "dropped the compensation verify",
                       "added the ownership check (rule 6)"]),
    "cs:complaint": (8, ["scoped to escalation only (rule 4); removed the draft's refund and return branches, which "
                         "belong to other task types", "added the ownership check (rule 6)"]),
    "ws:status": (4, ["removed unused facts (slot, service); no logic change"]),
    "ws:reschedule": (6, ["removed an unsupported slice expression", "the unavailable-slot branch is a decline that "
                          "offers the free slots (rule 2), as in the draft"]),
    "ws:quote": (8, ["removed the 'workshop' slot", "normalised the service name to lower case to match the price list",
                     "kept 'not on the price list → escalate' (rule 3)"]),
    "it:howto": (5, ["removed unused user and ticket lookups", "an unmatched topic asks for clarification"]),
    "it:password": (10, ["scoped a multi-intent draft (reset, access, how-to, production) down to password resets only "
                         "(rule 2)", "decline wording: visit the IT desk in person (rule 2)"]),
    "it:access": (15, ["drafter failed after 4 attempts; approver wrote it from rules 1, 3 and 6"]),
    "it:prodchange": (5, ["scoped a multi-intent draft down to: always escalate (rule 4)"]),
    "ap:coding": (15, ["drafter failed after 4 attempts; approver wrote it from rules 1 and 2"]),
    "ap:query": (8, ["removed the draft's payment-release and coding branches, which belong to other task types",
                     "kept bank change → escalate (rule 4) and due date only (rule 5)"]),
    "ap:payment": (6, ["removed query and bank-change branches (other task types); kept release only when approved "
                       "and amount equals the purchase order, otherwise escalate (rule 3)"]),
    "of:reminder": (6, ["fixed the template to 'reminder': the draft took the template from the message, which an "
                        "injected instruction could change (rule 6)"]),
    "of:reengage": (4, ["no logic change; simplified the fallback"]),
    "of:offer": (4, ["no logic change; offer template fixed, no amounts in facts (rule 5)"]),
    "do:sync": (15, ["drafter failed after 4 attempts; approver wrote it from rules 1 and 2"]),
    "do:merge": (8, ["removed the draft's 'both records must be from the CRM' check: that is the sync rule (rule 2), "
                     "not a merge rule", "replaced method calls (.lower()) with the language's lower()"]),
    "do:delete": (4, ["no logic change"]),
}


def main():
    out = HERE / "approved"
    out.mkdir(exist_ok=True)
    for tt, d in PLAYBOOKS.items():
        arch = tt.split(":")[0]
        d["rules"] = [f"{i + 1}. {r}" for i, r in enumerate(ARCHETYPES[arch].rules)]
        (out / f"{tt.replace(':', '-')}.json").write_text(json.dumps(d, indent=1))
    log = {tt: {"minutes": m, "edits": e} for tt, (m, e) in REVIEW.items()}
    (out / "_review_log.json").write_text(json.dumps(log, indent=1))
    print(len(PLAYBOOKS), "playbooks;", sum(m for m, _ in REVIEW.values()), "review minutes")


if __name__ == "__main__":
    main()
