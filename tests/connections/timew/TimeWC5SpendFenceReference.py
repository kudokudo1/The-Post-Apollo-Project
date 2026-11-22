"""CI-ONLY TimeW Scope A C5 spend/revoke ordering reference, NEVER authority.

All claims, times and SQLite files are caller-controlled test fixtures. This
module cannot issue consent, authenticate an installed producer, authorize a
SwayPX command or acknowledge a real-world revocation. Production must use a
separately custodied protected issuer and a reviewed cross-store receipt flow.
"""
from __future__ import annotations

import re
import sqlite3
import uuid
from pathlib import Path

AUDIENCE = "post-apollo.connections.c5.timew.scope-a.reference.v1"
ACTION = "one-selected-live-surface-geometry-operation"
MAX_MS = 9007199254740991
MAX_TTL_MS = 10000  # Reference cap; not an approved native consent lifetime.
FIELDS = frozenset((
    "audience", "action", "grant_id", "operation_id", "selection_sha256",
    "intent_sha256", "source_sha256", "session_id", "seat_id", "issuer_epoch",
    "issued_ms", "expires_ms",
))
HEX = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)


class ReferenceRefused(ValueError):
    pass


def _refuse():
    raise ReferenceRefused("TIMEW C5 REFERENCE REFUSED; NO NATIVE AUTHORITY")


def _uuid4(value):
    if type(value) is not str:
        _refuse()
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        _refuse()
    if parsed.version != 4 or str(parsed) != value:
        _refuse()
    return value


def _ms(value):
    if type(value) is not int or not 0 <= value <= MAX_MS:
        _refuse()
    return value


def _hash(value):
    if type(value) is not str or HEX.fullmatch(value) is None:
        _refuse()
    return value


def _claim(value):
    if not isinstance(value, dict) or set(value) != FIELDS:
        _refuse()
    if value["audience"] != AUDIENCE or value["action"] != ACTION:
        _refuse()
    for field in ("grant_id", "operation_id", "session_id", "issuer_epoch"):
        _uuid4(value[field])
    for field in ("selection_sha256", "intent_sha256", "source_sha256"):
        _hash(value[field])
    seat = value["seat_id"]
    if (type(seat) is not str or not 1 <= len(seat) <= 128
            or any(not 33 <= ord(ch) <= 126 for ch in seat)):
        _refuse()
    issued, expires = _ms(value["issued_ms"]), _ms(value["expires_ms"])
    if expires <= issued or expires - issued > MAX_TTL_MS:
        _refuse()
    return dict(value)  # Freeze the validated fixture against later mutation.


def _deny(state):
    return {
        "fixture_state": state,
        "production_authorized": False,
        "native_action_allowed": False,
        "production_revocation_ack": False,
        "retry_allowed": False,
        "undo_allowed": False,
        "safe_actions": [],
    }


class TestOnlyC5Fence:
    """Disposable SQLite ordering reference, NOT a protected consent ledger.

    A same-UID writer can replace/rollback this database; nothing here pins a
    signing key, original process, seat, active session, compositor selection,
    release, or independent revocation authority. No command API exists.
    """

    def __init__(self, path):
        if not isinstance(path, (str, Path)):
            _refuse()
        self.path = Path(path)
        if not self.path.is_absolute() or self.path.suffix != ".db":
            _refuse()

    def initialize_fixture(self):
        # Tests alone call this. No implicit initialization from a spend/read.
        db = sqlite3.connect(str(self.path), timeout=10, isolation_level=None)
        try:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            db.execute("""CREATE TABLE IF NOT EXISTS grants (
                grant_id TEXT PRIMARY KEY,
                operation_id TEXT NOT NULL UNIQUE,
                selection_sha256 TEXT NOT NULL,
                intent_sha256 TEXT NOT NULL UNIQUE,
                source_sha256 TEXT NOT NULL,
                session_id TEXT NOT NULL,
                seat_id TEXT NOT NULL,
                issuer_epoch TEXT NOT NULL,
                issued_ms INTEGER NOT NULL,
                expires_ms INTEGER NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('ACTIVE','SPENT','REVOKED')),
                revocation_requested INTEGER NOT NULL DEFAULT 0,
                spent_ms INTEGER
            )""")
            db.execute("PRAGMA user_version=1")
            db.commit()
        finally:
            db.close()

    def _open(self):
        # mode=rw avoids silently creating a replacement 'unspent' store.
        if not self.path.is_file() or self.path.is_symlink():
            _refuse()
        try:
            db = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True,
                                 timeout=10, isolation_level=None)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA synchronous=FULL")
            if db.execute("PRAGMA user_version").fetchone()[0] != 1:
                _refuse()
            return db
        except sqlite3.Error:
            _refuse()

    def register_fixture(self, claim):
        claim = _claim(claim)
        db = self._open()
        try:
            db.execute("BEGIN IMMEDIATE")
            db.execute("""INSERT INTO grants (
                grant_id, operation_id, selection_sha256, intent_sha256,
                source_sha256, session_id, seat_id, issuer_epoch,
                issued_ms, expires_ms, state
            ) VALUES (?,?,?,?,?,?,?,?,?,?,'ACTIVE')""", tuple(claim[k] for k in (
                "grant_id", "operation_id", "selection_sha256", "intent_sha256",
                "source_sha256", "session_id", "seat_id", "issuer_epoch",
                "issued_ms", "expires_ms")))
            db.commit()
        except sqlite3.Error:
            db.rollback()
            _refuse()
        finally:
            db.close()
        return _deny("ACTIVE_UNTRUSTED_FIXTURE")

    def spend_fixture(self, claim, *, now_ms):
        claim, now_ms = _claim(claim), _ms(now_ms)
        db = self._open()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM grants WHERE grant_id=?",
                             (claim["grant_id"],)).fetchone()
            if (row is None or row["state"] != "ACTIVE"
                    or row["revocation_requested"] != 0
                    or not claim["issued_ms"] <= now_ms < claim["expires_ms"]
                    or any(row[k] != claim[k] for k in (
                        "operation_id", "selection_sha256", "intent_sha256",
                        "source_sha256", "session_id", "seat_id", "issuer_epoch",
                        "issued_ms", "expires_ms"))):
                _refuse()
            db.execute("UPDATE grants SET state='SPENT',spent_ms=? WHERE grant_id=?",
                       (now_ms, claim["grant_id"]))
            db.commit()
        except (sqlite3.Error, ReferenceRefused):
            db.rollback()
            _refuse()
        finally:
            db.close()
        # The reference models write ordering only. Even SPENT is no permit.
        return _deny("SPENT_UNKNOWN_HOLD")

    def revoke_fixture(self, grant_id):
        grant_id = _uuid4(grant_id)
        db = self._open()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT state FROM grants WHERE grant_id=?",
                             (grant_id,)).fetchone()
            if row is None:
                _refuse()
            if row["state"] == "ACTIVE":
                db.execute("UPDATE grants SET state='REVOKED',revocation_requested=1 "
                           "WHERE grant_id=?", (grant_id,))
                state = "REVOKED_BEFORE_SPEND_FIXTURE"
            else:
                db.execute("UPDATE grants SET revocation_requested=1 WHERE grant_id=?",
                           (grant_id,))
                state = ("SPENT_REVOCATION_PENDING_UNKNOWN_HOLD"
                         if row["state"] == "SPENT" else "REVOKED_BEFORE_SPEND_FIXTURE")
            db.commit()
        except (sqlite3.Error, ReferenceRefused):
            db.rollback()
            _refuse()
        finally:
            db.close()
        return _deny(state)

    def inspect_fixture(self, grant_id):
        grant_id = _uuid4(grant_id)
        db = self._open()
        try:
            row = db.execute("SELECT state,revocation_requested FROM grants WHERE grant_id=?",
                             (grant_id,)).fetchone()
        except sqlite3.Error:
            _refuse()
        finally:
            db.close()
        if row is None:
            state = "ABSENT_UNKNOWN_HOLD"
        elif row["state"] == "ACTIVE":
            state = "ACTIVE_UNTRUSTED_FIXTURE"
        elif row["state"] == "REVOKED":
            state = "REVOKED_BEFORE_SPEND_FIXTURE"
        else:
            state = ("SPENT_REVOCATION_PENDING_UNKNOWN_HOLD"
                     if row["revocation_requested"] else "SPENT_UNKNOWN_HOLD")
        return _deny(state)
