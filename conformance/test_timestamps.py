"""Timestamps and ordering (EA-6.10, EA-6.11).

One exact UTC format in the record (`YYYY-MM-DDTHH:MM:SS.sssZ`); the record's order of truth is the sequence number in
the hash chain, never the timestamp.
"""
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from helpers import OK, START, act, engine

from earned_autonomy import (SQLiteBackend, TrustRecord, format_timestamp, normalise_timestamp, parse_timestamp)

CANONICAL_SHAPE = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$"


@pytest.mark.covers("EA-6.11")
def test_format_is_exact_even_at_zero_milliseconds():
    assert format_timestamp(datetime(2026, 10, 19, 3, 20, 0, tzinfo=timezone.utc)) == "2026-10-19T03:20:00.000Z"
    assert format_timestamp(datetime(2026, 10, 19, 3, 20, 0, 123456, tzinfo=timezone.utc)) == "2026-10-19T03:20:00.123Z"
    melbourne = timezone(timedelta(hours=11))
    assert format_timestamp(datetime(2026, 10, 19, 14, 20, 0, tzinfo=melbourne)) == "2026-10-19T03:20:00.000Z"


@pytest.mark.covers("EA-6.11")
def test_round_trip():
    text = "2026-10-19T03:20:00.123Z"
    assert format_timestamp(parse_timestamp(text)) == text
    moment = datetime(2026, 4, 5, 15, 30, 1, 999000, tzinfo=timezone.utc)
    assert parse_timestamp(format_timestamp(moment)) == moment


@pytest.mark.covers("EA-6.11")
def test_old_forms_normalise_to_the_canonical_string():
    assert normalise_timestamp("2026-10-19T03:20:00+00:00") == "2026-10-19T03:20:00.000Z"
    assert normalise_timestamp("2026-10-19T03:20:00.123456+00:00") == "2026-10-19T03:20:00.123Z"
    assert normalise_timestamp("2026-10-19T14:20:00+11:00") == "2026-10-19T03:20:00.000Z"


@pytest.mark.covers("EA-6.11")
def test_naive_datetimes_and_strings_are_rejected():
    with pytest.raises(ValueError):
        format_timestamp(datetime(2026, 10, 19, 3, 20))
    with pytest.raises(ValueError):
        parse_timestamp("2026-10-19T03:20:00")


@pytest.mark.covers("EA-6.11")
def test_every_record_timestamp_uses_the_canonical_format():
    trust_engine = engine()
    for _ in range(5):
        action = act()
        trust_engine.decide(action, OK)
        trust_engine.record_outcome(action.action_id, "approved", None, "pre_review", "reviewer")
    entries = list(trust_engine.record.entries())
    assert entries
    for entry in entries:
        assert entry.timestamp == normalise_timestamp(entry.timestamp)
        assert re.match(CANONICAL_SHAPE, entry.timestamp)
        created = entry.body.get("created_at")
        if created:
            assert re.match(CANONICAL_SHAPE, created)


class SkewedClock:
    """A clock that jumps backwards and forwards, as a drifting server clock might."""

    def __init__(self):
        self.offsets = [0, 5, -30, 2, -60, 10]
        self.calls = 0

    def __call__(self):
        offset = self.offsets[self.calls % len(self.offsets)]
        self.calls += 1
        return START + timedelta(minutes=self.calls) + timedelta(minutes=offset)


@pytest.mark.covers("EA-6.10")
def test_replay_follows_sequence_not_timestamps_under_clock_skew(tmp_path):
    path = str(tmp_path / "record.db")
    trust_engine = engine(clock=SkewedClock(), record=TrustRecord(SQLiteBackend(path)))
    for _ in range(20):
        action = act()
        trust_engine.decide(action, OK)
        trust_engine.record_outcome(action.action_id, "approved", None, "pre_review", "reviewer")
    entries = list(trust_engine.record.entries())
    sequences = [entry.sequence for entry in entries]
    timestamps = [entry.timestamp for entry in entries]
    assert sequences == sorted(sequences) == list(range(len(entries)))
    assert timestamps != sorted(timestamps), "the skewed clock should produce out-of-order timestamps"
    assert trust_engine.record.verify().ok
    assert trust_engine.rebuild_state() == trust_engine.live_state()
    # a fresh engine on the same database replays in sequence order and reaches the same state
    reopened = engine(clock=SkewedClock(), record=TrustRecord(SQLiteBackend(path)))
    assert reopened.live_state() == trust_engine.live_state()


@pytest.mark.covers("EA-6.8", "EA-6.11")
def test_external_rehash_of_the_stored_record_matches_the_chain(tmp_path):
    """An auditor's check: read the raw rows, canonicalise and hash them with nothing from this package."""
    path = str(tmp_path / "record.db")
    trust_engine = engine(record=TrustRecord(SQLiteBackend(path)))
    for _ in range(10):
        action = act()
        trust_engine.decide(action, OK)
        trust_engine.record_outcome(action.action_id, "approved", None, "pre_review", "reviewer")

    connection = sqlite3.connect(path)
    rows = connection.execute(
        "SELECT sequence, timestamp, type, body, previous_hash, hash FROM trust_record ORDER BY sequence").fetchall()
    previous_hash = "sha256:" + "0" * 64
    for sequence, timestamp, entry_type, body, stored_previous, stored_hash in rows:
        assert stored_previous == previous_hash
        blob = json.dumps({"sequence": sequence, "timestamp": timestamp, "type": entry_type, "body": json.loads(body),
                           "previous_hash": stored_previous},
                          sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        assert "sha256:" + hashlib.sha256(blob.encode()).hexdigest() == stored_hash
        previous_hash = stored_hash
    assert len(rows) == len(trust_engine.record) > 0
