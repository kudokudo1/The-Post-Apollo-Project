#!/usr/bin/env python3
"""Synthetic Sway fixtures only; never mutate the operator's compositor."""
import copy
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import json

root = Path(__file__).resolve().parents[2] / "services" / "time"
sys.path.insert(0, str(root))
spec = importlib.util.spec_from_file_location("machine_resolution", root / "MachineWindowResolver.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

rect = {"x": 0, "y": 0, "width": 1920, "height": 1080}
stored = {
    "schema_version": 1, "kind": "sway-layout-selection-preview",
    "preview_only": True, "label": "Work",
    "captured_at_utc": "2026-10-24T00:00:00+00:00",
    "outputs": [{"connector": "DP-5", "rect": rect}],
    "workspaces": [{"name": "1", "output": "DP-5"},
                   {"name": "2", "output": "DP-5"}],
    "windows": [{"app_id": "kitty", "workspace": "2", "floating": False}]
}
outputs = [{"name": "DP-5", "active": True, "rect": rect}]
workspaces = [{"name": "1", "output": "DP-5"},
              {"name": "2", "output": "DP-5"}]
def tree(*nodes):
    return {"type": "root", "nodes": [
        {"type": "workspace", "name": "1", "nodes": list(nodes),
         "floating_nodes": []}], "floating_nodes": []}
def win(app="kitty", id=51, floating=False, fullscreen=0):
    return {"type": "con", "id": id, "app_id": app,
            "floating": "user_on" if floating else "auto_off",
            "fullscreen_mode": fullscreen, "nodes": [], "floating_nodes": [],
            "name": "PRIVATE DOCUMENT", "pid": 4321}
original = copy.deepcopy(stored)
source = tree(win())
data = m.resolve(stored, outputs, workspaces, source)
assert data["read_only"] and not data["executable"]
assert data["requires_fresh_revalidation"]
assert data["counts"]["candidate"] == 1
assert data["candidates"][0]["live_con_id"] == 51
assert data["candidates"][0]["current_workspace"] == "1"
assert data["candidates"][0]["target_workspace"] == "2"
assert "PRIVATE" not in str(data) and "4321" not in str(data)
assert stored == original

sw = copy.deepcopy(stored)
sw["windows"][0]["workspace"] = "1"
assert m.resolve(sw, outputs, workspaces, source)["counts"]["already"] == 1
assert m.resolve(stored, outputs, workspaces, tree())["candidates"][0]["reason"] == "APP NOT RUNNING"
assert m.resolve(stored, outputs, workspaces, tree(win(id=51), win(id=52)))["counts"]["manual"] == 1
assert m.resolve(stored, outputs, workspaces, tree(win(id=0)))["counts"]["manual"] == 1
assert m.resolve(stored, outputs, workspaces, tree(win(floating=True)))["counts"]["manual"] == 1
assert m.resolve(stored, outputs, workspaces, tree(win(fullscreen=1)))["counts"]["manual"] == 1

bad_output = copy.deepcopy(workspaces)
bad_output[1]["output"] = "OTHER"
assert m.resolve(stored, outputs, bad_output, source)["counts"]["blocked"] == 1
assert m.resolve(stored, [], workspaces, source)["counts"]["blocked"] == 1
assert m.resolve(stored, outputs, workspaces[:1], source)["counts"]["blocked"] == 1
bad = copy.deepcopy(stored)
bad["windows"].append(copy.deepcopy(bad["windows"][0]))
assert m.resolve(bad, outputs, workspaces, source)["counts"]["manual"] == 1

bad = copy.deepcopy(stored)
bad["workspaces"][1]["name"] = "Work space"
bad["windows"][0]["workspace"] = "Work space"
space = copy.deepcopy(workspaces)
space[1]["name"] = "Work space"
assert m.resolve(bad, outputs, space, source)["candidates"][0]["reason"] == "WORKSPACE NAME REQUIRES MANUAL REVIEW"

bad = copy.deepcopy(stored)
bad["windows"][0]["title"] = "secret"
try:
    m.resolve(bad, outputs, workspaces, source)
    raise AssertionError("unsaved private field accepted")
except m.ResolutionError:
    pass

def runner(cmd, **kwargs):
    assert kwargs["shell"] is False and kwargs["timeout"] == 3
    result = {"get_outputs": outputs, "get_workspaces": workspaces, "get_tree": source}
    return SimpleNamespace(stdout=json.dumps(result[cmd[-1]]).encode())
assert m.capture_and_resolve(stored, runner=runner)["counts"]["candidate"] == 1
try:
    m.resolve(stored, outputs, workspaces, {"type": "root", "nodes": "bad"})
    raise AssertionError("invalid live tree allowed")
except m.ResolutionError:
    pass
print("TIMEW MACHINE M1J: EPHEMERAL LIVE RESOLUTION PASS / NO MOVES")
