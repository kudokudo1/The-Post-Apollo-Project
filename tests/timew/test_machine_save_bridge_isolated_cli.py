#!/usr/bin/env python3
"""Actual -I launcher smoke test: no compositor or checkpoint writes."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / "services" / "time" / "MachineSaveBridgeV2.py"
with tempfile.TemporaryDirectory(prefix="machine-bridge-isolated-") as tmp:
    env = dict(os.environ)
    for item in ("SWAYSOCK", "I3SOCK", "WAYLAND_DISPLAY"):
        env.pop(item, None)
    env["XDG_DATA_HOME"] = tmp
    result = subprocess.run(
        ["python3", "-B", "-I", str(BRIDGE), "invalid"],
        env=env, stdin=subprocess.DEVNULL,
        capture_output=True, timeout=8)
    assert result.returncode == 1, "unexpected launcher exit status"
    # It must enter main(), rather than fail on a sibling ModuleNotFoundError.
    answer = json.loads(result.stdout)
    assert answer == {"status": "error", "reason": "INVALID ACTION"}
    assert not (Path(tmp) / "post-apollo" / "machine" / "machine.db").exists()

print("MACHINE SAVE BRIDGE // REAL ISOLATED PYTHON IMPORT PASS")
