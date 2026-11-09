#!/usr/bin/env python3
"""MACHINE v2 capture/save; synthetic Sway reads and private SQLite only."""
from __future__ import annotations

import copy
import datetime as dt
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "time"))
from MachineCaptureSaveV2 import capture_and_save, CaptureError
from MachineGeometryStoreV2 import load_geometry
import MachineCheckpointStore as legacy

KEY1 = "11111111-1111-4111-8111-111111111111"
KEY2 = "22222222-2222-4222-8222-222222222222"
KEY3 = "33333333-3333-4333-8333-333333333333"


def rect(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


def window(id_, app, box, floating=False):
    return {"type": "floating_con" if floating else "con", "id": id_,
            "app_id": app, "rect": box, "layout": "none",
            "percent": 0.5 if not floating else None,
            "floating": "user_on" if floating else "auto_off",
            "window_rect": None, "deco_rect": None, "geometry": None,
            "fullscreen_mode": 0, "name": "SECRET PAGE TITLE",
            "pid": 123456, "nodes": [], "floating_nodes": []}


def fixture():
    outputs = [
        {"name": "DP-3", "active": True, "rect": rect(0, 0, 2560, 1440),
         "scale": 1.0, "transform": "normal", "serial": "PRIVATE"},
        {"name": "HDMI-A-1", "active": True, "rect": rect(2560, 0, 1360, 768),
         "scale": 1.0, "transform": "normal"},
    ]
    workspaces = [{"name": "1", "output": "DP-3"},
                  {"name": "2", "output": "HDMI-A-1"}]
    first = {"type": "workspace", "name": "1",
             "layout": "splith", "rect": rect(0, 0, 2560, 1440),
             "nodes": [
                window(101, "brave", rect(0, 0, 1280, 1440)),
                window(102, "brave", rect(1280, 0, 1280, 1440)),
             ], "floating_nodes": []}
    second = {"type": "workspace", "name": "2",
              "layout": "splith", "rect": rect(2560, 0, 1360, 768),
              "nodes": [], "floating_nodes": [
                  window(103, "kitty", rect(2700, 40, 700, 600), True)]}
    tree = {"type": "root", "nodes": [
        {"type": "output", "name": "DP-3", "nodes": [first]},
        {"type": "output", "name": "HDMI-A-1", "nodes": [second]},
    ]}
    return [outputs, workspaces, tree]


def reader(first, second=None):
    """Enforce two rounds of three fixed, read-only Sway commands."""
    calls = []
    frames = [copy.deepcopy(first), copy.deepcopy(first if second is None else second)]

    def call(command, **options):
        assert command == ["swaymsg", "-r", "-t", ("get_outputs", "get_workspaces", "get_tree")[len(calls) % 3]]
        assert options == {"check": True, "capture_output": True,
                           "timeout": 3, "shell": False}
        frame = frames[len(calls) // 3]
        value = frame[len(calls) % 3]
        calls.append(command)
        return SimpleNamespace(stdout=json.dumps(value).encode())
    return call, calls


def keys():
    ids = iter((KEY1, KEY2, KEY3))
    return lambda: next(ids)


def fake_clock():
    # Internal UTC timestamp is independent of display timezone.
    return dt.datetime(2026, 11, 9, 8, 50, tzinfo=dt.timezone(dt.timedelta(hours=-5)))


def fail(message, *, first=None, second=None, key_factory=keys(), label="TEST",
         store_adapter=None):
    read, calls = reader(first or fixture(), second)
    args = {"label": label, "read_runner": read, "clock": fake_clock,
            "key_factory": key_factory}
    if store_adapter is not None:
        args["store_adapter"] = store_adapter
    try:
        capture_and_save(**args)
    except CaptureError as exc:
        assert message in str(exc), (message, str(exc))
    else:
        raise AssertionError("bad capture was accepted")
    return calls


old_xdg = os.environ.get("XDG_DATA_HOME")
try:
    with tempfile.TemporaryDirectory(prefix="machine-capture-save-test-") as tmp:
        os.environ["XDG_DATA_HOME"] = tmp
        path = legacy.db_path()
        assert not path.exists()
        frame = fixture()
        changed = copy.deepcopy(frame)
        changed[2]["nodes"][0]["nodes"][0]["nodes"][0]["rect"]["width"] -= 1
        assert len(fail("DESKTOP CHANGED", second=changed)) == 6
        assert not path.exists(), "unstable capture reached persistence"

        replaced = copy.deepcopy(frame)
        replaced[2]["nodes"][0]["nodes"][0]["nodes"][0]["id"] = 444
        fail("DESKTOP CAPTURE UNAVAILABLE", second=replaced)
        assert not path.exists()

        moved = copy.deepcopy(frame)
        moved[2]["nodes"][1]["nodes"][0]["floating_nodes"][0]["rect"]["x"] += 30
        fail("DESKTOP CHANGED", second=moved)
        assert not path.exists()

        # A reused identity is never silently accepted for duplicate Brave windows.
        fail("DUPLICATE", key_factory=lambda: KEY1)
        assert not path.exists()

        fail("INVALID CHECKPOINT NAME", label="name\nsecret")
        assert not path.exists()

        # An existing original v1 checkpoint is preserved exactly.
        legacy_doc = {
            "schema_version": 1, "kind": "sway-layout-selection-preview",
            "preview_only": True,
            "captured_at_utc": "2026-11-09T10:00:00+00:00",
            "label": "OLD DESKTOP",
            "outputs": [{"connector": "DP-3", "rect": rect(0, 0, 2560, 1440)}],
            "workspaces": [{"name": "1", "output": "DP-3"}],
            "windows": [{"app_id": "brave", "workspace": "1", "floating": False}],
        }
        prior = legacy.save(legacy_doc)
        old_id = prior["checkpoint"]["id"]
        old_bytes = path.read_bytes()
        original_document = legacy.load(old_id)["document"]

        run, calls = reader(frame)
        result = capture_and_save(
            label="DESKTOP A", read_runner=run, clock=fake_clock, key_factory=keys())
        assert len(calls) == 6
        assert result["status"] == "saved" and result["geometry_available"]
        assert result["session_identity_verified"] is False
        assert result["checkpoint"]["counts"] == {"outputs": 2, "workspaces": 2, "windows": 3}
        saved_id = result["checkpoint"]["id"]
        loaded = legacy.load(saved_id)
        assert loaded["document"]["label"] == "DESKTOP A"
        assert loaded["document"]["captured_at_utc"] == "2026-11-09T13:50:00+00:00"
        assert legacy.load(old_id)["document"] == original_document
        detailed = load_geometry(saved_id)
        assert detailed["status"] == "loaded"
        assert len(detailed["geometry"]["windows"]) == 3
        assert [w["app_id"] for w in detailed["geometry"]["windows"]].count("brave") == 2
        assert detailed["geometry"]["windows"][2]["floating"] is True
        assert detailed["geometry"]["windows"][0]["rect"]["width"] == 1280
        assert "SECRET PAGE TITLE" not in json.dumps(detailed)
        assert "PRIVATE" not in json.dumps(detailed)
        assert "123456" not in json.dumps(detailed)
        assert legacy.listing()["checkpoints"][1]["id"] == old_id

        # No database mutation if the desktop changes on the next save.
        stable_list = legacy.listing()
        fail("DESKTOP CHANGED", second=changed)
        assert legacy.listing() == stable_list

        # Storage failure propagates and does not imply successful save.
        def storage_failure(*args):
            raise RuntimeError("synthetic disk failure")
        try:
            capture_and_save(label="FAIL", read_runner=reader(frame)[0],
                             clock=fake_clock, key_factory=keys(),
                             store_adapter=storage_failure)
        except RuntimeError:
            pass
        else:
            raise AssertionError("storage failure was hidden")
        assert legacy.listing() == stable_list
finally:
    if old_xdg is None:
        os.environ.pop("XDG_DATA_HOME", None)
    else:
        os.environ["XDG_DATA_HOME"] = old_xdg

print("MACHINE M2 automatic capture // two-read stability + atomic v2 save PASS")
