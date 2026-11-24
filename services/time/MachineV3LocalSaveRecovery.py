"""TimeW M7: read-only local two-database Save outcome observation.

No writer, retry, repair, compositor capture, UI hook or protected authority.
The caller must retain the original binding separately; this is not a durable
attempt journal. Matching local snapshots prove only observed consistency.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from MachineCheckpointStore import load as load_legacy, StoreError
from MachineGeometryStoreV2 import (
    load_geometry, validate_pair, GeometryStoreError,
)
from MachineV3LocalExactCaptureStore import (
    LocalExactCaptureStore, LocalCaptureRefused, MAX_RECORDS,
    _id, _text, _capture_value,
)


class BindingRefused(ValueError):
    pass


def _refuse():
    raise BindingRefused("TIMEW LOCAL SAVE BINDING REFUSED") from None


def _digest(document):
    return hashlib.sha256(json.dumps(
        document, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False,
    ).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class LocalSaveBinding:
    checkpoint_id: str
    checkpoint_digest: str
    candidate_digest: str


def _canonical_candidates(items):
    if type(items) is not list or not 1 <= len(items) <= MAX_RECORDS:
        _refuse()
    rows, keys = [], set()
    for item in items:
        if type(item) is not dict or set(item) != {
            "window_key", "app_id", "output_id", "workspace_id", "value"
        }:
            _refuse()
        key = _id(item["window_key"])
        if key in keys:
            _refuse()
        keys.add(key)
        rows.append((
            key, _text(item["app_id"]), _text(item["output_id"]),
            _text(item["workspace_id"]), *_capture_value(item["value"]),
        ))
    return sorted(rows)


def _pair(cid, legacy_reader, geometry_reader):
    old = legacy_reader(cid)
    geo = geometry_reader(cid)
    if (type(old) is not dict or set(old) != {
        "status", "checkpoint", "document", "read_only"
    } or old["status"] != "loaded" or old["read_only"] is not True
        or type(old["checkpoint"]) is not dict
        or type(geo) is not dict or set(geo) != {
            "status", "checkpoint_id", "geometry_available", "read_only",
            "session_identity_verified", "geometry"
        } or geo["status"] != "loaded" or geo["checkpoint_id"] != cid
        or geo["geometry_available"] is not True or geo["read_only"] is not True
        or geo["session_identity_verified"] is not False):
        _refuse()
    summary = old["checkpoint"]
    if set(summary) != {"id", "label", "saved_at_utc", "captured_at_utc", "counts"}:
        _refuse()
    if summary["id"] != cid or any(type(summary[k]) is not str for k in (
        "label", "saved_at_utc", "captured_at_utc"
    )):
        _refuse()
    original, geometry = validate_pair(old["document"], geo["geometry"])
    expected_counts = {k: len(geometry[k]) for k in (
        "outputs", "workspaces", "windows"
    )}
    counts = summary["counts"]
    if (type(counts) is not dict or counts != expected_counts
        or any(type(v) is not int for v in counts.values())
        or summary["label"] != original["label"]
        or summary["captured_at_utc"] != original["captured_at_utc"]):
        _refuse()
    windows = sorted((w["window_key"], w["app_id"], w["output"], w["workspace"])
                     for w in geometry["windows"])
    return _digest([summary, original, geometry]), windows


_ERRORS = (BindingRefused, LocalCaptureRefused, GeometryStoreError, StoreError,
           sqlite3.Error, OSError, ValueError, TypeError, KeyError,
           AttributeError, OverflowError, RecursionError)


def prepare_binding(*, checkpoint_id, observations,
                    legacy_reader=load_legacy, geometry_reader=load_geometry):
    """Read-only fingerprint of an already saved pair and explicit CURRENT set.

    A future producer must separately bind native observation time/generation
    to its original Save. This local fingerprint does not establish that fact.
    """
    try:
        cid = _id(checkpoint_id, version=4)
        candidates = _canonical_candidates(observations)
        digest, windows = _pair(cid, legacy_reader, geometry_reader)
        if [row[:4] for row in candidates] != windows:
            _refuse()
        # A second read detects observed pair changes, not hidden ABA.
        if _pair(cid, legacy_reader, geometry_reader) != (digest, windows):
            _refuse()
        return LocalSaveBinding(cid, digest, _digest(candidates))
    except _ERRORS:
        _refuse()


def _result(status, *, checkpoint_id=None):
    return {
        "status": status, "checkpoint_id": checkpoint_id,
        "read_only": True, "local_data_only": True,
        "cross_database_atomic": False,
        "save_attempt_verified": False,
        "source_authenticated": False,
        "operator_selection_verified": False,
        "c5_spent_verified": False,
        "native_receipt_verified": False,
        "production_restore_allowed": False,
        "automatic_retry_allowed": False,
        "automatic_undo_allowed": False,
        "safe_actions": [],
    }


def inspect_outcome(*, binding, observations, store,
                    legacy_reader=load_legacy, geometry_reader=load_geometry):
    """Observe the two local stores without writing or repeating any Save.

    Absent rows are only absent at the observed read, not proof an attempted
    write failed or permission to retry. Matching rows cannot identify who
    wrote them, when they were captured, or whether an old reply was lost.
    """
    cid = None
    try:
        if type(binding) is not LocalSaveBinding or type(store) is not LocalExactCaptureStore:
            _refuse()
        cid = _id(binding.checkpoint_id, version=4)
        candidates = _canonical_candidates(observations)
        if _digest(candidates) != binding.candidate_digest:
            return _result("CANDIDATE_CONFLICT_HOLD", checkpoint_id=cid)
        first, windows = _pair(cid, legacy_reader, geometry_reader)
        if first != binding.checkpoint_digest or windows != [r[:4] for r in candidates]:
            return _result("CHECKPOINT_CHANGED_HOLD", checkpoint_id=cid)
        rows = store.for_checkpoint(cid)
        # Even matching fractional rows are not usable if the original
        # checkpoint changed or disappeared during the independent v3 read.
        if _pair(cid, legacy_reader, geometry_reader) != (first, windows):
            return _result("CHECKPOINT_CHANGED_HOLD", checkpoint_id=cid)
        if not rows:
            return _result("LEGACY_MATCH_LOCAL_EXACT_ABSENT", checkpoint_id=cid)
        actual = _canonical_candidates([
            {k: row[k] for k in ("window_key", "app_id", "output_id", "workspace_id", "value")}
            for row in rows
        ])
        if actual != candidates or any(row["checkpoint_id"] != cid for row in rows):
            return _result("LOCAL_EXACT_CONFLICT_HOLD", checkpoint_id=cid)
        return _result("BOTH_LOCAL_RECORDS_OBSERVED_UNTRUSTED", checkpoint_id=cid)
    except _ERRORS:
        return _result("LOCAL_SAVE_OUTCOME_UNKNOWN_HOLD", checkpoint_id=cid)
