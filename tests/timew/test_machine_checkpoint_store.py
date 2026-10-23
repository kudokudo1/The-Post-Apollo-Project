#!/usr/bin/env python3
"""M1g checks the *real SQLite backend* only inside an isolated temp directory."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
script = root / "services/time/MachineCheckpointStore.py"
spec = importlib.util.spec_from_file_location("machine_store", script)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

preview = {
    "schema_version": 1, "kind": "sway-layout-selection-preview",
    "preview_only": True, "captured_at_utc": "2026-10-23T21:02:00+00:00",
    "label": "  Work + gaming  ",
    "outputs": [{"connector": "DP-5", "rect": {
        "x": 0, "y": 0, "width": 2560, "height": 1440}}],
    "workspaces": [{"name": "1", "output": "DP-5"}],
    "windows": [
        {"app_id": "brave", "workspace": "1", "floating": False},
        {"app_id": "brave", "workspace": "1", "floating": False},
        {"app_id": "kitty", "workspace": "1", "floating": True}
    ]
}
assert m.validate(preview)["label"] == "Work + gaming"
assert len(m.validate(preview)["windows"]) == 3
for field, extra in (
    ("title", "private window title"),
    ("clipboard", "private copied text"),
    ("browser_url", "https://example.com/private"),
    ("command", "secret shell")
):
    bad = copy.deepcopy(preview)
    bad["windows"][0][field] = extra
    try:
        m.validate(bad)
        raise AssertionError("private field permitted: " + field)
    except m.StoreError:
        pass
for changes in (
    {"outputs": []},
    {"workspaces": []},
    {"preview_only": False},
    {"kind": "sway-layout-metadata-preview"},
    {"schema_version": 2},
    {"label": "a" * 49}
):
    bad = dict(preview, **changes)
    if changes == {"workspaces": []}:
        pass
    try:
        m.validate(bad)
        raise AssertionError("bad checkpoint permitted")
    except m.StoreError:
        pass
for kind, index, key, new in (
    ("outputs", 0, "connector", "DP-OTHER"),
    ("workspaces", 0, "output", "DP-OTHER"),
    ("windows", 0, "workspace", "missing"),
    ("windows", 0, "floating", 1),
):
    bad = copy.deepcopy(preview)
    bad[kind][index][key] = new
    if kind == "outputs":
        # Now its dependent workspace is orphaned.
        pass
    try:
        m.validate(bad)
        raise AssertionError("dependency mismatch allowed")
    except m.StoreError:
        pass

old_xdg = os.environ.get("XDG_DATA_HOME")
with tempfile.TemporaryDirectory() as tmp:
    os.environ["XDG_DATA_HOME"] = tmp
    home = Path(tmp) / "post-apollo" / "machine"
    path = home / "machine.db"
    assert m.listing() == {"status": "listed", "checkpoints": []}
    assert not home.exists(), "read-only list unexpectedly created storage"
    result = m.save(preview)
    assert result["status"] == "saved"
    saved = result["checkpoint"]
    assert saved["label"] == "Work + gaming"
    assert saved["counts"] == {"outputs": 1, "workspaces": 1, "windows": 3}
    assert path.is_file()
    assert stat.S_IMODE(home.stat().st_mode) == 0o700
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert m.listing()["checkpoints"][0]["id"] == saved["id"]
    loaded = m.load(saved["id"])
    assert loaded["read_only"] is True
    assert loaded["document"]["label"] == "Work + gaming"
    assert loaded["document"]["windows"][0]["app_id"] == "brave"
    assert m.save(dict(preview, label="Gaming"))["checkpoint"]["id"] != saved["id"]
    assert len(m.listing()["checkpoints"]) == 2
    try:
        m.load("not-a-uuid")
        raise AssertionError("invalid ID accepted")
    except m.StoreError:
        pass
    # Process stdin is the only payload transport; not argv or shared files.
    env = dict(os.environ)
    cmd = [sys.executable, "-B", "-I", str(script), "save"]
    completed = subprocess.run(cmd, input=(json.dumps(preview)+"\n").encode(),
                               env=env, capture_output=True, timeout=10)
    assert completed.returncode == 0, completed.stdout
    response = json.loads(completed.stdout)
    assert response["status"] == "saved"
    assert len(m.listing()["checkpoints"]) == 3
    listed = subprocess.run([sys.executable, "-B", "-I", str(script), "list"],
                            env=env, capture_output=True, timeout=10)
    assert listed.returncode == 0
    assert len(json.loads(listed.stdout)["checkpoints"]) == 3
    another = subprocess.run([sys.executable, "-B", "-I", str(script), "load", saved["id"]],
                             env=env, capture_output=True, timeout=10)
    assert json.loads(another.stdout)["document"]["label"] == "Work + gaming"
    # One bad mutation must not create a new checkpoint.
    prior = len(m.listing()["checkpoints"])
    bad = copy.deepcopy(preview)
    bad["windows"][0]["title"] = "private"
    rejected = subprocess.run(cmd, input=(json.dumps(bad)+"\n").encode(), env=env,
                              capture_output=True, timeout=10)
    assert rejected.returncode != 0
    assert json.loads(rejected.stdout)["status"] == "error"
    assert b"private" not in rejected.stdout
    assert len(m.listing()["checkpoints"]) == prior
    os.chmod(path, 0o644)
    try:
        m.listing()
        raise AssertionError("insecure database permissions permitted")
    except m.StoreError:
        pass
    os.chmod(path, 0o600)
    os.chmod(home, 0o755)
    try:
        m.save(preview)
        raise AssertionError("insecure storage folder permitted")
    except m.StoreError:
        pass
if old_xdg is None:
    os.environ.pop("XDG_DATA_HOME", None)
else:
    os.environ["XDG_DATA_HOME"] = old_xdg
print("TIMEW MACHINE SQLITE: PASS / PRIVATE STORAGE / ROUNDTRIP / NO RESTORE")
