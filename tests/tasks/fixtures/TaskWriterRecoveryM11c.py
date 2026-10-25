#!/usr/bin/env python3
"""M11c durable, CONSUMABLE clean-quiescence evidence for disposable restart review.

Builds on M11b's private test coordinator and M10p's OS-owned flock. It never
rearms even simulated stage admission, authorizes SQLite, or opens live TASKS
storage. A matching checkpoint is only a one-time RECOVERY REVIEW CANDIDATE.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import re
import sqlite3

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    "m11c_existing_coordinator",
    ROOT / "tests/tasks/fixtures/TaskWriterCoordinationM11b.py")
coord = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coord)
AdmissionError = coord.AdmissionError
HASH = re.compile(r"[0-9a-f]{64}\Z")


def _result(reason, reviewable=False):
    return {"status":"REVIEW_CANDIDATE" if reviewable else "BLOCKED",
            "reason":reason, "reviewable":reviewable,
            "simulatedJsonStagePermitted":False,
            "legacyWriterEnforced":False,"sqliteWriteAuthorized":False,
            "remoteWriteAuthorized":False,"liveChangePerformed":False,
            "rearmPerformed":False}


class RecoveryCoordinator(coord.Coordinator):
    def __init__(self, db: Path, owner: str, *, bootstrap=False):
        super().__init__(db, owner, bootstrap=bootstrap)
        if bootstrap:
            def create(con, row):
                if (row["phase"] != "JSON_ACTIVE" or row["epoch"] != 0
                        or row["pending_stage"] is not None):
                    raise AdmissionError("INVALID_INITIAL_AUTHORITY")
                con.execute("""CREATE TABLE restart_review (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    checkpoint_epoch INTEGER,
                    source_hash TEXT,
                    consumed_epoch INTEGER,
                    CHECK(consumed_epoch IS NULL OR consumed_epoch>=0))""")
                con.execute("INSERT INTO restart_review VALUES(1,NULL,NULL,NULL)")
                return None
            self._owner._transition(create)

    def mark_quiescent_close(self):
        """Record a clean *source/owner checkpoint*, NOT a proven process exit.

        The caller must have performed freeze(), matching save callbacks and
        review_source_drain(). Both fresh reads and the authority must agree.
        """
        state = self._owner.snapshot()
        if (state["phase"] != "JSON_QUIESCED"
                or state["pendingStage"] is not None
                or type(state["sourceHash"]) is not str
                or HASH.fullmatch(state["sourceHash"]) is None):
            raise AdmissionError("SOURCE_NOT_QUIESCED")
        first = coord._read_exact(self._source)
        second = coord._read_exact(self._source)
        digest = hashlib.sha256(first).hexdigest()
        if first != second or digest != state["sourceHash"]:
            raise AdmissionError("SOURCE_CHANGED_AFTER_QUIESCENCE")

        def update(con, row):
            if (row["phase"] != "JSON_QUIESCED"
                    or row["pending_stage"] is not None
                    or row["source_hash"] != digest
                    or row["epoch"] != state["epoch"]):
                raise AdmissionError("AUTHORITY_CHANGED_DURING_CHECKPOINT")
            checkpoint = con.execute(
                "SELECT * FROM restart_review WHERE singleton=1").fetchone()
            if checkpoint is None or con.execute(
                    "SELECT COUNT(*) FROM restart_review").fetchone()[0] != 1:
                raise AdmissionError("RESTART_SCHEMA_CORRUPT")
            if checkpoint["checkpoint_epoch"] is not None:
                raise AdmissionError("CHECKPOINT_ALREADY_WRITTEN")
            con.execute("""UPDATE restart_review SET checkpoint_epoch=?,
                source_hash=?,consumed_epoch=NULL WHERE singleton=1""",
                (row["epoch"], digest))
            return _result("QUIESCENCE_CHECKPOINT_SAVED")
        return self._owner._transition(update)

    def inspect_restart(self, *, between_reads=None):
        """One-time re-review, never admission, under the *current* OS lock.

        A fresh M10p Authority always enters RECOVERY_REVIEW. A checkpoint
        cannot authorize a stage: evidence is advisory and may have been
        written before an abnormal process exit after quiescence.
        """
        state = self._owner.snapshot()
        if state["phase"] != "RECOVERY_REVIEW":
            return _result("NOT_IN_RECOVERY_REVIEW")
        # Catch missing/untrusted source without logging private bytes.
        try:
            first = coord._read_exact(self._source)
            if between_reads is not None:
                between_reads()  # tests only; cannot turn on admission
            second = coord._read_exact(self._source)
            stable = first == second
            current_sha = hashlib.sha256(second).hexdigest() if stable else None
        except (AdmissionError, OSError):
            stable = False
            current_sha = None

        def consume(con, row):
            if (row["phase"] != "RECOVERY_REVIEW"
                    or row["epoch"] != state["epoch"]
                    or row["owner_id"] != self._owner._writer_id):
                raise AdmissionError("STALE_RECOVERY_OWNER")
            if (con.execute("PRAGMA user_version").fetchone()[0] != 1
                    or con.execute(
                        "SELECT COUNT(*) FROM restart_review").fetchone()[0] != 1):
                raise AdmissionError("RESTART_SCHEMA_CORRUPT")
            checkpoint = con.execute(
                "SELECT * FROM restart_review WHERE singleton=1").fetchone()
            if checkpoint is None:
                raise AdmissionError("RESTART_SCHEMA_CORRUPT")
            if checkpoint["consumed_epoch"] is not None:
                return _result("CHECKPOINT_ALREADY_CONSUMED")
            # Persist consumption even when review fails: subsequent retries
            # must not turn a failed/mismatched read into a green signal.
            con.execute("""UPDATE restart_review SET consumed_epoch=?
                WHERE singleton=1""",(row["epoch"],))
            if (type(checkpoint["checkpoint_epoch"]) is not int
                    or type(checkpoint["source_hash"]) is not str
                    or HASH.fullmatch(checkpoint["source_hash"]) is None):
                return _result("NO_VERIFIABLE_CHECKPOINT")
            if (row["epoch"] != checkpoint["checkpoint_epoch"] + 1
                    or row["reason"] != "NEW_PROCESS_MUST_REVIEW"):
                return _result("OWNER_EPOCH_OR_RECOVERY_REASON_MISMATCH")
            if row["pending_stage"] is not None:
                return _result("UNSETTLED_SAVE_AFTER_RESTART")
            if (not stable or current_sha != checkpoint["source_hash"]
                    or row["source_hash"] != checkpoint["source_hash"]):
                return _result("SOURCE_MISMATCH_ON_RESTART")
            return _result("QUIESCENT_CHECKPOINT_MATCHED_FOR_REVIEW", True)
        return self._owner._transition(consume)
