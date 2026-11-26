#!/usr/bin/env python3
"""CPU++ private, bounded, local terminal-capture archive. One framed request."""
import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import sys

SCHEMA = "post-apollo-diagnostic-archive-v1"
KINDS = {"memory", "inventory", "threads", "census", "storage", "appcontrol", "workflow"}
STATUSES = {"COMPLETE", "CANCELLED", "NOT VERIFIED"}
LIMIT = 8
MAX_FRAME = 1024 * 1024
MAX_FILE = 4 * 1024 * 1024
ID = re.compile(r"[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[1-9][0-9]*")


def validate_record(record):
    if not isinstance(record, dict) or set(record) != {"kind", "id", "status", "summary", "text", "finishedAt"}:
        raise ValueError("record shape")
    if any(not isinstance(value, str) for value in record.values()):
        raise ValueError("record types")
    if (record["kind"] not in KINDS or record["status"] not in STATUSES
            or len(record["id"]) > 128 or not ID.fullmatch(record["id"])
            or len(record["summary"]) > 4096
            or len(record["text"]) > (300000 if record["kind"] == "workflow" else 65536)
            or (record["kind"] == "workflow" and not record["text"].isascii() and record["text"] != "")
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", record["finishedAt"])):
        raise ValueError("record values")
    datetime.datetime.fromisoformat(record["finishedAt"].replace("Z", "+00:00"))
    return record


def validate_rows(rows):
    if not isinstance(rows, list) or len(rows) > LIMIT:
        raise ValueError("archive bounds")
    for record in rows:
        validate_record(record)
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("duplicate capture identity")
    return rows


def encode(value):
    return json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode("ascii")


def private_fd(fd, directory=False):
    info = os.fstat(fd)
    if (info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != (0o700 if directory else 0o600)
            or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            or (not directory and info.st_nlink != 1)):
        raise ValueError("unsafe archive ownership or type")


def open_private(directory, name, flags):
    fd = os.open(name, flags | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                 0o600, dir_fd=directory)
    try:
        private_fd(fd)
        return fd
    except BaseException:
        os.close(fd)
        raise


def read_rows(directory):
    try:
        fd = open_private(directory, "reports.json", os.O_RDONLY)
    except FileNotFoundError:
        return []
    with os.fdopen(fd, "rb") as handle:
        raw = handle.read(MAX_FILE + 1)
    if len(raw) > MAX_FILE:
        raise ValueError("archive size")
    document = json.loads(raw)
    if not isinstance(document, dict) or document.get("schema") != SCHEMA or set(document) != {"schema", "rows"}:
        raise ValueError("archive schema")
    return validate_rows(document["rows"])


def commit(directory, rows):
    raw = encode({"schema": SCHEMA, "rows": rows})
    if len(raw) > MAX_FILE:
        raise ValueError("archive size")
    # The caller holds the archive lock. Reclaim only our fixed, private
    # staging file after an interrupted save; refuse unsafe filesystem types.
    name = ".pending"
    try:
        stale = open_private(directory, name, os.O_RDONLY)
    except FileNotFoundError:
        pass
    else:
        os.close(stale)
        os.unlink(name, dir_fd=directory)
    fd = open_private(directory, name, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, "reports.json", src_dir_fd=directory, dst_dir_fd=directory)
        os.fsync(directory)
    finally:
        try:
            os.unlink(name, dir_fd=directory)
        except FileNotFoundError:
            pass


def execute(folder, request):
    if not isinstance(request, dict):
        raise ValueError("request")
    action = request.get("action")
    if action == "save" and set(request) == {"action", "record"}:
        record = validate_record(request["record"])
    elif action == "list" and set(request) == {"action"}:
        record = None
    else:
        raise ValueError("unsupported request")
    folder = Path(folder)
    if record is not None:
        folder.parent.mkdir(parents=True, exist_ok=True)
        folder.mkdir(mode=0o700, exist_ok=True)
    try:
        directory = os.open(folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except FileNotFoundError:
        if record is None:
            return {"schema": SCHEMA, "rows": [], "savedId": None}
        raise
    try:
        private_fd(directory, directory=True)
        lock = open_private(directory, "archive.lock", os.O_CREAT | os.O_RDWR)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX)
            rows = read_rows(directory)
            if record is not None:
                existing = next((row for row in rows if row["id"] == record["id"]), None)
                if existing is not None and existing != record:
                    raise ValueError("capture identity collision")
                if existing is None:
                    rows = ([record] + rows)[:LIMIT]
                    # Retain newest first; the response includes savedId as well.
                    # Limit serialized size, not just character count.
                    while len(rows)>1 and len(encode({"schema": SCHEMA, "rows": rows, "savedId": record["id"]})) >= MAX_FILE:
                        rows.pop()
                    commit(directory, rows)
            return {"schema": SCHEMA, "rows": rows,
                    "savedId": record["id"] if record is not None else None}
        finally:
            os.close(lock)
    finally:
        os.close(directory)


def state_folder():
    configured = os.environ.get("XDG_STATE_HOME")
    parent = Path(configured) if configured and Path(configured).is_absolute() else Path.home() / ".local/state"
    return parent / "post-apollo-cpuplus-diagnostics"


def main():
    os.umask(0o077)
    try:
        raw = sys.stdin.buffer.readline(MAX_FRAME + 1)
        if len(raw) > MAX_FRAME or not raw.endswith(b"\n"):
            raise ValueError("request frame")
        result = execute(state_folder(), json.loads(raw))
        sys.stdout.buffer.write(encode(result) + b"\n")
        return 0
    except (OSError, ValueError, TypeError, RecursionError):
        # No raw payloads, private paths or exception details in shell logs.
        print("Diagnostic archive unavailable.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
