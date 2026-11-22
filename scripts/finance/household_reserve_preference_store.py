#!/usr/bin/env python3
"""FinanceW FP1k: manual reserve-cushion preferences, no financial data access.

One document per existing local planning context. Context labels are NOT
separately authenticated identities. No bank, Actual, Social or Connections IO.
"""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import stat
import sys
import uuid

CONTEXTS = frozenset(("mine", "shared", "mom", "granny", "family"))
PERCENTAGES = frozenset((100, 110, 125))
PREFIX = "FINANCEW_RESERVE_PREF_"
MAX_BYTES = 1024
MAX_REVISION = 2**53 - 1

class Refusal(Exception):
    pass

def fail(code):
    raise Refusal(code)

def exact(value, keys):
    return type(value) is dict and set(value) == set(keys)

def valid_context(value):
    return type(value) is str and value in CONTEXTS

def directory_path():
    base = os.environ.get("XDG_DATA_HOME")
    if not base or not Path(base).is_absolute():
        base = str(Path.home() / ".local" / "share")
    return Path(base) / "post-apollo" / "finance" / "household-reserve-preferences"

def private_dir(directory, create):
    if create:
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        info = directory.lstat()
    except FileNotFoundError:
        if not create:
            return False
        fail("STORE_UNAVAILABLE")
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o077):
        fail("UNSAFE_DIRECTORY")
    return True

def empty(context):
    if not valid_context(context):
        fail("INVALID_CONTEXT")
    return {"version": 1, "contextId": context,
            "revision": 0, "marginPercent": 100}

def validate(doc, context):
    if not exact(doc, ("version", "contextId", "revision", "marginPercent")):
        fail("INVALID_STORE")
    if (type(doc["version"]) is not int or doc["version"] != 1
            or doc["contextId"] != context
            or type(doc["revision"]) is not int
            or not 0 <= doc["revision"] < MAX_REVISION
            or type(doc["marginPercent"]) is not int
            or doc["marginPercent"] not in PERCENTAGES):
        fail("INVALID_STORE")
    return doc

def read_doc(directory, context):
    if not valid_context(context):
        fail("INVALID_CONTEXT")
    if not private_dir(directory, False):
        return empty(context)
    path = directory / (context + ".json")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return empty(context)
    except OSError:
        fail("UNSAFE_RECORD")
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or info.st_size > MAX_BYTES):
            fail("UNSAFE_RECORD")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            fail("STORE_LIMIT")
        try:
            doc = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeError):
            fail("INVALID_STORE")
        saved = validate(doc, context)
        # A version 1 on-disk record can only be created by an explicit
        # revisioned SAVE or RESET. Revision zero is reserved for the
        # synthetic missing-file default; refuse forged/partial records.
        if saved["revision"] == 0:
            fail("INVALID_STORE")
        return saved
    finally:
        os.close(fd)

def write_doc(directory, doc):
    validate(doc, doc["contextId"])
    private_dir(directory, True)
    path = directory / (doc["contextId"] + ".json")
    raw = (json.dumps(doc, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
    if len(raw) > MAX_BYTES:
        fail("STORE_LIMIT")
    tmp = directory / ("." + uuid.uuid4().hex + ".tmp")
    fd = None
    try:
        fd = os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        os.write(fd, raw)
        os.fsync(fd)
        os.close(fd)
        fd = None
        try:
            info = path.lstat()
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or info.st_mode & 0o077):
                fail("UNSAFE_RECORD")
        except FileNotFoundError:
            pass
        os.replace(tmp, path)
        dfd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if fd is not None:
            os.close(fd)
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass

def apply(doc, command):
    context = command.get("contextId") if type(command) is dict else None
    validate(doc, context)
    action = command.get("action")
    if action == "list" and exact(command, ("action", "contextId")):
        return doc, False
    if action not in ("save", "reset"):
        fail("INVALID_ACTION")
    if (type(command.get("expectedRevision")) is not int
            or command["expectedRevision"] != doc["revision"]):
        fail("STALE_REVISION")
    if action == "save":
        if not exact(command, ("action", "contextId", "expectedRevision", "marginPercent")):
            fail("INVALID_COMMAND")
        percent = command["marginPercent"]
        if type(percent) is not int or percent not in PERCENTAGES:
            fail("INVALID_PERCENT")
    else:
        if not exact(command, ("action", "contextId", "expectedRevision")):
            fail("INVALID_COMMAND")
        percent = 100
    if doc["revision"] >= MAX_REVISION - 1:
        fail("REVISION_LIMIT")
    return {"version": 1, "contextId": context,
            "revision": doc["revision"] + 1,
            "marginPercent": percent}, True

def run(directory, command):
    if type(command) is not dict or not valid_context(command.get("contextId")):
        fail("INVALID_CONTEXT")
    context = command["contextId"]
    if command.get("action") == "list":
        return apply(read_doc(directory, context), command)[0]
    if command.get("action") not in ("save", "reset"):
        fail("INVALID_ACTION")
    private_dir(directory, True)
    lock = directory / (context + ".lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    except OSError:
        fail("UNSAFE_LOCK")
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077):
            fail("UNSAFE_LOCK")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            fail("WRITE_BUSY")
        new, dirty = apply(read_doc(directory, context), command)
        if dirty:
            write_doc(directory, new)
        return new
    finally:
        os.close(fd)

def main():
    raw = sys.stdin.buffer.readline(4097)
    if len(raw) > 4096 or not raw.endswith(b"\n"):
        fail("INVALID_INPUT_FRAME")
    try:
        command = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError):
        fail("INVALID_JSON")
    doc = run(directory_path(), command)
    print(PREFIX + "RESULT " + json.dumps({
        "source": "LOCAL_OPERATOR_RESERVE_PREFS",
        "identityVerified": False, "bankVerified": False,
        # Presentation provenance only. This is NOT written into the v1 file.
        "savedOnDisk": doc["revision"] > 0,
        **doc
    }, separators=(",", ":"), ensure_ascii=False))

if __name__ == "__main__":
    try:
        main()
    except Refusal as error:
        print(PREFIX + "ERROR " + str(error), file=sys.stderr)
        raise SystemExit(1)
    except Exception:
        print(PREFIX + "ERROR OPERATION_FAILED", file=sys.stderr)
        raise SystemExit(1)
