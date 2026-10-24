#!/usr/bin/env python3
"""M10x disposable, independent SQLite lifecycle REVIEW journal fixture.

Strictly separate from the existing tasks.db SQLite-v2 experiment and JSON
TASKS writer. No default path, production imports, CLI, background loops,
GitHub transport, remote identity verification, or remote ACK transitions.
The only stored state is HELD (not sendable). An explicit private
lifecycle-test.db file is required for initialization and every operation.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
from urllib.parse import quote

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "m10x_review_contract", _HERE / "ExperimentalTaskGitLifecycleM10w.py")
review = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(review)
StoreError = review.StoreError
InterruptedCommit = review.records.InterruptedCommit

FIXTURE_VERSION = 3  # Independent test-only fixture; NOT a migration of tasks.db.
ZERO_HASH = "0" * 64
_ID = re.compile(r"lx[1-9][0-9]*\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
MAX_RECORDS = 200


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def _digest(value):
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _pairs(items):
    value = {}
    for k, v in items:
        if k in value:
            raise StoreError("DUPLICATE_STORED_KEY")
        value[k] = v
    return value


def _decode(value):
    try:
        return json.loads(value, object_pairs_hook=_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(
                              StoreError("NONFINITE_STORED_VALUE")))
    except (TypeError, ValueError) as exc:
        raise StoreError("INVALID_STORED_JSON") from exc


def _path(file):
    if (not isinstance(file, Path) or not file.is_absolute()
            or file.name != "lifecycle-test.db"):
        raise StoreError("EXPLICIT_TEST_DB_PATH_REQUIRED")
    directory = file.parent
    if not directory.exists():
        raise StoreError("PRIVATE_TEST_DIRECTORY_REQUIRED")
    info = directory.lstat()
    if (directory.is_symlink() or not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.geteuid()
            or (stat.S_IMODE(info.st_mode) & 0o077)):
        raise StoreError("UNSAFE_TEST_DIRECTORY")
    if file.is_symlink():
        raise StoreError("UNSAFE_DB_LINK")
    if file.exists():
        info = file.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or (stat.S_IMODE(info.st_mode) & 0o077)):
            raise StoreError("UNSAFE_TEST_FILE")
    return file


def _connect(file, *, initialize=False, writable=False):
    file = _path(file)
    if initialize:
        fd = os.open(file, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                     getattr(os, "O_NOFOLLOW", 0), 0o600)
        os.close(fd)
        conn = sqlite3.connect(str(file), timeout=0.2, isolation_level=None)
    else:
        if not file.exists():
            if writable:
                raise StoreError("FIXTURE_ABSENT")
            return None
        uri = "file:" + quote(str(file), safe="/") + (
            "?mode=rw" if writable else "?mode=ro")
        conn = sqlite3.connect(uri, uri=True, timeout=0.2,
                               isolation_level=None)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=200")
        conn.execute("PRAGMA foreign_keys=ON")
        if initialize:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=FULL")
        elif writable:
            conn.execute("PRAGMA synchronous=FULL")
        return conn
    except Exception:
        conn.close()
        raise


def initialize(file):
    """Explicit test-only initialization. Never replaces an existing fixture."""
    con = _connect(file, initialize=True)
    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute("""CREATE TABLE meta (
            singleton INTEGER PRIMARY KEY CHECK(singleton=1),
            fixture_version INTEGER NOT NULL,
            revision INTEGER NOT NULL,
            next_id INTEGER NOT NULL,
            head_hash TEXT NOT NULL)""")
        con.execute("""CREATE TABLE intents (
            id TEXT PRIMARY KEY,
            position INTEGER NOT NULL UNIQUE,
            kind TEXT NOT NULL,
            task_id TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state='HELD'),
            source_json TEXT NOT NULL,
            preview_json TEXT NOT NULL,
            dependencies_json TEXT NOT NULL,
            prev_hash TEXT NOT NULL,
            entry_hash TEXT NOT NULL)""")
        con.execute("""CREATE TABLE tombstones (
            intent_id TEXT PRIMARY KEY REFERENCES intents(id),
            task_json TEXT NOT NULL,
            task_hash TEXT NOT NULL)""")
        con.execute("INSERT INTO meta VALUES(1,?,?,?,?)",
                    (FIXTURE_VERSION, 0, 1, ZERO_HASH))
        con.execute("PRAGMA user_version=3")
        con.commit()
        return {"status": "TEST_FIXTURE_INITIALIZED", "revision": 0,
                "headHash": ZERO_HASH, "remoteWriteAuthorized": False}
    finally:
        con.close()


def _request(preview):
    kind = preview["kind"]
    if kind == "CREATE_GIT_TASK":
        return {"kind":kind, "taskId":preview["taskId"]}
    if kind == "DELETE_GIT_TASK":
        return {"kind":kind, "taskId":preview["taskId"], "confirmed":True}
    if kind == "MOVE_GIT_TASK":
        return {"kind":kind, "taskId":preview["taskId"],
                "targetProjectId":preview["targetProjectId"]}
    raise StoreError("INVALID_LIFECYCLE_KIND")


def _body(identifier, position, kind, task_id, source, preview,
          dependencies, previous_hash):
    return {"id":identifier, "position":position, "kind":kind,
            "taskId":task_id, "state":"HELD", "source":source,
            "preview":preview, "dependencies":dependencies,
            "prevHash":previous_hash}


def _inspect(con):
    if con.execute("PRAGMA user_version").fetchone()[0] != FIXTURE_VERSION:
        raise StoreError("UNSUPPORTED_FIXTURE_SCHEMA")
    row = con.execute("SELECT * FROM meta WHERE singleton=1").fetchone()
    if row is None or con.execute("SELECT COUNT(*) FROM meta").fetchone()[0] != 1:
        raise StoreError("MISSING_FIXTURE_META")
    revision, next_id, head = row["revision"], row["next_id"], row["head_hash"]
    if (type(revision) is not int or type(next_id) is not int
            or revision < 0 or next_id < 1 or not _HASH.fullmatch(head)):
        raise StoreError("INVALID_FIXTURE_META")
    rows = con.execute("SELECT * FROM intents ORDER BY position").fetchall()
    if len(rows) > MAX_RECORDS:
        raise StoreError("FIXTURE_CAPACITY_EXCEEDED")
    entries, by_id, previous = [], {}, ZERO_HASH
    for pos, item in enumerate(rows):
        identifier = item["id"]
        if (not isinstance(identifier, str) or not _ID.fullmatch(identifier)
                or identifier != "lx" + str(pos + 1)
                or item["position"] != pos or item["state"] != "HELD"):
            raise StoreError("INVALID_INTENT_ORDER")
        source = _decode(item["source_json"])
        preview = _decode(item["preview_json"])
        deps = _decode(item["dependencies_json"])
        if (type(deps) is not list or any(type(d) is not str for d in deps)
                or len(deps) != len(set(deps))
                or any(d not in by_id for d in deps)):
            raise StoreError("INVALID_INTENT_DEPENDENCIES")
        if (item["kind"] != preview.get("kind")
                or item["task_id"] != preview.get("taskId")
                or preview.get("status") != "REVIEW_ONLY"
                or preview.get("remoteWriteAuthorized") is not False
                or preview.get("journalWriteAuthorized") is not False
                or preview.get("localWriteAuthorized") is not False
                or not review.review_current(
                    source, _request(preview), preview).get("current")):
            raise StoreError("INVALID_STORED_REVIEW")
        prior_task = [x for x in entries if x["taskId"] == item["task_id"]]
        if (any(x["kind"] == "DELETE_GIT_TASK" for x in prior_task)
                or any(x["id"] not in deps for x in prior_task)):
            raise StoreError("UNSAFE_TASK_DEPENDENCY_ORDER")
        body = _body(identifier, pos, item["kind"], item["task_id"],
                     source, preview, deps, previous)
        digest = _digest(body)
        if (item["prev_hash"] != previous or item["entry_hash"] != digest):
            raise StoreError("JOURNAL_HASH_CHAIN_MISMATCH")
        tomb = con.execute("SELECT * FROM tombstones WHERE intent_id=?",
                           (identifier,)).fetchone()
        if item["kind"] == "DELETE_GIT_TASK":
            if tomb is None:
                raise StoreError("MISSING_DELETE_TOMBSTONE")
            snapshot = _decode(tomb["task_json"])
            if (snapshot != preview["taskBefore"]
                    or tomb["task_hash"] != _digest(snapshot)):
                raise StoreError("TOMBSTONE_MISMATCH")
        elif tomb is not None:
            raise StoreError("UNEXPECTED_TOMBSTONE")
        entry = {"id":identifier, "kind":item["kind"],
                 "taskId":item["task_id"], "state":"HELD",
                 "dependencies":deps, "sourceRevision":preview["expectedRevision"],
                 "sourceHash":preview["expectedModelHash"],
                 "tombstone":copy.deepcopy(preview["taskBefore"])
                 if tomb is not None else None, "entryHash":digest}
        entries.append(entry)
        by_id[identifier] = entry
        previous = digest
    if (revision != len(entries) or next_id != len(entries) + 1
            or head != previous
            or con.execute("SELECT COUNT(*) FROM tombstones").fetchone()[0]
                != sum(x["kind"] == "DELETE_GIT_TASK" for x in entries)):
        raise StoreError("FIXTURE_META_OR_TOMBSTONE_DIVERGENCE")
    if con.execute("PRAGMA foreign_key_check").fetchall():
        raise StoreError("FIXTURE_FOREIGN_KEY_FAILURE")
    if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise StoreError("FIXTURE_INTEGRITY_FAILURE")
    return {"status":"REVIEW_HELD", "fixtureVersion":FIXTURE_VERSION,
            "revision":revision, "nextId":next_id, "headHash":head,
            "intents":entries, "remoteWriteAuthorized":False,
            "remoteSent":False, "remoteAcknowledged":False}


def read(file):
    """Verified, read-only view. Absent fixture does not create a database."""
    con = _connect(file)
    if con is None:
        return {"status":"ABSENT", "available":False}
    try:
        con.execute("BEGIN")
        return _inspect(con)
    finally:
        if con.in_transaction:
            con.rollback()
        con.close()


def append_held(file, *, expected_revision, expected_head,
                source_model, request, reviewed_preview,
                depends_on=(), stop_at=None):
    """Append a durable HELD review. DOES NOT queue a sendable remote intent."""
    if (type(expected_revision) is not int or expected_revision < 0
            or type(expected_head) is not str
            or _HASH.fullmatch(expected_head) is None
            or type(depends_on) not in (list, tuple)
            or len(depends_on) > MAX_RECORDS):
        raise StoreError("INVALID_FIXTURE_BASELINE")
    # Strict re-derivation before opening a writable handle.
    if not review.review_current(source_model, request,
                                 reviewed_preview).get("current"):
        raise StoreError("PREVIEW_INVALID_OR_STALE")
    source = copy.deepcopy(source_model)
    preview = copy.deepcopy(reviewed_preview)
    deps = list(depends_on)
    if len(deps) != len(set(deps)) or any(
            type(d) is not str or _ID.fullmatch(d) is None for d in deps):
        raise StoreError("INVALID_INTENT_DEPENDENCIES")
    con = _connect(file, writable=True)
    try:
        con.execute("BEGIN IMMEDIATE")
        try:
            current = _inspect(con)
            if (current["revision"] != expected_revision
                    or current["headHash"] != expected_head):
                raise StoreError("STALE_FIXTURE_BASELINE")
            if current["revision"] >= MAX_RECORDS:
                raise StoreError("FIXTURE_CAPACITY_EXCEEDED")
            previous = current["intents"]
            known = {x["id"] for x in previous}
            if any(d not in known for d in deps):
                raise StoreError("UNKNOWN_DEPENDENCY")
            previous_for_task = [x for x in previous
                                 if x["taskId"] == preview["taskId"]]
            if any(x["kind"] == "DELETE_GIT_TASK" for x in previous_for_task):
                raise StoreError("DELETION_ALREADY_PROPOSED")
            if any(x["id"] not in deps for x in previous_for_task):
                raise StoreError("TASK_DEPENDENCY_REQUIRED")
            identifier = "lx" + str(current["nextId"])
            body = _body(identifier, current["revision"], preview["kind"],
                         preview["taskId"], source, preview, deps,
                         current["headHash"])
            digest = _digest(body)
            review.records._stop(stop_at, "before_intent_insert")
            con.execute("INSERT INTO intents VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (identifier, current["revision"], preview["kind"],
                         preview["taskId"], "HELD", _canonical(source),
                         _canonical(preview), _canonical(deps),
                         current["headHash"], digest))
            review.records._stop(stop_at, "after_intent_insert")
            if preview["kind"] == "DELETE_GIT_TASK":
                snapshot = preview["taskBefore"]
                con.execute("INSERT INTO tombstones VALUES(?,?,?)",
                            (identifier, _canonical(snapshot), _digest(snapshot)))
            review.records._stop(stop_at, "after_tombstone_insert")
            con.execute("UPDATE meta SET revision=?,next_id=?,head_hash=? "
                        "WHERE singleton=1",
                        (current["revision"]+1, current["nextId"]+1, digest))
            review.records._stop(stop_at, "before_commit")
            con.commit()
        except Exception:
            if con.in_transaction:
                con.rollback()
            raise
        review.records._stop(stop_at, "after_commit")
        verified = _inspect(con)
        if (verified["headHash"] != digest or
                verified["intents"][-1]["id"] != identifier):
            raise StoreError("POST_COMMIT_VERIFICATION_FAILED")
        return {"status":"HELD_REVIEW_SAVED", "id":identifier,
                "revision":verified["revision"], "headHash":digest,
                "localReviewSaved":True, "journalWriteAuthorized":False,
                "remoteWriteAuthorized":False, "remoteSent":False}
    finally:
        con.close()
