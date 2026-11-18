#!/usr/bin/env python3
"""MACHINE V2 geometry durable journal: isolated SQLite crash matrix.

Does not contact a compositor, Quickshell, Brave, or operator XDG storage.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sqlite3
import stat
import subprocess
import sys
import tempfile
import threading
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/time"))
from MachineV2GeometryJournal import (
    GeometryJournal, GeometryJournalError, suggested_path, DB_NAME,
)

CHECKPOINT = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
WINDOW = str(uuid.uuid5(uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
                        "custom-window-1"))
WINDOW_2 = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
BEFORE = {"x": 2040, "y": 160, "width": 520, "height": 350}
TARGET = {"x": 2100, "y": 100, "width": 700, "height": 500}
SUMMARY = {
    "checkpoint_id": CHECKPOINT,
    "window_key": WINDOW, "app_id": "brave", "live_con_id": 110,
    "before_rect": BEFORE, "target_rect": TARGET,
}


def rejects(fn):
    try:
        fn()
    except GeometryJournalError:
        return
    raise AssertionError("invalid journal action accepted")


def reopen(db, phase):
    """Fresh Python process proves recovery persistence without commands."""
    script = """
import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from MachineV2GeometryJournal import GeometryJournal
db=Path(sys.argv[2])
journal=GeometryJournal(db)
pending=journal.pending()
assert len(pending)==1, pending
assert pending[0]["phase"]==sys.argv[3], pending
assert pending[0]["manual_review_required"] is True
assert pending[0]["automatic_retry_allowed"] is False
assert pending[0]["automatic_undo_allowed"] is False
assert pending[0]["production_restore_allowed"] is False
assert pending[0]["persistent_identity_verified"] is False
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-I", "-c", script,
         str(ROOT / "services/time"), str(db), phase],
        capture_output=True, timeout=10, check=False)
    assert completed.returncode == 0, completed.stderr.decode(errors="replace")


with tempfile.TemporaryDirectory(prefix="machine-v2-durable-") as temp:
    base = Path(temp) / "post-apollo" / "machine"
    db = base / DB_NAME
    journal = GeometryJournal(db)
    assert not db.exists() and not base.exists()
    assert journal.pending() == []
    assert journal.get(str(uuid.uuid4())) is None
    assert not db.exists() and not base.exists()
    initial = copy.deepcopy(SUMMARY)

    operation = journal.begin(SUMMARY)
    assert SUMMARY == initial
    assert len(operation) == 36
    assert db.exists()
    assert stat.S_IMODE(db.stat().st_mode) == 0o600
    assert stat.S_IMODE(db.parent.stat().st_mode) == 0o700
    assert journal.get(operation)["phase"] == "prepared"
    assert journal.get(operation)["summary"] == SUMMARY
    assert journal.get(operation)["production_restore_allowed"] is False
    assert journal.get(operation)["persistent_identity_verified"] is False
    assert journal.get(operation)["automatic_retry_allowed"] is False
    assert len(journal.pending()) == 1
    reopen(db, "prepared")

    # Active geometry operation globally freezes all other geometry writes.
    rejects(lambda: journal.begin(dict(SUMMARY, window_key=WINDOW_2)))
    rejects(lambda: journal.begin(SUMMARY))
    rejects(lambda: journal.finish(operation, "verified_fixture_placement"))
    rejects(lambda: journal.dispatching("NOT-UUID"))
    assert journal.get(operation)["phase"] == "prepared"

    journal.dispatching(operation)
    reopen(db, "dispatching")
    rejects(lambda: journal.dispatching(operation))
    rejects(lambda: journal.finish(operation, "user_approved"))
    assert journal.get(operation)["phase"] == "dispatching"
    journal.finish(operation, "uncertain_requires_review")
    reopen(db, "uncertain_requires_review")
    assert journal.pending()[0]["manual_review_required"] is True
    rejects(lambda: journal.begin(dict(SUMMARY, window_key=WINDOW_2)))
    rejects(lambda: journal.finish(operation, "verified_fixture_placement"))

    # New temporary journal shows terminal success doesn't replay same
    # checkpoint/window key, but permits a distinct manually selected key.
    finished_path = Path(temp) / "complete" / "post-apollo" / "machine" / DB_NAME
    complete = GeometryJournal(finished_path)
    first = complete.begin(SUMMARY)
    complete.dispatching(first)
    complete.finish(first, "verified_fixture_placement")
    assert complete.pending() == []
    view = complete.get(first)
    assert view["phase"] == "verified_fixture_placement"
    assert view["manual_review_required"] is False
    assert view["production_restore_allowed"] is False
    assert view["automatic_retry_allowed"] is False
    rejects(lambda: complete.begin(SUMMARY))
    second = dict(SUMMARY, window_key=WINDOW_2, live_con_id=111)
    oid = complete.begin(second)
    complete.dispatching(oid)
    complete.finish(oid, "verified_fixture_placement")
    assert complete.pending() == []
    assert complete.get(oid)["summary"] == second

    # Database transitions and schema contain no approval tokens, private
    # titles, process IDs, browser URL, commands or session contents.
    con = sqlite3.connect(finished_path)
    try:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 1
        assert con.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert con.execute("PRAGMA synchronous").fetchone()[0] == 2
        timeline = con.execute(
            "SELECT phase FROM transitions WHERE operation_id=? ORDER BY seq",
            (first,)).fetchall()
        assert [row[0] for row in timeline] == [
            "prepared", "dispatching", "verified_fixture_placement"]
        schema = json.dumps([x[1] for x in con.execute(
            "PRAGMA table_info(operations)")])
        for forbidden in ("approval_token", "pid", "title", "url",
                          "command", "browser_profile"):
            assert forbidden not in schema
        serialized = con.execute(
            "SELECT summary_json FROM operations WHERE id=?", (first,)
        ).fetchone()[0]
        assert json.loads(serialized) == SUMMARY
    finally:
        con.close()

    bad_inputs = [
        dict(SUMMARY, pid=123),
        dict(SUMMARY, title="private"),
        dict(SUMMARY, browser_url="https://secret.example"),
        dict(SUMMARY, approval_token="secret"),
        dict(SUMMARY, live_con_id=True),
        dict(SUMMARY, live_con_id=0),
        dict(SUMMARY, checkpoint_id=WINDOW),
        dict(SUMMARY, checkpoint_id="NOT-A-UUID"),
        dict(SUMMARY, window_key="NOT-A-UUID"),
        dict(SUMMARY, app_id="brave\nsecret"),
        dict(SUMMARY, before_rect={"x": 1, "y": 1, "width": True, "height": 50}),
        dict(SUMMARY, target_rect={"x": 1, "y": 1, "width": 0, "height": 50}),
        dict(SUMMARY, target_rect=BEFORE),
    ]
    for candidate in bad_inputs:
        rejects(lambda candidate=candidate: complete.begin(candidate))
    assert complete.pending() == []

    # Concurrent first-write attempts: BEGIN IMMEDIATE serializes contenders.
    contenders_path = Path(temp) / "race" / "post-apollo" / "machine" / DB_NAME
    contenders = GeometryJournal(contenders_path)
    barrier = threading.Barrier(6)
    accepted, refused = [], []
    guard = threading.Lock()

    def attempt(i):
        request = dict(SUMMARY, live_con_id=200 + i, window_key=(
            str(uuid.uuid5(uuid.UUID(CHECKPOINT), "race-" + str(i)))))
        barrier.wait()
        try:
            result = contenders.begin(request)
            with guard:
                accepted.append(result)
        except GeometryJournalError:
            with guard:
                refused.append(i)

    threads = [threading.Thread(target=attempt, args=(i,)) for i in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)
        assert not thread.is_alive(), "GEOMETRY JOURNAL DEADLOCK"
    assert len(accepted) == 1 and len(refused) == 5
    assert len(contenders.pending()) == 1

    # POSIX permissions and symlinks fail closed even for read-only requests.
    os.chmod(finished_path, 0o644)
    rejects(complete.pending)
    os.chmod(finished_path, 0o600)
    os.chmod(finished_path.parent, 0o755)
    rejects(complete.pending)
    os.chmod(finished_path.parent, 0o700)

    symlinked = Path(temp) / "symlink" / "post-apollo" / "machine" / DB_NAME
    symlinked.parent.mkdir(parents=True, mode=0o700)
    symlinked.symlink_to(finished_path)
    rejects(lambda: GeometryJournal(symlinked).pending())
    rejects(lambda: GeometryJournal(symlinked).begin(SUMMARY))

    hardlink = Path(temp) / "hardlink" / "post-apollo" / "machine" / DB_NAME
    hardlink.parent.mkdir(parents=True, mode=0o700)
    os.link(finished_path, hardlink)
    rejects(lambda: GeometryJournal(hardlink).pending())
    hardlink.unlink()

    linked_dir = Path(temp) / "linked-dir" / "post-apollo" / "machine"
    linked_dir.parent.mkdir(parents=True)
    linked_dir.symlink_to(base, target_is_directory=True)
    rejects(lambda: GeometryJournal(linked_dir / DB_NAME).pending())

    # A future schema or injected private field is not trusted when reopened.
    with sqlite3.connect(finished_path) as con:
        con.execute("PRAGMA user_version=73")
    rejects(complete.pending)
    with sqlite3.connect(finished_path) as con:
        con.execute("PRAGMA user_version=1")
        con.execute("UPDATE operations SET summary_json=? WHERE id=?",
                    (json.dumps(dict(SUMMARY, url="https://private.example")), first))
    rejects(lambda: complete.get(first))
    assert complete.path.name == DB_NAME

    # Do not provide an automatic production entrypoint or Sway runner.
    import MachineV2GeometryJournal as module
    assert not hasattr(module, "main")
    assert not hasattr(module, "execute")
    assert suggested_path().name == DB_NAME

print("MACHINE V2 JOURNAL // DURABLE PHASES, CRASH HOLD, PRIVACY, NO REPLAY PASS")
