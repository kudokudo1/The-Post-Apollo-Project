"""MACHINE M1k: injectable single-window move pilot, NOT a live executor.

This module has no CLI, no default command runner and no TimeW wiring.
All movement tests use synthetic Sway responses. A future operator-approved
adapter must separately supply its own permissioned runners, before-state
journal and live confirmation UI. Never run on the operator's desktop as-is.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

# Importing existing read-only projection under python3 -I.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from MachineSwayRead import PreviewError, _read_json
from MachineWindowResolver import (
    ResolutionError, _id, _walk_live, resolve,
)

NUMERIC_WORKSPACE = re.compile(r"[1-9][0-9]{0,2}\Z")
REQUEST_FIELDS = frozenset(
    ("intent", "approved", "app_id", "con_id", "from_workspace", "to_workspace"))
MAX_COMMAND_RESPONSE = 4096


class MoveRefused(ValueError):
    pass


def _request(req, *, approval_required):
    if not isinstance(req, dict) or set(req) != REQUEST_FIELDS:
        raise MoveRefused("INVALID ACTION REQUEST")
    if req["intent"] != "single-existing-window-workspace-move":
        raise MoveRefused("UNSUPPORTED ACTION")
    if type(req["approved"]) is not bool:
        raise MoveRefused("INVALID APPROVAL")
    if approval_required and req["approved"] is not True:
        raise MoveRefused("EXPLICIT APPROVAL REQUIRED")
    if not _id(req["con_id"]):
        raise MoveRefused("INVALID CONTAINER ID")
    app = req["app_id"]
    if (not isinstance(app, str) or not 1 <= len(app) <= 128
            or any(ord(c) < 32 or ord(c) == 127 for c in app)):
        raise MoveRefused("INVALID APP ID")
    origin, target = req["from_workspace"], req["to_workspace"]
    if not isinstance(origin, str) or not 1 <= len(origin) <= 128:
        raise MoveRefused("INVALID SOURCE")
    if not isinstance(target, str) or not NUMERIC_WORKSPACE.fullmatch(target):
        raise MoveRefused("ONLY EXISTING NUMBERED WORKSPACES SUPPORTED")
    if origin == target:
        raise MoveRefused("NO MOVE NECESSARY")


def _read_state(runner):
    try:
        outputs = _read_json(["swaymsg", "-r", "-t", "get_outputs"], runner)
        workspaces = _read_json(["swaymsg", "-r", "-t", "get_workspaces"], runner)
        tree = _read_json(["swaymsg", "-r", "-t", "get_tree"], runner)
        return outputs, workspaces, tree
    except PreviewError as exc:
        raise MoveRefused("SWAY READ UNAVAILABLE") from exc


def _preflight(saved_document, request, *, runner, approval_required):
    _request(request, approval_required=approval_required)
    outputs, workspaces, tree = _read_state(runner)
    try:
        outcome = resolve(saved_document, outputs, workspaces, tree)
        nodes = _walk_live(tree)
    except ResolutionError as exc:
        raise MoveRefused("UNSAFE OR INCONSISTENT STATE") from exc
    # Even if only one app matches, reject duplicate compositor IDs globally.
    ids = [node["con_id"] for node in nodes if node["con_id"] is not None]
    if len(ids) != len(set(ids)):
        raise MoveRefused("DUPLICATE LIVE CONTAINER IDS")
    if outcome["truncated"]:
        raise MoveRefused("TRUNCATED WINDOW RESOLUTION")
    matches = [candidate for candidate in outcome["candidates"]
               if candidate["app_id"] == request["app_id"]]
    if len(matches) != 1:
        raise MoveRefused("CANDIDATE MISSING")
    candidate = matches[0]
    if (candidate["status"] != "candidate"
            or candidate["live_con_id"] != request["con_id"]
            or candidate["current_workspace"] != request["from_workspace"]
            or candidate["target_workspace"] != request["to_workspace"]):
        raise MoveRefused("CANDIDATE CHANGED OR AMBIGUOUS")

    # No action on a missing or changed monitor/workspace; resolve() verifies
    # target workspace association and existing connected output.
    command = ("[con_id=" + str(request["con_id"])
               + "] move container to workspace number "
               + request["to_workspace"])
    before = {"con_id": request["con_id"], "app_id": request["app_id"],
              "workspace": request["from_workspace"],
              "target_workspace": request["to_workspace"]}
    undo = {"kind": "manual-undo-preview", "executable": False,
            "requires_fresh_revalidation": True,
            "con_id": request["con_id"],
            "workspace": request["from_workspace"]}
    return {"before": before, "undo_preview": undo, "command": command}


def preview_one(saved_document, request, *, read_runner):
    """No command runner exists on the preview path."""
    report = _preflight(saved_document, request, runner=read_runner,
                        approval_required=False)
    return {"status": "ready_for_review", "executable": False,
            "requires_explicit_approval": True,
            "before": report["before"], "undo_preview": report["undo_preview"]}


def _command_success(result):
    blob = getattr(result, "stdout", None)
    if not isinstance(blob, bytes) or len(blob) > MAX_COMMAND_RESPONSE:
        return False
    if getattr(result, "returncode", 1) != 0:
        return False
    try:
        parsed = json.loads(blob)
    except (UnicodeError, ValueError):
        return False
    return (isinstance(parsed, list) and len(parsed) == 1
            and isinstance(parsed[0], dict)
            and parsed[0].get("success") is True)


def _observe(runner, saved_document, request):
    """Postflight rechecks target placement, app uniqueness and output mapping."""
    outputs, workspaces, tree = _read_state(runner)
    try:
        resolution = resolve(saved_document, outputs, workspaces, tree)
        nodes = _walk_live(tree)
    except ResolutionError:
        return "unavailable"
    matching = [row for row in resolution["candidates"]
                if row["app_id"] == request["app_id"]]
    app_nodes = [row for row in nodes if row["app_id"] == request["app_id"]]
    if len(matching) != 1 or len(app_nodes) != 1:
        return "unavailable"
    win = app_nodes[0]
    if win["con_id"] != request["con_id"] or win["fullscreen"]:
        return "unavailable"
    if matching[0]["status"] == "already" and win["workspace"] == request["to_workspace"]:
        return request["to_workspace"]
    if (matching[0]["status"] == "candidate"
            and matching[0]["live_con_id"] == request["con_id"]
            and win["workspace"] == request["from_workspace"]):
        return request["from_workspace"]
    return "unavailable"


def execute_one(saved_document, request, *, read_runner, command_runner):
    """Isolated-injection pilot only; intentionally NO production CLI.

    Real use requires a separately approved UI, immutable approval scope,
    runtime validation, a durable before-state journal and compositor tests.
    """
    report = _preflight(saved_document, request, runner=read_runner,
                        approval_required=True)
    argv = ["swaymsg", "-r", "-t", "command", report["command"]]
    # Fixed command grammar, exact numeric target, no shell interpolation.
    # Only one command is sent. No focus/kill/start/reload command is sent.
    try:
        outcome = command_runner(argv, check=False, capture_output=True,
                                 timeout=3, shell=False)
    except Exception:
        outcome = None
    accepted = _command_success(outcome)
    # Postflight must re-observe. Never claim success from IPC reply alone.
    try:
        observed = _observe(read_runner, saved_document, request)
    except MoveRefused:
        observed = "unavailable"
    if accepted and observed == request["to_workspace"]:
        status = "verified_moved"
    elif not accepted and observed == request["from_workspace"]:
        status = "refused_no_confirmed_move"
    else:
        status = "uncertain_requires_manual_review"
    return {"status": status, "before": report["before"],
            "observed_workspace": observed,
            "undo_preview": report["undo_preview"],
            "reversible_automatically": False,
            "no_automatic_undo": True}
