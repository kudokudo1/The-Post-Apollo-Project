"""Forest Core B5a // disposable host boundary mechanics, never authority.

This module deliberately cannot open an on-disk SQLite database, authenticate
a process, send text to a socket, issue C5 consent or activate ForestW.
It models two source-only seams: B1 owner+Tree bounded listing and a blocked
provisional B3 egress observation. Its output is NOT a trusted UI wire.
"""
from __future__ import annotations

import json
import re
import sqlite3

from session_journal_v0 import MAX_PAGE, SCHEMA_VERSION, _key

SCHEMA = "post-apollo.forest.host-contract-fixture.b5a"
MAX_FRAME_BYTES = 65536
MAX_DELTA_BYTES = 16000
MAX_TITLE_BYTES = 160
MAX_SAFE_TIME = 2**53 - 1
TREE_KEYS = frozenset(("CHERRY", "MAPLE", "BRISTLECONE_PINE",
                       "CEDAR", "MACINTOSH"))
TITLE_BLOCKED = re.compile(
    r"[\x00-\x1f\x7f\u202a-\u202e\u2066-\u2069]"
)
ROW_FIELDS = ("session_id", "tree_key", "title", "state", "revision",
              "created_at_ms", "updated_at_ms")


class HostFixtureHold(Exception):
    """Fixed refusal code only. Never expose SQLite or private payloads."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _fixture_db(db):
    """Only a single, already-open in-memory B1 fixture is even inspectable.

    This is NOT authentic custody: callers can fabricate these objects.
    No live on-disk DB or attached file is accepted, even for tests.
    """
    if type(db) is not sqlite3.Connection:
        raise HostFixtureHold("FIXTURE_DB_REQUIRED")
    try:
        if db.in_transaction:
            raise HostFixtureHold("ACTIVE_TRANSACTION")
        entries = db.execute("PRAGMA database_list").fetchall()
        if (len(entries) != 1 or entries[0][1] != "main"
                or entries[0][2] not in ("", ":memory:")):
            raise HostFixtureHold("DISK_OR_ATTACHED_DB_REFUSED")
        if db.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
            raise HostFixtureHold("UNSUPPORTED_SCHEMA")
        for table in ("forest_sessions", "forest_turns"):
            check = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()
            if check is None:
                raise HostFixtureHold("UNSUPPORTED_SCHEMA")
    except sqlite3.Error as exc:
        raise HostFixtureHold("FIXTURE_DB_UNAVAILABLE") from exc
    return db


def _scope(owner, tree):
    # Syntactic B1 owner/Tree values are NOT process or C5 authentication.
    try:
        owner, tree = _key(owner), _key(tree)
    except Exception as exc:
        raise HostFixtureHold("INVALID_FIXTURE_SCOPE") from exc
    if tree not in TREE_KEYS:
        raise HostFixtureHold("NONCANONICAL_PRESENTATION_TREE")
    return owner, tree


def _validate_row(row, tree):
    result = dict(zip(ROW_FIELDS, row))
    if (type(result["session_id"]) is not str
            or type(result["tree_key"]) is not str
            or result["tree_key"] != tree
            or type(result["title"]) is not str
            or not result["title"]
            or type(result["state"]) is not str
            or result["state"] != "OPEN"):
        raise HostFixtureHold("INVALID_FIXTURE_ROW")
    try:
        _key(result["session_id"])
        title_size = len(result["title"].encode("utf-8"))
    except Exception as exc:
        raise HostFixtureHold("INVALID_FIXTURE_ROW") from exc
    if (title_size > MAX_TITLE_BYTES or TITLE_BLOCKED.search(result["title"])
            or type(result["revision"]) is not int
            or not 0 <= result["revision"] <= MAX_SAFE_TIME
            or type(result["created_at_ms"]) is not int
            or type(result["updated_at_ms"]) is not int
            or not 0 < result["created_at_ms"] <=
                    result["updated_at_ms"] <= MAX_SAFE_TIME):
        raise HostFixtureHold("INVALID_FIXTURE_ROW")
    return result


def list_disposable_tree_fixture(db, *, owner, tree):
    """Exact Tree scope before LIMIT, one SELECT; no production list provider.

    B1 sessions(owner) is deliberately NOT reused: it limits across Trees.
    A 101st scoped OPEN record refuses a false complete 100-row snapshot.
    """
    db = _fixture_db(db)
    owner, tree = _scope(owner, tree)
    try:
        records = db.execute(
            "SELECT session_id,tree_key,title,state,revision,"
            "created_at_ms,updated_at_ms FROM forest_sessions "
            "WHERE owner_key=? AND tree_key=? AND state='OPEN' "
            "ORDER BY updated_at_ms DESC, session_id ASC LIMIT ?",
            (owner, tree, MAX_PAGE + 1),
        ).fetchall()
    except sqlite3.Error as exc:
        raise HostFixtureHold("FIXTURE_READ_UNAVAILABLE") from exc
    if len(records) > MAX_PAGE:
        raise HostFixtureHold("SNAPSHOT_TOO_LARGE")
    rows = [_validate_row(record, tree) for record in records]
    # No owner_key, transcript, model output, or writable handle serialized.
    report = {
        "schema": SCHEMA,
        "status": "DISPOSABLE_ROWS_UNAUTHENTICATED",
        "rows": rows,
        "complete_fixture": True,
        "sourceAuthenticated": False,
        "permissionGranted": False,
        "canListSessions": False,
        "mayDiscloseTitles": False,
        "productionAuthority": False,
        "safeActions": [],
    }
    try:
        raw = json.dumps(report, ensure_ascii=False, separators=(",", ":"))
        if len(raw.encode("utf-8")) > MAX_FRAME_BYTES:
            raise HostFixtureHold("FIXTURE_FRAME_LIMIT")
    except (UnicodeError, ValueError, TypeError) as exc:
        raise HostFixtureHold("INVALID_FIXTURE_ROW") from exc
    # NOT a LIST_SESSIONS response; cannot satisfy ForestW's exact schema.
    return report


class BlockedProvisionalEgressFixture:
    """Pure B3 DELTA observer. Does not hold an external sender or ACK.

    No bytes ever enter an OS socket/FD. Counting simulated bytes cannot
    authenticate a C5 one-use grant or linearize revocation with IPC writes.
    """

    def __init__(self):
        self._revoked = False
        self._seen = 0
        self._bytes = 0

    def observe(self, event):
        if self._revoked:
            raise HostFixtureHold("REVOKED_NO_NEW_ADMISSIONS")
        if (type(event) is not dict
                or set(event) != {"event", "text", "provisional"}
                or event["event"] != "DELTA"
                or event["provisional"] is not True
                or type(event["text"]) is not str
                or not event["text"]):
            raise HostFixtureHold("INVALID_PROVISIONAL_EVENT")
        try:
            size = len(event["text"].encode("utf-8"))
        except UnicodeError as exc:
            raise HostFixtureHold("INVALID_PROVISIONAL_EVENT") from exc
        if size > MAX_DELTA_BYTES or self._bytes + size > MAX_DELTA_BYTES:
            raise HostFixtureHold("PROVISIONAL_BUDGET_EXCEEDED")
        self._seen += 1
        self._bytes += size
        return self._report("BLOCKED_NO_EGRESS")

    def begin_revoke(self):
        self._revoked = True
        # No trusted issuer or verified recipient -> no fenced ACK.
        return self._report("REVOKE_REQUESTED_UNKNOWN_HOLD")

    def fence_ack(self):
        # Even when zero bytes were emitted locally, this model cannot
        # prove a kernel send queue or external recipient is drained.
        return self._report("UNKNOWN_HOLD_NO_NATIVE_FENCE")

    def _report(self, status):
        return {
            "schema": SCHEMA,
            "status": status,
            "simulatedChunksObserved": self._seen,
            "simulatedInputBytesObserved": self._bytes,
            "emittedBytes": 0,
            "inFlightSendsAuthenticated": False,
            "recipientAuthenticated": False,
            "issuerAuthenticated": False,
            "revocationFencedAck": False,
            "permissionGranted": False,
            "productionAuthority": False,
            "safeActions": [],
        }
