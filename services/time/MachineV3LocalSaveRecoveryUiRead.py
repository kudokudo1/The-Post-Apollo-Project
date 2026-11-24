#!/usr/bin/env python3
"""M11 read-only UI bridge for retained coordinated local Save intents.

Explicit list/inspect only. No captures, dispatch, repair or replay.
A request UUID correlates a response to a single UI request, not authority.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import MachineCheckpointStore as legacy
import MachineV3OriginalSaveIdentity as original
import MachineV3CoordinatedLocalSave as coordinated
from MachineV3LocalFractionalAttemptJournal import (
    LocalFractionalAttemptJournal, suggested_path as journal_path,
)
from MachineV3LocalExactCaptureStore import (
    LocalExactCaptureStore, suggested_path as capture_path, _safe_dir, _safe_file,
)

KIND = "timew-local-save-recovery-ui-v1"
MAX_IDS = coordinated.MAX_INTENTS
MAX_BYTES = 8192
UUID4 = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z", re.ASCII)
DENIALS = (
    "protected_attempt_verified", "source_authenticated",
    "operator_selection_verified", "c5_spent_verified",
    "native_receipt_verified", "production_restore_allowed",
    "automatic_retry_allowed", "automatic_undo_allowed",
    "cross_database_atomic", "dispatch_execution_verified",
)
MATCH = coordinated.MATCH
EXACT = coordinated.EXACT_MATCH
UNKNOWN = "COORDINATED_SAVE_UNKNOWN_HOLD"
ORDINARY = (
    original.PREPARED, original.MARKED,
    "ORIGINAL_SAVE_CONFLICT_HOLD", "ORIGINAL_SAVE_UNKNOWN_HOLD",
)
FRACTIONAL = (
    EXACT, "LEGACY_MATCH_LOCAL_EXACT_ABSENT",
    "CANDIDATE_CONFLICT_HOLD", "CHECKPOINT_CHANGED_HOLD",
    "LOCAL_EXACT_CONFLICT_HOLD", "LOCAL_SAVE_OUTCOME_UNKNOWN_HOLD",
)
RAW_KEYS = set(DENIALS) | {
    "status", "checkpoint_id", "read_only", "local_data_only", "safe_actions",
    "ordinary_status", "fractional_status", "fractional_attempt_id",
    "manual_review_required",
}


class RecoveryReadRefused(ValueError):
    pass


def _refuse():
    raise RecoveryReadRefused("TIMEW LOCAL SAVE RECOVERY READ REFUSED") from None


def _uuid(value):
    if type(value) is not str or not UUID4.fullmatch(value):
        _refuse()
    return value


def _packet(request_id, mode, checkpoint_id=None, *, status="UNAVAILABLE_HOLD",
            ordinary=None, fractional=None, aid=None, ids=()):
    result = dict(
        kind=KIND, request_id=request_id, mode=mode,
        checkpoint_id=checkpoint_id, status=status,
        ordinary_status=ordinary, fractional_status=fractional,
        fractional_attempt_id=aid, count=len(ids), intent_ids=list(ids),
        read_only=True, local_data_only=True, manual_review_required=True,
        safe_actions=[],
    )
    result.update({k: False for k in DENIALS})
    return result


def _discover():
    """One bounded local read snapshot, including pre-checkpoint attempts.

    Missing tables are not silently confused with corrupt association state.
    No checkpoint scan, journal adoption, digest or document disclosure.
    """
    path = legacy.db_path()
    if not path.is_absolute():
        _refuse()
    if not path.exists() and not path.is_symlink():
        return []
    _safe_dir(path.parent.parent, create=False)
    _safe_dir(path.parent, create=False)
    _safe_file(path)
    for suffix in ("-wal", "-shm", "-journal"):
        _safe_file(Path(str(path) + suffix))
    conn = legacy.connect(writable=False)
    if conn is None:
        _refuse()
    try:
        conn.execute("PRAGMA trusted_schema=OFF")
        conn.execute("PRAGMA query_only=ON")
        conn.execute("BEGIN")
        rows = conn.execute(
            "SELECT name,type,sql FROM sqlite_master WHERE name IN (?,?)",
            (original.TABLE, coordinated.TABLE),
        ).fetchall()
        schemas = {r["name"]: (r["type"], r["sql"]) for r in rows}
        if coordinated.TABLE not in schemas:
            return []
        if (schemas.get(coordinated.TABLE) != ("table", coordinated.SCHEMA)
                or schemas.get(original.TABLE) != ("table", original.SCHEMA)
                or conn.execute(f"SELECT COUNT(*) FROM {original.TABLE}").fetchone()[0]
                   > original.MAX_ATTEMPTS):
            _refuse()
        rows = conn.execute(f"SELECT id FROM {coordinated.TABLE} ORDER BY id LIMIT ?",
                            (MAX_IDS + 1,)).fetchall()
        if len(rows) > MAX_IDS:
            _refuse()
        ids = [_uuid(r[0]) for r in rows]
        if len(set(ids)) != len(ids):
            _refuse()
        for cid in ids:
            if coordinated._row(conn, cid) is None:
                _refuse()
        return ids
    finally:
        conn.close()


def _project(raw, cid, request_id):
    if (type(raw) is not dict or set(raw) != RAW_KEYS
            or raw["checkpoint_id"] != cid
            or any(raw[k] is not True for k in (
                "read_only", "local_data_only", "manual_review_required"))
            or any(raw[k] is not False for k in DENIALS)
            or type(raw["safe_actions"]) is not list or raw["safe_actions"]):
        _refuse()
    status, ordinary, fractional, aid = (
        raw["status"], raw["ordinary_status"], raw["fractional_status"],
        raw["fractional_attempt_id"],
    )
    if aid is not None:
        _uuid(aid)
    valid = (
        (status == UNKNOWN and ordinary is None and fractional is None)
        or (status == "ORDINARY_SAVE_UNRESOLVED_HOLD"
            and ordinary in ORDINARY and fractional is None)
        or (status == "ORDINARY_OBSERVED_FRACTIONAL_UNLINKED_HOLD"
            and ordinary == MATCH and fractional is None and aid is None)
        or (status == "FRACTIONAL_LINK_CONFLICT_HOLD"
            and ordinary == MATCH and fractional is None and aid is not None)
        or (status == "ORDINARY_OBSERVED_FRACTIONAL_UNRESOLVED_HOLD"
            and ordinary == MATCH and fractional in FRACTIONAL and aid is not None)
        or (status == "COORDINATED_LOCAL_RECORDS_OBSERVED_UNTRUSTED"
            and ordinary == MATCH and fractional == EXACT and aid is not None)
    )
    if not valid:
        _refuse()
    return _packet(request_id, "inspect", cid, status=status,
                   ordinary=ordinary, fractional=fractional, aid=aid)


def read_list(request_id):
    request_id = _uuid(request_id)
    try:
        ids = _discover()
        return _packet(request_id, "list", status="LOCAL_INTENTS_OBSERVED" if ids
                       else "NO_LOCAL_INTENTS_OBSERVED", ids=ids)
    except original._ERRORS:
        return _packet(request_id, "list")


def read_attempt(request_id, identity):
    request_id, cid = _uuid(request_id), _uuid(identity)
    try:
        journal = LocalFractionalAttemptJournal(journal_path())
        store = LocalExactCaptureStore(capture_path())
        return _project(coordinated.recover(cid, journal=journal, store=store),
                        cid, request_id)
    except original._ERRORS:
        return _packet(request_id, "inspect", cid)


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if len(args) == 2 and args[0] == "list":
            packet = read_list(args[1])
        elif len(args) == 3 and args[0] == "inspect":
            packet = read_attempt(args[1], args[2])
        else:
            _refuse()
        text = json.dumps(packet, ensure_ascii=True, separators=(",", ":"), allow_nan=False)
        if len(text.encode("utf-8")) > MAX_BYTES:
            _refuse()
        print(text)
        return 0
    except original._ERRORS:
        # Invalid invocation has no trustworthy correlation key.
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
