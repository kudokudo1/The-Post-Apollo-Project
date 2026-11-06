#!/usr/bin/env python3
"""TASKS M13y: post-exit read-only classification of the M12h synthetic ledger.

This inspector never constructs M10p Authority / M12h DisposableStageReceipt,
opens a DB write connection, writes JSON, repairs a journal, retries a stage,
or acknowledges a real saved task. Its results are non-authoritative review
hints for an operator. It is NOT mounted in Quickshell or usable on real tasks.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "m13y_existing_m12h", HERE / "TaskStageSourceReceiptM12h.py")
m12h = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m12h)

SHA = re.compile(r"[a-f0-9]{64}\Z")
LIMIT = 1000
COLS = {"stage_id", "owner_id", "epoch", "baseline_sha256",
        "expected_sha256", "actual_sha256", "state"}
PHASES = {"JSON_ACTIVE", "FREEZE_REQUESTED", "JSON_QUIESCED",
          "RECOVERY_REVIEW"}
NO_POWER = {
    "fixtureOnly": True, "journalReadOnly": True,
    "realTaskDataRead": False, "productionActivation": False,
    "nativeCallbackAuthenticated": False, "hostAuthenticated": False,
    "sourceOwnerAuthenticated": False, "consentAuthenticated": False,
    "captureAuthorized": False, "previewAuthorized": False,
    "deleteAuthorized": False, "restoreAuthorized": False,
    "keyReleaseAuthorized": False, "taskWriteAuthorized": False,
    "automaticReplayAuthorized": False, "savedAcknowledged": False,
    "clearDraftAuthorized": False,
}


def report(code, *, revision=None, pending=False, position="UNVERIFIED"):
    """Never expose source bytes, hashes, paths, IDs, writer names or drafts."""
    return {
        "classification": code, "lastSettledRevision": revision,
        "pendingStagePresent": pending, "sourcePosition": position,
        "draftDisposition": "KEEP_DRAFT",
        "lastConfirmedDisplay": "KEEP_LAST_CONFIRMED",
        "nextAction": "OPERATOR_REVIEW_ONLY",
        **NO_POWER,
    }


def strict_file(path):
    try:
        meta = path.lstat()
        if (path.is_symlink() or not stat.S_ISREG(meta.st_mode)
                or meta.st_uid != os.geteuid()
                or stat.S_IMODE(meta.st_mode) & 0o077
                or meta.st_nlink != 1):
            return False
        return True
    except OSError:
        return False


def inspect(db: Path):
    """No constructor accepting a caller assertion of native/auth ownership."""
    if (type(db) is not Path or not db.is_absolute()
            or db.name != "handoff-test.db"
            or db.parent.name != "m11e-fileview-test"):
        return report("REFUSED_NOT_DISPOSABLE_M12H_PATH")
    try:
        m12h.auth._private_directory(db)
        if not strict_file(db):
            return report("JOURNAL_UNAVAILABLE_OR_UNSAFE")
        lock = db.parent / "handoff-test.lock"
        if not strict_file(lock):
            return report("LOCK_UNAVAILABLE_OR_UNSAFE")
        fd = os.open(lock, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except Exception:
        return report("JOURNAL_UNAVAILABLE_OR_UNSAFE")
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except (BlockingIOError, OSError):
            return report("ACTIVE_OR_UNVERIFIED_OWNER_REFUSED")
        try:
            # Uses the EXISTING M11g safe-file reader, including O_NOFOLLOW,
            # inode/fstat and test-only exact document schema checks.
            before, doc = m12h.host.stable_file(m12h.host.fixture_file(db))
        except Exception:
            return report("SAVED_SOURCE_UNAVAILABLE_OR_UNSAFE")
        try:
            # SQLite ro/query_only perform no explicit application updates.
            # WAL mode may still manage transient -shm state internally.
            uri = "file:" + quote(str(db), safe="/") + "?mode=ro"
            with sqlite3.connect(uri, uri=True, timeout=0.2) as con:
                con.row_factory = sqlite3.Row
                con.execute("PRAGMA query_only=ON")
                con.execute("PRAGMA trusted_schema=OFF")
                if con.execute("PRAGMA user_version").fetchone()[0] != 1:
                    return report("JOURNAL_SCHEMA_UNVERIFIED")
                for table, columns in [
                    ("authority", {"id", "phase", "epoch", "owner_id",
                                   "pending_stage", "source_hash", "reason"}),
                    ("stage_receipts_m12h", COLS),
                ]:
                    meta = con.execute("PRAGMA table_info(" + table + ")").fetchall()
                    if {r["name"] for r in meta} != columns:
                        return report("JOURNAL_SCHEMA_UNVERIFIED")
                con.execute("BEGIN")
                authority = con.execute("SELECT * FROM authority LIMIT 2").fetchall()
                if len(authority) != 1:
                    return report("JOURNAL_STATE_UNVERIFIED")
                state = authority[0]
                if (state["id"] != 1 or state["phase"] not in PHASES
                        or type(state["epoch"]) is not int
                        or not 0 <= state["epoch"] < 999999999
                        or not m12h.auth._id(state["owner_id"])):
                    return report("JOURNAL_STATE_UNVERIFIED")
                pending = state["pending_stage"]
                if pending is not None and not m12h.auth._id(pending):
                    return report("JOURNAL_STATE_UNVERIFIED")
                records = con.execute(
                    "SELECT stage_id,owner_id,epoch,baseline_sha256,"
                    "expected_sha256,actual_sha256,state "
                    "FROM stage_receipts_m12h ORDER BY rowid LIMIT ?",
                    (LIMIT + 1,)).fetchall()
                if len(records) > LIMIT:
                    return report("JOURNAL_HISTORY_UNVERIFIED")
                try:
                    after, after_doc = m12h.host.stable_file(
                        m12h.host.fixture_file(db))
                except Exception:
                    return report("SAVED_SOURCE_UNAVAILABLE_OR_UNSAFE")
                if before != after or doc != after_doc:
                    return report("SOURCE_CHANGED_DURING_INSPECTION")
                # Reads are done; all further decisions use only this
                # immutable local set. Same-UID writers can still race after
                # return and are NOT fenced by the advisory lock.
                con.rollback()
        except (sqlite3.DatabaseError, OSError, ValueError, TypeError):
            return report("JOURNAL_UNREADABLE_OR_UNSAFE")

        last = None
        newest = None
        pending_row = None
        seen = set()
        for i, r in enumerate(records):
            stage = r["stage_id"]
            owner = r["owner_id"]
            epoch = r["epoch"]
            baseline = r["baseline_sha256"]
            expected = r["expected_sha256"]
            actual = r["actual_sha256"]
            state_name = r["state"]
            if (not m12h.auth._id(stage) or stage in seen
                    or not m12h.auth._id(owner)
                    or type(epoch) is not int or epoch < 0
                    or epoch > state["epoch"]
                    or type(baseline) is not str or not SHA.fullmatch(baseline)
                    or type(expected) is not str or not SHA.fullmatch(expected)):
                return report("JOURNAL_CHAIN_UNVERIFIED")
            seen.add(stage)
            if last is not None and baseline != last:
                return report("JOURNAL_CHAIN_UNVERIFIED")
            if state_name == "SETTLED_UNACKNOWLEDGED":
                if (actual != expected or pending_row is not None):
                    return report("JOURNAL_CHAIN_UNVERIFIED")
                last = actual
                newest = r
            elif state_name in ("RESERVED", "REVIEW_REQUIRED"):
                if (pending_row is not None or i != len(records)-1
                        or pending != stage):
                    return report("JOURNAL_CHAIN_UNVERIFIED")
                if actual is not None and (
                        type(actual) is not str or not SHA.fullmatch(actual)):
                    return report("JOURNAL_CHAIN_UNVERIFIED")
                pending_row = r
            else:
                return report("JOURNAL_CHAIN_UNVERIFIED")
        if (pending is None and pending_row is not None
                or pending is not None and pending_row is None):
            return report("JOURNAL_PENDING_MISMATCH")
        if (not records or newest is None) and pending_row is None:
            return report("NO_SETTLED_SOURCE_REVISION", revision=0,
                          position="BASELINE_NOT_ATTESTED")
        position_sha = hashlib.sha256(before).hexdigest()
        rev = sum(1 for r in records
                  if r["state"] == "SETTLED_UNACKNOWLEDGED")
        if newest is not None and newest["actual_sha256"] != last:
            return report("JOURNAL_CHAIN_UNVERIFIED")
        if pending_row is not None:
            if pending_row["state"] == "REVIEW_REQUIRED":
                return report("FAILED_STAGE_REQUIRES_REVIEW",
                              revision=rev, pending=True)
            if position_sha == pending_row["baseline_sha256"]:
                return report("RESERVED_SOURCE_STILL_AT_BASELINE",
                              revision=rev,pending=True,position="BASELINE")
            if position_sha == pending_row["expected_sha256"]:
                if doc["revision"] != rev+1:
                    return report("SOURCE_REVISION_UNVERIFIED",
                                  revision=rev,pending=True)
                return report("RESERVED_SOURCE_MATCHES_EXPECTED_UNACKNOWLEDGED",
                              revision=rev,pending=True,position="EXPECTED")
            return report("RESERVED_SOURCE_DIVERGED_REVIEW",
                          revision=rev,pending=True,position="OTHER")
        # All receipt rows settled. Saved bytes can be inspected, but a new
        # process may never infer that the original UI acknowledged them.
        if (last is None or doc["revision"] != rev or position_sha != last):
            return report("SETTLED_SOURCE_DIVERGED_REVIEW",
                          revision=rev,position="OTHER")
        return report("SETTLED_SOURCE_MATCHES_UI_UNACKNOWLEDGED",
                      revision=rev,position="LAST_SETTLED")
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def main():
    parser = argparse.ArgumentParser(
        description="M13y synthetic-only read-only post-crash inspection")
    parser.add_argument("--db", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(inspect(args.db),sort_keys=True))
    # Classification codes are data to review, never automatic action.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
