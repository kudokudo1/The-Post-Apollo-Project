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
import hashlib
import json
import subprocess
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from MachineSwayRead import _read_json, PreviewError
from MachineGeometryV2 import project_geometry, GeometryError
from MachineGeometryStoreV2 import (save_pair, GeometryStoreError)
from MachineCaptureSelectionV2 import select_geometry, SelectionError
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


def stable_geometry(*, read_runner=subprocess.run,
                    key_factory=lambda: str(uuid.uuid4()), namespace=None):
    """Return a bounded, double-observed geometry projection, without writes.

    A review namespace produces reproducible per-capture window UUIDs from
    ephemeral compositor IDs. This is not long-term window identification.
    """
    first = _frame(read_runner)
    keys = _window_keys(first[2], first[1], key_factory=key_factory)
    if namespace is not None:
        if not isinstance(namespace, str):
            raise CaptureError("INVALID REVIEW NAMESPACE")
        try:
            parsed = uuid.UUID(namespace)
        except (ValueError, AttributeError) as exc:
            raise CaptureError("INVALID REVIEW NAMESPACE") from exc
        if parsed.version != 4 or str(parsed) != namespace:
            raise CaptureError("INVALID REVIEW NAMESPACE")
        keys = {con_id: str(uuid.uuid5(parsed, str(con_id)))
                for con_id in keys}
    geometry = project_geometry(*first, window_keys=keys)
    again = project_geometry(*_frame(read_runner), window_keys=keys)
    if again != geometry:
        raise CaptureError("DESKTOP CHANGED WHILE SAVING; TRY AGAIN")
    return geometry


def geometry_digest(geometry):
    """Digest only strict projected geometry; not a permission or signature."""
    value = json.dumps(geometry, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def capture_and_save(*, label="DESKTOP CHECKPOINT", selection=None,
                     review_binding=None,
                     read_runner=subprocess.run,
                     store_adapter=save_pair,
                     key_factory=lambda: str(uuid.uuid4()),
                     clock=lambda: dt.datetime.now(dt.timezone.utc)):
    """A single explicit save; optional scoped selection, no preview or UI dependency.

    No disk access is attempted if any read, validation or stability check
    fails. The storage owner handles all-or-nothing rollback on write failure.
    """
    if not isinstance(label, str) or len(label) > 48:
        raise CaptureError("INVALID CHECKPOINT NAME")
    if any(ord(char) < 32 or ord(char) == 127 for char in label):
        raise CaptureError("INVALID CHECKPOINT NAME")

    try:
        if review_binding is not None:
            if (not isinstance(review_binding, dict)
                    or set(review_binding) != {"namespace", "digest"}
                    or not isinstance(review_binding["digest"], str)
                    or len(review_binding["digest"]) != 64
                    or any(c not in "0123456789abcdef"
                           for c in review_binding["digest"])):
                raise CaptureError("INVALID CUSTOM REVIEW")
            namespace = review_binding["namespace"]
        else:
            namespace = None
        geometry = stable_geometry(
            read_runner=read_runner, key_factory=key_factory,
            namespace=namespace)
        if (review_binding is not None
                and geometry_digest(geometry) != review_binding["digest"]):
            raise CaptureError("CUSTOM SELECTION STALE; REFRESH CUSTOMIZE")
        # Optional custom scope prunes the same verified geometry tree.
        # The ordinary SAVE path leaves selection None and includes all.
        geometry = select_geometry(geometry, selection)
        current = clock()
        if (not isinstance(current, dt.datetime)
                or current.tzinfo is None
                or current.utcoffset() is None):
            raise CaptureError("CLOCK UNAVAILABLE")
        captured = current.astimezone(dt.timezone.utc).isoformat()
        legacy = _legacy_from_geometry(
            geometry, label=label, captured_at=captured)
        return store_adapter(legacy, geometry)
    except SelectionError as exc:
        raise CaptureError(str(exc)) from exc
    except PreviewError as exc:
        # Stable category only: never echo private Sway socket paths or data.
        raise CaptureError("DESKTOP CAPTURE UNAVAILABLE // SWAY READ") from exc
    except GeometryError as exc:
        raise CaptureError("DESKTOP CAPTURE UNAVAILABLE // GEOMETRY") from exc
    except (StoreError, GeometryStoreError) as exc:
        raise CaptureError("DESKTOP CAPTURE UNAVAILABLE // CHECKPOINT STORE") from exc
