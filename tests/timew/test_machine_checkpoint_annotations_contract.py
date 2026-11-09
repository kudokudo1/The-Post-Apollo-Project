#!/usr/bin/env python3
"""No accidental activation, storage mutation, or competing geometry owner."""
import ast
from pathlib import Path

root = Path(__file__).resolve().parents[2]
owner = (root / "services/time/MachineCheckpointAnnotations.py").read_text()
cli = (root / "services/time/MachineCheckpointNotesCLI.py").read_text()
qml = (root / "widgets/TimeW.qml").read_text()
legacy = (root / "services/time/MachineCheckpointStore.py").read_text()
geometry = (root / "services/time/MachineGeometryStoreV2.py").read_text()
owner_functions = {n.name for n in ast.parse(owner).body
                   if isinstance(n, ast.FunctionDef)}
assert {"get_annotation", "set_annotation"}.issubset(owner_functions)
assert "BEGIN IMMEDIATE" in owner
assert "ON DELETE CASCADE" in owner
assert "expected_revision" in owner
assert "PRAGMA foreign_keys=ON" in owner
assert "legacy.connect(writable=False)" in owner
assert "legacy.connect(writable=True)" in owner
assert "MachineCheckpointAnnotations" not in qml
assert "MachineCheckpointNotesCLI" not in qml
assert "MachineCheckpointAnnotations" not in legacy
assert "MachineCheckpointAnnotations" not in geometry
assert "SCHEMA_VERSION = 1" in legacy
for forbidden in ("swaymsg", "Popen", "os.system", "shell=True", "gtk-launch",
                  "subprocess.run", "window_move"):
    assert forbidden not in owner, forbidden
assert "if __name__" not in owner
assert "def main(" not in owner
assert "sys.path.insert(0, str(Path(__file__).resolve().parent))" in cli
assert "MAX_INPUT_BYTES = 8192" in cli
assert "def _input(" in cli and "sys.stdin.buffer.readline" in cli
assert "if __name__" in cli
assert "MachineCheckpointNotesCLI" not in qml
print("MACHINE annotations // additive, revision guarded, explicitly called only PASS")
