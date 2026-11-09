#!/usr/bin/env python3
"""STORED notes QML bridge tests; no user's desktop, app, browser, or data."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "services/time/MachineSaveBridgeV2.py"
import sys
sys.path.insert(0, str(ROOT / "services/time"))
import MachineCheckpointStore as legacy
from MachineCheckpointAnnotations import get_annotation, TABLE


def rect(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


def call(args, env, payload=None):
    result = subprocess.run(
        ["python3", "-B", "-I", str(CLI)] + args,
        input=(json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
              if payload is not None else b"",
        capture_output=True, timeout=8, env=env)
    assert result.stdout, (args, result.stderr)
    assert b"Traceback" not in result.stderr, result.stderr
    return result.returncode, json.loads(result.stdout)


with tempfile.TemporaryDirectory(prefix="machine-stored-notes-") as directory:
    env = dict(os.environ, XDG_DATA_HOME=directory)
    for name in ("SWAYSOCK", "I3SOCK", "WAYLAND_DISPLAY"):
        env.pop(name, None)
    old = os.environ.get("XDG_DATA_HOME")
    try:
        os.environ["XDG_DATA_HOME"] = directory
        db = legacy.db_path()
        status, result = call(["notes-list"], env)
        assert status == 0 and result == {
            "status": "listed", "read_only": True, "items": []}
        assert not db.exists(), "read-only list created user database"

        doc = {
            "schema_version": 1,
            "kind": "sway-layout-selection-preview",
            "preview_only": True,
            "captured_at_utc": "2026-11-09T18:00:00+00:00",
            "label": "Original checkpoint",
            "outputs": [{"connector": "DP-3",
                         "rect": rect(0, 0, 2560, 1440)}],
            "workspaces": [{"name": "1", "output": "DP-3"}],
            "windows": [{"app_id": "brave", "workspace": "1", "floating": False}],
        }
        saved = legacy.save(doc)
        cid = saved["checkpoint"]["id"]
        with sqlite3.connect(db) as conn:
            original = conn.execute(
                "SELECT id,label,saved_at_utc,captured_at_utc,document_json "
                "FROM checkpoints WHERE id=?", (cid,)).fetchone()

        status, result = call(["notes-read", cid], env)
        assert status == 0
        assert result["status"] == "loaded" and result["read_only"]
        assert result["revision"] == 0
        assert result["display_name"] == "Original checkpoint"
        assert result["note"] == ""
        assert result["checkpoint_id"] == cid
        status, result = call(["notes-list"], env)
        assert status == 0 and result["items"] == []

        note = "Desktop remembered\nPrivate note ⟡"
        payload = {
            "checkpoint_id": cid, "display_name": "Monday desktop",
            "note": note, "expected_revision": 0,
        }
        status, updated = call(["notes-update"], env, payload)
        assert status == 0, updated
        assert updated["status"] == "updated"
        assert updated["display_name"] == "Monday desktop"
        assert updated["note"] == note and updated["revision"] == 1
        assert updated["capture_modified"] is False

        status, overlay = call(["notes-list"], env)
        assert status == 0 and overlay["read_only"]
        assert overlay["items"] == [{
            "checkpoint_id": cid, "display_name": "Monday desktop",
            "revision": 1,
        }]
        assert "Private note" not in json.dumps(overlay)
        assert "note" not in overlay["items"][0]
        status, loaded = call(["notes-read", cid], env)
        assert status == 0 and loaded["note"] == note
        assert loaded["original_label"] == "Original checkpoint"

        # Two editors both loaded revision 1. The first wins; the stale
        # editor cannot overwrite the newer name or note.
        first = dict(payload, display_name="Tuesday desktop",
                     note="New version", expected_revision=1)
        status, good = call(["notes-update"], env, first)
        assert status == 0 and good["revision"] == 2
        status, stale = call(["notes-update"], env, first)
        assert status == 1
        assert stale == {
            "status": "error", "reason": "CHECKPOINT NOTES STALE"}
        assert get_annotation(cid)["display_name"] == "Tuesday desktop"
        assert get_annotation(cid)["note"] == "New version"

        # Invalid requests and missing IDs never write notes or create rows.
        for args, value in [
            (["notes-update"], dict(first, expected_revision=True)),
            (["notes-update"], dict(first, display_name="")),
            (["notes-update"], {"note": "no UUID"}),
        ]:
            status, rejected = call(args, env, value)
            assert status == 1
            assert rejected["status"] == "error"
            assert "New version" not in json.dumps(rejected)
        status, rejected = call(["notes-read", str(uuid.uuid4())], env)
        assert status == 1 and rejected["reason"] == "ANNOTATION REJECTED"

        with sqlite3.connect(db) as conn:
            after = conn.execute(
                "SELECT id,label,saved_at_utc,captured_at_utc,document_json "
                "FROM checkpoints WHERE id=?", (cid,)).fetchone()
            assert after == original
            assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
            assert conn.execute("SELECT COUNT(*) FROM "
                                + TABLE).fetchone()[0] == 1
        assert legacy.load(cid)["checkpoint"]["label"] == "Original checkpoint"
    finally:
        if old is None:
            os.environ.pop("XDG_DATA_HOME", None)
        else:
            os.environ["XDG_DATA_HOME"] = old

print("MACHINE STORED notes // isolated CLI, names overlay, stale refusal PASS")
