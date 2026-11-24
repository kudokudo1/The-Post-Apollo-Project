"""M10: explicit ordinary local coordinated Save, no active UI or IPC.

Retain caller-known original identity and pair/candidate fingerprints before
any checkpoint write. Link the actual returned M8 attempt before fractional
dispatch. No recovery path invokes a writer; no unlinked attempt adoption.
This is a local reference, not native capture provenance or authorization.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import MachineV3OriginalSaveIdentity as original
from MachineGeometryStoreV2 import validate_pair
from MachineV3LocalSaveRecovery import _canonical_candidates, _digest, prepare_binding
from MachineV3LocalFractionalAttemptJournal import (
    LocalFractionalAttemptJournal, LocalAttempt, PREPARED, MARKED,
)
from MachineV3LocalExactCaptureStore import LocalExactCaptureStore
from MachineV3LocalCheckpointAdmission import admit_checkpoint
from MachineV2ExactLogicalGeometry import ExactLogicalRect, VALUE_VERSION, PHASE_CURRENT

TABLE = "machine_coordinated_save_intents_v1"
SCHEMA = """CREATE TABLE machine_coordinated_save_intents_v1 (
    id TEXT PRIMARY KEY NOT NULL,
    pair_sha256 TEXT NOT NULL,
    candidate_sha256 TEXT NOT NULL,
    fractional_attempt_id TEXT UNIQUE
)"""
MAX_INTENTS = 64
MATCH = "LOCAL_ORIGINAL_PAIR_OBSERVED_UNTRUSTED"
EXACT_MATCH = "BOTH_LOCAL_RECORDS_OBSERVED_UNTRUSTED"


class CoordinatedSaveRefused(ValueError):
    pass


def _refuse():
    raise CoordinatedSaveRefused("TIMEW COORDINATED LOCAL SAVE REFUSED") from None


def _context(journal, store):
    if type(journal) is not LocalFractionalAttemptJournal or type(store) is not LocalExactCaptureStore:
        _refuse()
    journal._store_context(store)


def _open(*, writable=False, create=False):
    conn = original._open(writable=writable, create=create)
    if conn is None:
        return None
    try:
        row = conn.execute("SELECT type,sql FROM sqlite_master WHERE name=?", (TABLE,)).fetchone()
        if row is None:
            if not create:
                conn.close()
                return None
            conn.execute(SCHEMA)
        elif tuple(row) != ("table", SCHEMA):
            _refuse()
        if conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0] > MAX_INTENTS:
            _refuse()
        return conn
    except original._ERRORS:
        conn.close()
        _refuse()


def _row(conn, cid):
    row = conn.execute(f"SELECT * FROM {TABLE} WHERE id=?", (cid,)).fetchone()
    if row is None:
        return None
    if (row["id"] != cid or any(type(row[k]) is not str
            or not original.DIGEST.fullmatch(row[k])
            for k in ("pair_sha256", "candidate_sha256"))):
        _refuse()
    if row["fractional_attempt_id"] is not None:
        original._id(row["fractional_attempt_id"])
    attempt = original._attempt(conn, cid)
    if attempt is None or attempt["pair_sha256"] != row["pair_sha256"]:
        _refuse()
    return tuple(row)


def _read(cid):
    conn = _open()
    if conn is None:
        return None
    try:
        return _row(conn, cid)
    finally:
        conn.close()


def _reserve(cid, pair_digest, candidate_digest):
    # Original reservation and coordinated intent are one transaction.
    conn = _open(writable=True, create=True)
    try:
        if (conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0] >= MAX_INTENTS
            or conn.execute(f"SELECT COUNT(*) FROM {original.TABLE}").fetchone()[0] >= original.MAX_ATTEMPTS
            or original._attempt(conn, cid) is not None
            or original._presence(conn, cid) != (False, False)):
            _refuse()
        conn.execute(f"INSERT INTO {original.TABLE} VALUES (?,?,?,NULL)",
                     (cid, pair_digest, original.PREPARED))
        conn.execute(f"INSERT INTO {TABLE} VALUES (?,?,?,NULL)",
                     (cid, pair_digest, candidate_digest))
        conn.commit()
    finally:
        conn.close()


def _link(cid, aid, pair_digest, candidate_digest):
    conn = _open(writable=True)
    try:
        if (_row(conn, cid) != (cid, pair_digest, candidate_digest, None)
                or original._attempt(conn, cid)["phase"] != original.COMMITTED):
            _refuse()
        updated = conn.execute(f"""UPDATE {TABLE} SET fractional_attempt_id=?
            WHERE id=? AND fractional_attempt_id IS NULL""", (aid, cid))
        if updated.rowcount != 1:
            _refuse()
        conn.commit()
    finally:
        conn.close()


def _observations(rows):
    return [
        {"window_key": r[0], "app_id": r[1], "output_id": r[2],
         "workspace_id": r[3], "value": ExactLogicalRect(
             VALUE_VERSION, PHASE_CURRENT, *(int(x, 16) for x in r[4:]))}
        for r in rows
    ]


def _result(cid, status, ordinary=None, fractional=None, aid=None):
    return dict(original._result(status, cid), ordinary_status=ordinary,
                fractional_status=fractional, fractional_attempt_id=aid,
                cross_database_atomic=False, dispatch_execution_verified=False,
                manual_review_required=True)


def recover(identity, *, journal, store):
    """Read-only composition; unknown/unlinked is never permission to continue."""
    cid = None
    try:
        cid = original._id(identity)
        _context(journal, store)
        row = _read(cid)
        if row is None:
            return _result(cid, "COORDINATED_SAVE_UNKNOWN_HOLD")
        ordinary = original.inspect(cid)["status"]
        aid = row[3]
        if ordinary != MATCH:
            return _result(cid, "ORDINARY_SAVE_UNRESOLVED_HOLD", ordinary, aid=aid)
        if aid is None:
            return _result(cid, "ORDINARY_OBSERVED_FRACTIONAL_UNLINKED_HOLD", ordinary)
        attempt = journal.get(aid)
        if (attempt is None or attempt.binding.checkpoint_id != cid
                or attempt.binding.candidate_digest != row[2]):
            return _result(cid, "FRACTIONAL_LINK_CONFLICT_HOLD", ordinary, aid=aid)
        evidence = journal.recover(aid, store=store)
        status = evidence["status"]
        if (_read(cid) != row or original.inspect(cid)["status"] != MATCH
                or journal.get(aid) != attempt):
            return _result(cid, "COORDINATED_SAVE_UNKNOWN_HOLD", aid=aid)
        if status == EXACT_MATCH and attempt.phase == MARKED:
            return _result(cid, "COORDINATED_LOCAL_RECORDS_OBSERVED_UNTRUSTED",
                           ordinary, status, aid)
        return _result(cid, "ORDINARY_OBSERVED_FRACTIONAL_UNRESOLVED_HOLD",
                       ordinary, status, aid)
    except original._ERRORS:
        return _result(cid, "COORDINATED_SAVE_UNKNOWN_HOLD")


def save_once(*, identity, v1_document, geometry_document, observations,
              journal, store, stage_hook=None):
    """New explicit caller-supplied local save only. No resume/retry entrypoint.

    Input must already be captured; current values are not derived from the
    integer pair. Hooks are for disposable tests, not a runtime dispatcher.
    """
    cid = None
    reserved = False
    try:
        cid = original._id(identity)
        _context(journal, store)
        old, geo = validate_pair(v1_document, geometry_document)
        _, _, _, pair_digest = original._pair(cid, old, geo)
        rows = tuple(_canonical_candidates(observations))
        expected = sorted((w["window_key"], w["app_id"], w["output"], w["workspace"])
                          for w in geo["windows"])
        if [r[:4] for r in rows] != expected:
            _refuse()
        candidate_digest = _digest(rows)
        exact = _observations(rows)
        _reserve(cid, pair_digest, candidate_digest)
        reserved = True
        if stage_hook:
            stage_hook("after_reserve")
        original.dispatch_once(identity=cid, v1_document=old, geometry_document=geo)
        if stage_hook:
            stage_hook("after_ordinary_commit")
        if original.inspect(cid)["status"] != MATCH:
            _refuse()
        # Do not fabricate or replace fractional observations.
        aid = journal.prepare(checkpoint_id=cid, observations=exact, store=store)
        if stage_hook:
            stage_hook("after_fractional_prepare")
        attempt = journal.get(aid)
        if (attempt is None or attempt.phase != PREPARED
                or attempt.binding.checkpoint_id != cid
                or attempt.binding.candidate_digest != candidate_digest
                or original.inspect(cid)["status"] != MATCH
                or attempt.binding != prepare_binding(checkpoint_id=cid, observations=exact)):
            _refuse()
        _link(cid, aid, pair_digest, candidate_digest)
        if stage_hook:
            stage_hook("after_link")
        journal.record_dispatch_marker(aid, store=store)
        if stage_hook:
            stage_hook("after_fractional_marker")
        # Last observation before explicit admission. Cannot close races
        # across independent databases; still ordinary untrusted data.
        if (original.inspect(cid)["status"] != MATCH
                or journal.get(aid) != LocalAttempt(aid, MARKED, attempt.binding, attempt.candidates)
                or journal.recover(aid, store=store)["status"] != "LEGACY_MATCH_LOCAL_EXACT_ABSENT"):
            _refuse()
        admit_checkpoint(checkpoint_id=cid, observations=exact, store=store)
        if stage_hook:
            stage_hook("after_fractional_commit")
        return recover(cid, journal=journal, store=store)
    except original._ERRORS:
        # Even a lost reserve reply may have committed; never repeat. A
        # duplicate input is not an accepted new attempt.
        if reserved:
            return recover(cid, journal=journal, store=store)
        _refuse()
