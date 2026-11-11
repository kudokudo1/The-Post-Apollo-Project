#!/usr/bin/env python3
"""Trash++ V2c: bounded, read-only SQLite copy index for the Archive UI.

This process has exactly one verb: index. It never creates an Archive database,
replays destructive actions, reads original owner sources, or returns payloads.
Its index is metadata-only and does not claim full payload integrity.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
from urllib.parse import quote

DB_NAME = "trashpp-archive-v2.sqlite3"
STORE_SCHEMA = "post-apollo.trash-archive.v2a"
PAGE_SIZE = 25
MAX_DIRECTORY_ARG = 4096
CURSOR = re.compile(r"^([1-9][0-9]{0,12}):([0-9a-f]{32})$")
HEX_ID = re.compile(r"^[0-9a-f]{32}$")
HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")
RESOURCE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
ALLOWED_OWNERS = {"demo-scrape", "weather-events"}


class ReadIndexError(Exception):
    pass


def _require(condition, code):
    if not condition:
        raise ReadIndexError(code)


def _private_regular(path):
    try:
        entry = path.lstat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise ReadIndexError("ARCHIVE_UNAVAILABLE") from exc
    _require(stat.S_ISREG(entry.st_mode)
             and entry.st_uid == os.geteuid()
             and entry.st_nlink == 1
             and entry.st_mode & 0o077 == 0, "ARCHIVE_FILE_UNSAFE")
    return True


def _dir(directory):
    _require(isinstance(directory, str)
             and directory.startswith("/")
             and ".." not in Path(directory).parts
             and "\x00" not in directory
             and len(directory) <= MAX_DIRECTORY_ARG, "INVALID_DATA_DIRECTORY")
    path = Path(directory)
    try:
        entry = path.lstat()
    except OSError as exc:
        raise ReadIndexError("ARCHIVE_ROOT_UNAVAILABLE") from exc
    _require(stat.S_ISDIR(entry.st_mode)
             and entry.st_uid == os.geteuid()
             and entry.st_mode & 0o077 == 0, "ARCHIVE_ROOT_UNSAFE")
    return path


def _cursor(value):
    if value == "":
        return None
    _require(isinstance(value, str), "INVALID_PAGE_CURSOR")
    match = CURSOR.fullmatch(value)
    _require(match is not None and 1 <= int(match.group(1)) <= 9999999999999,
             "INVALID_PAGE_CURSOR")
    return int(match.group(1)), match.group(2)


def _response(items, count, next_cursor=None, state="READY"):
    return {"ok": True, "kind": "archive-v2-index", "readOnly": True,
            "schema": STORE_SCHEMA, "state": state, "total": count,
            "items": items, "hasMore": next_cursor is not None,
            "nextCursor": next_cursor, "pageSize": PAGE_SIZE}


def _row(raw):
    sid, owner, rid, revision, captured, label, checksum, size = raw
    _require(isinstance(sid, str) and HEX_ID.fullmatch(sid) is not None,
             "ARCHIVE_METADATA_INVALID")
    _require(owner in ALLOWED_OWNERS, "ARCHIVE_OWNER_UNAUTHORIZED")
    _require(isinstance(rid, str) and RESOURCE_ID.fullmatch(rid) is not None
             and isinstance(revision, str)
             and RESOURCE_ID.fullmatch(revision) is not None,
             "ARCHIVE_METADATA_INVALID")
    _require(type(captured) is int and 1 <= captured <= 9999999999999,
             "ARCHIVE_METADATA_INVALID")
    _require(isinstance(label, str) and len(label) <= 120
             and all(c.isprintable() for c in label)
             and isinstance(checksum, str)
             and HEX_DIGEST.fullmatch(checksum) is not None
             and type(size) is int and 1 <= size <= 8 * 1024 * 1024,
             "ARCHIVE_METADATA_INVALID")
    when = datetime.fromtimestamp(captured / 1000, timezone.utc)
    source_label = ("WEATHER // V2 COPY" if owner == "weather-events"
                    else "RESEARCH // V2 COPY")
    return {"id": sid, "ownerId": owner, "resourceId": rid,
            "sourceRevision": revision, "kind": "V2 SNAPSHOT",
            "source": source_label, "title": label or "UNTITLED COPY",
            "recordedAtMs": captured, "recordedAt": when.strftime("%Y-%m-%d %H:%M UTC"),
            "state": "archived-v2", "copyOnly": True, "verified": False,
            "details": f"{size} BYTES // INDEX ONLY // PAYLOAD NOT VERIFIED",
            "capabilities": {"inspect": True, "saveCopy": False,
                             "archive": False, "trash": False,
                             "restore": False, "burn": False}}


def index(directory, cursor=""):
    page_after = _cursor(cursor)
    root = _dir(directory)
    database = root / DB_NAME
    if not _private_regular(database):
        return _response([], 0, state="NOT_INSTALLED")
    # V2a deliberately uses DELETE rollback journals, not WAL. Refuse any
    # unexpected sidecar before SQLite opens the database.
    for suffix in ("-wal", "-shm"):
        try:
            (root / (DB_NAME + suffix)).lstat()
        except FileNotFoundError:
            continue
        raise ReadIndexError("ARCHIVE_UNEXPECTED_SIDECAR")
    _private_regular(root / (DB_NAME + "-journal"))
    # SQLite URI mode=ro prevents creation or modification of this database.
    # A hot rollback journal that requires write recovery fails closed.
    uri = "file:" + quote(str(database), safe="/") + "?mode=ro&cache=private"
    try:
        with sqlite3.connect(uri, uri=True, timeout=1) as db:
            db.execute("PRAGMA query_only=ON")
            db.execute("PRAGMA busy_timeout=1000")
            meta = db.execute("SELECT schema_id FROM archive_meta WHERE id=1").fetchone()
            _require(meta == (STORE_SCHEMA,), "ARCHIVE_SCHEMA_UNSUPPORTED")
            total = db.execute("SELECT count(*) FROM snapshots").fetchone()[0]
            where = "WHERE (captured_ms,id) < (?,?)" if page_after else ""
            params = (*page_after, PAGE_SIZE + 1) if page_after else (PAGE_SIZE + 1,)
            records = db.execute(
                "SELECT id,owner_id,resource_id,source_revision,captured_ms,"
                "display_label,sha256,length(payload) FROM snapshots "
                + where + " ORDER BY captured_ms DESC,id DESC LIMIT ?",
                params
            ).fetchall()
            # Refuse an entire page if a metadata row is malformed. Showing
            # only a valid subset could falsely imply an exhaustive index.
            selected = [_row(record) for record in records[:PAGE_SIZE]]
            if len(records) > PAGE_SIZE:
                # Validate the look-ahead row too so a broken next page cannot
                # be silently advertised as healthy.
                _row(records[PAGE_SIZE])
            has_more = len(records) > PAGE_SIZE
            last = selected[-1] if has_more else None
            next_cursor = (str(last["recordedAtMs"]) + ":" + last["id"]
                           if last else None)
            return _response(selected, total, next_cursor)
    except sqlite3.Error as exc:
        raise ReadIndexError("ARCHIVE_INDEX_UNAVAILABLE") from exc


def main(argv):
    try:
        if len(argv) not in (3, 4) or argv[1] != "index":
            raise ReadIndexError("READ_ONLY_INDEX_ONLY")
        result = index(argv[2], argv[3] if len(argv) == 4 else "")
    except ReadIndexError as exc:
        result = {"ok": False, "error": str(exc)}
    except Exception:
        result = {"ok": False, "error": "ARCHIVE_INDEX_FAILED"}
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
