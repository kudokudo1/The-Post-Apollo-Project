#!/usr/bin/env python3
"""MACHINE v2 transaction tests: private temp XDG directory, synthetic frames."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "time"))
import MachineCheckpointStore as legacy
from MachineGeometryV2 import project_geometry
from MachineGeometryStoreV2 import (
    GeometryStoreError, TABLE, save_pair, load_geometry, validate_geometry,
    validate_pair,
)

KEY_A = "11111111-1111-4111-8111-111111111111"
KEY_B = "22222222-2222-4222-8222-222222222222"
KEY_C = "33333333-3333-4333-8333-333333333333"


def rect(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


def leaf(con, app, rectangle, *, floating=False):
    return {
        "type": "con", "id": con, "app_id": app,
        "rect": rectangle, "percent": 0.5 if app == "brave" else None,
        "layout": "none", "floating": "user_on" if floating else "auto_off",
        "nodes": [], "floating_nodes": [],
        "window_rect": None, "deco_rect": None, "geometry": None,
        "fullscreen_mode": 0, "title": "PRIVATE TITLE",
        "pid": 7700,
    }


def fixture():
    outputs = [
        {"name": "DP-3", "active": True, "rect": rect(0, 0, 2560, 1440),
         "scale": 1.0, "transform": "normal"},
        {"name": "HDMI-A-1", "active": True,
         "rect": rect(2560, 0, 1360, 768), "scale": 1.0,
         "transform": "normal"},
    ]
    workspaces = [{"name": "1", "output": "DP-3"},
                  {"name": "2", "output": "HDMI-A-1"}]
    tree = {"type": "root", "nodes": [
        {"type": "output", "name": "DP-3", "nodes": [{
            "type": "workspace", "name": "1", "layout": "splith",
            "rect": rect(0, 0, 2560, 1440),
            "nodes": [leaf(101, "brave", rect(0, 0, 1280, 1440)),
                      leaf(102, "brave", rect(1280, 0, 1280, 1440))],
            "floating_nodes": [],
        }]},
        {"type": "output", "name": "HDMI-A-1", "nodes": [{
            "type": "workspace", "name": "2", "layout": "splith",
            "rect": rect(2560, 0, 1360, 768), "nodes": [],
            "floating_nodes": [
                leaf(103, "kitty", rect(2790, 40, 700, 600), floating=True)],
        }]},
    ]}
    geometry = project_geometry(
        outputs, workspaces, tree,
        window_keys={101: KEY_A, 102: KEY_B, 103: KEY_C})
    legacy_doc = {
        "schema_version": 1, "kind": "sway-layout-selection-preview",
        "preview_only": True, "label": "Exact work layout",
        "captured_at_utc": "2026-11-09T17:48:00+00:00",
        "outputs": [
            {"connector": item["connector"], "rect": item["rect"]}
            for item in geometry["outputs"]],
        "workspaces": [
            {"name": item["name"], "output": item["output"]}
            for item in geometry["workspaces"]],
        "windows": [
            {"app_id": item["app_id"], "workspace": item["workspace"],
             "floating": item["floating"]}
            for item in geometry["windows"]],
    }
    return legacy_doc, geometry


old, geo = fixture()
assert validate_pair(old, geo)[0]["label"] == "Exact work layout"
assert len(validate_geometry(geo)["windows"]) == 3
assert "PRIVATE TITLE" not in json.dumps(validate_geometry(geo))
assert "pid" not in json.dumps(validate_geometry(geo))

def rejects(mutate_old=None, mutate_geom=None):
    a, b = copy.deepcopy((old, geo))
    if mutate_old:
        mutate_old(a)
    if mutate_geom:
        mutate_geom(b)
    try:
        validate_pair(a, b)
    except (GeometryStoreError, legacy.StoreError):
        return
    raise AssertionError("invalid or mismatched snapshot was accepted")

rejects(mutate_geom=lambda x: x["windows"][0].update({"url": "private"}))
rejects(mutate_geom=lambda x: x["windows"][0].update({"rect": "broken"}))
rejects(mutate_geom=lambda x: x["windows"][0].update({"window_key": KEY_C}))
rejects(mutate_geom=lambda x: x["windows"][0].update({"output": "HDMI-A-1"}))
rejects(mutate_geom=lambda x: x["workspaces"][0]["children"][0]
        .update({"window_key": None}))
rejects(mutate_geom=lambda x: x["workspaces"][0]["children"][0]
        .update({"percent": 1.5}))
rejects(mutate_geom=lambda x: x["outputs"][0].update({"scale": float("nan")}))
rejects(mutate_old=lambda x: x["outputs"][0]["rect"].update({"width": 100}))
rejects(mutate_old=lambda x: x["windows"].pop())
rejects(mutate_old=lambda x: x["workspaces"][0].update({"name": "altered"}))

old_xdg = os.environ.get("XDG_DATA_HOME")
with tempfile.TemporaryDirectory(prefix="machine-m2-store-") as temp:
    os.environ["XDG_DATA_HOME"] = temp
    path = legacy.db_path()
    assert legacy.listing()["checkpoints"] == []
    assert not path.exists()
    # Bad input must fail BEFORE creating a file or directory.
    corrupt = copy.deepcopy(geo)
    corrupt["windows"][0]["title"] = "PRIVATE"
    try:
        save_pair(old, corrupt)
    except GeometryStoreError:
        pass
    else:
        raise AssertionError("private payload created a checkpoint")
    assert not path.exists()

    prior = legacy.save(old)
    old_id = prior["checkpoint"]["id"]
    original_bytes = legacy.load(old_id)["document"]
    with sqlite3.connect(path) as conn:
        raw_original = conn.execute(
            "SELECT document_json FROM checkpoints WHERE id=?", (old_id,)
        ).fetchone()[0]
    assert load_geometry(old_id) == {
        "status": "legacy_only", "checkpoint_id": old_id,
        "geometry_available": False, "read_only": True,
    }
    assert legacy.listing()["checkpoints"][0]["id"] == old_id

    # Simulate process interruption after the compatibility row INSERT and
    # after the geometry row INSERT. Neither may leave a partial checkpoint.
    def inject(at):
        def stage(stage):
            if stage == at:
                raise RuntimeError("SYNTHETIC INTERRUPT")
        return stage
    for stage in ("after_v1_insert", "after_geometry_insert"):
        try:
            save_pair(old, geo, stage_hook=inject(stage))
        except RuntimeError as exc:
            assert str(exc) == "SYNTHETIC INTERRUPT"
        else:
            raise AssertionError("failed transaction committed")
        assert len(legacy.listing()["checkpoints"]) == 1
        assert legacy.load(old_id)["document"] == original_bytes
        with sqlite3.connect(path) as conn:
            count = conn.execute(
                f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]
            assert count == 0

    result = save_pair(old, geo)
    assert result["status"] == "saved"
    assert result["geometry_available"] is True
    assert result["session_identity_verified"] is False
    cid = result["checkpoint"]["id"]
    assert cid != old_id
    assert len(legacy.listing()["checkpoints"]) == 2
    assert legacy.load(cid)["document"] == legacy.validate(old)
    assert legacy.load(old_id)["document"] == original_bytes
    v2 = load_geometry(cid)
    assert v2["status"] == "loaded" and v2["read_only"]
    assert v2["geometry_available"] is True
    assert v2["geometry"]["windows"][0]["window_key"] == KEY_A
    assert v2["geometry"]["windows"][0]["rect"] == rect(0, 0, 1280, 1440)
    assert len(v2["geometry"]["workspaces"][0]["children"]) == 2
    assert v2["geometry"]["windows"][2]["floating"] is True
    assert load_geometry(old_id)["status"] == "legacy_only"

    with sqlite3.connect(path) as conn:
        user_version = conn.execute("PRAGMA user_version").fetchone()[0]
        assert user_version == 1  # old reader/writer still works
        stored_original = conn.execute(
            "SELECT document_json FROM checkpoints WHERE id=?", (old_id,)
        ).fetchone()[0]
        assert stored_original == raw_original
        geometry_count = conn.execute(
            f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]
        assert geometry_count == 1
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert path.stat().st_mode & 0o077 == 0
    assert path.parent.stat().st_mode & 0o077 == 0

    # Atomic v2 records are read with a digest and strictly parsed.
    with sqlite3.connect(path) as conn:
        conn.execute(f"UPDATE {TABLE} SET geometry_json='{{}}' WHERE checkpoint_id=?",
                     (cid,))
    try:
        load_geometry(cid)
    except GeometryStoreError as exc:
        assert str(exc) == "GEOMETRY RECORD DAMAGED"
    else:
        raise AssertionError("geometry modification was accepted")

if old_xdg is None:
    os.environ.pop("XDG_DATA_HOME", None)
else:
    os.environ["XDG_DATA_HOME"] = old_xdg

print("MACHINE M2 geometry SQLite // atomic legacy+geometry and rollback PASS")
