#!/usr/bin/env python3
"""M10y explicit-use SQLite-v2 read-only compatibility snapshot probe.

TEST FIXTURES ONLY. A private m10y-snapshot-test/tasks.db must already exist.
Never creates, upgrades, rewrites, migrates, syncs or authorizes TASKS storage.
The response intentionally contains task content needed for rendering; callers
must not log it or send it to network endpoints.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys

MAX_RESPONSE_BYTES = 1048576
PROTOCOL = 1


def _adapter():
    source = Path(__file__).resolve().with_name("ExperimentalTaskSqliteRecordsV2.py")
    spec = importlib.util.spec_from_file_location("m10y_v2_reader", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("READER_UNAVAILABLE")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _unavailable(status):
    return {"protocol":PROTOCOL, "status":status,
            "available":False,"revision":None,"sourceHash":None,
            "blockedOperations":0,"document":None,
            "writeReady":False,"remoteWriteAuthorized":False}


def report(path):
    if (not isinstance(path, Path) or not path.is_absolute()
            or path.name != "tasks.db" or path.parent.name != "m10y-snapshot-test"):
        return _unavailable("ERROR")
    store = _adapter()
    try:
        result = store.read(path)  # Existing DB, sqlite mode=ro, no bootstrap.
        if result["status"] == "ABSENT":
            return _unavailable("ABSENT")
        doc = result["document"]
        projects = [{"id":p["id"],"name":p["name"],
                     "createdAtMs":p["createdAtMs"],
                     "updatedAtMs":p["updatedAtMs"]}
                    for p in doc["projects"]]
        tasks = [{"id":t["id"],"title":t["title"],"done":t["done"],
                  "createdAtMs":t["createdAtMs"],
                  "updatedAtMs":t["updatedAtMs"],
                  "priority":t["priority"],"description":t["description"],
                  "dueDate":t["dueDate"],"projectId":t["projectId"]}
                 for t in doc["tasks"]]
        compatibility = {
            "version":3, "nextId":doc["nextId"],
            "nextProjectId":doc["nextProjectId"],
            "projects":projects,"tasks":tasks}
        # No source metadata, custom values, remote IDs, queue bodies or
        # identity/permission claims are serialized into the UI response.
        status = ("RECOVERY_REVIEW" if result["status"]=="RECOVERY_REVIEW"
                  else "READY" if tasks else "EMPTY")
        output = {"protocol":PROTOCOL,"status":status,"available":True,
                  "revision":result["revision"],"sourceHash":result["hash"],
                  "blockedOperations":len(result["blockedOperations"]),
                  "document":compatibility,
                  "writeReady":False,"remoteWriteAuthorized":False}
        serialized = json.dumps(output,separators=(",",":"),
                                ensure_ascii=False,allow_nan=False)
        if len(serialized.encode("utf-8")) > MAX_RESPONSE_BYTES:
            return _unavailable("ERROR")
        return output
    except (store.StoreError,sqlite3.Error,OSError,UnicodeError,
            ValueError,KeyError,TypeError):
        return _unavailable("ERROR")


def main(argv=None):
    parser = argparse.ArgumentParser(description="M10y disposable SQLite-v2 read-only snapshot")
    parser.add_argument("--db",type=Path,required=True)
    args = parser.parse_args(argv)
    result = report(args.db)
    sys.stdout.write(json.dumps(result,separators=(",",":"),
                                ensure_ascii=False,allow_nan=False)+"\n")
    return 2 if result["status"]=="ERROR" else 0


if __name__ == "__main__":
    raise SystemExit(main())
