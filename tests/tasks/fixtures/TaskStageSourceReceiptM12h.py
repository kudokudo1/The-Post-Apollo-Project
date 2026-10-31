#!/usr/bin/env python3
"""M12h // isolated SQLite stage-to-source receipt experiment.

Uses the existing M10p disposable Authority and M11g strict synthetic
source parser. Extends ONLY a freshly bootstrapped M11e fixture database
with stage-scoped metadata. The *test* FileView replacement is external;
this module NEVER writes the JSON source, real TASKS, or Quickshell config.

All methods are lab mechanics, NOT independently trusted OS host authority.
The M10p flock is advisory; non-cooperating same-user writers remain a threat.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import re
import sqlite3

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "tests/tasks/fixtures"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


host = _load("m12h_disposable_m11g_host",
             FIXTURES / "TaskFileViewOwnerHostM11g.py")
# Reuse M11g's already loaded M10p module. Importing the same Python file
# twice under distinct names creates unrelated AdmissionError classes and
# would break fail-closed handling for missing/unsafe source readbacks.
auth = host.auth
AdmissionError = auth.AdmissionError
SHA = re.compile(r"[a-f0-9]{64}\Z")

DDL = """CREATE TABLE stage_receipts_m12h (
    stage_id TEXT PRIMARY KEY NOT NULL,
    owner_id TEXT NOT NULL,
    epoch INTEGER NOT NULL,
    baseline_sha256 TEXT NOT NULL,
    expected_sha256 TEXT NOT NULL,
    actual_sha256 TEXT,
    state TEXT NOT NULL CHECK(state IN
      ('RESERVED','SETTLED_UNACKNOWLEDGED','REVIEW_REQUIRED'))
)"""


def sha(raw: bytes):
    return hashlib.sha256(raw).hexdigest()


class DisposableStageReceipt:
    """Stage-bound receipt within the *same* disposable M10p SQLite journal.

    M10p's private transition method is used for this isolated experimental
    fixture so the stage reservation and its hashes share one DB transaction.
    Production MUST use a separately audited public host API, not this seam.
    """

    def __init__(self, db: Path, owner_id: str, *, bootstrap=False):
        if (not isinstance(db, Path) or not db.is_absolute()
                or db.name != "handoff-test.db"
                or db.parent.name != "m11e-fileview-test"):
            raise AdmissionError("M11E_DISPOSABLE_JOURNAL_ONLY")
        self.owner = None
        self.db = db
        self.file = host.fixture_file(db)
        # Verify real fixture file BEFORE constructing SQLite authority.
        initial, _ = host.stable_file(self.file)
        try:
            self.owner = auth.Authority(db, owner_id, bootstrap=bootstrap)
            self.owner_id = owner_id
            self.confirmed = initial
            if bootstrap:
                def setup(con, row):
                    if (row["phase"] != "JSON_ACTIVE"
                            or row["pending_stage"] is not None
                            or row["epoch"] != 0):
                        raise AdmissionError("INITIAL_AUTHORITY_UNEXPECTED")
                    con.execute(DDL)
                self.owner._transition(setup)
            else:
                self._check_schema()
        except BaseException:
            self.close()
            raise

    def _check_schema(self):
        con = self.owner._guard()
        cols = {r[1] for r in con.execute(
            "PRAGMA table_info(stage_receipts_m12h)")}
        if cols != {"stage_id","owner_id","epoch","baseline_sha256",
                    "expected_sha256","actual_sha256","state"}:
            raise AdmissionError("M12H_RECEIPT_SCHEMA_UNAVAILABLE")

    def snapshot(self):
        state = self.owner.snapshot()
        con = self.owner._guard()
        rows = con.execute(
            "SELECT stage_id,epoch,baseline_sha256,expected_sha256,"
            "actual_sha256,state FROM stage_receipts_m12h ORDER BY rowid"
        ).fetchall()
        evidence = []
        for r in rows:
            if (not SHA.fullmatch(r["baseline_sha256"])
                    or not SHA.fullmatch(r["expected_sha256"])
                    or (r["actual_sha256"] is not None and
                        not SHA.fullmatch(r["actual_sha256"]))):
                raise AdmissionError("M12H_RECEIPT_CORRUPT")
            evidence.append({
                "stageId":r["stage_id"], "epoch":r["epoch"],
                "baselineSha256":r["baseline_sha256"],
                "expectedSha256":r["expected_sha256"],
                "actualSha256":r["actual_sha256"],
                "receiptState":r["state"]})
        return {"phase":state["phase"],"epoch":state["epoch"],
                "pendingStage":state["pendingStage"],"receipts":evidence,
                "syntheticOnly":True,"productionWriterAuthorized":False,
                "nativeCallbackStageProven":False,
                "independentTrustedSignerProven":False}

    def reserve(self, stage_id: str):
        if not auth._id(stage_id):
            raise AdmissionError("INVALID_SYNTHETIC_STAGE")
        source, doc = host.stable_file(self.file)
        if source != self.confirmed:
            raise AdmissionError("EXTERNAL_SOURCE_BEFORE_RESERVE")
        expected = host.encode_next(doc)

        def tx(con, row):
            # Recheck after beginning the transaction. This remains only
            # protection against cooperating writers and ordinary drift.
            now, _ = host.stable_file(self.file)
            if now != source:
                raise AdmissionError("SOURCE_CHANGED_AT_RESERVATION")
            if row["phase"] != "JSON_ACTIVE" or row["pending_stage"] is not None:
                raise AdmissionError("STAGE_ADMISSION_REFUSED")
            con.execute(
                "INSERT INTO stage_receipts_m12h "
                "(stage_id,owner_id,epoch,baseline_sha256,expected_sha256,"
                "actual_sha256,state) VALUES (?,?,?,?,?,NULL,'RESERVED')",
                (stage_id,self.owner_id,row["epoch"],sha(source),sha(expected)))
            con.execute("UPDATE authority SET pending_stage=? WHERE id=1",
                        (stage_id,))
            return {"stageId":stage_id,"epoch":row["epoch"],
                    "baselineSha256":sha(source),"expectedSha256":sha(expected),
                    "payload":expected, "status":"SYNTHETIC_RESERVED",
                    "productionWriterAuthorized":False}
        try:
            return self.owner._transition(tx)
        except sqlite3.IntegrityError as exc:
            raise AdmissionError("DUPLICATE_STAGE_REPLAY") from exc

    def notify_native(self, tag):
        # Quickshell callback tag is advisory, not a stage assertion.
        if tag not in ("FILE_SAVED", "FILE_READBACK_OK"):
            raise AdmissionError("UNSUPPORTED_NATIVE_HINT")
        return {"status":"NATIVE_HINT_ONLY","settled":False,
                "productionWriterAuthorized":False}

    def settle_after_independent_readback(self, stage_id: str, epoch: int):
        if not auth._id(stage_id) or type(epoch) is not int or epoch < 0:
            raise AdmissionError("INVALID_SETTLEMENT_REQUEST")
        # Real source bytes are read from the prevalidated *fixture* path,
        # not from a caller-reported QML callback or expected-hash field.
        try:
            initial, _ = host.stable_file(self.file)
        except AdmissionError:
            initial = None

        def tx(con, row):
            evidence = con.execute(
                "SELECT * FROM stage_receipts_m12h WHERE stage_id=?",
                (stage_id,)).fetchone()
            if (evidence is None or evidence["state"] != "RESERVED"
                    or evidence["owner_id"] != self.owner_id
                    or evidence["epoch"] != epoch
                    or row["epoch"] != epoch
                    or row["pending_stage"] != stage_id
                    or row["phase"] != "JSON_ACTIVE"):
                # Do not modify an already settled receipt just because
                # a late callback was delivered.
                raise AdmissionError("STALE_OR_UNOWNED_STAGE")

            try:
                actual, _ = host.stable_file(self.file)
            except AdmissionError:
                actual = None
            if (initial is None or actual is None or actual != initial
                    or sha(actual) != evidence["expected_sha256"]
                    or evidence["baseline_sha256"] != sha(self.confirmed)):
                # Commit the refusal durably. Preserve pending stage and
                # last confirmed source for the operator, no auto-replay.
                con.execute(
                    "UPDATE stage_receipts_m12h SET state='REVIEW_REQUIRED',"
                    "actual_sha256=? WHERE stage_id=?",
                    (sha(actual) if actual is not None else None, stage_id))
                con.execute(
                    "UPDATE authority SET phase='RECOVERY_REVIEW',"
                    "epoch=epoch+1,reason='M12H_READBACK_UNCERTAIN' WHERE id=1")
                return {"status":"READBACK_REVIEW_REQUIRED","settled":False,
                        "productionWriterAuthorized":False}
            observed = sha(actual)
            # This is the same SQLite transaction that clears pending:
            # durable stage receipt and current authority cannot disagree
            # under a single cooperating journal owner.
            con.execute(
                "UPDATE stage_receipts_m12h SET actual_sha256=?,"
                "state='SETTLED_UNACKNOWLEDGED' WHERE stage_id=?",
                (observed,stage_id))
            con.execute(
                "UPDATE authority SET pending_stage=NULL WHERE id=1")
            return {"status":"TEST_RECEIPT_SETTLED_UI_UNACKNOWLEDGED",
                    "settled":True,"stageId":stage_id,"epoch":epoch,
                    "actualSha256":observed,
                    "productionWriterAuthorized":False,
                    "independentNativeStageAttributionProven":False}
        receipt = self.owner._transition(tx)
        if receipt["settled"]:
            self.confirmed = initial
        return receipt

    def close(self):
        if self.owner is not None:
            self.owner.close()
            self.owner = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
