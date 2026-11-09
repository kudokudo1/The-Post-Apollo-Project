#!/usr/bin/env python3
"""Explicit MACHINE checkpoint annotation CLI. Never invoked on import.

READ: python3 -B -I MachineCheckpointNotesCLI.py read <checkpoint UUID>
UPDATE: python3 -B -I MachineCheckpointNotesCLI.py update
        stdin: one bounded JSON line with id, name, note and read revision.

No shell commands, Sway IPC, browser data, UI timers or restore actions.
Metadata input travels via stdin, never the process argument list.
"""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from MachineCheckpointAnnotations import (
    AnnotationError, get_annotation, set_annotation)
from MachineCheckpointStore import StoreError

MAX_INPUT_BYTES = 8192
MAX_OUTPUT_BYTES = 16384


def _input():
    data = sys.stdin.buffer.readline(MAX_INPUT_BYTES + 1)
    if (not data or len(data) > MAX_INPUT_BYTES
            or not data.endswith(b"\n")):
        raise AnnotationError("INVALID ANNOTATION REQUEST")
    try:
        payload = json.loads(data)
    except (ValueError, UnicodeError, TypeError) as exc:
        raise AnnotationError("INVALID ANNOTATION REQUEST") from exc
    if not isinstance(payload, dict) or set(payload) != {
            "checkpoint_id", "display_name", "note", "expected_revision"}:
        raise AnnotationError("INVALID ANNOTATION REQUEST")
    return payload


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not (len(argv) == 2 and argv[0] == "read") and argv != ["update"]:
        print(json.dumps({"status": "error", "reason": "INVALID ACTION"}))
        return 1
    try:
        if argv[0] == "read":
            result = get_annotation(argv[1])
        else:
            payload = _input()
            result = set_annotation(
                payload["checkpoint_id"],
                display_name=payload["display_name"], note=payload["note"],
                expected_revision=payload["expected_revision"])
        encoded = json.dumps(
            result, separators=(",", ":"), ensure_ascii=False)
        if len(encoded.encode("utf-8")) > MAX_OUTPUT_BYTES:
            raise AnnotationError("ANNOTATION RESPONSE TOO LARGE")
        print(encoded)
        return 0
    except (AnnotationError, StoreError):
        # Do not print file paths or private note contents on failure.
        print(json.dumps({
            "status": "error", "reason": "ANNOTATION REJECTED"}))
        return 1
    except (sqlite3.Error, OSError, TypeError, ValueError):
        print(json.dumps({
            "status": "error", "reason": "ANNOTATION STORE UNAVAILABLE"}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
