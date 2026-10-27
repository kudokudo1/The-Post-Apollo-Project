#!/usr/bin/env python3
"""M11r read-only, sanitized inspector for ONE new disposable native fault.

No writes, no bootstrap, no process launch and no actual TASKS paths.
Run only after the standalone Quickshell test host has exited.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[3]
GATE = ROOT / "services/projects/TaskJsonGateCandidateM11l.py"
spec = importlib.util.spec_from_file_location("m11r_disposable_gate", GATE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

FAULTS = {
    "AFTER_RESERVE": (0, True, "RESERVED", True),
    "AFTER_SAVED": (1, True, "RESERVED", False),
    "AFTER_READBACK": (1, True, "RESERVED", False),
    "AFTER_SETTLEMENT": (1, False, "SETTLED", True)
}


def inspect(source: Path, fault: str, *, reopened: bool = False):
    if fault not in FAULTS or not isinstance(source, Path):
        raise ValueError("INVALID_TEST_ARGUMENTS")
    if (not source.is_absolute() or source.name != "todo-copy.json"
            or source.parent.name != "m11l-tasks-copy"):
        raise ValueError("DISPOSABLE_COPY_ONLY")
    gate.private_dir(source.parent)
    raw = gate.source_bytes(source)
    doc = gate.parse_task_document(raw)
    title = doc["tasks"][0]["title"] if len(doc["tasks"]) == 1 else ""
    match = re.fullmatch(r"M11M_TEST_(0|[1-9][0-9]?)", title)
    if not match:
        raise ValueError("NOT_M11M_SYNTHETIC_DATA")
    fixture_counter = int(match.group(1))
    journal = source.parent / "gate-review.db"
    gate.owned_regular(journal)
    backup = gate.source_bytes(source.parent / "source-before-gate.bak")
    gate.parse_task_document(backup)
    # A strict, read-only sqlite3 connection cannot create any schema.
    uri = "file:" + quote(str(journal), safe="/") + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as db:
        db.row_factory = sqlite3.Row
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version != 2:
            raise ValueError("REPLAY_HISTORY_REQUIRED")
        row = db.execute("SELECT * FROM owner WHERE id=1").fetchone()
        if row is None:
            raise ValueError("MISSING_DURABLE_OWNER")
        history = db.execute("""SELECT stage_id,epoch,expected_hash,
            source_hash_before,state FROM stage_history""").fetchall()
    if len(history) != 1:
        raise ValueError("UNEXPECTED_HISTORY_LENGTH")
    stage = history[0]
    expected_counter, expected_pending, expected_state, expected_hash_match = FAULTS[fault]
    is_pending = row["pending_stage"] is not None
    hash_matches = hashlib.sha256(raw).hexdigest() == row["source_hash"]
    backup_matches = hashlib.sha256(backup).hexdigest() == row["backup_hash"]
    stage_matches = (
        is_pending
        and row["pending_stage"] == stage["stage_id"]
        and row["expected_hash"] == stage["expected_hash"]
    ) if expected_pending else (
        row["pending_stage"] is None and row["expected_hash"] is None
    )
    expected_phase = "RECOVERY_REVIEW" if reopened else "JSON_ACTIVE"
    accepted = all((
        row["phase"] == expected_phase,
        row["history_complete"] == 1,
        fixture_counter == expected_counter,
        is_pending == expected_pending,
        stage["state"] == expected_state,
        stage_matches,
        hash_matches == expected_hash_match,
        backup_matches,
        json.loads(backup)["tasks"][0]["title"] == "M11M_TEST_0",
    ))
    # Deliberately no paths, stage IDs, hashes, JSON data, host stdout.
    return {
        "milestone": "M11r",
        "scope": "SYNTHETIC_COPY_ONLY",
        "fault": fault,
        "phase": row["phase"],
        "epoch": row["epoch"],
        "pending": is_pending,
        "stageState": stage["state"],
        "counter": fixture_counter,
        "sourceHashMatchesJournal": hash_matches,
        "initialBackupVerified": backup_matches,
        "expectationMet": accepted,
        "nativeCallbackTraceObserved": False,
        "productionWriterAuthorized": False
    }


def main():
    parser = argparse.ArgumentParser(description="M11r read-only synthetic fault journal inspector")
    parser.add_argument("--test-file", type=Path, required=True)
    parser.add_argument("--fault", choices=sorted(FAULTS), required=True)
    parser.add_argument("--after-existing", action="store_true")
    args = parser.parse_args()
    try:
        report = inspect(args.test_file, args.fault, reopened=args.after_existing)
        print(json.dumps(report, sort_keys=True))
        return 0 if report["expectationMet"] else 1
    except (ValueError, OSError, sqlite3.Error, gate.GateError,
            KeyError, TypeError, IndexError):
        print("M11R_INSPECTION_REFUSED")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
