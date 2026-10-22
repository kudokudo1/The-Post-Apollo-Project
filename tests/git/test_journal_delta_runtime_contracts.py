#!/usr/bin/env python3
"""Run extracted *service* logic using disposable FileView doubles.

This exercises journal begin/complete/load/replay without touching the user's
files. It does NOT certify the Qt FileView runtime or disk-level fsync.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
test = ROOT / "tests/git/fixtures/journal_delta_service_runtime.cjs"
result = subprocess.run(
    ["node", str(test)],
    cwd=ROOT, text=True, capture_output=True, timeout=45, check=False,
)
assert result.returncode == 0, result.stdout + "\n" + result.stderr
print(result.stdout.strip())
