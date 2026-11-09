#!/usr/bin/env python3
"""M2 persistent checkpoint owner stays dormant until capture/UI review."""
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[2]
owner = (root / "services/time/MachineGeometryStoreV2.py").read_text()
legacy = (root / "services/time/MachineCheckpointStore.py").read_text()
qml = (root / "widgets/TimeW.qml").read_text()
tree = ast.parse(owner)
names = [x.name for x in tree.body if isinstance(x, ast.FunctionDef)]
assert {"validate_geometry", "validate_pair", "save_pair", "load_geometry"}.issubset(names)
assert "from MachineGeometryV2 import" in owner
assert "import MachineCheckpointStore as legacy" in owner
assert "with conn:" in owner
assert "CREATE TABLE IF NOT EXISTS" in owner
assert "INSERT INTO checkpoints" in owner
assert "machine_checkpoint_geometry_v2" in owner
assert "PRAGMA foreign_keys=ON" in owner
assert "legacy.connect(writable=False)" in owner
assert "stage_hook(\"after_v1_insert\")" in owner
assert "stage_hook(\"after_geometry_insert\")" in owner
assert "session_identity_verified" in owner
assert "MachineGeometryStoreV2" not in qml
assert "MachineGeometryStoreV2" not in legacy
assert "SCHEMA_VERSION = 1" in legacy
assert "subprocess" not in owner
assert "swaymsg" not in owner
assert "socket" not in owner
assert "os.system(" not in owner
assert "def main(" not in owner
assert "if __name__" not in owner
print("MACHINE M2 store // dormant, additive v1 compatibility source PASS")
