#!/usr/bin/env python3
"""Explicit one-time disposable SQLite-v2 sample for M10z QML acceptance.

No default location. Requires a caller-created private m10y-snapshot-test
directory; refuses to overwrite any existing tasks.db. SYNTHETIC DATA ONLY.
Never operates on the active TASKS JSON or GitHub Projects.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

TEST_TS = 1700000000000


def initialize(path: Path):
    if (not path.is_absolute() or path.name != "tasks.db"
            or path.parent.name != "m10y-snapshot-test"):
        raise ValueError("EXPLICIT_DISPOSABLE_TASKS_DB_REQUIRED")
    spec=importlib.util.spec_from_file_location(
        "m10z_fixture_store",
        Path(__file__).resolve().parents[3] /
        "services/projects/ExperimentalTaskSqliteRecordsV2.py")
    records=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(records)
    doc={
        "version":2, "revision":0,
        "nextId":3, "nextProjectId":2, "nextOperationId":1,
        "projects":[{"id":"p1","name":"TEST PROJECT","family":"normal",
                     "remote":None,"fields":[],"createdAtMs":TEST_TS,
                     "updatedAtMs":TEST_TS}],
        "tasks":[{"id":"t1","projectId":"p1",
                  "title":"M10z disposable example task","done":False,
                  "priority":"low","description":"Synthetic sample only",
                  "dueDate":"2026-10-24","remote":None,"values":{},
                  "createdAtMs":TEST_TS,"updatedAtMs":TEST_TS},
                 {"id":"t2","projectId":"p1",
                  "title":"M10z completed example","done":True,
                  "priority":"none","description":"",
                  "dueDate":None,"remote":None,"values":{},
                  "createdAtMs":TEST_TS,"updatedAtMs":TEST_TS}],
        "operations":[]}
    return records.initialize(path, doc)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description="M10z disposable read-only demo fixture")
    parser.add_argument("--db",type=Path,required=True)
    args=parser.parse_args()
    result=initialize(args.db)
    assert result["writeReady"] is False
    print("M10z synthetic fixture created (not active TASKS storage).")
