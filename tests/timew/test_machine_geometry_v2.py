#!/usr/bin/env python3
"""Synthetic MACHINE geometry-v2 contract: no Sway session or disk access."""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "time"))
from MachineGeometryV2 import (GeometryError, KIND, project_geometry, compare_to_v1)

W1 = "11111111-1111-4111-8111-111111111111"
W2 = "22222222-2222-4222-8222-222222222222"
W3 = "33333333-3333-4333-8333-333333333333"


def rect(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


def window(id_, app, box, *, floating=False):
    return {"type": "con", "id": id_, "app_id": app,
            "rect": box, "window_rect": rect(0, 20, box["width"], box["height"] - 20),
            "deco_rect": rect(0, 0, box["width"], 20),
            "geometry": rect(0, 0, box["width"], box["height"]),
            "fullscreen_mode": 0, "floating": "user_on" if floating else "auto_off",
            "layout": "none", "percent": None,
            "name": "SECRET WINDOW TITLE",
            "pid": 4567, "shell": "top secret", "nodes": [],
            "floating_nodes": []}


def fixture():
    output_list = [
        {"name": "DP-3", "active": True, "rect": rect(0, 0, 2560, 1440),
         "scale": 1.0, "transform": "normal", "serial": "PRIVATE"},
        {"name": "HDMI-A-1", "active": True, "rect": rect(2560, 0, 1360, 768),
         "scale": 1.0, "transform": "normal"},
    ]
    workspace_list = [{"name": "1", "output": "DP-3"},
                      {"name": "2", "output": "HDMI-A-1"}]
    main = {
        "type": "con", "id": 400, "rect": rect(0, 0, 2560, 1440),
        "layout": "splith", "percent": 1.0,
        "nodes": [window(101, "brave-browser", rect(0, 0, 1280, 1440)),
                  window(102, "brave-browser", rect(1280, 0, 1280, 1440))],
        "floating_nodes": [],
    }
    screen1 = {"type": "workspace", "name": "1",
               "rect": rect(0, 0, 2560, 1440), "layout": "splith",
               "nodes": [main], "floating_nodes": []}
    screen2 = {"type": "workspace", "name": "2",
               "rect": rect(2560, 0, 1360, 768), "layout": "splith",
               "nodes": [], "floating_nodes": [
                   window(103, "kitty", rect(2800, 40, 900, 650), floating=True)]}
    tree = {"type": "root", "nodes": [
        {"type": "output", "name": "DP-3", "nodes": [screen1]},
        {"type": "output", "name": "HDMI-A-1", "nodes": [screen2]},
    ]}
    keys = {101: W1, 102: W2, 103: W3}
    return output_list, workspace_list, tree, keys


outputs, workspaces, tree, keys = fixture()
snapshot = project_geometry(outputs, workspaces, tree, window_keys=keys)
assert snapshot["kind"] == KIND
assert snapshot["schema_version"] == 2
assert snapshot["session_identity_verified"] is False
assert snapshot["capture_only"] is True
assert len(snapshot["outputs"]) == 2
assert len(snapshot["workspaces"]) == 2
assert len(snapshot["windows"]) == 3
assert [w["window_key"] for w in snapshot["windows"]] == [W1, W2, W3]
assert snapshot["windows"][0]["rect"] == rect(0, 0, 1280, 1440)
assert snapshot["windows"][1]["rect"] == rect(1280, 0, 1280, 1440)
assert snapshot["windows"][2]["floating"] is True
assert snapshot["windows"][2]["workspace"] == "2"
assert snapshot["workspaces"][0]["children"][0]["layout"] == "splith"
assert len(snapshot["workspaces"][0]["children"][0]["children"]) == 2
assert "percent" in snapshot["workspaces"][0]["children"][0]
serialized = json.dumps(snapshot)
for secret in ("SECRET WINDOW TITLE", "PRIVATE", "pid", "shell", "con_id",
               "101", "102", "103"):
    assert secret not in serialized, secret

v1 = {"schema_version": 1, "kind": "sway-layout-selection-preview",
      "preview_only": True, "captured_at_utc": "2026-11-09T10:00:00+00:00",
      "label": "MACHINE CHECKPOINT",
      "outputs": [{"connector": x["connector"], "rect": x["rect"]}
                  for x in snapshot["outputs"]],
      "workspaces": [{"name": x["name"], "output": x["output"]}
                     for x in snapshot["workspaces"]],
      "windows": [{"app_id": x["app_id"], "workspace": x["workspace"],
                   "floating": x["floating"]} for x in snapshot["windows"]]}
comparison = compare_to_v1(snapshot, v1)
assert comparison == {"v1_window_multiset_matches": True,
                      "exact_session_match": False, "safe_restore_actions": []}
v1["windows"].pop()
assert compare_to_v1(snapshot, v1)["v1_window_multiset_matches"] is False


def refuses(changer):
    output, workspace, root, ids = copy.deepcopy(fixture())
    changer(output, workspace, root, ids)
    try:
        project_geometry(output, workspace, root, window_keys=ids)
    except GeometryError:
        return
    raise AssertionError("unsafe geometry input accepted")


refuses(lambda o, w, t, k: k.update({101: W2}))
refuses(lambda o, w, t, k: k.pop(102))
refuses(lambda o, w, t, k: k.update({999: W2}))
refuses(lambda o, w, t, k: o[0].update({"scale": -1}))
refuses(lambda o, w, t, k: w[0].update({"output": "MISSING"}))
refuses(lambda o, w, t, k: t["nodes"][0]["nodes"][0]
        ["nodes"][0]["nodes"][0]["rect"].update({"width": -40}))
refuses(lambda o, w, t, k: t["nodes"][0]["nodes"][0]
        ["nodes"][0].update({"layout": "UNSUPPORTED"}))
print("MACHINE v2 geometry // precise window + tiling proposal PASS")
