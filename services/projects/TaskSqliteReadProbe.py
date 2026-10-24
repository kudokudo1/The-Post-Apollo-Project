#!/usr/bin/env python3
"""M10k read-only, explicit-path SQLite diagnostic probe for an unmounted UI.

NEVER creates/initializes a TASKS database or mutates task content.
This helper accepts no save/update/migrate/sync commands and emits only
bounded metadata; the actual document and its task titles never leave here.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys


def load_adapter():
    file = Path(__file__).resolve().with_name("ExperimentalTaskSqliteStore.py")
    spec = importlib.util.spec_from_file_location("m10k_task_storage", file)
    if spec is None or spec.loader is None:
        raise RuntimeError("ADAPTER_NOT_FOUND")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def report(path):
    if not path.is_absolute() or path.name != "tasks.db":
        return {"status": "ERROR", "reason": "EXPLICIT_ABSOLUTE_TASKS_DB_REQUIRED",
                "available": False, "writeReady": False, "remoteWriteAuthorized": False}
    adapter = load_adapter()
    try:
        result = adapter.read(path)
        if result["status"] == "ABSENT":
            return {"status": "ABSENT", "available": False,
                    "writeReady": False, "remoteWriteAuthorized": False}
        if result["status"] == "EMPTY":
            return {"status": "EMPTY", "available": False,
                    "writeReady": False, "remoteWriteAuthorized": False}
        doc = result["document"]
        return {"status": result["status"], "available": True,
                "revision": result["revision"], "projects": len(doc["projects"]),
                "tasks": len(doc["tasks"]), "operations": len(doc["operations"]),
                "blockedOperations": len(result["blockedOperations"]),
                "writeReady": False, "remoteWriteAuthorized": False}
    except (adapter.StoreError, sqlite3.Error, OSError, UnicodeError, ValueError):
        # Do not leak local paths, task text, or SQL error messages into QML.
        return {"status": "ERROR", "reason": "STORAGE_VALIDATION_FAILED",
                "available": False, "writeReady": False, "remoteWriteAuthorized": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description="TASKS SQLite read-only status")
    parser.add_argument("--db", type=Path, required=True)
    args = parser.parse_args(argv)
    status = report(args.db)
    sys.stdout.write(json.dumps(status, separators=(",", ":")) + "\n")
    return 0 if status["status"] != "ERROR" else 2


if __name__ == "__main__":
    raise SystemExit(main())
