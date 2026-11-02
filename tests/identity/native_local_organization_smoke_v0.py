#!/usr/bin/env python3
"""Two fresh real qs processes, fake company data, private temporary XDG roots."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
QML = ROOT / "LocalOrganizationNativeSmokeV0.qml"
SCHEMA = "post-apollo.social-local-organizations.v1"


def inspect(document: dict) -> None:
    assert document["schema"] == SCHEMA
    assert document["revision"] == 9
    assert document["nextId"] == 4
    assert document["organizations"] == [
        {"id": "org-1", "name": "SYNTHETIC LLC RENAMED", "kind": "llc",
         "archived": False, "branches": [
             {"id": "branch-3", "name": "SYNTHETIC PROGRAM", "archived": False}
         ]},
        {"id": "org-2", "name": "SYNTHETIC NONPROFIT", "kind": "nonprofit",
         "archived": False, "branches": []},
    ]


def run() -> None:
    qs = shutil.which("qs")
    if qs is None or not QML.is_file():
        raise RuntimeError("Disposable Quickshell binary/root unavailable")
    with tempfile.TemporaryDirectory(prefix="local-org-native-smoke-") as tmp:
        base = Path(tmp)
        env = os.environ.copy()
        for key, name in (("HOME", "home"), ("XDG_RUNTIME_DIR", "runtime"),
                          ("XDG_CONFIG_HOME", "config"), ("XDG_STATE_HOME", "state"),
                          ("XDG_CACHE_HOME", "cache"), ("XDG_DATA_HOME", "data")):
            p = base / name
            p.mkdir(mode=0o700)
            env[key] = str(p)
        env.update({
            "QT_QPA_PLATFORM": "offscreen",
            "QT_QUICK_BACKEND": "software",
            "LIBGL_ALWAYS_SOFTWARE": "1",
            "WAYLAND_DISPLAY": "",
            "DISPLAY": "",
            "QT_LOGGING_RULES": "qt.qpa.*=false",
            "QS_DISABLE_FILE_WATCHER": "1",
            "POST_APOLLO_LOCAL_ORG_SMOKE": "CI_DISPOSABLE_ONLY",
        })
        folder = base / "data" / "post-apollo" / "social"
        filepath = folder / "local-organizations-v1.json"
        assert not filepath.exists()
        saved = None
        for phase in ("create", "reload"):
            env["POST_APOLLO_LOCAL_ORG_PHASE"] = phase
            result = subprocess.run(
                [qs, "-p", str(QML), "--no-color"],
                cwd=str(ROOT), env=env, check=False, timeout=25,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, errors="replace",
            )
            output = result.stdout or ""
            marker = "LOCAL_ORG_NATIVE_PASS_" + phase.upper()
            if result.returncode != 0 or marker not in output or "LOCAL_ORG_NATIVE_FAIL|" in output:
                relevant = [line for line in output.splitlines()
                            if any(s in line for s in
                                   ("ERROR", "Error:", "Failed", "WARN", "LOCAL_ORG_NATIVE_FAIL"))]
                raise AssertionError(
                    f"Native local directory {phase} failed: exit={result.returncode}, "
                    f"marker={marker}, diagnostics={relevant[-6:]}"
                )
            assert filepath.is_file(), "No persisted organization directory"
            assert stat.S_IMODE(folder.stat().st_mode) == 0o700
            assert stat.S_IMODE(filepath.stat().st_mode) == 0o600
            data = filepath.read_bytes()
            assert len(data) <= 65536
            inspect(json.loads(data))
            assert b"scopeGrants" not in data and b"accessToken" not in data
            if saved is None:
                saved = data
            else:
                assert data == saved, "Second Quickshell process modified data on read"
            print(f"PASS / real Quickshell {phase} / private synthetic organizations")


if __name__ == "__main__":
    run()
