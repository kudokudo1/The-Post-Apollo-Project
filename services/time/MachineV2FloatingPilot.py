"""MACHINE V2: opt-in floating geometry placement rehearsal, disposable CI only.

This is a functional command-path pilot for synthetic / isolated test runners,
NOT a production restore service, CLI, trusted browser/Sway identity witness,
or operator-authorization implementation. No default command runner exists.
"""
from __future__ import annotations

from collections import Counter
import json
import os
import uuid
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from MachineCaptureSaveV2 import _frame, _window_keys
from MachineCheckpointStore import load as load_legacy
from MachineGeometryStoreV2 import load_geometry, validate_pair
from MachineGeometryV2 import project_geometry
from MachineWindowResolver import _id as valid_con_id

KIND = "machine-v2-floating-disposable-rehearsal-v1"
FIELDS = frozenset((
    "checkpoint_id", "checkpoint_window_key", "live_con_id",
    "operator_selected", "execution_approved", "approval_kind",
))
APPROVAL_KIND = "disposable-manual-window-selection-v1"
MAX_COMMAND_RESPONSE = 4096


class RehearsalRefused(ValueError):
    pass


def refuse(reason="V2 FLOATING REHEARSAL REFUSED"):
    raise RehearsalRefused(reason)


def _uuid(value):
    if not isinstance(value, str):
        refuse("INVALID CHECKPOINT ID")
    try:
        parsed = uuid.UUID(value)
    except (TypeError, ValueError, AttributeError):
        refuse("INVALID CHECKPOINT ID")
    if parsed.version != 4 or str(parsed) != value:
        refuse("INVALID CHECKPOINT ID")
    return value


def _request(request):
    if not isinstance(request, dict) or set(request) != FIELDS:
        refuse("INVALID REQUEST SHAPE")
    _uuid(request["checkpoint_id"])
    _uuid(request["checkpoint_window_key"])
    if not valid_con_id(request["live_con_id"]):
        refuse("INVALID LIVE WINDOW")
    if (request["operator_selected"] is not True
            or request["execution_approved"] is not True
            or request["approval_kind"] != APPROVAL_KIND):
        refuse("EXPLICIT FIXTURE APPROVAL REQUIRED")
    return request


def _sample(read_runner):
    """Double-observe real fixed Sway READ IPC, retaining only ephemeral IDs."""
    first = _frame(read_runner)
    keys = _window_keys(first[2], first[1],
                        key_factory=lambda: str(uuid.uuid4()))
    one = project_geometry(*first, window_keys=keys)
    again = project_geometry(*_frame(read_runner), window_keys=keys)
    if one != again:
        refuse("DESKTOP CHANGED DURING OBSERVATION")
    id_to_window = {con: next((
        win for win in one["windows"] if win["window_key"] == key), None)
        for con, key in keys.items()}
    if any(win is None for win in id_to_window.values()):
        refuse("LIVE WINDOW MAP INCOMPLETE")
    return one, id_to_window


def _saved(checkpoint_id, legacy_reader, geometry_reader):
    old = legacy_reader(checkpoint_id)
    geo = geometry_reader(checkpoint_id)
    if (not isinstance(old, dict) or old.get("status") != "loaded"
            or old.get("read_only") is not True
            or old.get("checkpoint", {}).get("id") != checkpoint_id
            or not isinstance(geo, dict) or geo.get("status") != "loaded"
            or geo.get("read_only") is not True
            or geo.get("checkpoint_id") != checkpoint_id
            or geo.get("geometry_available") is not True
            or geo.get("session_identity_verified") is not False):
        refuse("V2 CHECKPOINT NOT VERIFIED")
    _, clean = validate_pair(old["document"], geo["geometry"])
    return clean


def _window_checked(saved, live, mapping, request):
    key = request["checkpoint_window_key"]
    selected = [win for win in saved["windows"] if win["window_key"] == key]
    if len(selected) != 1:
        refuse("SAVED WINDOW NOT FOUND")
    target = selected[0]
    con_id = request["live_con_id"]
    live_win = mapping.get(con_id)
    if live_win is None or live_win["app_id"] != target["app_id"]:
        refuse("MANUAL WINDOW DOES NOT MATCH APPLICATION")
    if not target["floating"] or not live_win["floating"]:
        refuse("TILING GEOMETRY IS NOT SUPPORTED")
    if target["fullscreen_mode"] != 0 or live_win["fullscreen_mode"] != 0:
        refuse("FULLSCREEN WINDOW NOT SUPPORTED")
    if (target["output"] != live_win["output"]
            or target["workspace"] != live_win["workspace"]):
        refuse("CROSS WORKSPACE OR OUTPUT MOVE NOT SUPPORTED")

    outputs = {o["connector"]: o for o in saved["outputs"]}
    live_outputs = {o["connector"]: o for o in live["outputs"]}
    out = outputs[target["output"]]
    if live_outputs.get(target["output"]) != out:
        refuse("MONITOR RECT SCALE OR TRANSFORM CHANGED")
    workspaces = {w["name"]: w["output"] for w in live["workspaces"]}
    if workspaces.get(target["workspace"]) != target["output"]:
        refuse("WORKSPACE OUTPUT CHANGED")

    box = target["rect"]
    screen = out["rect"]
    if (box["width"] < 100 or box["height"] < 80
            or box["x"] < screen["x"] or box["y"] < screen["y"]
            or box["x"] + box["width"] > screen["x"] + screen["width"]
            or box["y"] + box["height"] > screen["y"] + screen["height"]):
        refuse("SAVED FLOATING RECT OUTSIDE TARGET DISPLAY")
    # This is an explicitly manually selected *current* Sway container,
    # not a persistent pairing. Another app with the same ID is allowed
    # only because this fixture scoped the exact live con_id to review.
    signature = sorted((ident, win["app_id"], win["workspace"],
                        win["output"], win["floating"], win["fullscreen_mode"])
                       for ident, win in mapping.items())
    return target, live_win, signature


def prepare(request, *, legacy_reader=load_legacy,
            geometry_reader=load_geometry, read_runner):
    """Read-only fresh preflight. No executable permission is returned."""
    request = _request(request)
    saved = _saved(request["checkpoint_id"], legacy_reader, geometry_reader)
    live, mapping = _sample(read_runner)
    target, current, signature = _window_checked(saved, live, mapping, request)
    return {
        "saved": saved, "target": target, "current": current,
        "signature": signature,
        "status": "already" if current["rect"] == target["rect"]
                  else "manual_fixture_candidate",
        "read_only": True, "production_restore_allowed": False,
        "persistent_identity_verified": False,
        "browser_tabs_restorable": False,
    }


def _command_ok(result):
    blob = getattr(result, "stdout", None)
    if (not isinstance(blob, bytes) or not 1 <= len(blob) <= MAX_COMMAND_RESPONSE
            or getattr(result, "returncode", 1) != 0):
        return False
    try:
        decoded = json.loads(blob)
    except (ValueError, UnicodeError):
        return False
    return (isinstance(decoded, list) and len(decoded) == 1
            and isinstance(decoded[0], dict)
            and decoded[0].get("success") is True)


def _response(status, *, dispatched=0):
    return {
        "kind": KIND, "status": status, "dispatched_commands": dispatched,
        "production_restore_allowed": False,
        "persistent_identity_verified": False,
        "browser_tabs_restorable": False,
        "no_automatic_retry": True, "no_automatic_undo": True,
        "manual_recovery_required": status == "uncertain_requires_review",
    }


def execute_disposable(request, *, read_runner, command_runner, journal,
                       legacy_reader=load_legacy, geometry_reader=load_geometry):
    """Test-only two-command resize+position. No production entrypoint.

    The injected journal must record BEGIN and DISPATCHING before any command.
    This function deliberately cannot attest to an authenticated human seat or
    durable browser identity; in real operation those checks need separate owners.
    """
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("CI") != "true":
        refuse("DISPOSABLE CI ONLY")
    if journal is None or not all(callable(getattr(journal, name, None))
                                  for name in ("begin", "dispatching", "finish")):
        refuse("EXPLICIT FIXTURE JOURNAL REQUIRED")
    prepared = prepare(request, legacy_reader=legacy_reader,
                       geometry_reader=geometry_reader,
                       read_runner=read_runner)
    if prepared["status"] == "already":
        return _response("already_observed")
    target, signature = prepared["target"], prepared["signature"]
    con_id = request["live_con_id"]
    current_rect = prepared["current"]["rect"]
    box = target["rect"]
    # Single-use fixture journal. A failed write refuses BEFORE command.
    op = journal.begin({
        "checkpoint_id": request["checkpoint_id"],
        "window_key": target["window_key"], "app_id": target["app_id"],
        "live_con_id": con_id, "before_rect": current_rect, "target_rect": box,
    })
    journal.dispatching(op)
    commands = (
        "[con_id=" + str(con_id) + "] resize set "
        + str(box["width"]) + " px " + str(box["height"]) + " px",
        "[con_id=" + str(con_id) + "] move absolute position "
        + str(box["x"]) + " px " + str(box["y"]) + " px",
    )
    count = 0
    status = "uncertain_requires_review"
    for index, command in enumerate(commands):
        # Reobserve without retry or widening the operator-selected binding.
        try:
            live, mapping = _sample(read_runner)
            saved = prepared["saved"]
            check, current, now_signature = _window_checked(saved, live, mapping, request)
            if check != target or now_signature != signature:
                break
            # First command may have changed size but cannot change the
            # chosen window's other metadata or trigger a different target.
            if index == 0 and current["rect"] != current_rect:
                break
            if index == 1 and (current["rect"]["x"] != current_rect["x"]
                               or current["rect"]["y"] != current_rect["y"]):
                break
            try:
                reply = command_runner(
                    ["swaymsg", "-r", "-t", "command", command],
                    check=False, capture_output=True, timeout=3, shell=False)
            except Exception:
                break
            count += 1
            if not _command_ok(reply):
                break
        except (ValueError, KeyError, TypeError, OSError):
            break
    if count == 2:
        try:
            live, mapping = _sample(read_runner)
            check, current, now_signature = _window_checked(
                prepared["saved"], live, mapping, request)
            if (check == target and now_signature == signature
                    and current["rect"] == box):
                status = "verified_fixture_placement"
        except (ValueError, KeyError, TypeError, OSError):
            pass
    # If this fails, the journal remains DISPATCHING and cannot be retried.
    journal.finish(op, status)
    return _response(status, dispatched=count)
