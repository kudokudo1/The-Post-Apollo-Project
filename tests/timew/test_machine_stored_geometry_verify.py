#!/usr/bin/env python3
"""STORED geometry verification uses only read-only v1/v2 checkpoint APIs."""
import copy
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "time"))
import MachineCheckpointStore as legacy
from MachineGeometryV2 import project_geometry
from MachineGeometryStoreV2 import (
    save_pair, load_geometry, TABLE, GeometryStoreError)
from MachineSaveBridgeV2 import inspect_checkpoint, BridgeError


def rect(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


def capture():
    outputs = [
        {"name": "HEADLESS-1", "active": True,
         "rect": rect(0, 0, 1600, 900),
         "scale": 1.0, "transform": "normal"},
    ]
    workspaces = [{"name": "1", "output": "HEADLESS-1"}]
    app = {
        "type": "con", "id": 51, "app_id": "brave", "layout": "none",
        "rect": rect(0, 0, 1600, 900), "percent": 1.0,
        "floating": "auto_off", "fullscreen_mode": 0,
        "window_rect": None, "deco_rect": None, "geometry": None,
        "nodes": [], "floating_nodes": [],
        "title": "PRIVATE TAB", "pid": 999,
    }
    tree = {
        "type": "root", "nodes": [
            {"type": "output", "name": "HEADLESS-1", "nodes": [
                {"type": "workspace", "name": "1", "layout": "splith",
                 "rect": rect(0, 0, 1600, 900),
                 "nodes": [app], "floating_nodes": []},
            ]},
        ],
    }
    geo = project_geometry(
        outputs, workspaces, tree,
        window_keys={51: "11111111-1111-4111-8111-111111111111"})
    v1 = {
        "schema_version": 1,
        "kind": "sway-layout-selection-preview",
        "preview_only": True,
        "captured_at_utc": "2026-11-09T17:00:00+00:00",
        "label": "TEST GEOMETRY",
        "outputs": [{"connector": "HEADLESS-1",
                     "rect": rect(0, 0, 1600, 900)}],
        "workspaces": [{"name": "1", "output": "HEADLESS-1"}],
        "windows": [{"app_id": "brave", "workspace": "1", "floating": False}],
    }
    return v1, geo


original_xdg = os.environ.get("XDG_DATA_HOME")
try:
    with tempfile.TemporaryDirectory(prefix="timew-verify-geometry-") as tmp:
        os.environ["XDG_DATA_HOME"] = tmp
        path = legacy.db_path()
        absent = str(uuid.uuid4())
        try:
            inspect_checkpoint(absent)
        except legacy.StoreError:
            pass
        else:
            raise AssertionError("missing DB incorrectly verified")
        assert not path.exists()

        v1, geo = capture()
        old = legacy.save(v1)
        old_id = old["checkpoint"]["id"]
        legacy_summary = legacy.load(old_id)["checkpoint"]
        legacy_only = inspect_checkpoint(old_id)
        assert legacy_only == {
            "kind": "machine-stored-geometry-verification",
            "checkpoint_id": old_id,
            "read_only": True,
            "exact_restore_verified": False,
            "session_identity_verified": False,
            "status": "legacy_only",
            "geometry_available": False,
            "counts": {"outputs": 1, "workspaces": 1, "windows": 1},
        }
        assert legacy.load(old_id)["checkpoint"] == legacy_summary

        saved = save_pair(v1, geo)
        cid = saved["checkpoint"]["id"]
        assert cid != old_id
        verified = inspect_checkpoint(cid)
        assert verified["status"] == "geometry_verified"
        assert verified["geometry_available"] is True
        assert verified["counts"] == {
            "outputs": 1, "workspaces": 1, "windows": 1}
        assert verified["read_only"] is True
        assert verified["exact_restore_verified"] is False
        assert verified["session_identity_verified"] is False
        raw = json.dumps(verified)
        for private in ("PRIVATE TAB", '"pid"', '"title"', '"window_key"'):
            assert private not in raw

        # Preserve record identity; a reader cannot manufacture approval.
        checked = load_geometry(cid)
        wrong = copy.deepcopy(checked)
        wrong["geometry"]["windows"].clear()
        mismatch = inspect_checkpoint(cid, geometry_reader=lambda _: wrong)
        assert mismatch["status"] == "geometry_mismatch"
        assert mismatch["exact_restore_verified"] is False

        for bad in ("bad", cid.upper(), " " + cid, 42):
            try:
                inspect_checkpoint(bad)
            except BridgeError:
                pass
            else:
                raise AssertionError("accepted invalid checkpoint identity")

        # Corrupt stored JSON after commit; real reader must refuse it.
        with sqlite3.connect(path) as conn:
            conn.execute(f"UPDATE {TABLE} SET geometry_json='{{}}'"
                         " WHERE checkpoint_id=?", (cid,))
        try:
            inspect_checkpoint(cid)
        except GeometryStoreError:
            pass
        else:
            raise AssertionError("accepted corrupt persistent geometry")
        assert inspect_checkpoint(old_id)["status"] == "legacy_only"
finally:
    if original_xdg is None:
        os.environ.pop("XDG_DATA_HOME", None)
    else:
        os.environ["XDG_DATA_HOME"] = original_xdg

print("MACHINE STORED // verified, legacy, mismatch and corrupted geometry PASS")
