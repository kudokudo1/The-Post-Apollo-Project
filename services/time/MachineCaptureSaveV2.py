#!/usr/bin/env python3
"""MACHINE M2: a single SAVE request captures and persists desktop geometry.

Dormant orchestration only: not imported by TimeW, no CLI, no background
polling, no browser data and no compositor mutations. One explicit call
performs two sequential Sway observation rounds, refuses changed layouts,
then invokes the existing atomic v1 + geometry-v2 checkpoint writer.

The Sway IPC protocol is not an atomic multi-query snapshot. The repeated
read detects observed changes, but cannot make a guarantee against a change
between final revalidation and SQLite commit. Never call this an exact
application-session capture or an executable restore plan.
"""
from __future__ import annotations

import datetime as dt
import subprocess
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from MachineSwayRead import _read_json, PreviewError
from MachineGeometryV2 import project_geometry, GeometryError
from MachineGeometryStoreV2 import (save_pair, GeometryStoreError)
from MachineCheckpointStore import validate as validate_legacy, StoreError

MAX_TREE_DEPTH = 48
MAX_TREE_NODES = 4096
MAX_TRACKED_WINDOWS = 512
KINDS = ("get_outputs", "get_workspaces", "get_tree")


class CaptureError(ValueError):
    pass


def _frame(read_runner):
    """Read only allowlisted Sway IPC queries; never send command IPC."""
    return tuple(_read_json(["swaymsg", "-r", "-t", key], read_runner)
                 for key in KINDS)


def _window_keys(tree, workspaces, *, key_factory):
    """Associate transient Sway IDs with newly allocated checkpoint UUIDs.

    The same map is reused when validating the second observation; it is not
    a claim that compositor IDs remain stable after the save completes.
    """
    if not isinstance(tree, dict) or not isinstance(workspaces, list):
        raise CaptureError("INVALID DESKTOP OBSERVATION")
    names = set()
    for ws in workspaces:
        if not isinstance(ws, dict) or not isinstance(ws.get("name"), str):
            raise CaptureError("INVALID WORKSPACE OBSERVATION")
        if ws["name"] in names:
            raise CaptureError("DUPLICATE WORKSPACE")
        names.add(ws["name"])
    assigned, nodes = {}, 0

    def walk(node, *, workspace=None, depth=0):
        nonlocal nodes
        nodes += 1
        if nodes > MAX_TREE_NODES or depth > MAX_TREE_DEPTH:
            raise CaptureError("DESKTOP TREE TOO LARGE")
        if not isinstance(node, dict):
            raise CaptureError("INVALID DESKTOP TREE")
        kind = node.get("type")
        if kind == "workspace":
            workspace = node.get("name")
        if workspace in names and kind in ("con", "floating_con"):
            app = node.get("app_id")
            if app is None and isinstance(node.get("window_properties"), dict):
                app = node["window_properties"].get("class")
            if isinstance(app, str) and app:
                con_id = node.get("id")
                if type(con_id) is not int or con_id <= 0 or con_id in assigned:
                    raise CaptureError("AMBIGUOUS TRANSIENT WINDOW")
                key = key_factory()
                if not isinstance(key, str):
                    raise CaptureError("INVALID WINDOW KEY FACTORY")
                assigned[con_id] = key
                if len(assigned) > MAX_TRACKED_WINDOWS:
                    raise CaptureError("TOO MANY WINDOWS")
        for collection in ("nodes", "floating_nodes"):
            children = node.get(collection, [])
            if not isinstance(children, list) or len(children) > 512:
                raise CaptureError("INVALID DESKTOP CHILDREN")
            for child in children:
                walk(child, workspace=workspace, depth=depth + 1)

    walk(tree)
    if len(set(assigned.values())) != len(assigned):
        raise CaptureError("DUPLICATE CHECKPOINT WINDOW KEYS")
    return assigned


def _legacy_from_geometry(geometry, *, label, captured_at):
    """Derive BOTH save records from one validated geometry projection."""
    return validate_legacy({
        "schema_version": 1,
        "kind": "sway-layout-selection-preview",
        "preview_only": True,
        "captured_at_utc": captured_at,
        "label": label,
        "outputs": [{"connector": x["connector"], "rect": x["rect"]}
                    for x in geometry["outputs"]],
        "workspaces": [{"name": x["name"], "output": x["output"]}
                       for x in geometry["workspaces"]],
        "windows": [{"app_id": x["app_id"], "workspace": x["workspace"],
                     "floating": x["floating"]}
                    for x in geometry["windows"]],
    })


def capture_and_save(*, label="DESKTOP CHECKPOINT",
                     read_runner=subprocess.run,
                     store_adapter=save_pair,
                     key_factory=lambda: str(uuid.uuid4()),
                     clock=lambda: dt.datetime.now(dt.timezone.utc)):
    """A single explicit save; no preview, selection or UI dependency.

    No disk access is attempted if any read, validation or stability check
    fails. The storage owner handles all-or-nothing rollback on write failure.
    """
    if not isinstance(label, str) or len(label) > 48:
        raise CaptureError("INVALID CHECKPOINT NAME")
    if any(ord(char) < 32 or ord(char) == 127 for char in label):
        raise CaptureError("INVALID CHECKPOINT NAME")

    try:
        first = _frame(read_runner)
        keys = _window_keys(first[2], first[1], key_factory=key_factory)
        geometry = project_geometry(*first, window_keys=keys)
        # Detect intervening changes in both saved content AND transient
        # window identities. Do not silently pair a replacement window by
        # matching only its app_id and rectangle.
        second = _frame(read_runner)
        again = project_geometry(*second, window_keys=keys)
        if again != geometry:
            raise CaptureError("DESKTOP CHANGED WHILE SAVING; TRY AGAIN")
        current = clock()
        if (not isinstance(current, dt.datetime)
                or current.tzinfo is None
                or current.utcoffset() is None):
            raise CaptureError("CLOCK UNAVAILABLE")
        captured = current.astimezone(dt.timezone.utc).isoformat()
        legacy = _legacy_from_geometry(
            geometry, label=label, captured_at=captured)
        return store_adapter(legacy, geometry)
    except (PreviewError, GeometryError, StoreError, GeometryStoreError) as exc:
        raise CaptureError("DESKTOP CAPTURE UNAVAILABLE") from exc
