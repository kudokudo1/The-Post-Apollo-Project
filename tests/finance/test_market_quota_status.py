#!/usr/bin/env python3
"""M21: disposable read-only quota status, no provider calls or host files."""
import fcntl
import os
from pathlib import Path
import sqlite3
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "finance"))
from market_shared_quota import reserve, LIMITS  # noqa: E402
from market_quota_status import quota_status, SOURCE  # noqa: E402

DAY = "2026-11-23"
OTHER_DAY = "2026-11-22"


def check_unknown(view, expected):
    assert view["schemaVersion"] == 1
    assert view["source"] == SOURCE
    assert view["readOnly"] is True
    assert view["noProviderCalls"] is True
    assert view["notAccountBalance"] is True
    assert view["utcDay"] == DAY
    assert view["ledgerState"] == expected
    assert [x["provider"] for x in view["providers"]] == [
        "eodhd", "alpha-vantage"
    ]
    assert [x["limit"] for x in view["providers"]] == [20, 25]
    assert all(x["reserved"] is None and x["recordState"] == "unknown"
               for x in view["providers"])


with tempfile.TemporaryDirectory(prefix="finance-m21-readonly-") as tmp:
    root = Path(tmp)
    home = root / "fake-home"
    home.mkdir(mode=0o700)
    base = home / ".local" / "share" / "post-apollo" / "finance-market"
    db = base / "global-free-provider-attempts-v1.sqlite3"
    with patch("market_quota_status.pwd.getpwuid",
               return_value=SimpleNamespace(pw_dir=str(home))):
        # No ledger or directories: status is UNKNOWN, no mkdir/db creation.
        check_unknown(quota_status(utc_day=DAY), "absent")
        assert list(home.iterdir()) == []
        for part in [home / ".local", home / ".local" / "share",
                     home / ".local" / "share" / "post-apollo", base]:
            part.mkdir(mode=0o700)
        check_unknown(quota_status(utc_day=DAY), "absent")
        assert not db.exists()

        # Use the existing M20 writer only in disposable test setup.
        reserve("eodhd", utc_day=DAY, database=db)
        reserve("eodhd", utc_day=DAY, database=db)
        reserve("alpha-vantage", utc_day=OTHER_DAY, database=db)
        before = db.read_bytes()
        before_stat = db.stat()
        view = quota_status(utc_day=DAY)
        if view["ledgerState"] != "ready":
            from market_quota_status import _read_canonical, _rows
            try:
                print("M21 DIAGNOSTIC canonical snapshot bytes",
                      len(_read_canonical()), file=sys.stderr)
                print("M21 DIAGNOSTIC parsed rows",
                      _rows(_read_canonical(), DAY), file=sys.stderr)
            except Exception as error:
                print("M21 DIAGNOSTIC failure", type(error).__name__,
                      repr(error), file=sys.stderr)
        assert view["ledgerState"] == "ready", view
        assert [x["reserved"] for x in view["providers"]] == [2, 0], view
        assert all(x["recordState"] == "known" for x in view["providers"])
        # No file content or modification-time changes after the inspection.
        assert db.read_bytes() == before
        assert db.stat().st_mtime_ns == before_stat.st_mtime_ns
        assert sorted(x.name for x in base.iterdir()) == [db.name]

        # Prior date carries its own count, no network calls or rollovers.
        previous = quota_status(utc_day=OTHER_DAY)
        assert [x["reserved"] for x in previous["providers"]] == [0, 1]
        assert db.read_bytes() == before

        # An existing DB with no row for today's date does mean 0 LOCAL
        # attempts, not 0 provider-account usage.
        future = quota_status(utc_day="2026-11-24")
        assert [x["reserved"] for x in future["providers"]] == [0, 0]
        assert future["notAccountBalance"] is True

        # Count remains correct after the writer reserves again.
        reserve("alpha-vantage", utc_day=DAY, database=db)
        current = quota_status(utc_day=DAY)
        assert [x["reserved"] for x in current["providers"]] == [2, 1]

        # File trust failures never silently render zero.
        db.chmod(0o644)
        check_unknown(quota_status(utc_day=DAY), "unavailable")
        db.chmod(0o600)
        base.chmod(0o755)
        check_unknown(quota_status(utc_day=DAY), "unavailable")
        base.chmod(0o700)

        # Sidecar indicates an in-progress/hot transaction; don't recover.
        journal = base / (db.name + "-journal")
        journal.write_bytes(b"intentional-journal-marker")
        check_unknown(quota_status(utc_day=DAY), "unavailable")
        journal.unlink()
        assert quota_status(utc_day=DAY)["ledgerState"] == "ready"

        # A read-only OS descriptor may not see a symlinked DB.
        with tempfile.TemporaryDirectory(prefix="finance-m21-links-") as other:
            alias = base / "symlink-test"
            alias.symlink_to(db)
            check_unknown(quota_status(database=alias, utc_day=DAY),
                          "unavailable")
            alias.unlink()

        # Separate holder of an exclusive POSIX lock => refuse, not guess.
        holder_code = """
import fcntl, os, sys
fd=os.open(sys.argv[1], os.O_RDWR | os.O_NOFOLLOW)
fcntl.lockf(fd, fcntl.LOCK_EX)
print("LOCKED",flush=True)
sys.stdin.readline()
fcntl.lockf(fd, fcntl.LOCK_UN)
os.close(fd)
"""
        child = subprocess.Popen(
            [sys.executable, "-c", holder_code, str(db)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True
        )
        try:
            assert child.stdout.readline().strip() == "LOCKED"
            check_unknown(quota_status(utc_day=DAY), "unavailable")
        finally:
            child.stdin.write("\n")
            child.stdin.flush()
            child.communicate(timeout=8)
        assert child.returncode == 0
        assert quota_status(utc_day=DAY)["ledgerState"] == "ready"

        # No status operation adds rows, mutates values, or creates files.
        with sqlite3.connect(db) as conn:
            rows = conn.execute(
                "SELECT provider,utc_day,reserved FROM quota_attempts "
                "ORDER BY provider,utc_day"
            ).fetchall()
        assert rows == [
            ("alpha-vantage", OTHER_DAY, 1),
            ("alpha-vantage", DAY, 1),
            ("eodhd", DAY, 2),
        ]
        assert sorted(x.name for x in base.iterdir()) == [db.name]

    # Corrupt and schema-less databases are unavailable, not zero.
    corrupt = root / "corrupt.sqlite3"
    corrupt.write_bytes(b"corrupted")
    check_unknown(quota_status(database=corrupt,utc_day=DAY), "unavailable")
    empty = root / "empty.sqlite3"
    sqlite3.connect(empty).close()
    check_unknown(quota_status(database=empty,utc_day=DAY), "unavailable")

print("Finance M21 no-write quota inspection, missing/unsafe/busy status and validated per-provider rows: PASS")
