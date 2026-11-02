#!/usr/bin/env python3
"""TASKS M12u: operator-launched disposable real-Quickshell self-report.

No live TASKS data, no default config restart. The only path written by
the QML singleton is inside a fresh private temporary XDG_DATA_HOME.
The launcher terminates only the subprocess it started and independently
reopens the synthetic file before claiming a native PASS.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import stat
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
QML = ROOT / "TaskNativeSelfReportM12u.qml"
SUFFIX = "post-apollo-m12u-fixture"
SOURCE = "apollo-hub-todo-v1.json"
TITLE = "M12U_SYNTHETIC_TASK"
EXPECTED = (
    "INITIAL_EMPTY", "TICKET_DISABLED", "NATIVE_SAVE", "NATIVE_RELOAD"
)
STAGE = re.compile(r"M12U_STAGE\|([A-Z_]+)\|PASS(?:\s|$)")
RESULT = re.compile(r"M12U_RESULT\|(PASS|FAIL)\|([A-Z_]+)(?:\s|$)")


def evidence(lines: list[str], source: Path) -> dict:
    """Pure evaluator. Requires both native markers AND independent file read."""
    stages = []
    results = []
    for line in lines:
        found = STAGE.search(line)
        if found:
            stages.append(found.group(1))
        found = RESULT.search(line)
        if found:
            results.append((found.group(1), found.group(2)))
    if stages != list(EXPECTED):
        return {"status": "FAIL", "reason": "NATIVE_STAGE_SEQUENCE_MISSING"}
    if len(results) != 1 or results[0] != ("PASS", "NATIVE_SEQUENCE"):
        return {"status": "FAIL", "reason": "NATIVE_RESULT_NOT_CONFIRMED"}
    try:
        st = source.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or (
            hasattr(os, "geteuid") and st.st_uid != os.geteuid()
        ):
            return {"status": "FAIL", "reason": "UNSAFE_FIXTURE_SOURCE"}
        if st.st_size < 1 or st.st_size > 1048576:
            return {"status": "FAIL", "reason": "INVALID_FIXTURE_SIZE"}
        raw = source.read_bytes()
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicates)
        if not isinstance(data, dict) or data.get("version") != 3:
            return {"status": "FAIL", "reason": "INVALID_TASKS_VERSION"}
        tasks = data.get("tasks")
        if not isinstance(tasks, list) or len(tasks) != 1:
            return {"status": "FAIL", "reason": "UNEXPECTED_TASK_COUNT"}
        task = tasks[0]
        if not isinstance(task, dict) or task.get("title") != TITLE or (
            task.get("done") is not False
        ):
            return {"status": "FAIL", "reason": "UNEXPECTED_SYNTHETIC_TASK"}
        if data.get("projects") != []:
            return {"status": "FAIL", "reason": "UNEXPECTED_SYNTHETIC_PROJECTS"}
        return {
            "status": "PASS",
            "reason": "NATIVE_AND_DISK_AGREE",
            "version": 3,
            "count": 1,
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    except (OSError, ValueError, UnicodeError, TypeError):
        return {"status": "FAIL", "reason": "FIXTURE_READBACK_UNAVAILABLE"}


def no_duplicates(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("DUPLICATE_JSON_KEY")
        obj[key] = value
    return obj


def collect(proc: subprocess.Popen, seconds: float = 35.0) -> list[str]:
    """Read only the launched child's log until its terminal test marker."""
    lines: list[str] = []
    buffer = b""
    deadline = time.monotonic() + seconds
    with selectors.DefaultSelector() as selector:
        assert proc.stdout is not None
        selector.register(proc.stdout, selectors.EVENT_READ)
        while time.monotonic() < deadline:
            readable = selector.select(timeout=0.25)
            if not readable:
                if proc.poll() is not None:
                    break
                continue
            chunk = os.read(proc.stdout.fileno(), 8192)
            if not chunk:
                break
            buffer += chunk
            if len(buffer) > 131072:
                lines.append("OUTPUT_LIMIT_EXCEEDED")
                break
            while b"\n" in buffer:
                part, buffer = buffer.split(b"\n", 1)
                line = part.decode("utf-8", "replace")
                lines.append(line)
                if RESULT.search(line):
                    return lines
        if buffer:
            lines.append(buffer.decode("utf-8", "replace"))
    return lines


def stop_child(proc: subprocess.Popen):
    """Never pkill or stop the user's existing Quickshell instance."""
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def main() -> int:
    if not QML.is_file():
        print("M12u // FAIL // TEST_CONFIGURATION_MISSING")
        return 1
    qs = shutil.which("qs")
    if qs is None:
        print("M12u // FAIL // QS_EXECUTABLE_MISSING")
        return 1
    # Explicit test-only root and env. The QML itself validates DataDir,
    # exact singleton source path, false production gates and this marker.
    with tempfile.TemporaryDirectory(prefix="post-apollo-m12u-") as temp:
        base = Path(temp)
        data_home = base / "share"
        state_home = base / "state"
        data_home.mkdir(mode=0o700)
        state_home.mkdir(mode=0o700)
        source = data_home / SUFFIX / SOURCE
        if source.exists() or source.is_symlink():
            print("M12u // FAIL // FIXTURE_NOT_FRESH")
            return 1
        env = os.environ.copy()
        env["XDG_DATA_HOME"] = str(data_home)
        env["XDG_STATE_HOME"] = str(state_home)
        env["POST_APOLLO_M12U_DISPOSABLE"] = "1"
        print("M12u // Starting a separate disposable Quickshell test")
        print("M12u // Live shell and live tasks are not targeted")
        try:
            proc = subprocess.Popen(
                [qs, "-p", str(QML)],
                cwd=str(ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
            )
        except OSError:
            print("M12u // FAIL // TEST_PROCESS_NOT_STARTED")
            return 1
        try:
            lines = collect(proc)
        except KeyboardInterrupt:
            print("M12u // FAIL // TEST_INTERRUPTED")
            return 130
        finally:
            stop_child(proc)
        result = evidence(lines, source)
        print("M12u // " + result["status"] + " // " + result["reason"])
        if result["status"] == "PASS":
            print("Native: " + ", ".join(EXPECTED))
            print("Fixture: version=3 tasks=1")
            print("Fixture SHA-256: " + result["sha256"])
            print("Classification: disposable legacy save/reload; no ticket activation")
            return 0
        # No raw task content or local full path in test output. The private
        # test root is discarded on process exit, including on failure.
        print("Native or disk evidence was incomplete; no success assumed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
