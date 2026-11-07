#!/usr/bin/env python3
"""M15a real Quickshell/Process native smoke, disposable GitHub CI only.

An Xvfb display runs the actual TaskLocalSourceInspectPaneM15a component.
Five private fake JSON states are checked; neither OS user files nor a live
Quickshell session are touched. Never run with local desktop credentials.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
QML = ROOT / "TaskLocalSourceNativeSmokeM15a.qml"
SCENARIOS = ("valid", "missing", "malformed", "permissions", "symlink")


def run(scenario: str):
    if (os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("POST_APOLLO_M15A_DISPOSABLE_CI") != "1"):
        raise RuntimeError("M15A_REFUSES_NON_CI_NATIVE_EXECUTION")
    if scenario not in SCENARIOS or not QML.is_file():
        raise RuntimeError("M15A_INVALID_TEST_SCENARIO")
    executable = shutil.which("qs")
    if executable is None:
        raise RuntimeError("M15A_NO_REAL_QUICKSHELL_BINARY")
    with tempfile.TemporaryDirectory(prefix="m15a-qs-private-") as temporary:
        base = Path(temporary)
        env = os.environ.copy()
        for key, child in (
            ("HOME", "home"),
            ("XDG_CONFIG_HOME", "config"),
            ("XDG_DATA_HOME", "data"),
            ("XDG_STATE_HOME", "state"),
            ("XDG_CACHE_HOME", "cache"),
            ("XDG_RUNTIME_DIR", "runtime"),
        ):
            directory = base / child
            directory.mkdir(mode=0o700)
            env[key] = str(directory)
        folder = base / "data" / "tasks-source"
        folder.mkdir(mode=0o700)
        source = folder / "apollo-hub-todo-v1.json"
        if scenario in ("valid", "permissions", "symlink"):
            payload = (json.dumps({
                "version": 3, "nextId": 2, "nextProjectId": 1,
                "projects": [], "tasks": [{
                    "id": "t1", "title": "SYNTHETIC_M15A_PRIVATE_TITLE",
                    "done": False, "createdAtMs": 1700000000000,
                    "updatedAtMs": 1700000000000, "priority": "none",
                    "description": "SYNTHETIC_PRIVATE_DESCRIPTION",
                    "dueDate": None, "projectId": None
                }]
            }, separators=(",", ":")) + "\n").encode()
        elif scenario == "malformed":
            payload = b"{ invalid JSON"
        else:
            payload = None
        if payload is not None:
            if scenario == "symlink":
                target = folder / "fixture-safe-data.json"
                target.write_bytes(payload)
                target.chmod(0o600)
                source.symlink_to(target)
            else:
                source.write_bytes(payload)
                source.chmod(0o644 if scenario == "permissions" else 0o600)
        before = (source.read_bytes()
                  if source.exists() and not source.is_symlink() else None)
        before_listing = sorted(x.name for x in folder.iterdir())
        env.update({
            "POST_APOLLO_TASKS_M15A_NATIVE": "CI_DISPOSABLE_ONLY",
            "POST_APOLLO_TASKS_M15A_SCENARIO": scenario,
            "POST_APOLLO_TASKS_M15A_SOURCE": str(source),
            "QT_QPA_PLATFORM": "xcb",
            "QT_QUICK_BACKEND": "software",
            "LIBGL_ALWAYS_SOFTWARE": "1",
            "QS_DISABLE_FILE_WATCHER": "1",
            "WAYLAND_DISPLAY": "",
            "QT_LOGGING_RULES": "qt.qpa.*=false"
        })
        child = subprocess.run(
            [executable, "-p", str(QML), "--no-color"],
            cwd=str(ROOT), env=env, timeout=24, check=False,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, errors="replace"
        )
        output = child.stdout or ""
        marker = "M15A_NATIVE_PASS_" + scenario.upper()
        if (child.returncode != 0 or marker not in output
                or "M15A_NATIVE_TIMEOUT" in output
                or "M15A_NATIVE_BAD" in output
                or "M15A_NATIVE_START_REFUSED" in output
                or "M15A_NATIVE_NOT_ARMED" in output):
            # No process logs or task-source bytes are printed on failure.
            raise AssertionError(
                "M15A_NATIVE_UI_FAILED scenario="+scenario+
                " return="+str(child.returncode)+
                " markerSeen="+str(marker in output)
            )
        after = (source.read_bytes()
                 if source.exists() and not source.is_symlink() else None)
        if after != before or sorted(x.name for x in folder.iterdir()) != before_listing:
            raise AssertionError("M15A_NATIVE_INSPECTOR_CHANGED_SOURCE")
        print(marker)
        print("M15A_NATIVE_PRIVATE_SOURCE_UNCHANGED")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=SCENARIOS, required=True)
    args = parser.parse_args()
    run(args.scenario)


if __name__ == "__main__":
    main()
