#!/usr/bin/env python3
"""MACHINE v2 custom selection: pure geometry and one-call SAVE regression.

No user compositor, browser, or permanent filesystem access. Only supplied
Sway-shaped fixtures and a temporary SQLite database.
"""
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
from MachineCaptureSelectionV2 import select_geometry, SelectionError
from MachineCaptureSaveV2 import capture_and_save, CaptureError
from MachineGeometryV2 import project_geometry
from MachineGeometryStoreV2 import load_geometry
import MachineCheckpointStore as legacy

A = "11111111-1111-4111-8111-111111111111"
B = "22222222-2222-4222-8222-222222222222"
C = "33333333-3333-4333-8333-333333333333"


def rect(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


def leaf(id_, app, box, *, floating=False):
    return {
        "type": "floating_con" if floating else "con",
        "id": id_, "app_id": app, "rect": box,
        "percent": None, "layout": "none",
        "floating": "user_on" if floating else "auto_off",
        "fullscreen_mode": 0, "nodes": [], "floating_nodes": [],
        "name": "SECRET USER WINDOW TITLE", "pid": 12345,
    }


def fixture():
    outputs = [
        {"name": "DP-3", "active": True,
         "rect": rect(0, 0, 2560, 1440), "scale": 1.0,
         "transform": "normal", "serial": "PRIVATE MONITOR SERIAL"},
        {"name": "HDMI-A-1", "active": True,
         "rect": rect(2560, 0, 1360, 768), "scale": 1.0,
         "transform": "normal"},
    ]
    workspaces = [{"name": "1", "output": "DP-3"},
                  {"name": "2", "output": "HDMI-A-1"}]
    tiled = {
        "type": "con", "id": 99, "rect": rect(0, 0, 2560, 1440),
        "percent": 1.0, "layout": "splith",
        "nodes": [leaf(101, "brave", rect(0, 0, 1280, 1440)),
                  leaf(102, "brave", rect(1280, 0, 1280, 1440))],
        "floating_nodes": [],
    }
    first = {
        "type": "workspace", "name": "1", "layout": "splith",
        "rect": rect(0, 0, 2560, 1440),
        "nodes": [tiled], "floating_nodes": [],
    }
    second = {
        "type": "workspace", "name": "2", "layout": "splith",
        "rect": rect(2560, 0, 1360, 768),
        "nodes": [], "floating_nodes": [
            leaf(103, "kitty", rect(2760, 50, 900, 600), floating=True),
        ],
    }
    tree = {
        "type": "root",
        "nodes": [
            {"type": "output", "name": "DP-3", "nodes": [first]},
            {"type": "output", "name": "HDMI-A-1", "nodes": [second]},
        ],
    }
    return [outputs, workspaces, tree]


source = fixture()
whole = project_geometry(*source, window_keys={101: A, 102: B, 103: C})
unchanged = copy.deepcopy(whole)
assert select_geometry(whole) == select_geometry(whole, {})
assert len(select_geometry(whole)["windows"]) == 3
assert len(select_geometry(whole)["outputs"]) == 2

main_only = select_geometry(whole, {"outputs": ["DP-3"]})
assert [x["connector"] for x in main_only["outputs"]] == ["DP-3"]
assert [x["name"] for x in main_only["workspaces"]] == ["1"]
assert len(main_only["windows"]) == 2
assert all(x["app_id"] == "brave" for x in main_only["windows"])
assert len(main_only["workspaces"][0]["children"][0]["children"]) == 2

second_only = select_geometry(whole, {"outputs": ["HDMI-A-1"]})
assert len(second_only["windows"]) == 1
assert second_only["windows"][0]["window_key"] == C
assert second_only["windows"][0]["floating"] is True
assert second_only["windows"][0]["rect"] == rect(2760, 50, 900, 600)

single = select_geometry(whole, {"windows": [A]})
assert [x["window_key"] for x in single["windows"]] == [A]
assert len(single["workspaces"][0]["children"]) == 1
assert len(single["workspaces"][0]["children"][0]["children"]) == 1
assert single["workspaces"][0]["children"][0]["children"][0]["window_key"] == A
assert single["workspaces"][0]["children"][0]["layout"] == "splith"
assert single["windows"][0]["rect"]["width"] == 1280
assert single["workspaces"][1]["floating_children"] == []

empty_windows = select_geometry(whole, {"windows": []})
assert empty_windows["windows"] == []
assert all(not x["children"] and not x["floating_children"]
           for x in empty_windows["workspaces"])

empty_workspaces = select_geometry(whole, {"workspaces": []})
assert empty_workspaces["workspaces"] == []
assert empty_workspaces["windows"] == []
assert len(empty_workspaces["outputs"]) == 2
assert whole == unchanged, "custom selection mutated the original capture"


def refused(selection, message):
    try:
        select_geometry(whole, selection)
    except SelectionError as exc:
        assert message in str(exc), str(exc)
    else:
        raise AssertionError("INVALID CUSTOM SCOPE ACCEPTED: " + str(selection))


refused({"outputs": []}, "NO MONITORS")
refused({"outputs": ["DP-3", "DP-3"]}, "DUPLICATE")
refused({"outputs": ["DP-GONE"]}, "STALE")
refused({"outputs": "DP-3"}, "INVALID SELECTION LIST")
refused({"workspaces": ["3"]}, "STALE")
refused({"windows": [A, A]}, "DUPLICATE")
refused({"windows": ["NOT-UUID"]}, "INVALID WINDOW")
refused({"windows": ["44444444-4444-4444-8444-444444444444"]}, "STALE")
refused({"outputs": ["DP-3"], "workspaces": ["2"]}, "EXCLUDED MONITOR")
refused({"outputs": ["DP-3"], "windows": [C]}, "EXCLUDED WORKSPACE")
refused({"workspaces": ["1"], "windows": [C]}, "EXCLUDED WORKSPACE")
refused({"mystery": [A]}, "UNKNOWN SELECTION FIELDS")
refused(None, "THIS MUST NOT BE CALLED") if False else None


def make_runner():
    calls = []
    def run(command, **kwargs):
        assert kwargs == {"check": True, "capture_output": True,
                          "timeout": 3, "shell": False}
        assert command == [
            "swaymsg", "-r", "-t",
            ("get_outputs", "get_workspaces", "get_tree")[len(calls) % 3],
        ]
        if len(calls) >= 6:
            raise AssertionError("UNEXPECTED ADDITIONAL SWAY READ")
        doc = source[len(calls) % 3]
        calls.append(command)
        return SimpleNamespace(stdout=json.dumps(doc).encode("utf-8"))
    return run, calls


def make_keys():
    it = iter([A, B, C])
    return lambda: next(it)


def clock():
    return dt.datetime(2026, 11, 9, 8, 50,
                       tzinfo=dt.timezone(dt.timedelta(hours=-5)))


original_xdg = os.environ.get("XDG_DATA_HOME")
try:
    with tempfile.TemporaryDirectory(prefix="machine-m2-select-") as base:
        os.environ["XDG_DATA_HOME"] = base
        assert not legacy.db_path().exists()
        for invalid in (
            {"outputs": []},
            {"outputs": ["DP-3"], "windows": [C]},
            {"windows": ["44444444-4444-4444-8444-444444444444"]},
        ):
            runner, calls = make_runner()
            try:
                capture_and_save(
                    label="INVALID SCOPE", selection=invalid,
                    read_runner=runner, key_factory=make_keys(),
                    clock=clock)
            except CaptureError as exc:
                assert str(exc)
            else:
                raise AssertionError("invalid scope was saved")
            assert len(calls) == 6
            assert not legacy.db_path().exists(), "invalid selection wrote storage"

        run, calls = make_runner()
        saved = capture_and_save(
            label="Only Brave A", selection={"outputs": ["DP-3"],
                                            "windows": [A]},
            read_runner=run, key_factory=make_keys(), clock=clock)
        assert saved["status"] == "saved"
        assert len(calls) == 6
        assert saved["checkpoint"]["counts"] == {
            "outputs": 1, "workspaces": 1, "windows": 1,
        }
        checkpoint_id = saved["checkpoint"]["id"]
        legacy_row = legacy.load(checkpoint_id)["document"]
        detailed = load_geometry(checkpoint_id)["geometry"]
        assert [x["app_id"] for x in legacy_row["windows"]] == ["brave"]
        assert [x["window_key"] for x in detailed["windows"]] == [A]
        assert [x["connector"] for x in detailed["outputs"]] == ["DP-3"]
        assert detailed["windows"][0]["rect"] == rect(0, 0, 1280, 1440)
        assert len(detailed["workspaces"][0]["children"][0]["children"]) == 1
        assert "SECRET USER WINDOW TITLE" not in json.dumps(detailed)
        assert "PRIVATE MONITOR SERIAL" not in json.dumps(detailed)
        assert "pid" not in json.dumps(detailed)
        assert saved["session_identity_verified"] is False

        # Ordinary one-click SAVE remains all-inclusive. No need to pass a
        # custom selection or preview from the interface.
        all_run, all_calls = make_runner()
        all_saved = capture_and_save(
            label="Whole Desktop", read_runner=all_run,
            key_factory=make_keys(), clock=clock)
        assert len(all_calls) == 6
        assert all_saved["checkpoint"]["counts"] == {
            "outputs": 2, "workspaces": 2, "windows": 3,
        }
        assert len(load_geometry(all_saved["checkpoint"]["id"])["geometry"]["windows"]) == 3
        assert len(legacy.listing()["checkpoints"]) == 2
        assert legacy.load(checkpoint_id)["document"] == legacy_row
finally:
    if original_xdg is None:
        os.environ.pop("XDG_DATA_HOME", None)
    else:
        os.environ["XDG_DATA_HOME"] = original_xdg

print("MACHINE M2 custom scope // per-window tree pruning + automatic SAVE PASS")
