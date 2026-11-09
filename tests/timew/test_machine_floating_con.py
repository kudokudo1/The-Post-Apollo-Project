#!/usr/bin/env python3
"""Regression for Sway's actual floating_con client leaf. Synthetic only."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "time"))
from MachineSwayRead import normalize
from MachineWindowResolver import _walk_live, resolve
from MachineGeometryV2 import project_geometry, compare_to_v1

BOX = {"x": 0, "y": 0, "width": 1000, "height": 750}
FLOAT_RECT = {"x": 100, "y": 90, "width": 420, "height": 300}
KEY = "99999999-9999-4999-8999-999999999999"
outputs = [{"name": "HEADLESS-1", "active": True, "rect": BOX}]
workspaces = [{"name": "1", "output": "HEADLESS-1"},
              {"name": "2", "output": "HEADLESS-1"}]
float_win = {
    "type": "floating_con", "id": 501, "app_id": "kitty",
    "rect": FLOAT_RECT, "layout": "none", "percent": None,
    "fullscreen_mode": 0, "floating": None,
    "name": "PRIVATE TERMINAL TITLE", "pid": 12345,
    "nodes": [], "floating_nodes": []}
def ws(name, floating_nodes=()):
    return {"type": "workspace", "name": name, "rect": BOX,
            "layout": "splith", "nodes": [],
            "floating_nodes": list(floating_nodes)}
tree = {"type": "root", "nodes": [
    {"type": "output", "name": "HEADLESS-1",
     "nodes": [ws("1", [float_win]), ws("2")]},
]}

captured = normalize(outputs, workspaces, tree)
assert captured["windows"] == [
    {"app_id": "kitty", "workspace": "1", "floating": True}]
observed = _walk_live(tree)
assert len(observed) == 1
assert observed[0]["app_id"] == "kitty"
assert observed[0]["con_id"] == 501
assert observed[0]["workspace"] == "1"
assert observed[0]["floating"] is True

v1 = {
    "schema_version": 1, "kind": "sway-layout-selection-preview",
    "preview_only": True, "captured_at_utc": "2026-11-09T12:00:00+00:00",
    "label": "FLOATING TEST",
    "outputs": [{"connector": "HEADLESS-1", "rect": BOX}],
    "workspaces": workspaces,
    "windows": captured["windows"],
}
# A matching floating target on a different workspace is not lost.
destination = dict(v1, windows=[
    {"app_id": "kitty", "workspace": "2", "floating": True}])
r = resolve(destination, outputs, workspaces, tree)
assert r["counts"]["candidate"] == 1
assert r["candidates"][0]["live_con_id"] == 501
assert r["candidates"][0]["current_workspace"] == "1"
assert r["candidates"][0]["target_workspace"] == "2"

geo = project_geometry(outputs, workspaces, tree, window_keys={501: KEY})
assert len(geo["windows"]) == 1
assert geo["windows"][0]["window_key"] == KEY
assert geo["windows"][0]["rect"] == FLOAT_RECT
assert geo["windows"][0]["floating"] is True
assert compare_to_v1(geo, v1)["v1_window_multiset_matches"] is True
assert "PRIVATE TERMINAL TITLE" not in str(geo)
assert "12345" not in str(geo)
assert "con_id" not in str(geo)
print("MACHINE Sway floating_con // v1 capture + live match + v2 geometry PASS")
