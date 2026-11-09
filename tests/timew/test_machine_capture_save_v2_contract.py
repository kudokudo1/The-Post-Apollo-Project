#!/usr/bin/env python3
"""MACHINE v2 capture stays callable-only, not auto-running in production."""
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[2]
capture = (root / "services/time/MachineCaptureSaveV2.py").read_text()
qml = (root / "widgets/TimeW.qml").read_text()
legacy = (root / "services/time/MachineCheckpointStore.py").read_text()
mod = ast.parse(capture)
functions = [n.name for n in mod.body if isinstance(n, ast.FunctionDef)]
assert "capture_and_save" in functions
assert "_window_keys" in functions
assert "_frame" in functions
assert "def main(" not in capture
assert "if __name__" not in capture
assert '("get_outputs", "get_workspaces", "get_tree")' in capture
assert "save_pair" in capture
assert "capture_only" not in qml
assert "MachineCaptureSaveV2" not in qml
assert "MachineCaptureSaveV2" not in legacy
assert "SCHEMA_VERSION = 1" in legacy
assert "shell=True" not in capture
assert "Popen" not in capture
assert "swaymsg\", \"-r\", \"-t" in capture
assert "move container" not in capture
assert "gtk-launch" not in capture
assert "subprocess.run" in capture
assert "DESKTOP CHANGED WHILE SAVING" in capture
assert "geometry != again" in capture or "again != geometry" in capture
print("MACHINE M2 capture // explicitly invoked only, read-only Sway IPC, atomic store owner PASS")
