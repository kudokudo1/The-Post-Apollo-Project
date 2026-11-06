#!/usr/bin/env python3
"""TASKS M13u: read-only revision evidence from existing M12h disposable journal.

No production TASKS paths or QML imports. The existing M12h owner retains the
only *synthetic* stage/journal authority; this module writes neither JSON nor
SQLite. A successful comparison is an observation, NEVER a permission grant.
The M12h journal is cooperatively owned, not OS-authenticated source truth.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import re

FIXTURES = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "m13u_existing_m12h", FIXTURES / "TaskStageSourceReceiptM12h.py")
_m12h = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m12h)

SHA256 = re.compile(r"[a-f0-9]{64}\Z")
NO_POWER = {
    "productionActivation": False,
    "sourceTrusted": False,
    "hostAuthenticated": False,
    "userConsentAuthenticated": False,
    "keyReleaseAuthorized": False,
    "captureAuthorized": False,
    "previewAuthorized": False,
    "deleteAuthorized": False,
    "restoreAuthorized": False,
    "taskWriteAuthorized": False,
}


def _status(code: str, **info):
    # Only fixed caller-selected fields, never JSON bodies or private drafts.
    return {"status": code, "disposableOnly": True, **info, **NO_POWER}


def _expected_shape(value):
    return (type(value) is dict
            and set(value) == {"revision", "stageId", "sourceSha256",
                               "ownerEpoch"}
            and type(value["revision"]) is int
            and 1 <= value["revision"] <= 1000
            and type(value["stageId"]) is str
            and _m12h.auth._id(value["stageId"])
            and type(value["sourceSha256"]) is str
            and SHA256.fullmatch(value["sourceSha256"]) is not None
            and type(value["ownerEpoch"]) is int
            and value["ownerEpoch"] >= 0)


def inspect(owner, expected=None):
    """Inspect existing journal and source under an already-held test owner.

    Expected receipt is only a test-side CAS pin, not a bearer capability.
    An active owner must rescan at consumption. It cannot fence a hostile
    same-UID process in the interval after this method returns.
    """
    if type(owner) is not _m12h.DisposableStageReceipt:
        return _status("REFUSED_NOT_EXISTING_DISPOSABLE_OWNER")
    if expected is not None and not _expected_shape(expected):
        return _status("INVALID_REVISION_RECEIPT")
    try:
        snap = owner.snapshot()  # Already owns M10p lifetime flock.
        records = snap["receipts"]
    except Exception:
        return _status("JOURNAL_NOT_VERIFIED")

    if type(records) is not list or len(records) > 1000:
        return _status("JOURNAL_HISTORY_UNVERIFIED")
    if not records:
        return _status("NO_DURABLE_SETTLED_REVISION")
    if any(r["receiptState"] != "SETTLED_UNACKNOWLEDGED"
           for r in records):
        return _status("UNSETTLED_STAGE_REVIEW_REQUIRED")
    previous = None
    for r in records:
        if (type(r["stageId"]) is not str
                or not _m12h.auth._id(r["stageId"])
                or type(r["epoch"]) is not int or r["epoch"] < 0
                or type(r["baselineSha256"]) is not str
                or SHA256.fullmatch(r["baselineSha256"]) is None
                or type(r["expectedSha256"]) is not str
                or SHA256.fullmatch(r["expectedSha256"]) is None
                or r["actualSha256"] != r["expectedSha256"]):
            return _status("JOURNAL_CHAIN_INVALID")
        if previous is not None and r["baselineSha256"] != previous:
            return _status("JOURNAL_CHAIN_INVALID")
        previous = r["actualSha256"]

    try:
        raw, document = _m12h.host.stable_file(owner.file)
    except Exception:
        return _status("SAVED_SOURCE_UNAVAILABLE_OR_UNSAFE")
    current_hash = hashlib.sha256(raw).hexdigest()
    # The M11g synthetic schema intentionally increments with each stage.
    if current_hash != previous or document["revision"] != len(records):
        return _status("SOURCE_JOURNAL_REVISION_MISMATCH")

    # M10p deliberately enters RECOVERY_REVIEW on a new process/epoch.
    # Historical receipts remain visible, but nothing is authorized.
    if snap["phase"] != "JSON_ACTIVE" or snap["pendingStage"] is not None:
        return _status("OWNER_REVIEW_REQUIRED", lastObservedRevision=len(records))

    pin = {
        "revision": len(records),
        "stageId": records[-1]["stageId"],
        "sourceSha256": current_hash,
        "ownerEpoch": snap["epoch"],
    }
    if expected is not None and expected != pin:
        return _status("STALE_REVISION_OR_OWNER_EPOCH")
    return _status("SYNTHETIC_CURRENT_SOURCE_REVISION_OBSERVED",
                   receipt=pin, sourceMatched=True, historyComplete=True)
