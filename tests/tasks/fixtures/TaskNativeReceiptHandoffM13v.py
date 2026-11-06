#!/usr/bin/env python3
"""M13v // isolated native-callback → M12h journal → M13u revision handoff.

This is a never-mounted test fixture, not a production task coordinator.
It delegates synthetic stage reservation/settlement to the EXISTING M12h
durable journal owner and all source checks to M11g/M13u. It never writes
the JSON source, creates a DB, grants opt-in, launches Quickshell or sees
actual task drafts. A FileView callback is only an advisory hint.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "m13v_existing_m13u", HERE / "TaskSourceRevisionEvidenceM13u.py")
revision = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(revision)
m12h = revision._m12h

NO_POWER = dict(revision.NO_POWER, **{
    "independentNativeCallbackAuthenticated": False,
    "sourceWritePerformed": False,
    "pendingStageReplayAuthorized": False,
    "realDraftDataRead": False,
    "durableUserSaveAcknowledged": False,
    "automaticRecoveryAuthorized": False,
})


def response(code, **fields):
    return {"status": code, "fixtureOnly": True, **fields, **NO_POWER}


class DisposableNativeReceiptHandoff:
    """A single-use, test-only coordinator facade around an *existing* owner.

    One instance may handle sequential stages but never takes source ownership
    or writes task data. The existing owner retains the M10p flock/SQLite
    transaction; this object does not even hold a separate connection.
    """
    def __init__(self, owner):
        if type(owner) is not m12h.DisposableStageReceipt:
            raise ValueError("M13V_EXISTING_DISPOSABLE_OWNER_REQUIRED")
        self.owner = owner
        self.pending = None
        self.stopped_for_review = False

    def _baseline(self):
        try:
            snap = self.owner.snapshot()
            if snap["phase"] != "JSON_ACTIVE" or snap["pendingStage"] is not None:
                return None, "OWNER_REVIEW_OR_PENDING"
            seen = revision.inspect(self.owner)
            if seen["status"] == "SYNTHETIC_CURRENT_SOURCE_REVISION_OBSERVED":
                return seen["receipt"], None
            # First *synthetic stage* is allowed only for M11g's EXISTING
            # fixture seed. This is NOT permission to create a missing file.
            if seen["status"] != "NO_DURABLE_SETTLED_REVISION":
                return None, seen["status"]
            raw, doc = m12h.host.stable_file(self.owner.file)
            if (doc["revision"] != 0 or doc["counter"] != 0
                    or snap["receipts"] != []):
                return None, "INITIAL_SOURCE_PROVENANCE_UNVERIFIED"
            return {"revision": 0, "stageId": "",
                    "sourceSha256": hashlib.sha256(raw).hexdigest(),
                    "ownerEpoch": snap["epoch"]}, None
        except Exception:
            return None, "SAVED_SOURCE_UNAVAILABLE_OR_UNSAFE"

    def begin(self, stage_id):
        if self.stopped_for_review:
            return response("REVIEW_REQUIRED_NO_REPLAY")
        if self.pending is not None:
            return response("STAGE_ALREADY_PENDING")
        if not m12h.auth._id(stage_id):
            return response("INVALID_SYNTHETIC_STAGE")
        baseline, refused = self._baseline()
        if refused is not None:
            return response(refused)
        try:
            staged = self.owner.reserve(stage_id)
        except Exception:
            self.stopped_for_review = True
            return response("STAGE_RESERVATION_FAILED_REVIEW_REQUIRED")
        if (staged["epoch"] != baseline["ownerEpoch"]
                or staged["baselineSha256"] != baseline["sourceSha256"]):
            self.stopped_for_review = True
            return response("STAGE_BASELINE_REVIEW_REQUIRED")
        self.pending = {
            "stageId": staged["stageId"],
            "ownerEpoch": staged["epoch"],
            "baselineRevision": baseline["revision"],
            "expectedSha256": staged["expectedSha256"],
            "hintSeen": False,
        }
        # staged["payload"] stays inside the existing M12h fixture.
        # The facade deliberately does not expose even synthetic JSON.
        return response("SYNTHETIC_STAGE_RESERVED_NO_SOURCE_WRITE",
                        stageId=stage_id, ownerEpoch=staged["epoch"],
                        baselineRevision=baseline["revision"])

    def native_hint(self, *, stage_id, owner_epoch, kind):
        if (self.stopped_for_review or self.pending is None
                or stage_id != self.pending["stageId"]
                or type(owner_epoch) is not int
                or owner_epoch != self.pending["ownerEpoch"]):
            return response("STALE_OR_UNOWNED_NATIVE_HINT")
        if kind == "FILE_SAVED":
            if self.pending["hintSeen"]:
                return response("DUPLICATE_NATIVE_HINT_REFUSED")
            self.pending["hintSeen"] = True
            # No database change and no save acknowledgment. The caller
            # MUST request a separate independent source readback.
            return response("NATIVE_HINT_ONLY_NOT_A_RECEIPT")
        if kind in ("FILE_SAVE_FAILED", "FILE_LOAD_FAILED"):
            self.stopped_for_review = True
            # Keep M12h's RESERVED stage as evidence. No automatic retry,
            # rollback, clearing or invented callback correlation.
            return response("AMBIGUOUS_NATIVE_FAILURE_REVIEW_REQUIRED")
        return response("UNKNOWN_NATIVE_HINT")

    def inspect(self):
        if self.stopped_for_review:
            return response("REVIEW_REQUIRED_NO_REPLAY")
        if self.pending is not None:
            return response("UNACKNOWLEDGED_STAGE_PENDING",
                            stageId=self.pending["stageId"])
        evidence = revision.inspect(self.owner)
        if evidence["status"] != "SYNTHETIC_CURRENT_SOURCE_REVISION_OBSERVED":
            return response(evidence["status"])
        return response("SYNTHETIC_REVISION_OBSERVED_NO_AUTHORITY",
                        receipt=evidence["receipt"])

    def settle_after_independent_readback(self, *, stage_id, owner_epoch):
        if self.stopped_for_review:
            return response("REVIEW_REQUIRED_NO_REPLAY")
        stage = self.pending
        if (stage is None or stage["stageId"] != stage_id
                or type(owner_epoch) is not int
                or stage["ownerEpoch"] != owner_epoch):
            return response("STALE_OR_UNOWNED_SETTLEMENT")
        if not stage["hintSeen"]:
            return response("NATIVE_HINT_MISSING_NO_SETTLEMENT")
        try:
            result = self.owner.settle_after_independent_readback(
                stage_id, owner_epoch)
        except Exception:
            self.stopped_for_review = True
            return response("INDEPENDENT_SETTLEMENT_UNVERIFIED_REVIEW_REQUIRED")
        if not result["settled"]:
            self.stopped_for_review = True
            return response("SOURCE_READBACK_REVIEW_REQUIRED")
        confirmed = revision.inspect(self.owner)
        receipt = confirmed.get("receipt") if confirmed["status"] == (
            "SYNTHETIC_CURRENT_SOURCE_REVISION_OBSERVED") else None
        if (receipt is None or receipt["revision"] != stage["baselineRevision"]+1
                or receipt["stageId"] != stage_id
                or receipt["ownerEpoch"] != owner_epoch
                or receipt["sourceSha256"] != stage["expectedSha256"]):
            # Journal may have settled: NEVER retry a potentially completed
            # operation or return a positive receipt on uncertain outcome.
            self.stopped_for_review = True
            return response("POST_SETTLEMENT_REVISION_REVIEW_REQUIRED")
        self.pending = None
        return response("SYNTHETIC_RECEIPT_OBSERVED_UI_UNACKNOWLEDGED",
                        receipt=receipt, independentlyReadBack=True)
