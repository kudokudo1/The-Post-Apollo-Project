#!/usr/bin/env python3
"""MACHINE M1j: one-shot, read-only live window candidate resolution.

A saved app_id is not a stable window identity. Report single-window
candidates using transient Sway IDs *only* for a later revalidation gate.
This module never sends a Sway command, writes storage, or moves a window.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

# Python -I does not add the script directory to sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from MachineCheckpointStore import StoreError, validate
from MachineSwayRead import _read_json, normalize, PreviewError

MAX_REQUEST_BYTES = 262144
MAX_CANDIDATES = 40
SAFE_WORKSPACE = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")


class ResolutionError(ValueError):
    pass


def _id(value):
    return type(value) is int and 0 < value <= 9007199254740991


def _walk_live(tree):
    """Ephemeral identifiers; no window titles, commands, process IDs or URLs."""
    if not isinstance(tree, dict):
        raise ResolutionError("INVALID SWAY TREE")
    windows = []
    def walk(node, workspace=None, floating=False, depth=0):
        if depth > 48 or not isinstance(node, dict):
            raise ResolutionError("INVALID SWAY TREE")
        kind = node.get("type")
        if kind == "workspace":
            workspace = node.get("name")
        app = node.get("app_id")
        if app is None and isinstance(node.get("window_properties"), dict):
            app = node["window_properties"].get("class")
        if kind == "con" and isinstance(app, str) and app and workspace is not None:
            container_id = node.get("id")
            # Invalid/absent live IDs are not silently paired with a saved window.
            windows.append({
                "app_id": app, "workspace": workspace,
                "floating": floating or node.get("floating") in ("user_on", "auto_on"),
                "con_id": container_id if _id(container_id) else None,
                "fullscreen": node.get("fullscreen_mode", 0) not in (0, None)
            })
            if len(windows) > 512:
                raise ResolutionError("TOO MANY WINDOWS")
        for key, is_floating in (("nodes", floating), ("floating_nodes", True)):
            children = node.get(key, [])
            if not isinstance(children, list):
                raise ResolutionError("INVALID SWAY TREE")
            for child in children:
                walk(child, workspace, is_floating, depth + 1)
    walk(tree)
    return windows


def resolve(saved_document, outputs, workspaces, tree):
    """A *candidate*, not an executable permit. Requery before future action."""
    try:
        saved = validate(saved_document)
        current = normalize(outputs, workspaces, tree)
        live = _walk_live(tree)
    except (StoreError, PreviewError) as exc:
        raise ResolutionError("INVALID CHECKPOINT OR SWAY STATE") from exc
    active_outputs = set()
    for output in current["outputs"]:
        name = output.get("name")
        if isinstance(name, str):
            active_outputs.add(name)
    current_workspaces = {}
    for ws in current["workspaces"]:
        if ws["name"] in current_workspaces:
            raise ResolutionError("DUPLICATE LIVE WORKSPACE")
        current_workspaces[ws["name"]] = ws["output"]
    targets = {ws["name"]: ws["output"] for ws in saved["workspaces"]}
    saved_by_app = {}
    for win in saved["windows"]:
        saved_by_app.setdefault(win["app_id"], []).append(win)
    live_by_app = {}
    for win in live:
        live_by_app.setdefault(win["app_id"], []).append(win)
    results = []
    totals = {"already": 0, "candidate": 0, "manual": 0, "blocked": 0}
    for app in sorted(saved_by_app):
        expected = saved_by_app[app]
        matches = live_by_app.get(app, [])
        desired = expected[0]
        destination = desired["workspace"]
        output = targets[destination]
        category = "manual"
        reason = "AMBIGUOUS APP INSTANCES"
        con_id = None
        origin = None
        if output not in active_outputs or destination not in current_workspaces:
            category, reason = "blocked", "TARGET WORKSPACE OR MONITOR ABSENT"
        elif current_workspaces[destination] != output:
            category, reason = "blocked", "WORKSPACE ON DIFFERENT MONITOR"
        elif not SAFE_WORKSPACE.fullmatch(destination):
            category, reason = "manual", "WORKSPACE NAME REQUIRES MANUAL REVIEW"
        elif len(expected) != 1 or len(matches) != 1:
            if not matches:
                category, reason = "manual", "APP NOT RUNNING"
        else:
            win = matches[0]
            origin = win["workspace"]
            if (win["con_id"] is None or win["fullscreen"]
                    or win["floating"] != desired["floating"]):
                category, reason = "manual", "WINDOW STATE REQUIRES REVIEW"
            elif origin == destination:
                category, reason = "already", "WINDOW ALREADY ON TARGET WORKSPACE"
            else:
                category, reason = "candidate", "UNIQUE LIVE WINDOW; NOT YET APPROVED"
                con_id = win["con_id"]
        totals[category] += 1
        if len(results) < MAX_CANDIDATES:
            results.append({"app_id": app, "status": category, "reason": reason,
                            "target_workspace": destination, "current_workspace": origin,
                            "live_con_id": con_id})
    return {"kind": "machine-live-window-resolution", "read_only": True,
            "executable": False, "status": "review", "counts": totals,
            "total_apps": len(saved_by_app), "candidates": results,
            "truncated": len(saved_by_app) > len(results),
            "requires_fresh_revalidation": True}


def capture_and_resolve(document, *, runner=None):
    if runner is None:
        import subprocess
        runner = subprocess.run
    try:
        outputs = _read_json(["swaymsg", "-r", "-t", "get_outputs"], runner)
        workspaces = _read_json(["swaymsg", "-r", "-t", "get_workspaces"], runner)
        tree = _read_json(["swaymsg", "-r", "-t", "get_tree"], runner)
        return resolve(document, outputs, workspaces, tree)
    except PreviewError as exc:
        raise ResolutionError("LIVE SWAY READ UNAVAILABLE") from exc


def main():
    raw = sys.stdin.buffer.readline(MAX_REQUEST_BYTES + 1)
    if not raw or len(raw) > MAX_REQUEST_BYTES or not raw.endswith(b"\n"):
        print(json.dumps({"status": "error", "reason": "INVALID REQUEST"}))
        return 1
    try:
        payload = json.loads(raw)
        result = capture_and_resolve(payload)
    except (ResolutionError, ValueError, TypeError, UnicodeError):
        print(json.dumps({"status": "error", "reason": "RESOLUTION UNAVAILABLE"}))
        return 1
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
