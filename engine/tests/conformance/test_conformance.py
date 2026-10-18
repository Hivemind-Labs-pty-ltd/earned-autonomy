"""SPEC §13 conformance suite. A build is compliant if all of these pass.

1. Every executed autonomous action has a Decision explaining why it was allowed.
2. No action executes autonomously at L1, while paused, after a failed check, or in a capped type.
3. After an incident, the key is one level lower before the next decision.
4. Replaying the trust record from empty reproduces every TrustState exactly.
5. Self-promotion and rule-loosening by an agent or its builder is blocked and logged; legitimate requests pass.
6. Hidden tests are unreadable by the agent and its improver.
7. Trust Gym T1 parity: promotion precision ≥ 90%, median demotion latency ≤ 15.
Plus: tamper-evident record, privacy (no customer content), unpredictable sampling.
"""
import random
import secrets
import sqlite3
import statistics as st
from dataclasses import fields

import pytest
from helpers import AGENT, AI_OWNER, AUDITOR, BUILDER, FAIL, OK, POLICY_OWNER, REVIEWER, act, engine, promote_to
from sim import load_worlds, run_world

from earned_autonomy import (L1, L2, L3, Actor, Decision, SQLiteBackend, TrustEngine, TrustRecord)
from earned_autonomy.record import Entry, MemoryBackend, entry_hash

REQUIRED = ("level", "evidence_n", "evidence_err", "upper_bound", "eps", "checks", "policy_version",
            "agent_version", "trust_key", "why", "consequence", "payload_hash")


def busy_engine(seed=0, n=1500):
    """An engine with promotions, demotions, incidents, pauses, versions and reviewer evidence on its record."""
    e = engine(sampler=random.Random(seed))
    rng = random.Random(seed + 1)
    for i in range(n):
        tt = rng.choice(["cs.status.update", "cs.reply.send", "cs.payment.release"])
        a = act(tt)
        d = e.decide(a, FAIL if rng.random() < 0.03 else OK)
        bad = rng.random() < 0.04
        if d.allowed:
            e.mark_executed(a.action_id)
            if any(q["action_id"] == a.action_id for q in e.review_queue()):
                e.record_outcome(a.action_id, "rejected" if bad else "approved", "wrong_fact" if bad else None,
                                 "spot_check", "rev")
            elif bad and rng.random() < 0.3:
                e.report_incident(a.action_id, "high", "ops")
        else:
            label = rng.choice(["rejected", "material_edit"]) if bad else rng.choice(["approved", "cosmetic_edit"])
            e.record_outcome(a.action_id, label, "wrong_amount" if bad else ("tone" if label == "cosmetic_edit" else None),
                             "pre_review", rng.choice(["rex", "ann"]))
        if i == 700:
            e.pause(REVIEWER, "org", "cs", "cs.reply.send")
        if i == 800:
            e.resume(AI_OWNER, "org", "cs", "cs.reply.send")
        if i == 900:
            e.suites.seed_hidden("cs.status.update", [(f"h{j}", {}) for j in range(12)])
            e.on_version_published("cs", "v2", {"cs.status.update": {"hidden_pass": 0.9}})
        if i % 50 == 0:
            e.record_canary("org", "rex", "cs.reply.send", caught=rng.random() < 0.9)
    return e


# ---- 1 ---------------------------------------------------------------------------------------------------------
def test_c1_every_autonomous_execution_is_explained():
    e = busy_engine()
    decisions = {}
    executed = 0
    for x in e.record.entries():
        if x.type == "decision":
            decisions[x.body["action_id"]] = x.body
        elif x.type == "executed" and x.body["autonomous"]:
            executed += 1
            d = decisions[x.body["action_id"]]
            assert d["mode"] == "act" and d["why"] == "trusted"
            assert all(d.get(f) is not None for f in REQUIRED), d
            assert d["level"] >= L2
            ex = e.explain(x.body["action_id"])
            assert ex["policy"] is not None and ex["decisions"]
    assert executed > 50


# ---- 2 ---------------------------------------------------------------------------------------------------------
def test_c2_no_autonomous_execution_when_not_allowed():
    e = engine()
    a = act()
    e.decide(a, OK)                                           # L1
    with pytest.raises(PermissionError):
        e.mark_executed(a.action_id)
    promote_to(e, L2)
    for setup, why in ((lambda: None, "check_failed"),):
        a = act()
        e.decide(a, FAIL)
        with pytest.raises(PermissionError):
            e.mark_executed(a.action_id)
    e.pause(REVIEWER, "org", "cs")
    a = act()
    assert e.decide(a, OK).why == "paused"
    with pytest.raises(PermissionError):
        e.mark_executed(a.action_id)
    e.resume(AI_OWNER, "org", "cs")
    a = act("cs.payment.release")
    e.decide(a, OK)
    with pytest.raises(PermissionError):
        e.mark_executed(a.action_id)
    # re-decision at execution time wins: allowed at proposal, paused before execution
    a = act()
    assert e.decide(a, OK).allowed
    e.pause(REVIEWER, "org", "cs")
    assert not e.decide(a, OK).allowed
    with pytest.raises(PermissionError):
        e.mark_executed(a.action_id)
    # across a busy record, every autonomous execution followed an 'act' decision at L2+
    b = busy_engine(3)
    last = {}
    for x in b.record.entries():
        if x.type == "decision":
            last[x.body["action_id"]] = x.body
        elif x.type == "executed" and x.body["autonomous"]:
            d = last[x.body["action_id"]]
            assert d["mode"] == "act" and d["level"] >= L2 and not d["checks"]["failed"]
            assert d["consequence"] != "C4"


# ---- 3 ---------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("start", [L2, L3])
def test_c3_incident_steps_down_before_next_decision(start):
    e = engine()
    promote_to(e, start)
    a = act()
    e.decide(a, OK)
    e.mark_executed(a.action_id)
    e.report_incident(a.action_id, "high", "ops")
    nxt = e.decide(act(), OK)
    assert nxt.level == start - 1


# ---- 4 ---------------------------------------------------------------------------------------------------------
def test_c4_replay_reproduces_state_exactly():
    e = busy_engine()
    assert e.rebuild_state() == e.live_state()
    # a fresh engine opened on the same record has identical state
    e2 = TrustEngine(record=e.record, clock=e.clock)
    assert e2.live_state() == e.live_state()


def test_c4_replay_sqlite_reopen(tmp_path):
    path = str(tmp_path / "trust.db")
    e = engine(record=TrustRecord(SQLiteBackend(path)))
    promote_to(e, L2)
    a = act()
    e.decide(a, OK)
    e.mark_executed(a.action_id)
    e.report_incident(a.action_id, "high", "ops")
    live = e.live_state()
    reopened = TrustEngine(record=TrustRecord(SQLiteBackend(path)), clock=e.clock)
    assert reopened.live_state() == live
    assert reopened.record.verify().ok


# ---- 5 ---------------------------------------------------------------------------------------------------------
OWNER_BUILDER = Actor("oli", {"ai_owner", "builder"}, builds={"cs"})
AGENT_WITH_ROLE = Actor("cs", {"policy_owner"}, agent_id="cs")       # misconfigured grant

ATTACKS = [
    (AGENT, "promote", "cs"), (AGENT, "set_eps", None), (AGENT, "set_cap", None), (AGENT, "set_spot_rate", None),
    (AGENT, "edit_tests", "cs"), (AGENT, "edit_checks", "cs"), (AGENT, "edit_record", "cs"),
    (AGENT, "read_hidden_tests", "cs"), (AGENT, "set_policy", None), (AGENT, "resume", "cs"),
    (AGENT_WITH_ROLE, "promote", "cs"), (AGENT_WITH_ROLE, "set_eps", None), (AGENT_WITH_ROLE, "edit_tests", "cs"),
    (BUILDER, "promote", "cs"), (BUILDER, "set_eps", None), (BUILDER, "edit_tests", "cs"),
    (BUILDER, "edit_checks", "cs"), (BUILDER, "edit_record", None), (BUILDER, "read_hidden_tests", "cs"),
    (OWNER_BUILDER, "set_consequence", None), (OWNER_BUILDER, "set_spot_rate", None),
    (OWNER_BUILDER, "set_cap", None), (OWNER_BUILDER, "resume", "cs"),
    (AI_OWNER, "promote", "cs"), (AI_OWNER, "set_eps", None), (AI_OWNER, "edit_record", None),
    (REVIEWER, "promote", "cs"), (REVIEWER, "edit_tests", "cs"), (AUDITOR, "demote", "cs"),
    (POLICY_OWNER, "edit_record", None),
]
LEGIT = [
    (POLICY_OWNER, "set_eps", None), (POLICY_OWNER, "promote", "cs"), (AI_OWNER, "add_task_type", None),
    (AI_OWNER, "set_consequence", None), (REVIEWER, "demote", "cs"), (AI_OWNER, "pause", "cs"),
    (AUDITOR, "read_record", None), (BUILDER, "publish_version", "cs"), (AGENT, "read_record", "cs"),
    (AUDITOR, "read_hidden_tests", "cs"),
]


def test_c5_governance_attacks_blocked_and_logged():
    e = engine()
    before = len(e.record)
    blocked = sum(not e.governance.request(a, op, t) for a, op, t in ATTACKS)
    allowed = sum(e.governance.request(a, op, t) for a, op, t in LEGIT)
    assert len(ATTACKS) >= 20 and blocked == len(ATTACKS)
    assert allowed == len(LEGIT)
    logged = [x for x in e.record.entries() if x.type == "governance"]
    assert len(logged) == len(ATTACKS) + len(LEGIT) == len(e.record) - before
    assert sum(not x.body["allowed"] for x in logged) == len(ATTACKS)
    # end to end: the builder cannot promote its own agent, the agent cannot pause itself out of review
    assert not e.promote(BUILDER, "org", "cs", "cs.status.update")
    assert not e.set_task_eps(BUILDER, "cs.reply.send", 0.04)
    assert not e.resume(AGENT, "org", "cs")
    assert e.get_state("org", "cs", "cs.status.update") == []


def test_c5_record_has_no_edit_api():
    rec = TrustRecord()
    assert not any(hasattr(rec, m) for m in ("update", "delete", "edit", "remove", "replace"))


# ---- 6 ---------------------------------------------------------------------------------------------------------
def test_c6_hidden_tests_unreadable_by_agent_and_builder():
    e = engine()
    e.suites.seed_hidden("cs.reply.send", [("h1", {"expect": "secret"})])
    for actor in (AGENT, BUILDER, OWNER_BUILDER):
        with pytest.raises(PermissionError):
            e.suites.hidden(actor, "cs.reply.send", "cs")
    assert all(t.visibility == "training" for t in e.suites.training("cs.reply.send"))
    assert len(e.suites.hidden(POLICY_OWNER, "cs.reply.send", "cs")) == 1
    assert len(e.suites.hidden(AUDITOR, "cs.reply.send", "cs")) == 1
    rate, n = e.suites.run_hidden("cs.reply.send", lambda spec: True)
    assert (rate, n) == (1.0, 1)


# ---- 7 ---------------------------------------------------------------------------------------------------------
def test_c7_trust_gym_t1_parity():
    good = total = 0
    lat = []
    for w in load_worlds():
        e, g, t, l = run_world(w)
        good += g
        total += t
        lat += l
        assert e.record.verify().ok
    precision = good / total
    assert total > 200 and len(lat) > 15
    assert precision >= 0.90, precision            # v3 reference 93.3%
    assert st.median(lat) <= 15, st.median(lat)    # v3 reference 14


# ---- tamper evidence ---------------------------------------------------------------------------------------
def _tampered(edit):
    e = busy_engine(n=300)
    rows = list(e.record.entries())
    be = MemoryBackend()
    for r in edit(rows):
        be.append(r)
    return TrustRecord(be).verify()


def test_tamper_edit_detected():
    def edit(rows):
        r = rows[50]
        body = dict(r.body)
        body["label"] = "approved"
        rows[50] = Entry(r.seq, r.ts, r.type, body, r.prev_hash, r.hash)
        return rows
    v = _tampered(edit)
    assert not v.ok and v.first_bad_seq == 50


def test_tamper_rehash_one_entry_detected():
    # an attacker who recomputes the edited entry's own hash still breaks the next link
    def edit(rows):
        r = rows[50]
        body = dict(r.body)
        body["serious"] = False
        rows[50] = Entry(r.seq, r.ts, r.type, body, r.prev_hash, entry_hash(r.seq, r.ts, r.type, body, r.prev_hash))
        return rows
    v = _tampered(edit)
    assert not v.ok and v.first_bad_seq == 51


def test_tamper_delete_and_reorder_detected():
    assert not _tampered(lambda rows: rows[:40] + rows[41:]).ok
    assert not _tampered(lambda rows: rows[:40] + [rows[41], rows[40]] + rows[42:]).ok
    assert not _tampered(lambda rows: rows[:-1] + [rows[-1], rows[-1]]).ok


def test_sqlite_refuses_update_delete_and_detects_tampering(tmp_path):
    path = str(tmp_path / "t.db")
    e = engine(record=TrustRecord(SQLiteBackend(path)))
    promote_to(e, L2)
    conn = sqlite3.connect(path)
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("UPDATE trust_record SET body='{}' WHERE seq=5")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM trust_record WHERE seq=5")
    # an attacker with raw database access who drops the triggers is still caught by verify()
    conn.execute("DROP TRIGGER trust_record_no_update")
    conn.execute("UPDATE trust_record SET body='{\"x\":1}' WHERE seq=5")
    conn.commit()
    assert not TrustRecord(SQLiteBackend(path)).verify().ok


# ---- privacy -----------------------------------------------------------------------------------------------
def test_record_holds_no_customer_content():
    e = engine()
    secret = "Jane Citizen, 12 Example St, card 4111"
    a = act(payload={"customer": secret, "amount": 49})
    e.decide(a, OK)
    e.record_outcome(a.action_id, "approved", None, "pre_review", "rex")
    e.report_incident(a.action_id, "low", "ops", note=secret)
    dump = "".join(x.hash + str(x.body) for x in e.record.entries())
    assert "Jane" not in dump and "4111" not in dump
    d = [x for x in e.record.entries() if x.type == "decision"][0]
    assert d.body["payload_hash"].startswith("sha256:")


# ---- unpredictable sampling --------------------------------------------------------------------------------
def test_sampling_is_unpredictable_and_hidden_from_the_agent():
    e = TrustEngine(e_policy := engine().policy)          # default sampler
    assert isinstance(e._sampler, secrets.SystemRandom)
    assert {f.name for f in fields(Decision)}.isdisjoint({"spot", "sampled", "spot_check"})
    b = busy_engine()
    assert all(x.body.get("mode") in ("hold", "act") for x in b.record.entries() if x.type == "decision")
    agent_view = b.record.read_for("agent")
    assert not any(x.type in ("spot_sample", "canary", "second_check_sample") for x in agent_view)
    assert any(x.type == "spot_sample" for x in b.record.read_for("auditor"))
    a = act()
    promote_to(b, L2)
    b.decide(a, OK)
    assert b.mark_executed(a.action_id) is None           # nothing about sampling comes back
