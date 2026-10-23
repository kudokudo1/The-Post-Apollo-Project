#!/usr/bin/env python3
"""Pure-fixture tests: no compositor, files, or user data accessed."""
import importlib.util
from pathlib import Path

path = Path(__file__).resolve().parents[2] / "services/time/MachineCheckpointModel.py"
spec = importlib.util.spec_from_file_location("machine_model", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

sample = {
    "outputs": [{"name": "DP-5", "rect": {"x": 0, "y": 0, "width": 2560, "height": 1440}}],
    "workspaces": [{"name": "1", "output": "DP-5"}],
    "windows": [
        {"app_id": "browser", "workspace": "1", "floating": False,
         "name": "SECRET PAGE", "pid": 99, "command": "private", "url": "https://secret"},
        {"app_id": "terminal", "workspace": "1", "floating": True},
    ],
    "clipboard": "secret"
}
p = mod.project(sample, excluded_apps=["terminal"], captured_at="2026-10-23T10:00:00+00:00")
assert p["preview_only"] and p["schema_version"] == 1
assert len(p["windows"]) == 1 and p["excluded_counts"] == {"windows": 1}
assert p["windows"][0] == {"app_id": "browser", "workspace": "1", "floating": False}
assert all(term not in str(p) for term in ("SECRET", "private", "https://secret", "clipboard", "pid"))
assert p["outputs"][0]["rect"]["width"] == 2560
for bad in (
    {"outputs": [], "workspaces": [], "windows": [{"app_id": "a"}]},
    {"outputs": [], "workspaces": [], "windows": [{"app_id": "a", "workspace": "1\nsecret"}]},
    {"outputs": [{}], "workspaces": [], "windows": []},
    {"outputs": [], "workspaces": [], "windows": [{}]},
    {"outputs": [], "workspaces": [], "windows": [], "invalid": object()},
):
    try:
        result = mod.project(bad)
        assert bad.get("invalid") is not None, "expected invalid metadata to fail"
        assert result["preview_only"], "unexpected result"
    except mod.PreviewError:
        pass
assert mod.project({"outputs": [], "workspaces": [], "windows": []})["preview_only"]
try:
    mod.project({"outputs": [], "workspaces": [], "windows": [{}] * 513})
    raise AssertionError("oversized window list accepted")
except mod.PreviewError:
    pass
assert "subprocess" not in path.read_text()
assert "swaymsg" not in path.read_text()
assert "open(" not in path.read_text()
print("TIMEW MACHINE CHECKPOINT MODEL: FIXTURE PASS / NO LIVE CAPTURE")
