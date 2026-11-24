"""TimeW M8: ordinary local post-checkpoint fractional attempt custody.

Persist the original M7 binding and exact values before a future explicit
fractional admission. No dispatcher, writer to the capture stores, replay,
repair, CLI, or protected authority. A marker is NOT evidence of execution.
The older checkpoint must already exist; lost V1/V2 Save replies are outside
this contract. Same-user files and hashes are not rollback/tamper protection.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import sqlite3
import sys
import uuid
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import MachineCheckpointStore as legacy
from MachineV2ExactLogicalGeometry import (
    ExactLogicalRect, VALUE_VERSION, PHASE_CURRENT,
)
from MachineV3LocalExactCaptureStore import (
    LocalExactCaptureStore, MAX_RECORDS, HEX, _id, _safe_dir,
    _safe_file, _ensure_file,
)
from MachineV3LocalSaveRecovery import (
    LocalSaveBinding, prepare_binding, inspect_outcome,
    _canonical_candidates, _digest, _ERRORS,
)

DB_NAME = "v3-local-fractional-attempts.db"
SCHEMA_VERSION = 1
MAX_ATTEMPTS = 64
MAX_PAYLOAD_BYTES = 524288
DIGEST = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
PREPARED = "PREPARED_HOLD"
MARKED = "DISPATCH_MARKED_UNKNOWN_HOLD"
PHASES = (PREPARED, MARKED)
SCHEMA = """CREATE TABLE attempts (
    id TEXT PRIMARY KEY NOT NULL,
    checkpoint_id TEXT UNIQUE NOT NULL,
    phase TEXT NOT NULL CHECK(phase IN ('PREPARED_HOLD','DISPATCH_MARKED_UNKNOWN_HOLD')),
    payload TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL
)"""


class AttemptRefused(ValueError):
    pass


def _refuse():
    raise AttemptRefused("TIMEW LOCAL FRACTIONAL ATTEMPT REFUSED") from None


def suggested_path():
    return legacy.db_path().parent / DB_NAME


@dataclass(frozen=True, slots=True)
class LocalAttempt:
    id: str
    phase: str
    binding: LocalSaveBinding
    candidates: tuple

    def observations(self):
        # Fresh objects: no caller mutation of the retained original tuple.
        return [
            {"window_key": row[0], "app_id": row[1], "output_id": row[2],
             "workspace_id": row[3], "value": ExactLogicalRect(
                 VALUE_VERSION, PHASE_CURRENT, *(int(x, 16) for x in row[4:]))}
            for row in self.candidates
        ]


def _encode(attempt):
    if type(attempt) is not LocalAttempt or attempt.phase not in PHASES:
        _refuse()
    aid = _id(attempt.id, version=4)
    binding = attempt.binding
    if type(binding) is not LocalSaveBinding:
        _refuse()
    cid = _id(binding.checkpoint_id, version=4)
    if any(type(d) is not str or not DIGEST.fullmatch(d) for d in (
            binding.checkpoint_digest, binding.candidate_digest)):
        _refuse()
    rows = attempt.candidates
    if (type(rows) is not tuple or not 1 <= len(rows) <= MAX_RECORDS
            or any(type(row) is not tuple or len(row) != 8
                   or any(type(x) is not str for x in row)
                   or any(not HEX.fullmatch(x) for x in row[4:]) for row in rows)):
        _refuse()
    canonical = tuple(_canonical_candidates(attempt.observations()))
    if rows != canonical or _digest(rows) != binding.candidate_digest:
        _refuse()
    payload = {
        "id": aid, "checkpoint_id": cid,
        "checkpoint_digest": binding.checkpoint_digest,
        "candidate_digest": binding.candidate_digest,
        "candidates": rows,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if len(raw.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        _refuse()
    return raw, _digest(payload)


def _decode(row):
    raw = row["payload"]
    if type(raw) is not str or len(raw.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        _refuse()
    obj = json.loads(raw)
    if (type(obj) is not dict or set(obj) != {
            "id", "checkpoint_id", "checkpoint_digest", "candidate_digest", "candidates"}
            or obj["id"] != row["id"] or obj["checkpoint_id"] != row["checkpoint_id"]
            or type(obj["candidates"]) is not list
            or not 1 <= len(obj["candidates"]) <= MAX_RECORDS
            or any(type(x) is not list for x in obj["candidates"])):
        _refuse()
    attempt = LocalAttempt(
        obj["id"], row["phase"],
        LocalSaveBinding(obj["checkpoint_id"], obj["checkpoint_digest"], obj["candidate_digest"]),
        tuple(tuple(x) for x in obj["candidates"]),
    )
    rebuilt, digest = _encode(attempt)
    if raw != rebuilt or row["payload_sha256"] != digest:
        _refuse()
    return attempt


class LocalFractionalAttemptJournal:
    """Explicit local path, no startup IO; one retained attempt per checkpoint."""

    def __init__(self, path):
        if not isinstance(path, (str, Path)):
            _refuse()
        self.path = Path(path)
        self._context()

    def _context(self):
        if not self.path.is_absolute() or self.path != suggested_path():
            _refuse()

    def _store_context(self, store):
        self._context()
        if (type(store) is not LocalExactCaptureStore
                or store.path.parent != self.path.parent):
            _refuse()

    def _connect(self, *, writable=False, create=False):
        self._context()
        conn = None
        try:
            # Read/mark of a missing journal never creates it.
            if not self.path.exists() and not self.path.is_symlink() and not create:
                return None
            _safe_dir(self.path.parent.parent, create=create)
            _safe_dir(self.path.parent, create=create)
            if create:
                _ensure_file(self.path)
            if not _safe_file(self.path):
                _refuse()
            # No alternate WAL/SHM authority or symlinked rollback journal.
            for suffix in ("-wal", "-shm"):
                side = Path(str(self.path) + suffix)
                if side.exists() or side.is_symlink():
                    _refuse()
            side = Path(str(self.path) + "-journal")
            _safe_file(side)
            mode = "rw" if writable else "ro"
            conn = sqlite3.connect(
                "file:" + quote(str(self.path), safe="/") + "?mode=" + mode,
                uri=True, timeout=5.0,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA trusted_schema=OFF")
            conn.execute("PRAGMA busy_timeout=5000")
            if conn.execute("PRAGMA journal_mode").fetchone()[0] != "delete":
                _refuse()
            if writable:
                conn.execute("PRAGMA synchronous=FULL")
            else:
                conn.execute("PRAGMA query_only=ON")
            if writable:
                conn.execute("BEGIN IMMEDIATE")
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            objects = conn.execute(
                "SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
            ).fetchall()
            if version == 0 and create and not objects:
                conn.execute(SCHEMA)
                conn.execute("PRAGMA user_version=1")
                objects = conn.execute(
                    "SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
                ).fetchall()
                version = SCHEMA_VERSION
            if (version != SCHEMA_VERSION or len(objects) != 1
                    or tuple(objects[0]) != ("table", "attempts", SCHEMA)):
                _refuse()
            if conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] > MAX_ATTEMPTS:
                _refuse()
            return conn
        except _ERRORS:
            if conn is not None:
                conn.close()
            _refuse()

    @staticmethod
    def _read(conn, attempt_id):
        lengths = conn.execute(
            "SELECT length(CAST(payload AS BLOB)) FROM attempts WHERE id=?",
            (attempt_id,),
        ).fetchone()
        if lengths is None:
            return None
        if type(lengths[0]) is not int or not 1 <= lengths[0] <= MAX_PAYLOAD_BYTES:
            _refuse()
        row = conn.execute("SELECT * FROM attempts WHERE id=?", (attempt_id,)).fetchone()
        if row is None:
            _refuse()
        return _decode(row)

    def prepare(self, *, checkpoint_id, observations, store):
        """Persist original exact input only, prior to any fractional dispatch."""
        conn = None
        try:
            self._store_context(store)
            binding = prepare_binding(checkpoint_id=checkpoint_id, observations=observations)
            rows = tuple(_canonical_candidates(observations))
            attempt = LocalAttempt(str(uuid.uuid4()), PREPARED, binding, rows)
            raw, digest = _encode(attempt)
            # Do not claim a new attempt over already present/conflicting rows.
            if inspect_outcome(binding=binding, observations=attempt.observations(),
                               store=store)["status"] != "LEGACY_MATCH_LOCAL_EXACT_ABSENT":
                _refuse()
            conn = self._connect(writable=True, create=True)
            if conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] >= MAX_ATTEMPTS:
                _refuse()
            conn.execute(
                "INSERT INTO attempts VALUES (?,?,?,?,?)",
                (attempt.id, binding.checkpoint_id, PREPARED, raw, digest),
            )
            conn.commit()
            return attempt.id
        except _ERRORS:
            _refuse()
        finally:
            if conn is not None:
                conn.close()

    def get(self, attempt_id):
        conn = None
        try:
            aid = _id(attempt_id, version=4)
            conn = self._connect()
            if conn is None:
                return None
            # One read snapshot for size check and payload retrieval.
            conn.execute("BEGIN")
            return self._read(conn, aid)
        except _ERRORS:
            _refuse()
        finally:
            if conn is not None:
                conn.close()

    def list_ids(self):
        """Bounded discovery after a prepare reply is lost; no auto dispatch."""
        conn = None
        try:
            conn = self._connect()
            if conn is None:
                return []
            ids = conn.execute("SELECT id FROM attempts ORDER BY id LIMIT ?",
                               (MAX_ATTEMPTS + 1,)).fetchall()
            if len(ids) > MAX_ATTEMPTS:
                _refuse()
            return [_id(row[0], version=4) for row in ids]
        except _ERRORS:
            _refuse()
        finally:
            if conn is not None:
                conn.close()

    def record_dispatch_marker(self, attempt_id, *, store):
        """One-way local marker. Does not call a writer or grant permission."""
        conn = None
        try:
            self._store_context(store)
            original = self.get(attempt_id)
            if original is None or original.phase != PREPARED:
                _refuse()
            if inspect_outcome(binding=original.binding,
                               observations=original.observations(),
                               store=store)["status"] != "LEGACY_MATCH_LOCAL_EXACT_ABSENT":
                _refuse()
            conn = self._connect(writable=True)
            if conn is None or self._read(conn, original.id) != original:
                _refuse()
            changed = conn.execute(
                "UPDATE attempts SET phase=? WHERE id=? AND phase=?",
                (MARKED, original.id, PREPARED),
            )
            if changed.rowcount != 1:
                _refuse()
            conn.commit()
        except _ERRORS:
            _refuse()
        finally:
            if conn is not None:
                conn.close()

    def recover(self, attempt_id, *, store):
        """Observe retained original data, never dispatch or advance a phase."""
        try:
            self._store_context(store)
            attempt = self.get(attempt_id)
            if attempt is None:
                _refuse()
            result = inspect_outcome(
                binding=attempt.binding, observations=attempt.observations(), store=store)
            if self.get(attempt.id) != attempt:
                _refuse()
            return dict(result, attempt_id=attempt.id, journal_phase=attempt.phase,
                        dispatch_execution_verified=False,
                        manual_review_required=True)
        except _ERRORS:
            _refuse()
