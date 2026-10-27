#!/usr/bin/env python3
"""M11s opt-in four-case private fixture preparation and read-only audit.

Never imports, enumerates, cleans or changes real TASKS or existing test
folders. The caller must explicitly supply an owned, private parent.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import tempfile

HERE = Path(__file__).resolve().parent
CASES = {
    "AFTER_RESERVE": "after-reserve",
    "AFTER_SAVED": "after-saved",
    "AFTER_READBACK": "after-readback",
    "AFTER_SETTLEMENT": "after-settlement"
}


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


seeder = load(HERE / "TaskJsonGateSeedM11m.py", "m11s_seed")
inspector = load(HERE / "TaskNativeFaultInspectorM11r.py", "m11s_inspector")


def private_directory(folder: Path, *, expected_name=None):
    if not folder.is_absolute() or folder.is_symlink():
        raise ValueError("PRIVATE_ABSOLUTE_DIRECTORY_REQUIRED")
    m = folder.lstat()
    if (not stat.S_ISDIR(m.st_mode) or m.st_uid != os.geteuid()
            or stat.S_IMODE(m.st_mode) & 0o077):
        raise ValueError("PRIVATE_DIRECTORY_REQUIRED")
    if expected_name is not None and folder.name != expected_name:
        raise ValueError("UNEXPECTED_SUITE_DIRECTORY")
    return folder


def prepare(parent: Path):
    private_directory(parent)
    # mkdtemp creates a new, unpredictable 0700 folder, never overwrites
    # a prior suite and never assumes the user's Quickshell checkout.
    suite = Path(tempfile.mkdtemp(prefix="m11s-native-", dir=str(parent)))
    private_directory(suite)
    files = {}
    for fault, label in CASES.items():
        case = suite / label
        case.mkdir(mode=0o700)
        files[fault] = str(seeder.seed(case))
    # Human-only setup output includes absolute disposable paths for UI entry.
    # The inspection output intentionally does not.
    return {"suite": str(suite), "syntheticOnly": True,
            "fixtures": files, "runMode": "MANUAL_QUICKSHELL_ONLY"}


def verify_suite(suite: Path, *, reopened=False):
    if not re.fullmatch(r"m11s-native-[A-Za-z0-9_]+", suite.name):
        raise ValueError("NOT_M11S_SUITE")
    private_directory(suite)
    result = []
    for fault, label in CASES.items():
        case = suite / label
        private_directory(case, expected_name=label)
        source = case / "m11l-tasks-copy" / "todo-copy.json"
        test_dir = case / "m11l-tasks-copy"
        private_directory(test_dir, expected_name="m11l-tasks-copy")
        if (not (test_dir / "gate-review.db").exists()):
            # Preparation alone is never called "passed".
            result.append({"fault":fault,"status":"NOT_RUN"})
            continue
        try:
            item = inspector.inspect(source,fault,reopened=reopened)
            result.append({
                "fault": fault,
                "status": "PASS" if item["expectationMet"] else "FAIL",
                "phase": item["phase"],
                "pending": item["pending"],
                "stageState": item["stageState"],
                "counter": item["counter"],
                "sourceHashMatchesJournal": item["sourceHashMatchesJournal"],
                "backupVerified": item["initialBackupVerified"]
            })
        except (OSError, ValueError, KeyError, TypeError, IndexError,
                inspector.gate.GateError, inspector.sqlite3.Error):
            result.append({"fault":fault,"status":"REFUSED"})
    return {"milestone":"M11s","scope":"SYNTHETIC_COPY_ONLY",
            "inspection":"AFTER_EXISTING" if reopened else "AFTER_FAULT",
            "cases":result,
            "complete":all(x["status"] == "PASS" for x in result),
            "nativeCallbacksObservedByThisTool":False,
            "productionWriterAuthorized":False}


def main(argv=None):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="operation",required=True)
    a = sub.add_parser("prepare",help="explicitly create 4 fresh private copies")
    a.add_argument("--private-parent",required=True,type=Path)
    b = sub.add_parser("inspect",help="read-only result for all 4 cases")
    b.add_argument("--suite-dir",required=True,type=Path)
    b.add_argument("--after-existing",action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.operation == "prepare":
            payload = prepare(args.private_parent)
            code = 0
        else:
            payload = verify_suite(args.suite_dir,reopened=args.after_existing)
            code = 0 if payload["complete"] else 1
        print(json.dumps(payload,indent=2,sort_keys=True))
        return code
    except (OSError,ValueError,TypeError):
        print("M11S_OPERATION_REFUSED")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
