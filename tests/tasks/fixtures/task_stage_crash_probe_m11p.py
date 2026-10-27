#!/usr/bin/env python3
"""M11p crash-window child: deliberately terminates without normal cleanup.

SYNTHETIC TEST COPY ONLY. Accepts an owned m11l-tasks-copy directory and
todo-copy.json from tests. Never loads production Quickshell task data.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWNER_FILE = ROOT / "services/projects/TaskJsonGateCandidateM11l.py"
spec = importlib.util.spec_from_file_location("m11p_owner", OWNER_FILE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def new_document(counter):
    return (json.dumps({
        "version": 3, "nextId": 2, "nextProjectId": 1,
        "projects": [], "tasks": [{
            "id": "t1", "title": f"M11P_TEST_{counter}", "done": False,
            "createdAtMs": 1000, "updatedAtMs": 1000 + counter,
            "priority": "none", "description": "",
            "dueDate": None, "projectId": None
        }]
    }, separators=(",", ":")) + "\n").encode()


def test_atomic_file_replace(path: Path, data: bytes):
    replacement = path.parent / "m11p-write-next.json"
    fd = os.open(replacement, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(replacement, path)
        dirfd = os.open(path.parent, os.O_RDONLY |
                        getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    except BaseException:
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--mode", required=True,
                        choices=["before-reserve", "after-reserve",
                                 "after-file-write", "after-settlement"])
    parser.add_argument("--stage-id", default="m11p-crash-stage-001")
    args = parser.parse_args()
    # Bootstrap exclusively in a fresh disposable folder; the test runner
    # never reuses a journal after an interrupted process.
    owner = gate.CandidateOwner(args.directory,
                                "m11p-crash-process-owner-001",
                                bootstrap=True)
    if args.mode == "before-reserve":
        os._exit(80)
    candidate = new_document(1)
    token = owner.reserve(args.stage_id, candidate)
    if args.mode == "after-reserve":
        os._exit(81)
    test_atomic_file_replace(owner.source, candidate)
    if args.mode == "after-file-write":
        os._exit(82)
    owner.verify(args.stage_id, token["epoch"])
    if args.mode == "after-settlement":
        os._exit(83)
    raise AssertionError("UNEXPECTED_MODE")


if __name__ == "__main__":
    main()
