#!/usr/bin/env python3
"""Finance Market M21: inspect M20 quota rows without writing or fetching.

Never imports/calls M20's directory-creating _database()/reserve() routines.
The canonical CLI accepts no caller path. Tests can inject a disposable DB.
"""
import datetime as dt
import fcntl
import json
import os
import pwd
import sqlite3
import stat
import sys
from pathlib import Path

from market_shared_quota import LIMITS, SCOPE, DB_NAME

MAX_DB_BYTES = 2 * 1024 * 1024
SOURCE = "post-apollo-market-local-quota-status-v1"


class MissingLedger(Exception):
    pass


class UnavailableLedger(Exception):
    pass


def _open_db(filename, directory_fd):
    flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NOATIME", 0)
    try:
        fd = os.open(filename, flags, dir_fd=directory_fd)
    except FileNotFoundError as exc:
        raise MissingLedger() from exc
    except OSError as exc:
        raise UnavailableLedger("db-open") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() \
                or info.st_nlink != 1 or info.st_mode & 0o077 \
                or not (100 <= info.st_size <= MAX_DB_BYTES):
            raise UnavailableLedger("db-type")
        return fd
    except BaseException:
        os.close(fd)
        raise


def _snapshot(fd, sibling_exists):
    try:
        # M20 uses rollback-journal SQLite. Never recover a hot journal or
        # inspect a WAL snapshot while its potentially uncommitted data exists.
        fcntl.lockf(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
    except OSError as exc:
        raise UnavailableLedger("db-busy") from exc
    try:
        if sibling_exists():
            raise UnavailableLedger("db-sidecars")
        info = os.fstat(fd)
        if not (100 <= info.st_size <= MAX_DB_BYTES):
            raise UnavailableLedger("db-size")
        size = info.st_size
        chunks = []
        os.lseek(fd, 0, os.SEEK_SET)
        while size:
            part = os.read(fd, min(size, 65536))
            if not part:
                raise UnavailableLedger("db-short")
            chunks.append(part)
            size -= len(part)
        data = b"".join(chunks)
        if os.fstat(fd).st_size != info.st_size \
                or not data.startswith(b"SQLite format 3\x00") \
                or data[18] != 1 or data[19] != 1:
            raise UnavailableLedger("db-format")
        return data
    finally:
        fcntl.lockf(fd, fcntl.LOCK_UN)


def _rows(data, day):
    # A fully in-memory copy avoids sqlite3.connect(file) and accidental
    # WAL/journal/shm creation on the real file. No sqlite write APIs here.
    conn = sqlite3.connect(":memory:")
    try:
        conn.deserialize(data)
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA trusted_schema=OFF")
        schema = conn.execute("PRAGMA table_info(quota_attempts)").fetchall()
        if [(col[1], col[2].upper()) for col in schema] != [
            ("provider", "TEXT"), ("utc_day", "TEXT"), ("reserved", "INTEGER")
        ]:
            raise UnavailableLedger("db-schema")
        result = {}
        for provider, reserved in conn.execute(
            "SELECT provider, reserved FROM quota_attempts WHERE utc_day=?",
            (day,)
        ):
            if provider not in LIMITS or type(reserved) is not int \
                    or not (1 <= reserved <= LIMITS[provider]) \
                    or provider in result:
                raise UnavailableLedger("db-count")
            result[provider] = reserved
        return result
    finally:
        conn.close()


def _has_sidecars(directory_fd, base):
    for suffix in ("-journal", "-wal", "-shm"):
        try:
            os.stat(base + suffix, dir_fd=directory_fd,
                    follow_symlinks=False)
        except FileNotFoundError:
            continue
        except OSError:
            return True
        return True
    return False


def _read_canonical():
    home = pwd.getpwuid(os.getuid()).pw_dir
    if not home or not os.path.isabs(home):
        raise UnavailableLedger("untrusted-home")
    # Open each existing component read-only, never mkdir/chmod/unlink.
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    parent = None
    fd = None
    try:
        parent = os.open(home, directory_flags)
        for index, component in enumerate((
            ".local", "share", "post-apollo", "finance-market"
        )):
            child = os.open(component, directory_flags, dir_fd=parent)
            info = os.fstat(child)
            if info.st_uid != os.getuid() or not stat.S_ISDIR(info.st_mode) \
                    or info.st_mode & 0o022 \
                    or index == 3 and info.st_mode & 0o077:
                os.close(child)
                raise UnavailableLedger("unsafe-directory")
            os.close(parent)
            parent = child
        fd = _open_db(DB_NAME, parent)
        return _snapshot(fd, lambda: _has_sidecars(parent, DB_NAME))
    except FileNotFoundError as exc:
        raise MissingLedger() from exc
    except OSError as exc:
        raise UnavailableLedger("unreadable-directory") from exc
    finally:
        if fd is not None:
            os.close(fd)
        if parent is not None:
            os.close(parent)


def _read_test_file(path):
    # Not exposed by CLI: only disposable tests may inject this.
    p = Path(path)
    parent = os.open(str(p.parent),
                     os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fd = _open_db(p.name, parent)
        try:
            return _snapshot(fd, lambda: _has_sidecars(parent, p.name))
        finally:
            os.close(fd)
    finally:
        os.close(parent)


def quota_status(*, database=None, utc_day=None):
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    day = today if utc_day is None else utc_day
    if type(day) is not str or dt.date.fromisoformat(day).isoformat() != day:
        raise ValueError("invalid-day")
    state = "ready"
    counts = {}
    try:
        data = _read_canonical() if database is None else _read_test_file(database)
        counts = _rows(data, day)
    except MissingLedger:
        state = "absent"
    except (UnavailableLedger, sqlite3.Error, OSError, ValueError, OverflowError):
        state = "unavailable"
    return {
        "schemaVersion": 1,
        "source": SOURCE,
        "scope": SCOPE,
        "readOnly": True,
        "noProviderCalls": True,
        "notAccountBalance": True,
        "utcDay": day,
        "ledgerState": state,
        "providers": [
            {
                "provider": provider,
                "limit": limit,
                "reserved": counts.get(provider, 0) if state == "ready"
                    else None,
                "recordState": "known" if state == "ready" else "unknown",
            }
            for provider, limit in LIMITS.items()
        ],
    }


def main():
    if len(sys.argv) != 2 or sys.argv[1] != "status":
        print("FINANCE_QUOTA_STATUS_ERROR invalid-command")
        return 2
    try:
        result = quota_status()
    except (ValueError, OSError, sqlite3.Error):
        print("FINANCE_QUOTA_STATUS_ERROR status-unavailable")
        return 3
    print("FINANCE_QUOTA_STATUS " + json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
