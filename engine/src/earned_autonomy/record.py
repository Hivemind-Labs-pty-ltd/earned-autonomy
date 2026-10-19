"""The trust record (SPEC §5, §10): append-only, kept forever, tamper-evident.

Every entry is hash-chained: `hash = sha256(canonical_json({sequence, timestamp, type, body, previous_hash}))`. `verify()`
recomputes the chain and detects any edited, deleted, inserted or reordered entry. Entries hold references and
labels only, never customer content (payloads are stored as hashes).

There is no update or delete API. Backends: in-memory and SQLite.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from dataclasses import dataclass
from typing import Iterator, Protocol

GENESIS = "sha256:" + "0" * 64

# Entry types an agent must never see in its own record (unpredictable sampling, SPEC §6 / §9).
PRIVATE_TYPES = frozenset({"spot_sample", "canary", "second_check_sample"})


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def entry_hash(sequence: int, timestamp: str, entry_type: str, body: dict, previous_hash: str) -> str:
    blob = canonical({"sequence": sequence, "timestamp": timestamp, "type": entry_type, "body": body,
                      "previous_hash": previous_hash})
    return "sha256:" + hashlib.sha256(blob.encode()).hexdigest()


@dataclass(frozen=True)
class Entry:
    sequence: int
    timestamp: str
    type: str
    body: dict
    previous_hash: str
    hash: str


@dataclass
class VerifyResult:
    ok: bool
    entries: int
    first_bad_sequence: int | None = None
    reason: str | None = None


class Backend(Protocol):
    def append(self, entry: Entry) -> None: ...
    def last(self) -> Entry | None: ...
    def scan(self) -> Iterator[Entry]: ...
    def count(self) -> int: ...


class MemoryBackend:
    def __init__(self):
        self._rows: list[Entry] = []

    def append(self, entry: Entry) -> None:
        self._rows.append(entry)

    def last(self) -> Entry | None:
        return self._rows[-1] if self._rows else None

    def scan(self) -> Iterator[Entry]:
        return iter(list(self._rows))

    def count(self) -> int:
        return len(self._rows)


class SQLiteBackend:
    """One table, insert-only. Triggers refuse UPDATE and DELETE at the database level."""

    def __init__(self, path: str = ":memory:"):
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS trust_record (
                sequence INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, type TEXT NOT NULL,
                body TEXT NOT NULL, previous_hash TEXT NOT NULL, hash TEXT NOT NULL);
            CREATE TRIGGER IF NOT EXISTS trust_record_no_update BEFORE UPDATE ON trust_record
                BEGIN SELECT RAISE(ABORT, 'trust record is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS trust_record_no_delete BEFORE DELETE ON trust_record
                BEGIN SELECT RAISE(ABORT, 'trust record is append-only'); END;
        """)
        self.connection.commit()

    def append(self, entry: Entry) -> None:
        self.connection.execute("INSERT INTO trust_record VALUES (?,?,?,?,?,?)",
                          (entry.sequence, entry.timestamp, entry.type, canonical(entry.body), entry.previous_hash, entry.hash))
        self.connection.commit()

    def _row(self, row) -> Entry:
        return Entry(row[0], row[1], row[2], json.loads(row[3]), row[4], row[5])

    def last(self) -> Entry | None:
        row = self.connection.execute("SELECT * FROM trust_record ORDER BY sequence DESC LIMIT 1").fetchone()
        return self._row(row) if row else None

    def scan(self) -> Iterator[Entry]:
        for row in self.connection.execute("SELECT * FROM trust_record ORDER BY rowid"):
            yield self._row(row)

    def count(self) -> int:
        return self.connection.execute("SELECT COUNT(*) FROM trust_record").fetchone()[0]


class TrustRecord:
    """Append-only, hash-chained log. The single source of truth: all trust state is derived from it."""

    def __init__(self, backend: Backend | None = None):
        self.backend = backend if backend is not None else MemoryBackend()
        self._lock = threading.Lock()

    def append(self, entry_type: str, body: dict, timestamp: str) -> Entry:
        with self._lock:
            last = self.backend.last()
            sequence = 0 if last is None else last.sequence + 1
            previous = GENESIS if last is None else last.hash
            body = json.loads(canonical(body))          # freeze to plain JSON
            entry = Entry(sequence, timestamp, entry_type, body, previous, entry_hash(sequence, timestamp, entry_type, body, previous))
            self.backend.append(entry)
            return entry

    def entries(self) -> Iterator[Entry]:
        return self.backend.scan()

    def __len__(self) -> int:
        return self.backend.count()

    def read_for(self, viewer_role: str) -> list[Entry]:
        """What a viewer may read. Agents see their record without sampling, canary or second-check entries."""
        rows = list(self.entries())
        if viewer_role == "agent":
            return [entry for entry in rows if entry.type not in PRIVATE_TYPES]
        return rows

    def verify(self) -> VerifyResult:
        previous = GENESIS
        count = 0
        for position, entry in enumerate(self.entries()):
            count += 1
            if entry.sequence != position:
                return VerifyResult(False, count, entry.sequence, f"sequence gap or reorder at position {position} (sequence {entry.sequence})")
            if entry.previous_hash != previous:
                return VerifyResult(False, count, entry.sequence, "broken link to the previous entry")
            if entry_hash(entry.sequence, entry.timestamp, entry.type, entry.body, entry.previous_hash) != entry.hash:
                return VerifyResult(False, count, entry.sequence, "entry content does not match its hash")
            previous = entry.hash
        return VerifyResult(True, count)

    def head(self) -> str:
        last = self.backend.last()
        return GENESIS if last is None else last.hash
