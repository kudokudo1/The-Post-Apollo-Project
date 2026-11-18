#!/usr/bin/env python3
"""MACHINE // V2 saved-vs-current geometry review. Read-only and never authority.

No Sway command IPC, launch, move, browser access, record mutation or retry.
Saved UUID window keys identify only checkpoint entries, never live processes.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
import sqlite3
from pathlib import Path
import sys
import uuid

# Python -I removes the entrypoint directory from sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from MachineCheckpointStore import load as load_legacy, validate as validate_legacy
from MachineGeometryStoreV2 import (
    load_geometry, validate_pair, validate_geometry,
)
from MachineCaptureSaveV2 import stable_geometry

KIND = "machine-v2-restore-review-v1"
OBSERVED = "OBSERVED_GEOMETRY_AGREEMENT_UNTRUSTED"
MAX_OUTPUT_BYTES = 262144


class ReviewError(ValueError):
    pass


def _id(value):
    if not isinstance(value, str):
        raise ReviewError("INVALID CHECKPOINT ID")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise ReviewError("INVALID CHECKPOINT ID") from exc
    if parsed.version != 4 or str(parsed) != value:
        raise ReviewError("INVALID CHECKPOINT ID")
    return value


def _result(checkpoint_id, status, items, *, saved_windows):
    observed = sum(x["classification"] == OBSERVED for x in items)
    return {
        "kind": KIND, "status": status, "checkpoint_id": checkpoint_id,
        "counts": {
            "saved_windows": saved_windows,
            "observed_untrusted": observed,
            "needs_attention": saved_windows - observed,
        },
        "items": items,
        "read_only": True, "restore_allowed": False,
        "browser_tabs_restorable": False,
        "exact_geometry_restore_verified": False,
        "live_window_identity_verified": False,
        "checkpoint_keys_are_live_identity": False,
        "requires_fresh_recheck": True, "safe_actions": [],
    }


def plan(checkpoint_id, legacy_record, geometry_record, live_geometry=None):
    """Validate both saved records and classify an independent live observation.

    Even a matching app/rectangle is NOT proof of window identity or permission.
    This function is pure: it neither reads nor writes state.
    """
    _id(checkpoint_id)
    if (not isinstance(legacy_record, dict)
            or set(legacy_record) != {"status", "checkpoint", "document", "read_only"}
            or legacy_record["status"] != "loaded"
            or legacy_record["read_only"] is not True
            or not isinstance(legacy_record["checkpoint"], dict)
            or legacy_record["checkpoint"].get("id") != checkpoint_id):
        raise ReviewError("SAVED CHECKPOINT UNAVAILABLE")
    old = validate_legacy(legacy_record["document"])

    if not isinstance(geometry_record, dict):
        raise ReviewError("GEOMETRY RECORD UNAVAILABLE")
    if (set(geometry_record) == {
            "status", "checkpoint_id", "geometry_available", "read_only"}
            and geometry_record["status"] == "legacy_only"
            and geometry_record["checkpoint_id"] == checkpoint_id
            and geometry_record["geometry_available"] is False
            and geometry_record["read_only"] is True):
        return _result(checkpoint_id, "legacy_only", [],
                       saved_windows=len(old["windows"]))

    if (set(geometry_record) != {
            "status", "checkpoint_id", "geometry_available", "read_only",
            "session_identity_verified", "geometry"}
            or geometry_record["status"] != "loaded"
            or geometry_record["checkpoint_id"] != checkpoint_id
            or geometry_record["geometry_available"] is not True
            or geometry_record["read_only"] is not True
            or geometry_record["session_identity_verified"] is not False):
        raise ReviewError("GEOMETRY RECORD UNAVAILABLE")
    _, saved = validate_pair(old, geometry_record["geometry"])
    if live_geometry is None:
        raise ReviewError("LIVE GEOMETRY REQUIRED")
    current = validate_geometry(live_geometry)

    saved_counts = Counter(w["app_id"] for w in saved["windows"])
    live_apps = defaultdict(list)
    for window in current["windows"]:
        live_apps[window["app_id"]].append(window)
    current_outputs = {x["connector"]: x for x in current["outputs"]}
    current_workspaces = {x["name"]: x for x in current["workspaces"]}
    saved_outputs = {x["connector"]: x for x in saved["outputs"]}

    items = []
    for window in saved["windows"]:
        app, output, workspace = (
            window["app_id"], window["output"], window["workspace"])
        live_output = current_outputs.get(output)
        live_workspace = current_workspaces.get(workspace)
        live_matches = live_apps[app]
        if live_output is None:
            reason = "TARGET_OUTPUT_MISSING"
        elif live_output != saved_outputs[output]:
            reason = "TARGET_OUTPUT_GEOMETRY_CHANGED"
        elif live_workspace is None:
            reason = "TARGET_WORKSPACE_MISSING"
        elif live_workspace["output"] != output:
            reason = "TARGET_WORKSPACE_MOVED"
        elif saved_counts[app] != 1 or len(live_matches) > 1:
            reason = "AMBIGUOUS_APP_INSTANCES"
        elif not live_matches:
            reason = "APP_NOT_RUNNING"
        else:
            live = live_matches[0]
            if (live["floating"] != window["floating"]
                    or live["fullscreen_mode"] != window["fullscreen_mode"]):
                reason = "WINDOW_STATE_DIFFERENT"
            elif live["output"] != output:
                reason = "CURRENT_OUTPUT_DIFFERENT"
            elif live["workspace"] != workspace:
                reason = "CURRENT_WORKSPACE_DIFFERENT"
            elif live["rect"] != window["rect"]:
                reason = "CURRENT_RECTANGLE_DIFFERENT"
            else:
                reason = OBSERVED
        items.append({
            "checkpoint_window_key": window["window_key"],
            "app_id": app, "target_output": output,
            "target_workspace": workspace, "classification": reason,
            "identity_verified": False, "action_allowed": False,
        })
    return _result(checkpoint_id, "review_only", items,
                   saved_windows=len(saved["windows"]))


def inspect(checkpoint_id, *, legacy_reader=load_legacy,
            geometry_reader=load_geometry, live_reader=stable_geometry):
    """Read existing SQLite and double-observe Sway; never send command IPC."""
    _id(checkpoint_id)
    legacy_record = legacy_reader(checkpoint_id)
    geometry_record = geometry_reader(checkpoint_id)
    # Do not read the desktop when only a legacy checkpoint is available.
    if isinstance(geometry_record, dict) and geometry_record.get("status") == "legacy_only":
        return plan(checkpoint_id, legacy_record, geometry_record)
    current = live_reader()
    return plan(checkpoint_id, legacy_record, geometry_record, current)


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if len(args) != 2 or args[0] != "review":
            raise ReviewError("INVALID REQUEST")
        result = inspect(args[1])
        encoded = json.dumps(result, separators=(",", ":"), ensure_ascii=False)
        if len(encoded.encode("utf-8")) > MAX_OUTPUT_BYTES:
            raise ReviewError("REVIEW TOO LARGE")
    except (ValueError, KeyError, TypeError, OSError, RuntimeError,
            sqlite3.Error):
        result = {
            "kind": KIND, "status": "unavailable",
            "read_only": True, "restore_allowed": False,
            "browser_tabs_restorable": False,
            "exact_geometry_restore_verified": False,
            "live_window_identity_verified": False,
            "requires_fresh_recheck": True, "safe_actions": [],
        }
        print(json.dumps(result, separators=(",", ":")))
        return 1
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
