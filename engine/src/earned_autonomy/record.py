"""The trust record (SPEC §5, §10): append-only, kept forever, tamper-evident.

Every entry is hash-chained: `hash = sha256(canonical_json({seq, ts, type, body, prev_hash}))`. `verify()`
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


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def entry_hash(seq: int, ts: str, type_: str, body: dict, prev_hash: str) -> str:
    blob = canonical({"seq": seq, "ts": ts, "type": type_, "body": body, "prev_hash": prev_hash})
    return "sha256:" + hashlib.sha256(blob.encode()).hexdigest()


@dataclass(frozen=True)
class Entry:
    seq: int
    ts: str
    type: str
    body: dict
    prev_hash: str
    hash: str


@dataclass
class VerifyResult:
    ok: bool
    entries: int
    first_bad_seq: int | None = None
    reason: str | None = None


class Backend(Protocol):
    def append(self, e: Entry) -> None: ...
    def last(self) -> Entry | None: ...
    def scan(self) -> Iterator[Entry]: ...
    def count(self) -> int: ...


class MemoryBackend:
    def __init__(self):
        self._rows: list[Entry] = []

    def append(self, e: Entry) -> None:
        self._rows.append(e)

    def last(self) -> Entry | None:
        return self._rows[-1] if self._rows else None

    def scan(self) -> Iterator[Entry]:
        return iter(list(self._rows))

    def count(self) -> int:
        return len(self._rows)


class SQLiteBackend:
    """One table, insert-only. Triggers refuse UPDATE and DELETE at the database level."""

    def __init__(self, path: str = ":memory:"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS trust_record (
                seq INTEGER PRIMARY KEY, ts TEXT NOT NULL, type TEXT NOT NULL,
                body TEXT NOT NULL, prev_hash TEXT NOT NULL, hash TEXT NOT NULL);
            CREATE TRIGGER IF NOT EXISTS trust_record_no_update BEFORE UPDATE ON trust_record
                BEGIN SELECT RAISE(ABORT, 'trust record is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS trust_record_no_delete BEFORE DELETE ON trust_record
                BEGIN SELECT RAISE(ABORT, 'trust record is append-only'); END;
        """)
        self.conn.commit()

    def append(self, e: Entry) -> None:
        self.conn.execute("INSERT INTO trust_record VALUES (?,?,?,?,?,?)",
                          (e.seq, e.ts, e.type, canonical(e.body), e.prev_hash, e.hash))
        self.conn.commit()

    def _row(self, r) -> Entry:
        return Entry(r[0], r[1], r[2], json.loads(r[3]), r[4], r[5])

    def last(self) -> Entry | None:
        r = self.conn.execute("SELECT * FROM trust_record ORDER BY seq DESC LIMIT 1").fetchone()
        return self._row(r) if r else None

    def scan(self) -> Iterator[Entry]:
        for r in self.conn.execute("SELECT * FROM trust_record ORDER BY rowid"):
            yield self._row(r)

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM trust_record").fetchone()[0]


class TrustRecord:
    """Append-only, hash-chained log. The single source of truth: all trust state is derived from it."""

    def __init__(self, backend: Backend | None = None):
        self.backend = backend if backend is not None else MemoryBackend()
        self._lock = threading.Lock()

    def append(self, type_: str, body: dict, ts: str) -> Entry:
        with self._lock:
            last = self.backend.last()
            seq = 0 if last is None else last.seq + 1
            prev = GENESIS if last is None else last.hash
            body = json.loads(canonical(body))          # freeze to plain JSON
            e = Entry(seq, ts, type_, body, prev, entry_hash(seq, ts, type_, body, prev))
            self.backend.append(e)
            return e

    def entries(self) -> Iterator[Entry]:
        return self.backend.scan()

    def __len__(self) -> int:
        return self.backend.count()

    def read_for(self, viewer_role: str) -> list[Entry]:
        """What a viewer may read. Agents see their record without sampling, canary or second-check entries."""
        rows = list(self.entries())
        if viewer_role == "agent":
            return [e for e in rows if e.type not in PRIVATE_TYPES]
        return rows

    def verify(self) -> VerifyResult:
        prev = GENESIS
        n = 0
        for i, e in enumerate(self.entries()):
            n += 1
            if e.seq != i:
                return VerifyResult(False, n, e.seq, f"sequence gap or reorder at position {i} (seq {e.seq})")
            if e.prev_hash != prev:
                return VerifyResult(False, n, e.seq, "broken link to the previous entry")
            if entry_hash(e.seq, e.ts, e.type, e.body, e.prev_hash) != e.hash:
                return VerifyResult(False, n, e.seq, "entry content does not match its hash")
            prev = e.hash
        return VerifyResult(True, n)

    def head(self) -> str:
        last = self.backend.last()
        return GENESIS if last is None else last.hash
