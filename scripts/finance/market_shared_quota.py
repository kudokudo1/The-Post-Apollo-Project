#!/usr/bin/env python3
"""M20: fail-closed, local-only SQLite reservation before free market fetches.

This is NOT the provider's account quota. It counts just the two opt-in
FinanceW global price CLI adapters. Never stores credentials or symbols.
"""
import datetime as dt
import json
import os
import pwd
import sqlite3
import stat
import sys
from pathlib import Path

LIMITS = {"eodhd": 20, "alpha-vantage": 25}
SCOPE = "post-apollo-market-local-v1"
DB_NAME = "global-free-provider-attempts-v1.sqlite3"


class QuotaExhausted(Exception):
    pass


class QuotaStorageUnavailable(Exception):
    pass


def _owned_directory():
    """Walk host directories without following symlinks."""
    home = pwd.getpwuid(os.getuid()).pw_dir
    if not home or not os.path.isabs(home):
        raise QuotaStorageUnavailable("home-not-trusted")
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(home, flags)
    try:
        for index, component in enumerate(
            (".local", "share", "post-apollo", "finance-market")
        ):
            try:
                os.mkdir(component, mode=0o700, dir_fd=fd)
            except FileExistsError:
                pass
            child = os.open(component, flags, dir_fd=fd)
            st = os.fstat(child)
            if st.st_uid != os.getuid() or not stat.S_ISDIR(st.st_mode) \
                    or (st.st_mode & 0o022) != 0 \
                    or (index == 3 and (st.st_mode & 0o077) != 0):
                os.close(child)
                raise QuotaStorageUnavailable("unsafe-directory")
            os.close(fd)
            fd = child
        return Path(home, ".local", "share", "post-apollo", "finance-market"), fd
    except BaseException:
        os.close(fd)
        raise


def _database():
    directory, dirfd = _owned_directory()
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL \
            | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(DB_NAME, flags, 0o600, dir_fd=dirfd)
            os.close(fd)
        except FileExistsError:
            pass
        st = os.stat(DB_NAME, dir_fd=dirfd, follow_symlinks=False)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() \
                or st.st_nlink != 1 or (st.st_mode & 0o077) != 0:
            raise QuotaStorageUnavailable("unsafe-db")
        return directory / DB_NAME
    finally:
        os.close(dirfd)


def reserve(provider, *, utc_day=None, database=None):
    """Atomically reserve a call. Failed fetches still consume a local slot.

    The database override exists for disposable tests only. CLI never accepts
    a caller-supplied path.
    """
    if provider not in LIMITS:
        raise ValueError("unknown-provider")
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    day = today if utc_day is None else utc_day
    try:
        if dt.date.fromisoformat(day).isoformat() != day:
            raise ValueError("invalid-day")
    except (ValueError, TypeError):
        raise ValueError("invalid-day") from None
    path = Path(database) if database is not None else _database()
    con = None
    try:
        con = sqlite3.connect(str(path), timeout=5.0, isolation_level=None)
        con.execute("PRAGMA busy_timeout=5000")
        con.execute("BEGIN IMMEDIATE")
        con.execute("""CREATE TABLE IF NOT EXISTS quota_attempts (
            provider TEXT NOT NULL,
            utc_day TEXT NOT NULL,
            reserved INTEGER NOT NULL CHECK(reserved >= 0),
            PRIMARY KEY (provider, utc_day)
        )""")
        found = con.execute(
            "SELECT reserved FROM quota_attempts WHERE provider=? AND utc_day=?",
            (provider, day)
        ).fetchone()
        count = int(found[0]) if found else 0
        limit = LIMITS[provider]
        if count >= limit:
            con.execute("ROLLBACK")
            raise QuotaExhausted("local-budget-exhausted")
        count += 1
        con.execute("""INSERT INTO quota_attempts(provider,utc_day,reserved)
            VALUES (?,?,?)
            ON CONFLICT(provider,utc_day) DO UPDATE
            SET reserved=excluded.reserved""", (provider, day, count))
        con.execute("COMMIT")
        return {
            "schemaVersion": 1,
            "scope": SCOPE,
            "provider": provider,
            "utcDay": day,
            "reserved": count,
            "limit": limit,
            "notAccountBalance": True,
        }
    except sqlite3.Error as exc:
        if con is not None and con.in_transaction:
            con.execute("ROLLBACK")
        raise QuotaStorageUnavailable("sqlite-unavailable") from exc
    finally:
        if con is not None:
            con.close()


def main():
    if len(sys.argv) != 3 or sys.argv[1] != "reserve" \
            or sys.argv[2] not in LIMITS:
        print("FINANCE_LOCAL_QUOTA_ERROR invalid-command")
        return 2
    try:
        payload = reserve(sys.argv[2])
    except QuotaExhausted:
        print("FINANCE_LOCAL_QUOTA_ERROR local-quota-exhausted")
        return 3
    except (OSError, sqlite3.Error, QuotaStorageUnavailable, ValueError):
        print("FINANCE_LOCAL_QUOTA_ERROR local-quota-unavailable")
        return 4
    print("FINANCE_LOCAL_QUOTA " + json.dumps(payload, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
