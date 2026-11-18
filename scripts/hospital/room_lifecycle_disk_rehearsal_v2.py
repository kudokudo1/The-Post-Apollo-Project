#!/usr/bin/env python3
"""CI-ONLY disposable disk-backed PX v10 Room Trash/Restore rehearsal.

NO executable service / no real PX data paths / no production authorization.
Creates a fresh private database in the GitHub runner's temporary directory
and refuses direct execution. Inputs cannot name a preexisting database.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path

class SyntheticOnly(RuntimeError):
    pass

# The triggers represent a proposed PX owner enforcement contract in a private
# test database. They are NOT installed into PX or the user's Hospital store.
TABLE_REFS = {
    "rooms": ("room_id",),
    "sessions": ("room_id",),
    "messages": ("room_id",),
    "room_checkpoints": ("room_id",),
    "room_reports": ("room_id",),
    "assignments": ("room_id",),
    "chart_entries": ("room_id", "source_room_id"),
    "chart_suggestions": ("room_id", "source_room_id"),
}

def _condition(alias, cols):
    refs = " OR ".join("l.room_id = " + alias + "." + col for col in cols)
    return "EXISTS (SELECT 1 FROM room_lifecycle_fixture l WHERE " \
        + "l.state='TRASHED' AND (" + refs + "))"

def _make_guards(conn):
    for table, cols in TABLE_REFS.items():
        for operation in ("INSERT", "UPDATE", "DELETE"):
            aliases = ("NEW",) if operation == "INSERT" else (
                ("OLD",) if operation == "DELETE" else ("OLD", "NEW"))
            predicate = " OR ".join(_condition(a, cols) for a in aliases)
            conn.execute(
                "CREATE TRIGGER fixture_guard_" + table + "_" + operation.lower()
                + " BEFORE " + operation + " ON " + table
                + " WHEN " + predicate
                + " BEGIN SELECT RAISE(ABORT,'TRASHED_ROOM_WRITE_REFUSED'); END"
            )
    # Session events have no room_id. Resolve their Room using the parent
    # Session on both old and new key paths.
    for operation in ("INSERT", "UPDATE", "DELETE"):
        aliases = ("NEW",) if operation == "INSERT" else (
            ("OLD",) if operation == "DELETE" else ("OLD", "NEW"))
        predicate = " OR ".join(
            "EXISTS (SELECT 1 FROM sessions s JOIN room_lifecycle_fixture l "
            "ON l.room_id=s.room_id WHERE l.state='TRASHED' "
            "AND s.session_id=" + alias + ".session_id)"
            for alias in aliases
        )
        conn.execute(
            "CREATE TRIGGER fixture_guard_session_events_"
            + operation.lower() + " BEFORE " + operation
            + " ON session_events WHEN " + predicate
            + " BEGIN SELECT RAISE(ABORT,'TRASHED_ROOM_WRITE_REFUSED'); END"
        )

def _require_ci():
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("CI") != "true":
        raise SyntheticOnly("CI_ONLY")
    base = os.environ.get("RUNNER_TEMP", "")
    path = Path(base)
    if not base or not path.is_absolute() or path.is_symlink() \
            or not path.is_dir() or not os.access(path, os.W_OK):
        raise SyntheticOnly("RUNNER_TEMP_REQUIRED")
    return path

class Scratch:
    """Create exactly one new, private PX-schema file; accept no DB path."""
    def __init__(self, px_module, v1):
        base = _require_ci()
        self._tmp = tempfile.TemporaryDirectory(
            prefix="hospital-lifecycle-disposable-", dir=str(base))
        self._path = Path(self._tmp.name) / "fixture.db"
        self._v1 = v1
        try:
            with self.connect() as db:
                px_module.migrate(db)
                for sql in v1.CREATE_SQL:
                    db.execute(sql)
                _make_guards(db)
        except BaseException:
            self._tmp.cleanup()
            raise

    @property
    def path(self):
        # Only test fixtures receive this path. Not a service/API entrypoint.
        return self._path

    @contextmanager
    def connect(self):
        if not self._path.parent.exists() or self._path.is_symlink() \
                or not str(self._path.resolve()).startswith(
                    str(Path(self._tmp.name).resolve()) + os.sep):
            raise SyntheticOnly("SCRATCH_PATH_CHANGED")
        con = sqlite3.connect(str(self._path), timeout=0.20,
                              isolation_level=None)
        con.row_factory = sqlite3.Row
        try:
            con.execute("PRAGMA foreign_keys=ON")
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA synchronous=FULL")
            yield con
        finally:
            con.close()

    def close(self):
        self._tmp.cleanup()

    def review(self, room_id, db=None):
        if db is None:
            with self.connect() as current:
                return self.review(room_id, current)
        self._v1._identity(room_id)
        graph, digest = self._v1._graph(db, room_id)
        entry = db.execute(
            "SELECT state,revision,frozen_digest FROM room_lifecycle_fixture "
            "WHERE room_id=?", (room_id,)).fetchone()
        state = str(entry["state"]) if entry else "ACTIVE"
        revision = int(entry["revision"]) if entry else 0
        blockers = []
        if any(str(a["status"]).upper() not in ("COMPLETE","CANCELLED")
               for a in graph["assignments"]):
            blockers.append("NONTERMINAL_ASSIGNMENT")
        if any(not str(s["ended_at"] or "").strip()
               or str(s["status"]).upper() not in ("COMPLETE","FAILED")
               or s["active_pid"] is not None
               for s in graph["sessions"]):
            blockers.append("SESSION_NOT_PROVEN_TERMINAL")
        assigned = str(graph["rooms"][0]["current_assignment_id"] or "")
        if assigned and not any(str(a["assignment_id"]) == assigned
                                for a in graph["assignments"]):
            blockers.append("UNKNOWN_CURRENT_ASSIGNMENT")
        if state == "TRASHED" and digest != str(entry["frozen_digest"]):
            blockers.append("TRASHED_GRAPH_CHANGED")
        return {
            "roomId":room_id, "revision":revision, "state":state,
            "digest":digest, "blockers":sorted(blockers),
            "counts":{key:len(rows) for key,rows in graph.items() if key!="rooms"},
            "syntheticOnly":True, "productionAuthority":False,
            "burnSupported":False
        }

    def transition(self, room_id, action, expected_revision, expected_digest):
        # No external connection can be supplied to the transaction API.
        if action not in ("TRASH", "RESTORE"):
            raise SyntheticOnly("BURN_AND_OTHER_ACTIONS_REFUSED")
        self._v1._identity(room_id)
        if type(expected_revision) is not int or not 0 <= expected_revision < 10**9:
            raise SyntheticOnly("EXPECTED_REVISION_REFUSED")
        if type(expected_digest) is not str or len(expected_digest)!=64 \
                or any(c not in "0123456789abcdef" for c in expected_digest):
            raise SyntheticOnly("EXPECTED_DIGEST_REFUSED")
        with self.connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                review = self.review(room_id, db)
                if review["revision"] != expected_revision:
                    raise SyntheticOnly("STALE_REVISION")
                if review["digest"] != expected_digest:
                    raise SyntheticOnly("STALE_GRAPH")
                if action == "TRASH":
                    if review["state"] != "ACTIVE":
                        raise SyntheticOnly("NOT_ACTIVE")
                    if review["blockers"]:
                        raise SyntheticOnly("ROOM_NOT_QUIESCENT")
                    target = "TRASHED"
                else:
                    if review["state"] != "TRASHED":
                        raise SyntheticOnly("NOT_TRASHED")
                    if "TRASHED_GRAPH_CHANGED" in review["blockers"]:
                        raise SyntheticOnly("TRASHED_GRAPH_CHANGED")
                    target = "ACTIVE"
                revision = review["revision"] + 1
                if expected_revision == 0:
                    db.execute(
                        "INSERT INTO room_lifecycle_fixture "
                        "(room_id,state,revision,frozen_digest) VALUES(?,?,?,?)",
                        (room_id,target,revision,review["digest"])
                    )
                else:
                    changed = db.execute(
                        "UPDATE room_lifecycle_fixture SET state=?,revision=?,"
                        "frozen_digest=?,changed_at=CURRENT_TIMESTAMP "
                        "WHERE room_id=? AND state=? AND revision=?",
                        (target,revision,review["digest"],room_id,
                         review["state"],expected_revision)
                    ).rowcount
                    if changed != 1:
                        raise SyntheticOnly("CAS_REFUSED")
                db.execute(
                    "INSERT INTO room_lifecycle_fixture_receipts "
                    "(room_id,action,revision_before,revision_after,graph_digest) "
                    "VALUES(?,?,?,?,?)",
                    (room_id,action,expected_revision,revision,review["digest"])
                )
                db.commit()
                return {"state":target,"revision":revision,"syntheticOnly":True}
            except BaseException:
                db.rollback()
                raise

    def visible_rooms(self):
        # Fixture-only projection; real PX 'rooms' command remains unfiltered.
        with self.connect() as db:
            return [row[0] for row in db.execute(
                "SELECT r.room_id FROM rooms r "
                "LEFT JOIN room_lifecycle_fixture l ON l.room_id=r.room_id "
                "WHERE l.state IS NULL OR l.state='ACTIVE' ORDER BY r.room_id"
            )]

if __name__ == "__main__":
    raise SystemExit("CI_FIXTURE_ONLY // NO LIVE DATABASE OR CLI")
