#!/usr/bin/env python3
"""TASKS M14c: run REAL Quickshell 0.3.2 against only disposable M12h data.

No desktop session, live TASKS, real usernames, credentials, network, user
home, app configuration, production process or source-writer modification.
The CI gate is a safety preflight, not an OS security boundary.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[2]
QML = ROOT / "TaskPostCrashNativeSmokeM14c.qml"
M12H = ROOT / "tests/tasks/fixtures/TaskStageSourceReceiptM12h.py"
SCENARIOS = ("baseline", "expected", "settled", "unsafe", "missing", "locked")


def m12h_module():
    spec = importlib.util.spec_from_file_location("m14c_m12h_fixture", M12H)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def snapshot(db: Path):
    """Compare actual application journal records before and after native read."""
    uri = "file:" + str(db) + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as con:
        con.execute("PRAGMA query_only=ON")
        return (
            tuple(con.execute("SELECT * FROM authority ORDER BY id").fetchall()),
            tuple(con.execute(
                "SELECT * FROM stage_receipts_m12h ORDER BY rowid").fetchall()),
        )


def create_fixture(folder: Path, scenario: str):
    folder.mkdir(mode=0o700)
    source = folder / "fixture-only.json"
    data = (json.dumps({
        "fixture": "M11E_SYNTHETIC_ONLY", "revision": 0,
        "counter": 0, "marker": "sample"
    }, separators=(",", ":")) + "\n").encode()
    fd = os.open(source, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    db = folder / "handoff-test.db"
    module = m12h_module()
    owner = module.DisposableStageReceipt(
        db, "m14c-real-native-synthetic-owner", bootstrap=True)
    try:
        stage = owner.reserve("m14c-native-test-stage-000001")
        if scenario in ("expected", "settled"):
            temp = folder / (".m14c-atomic-" + uuid.uuid4().hex)
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as output:
                output.write(stage["payload"])
                output.flush()
                os.fsync(output.fileno())
            os.replace(temp, source)
            directory = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)
            os.fsync(directory)
            os.close(directory)
        if scenario == "settled":
            done = owner.settle_after_independent_readback(
                stage["stageId"], stage["epoch"])
            assert done["settled"], "DISPOSABLE_TEST_SETTLEMENT_FAILED"
        if scenario == "unsafe":
            other = folder / "unrelated-synthetic.json"
            with other.open("xb") as output:
                output.write(data)
            other.chmod(0o600)
            source.unlink()
            source.symlink_to(other)
        if scenario == "missing":
            source.unlink()
        if scenario != "locked":
            owner.close()
            owner = None
        return db, source, owner
    except BaseException:
        owner.close()
        raise


def assert_disposable(db: Path, base: Path):
    assert db.is_absolute() and base == db.parent.parent
    assert db.name == "handoff-test.db"
    assert db.parent.name == "m11e-fileview-test"
    assert stat.S_IMODE(db.parent.stat().st_mode) == 0o700
    assert db.parent.stat().st_uid == os.geteuid()
    assert db.parent.parent.name.startswith("m14c-real-qs-")


def run(scenario: str):
    if (os.environ.get("GITHUB_ACTIONS") != "true" or
            os.environ.get("POST_APOLLO_M14C_DISPOSABLE_CI") != "1"):
        raise RuntimeError("M14C_REFUSES_NON_CI_NATIVE_LAUNCH")
    if scenario not in SCENARIOS:
        raise ValueError("REFUSED_UNRECOGNIZED_SCENARIO")
    qs = shutil.which("qs")
    if qs is None or not QML.is_file():
        raise RuntimeError("M14C_REAL_QUICKSHELL_UNAVAILABLE")
    with tempfile.TemporaryDirectory(prefix="m14c-real-qs-") as temporary:
        base = Path(temporary)
        db, source, owner = create_fixture(base / "m11e-fileview-test", scenario)
        try:
            assert_disposable(db, base)
            before_journal = snapshot(db)
            before_source = source.read_bytes() if source.exists() and not source.is_symlink() else None
            before_lstat = source.lstat() if source.is_symlink() else None
            env = os.environ.copy()
            for key, sub in (
                ("HOME", "home"),
                ("XDG_CONFIG_HOME", "config"),
                ("XDG_DATA_HOME", "data"),
                ("XDG_STATE_HOME", "state"),
                ("XDG_CACHE_HOME", "cache"),
                ("XDG_RUNTIME_DIR", "runtime"),
            ):
                target = base / sub
                target.mkdir(mode=0o700)
                env[key] = str(target)
            env.update({
                "QT_QPA_PLATFORM": "offscreen",
                "QT_QUICK_BACKEND": "software",
                "LIBGL_ALWAYS_SOFTWARE": "1",
                "QS_DISABLE_FILE_WATCHER": "1",
                "WAYLAND_DISPLAY": "",
                "DISPLAY": "",
                "QT_LOGGING_RULES": "qt.qpa.*=false",
                "POST_APOLLO_TASKS_M14C_NATIVE": "CI_DISPOSABLE_ONLY",
                "POST_APOLLO_TASKS_M14C_SCENARIO": scenario,
                "POST_APOLLO_TASKS_M14C_FIXTURE": str(db),
            })
            proc = subprocess.run(
                [qs, "-p", str(QML), "--no-color"],
                cwd=str(ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                timeout=28,
                check=False,
            )
            output = proc.stdout or ""
            expected = "M14C_NATIVE_PASS_" + scenario.upper()
            if (proc.returncode != 0 or expected not in output
                    or "M14C_NATIVE_TIMEOUT" in output
                    or "M14C_NATIVE_REFUSED" in output
                    or "M14C_NATIVE_NOT_ARMED" in output):
                diagnostics = [
                    line for line in output.splitlines()
                    if ("Error:" in line or "ERROR" in line
                        or "WARN" in line or "Failed" in line
                        or "file:" in line)
                ]
                # No raw process log, fixture path, usernames or JSON contents.
                raise AssertionError(
                    "M14C_REAL_QUICKSHELL_FAILED "
                    + f"scenario={scenario} return={proc.returncode} "
                    + f"marker={expected} diagnostic_count={len(diagnostics)}"
                )
            if snapshot(db) != before_journal:
                raise AssertionError("M14C_APPLICATION_JOURNAL_CHANGED")
            after_source = source.read_bytes() if source.exists() and not source.is_symlink() else None
            if after_source != before_source:
                raise AssertionError("M14C_SOURCE_WAS_MODIFIED_BY_INSPECTION")
            if before_lstat is not None:
                after_link = source.lstat()
                if not source.is_symlink() or after_link.st_ino != before_lstat.st_ino:
                    raise AssertionError("M14C_UNSAFE_SYMLINK_WAS_CHANGED")
            print("M14C_NATIVE_PASS_" + scenario.upper())
            print("M14C_REAL_QUICKSHELL_SOURCE_AND_JOURNAL_READ_ONLY")
        finally:
            if owner is not None:
                owner.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=SCENARIOS, required=True)
    args = parser.parse_args()
    run(args.scenario)


if __name__ == "__main__":
    main()
