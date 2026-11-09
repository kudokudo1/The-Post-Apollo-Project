#!/usr/bin/env python3
"""MACHINE v2: dormant, additive, all-or-nothing geometry checkpoint owner.

No CLI, import-time writes, IPC, app inspection, UI binding, or restoration.
A caller supplies an already captured v1-compatible document and the matching
geometry-v2 projection. Both records share ONE SQLite transaction in the
existing v1 private machine.db. Legacy rows and user_version=1 stay untouched.
"""
from __future__ import annotations

from collections import Counter
import datetime as dt
import hashlib
import json
import math
import sqlite3
import uuid

import MachineCheckpointStore as legacy
from MachineGeometryV2 import KIND, LAYOUTS, MAX_NODES, MAX_DEPTH, MAX_WINDOWS

MAX_BYTES = 2_000_000
TABLE = "machine_checkpoint_geometry_v2"


class GeometryStoreError(ValueError):
    pass


def _fields(value, required):
    if not isinstance(value, dict) or set(value) != set(required):
        raise GeometryStoreError("INVALID GEOMETRY FIELDS")


def _text(value):
    if (not isinstance(value, str) or not 1 <= len(value) <= 128
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise GeometryStoreError("INVALID GEOMETRY IDENTIFIER")
    return value


def _id(value):
    if not isinstance(value, str):
        raise GeometryStoreError("INVALID GEOMETRY WINDOW KEY")
    try:
        original = str(uuid.UUID(value))
    except (ValueError, AttributeError) as exc:
        raise GeometryStoreError("INVALID GEOMETRY WINDOW KEY") from exc
    if original != value:
        raise GeometryStoreError("NONCANONICAL GEOMETRY WINDOW KEY")
    return original


def _rect(value, *, optional=False):
    if value is None and optional:
        return None
    _fields(value, ("x", "y", "width", "height"))
    cleaned = {}
    for field in ("x", "y", "width", "height"):
        n = value[field]
        if (type(n) is not int or n < (-100000 if field in ("x", "y") else 0)
                or n > 100000):
            raise GeometryStoreError("INVALID GEOMETRY RECTANGLE")
        cleaned[field] = n
    return cleaned


def _ratio(value):
    if value is None:
        return None
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= 1:
        raise GeometryStoreError("INVALID GEOMETRY SPLIT FRACTION")
    return float(value)


def _layout(value):
    if value not in LAYOUTS:
        raise GeometryStoreError("UNSUPPORTED GEOMETRY LAYOUT")
    return value


def _raw(value):
    try:
        result = json.dumps(value, ensure_ascii=False, allow_nan=False,
                            sort_keys=True, separators=(",", ":"))
        encoded = result.encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise GeometryStoreError("INVALID GEOMETRY DATA") from exc
    if len(encoded) > MAX_BYTES:
        raise GeometryStoreError("GEOMETRY CHECKPOINT TOO LARGE")
    return encoded


def validate_geometry(document):
    """Strictly validate and sanitize the complete nested stored geometry.

    Raw tree data, titles, commands, PIDs and transient compositor IDs are
    rejected, not merely ignored. Never trust a syntactically valid UUID as a
    stable app window identity after restart.
    """
    _raw(document)  # bounded serialization before recursive parsing
    _fields(document, ("schema_version", "kind", "coordinate_space",
                       "outputs", "workspaces", "windows",
                       "capture_only", "session_identity_verified"))
    if (type(document["schema_version"]) is not int
            or document["schema_version"] != 2 or document["kind"] != KIND
            or document["coordinate_space"] != "sway-logical-pixels"
            or document["capture_only"] is not True
            or document["session_identity_verified"] is not False):
        raise GeometryStoreError("UNSUPPORTED GEOMETRY CHECKPOINT")

    outputs = document["outputs"]
    workspaces = document["workspaces"]
    windows = document["windows"]
    if (not isinstance(outputs, list) or not 1 <= len(outputs) <= 16
            or not isinstance(workspaces, list) or len(workspaces) > 128
            or not isinstance(windows, list) or len(windows) > MAX_WINDOWS):
        raise GeometryStoreError("INVALID GEOMETRY COLLECTION")
    clean_outputs, output_names = [], set()
    for output in outputs:
        _fields(output, ("connector", "rect", "scale", "transform"))
        connector = _text(output["connector"])
        if connector in output_names:
            raise GeometryStoreError("DUPLICATE GEOMETRY MONITOR")
        output_names.add(connector)
        scale = output["scale"]
        if type(scale) not in (int, float) or not math.isfinite(scale) or not 0.1 <= scale <= 8:
            raise GeometryStoreError("INVALID MONITOR SCALE")
        clean_outputs.append({
            "connector": connector, "rect": _rect(output["rect"]),
            "scale": float(scale), "transform": _text(output["transform"]),
        })

    count = 0
    tree_windows = {}
    def node(value, *, workspace, output, floating, depth):
        nonlocal count
        if depth > MAX_DEPTH:
            raise GeometryStoreError("GEOMETRY TREE TOO DEEP")
        count += 1
        if count > MAX_NODES:
            raise GeometryStoreError("TOO MANY GEOMETRY NODES")
        _fields(value, ("layout", "percent", "rect", "window_key",
                        "children", "floating_children"))
        children, floaters = value["children"], value["floating_children"]
        if (not isinstance(children, list) or len(children) > 512
                or not isinstance(floaters, list) or len(floaters) > 512):
            raise GeometryStoreError("INVALID GEOMETRY CHILDREN")
        key = value["window_key"]
        if key is not None:
            key = _id(key)
            if key in tree_windows:
                raise GeometryStoreError("DUPLICATE TREE WINDOW KEY")
            tree_windows[key] = (workspace, output, floating)
        return {
            "layout": _layout(value["layout"]),
            "percent": _ratio(value["percent"]),
            "rect": _rect(value["rect"]),
            "window_key": key,
            "children": [node(x, workspace=workspace, output=output,
                              floating=floating, depth=depth + 1)
                         for x in children],
            "floating_children": [node(x, workspace=workspace, output=output,
                                       floating=True, depth=depth + 1)
                                  for x in floaters],
        }

    clean_workspaces, workspace_outputs = [], {}
    for ws in workspaces:
        _fields(ws, ("name", "output", "rect", "layout",
                     "children", "floating_children"))
        name = _text(ws["name"])
        output = _text(ws["output"])
        if name in workspace_outputs or output not in output_names:
            raise GeometryStoreError("INVALID WORKSPACE OUTPUT")
        workspace_outputs[name] = output
        if (not isinstance(ws["children"], list) or len(ws["children"]) > 512
                or not isinstance(ws["floating_children"], list)
                or len(ws["floating_children"]) > 512):
            raise GeometryStoreError("INVALID WORKSPACE CHILDREN")
        clean_workspaces.append({
            "name": name, "output": output, "rect": _rect(ws["rect"]),
            "layout": _layout(ws["layout"]),
            "children": [node(x, workspace=name, output=output, floating=False,
                              depth=1) for x in ws["children"]],
            "floating_children": [
                node(x, workspace=name, output=output, floating=True,
                     depth=1) for x in ws["floating_children"]],
        })

    clean_windows, window_keys = [], set()
    for window in windows:
        _fields(window, ("window_key", "app_id", "workspace", "output",
                         "floating", "rect", "window_rect", "deco_rect",
                         "geometry", "fullscreen_mode"))
        key = _id(window["window_key"])
        if key in window_keys:
            raise GeometryStoreError("DUPLICATE WINDOW KEY")
        window_keys.add(key)
        ws = _text(window["workspace"])
        output = _text(window["output"])
        floating = window["floating"]
        if (ws not in workspace_outputs or workspace_outputs[ws] != output
                or type(floating) is not bool):
            raise GeometryStoreError("INCONSISTENT GEOMETRY WINDOW")
        if tree_windows.get(key) != (ws, output, floating):
            raise GeometryStoreError("WINDOW DOES NOT MATCH TILING TREE")
        fullscreen = window["fullscreen_mode"]
        if type(fullscreen) is not int or not 0 <= fullscreen <= 2:
            raise GeometryStoreError("INVALID WINDOW FULLSCREEN")
        clean_windows.append({
            "window_key": key, "app_id": _text(window["app_id"]),
            "workspace": ws, "output": output, "floating": floating,
            "rect": _rect(window["rect"]),
            "window_rect": _rect(window["window_rect"], optional=True),
            "deco_rect": _rect(window["deco_rect"], optional=True),
            "geometry": _rect(window["geometry"], optional=True),
            "fullscreen_mode": fullscreen,
        })
    if len(tree_windows) != len(window_keys) or set(tree_windows) != window_keys:
        raise GeometryStoreError("WINDOWS MISSING FROM TILING TREE")
    # The validated document is reconstructed from its strict allowlist.
    return {
        "schema_version": 2, "kind": KIND,
        "coordinate_space": "sway-logical-pixels",
        "outputs": clean_outputs, "workspaces": clean_workspaces,
        "windows": clean_windows, "capture_only": True,
        "session_identity_verified": False,
    }


def validate_pair(v1_document, geometry_document):
    try:
        old = legacy.validate(v1_document)
    except (legacy.StoreError, KeyError, TypeError) as exc:
        raise GeometryStoreError("INVALID LEGACY COMPATIBILITY RECORD") from exc
    geo = validate_geometry(geometry_document)
    old_outputs = {x["connector"]: x["rect"] for x in old["outputs"]}
    geo_outputs = {x["connector"]: x["rect"] for x in geo["outputs"]}
    old_ws = {x["name"]: x["output"] for x in old["workspaces"]}
    geo_ws = {x["name"]: x["output"] for x in geo["workspaces"]}
    old_apps = Counter((x["app_id"], x["workspace"], x["floating"])
                       for x in old["windows"])
    geo_apps = Counter((x["app_id"], x["workspace"], x["floating"])
                       for x in geo["windows"])
    if old_outputs != geo_outputs or old_ws != geo_ws or old_apps != geo_apps:
        raise GeometryStoreError("V1 AND V2 CAPTURES DO NOT MATCH")
    return old, geo


def _checkpoint_id(value):
    return _id(value)


def save_pair(v1_document, geometry_document, *, stage_hook=None):
    """Atomically commit v1 compatibility and v2 geometry, never half a save.

    Deliberately not connected to a CLI, TimeW or live capture path. Caller
    must explicitly provide both projections from the same captured frame.
    `stage_hook` exists only to inject failures in disposable tests.
    """
    legacy_doc, geom = validate_pair(v1_document, geometry_document)
    raw_v1 = json.dumps(legacy_doc, separators=(",", ":"), ensure_ascii=False)
    if len(raw_v1.encode("utf-8")) > legacy.MAX_DOC_BYTES:
        raise GeometryStoreError("LEGACY RECORD TOO LARGE")
    raw_v2 = _raw(geom).decode("utf-8")
    digest = hashlib.sha256(raw_v2.encode("utf-8")).hexdigest()
    cid = str(uuid.uuid4())
    now = dt.datetime.now(dt.timezone.utc).isoformat()

    conn = legacy.connect(writable=True)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        with conn:
            conn.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE} (
                checkpoint_id TEXT PRIMARY KEY
                    REFERENCES checkpoints(id) ON DELETE RESTRICT,
                schema_version INTEGER NOT NULL CHECK(schema_version=2),
                geometry_json TEXT NOT NULL,
                geometry_sha256 TEXT NOT NULL
            )""")
            conn.execute(
                "INSERT INTO checkpoints (id, schema_version, label, saved_at_utc, "
                "captured_at_utc, document_json) VALUES (?, ?, ?, ?, ?, ?)",
                (cid, legacy.SCHEMA_VERSION, legacy_doc["label"], now,
                 legacy_doc["captured_at_utc"], raw_v1))
            if stage_hook is not None:
                stage_hook("after_v1_insert")
            conn.execute(
                f"INSERT INTO {TABLE} (checkpoint_id, schema_version, "
                "geometry_json, geometry_sha256) VALUES (?, 2, ?, ?)",
                (cid, raw_v2, digest))
            if stage_hook is not None:
                stage_hook("after_geometry_insert")
        row = conn.execute("SELECT * FROM checkpoints WHERE id=?", (cid,)).fetchone()
        if row is None:
            raise GeometryStoreError("ATOMIC CHECKPOINT NOT VERIFIED")
        return {"status": "saved", "checkpoint": legacy._summary(row),
                "geometry_available": True,
                "session_identity_verified": False}
    finally:
        conn.close()


def load_geometry(checkpoint_id):
    """Read-only v2 lookup; legacy-only records explicitly remain legacy."""
    cid = _checkpoint_id(checkpoint_id)
    conn = legacy.connect(writable=False)
    if conn is None:
        raise GeometryStoreError("CHECKPOINT NOT FOUND")
    try:
        old = conn.execute("SELECT * FROM checkpoints WHERE id=?", (cid,)).fetchone()
        if old is None:
            raise GeometryStoreError("CHECKPOINT NOT FOUND")
        table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (TABLE,)).fetchone()
        if table is None:
            return {"status": "legacy_only", "checkpoint_id": cid,
                    "geometry_available": False, "read_only": True}
        row = conn.execute(
            f"SELECT geometry_json, geometry_sha256 FROM {TABLE} "
            "WHERE checkpoint_id=?", (cid,)).fetchone()
        if row is None:
            return {"status": "legacy_only", "checkpoint_id": cid,
                    "geometry_available": False, "read_only": True}
        raw = row["geometry_json"].encode("utf-8")
        if hashlib.sha256(raw).hexdigest() != row["geometry_sha256"]:
            raise GeometryStoreError("GEOMETRY RECORD DAMAGED")
        try:
            value = json.loads(raw)
            old_doc = json.loads(old["document_json"])
        except (ValueError, UnicodeError, TypeError) as exc:
            raise GeometryStoreError("GEOMETRY RECORD DAMAGED") from exc
        _, clean = validate_pair(old_doc, value)
        return {"status": "loaded", "checkpoint_id": cid,
                "geometry_available": True, "read_only": True,
                "session_identity_verified": False, "geometry": clean}
    finally:
        conn.close()
