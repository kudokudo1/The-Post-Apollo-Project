#!/usr/bin/env python3
"""MACHINE annotations: temporary SQLite, legacy + geometry preservation."""
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
from MachineCheckpointAnnotations import (
    AnnotationError, TABLE, get_annotation, set_annotation)
from MachineGeometryV2 import project_geometry
from MachineGeometryStoreV2 import save_pair, load_geometry


def rect(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


def fixtures():
    box = rect(0, 0, 1600, 900)
    outputs = [{"name": "DP-3", "active": True, "rect": box,
                "scale": 1.0, "transform": "normal"}]
    workspaces = [{"name": "1", "output": "DP-3"}]
    tree = {"type": "root", "nodes": [
        {"type": "output", "name": "DP-3", "nodes": [
            {"type": "workspace", "name": "1", "layout": "splith",
             "rect": box, "nodes": [
                 {"type": "con", "id": 101, "app_id": "brave", "rect": box,
                  "percent": 1.0, "layout": "none", "floating": "auto_off",
                  "window_rect": None, "deco_rect": None, "geometry": None,
                  "fullscreen_mode": 0, "nodes": [], "floating_nodes": [],
                  "title": "PRIVATE PAGE", "pid": 50},
             ], "floating_nodes": []},
        ]},
    ]}
    geometry = project_geometry(
        outputs, workspaces, tree,
        window_keys={101: "11111111-1111-4111-8111-111111111111"})
    v1 = {
        "schema_version": 1, "kind": "sway-layout-selection-preview",
        "preview_only": True,
        "captured_at_utc": "2026-11-09T18:00:00+00:00",
        "label": "Original work desktop",
        "outputs": [{"connector": "DP-3", "rect": box}],
        "workspaces": [{"name": "1", "output": "DP-3"}],
        "windows": [{"app_id": "brave", "workspace": "1",
                     "floating": False}],
    }
    return v1, geometry


def refused(call, needle):
    try:
        call()
    except AnnotationError as error:
        assert needle in str(error), (needle, str(error))
    else:
        raise AssertionError("invalid annotation write accepted")


old_xdg = os.environ.get("XDG_DATA_HOME")
try:
    with tempfile.TemporaryDirectory(prefix="machine-annotations-") as tmp:
        os.environ["XDG_DATA_HOME"] = tmp
        path = legacy.db_path()
        nonexistent = str(uuid.uuid4())
        refused(lambda: get_annotation(nonexistent), "NOT FOUND")
        refused(lambda: set_annotation(
            nonexistent, display_name="X", note="", expected_revision=0),
            "NOT FOUND")
        refused(lambda: get_annotation("not-uuid"), "INVALID CHECKPOINT ID")
        assert not path.exists(), "missing UUID created a database"

        v1, geometry = fixtures()
        original = legacy.save(v1)
        legacy_id = original["checkpoint"]["id"]
        prior = get_annotation(legacy_id)
        assert prior["display_name"] == "Original work desktop"
        assert prior["note"] == "" and prior["revision"] == 0
        assert prior["read_only"] and not prior["capture_modified"]
        with sqlite3.connect(path) as conn:
            table_names = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            assert TABLE not in table_names

        added = save_pair(v1, geometry)
        geometry_id = added["checkpoint"]["id"]
        orig_geo = load_geometry(geometry_id)["geometry"]
        with sqlite3.connect(path) as conn:
            original_rows = conn.execute(
                "SELECT id, label, saved_at_utc, captured_at_utc, "
                "document_json FROM checkpoints ORDER BY id").fetchall()
            raw_geometry = conn.execute(
                "SELECT geometry_json, geometry_sha256 FROM "
                "machine_checkpoint_geometry_v2 WHERE checkpoint_id=?",
                (geometry_id,)).fetchone()
            assert conn.execute("PRAGMA user_version").fetchone()[0] == 1

        def interrupt(stage_name):
            def hook(stage):
                if stage == stage_name:
                    raise RuntimeError("INJECTED TRANSACTION INTERRUPT")
            return hook

        for stage in ("before_write", "after_write"):
            try:
                set_annotation(
                    geometry_id, display_name="Draft 1", note="private",
                    expected_revision=0, stage_hook=interrupt(stage))
            except RuntimeError:
                pass
            else:
                raise AssertionError("interrupted insert committed")
            assert get_annotation(geometry_id)["revision"] == 0
            with sqlite3.connect(path) as conn:
                assert conn.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE "
                    "type='table' AND name=?", (TABLE,)).fetchone()[0] == 0

        note = "Workspace layout\nRemember second display"
        created = set_annotation(
            geometry_id, display_name="  Work and research  ",
            note=note, expected_revision=0)
        assert created["status"] == "updated" and not created["read_only"]
        assert created["display_name"] == "Work and research"
        assert created["note"] == note and created["revision"] == 1
        assert created["updated_at_utc"].endswith("+00:00")
        verified = get_annotation(geometry_id)
        assert verified["display_name"] == "Work and research"
        assert verified["revision"] == 1 and verified["read_only"]
        assert verified["original_label"] == "Original work desktop"

        refused(lambda: set_annotation(
            geometry_id, display_name="Other editor", note="changed",
            expected_revision=0), "STALE")
        for stage in ("before_write", "after_write"):
            try:
                set_annotation(
                    geometry_id, display_name="Partial", note="BAD",
                    expected_revision=1, stage_hook=interrupt(stage))
            except RuntimeError:
                pass
            else:
                raise AssertionError("interrupted update committed")
            assert get_annotation(geometry_id) == verified

        updated = set_annotation(
            geometry_id, display_name="Final desktop", note="",
            expected_revision=1)
        assert updated["revision"] == 2 and updated["note"] == ""
        assert get_annotation(geometry_id)["display_name"] == "Final desktop"
        old_anno = set_annotation(
            legacy_id, display_name="Legacy notes", note="not a v2 save",
            expected_revision=0)
        assert old_anno["revision"] == 1
        assert get_annotation(legacy_id)["original_label"] == "Original work desktop"

        # All validation failures happen before a new mutation.
        for values, error in [
            ({"display_name": "", "note": ""}, "NAME"),
            ({"display_name": "X" * 49, "note": ""}, "NAME"),
            ({"display_name": "bad\nlabel", "note": ""}, "NAME"),
            ({"display_name": "ok", "note": "X" * 1025}, "NOTE"),
            ({"display_name": "ok", "note": "bad\x00note"}, "NOTE"),
        ]:
            refused(lambda values=values: set_annotation(
                geometry_id, expected_revision=2, **values),
                error)
        refused(lambda: set_annotation(
            geometry_id, display_name="ok", note="ok",
            expected_revision=True), "REVISION")
        refused(lambda: set_annotation(
            geometry_id.upper(), display_name="ok", note="ok",
            expected_revision=2), "INVALID CHECKPOINT ID")

        # Metadata must never rewrite the old checkpoint's label or JSON.
        with sqlite3.connect(path) as conn:
            rows_after = conn.execute(
                "SELECT id, label, saved_at_utc, captured_at_utc, "
                "document_json FROM checkpoints ORDER BY id").fetchall()
            geometry_after = conn.execute(
                "SELECT geometry_json, geometry_sha256 FROM "
                "machine_checkpoint_geometry_v2 WHERE checkpoint_id=?",
                (geometry_id,)).fetchone()
            assert rows_after == original_rows
            assert geometry_after == raw_geometry
            assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

        assert legacy.load(geometry_id)["document"] == legacy.validate(v1)
        assert legacy.load(legacy_id)["checkpoint"]["label"] == "Original work desktop"
        assert load_geometry(geometry_id)["geometry"] == orig_geo
        assert "Workspace layout" not in json.dumps(orig_geo)
        assert len(legacy.listing()["checkpoints"]) == 2
finally:
    if old_xdg is None:
        os.environ.pop("XDG_DATA_HOME", None)
    else:
        os.environ["XDG_DATA_HOME"] = old_xdg

print("MACHINE notes // atomic revisioned annotations and unchanged checkpoints PASS")
