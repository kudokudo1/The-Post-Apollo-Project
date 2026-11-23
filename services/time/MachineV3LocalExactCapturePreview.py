#!/usr/bin/env python3
"""TimeW M4: explicit, read-only preview of untrusted local v3 captures.

Existing TimeW's V2 review uses a bounded deny-only JSON response. This
separate M4 preview follows that pattern for *local caller-supplied data only*.
It never queries Sway, records a capture, consumes protected grants, performs
Restore, or silently reads the default XDG store. No import-time file IO.
"""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import sys
import uuid

# Python -I intentionally omits the script directory from sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from MachineV2ExactLogicalGeometry import (
    ExactGeometryRefused, PHASE_CURRENT, read_value,
)
from MachineV3LocalExactCaptureStore import (
    LocalCaptureRefused, LocalExactCaptureStore, MAX_RECORDS,
)

KIND = "timew-v3-local-exact-capture-preview-v1"
MAX_OUTPUT_BYTES = 524288
ENTRY_FIELDS = frozenset((
    "id", "checkpoint_id", "window_key", "app_id", "output_id",
    "workspace_id", "value", "saved_at_utc", "local_capture_only",
    "source_authenticated", "operator_selection_verified",
    "production_restore_allowed", "c5_spent_verified",
    "terminal_receipt_verified", "automatic_retry_allowed",
    "automatic_undo_allowed", "safe_actions",
))
DENIAL_FIELDS = (
    "source_authenticated", "operator_selection_verified",
    "production_restore_allowed", "c5_spent_verified",
    "terminal_receipt_verified", "automatic_retry_allowed",
    "automatic_undo_allowed",
)
COORDINATES = ("x", "y", "width", "height")


class PreviewRefused(ValueError):
    pass


def _refuse():
    raise PreviewRefused("LOCAL EXACT PREVIEW REFUSED")


def _checkpoint_id(value):
    if type(value) is not str:
        _refuse()
    try:
        ident = uuid.UUID(value)
    except (ValueError, TypeError, AttributeError):
        _refuse()
    if ident.version != 4 or str(ident) != value:
        _refuse()
    return value


def _result(checkpoint_id, status, entries):
    return {
        "kind": KIND,
        "checkpoint_id": checkpoint_id,
        "status": status,
        "count": len(entries),
        "entries": entries,
        "read_only": True,
        "data_origin": "CALLER_SUPPLIED_LOCAL_UNTRUSTED",
        "source_authenticated": False,
        "operator_selection_verified": False,
        "c5_spent_verified": False,
        "native_receipt_verified": False,
        "exact_restore_verified": False,
        "restore_allowed": False,
        "native_action_allowed": False,
        "retry_allowed": False,
        "undo_allowed": False,
        "safe_actions": [],
    }


def unavailable():
    """Fixed refusal. No operator path, stored ID or private data leaks."""
    return _result(None, "UNAVAILABLE_HOLD", [])


def _render_entry(raw, checkpoint_id):
    # v3 is ordinary data. Explicit refusal if its schema or a future caller
    # reports more authority than the reviewed local-only store can establish.
    if type(raw) is not dict or set(raw) != ENTRY_FIELDS:
        _refuse()
    if (raw["checkpoint_id"] != checkpoint_id
            or raw["local_capture_only"] is not True
            or type(raw["safe_actions"]) is not list
            or raw["safe_actions"] != []
            or any(raw[name] is not False for name in DENIAL_FIELDS)):
        _refuse()
    try:
        ident = uuid.UUID(raw["id"])
        wid = uuid.UUID(raw["window_key"])
    except (TypeError, ValueError, AttributeError):
        _refuse()
    if (ident.version != 4 or str(ident) != raw["id"]
            or str(wid) != raw["window_key"]
            or type(raw["app_id"]) is not str
            or type(raw["output_id"]) is not str
            or type(raw["workspace_id"]) is not str
            or type(raw["saved_at_utc"]) is not str):
        _refuse()
    value = raw["value"]
    try:
        coordinates = read_value(value)
    except (ExactGeometryRefused, TypeError, AttributeError):
        _refuse()
    if value.phase != PHASE_CURRENT:
        _refuse()
    return {
        "capture_id": raw["id"],
        "checkpoint_window_key": raw["window_key"],
        "app_id": raw["app_id"],
        "output_id": raw["output_id"],
        "workspace_id": raw["workspace_id"],
        "saved_at_utc": raw["saved_at_utc"],
        "geometry": {
            name: {"decimal": repr(number), "binary64_hex": number.hex()}
            for name, number in zip(COORDINATES, coordinates)
        },
        "observed_phase": "CURRENT_VALUE_ONLY",
        "local_data_untrusted": True,
        "selected_window_identity_verified": False,
        "source_authenticated": False,
        "settled_frame_verified": False,
        "action_allowed": False,
    }


def preview(checkpoint_id, *, store):
    """Bounded, checkpoint-scoped snapshot. No Sway, Save, Restore or writes."""
    _checkpoint_id(checkpoint_id)
    if type(store) is not LocalExactCaptureStore:
        _refuse()
    try:
        raw_entries = store.for_checkpoint(checkpoint_id)
    except LocalCaptureRefused:
        _refuse()
    if (type(raw_entries) is not list
            or len(raw_entries) > MAX_RECORDS):
        _refuse()
    entries = [_render_entry(item, checkpoint_id) for item in raw_entries]
    status = "LOCAL_CAPTURES_UNTRUSTED_HOLD" if entries else "NO_LOCAL_CAPTURES"
    return _result(checkpoint_id, status, entries)


def _encode_bounded(result):
    encoded = json.dumps(result, ensure_ascii=False, separators=(",", ":"),
                         allow_nan=False)
    if len(encoded.encode("utf-8")) > MAX_OUTPUT_BYTES:
        _refuse()
    return encoded


def main(argv=None):
    """Opt-in: preview <absolute-local-db> <v4-checkpoint-uuid>.

    No implicit/default path, no enumerate-all mode and no mutation options.
    A failed request always produces a fixed non-authorizing reply.
    """
    args = sys.argv[1:] if argv is None else argv
    try:
        if len(args) != 3 or args[0] != "preview":
            _refuse()
        checkpoint = _checkpoint_id(args[2])
        store = LocalExactCaptureStore(args[1])
        result = preview(checkpoint, store=store)
        output = _encode_bounded(result)
    except (PreviewRefused, LocalCaptureRefused, ValueError, TypeError,
            AttributeError, OSError, sqlite3.Error, OverflowError):
        print(_encode_bounded(unavailable()))
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
