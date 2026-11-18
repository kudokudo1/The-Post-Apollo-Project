#!/usr/bin/env python3
"""MACHINE V2 review: real temporary SQLite and synthetic two-output Sway.

No Sway process, user's desktop, browser or protected archive is accessed.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/time"))
import MachineCheckpointStore as legacy
from MachineCaptureSaveV2 import _legacy_from_geometry
from MachineGeometryV2 import project_geometry
from MachineGeometryStoreV2 import save_pair, load_geometry
from MachineRestoreReviewV2 import plan, inspect, main, ReviewError, OBSERVED


def rect(x, y, width, height):
    return {"x": x, "y": y, "width": width, "height": height}


def leaf(con, app, r, *, floating=False):
    return {
        "type": "con", "id": con, "app_id": app,
        "rect": r, "percent": None, "layout": "none",
        "floating": "user_on" if floating else "auto_off",
        "nodes": [], "floating_nodes": [],
        "window_rect": None, "deco_rect": None, "geometry": None,
        "fullscreen_mode": 0, "title": "PRIVATE TITLE", "pid": 73123,
    }


def frame():
    outputs = [
        {"name": "DP-3", "active": True, "rect": rect(0, 0, 2560, 1440),
         "scale": 1.0, "transform": "normal"},
        {"name": "HDMI-A-1", "active": True,
         "rect": rect(2560, 0, 1360, 768),
         "scale": 1.0, "transform": "normal"},
    ]
    workspaces = [
        {"name": "1", "output": "DP-3"},
        {"name": "2", "output": "HDMI-A-1"},
    ]
    tree = {"type": "root", "nodes": [
        {"type": "output", "name": "DP-3", "nodes": [
            {"type": "workspace", "name": "1", "layout": "splith",
             "rect": rect(0, 0, 2560, 1440),
             "nodes": [leaf(101, "brave", rect(0, 0, 1280, 1440)),
                       leaf(102, "brave", rect(1280, 0, 1280, 1440))],
             "floating_nodes": [],
            }]},
        {"type": "output", "name": "HDMI-A-1", "nodes": [
            {"type": "workspace", "name": "2", "layout": "splith",
             "rect": rect(2560, 0, 1360, 768), "nodes": [],
             "floating_nodes": [leaf(103, "kitty",
                                     rect(2790, 40, 700, 600), floating=True)],
            }]},
    ]}
    return outputs, workspaces, tree


SAVED_KEYS = {
    101: "11111111-1111-4111-8111-111111111111",
    102: "22222222-2222-4222-8222-222222222222",
    103: "33333333-3333-4333-8333-333333333333",
}
LIVE_KEYS = {
    101: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    102: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
    103: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
    104: "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
}


def projected(source=None, *, saved=False):
    source = frame() if source is None else source
    # Each synthetic variant has its own exact window set. Like the real
    # capture adapter, reject extraneous/transient keys instead of bypassing
    # the projector's strict complete-map validation.
    ids = set()
    def visit(node):
        if node.get("app_id") and node.get("id") is not None:
            ids.add(node["id"])
        for name in ("nodes", "floating_nodes"):
            for child in node.get(name, []):
                visit(child)
    visit(source[2])
    available = SAVED_KEYS if saved else LIVE_KEYS
    assert ids <= set(available)
    return project_geometry(*source, window_keys={
        key: available[key] for key in ids})


def reasons(value):
    return [x["classification"] for x in value["items"]]


def refuses(fn):
    try:
        fn()
    except (ReviewError, ValueError, TypeError, KeyError):
        return
    raise AssertionError("unsafe review input was accepted")


old_home = os.environ.get("XDG_DATA_HOME")
try:
    with tempfile.TemporaryDirectory(prefix="machine-v2-review-") as root:
        os.environ["XDG_DATA_HOME"] = root
        saved_geometry = projected(saved=True)
        old = _legacy_from_geometry(
            saved_geometry, label="SYNTHETIC LAYOUT",
            captured_at="2026-11-18T00:00:00+00:00")
        receipt = save_pair(old, saved_geometry)
        checkpoint_id = receipt["checkpoint"]["id"]
        store = legacy.load(checkpoint_id)
        geometry = load_geometry(checkpoint_id)
        live = projected()

        review = plan(checkpoint_id, store, geometry, live)
        assert review["status"] == "review_only"
        assert review["counts"] == {
            "saved_windows": 3, "observed_untrusted": 1,
            "needs_attention": 2}
        assert reasons(review) == [
            "AMBIGUOUS_APP_INSTANCES", "AMBIGUOUS_APP_INSTANCES", OBSERVED]
        assert all(row["identity_verified"] is False
                   and row["action_allowed"] is False for row in review["items"])
        assert all(review[x] is False for x in (
            "restore_allowed", "browser_tabs_restorable",
            "exact_geometry_restore_verified", "live_window_identity_verified",
            "checkpoint_keys_are_live_identity"))
        assert review["safe_actions"] == []
        assert review["requires_fresh_recheck"] is True
        # Matching rectangles with entirely DIFFERENT current UUIDs
        # must never become an authenticated live-window match.
        assert live["windows"][2]["window_key"] != saved_geometry["windows"][2]["window_key"]
        assert OBSERVED in reasons(review)
        emitted = json.dumps(review, sort_keys=True)
        assert "PRIVATE TITLE" not in emitted
        assert "73123" not in emitted
        assert "http" not in emitted.lower()
        assert "live_con_id" not in emitted

        result = inspect(checkpoint_id,
                         legacy_reader=lambda _: store,
                         geometry_reader=lambda _: geometry,
                         live_reader=lambda: live)
        assert result == review

        changed = frame()
        changed[2]["nodes"][1]["nodes"][0]["floating_nodes"][0]["rect"]["x"] += 10
        assert reasons(plan(checkpoint_id, store, geometry, projected(changed)))[2] == (
            "CURRENT_RECTANGLE_DIFFERENT")

        missing_output = frame()
        missing_output[0].pop()
        missing_output[1].pop()
        missing_output[2]["nodes"].pop()
        assert reasons(plan(checkpoint_id, store, geometry,
                            projected(missing_output)))[2] == "TARGET_OUTPUT_MISSING"

        display_shift = frame()
        display_shift[0][1]["rect"]["x"] += 15
        assert reasons(plan(checkpoint_id, store, geometry,
                            projected(display_shift)))[2] == "TARGET_OUTPUT_GEOMETRY_CHANGED"

        workspace_removed = frame()
        workspace_removed[1][1]["name"] = "3"
        workspace_removed[2]["nodes"][1]["nodes"][0]["name"] = "3"
        assert reasons(plan(checkpoint_id, store, geometry,
                            projected(workspace_removed)))[2] == "TARGET_WORKSPACE_MISSING"

        not_running = frame()
        not_running[2]["nodes"][1]["nodes"][0]["floating_nodes"].clear()
        assert reasons(plan(checkpoint_id, store, geometry,
                            projected(not_running)))[2] == "APP_NOT_RUNNING"

        multiple = frame()
        multiple[2]["nodes"][1]["nodes"][0]["floating_nodes"].append(
            leaf(104, "kitty", rect(3500, 40, 350, 450), floating=True))
        assert reasons(plan(checkpoint_id, store, geometry,
                            projected(multiple)))[2] == "AMBIGUOUS_APP_INSTANCES"

        switched = frame()
        switched[2]["nodes"][1]["nodes"][0]["floating_nodes"][0]["floating"] = "auto_off"
        # The Sway floating_nodes branch still makes this floating. Instead
        # change the saved/current fullscreen state to exercise state refusal.
        switched[2]["nodes"][1]["nodes"][0]["floating_nodes"][0]["fullscreen_mode"] = 1
        assert reasons(plan(checkpoint_id, store, geometry,
                            projected(switched)))[2] == "WINDOW_STATE_DIFFERENT"

        forged = copy.deepcopy(geometry)
        forged["session_identity_verified"] = True
        refuses(lambda: plan(checkpoint_id, store, forged, live))
        forged = copy.deepcopy(geometry)
        forged["restore_allowed"] = True
        refuses(lambda: plan(checkpoint_id, store, forged, live))
        forged = copy.deepcopy(geometry)
        forged["geometry"]["windows"][2]["title"] = "PRIVATE LEAK"
        refuses(lambda: plan(checkpoint_id, store, forged, live))
        forged = copy.deepcopy(store)
        forged["document"]["windows"][0]["app_id"] = "changed"
        refuses(lambda: plan(checkpoint_id, forged, geometry, live))
        forged = copy.deepcopy(live)
        forged["windows"][2]["url"] = "https://secret.invalid/token"
        refuses(lambda: plan(checkpoint_id, store, geometry, forged))
        refuses(lambda: plan("NOT-A-UUID", store, geometry, live))
        refuses(lambda: plan(checkpoint_id.upper(), store, geometry, live))
        refuses(lambda: plan(checkpoint_id, store, geometry, None))

        older = legacy.save(old)["checkpoint"]["id"]
        no_live_reads = []
        legacy_only = inspect(
            older, legacy_reader=legacy.load, geometry_reader=load_geometry,
            live_reader=lambda: no_live_reads.append("WRONG"))
        assert no_live_reads == []
        assert legacy_only["status"] == "legacy_only"
        assert legacy_only["counts"]["needs_attention"] == 3
        assert legacy_only["items"] == []
        assert legacy_only["restore_allowed"] is False
        assert legacy.load(checkpoint_id)["document"] == store["document"]
        assert load_geometry(checkpoint_id) == geometry

        # Invalid invocation is denied without consulting any local runtime.
        assert main(["not-review", checkpoint_id]) == 1
finally:
    if old_home is None:
        os.environ.pop("XDG_DATA_HOME", None)
    else:
        os.environ["XDG_DATA_HOME"] = old_home

print("MACHINE V2 read-only geometry review // synthetic and SQLite PASS")
