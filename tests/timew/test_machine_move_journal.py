#!/usr/bin/env python3
"""M1l durable recovery fixture. Uses only temp SQLite databases, not Sway."""
from pathlib import Path
import copy
import os
import sqlite3
import stat
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2] / "services" / "time"
sys.path.insert(0, str(root))
from MachineMoveJournal import MoveJournal, JournalError, suggested_path

before = {"con_id": 51, "app_id": "kitty",
          "workspace": "1", "target_workspace": "2"}
original = copy.deepcopy(before)
with tempfile.TemporaryDirectory() as temp:
    db = Path(temp) / "post-apollo" / "machine" / "move-operations.db"
    journal = MoveJournal(db)
    assert not db.exists()
    assert journal.pending() == [] and journal.get("00000000-0000-0000-0000-000000000000") is None
    assert not db.parent.exists(), "read-only operations created a database"

    op = journal.begin(before)
    assert before == original
    assert db.exists()
    assert stat.S_IMODE(db.stat().st_mode) == 0o600
    assert stat.S_IMODE(db.parent.stat().st_mode) == 0o700
    assert journal.get(op)["phase"] == "prepared"
    assert journal.get(op)["before"] == before
    assert journal.get(op)["requires_manual_review"] is True
    assert journal.get(op)["automatic_retry_allowed"] is False
    assert len(journal.pending()) == 1

    # Simulate helper death: a fresh Python process sees the durable record
    # but never executes/retries any compositor command.
    child = """
import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from MachineMoveJournal import MoveJournal
j=MoveJournal(Path(sys.argv[2]))
rows=j.pending()
assert len(rows)==1 and rows[0]['phase']==sys.argv[3]
assert not rows[0]['automatic_retry_allowed']
"""
    def reopen(expected):
        got = subprocess.run(
            [sys.executable, "-B", "-I", "-c", child, str(root), str(db), expected],
            capture_output=True, timeout=10)
        assert got.returncode == 0, got.stderr.decode(errors="replace")
    reopen("prepared")

    try:
        journal.begin(before)
        raise AssertionError("second active move allowed")
    except JournalError:
        pass
    assert len(journal.pending()) == 1

    journal.mark_dispatching(op)
    assert journal.get(op)["phase"] == "dispatching"
    reopen("dispatching")
    for invalid in (lambda: journal.mark_dispatching(op),
                    lambda: journal.finish(op, "verified_moved" + "X"),
                    lambda: journal.finish("invalid", "verified_moved")):
        try:
            invalid()
            raise AssertionError("invalid transition allowed")
        except JournalError:
            pass
    # An unacknowledged command remains pending even after restart.
    assert journal.pending()[0]["phase"] == "dispatching"
    journal.finish(op, "uncertain_requires_manual_review", None)
    reopen("uncertain_requires_manual_review")
    assert journal.get(op)["requires_manual_review"]
    try:
        journal.begin(before)
        raise AssertionError("unresolved uncertain move was ignored")
    except JournalError:
        pass

    # Independent completed ledger in another temporary DB.
    finished_path = Path(temp) / "completed" / "move-operations.db"
    finished = MoveJournal(finished_path)
    success = finished.begin(before)
    finished.mark_dispatching(success)
    finished.finish(success, "verified_moved", "2")
    assert finished.pending() == []
    assert finished.get(success)["observed_workspace"] == "2"
    assert not finished.get(success)["requires_manual_review"]
    assert not finished.get(success)["automatic_retry_allowed"]
    refused = finished.begin(before)
    finished.mark_dispatching(refused)
    finished.finish(refused, "refused_no_confirmed_move", "1")
    assert finished.pending() == []
    assert finished.get(refused)["phase"] == "refused_no_confirmed_move"

    connection = sqlite3.connect(finished_path)
    try:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        transitions = connection.execute(
            "SELECT phase FROM transitions WHERE operation_id=? ORDER BY seq",
            (success,)).fetchall()
        assert [v[0] for v in transitions] == [
            "prepared", "dispatching", "verified_moved"]
        fields = [x[1] for x in connection.execute("PRAGMA table_info(operations)")]
        assert "before_json" in fields and "approval_token" not in fields
        records = connection.execute("SELECT before_json FROM operations").fetchall()
        assert all("pid" not in row[0] and "title" not in row[0] for row in records)
    finally:
        connection.close()

    for bad in (
        dict(before, pid=1000),
        dict(before, title="private"),
        dict(before, con_id=True),
        dict(before, workspace="1\n"),
        dict(before, target_workspace="1"),
        dict(before, app_id=""),
    ):
        try:
            finished.begin(bad)
            raise AssertionError("private/invalid state accepted")
        except JournalError:
            pass
    assert finished.pending() == []

    # Fail shut on world-readable DB or directory, even for read-only listing.
    os.chmod(finished_path, 0o644)
    try:
        finished.pending()
        raise AssertionError("insecure DB opened")
    except JournalError:
        pass
    os.chmod(finished_path, 0o600)
    os.chmod(finished_path.parent, 0o755)
    try:
        finished.begin(before)
        raise AssertionError("insecure directory accepted")
    except JournalError:
        pass
    os.chmod(finished_path.parent, 0o700)

    # A symlink is rejected rather than followed.
    link = Path(temp) / "linked" / "move-operations.db"
    link.parent.mkdir(mode=0o700)
    link.symlink_to(finished_path)
    try:
        MoveJournal(link).pending()
        raise AssertionError("symlinked journal accepted")
    except JournalError:
        pass

    # Invalid schema version refuses both read and write.
    connection = sqlite3.connect(finished_path)
    connection.execute("PRAGMA user_version=9")
    connection.commit()
    connection.close()
    try:
        finished.pending()
        raise AssertionError("future journal schema accepted")
    except JournalError:
        pass

assert suggested_path().name == "move-operations.db"
print("TIMEW M1L: DURABLE JOURNAL PASS / CRASH RECOVERY / NO REPLAY")
