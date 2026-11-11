#!/usr/bin/env python3
"""MACHINE // ephemeral title-marker Sway window observation.

Used ONLY by a separate, opt-in, disposable Brave native host.
Compares an unpredictable marker displayed in a user-created extension tab
to the focused Sway client title on TWO bounded tree reads. Returns a
transient Sway container number only when the marker is unique and stable.
Not an authenticated browser/process identity, restart-stable association,
private-window proof, session capture or permission to restore.
"""
from __future__ import annotations

import subprocess
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from MachineSwayRead import _read_json, PreviewError
from MachineBraveFocusWitness import (
    BRAVE_APP_IDS, FocusWitnessError, MAX_DEPTH, MAX_NODES, MAX_CHILDREN
)

TREE_CMD = ["swaymsg", "-r", "-t", "get_tree"]
TITLE_PREFIX = "MACHINE WINDOW CHECK "
TITLE_SUFFIXES = ("", " - Brave", " - Brave Browser", " - Brave Beta")
MAX_TITLE = 192


class MarkerWitnessError(ValueError):
    pass


def _challenge(value):
    if not isinstance(value, str):
        raise MarkerWitnessError("INVALID MARKER")
    try:
        if str(uuid.UUID(value)) != value:
            raise MarkerWitnessError("NONCANONICAL MARKER")
    except (ValueError, AttributeError) as exc:
        raise MarkerWitnessError("INVALID MARKER") from exc
    return value


def _one_frame(tree, marker):
    """Return private (con_id, output, workspace, app_id), or no match.

    Every container with the marker title participates in ambiguity checks,
    regardless of which one is focused. An attacker or duplicated tab can
    never turn a multi-match into an accepted mapping.
    """
    if not isinstance(tree, dict):
        raise MarkerWitnessError("UNSUPPORTED SWAY TREE")
    expected = TITLE_PREFIX + marker
    matches = []
    focused = []
    total = 0

    def visit(node, output=None, workspace=None, depth=0):
        nonlocal total
        if depth > MAX_DEPTH or not isinstance(node, dict):
            raise MarkerWitnessError("UNSUPPORTED SWAY TREE")
        total += 1
        if total > MAX_NODES:
            raise MarkerWitnessError("SWAY TREE LIMIT")
        kind = node.get("type")
        if kind == "output":
            output = node.get("name")
        if kind == "workspace":
            workspace = node.get("name")
        if kind in ("con", "floating_con"):
            app = node.get("app_id")
            if app is None and isinstance(node.get("window_properties"), dict):
                app = node["window_properties"].get("class")
            ident = node.get("id")
            name = node.get("name")
            if node.get("focused") is True:
                focused.append(ident)
            if isinstance(name, str) and name.startswith(expected):
                # Count even malformed/foreign candidates as ambiguous.
                matches.append((ident, name, app, output, workspace,
                                node.get("focused") is True))
        for key in ("nodes", "floating_nodes"):
            children = node.get(key, [])
            if not isinstance(children, list) or len(children) > MAX_CHILDREN:
                raise MarkerWitnessError("SWAY TREE LIMIT")
            for child in children:
                visit(child, output, workspace, depth + 1)

    visit(tree)
    if len(matches) != 1 or len(focused) != 1:
        return None
    ident, name, app, output, workspace, is_focused = matches[0]
    if (not is_focused or focused[0] != ident
            or type(ident) is not int or ident <= 0
            or app not in BRAVE_APP_IDS
            or not isinstance(output, str) or not 1 <= len(output) <= 128
            or not isinstance(workspace, str) or not 1 <= len(workspace) <= 128
            or len(name) > MAX_TITLE
            or any(ord(c) < 32 or ord(c) == 127 for c in (output + workspace))
            or name[len(expected):] not in TITLE_SUFFIXES):
        return None
    return ident, output, workspace, app


def inspect_marker(marker, *, runner=subprocess.run):
    """Two read-only Sway snapshots; no focus/move/launch/write."""
    value = _challenge(marker)
    try:
        first = _one_frame(_read_json(TREE_CMD, runner), value)
        again = _one_frame(_read_json(TREE_CMD, runner), value)
    except (PreviewError, FocusWitnessError, MarkerWitnessError,
            OSError, TypeError, ValueError):
        return None
    if first is None or again is None or first != again:
        return None
    return {"sway_container_id": first[0],
            "output": first[1], "workspace": first[2]}
