#!/usr/bin/env python3
"""Host manifest proposal: exact origin and path, never registered locally."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/time"))
from MachineBraveNativeManifest import generate, HOST_NAME

ID = "a" * 32
PATH = "/opt/postapollo/services/time/MachineBraveNativeProbe.py"
expected = {
    "name": HOST_NAME,
    "description": "Post-Apollo MACHINE one-shot read-only Brave connection probe",
    "path": PATH,
    "type": "stdio",
    "allowed_origins": ["chrome-extension://" + ID + "/"],
}
assert generate(ID, PATH) == expected
assert len(expected["allowed_origins"]) == 1
assert "*" not in json.dumps(expected)

for bad_id in ("", "x" * 32, "a" * 31, "a" * 33, "ABC",
               "a" * 31 + "\n", "../" + ID, 1, None):
    try:
        generate(bad_id, PATH)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid extension origin accepted")

for bad_path in ("relative/MachineBraveNativeProbe.py", "/bin/bash",
                 "MachineBraveNativeProbe.py", "/tmp/fake.json",
                 "/tmp/PRIVATE\nMachineBraveNativeProbe.py", "", 1, None):
    try:
        generate(ID, bad_path)
    except (ValueError, TypeError):
        pass
    else:
        raise AssertionError("invalid host executable path accepted")

with tempfile.TemporaryDirectory(prefix="machine-brave-manifest-test-") as d:
    executable = ROOT / "services/time/MachineBraveNativeManifest.py"
    p = subprocess.run(
        ["python3", "-B", "-I", str(executable), ID, PATH],
        capture_output=True, timeout=6, cwd=d)
    assert p.returncode == 0 and not p.stderr
    assert json.loads(p.stdout) == expected
    assert list(Path(d).iterdir()) == [], "manifest builder installed files"
    bad = subprocess.run(
        ["python3", "-B", "-I", str(executable), "BAD", PATH],
        capture_output=True, timeout=6, cwd=d)
    assert bad.returncode == 2 and not bad.stdout and not bad.stderr
    assert list(Path(d).iterdir()) == []

print("MACHINE Brave // exact per-extension host manifest preview, no install PASS")
