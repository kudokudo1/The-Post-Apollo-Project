#!/usr/bin/env python3
"""Source-only boundary: custom selection must not become a second save path."""
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[2]
scoper = (root / "services/time/MachineCaptureSelectionV2.py").read_text()
coordinator = (root / "services/time/MachineCaptureSaveV2.py").read_text()
legacy = (root / "services/time/MachineCheckpointStore.py").read_text()
qml = (root / "widgets/TimeW.qml").read_text()

functions = {node.name for node in ast.parse(scoper).body
             if isinstance(node, ast.FunctionDef)}
assert "select_geometry" in functions
assert "MachineGeometryStoreV2" in scoper
assert "validate_geometry" in scoper
assert "MachineCaptureSelectionV2 import select_geometry" in coordinator
assert "selection=None" in coordinator
assert "select_geometry(geometry, selection)" in coordinator
assert "return store_adapter(legacy, geometry)" in coordinator
assert "MachineCaptureSelectionV2" not in qml
assert "MachineCaptureSelectionV2" not in legacy
assert "MachineCaptureSaveV2" not in qml
assert "SCHEMA_VERSION = 1" in legacy
for forbidden in ("swaymsg", "subprocess", "sqlite3", "Popen",
                  "os.system", "shell=True", "gtk-launch", "open("):
    assert forbidden not in scoper, forbidden
assert "if __name__" not in scoper
assert "def main(" not in scoper
print("MACHINE M2 selection // pure allowlist and single-save owner PASS")
