"""TimeW M6: explicit local-only checkpoint-bound exact observation admission.

A caller supplies genuine ExactLogicalRect(CURRENT) values from a *future*
separate fractional observer. Existing V1/V2 saved rectangles are INT-ONLY:
they MUST NOT be silently re-encoded as "fractional captures".

We cross-check ordinary saved checkpoint window metadata and atomically
append the complete candidate bundle to the separate private v3 DB.
This cannot authenticate a compositor, grant C5, or authorize Restore.
No UI/CLI, implicit path, import-time I/O, Sway command or background work.
"""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from MachineCheckpointStore import load as load_legacy, StoreError
from MachineGeometryStoreV2 import (
    GeometryStoreError, load_geometry, validate_pair,
)
from MachineV3LocalExactCaptureStore import (
    LocalCaptureRefused, LocalExactCaptureStore, MAX_RECORDS,
    _capture_value, _id, _text,
)


class AdmissionRefused(ValueError):
    pass


def _refuse():
    raise AdmissionRefused("TIMEW LOCAL EXACT ADMISSION REFUSED")


def admit_checkpoint(*, checkpoint_id, observations, store,
                     legacy_reader=load_legacy, geometry_reader=load_geometry):
    """Write all or no local v3 rows after strict ordinary V1/V2 correlation.

    The caller's exact observations remain UNTRUSTED despite a matching saved
    window key/app/output/workspace. The two local readers do not prove that
    those CURRENT coordinates were captured at the original Save instant.
    """
    try:
        cid = _id(checkpoint_id, version=4)
        if type(store) is not LocalExactCaptureStore:
            _refuse()
        if (type(observations) is not list
                or not 1 <= len(observations) <= MAX_RECORDS):
            _refuse()

        # Validate entire caller bundle before any read/write. Strictly deny
        # credential/source/receipt/consent fields, including unknown extras.
        clean, seen = [], set()
        expected_fields = {
            "window_key", "app_id", "output_id", "workspace_id", "value",
        }
        for entry in observations:
            if type(entry) is not dict or set(entry) != expected_fields:
                _refuse()
            key = _id(entry["window_key"])
            if key in seen:
                _refuse()
            seen.add(key)
            _text(entry["app_id"])
            _text(entry["output_id"])
            _text(entry["workspace_id"])
            _capture_value(entry["value"])  # exact CURRENT; no dict/int coercion
            clean.append(dict(entry))

        legacy = legacy_reader(cid)
        geometry = geometry_reader(cid)
        if (type(legacy) is not dict
                or set(legacy) != {"status", "checkpoint", "document", "read_only"}
                or legacy["status"] != "loaded"
                or legacy["read_only"] is not True
                or type(legacy["checkpoint"]) is not dict
                or legacy["checkpoint"].get("id") != cid
                or type(legacy["document"]) is not dict
                or type(geometry) is not dict
                or set(geometry) != {
                    "status", "checkpoint_id", "geometry_available",
                    "read_only", "session_identity_verified", "geometry",
                }
                or geometry["status"] != "loaded"
                or geometry["checkpoint_id"] != cid
                or geometry["geometry_available"] is not True
                or geometry["read_only"] is not True
                or geometry["session_identity_verified"] is not False
                or type(geometry["geometry"]) is not dict):
            _refuse()

        old, recorded = validate_pair(
            legacy["document"], geometry["geometry"])
        saved_windows = recorded["windows"]
        if (len(saved_windows) != len(clean)
                or legacy["checkpoint"].get("counts", {}).get("windows")
                != len(clean)):
            _refuse()
        expected = {
            entry["window_key"]: (
                entry["app_id"], entry["output"], entry["workspace"])
            for entry in saved_windows
        }
        if len(expected) != len(clean) or set(expected) != seen:
            _refuse()
        for entry in clean:
            if (entry["app_id"], entry["output_id"], entry["workspace_id"]) != (
                expected[entry["window_key"]]):
                _refuse()

        ids = store.save_many(checkpoint_id=cid, captures=clean)
        return {
            "status": "LOCAL_EXACT_CAPTURE_RECORDED_UNTRUSTED",
            "checkpoint_id": cid, "count": len(ids),
            "capture_ids": ids, "local_capture_only": True,
            "source_authenticated": False,
            "operator_selection_verified": False,
            "c5_spent_verified": False,
            "native_receipt_verified": False,
            "production_restore_allowed": False,
            "automatic_retry_allowed": False,
            "automatic_undo_allowed": False,
            "safe_actions": [],
        }
    except (AdmissionRefused, LocalCaptureRefused, StoreError,
            GeometryStoreError, ValueError, TypeError, KeyError,
            OverflowError):
        _refuse()
