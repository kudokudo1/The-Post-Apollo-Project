#!/usr/bin/env python3
"""Hospital Room Trash -> Restore SQLite *in-memory fixture*.

NO LIVE ENTRYPOINT. NO PERSISTENT DB SUPPORT. NO OWNER AUTHORIZATION.
The source owner's PX Room writer does not consult this fixture and must not
treat its synthetic receipts or review as authority for production actions.
Only :memory: SQLite with the existing PX v10 schema can be mutated.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3

ROOM_ID = re.compile(r"^[A-Za-z0-9._:/-]{1,160}$")
MAX_ROWS_PER_RELATION = 10_000

CREATE_SQL = (
    """CREATE TABLE IF NOT EXISTS room_lifecycle_fixture (
        room_id TEXT PRIMARY KEY REFERENCES rooms(room_id) ON DELETE RESTRICT,
        state TEXT NOT NULL CHECK(state IN ('ACTIVE','TRASHED')),
        revision INTEGER NOT NULL CHECK(revision BETWEEN 1 AND 1000000000),
        frozen_digest TEXT NOT NULL,
        changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS room_lifecycle_fixture_receipts (
        receipt_id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id TEXT NOT NULL REFERENCES rooms(room_id) ON DELETE RESTRICT,
        action TEXT NOT NULL CHECK(action IN ('TRASH','RESTORE')),
        revision_before INTEGER NOT NULL,
        revision_after INTEGER NOT NULL,
        graph_digest TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(room_id,revision_after)
    )""",
)

# Every existing Room relation is preserved. Include inbound source-room
# references and session events, not just sessions directly linked to Room.
RELATIONS = (
    ("sessions", "room_id = ?", False),
    ("messages", "room_id = ?", False),
    ("room_checkpoints", "room_id = ? OR 1=0", False),
    ("room_reports", "room_id = ?", False),
    ("assignments", "room_id = ?", False),
    ("chart_entries", "room_id = ? OR source_room_id = ?", True),
    ("chart_suggestions", "room_id = ? OR source_room_id = ?", True),
)

class FixtureRefusal(RuntimeError):
    pass

def _require_fixture(conn):
    if not isinstance(conn, sqlite3.Connection):
        raise FixtureRefusal("CONNECTION_NOT_SQLITE")
    dbs = conn.execute("PRAGMA database_list").fetchall()
    if len(dbs) != 1 or str(dbs[0][1]) != "main" or str(dbs[0][2]):
        raise FixtureRefusal("DISK_OR_ATTACHED_DATABASE_REFUSED")
    try:
        row = conn.execute(
            "SELECT value FROM schema_meta WHERE key='schema_version'"
        ).fetchone()
    except sqlite3.OperationalError as exc:
        raise FixtureRefusal("PX_SCHEMA_MISSING") from exc
    if row is None or str(row[0]) != "10":
        raise FixtureRefusal("PX_V10_FIXTURE_REQUIRED")

def install_fixture(conn):
    """Install only in an in-memory PX v10 fixture, never on disk."""
    _require_fixture(conn)
    if conn.in_transaction:
        raise FixtureRefusal("OPEN_TRANSACTION_REFUSED")
    for sql in CREATE_SQL:
        conn.execute(sql)

def _ensure_tables(conn):
    _require_fixture(conn)
    for table in ("room_lifecycle_fixture", "room_lifecycle_fixture_receipts"):
        if conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone() is None:
            raise FixtureRefusal("LIFECYCLE_FIXTURE_NOT_INSTALLED")

def _identity(room_id):
    if type(room_id) is not str or not ROOM_ID.fullmatch(room_id):
        raise FixtureRefusal("ROOM_ID_REFUSED")
    return room_id

def _rows(conn, sql, args):
    result = conn.execute(sql + " LIMIT ?", (*args, MAX_ROWS_PER_RELATION + 1))
    rows = result.fetchall()
    if len(rows) > MAX_ROWS_PER_RELATION:
        raise FixtureRefusal("RELATED_GRAPH_TOO_LARGE")
    return [dict(row) for row in rows]

def _graph(conn, room_id):
    room = conn.execute(
        "SELECT * FROM rooms WHERE room_id=?", (room_id,)
    ).fetchone()
    if room is None:
        raise FixtureRefusal("ROOM_NOT_FOUND")
    snapshot = {"rooms": [dict(room)]}
    for table, where, twice in RELATIONS:
        params = (room_id, room_id) if twice else (room_id,)
        snapshot[table] = _rows(
            conn, "SELECT * FROM " + table + " WHERE " + where
            + " ORDER BY rowid", params
        )
    snapshot["session_events"] = _rows(
        conn, """SELECT e.* FROM session_events e
                 JOIN sessions s ON e.session_id=s.session_id
                 WHERE s.room_id=? ORDER BY e.rowid""", (room_id,)
    )
    digest = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    return snapshot, digest

def review(conn, room_id):
    """Metadata-only review. Digest covers sensitive bytes but reveals none."""
    _ensure_tables(conn)
    room_id = _identity(room_id)
    graph, digest = _graph(conn, room_id)
    lifecycle = conn.execute(
        "SELECT state,revision,frozen_digest FROM room_lifecycle_fixture "
        "WHERE room_id=?", (room_id,)
    ).fetchone()
    state = str(lifecycle[0]) if lifecycle else "ACTIVE"
    revision = int(lifecycle[1]) if lifecycle else 0
    blockers = []
    assignments = graph["assignments"]
    if any(str(a["status"]).upper() not in ("COMPLETE", "CANCELLED")
           for a in assignments):
        blockers.append("NONTERMINAL_ASSIGNMENT")
    if any(str(s["ended_at"] or "").strip() == ""
           or str(s["status"]).upper() not in ("COMPLETE", "FAILED")
           or s["active_pid"] is not None
           for s in graph["sessions"]):
        blockers.append("SESSION_NOT_PROVEN_TERMINAL")
    current_assignment_id = str(graph["rooms"][0].get("current_assignment_id") or "")
    if current_assignment_id and not any(
            str(a["assignment_id"]) == current_assignment_id
            for a in assignments):
        blockers.append("UNKNOWN_CURRENT_ASSIGNMENT")
    if state == "TRASHED" and digest != str(lifecycle[2]):
        blockers.append("TRASHED_GRAPH_CHANGED")
    return {
        "roomId": room_id, "state": state, "revision": revision,
        "digest": digest, "relatedCounts": {
            key: len(value) for key, value in graph.items() if key != "rooms"
        },
        "blockers": sorted(blockers),
        "syntheticOnly": True, "productionAuthority": False,
        "burnSupported": False,
    }

def visible_room_ids(conn):
    """Future PX query semantics, *not* wired into actual PX rooms_list."""
    _ensure_tables(conn)
    return [row[0] for row in conn.execute(
        """SELECT r.room_id FROM rooms r
           LEFT JOIN room_lifecycle_fixture l ON l.room_id=r.room_id
           WHERE l.state IS NULL OR l.state='ACTIVE'
           ORDER BY r.room_id"""
    ).fetchall()]

def transition(conn, room_id, action, expected_revision, expected_digest,
               *, fail_before_commit=False):
    """Atomic synthetic Room TRASH/RESTORE: no DELETE on original tables.

    Requests are untrusted fixture test inputs, not operator authorization.
    Refuses disk DBs, stale revisions, changed graphs, open work, and replay.
    """
    _ensure_tables(conn)
    _identity(room_id)
    if action not in ("TRASH", "RESTORE"):
        raise FixtureRefusal("BURN_AND_UNKNOWN_ACTION_REFUSED")
    if type(expected_revision) is not int or not (0 <= expected_revision < 10**9):
        raise FixtureRefusal("EXPECTED_REVISION_REFUSED")
    if type(expected_digest) is not str or not re.fullmatch(
            r"[0-9a-f]{64}", expected_digest):
        raise FixtureRefusal("EXPECTED_DIGEST_REFUSED")
    if conn.in_transaction:
        raise FixtureRefusal("OPEN_TRANSACTION_REFUSED")
    try:
        conn.execute("BEGIN IMMEDIATE")
        before = review(conn, room_id)
        if before["revision"] != expected_revision:
            raise FixtureRefusal("STALE_REVISION")
        if before["digest"] != expected_digest:
            raise FixtureRefusal("CHANGED_GRAPH")
        if action == "TRASH":
            if before["state"] != "ACTIVE":
                raise FixtureRefusal("ROOM_ALREADY_TRASHED")
            if before["blockers"]:
                raise FixtureRefusal("ROOM_NOT_QUIESCENT")
            after_state = "TRASHED"
        else:
            if before["state"] != "TRASHED":
                raise FixtureRefusal("ROOM_NOT_TRASHED")
            if "TRASHED_GRAPH_CHANGED" in before["blockers"]:
                raise FixtureRefusal("TRASHED_GRAPH_CHANGED")
            after_state = "ACTIVE"
        new_revision = before["revision"] + 1
        if before["revision"] == 0:
            conn.execute(
                """INSERT INTO room_lifecycle_fixture
                   (room_id,state,revision,frozen_digest)
                   VALUES(?,?,?,?)""",
                (room_id, after_state, new_revision, before["digest"])
            )
        else:
            changed = conn.execute(
                """UPDATE room_lifecycle_fixture
                   SET state=?,revision=?,frozen_digest=?,
                       changed_at=CURRENT_TIMESTAMP
                   WHERE room_id=? AND revision=? AND state=?""",
                (after_state, new_revision, before["digest"], room_id,
                 before["revision"], before["state"])
            ).rowcount
            if changed != 1:
                raise FixtureRefusal("CAS_STATE_CHANGED")
        conn.execute(
            """INSERT INTO room_lifecycle_fixture_receipts
               (room_id,action,revision_before,revision_after,graph_digest)
               VALUES(?,?,?,?,?)""",
            (room_id, action, before["revision"], new_revision, before["digest"])
        )
        if fail_before_commit:
            raise FixtureRefusal("INJECTED_CRASH_BEFORE_COMMIT")
        conn.commit()
        return {"roomId": room_id, "state": after_state,
                "revision": new_revision, "receiptRecorded": True,
                "syntheticOnly": True, "burnSupported": False}
    except BaseException:
        conn.rollback()
        raise

if __name__ == "__main__":
    raise SystemExit("FIXTURE_ONLY // NO PX OR LIVE ROOM COMMAND")
