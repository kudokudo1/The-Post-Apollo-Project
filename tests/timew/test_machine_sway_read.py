#!/usr/bin/env python3
"""Fixture-only Sway adapter tests. No real compositor query."""
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

source = Path(__file__).resolve().parents[2] / "services/time"
sys.path.insert(0, str(source))
spec = importlib.util.spec_from_file_location("MachineSwayRead", source / "MachineSwayRead.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)

outputs = [{"name": "DP-5", "active": True, "rect":
            {"x": 0, "y": 0, "width": 2560, "height": 1440}},
           {"name": "DP-9", "active": False, "rect":
            {"x": 0, "y": 0, "width": 300, "height": 200}}]
workspaces = [{"name": "1", "output": "DP-5"}]
tree = {"type": "root", "nodes": [
    {"type": "workspace", "name": "1", "nodes": [
        {"type": "con", "app_id": "browser", "window": 42,
         "name": "private video title", "pid": 123,
         "nodes": [], "floating_nodes": []}
    ], "floating_nodes": [
        {"type": "con", "app_id": None, "window": 43,
         "window_properties": {"class": "terminal", "title": "private"},
         "nodes": [], "floating_nodes": []}
    ]}
]}
expected = ["get_outputs", "get_workspaces", "get_tree"]
seen = []
def runner(command, **kwargs):
    assert command == ["swaymsg", "-r", "-t", expected[len(seen)]]
    assert kwargs["shell"] is False and kwargs["timeout"] == 3
    seen.append(command)
    return SimpleNamespace(stdout=json.dumps([outputs, workspaces, tree][len(seen)-1]).encode())

preview = adapter.capture_preview(runner=runner, excluded_apps=["terminal"])
assert len(seen) == 3
assert len(preview["outputs"]) == 1
assert preview["windows"] == [{"app_id": "browser", "workspace": "1", "floating": False}]
assert preview["excluded_counts"]["windows"] == 1
assert preview["preview_only"]
for secret in ("private", "pid", "42", "43", "title"):
    assert secret not in str(preview), secret

for broken in ({"type": "root", "nodes": "invalid"},
               {"type": "root", "nodes": [{"type": "con", "nodes": []}],
                "floating_nodes": "invalid"}):
    try:
        adapter.normalize(outputs, workspaces, broken)
        raise AssertionError("invalid tree accepted")
    except adapter.PreviewError:
        pass

def huge(_command, **_kwargs):
    return SimpleNamespace(stdout=b"x" * (adapter.MAX_IPC_BYTES + 1))
try:
    adapter.capture_preview(runner=huge)
    raise AssertionError("unbounded response accepted")
except adapter.PreviewError:
    pass

assert "subprocess.Popen" not in (source / "MachineSwayRead.py").read_text()
print("TIMEW SWAY READ ADAPTER: FIXTURE PASS / NO LIVE IPC")
