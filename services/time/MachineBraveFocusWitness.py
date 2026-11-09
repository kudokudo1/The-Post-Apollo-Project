#!/usr/bin/env python3
"""One-shot, read-only Sway focus witness for a future Brave pairing review.

NOT a Brave-to-Sway binding and NOT an authenticated browser transport.
This opt-in CLI is not called by TimeW, a browser extension or a daemon.
It reads only the live compositor's get_tree, twice, without Sway commands.
Never emits PIDs, titles, native window IDs, browser data or raw Sway JSON.
"""
from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from MachineSwayRead import _read_json, PreviewError

MAX_DEPTH = 48
MAX_NODES = 4096
MAX_CHILDREN = 512
MAX_NAME = 128
BRAVE_APP_IDS = frozenset((
    "brave-browser", "Brave-browser", "com.brave.Browser", "brave",
))


class FocusWitnessError(ValueError):
    pass


def _safe_name(value):
    return (isinstance(value, str) and 1 <= len(value) <= MAX_NAME
            and all(ord(c) >= 32 and ord(c) != 127 for c in value))


def _focused_leaf(tree):
    """Return private/internal tuple for two-read equality; never expose it."""
    total = 0
    focused = []
    def walk(node, output=None, workspace=None, depth=0):
        nonlocal total
        if depth > MAX_DEPTH or not isinstance(node, dict):
            raise FocusWitnessError("UNSUPPORTED SWAY TREE")
        total += 1
        if total > MAX_NODES:
            raise FocusWitnessError("SWAY TREE TOO LARGE")
        kind = node.get("type")
        if kind == "output":
            output = node.get("name")
        elif kind == "workspace":
            workspace = node.get("name")

        if kind in ("con", "floating_con") and node.get("focused") is True:
            app = node.get("app_id")
            if app is None and isinstance(node.get("window_properties"), dict):
                app = node["window_properties"].get("class")
            ident = node.get("id")
            if (type(ident) is not int or ident <= 0 or not _safe_name(app)
                    or not _safe_name(output) or not _safe_name(workspace)):
                raise FocusWitnessError("UNSUPPORTED FOCUSED WINDOW")
            focused.append((ident, app, output, workspace, kind))

        for key in ("nodes", "floating_nodes"):
            children = node.get(key, [])
            if not isinstance(children, list) or len(children) > MAX_CHILDREN:
                raise FocusWitnessError("UNSUPPORTED SWAY TREE")
            for child in children:
                walk(child, output, workspace, depth + 1)

    walk(tree)
    if len(focused) > 1:
        raise FocusWitnessError("AMBIGUOUS FOCUSED WINDOWS")
    return focused[0] if focused else None


def inspect_focus(*, runner=subprocess.run, new_id=uuid.uuid4):
    """Read two full frames, and return only an ephemeral observation UUID.

    No observable browser window ID is accepted as input. No time-ordered
    matching from the two sources is taken as identity authentication.
    """
    try:
        first = _focused_leaf(
            _read_json(["swaymsg", "-r", "-t", "get_tree"], runner))
        again = _focused_leaf(
            _read_json(["swaymsg", "-r", "-t", "get_tree"], runner))
    except PreviewError as exc:
        raise FocusWitnessError("SWAY READ UNAVAILABLE") from exc

    base = {
        "kind": "machine-sway-brave-focus-witness-v1",
        "read_only": True,
        "browser_window_id": None,
        "sway_window_binding_verified": False,
        "browser_session_identity_verified": False,
        "private_window_exclusion_verified": False,
        "session_restorable": False,
        "action_allowed": False,
        "safe_actions": [],
    }
    if first is None or again is None:
        return dict(base, status="no_focused_client")
    if first != again:
        return dict(base, status="focus_changed")
    _, app, output, workspace, _ = first
    if app not in BRAVE_APP_IDS:
        return dict(base, status="not_brave_focused")

    tag = new_id()
    if not isinstance(tag, uuid.UUID):
        raise FocusWitnessError("INVALID WITNESS IDENTIFIER")
    return dict(
        base,
        status="brave_focus_observed",
        observation_id=str(tag),
        reported_app_id=app,
        output=output,
        workspace=workspace,
        same_focused_client_in_two_reads=True,
    )


def main(args=None):
    args = sys.argv[1:] if args is None else args
    if args != ["inspect"]:
        print(json.dumps({"status": "error", "reason": "INVALID ACTION"}))
        return 1
    try:
        result = inspect_focus()
    except (FocusWitnessError, OSError, TypeError, ValueError):
        print(json.dumps({
            "status": "error",
            "reason": "SWAY FOCUS OBSERVATION UNAVAILABLE",
        }))
        return 1
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
