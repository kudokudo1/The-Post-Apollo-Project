"""M9: explicit original local Save identity, no live UI/IPC entrypoint.

Reserve a caller-known checkpoint UUID and validated pair fingerprint before
dispatch. One-way mark before the actual write; both checkpoint rows and
local committed association share machine.db's transaction. No retry or
resume method. Readback is ordinary local data, not protected authorization.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import MachineCheckpointStore as legacy
from MachineGeometryStoreV2 import (
    TABLE as GEOMETRY_TABLE, MAX_BYTES, validate_pair, _raw, _insert_pair,
)
from MachineV3LocalExactCaptureStore import _safe_dir, _safe_file

TABLE = "machine_original_save_attempts_v1"
MAX_ATTEMPTS = 128
PREPARED = "PREPARED_HOLD"
MARKED = "DISPATCH_MARKED_UNKNOWN_HOLD"
COMMITTED = "LOCAL_PAIR_COMMITTED"
DIGEST = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
SCHEMA = """CREATE TABLE machine_original_save_attempts_v1 (
    id TEXT PRIMARY KEY NOT NULL,
    pair_sha256 TEXT NOT NULL,
    phase TEXT NOT NULL CHECK(phase IN ('PREPARED_HOLD','DISPATCH_MARKED_UNKNOWN_HOLD','LOCAL_PAIR_COMMITTED')),
    saved_at_utc TEXT,
    CHECK((phase='LOCAL_PAIR_COMMITTED' AND saved_at_utc IS NOT NULL)
          OR (phase!='LOCAL_PAIR_COMMITTED' AND saved_at_utc IS NULL))
)"""


class OriginalSaveRefused(ValueError):
    pass


def _refuse():
    raise OriginalSaveRefused("TIMEW ORIGINAL LOCAL SAVE REFUSED") from None


_ERRORS = (ValueError, TypeError, KeyError, AttributeError, OSError,
           sqlite3.Error, OverflowError, RecursionError)


def _id(value):
    if type(value) is not str:
        _refuse()
    u = uuid.UUID(value)
    if u.version != 4 or str(u) != value:
        _refuse()
    return value


def new_identity():
    """Pure ID allocation. The caller must retain it before prepare/dispatch."""
    return str(uuid.uuid4())


def _sha(raw):
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _pair(cid, old, geo):
    clean_old, clean_geo = validate_pair(old, geo)
    raw_v1 = json.dumps(clean_old, separators=(",", ":"), ensure_ascii=False)
    if len(raw_v1.encode("utf-8")) > legacy.MAX_DOC_BYTES:
        _refuse()
    raw_v2 = _raw(clean_geo).decode("utf-8")
    digest = _sha(json.dumps(
        ["timew-original-local-save-v1", cid, _sha(raw_v1), _sha(raw_v2)],
        separators=(",", ":"),
    ))
    return clean_old, raw_v1, raw_v2, digest


def _open(*, writable, create=False):
    path = legacy.db_path()
    if not path.is_absolute():
        _refuse()
    if not path.exists() and not path.is_symlink() and not create:
        return None
    _safe_dir(path.parent.parent, create=create)
    _safe_dir(path.parent, create=create)
    _safe_file(path)
    for suffix in ("-wal", "-shm", "-journal"):
        _safe_file(Path(str(path) + suffix))
    conn = legacy.connect(writable=writable)
    if conn is None:
        return None
    try:
        conn.execute("PRAGMA trusted_schema=OFF")
        conn.execute("PRAGMA foreign_keys=ON")
        if writable:
            conn.execute("BEGIN IMMEDIATE")
        else:
            conn.execute("PRAGMA query_only=ON")
            conn.execute("BEGIN")
        row = conn.execute(
            "SELECT type,sql FROM sqlite_master WHERE name=?", (TABLE,)
        ).fetchone()
        if row is None:
            if create:
                conn.execute(SCHEMA)
            else:
                conn.close()
                return None
        elif tuple(row) != ("table", SCHEMA):
            _refuse()
        if conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0] > MAX_ATTEMPTS:
            _refuse()
        return conn
    except _ERRORS:
        conn.close()
        _refuse()


def _attempt(conn, cid):
    row = conn.execute(f"SELECT * FROM {TABLE} WHERE id=?", (cid,)).fetchone()
    if row is None:
        return None
    if (row["id"] != cid or type(row["pair_sha256"]) is not str
            or not DIGEST.fullmatch(row["pair_sha256"])
            or row["phase"] not in (PREPARED, MARKED, COMMITTED)):
        _refuse()
    stamp = row["saved_at_utc"]
    if row["phase"] == COMMITTED:
        if type(stamp) is not str or legacy._utc(stamp) != stamp:
            _refuse()
    elif stamp is not None:
        _refuse()
    return row


def _presence(conn, cid):
    old = conn.execute("SELECT 1 FROM checkpoints WHERE id=?", (cid,)).fetchone()
    table = conn.execute(
        "SELECT type FROM sqlite_master WHERE name=?", (GEOMETRY_TABLE,)
    ).fetchone()
    if table is not None and table[0] != "table":
        _refuse()
    geo = None if table is None else conn.execute(
        f"SELECT 1 FROM {GEOMETRY_TABLE} WHERE checkpoint_id=?", (cid,)
    ).fetchone()
    return old is not None, geo is not None


def prepare(*, identity, v1_document, geometry_document):
    """Explicitly reserve the original UUID and exact pair digest; no save."""
    conn = None
    try:
        cid = _id(identity)
        _, _, _, digest = _pair(cid, v1_document, geometry_document)
        conn = _open(writable=True, create=True)
        if (conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0] >= MAX_ATTEMPTS
                or _attempt(conn, cid) is not None
                or _presence(conn, cid) != (False, False)):
            _refuse()
        conn.execute(f"INSERT INTO {TABLE} VALUES (?,?,?,NULL)", (cid, digest, PREPARED))
        conn.commit()
        return cid
    except _ERRORS:
        _refuse()
    finally:
        if conn is not None:
            conn.close()


def dispatch_once(*, identity, v1_document, geometry_document, stage_hook=None):
    """Explicit developer-only commit, using the original validated pair.

    Consume the local attempt by recording MARKED in a separate durable
    transaction. Failures after that never re-enter this method successfully
    for the same identity. The existing pair writer's insertion seam is
    shared, not its random-ID allocation or external transaction.
    """
    conn = None
    try:
        cid = _id(identity)
        old, raw_v1, raw_v2, digest = _pair(cid, v1_document, geometry_document)
        conn = _open(writable=True)
        if conn is None:
            _refuse()
        attempt = _attempt(conn, cid)
        if (attempt is None or attempt["phase"] != PREPARED
                or attempt["pair_sha256"] != digest
                or _presence(conn, cid) != (False, False)):
            _refuse()
        updated = conn.execute(f"UPDATE {TABLE} SET phase=? WHERE id=? AND phase=?",
                               (MARKED, cid, PREPARED))
        if updated.rowcount != 1:
            _refuse()
        conn.commit()
        conn.close()
        conn = None
        if stage_hook is not None:
            stage_hook("after_dispatch_marker")
        conn = _open(writable=True)
        if conn is None:
            _refuse()
        attempt = _attempt(conn, cid)
        if (attempt is None or attempt["phase"] != MARKED
                or attempt["pair_sha256"] != digest
                or _presence(conn, cid) != (False, False)):
            _refuse()
        now = datetime.now(timezone.utc).isoformat()
        _insert_pair(conn, cid=cid, now=now, legacy_doc=old,
                     raw_v1=raw_v1, raw_v2=raw_v2, digest=_sha(raw_v2),
                     stage_hook=stage_hook)
        updated = conn.execute(
            f"UPDATE {TABLE} SET phase=?,saved_at_utc=? WHERE id=? AND phase=? AND pair_sha256=?",
            (COMMITTED, now, cid, MARKED, digest),
        )
        if updated.rowcount != 1:
            _refuse()
        if stage_hook is not None:
            stage_hook("after_association")
        conn.commit()
        return cid
    except _ERRORS:
        _refuse()
    finally:
        if conn is not None:
            conn.close()


def _result(status, cid=None):
    return dict(
        status=status, checkpoint_id=cid, read_only=True, local_data_only=True,
        protected_attempt_verified=False, source_authenticated=False,
        operator_selection_verified=False, c5_spent_verified=False,
        native_receipt_verified=False, production_restore_allowed=False,
        automatic_retry_allowed=False, automatic_undo_allowed=False,
        safe_actions=[],
    )


def inspect(identity):
    """Read the original association and both rows in ONE local DB snapshot.

    No search by label/time/last saved, no reconstruction or retry. Absence
    does not establish a failed operation. A local match is not protected
    evidence of original source, capture instant, or operator authorization.
    """
    cid, conn = None, None
    try:
        cid = _id(identity)
        conn = _open(writable=False)
        if conn is None:
            return _result("ORIGINAL_SAVE_UNKNOWN_HOLD", cid)
        attempt = _attempt(conn, cid)
        if attempt is None:
            return _result("ORIGINAL_SAVE_UNKNOWN_HOLD", cid)
        present = _presence(conn, cid)
        if attempt["phase"] != COMMITTED:
            return _result(attempt["phase"] if present == (False, False)
                           else "ORIGINAL_SAVE_CONFLICT_HOLD", cid)
        if present != (True, True):
            return _result("ORIGINAL_SAVE_CONFLICT_HOLD", cid)
        old_size = conn.execute(
            "SELECT length(CAST(document_json AS BLOB)) FROM checkpoints WHERE id=?", (cid,)
        ).fetchone()[0]
        geo_size = conn.execute(
            f"SELECT length(CAST(geometry_json AS BLOB)) FROM {GEOMETRY_TABLE} WHERE checkpoint_id=?",
            (cid,),
        ).fetchone()[0]
        if (type(old_size) is not int or not 1 <= old_size <= legacy.MAX_DOC_BYTES
                or type(geo_size) is not int or not 1 <= geo_size <= MAX_BYTES):
            _refuse()
        old = conn.execute("SELECT * FROM checkpoints WHERE id=?", (cid,)).fetchone()
        geo = conn.execute(f"SELECT * FROM {GEOMETRY_TABLE} WHERE checkpoint_id=?", (cid,)).fetchone()
        clean, raw_v1, raw_v2, digest = _pair(
            cid, json.loads(old["document_json"]), json.loads(geo["geometry_json"])
        )
        if (old["id"] != cid or old["schema_version"] != legacy.SCHEMA_VERSION
                or old["label"] != clean["label"]
                or old["captured_at_utc"] != clean["captured_at_utc"]
                or old["saved_at_utc"] != attempt["saved_at_utc"]
                or geo["checkpoint_id"] != cid or geo["schema_version"] != 2
                or old["document_json"] != raw_v1 or geo["geometry_json"] != raw_v2
                or geo["geometry_sha256"] != _sha(raw_v2)
                or digest != attempt["pair_sha256"]):
            return _result("ORIGINAL_SAVE_CONFLICT_HOLD", cid)
        return _result("LOCAL_ORIGINAL_PAIR_OBSERVED_UNTRUSTED", cid)
    except _ERRORS:
        return _result("ORIGINAL_SAVE_UNKNOWN_HOLD", cid)
    finally:
        if conn is not None:
            conn.close()
