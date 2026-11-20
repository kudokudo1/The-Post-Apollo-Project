#!/usr/bin/env python3
"""FinanceW FP1c: versioned operator planning drafts, never bank or identity access."""
from __future__ import annotations
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

CONTEXTS = frozenset(("mine", "shared", "mom", "granny", "family"))
MAX_BYTES = 32768
MAX_ROWS = 60
MAX_CENTS = 10_000_000_000
PREFIX = "FINANCEW_HOUSEHOLD_PLAN_"

class Refusal(Exception):
    pass

def fail(code: str):
    raise Refusal(code)

def exact(obj, keys):
    return type(obj) is dict and set(obj) == set(keys)

def valid_context(value):
    return type(value) is str and value in CONTEXTS

def parse_money(value):
    if type(value) is not str or not re.fullmatch(r"(?:0|[1-9][0-9]{0,8})(?:\.[0-9]{1,2})?", value):
        fail("INVALID_MONEY")
    a, _, b = value.partition(".")
    cents = int(a) * 100 + int(b.ljust(2, "0") or "0")
    if cents > MAX_CENTS:
        fail("MONEY_LIMIT")
    return cents

def valid_deadline(value):
    return (type(value) is str and (value == "" or
            re.fullmatch(r"(?:19|20)[0-9]{2}-(?:0[1-9]|1[0-2])", value) is not None))

def valid_row(row, version):
    fields = ("id", "kind", "title", "targetCents", "savedCents", "monthlyCents")
    if version == 2:
        fields += ("deadlineMonth",)
    if not exact(row, fields):
        return False
    if (type(row["id"]) is not str or
            re.fullmatch(r"p-[0-9a-f]{32}", row["id"]) is None or
            type(row["kind"]) is not str or
            row["kind"] not in (("goal", "expense") if version == 1
                                else ("goal", "expense", "income")) or
            type(row["title"]) is not str or
            not 1 <= len(row["title"]) <= 80 or
            row["title"] != row["title"].strip() or
            re.search(r"[\x00-\x1f\x7f]", row["title"]) is not None or
            not all(type(row[key]) is int and 0 <= row[key] <= MAX_CENTS
                    for key in ("targetCents", "savedCents", "monthlyCents"))):
        return False
    if version == 2 and (not valid_deadline(row["deadlineMonth"]) or
                         (row["kind"] != "goal" and row["deadlineMonth"] != "")):
        return False
    if row["kind"] == "goal":
        return row["targetCents"] > 0 and row["savedCents"] <= row["targetCents"]
    return row["targetCents"] == 0 and row["savedCents"] == 0 and row["monthlyCents"] > 0

def empty(context):
    if not valid_context(context):
        fail("UNKNOWN_CONTEXT")
    return {"version": 2, "contextId": context, "revision": 0, "rows": []}

def validate(doc, context):
    if not exact(doc, ("version", "contextId", "revision", "rows")):
        fail("INVALID_STORE")
    if (type(doc["version"]) is not int or doc["version"] not in (1, 2)
            or doc["contextId"] != context):
        fail("INVALID_STORE")
    if type(doc["revision"]) is not int or not 0 <= doc["revision"] < 2**53:
        fail("INVALID_STORE")
    rows = doc["rows"]
    if (type(rows) is not list or len(rows) > MAX_ROWS or
            not all(valid_row(x, doc["version"]) for x in rows)):
        fail("INVALID_STORE")
    if len({x["id"] for x in rows}) != len(rows):
        fail("INVALID_STORE")
    return doc

def upgrade_in_memory(doc):
    # v1 files stay unchanged on list; first deliberate write converts to v2.
    if doc["version"] == 2:
        return doc
    return {"version": 2, "contextId": doc["contextId"],
            "revision": doc["revision"],
            "rows": [{**row, "deadlineMonth": ""} for row in doc["rows"]]}

def directory_path():
    base = os.environ.get("XDG_DATA_HOME")
    if not base or not Path(base).is_absolute():
        base = str(Path.home() / ".local" / "share")
    return Path(base) / "post-apollo" / "finance" / "household-plans"

def private_dir(directory, create):
    if create:
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        info = directory.lstat()
    except FileNotFoundError:
        if not create:
            return False
        fail("STORE_UNAVAILABLE")
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        fail("UNSAFE_DIRECTORY")
    return True

def read_doc(directory, context):
    if not valid_context(context):
        fail("UNKNOWN_CONTEXT")
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
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_size > MAX_BYTES:
            fail("UNSAFE_RECORD")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            fail("INVALID_STORE")
        try:
            doc = json.loads(raw.decode("utf-8"))
        except (UnicodeError, ValueError):
            fail("INVALID_STORE")
        return validate(doc, context)
    finally:
        os.close(fd)

def write_doc(directory, doc):
    context = doc["contextId"]
    validate(doc, context)
    private_dir(directory, True)
    dest = directory / (context + ".json")
    temp = directory / ("." + uuid.uuid4().hex + ".tmp")
    raw = (json.dumps(doc, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
    if len(raw) > MAX_BYTES:
        fail("STORE_LIMIT")
    fd = None
    try:
        fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        os.write(fd, raw)
        os.fsync(fd)
        os.close(fd)
        fd = None
        try:
            info = dest.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                fail("UNSAFE_RECORD")
        except FileNotFoundError:
            pass
        os.replace(temp, dest)
        dfd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if fd is not None:
            os.close(fd)
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass

def normalized_row(kind, title, target_text, saved_text, monthly_text,
                   deadline_month):
    if type(kind) is not str or kind not in ("goal", "expense", "income"):
        fail("INVALID_KIND")
    if (type(title) is not str or not 1 <= len(title) <= 80 or
            title != title.strip() or
            re.search(r"[\x00-\x1f\x7f]", title) is not None):
        fail("INVALID_TITLE")
    target = parse_money(target_text)
    saved = parse_money(saved_text)
    monthly = parse_money(monthly_text)
    if not valid_deadline(deadline_month):
        fail("INVALID_DEADLINE")
    if kind == "goal":
        if target <= 0 or saved > target:
            fail("INVALID_GOAL")
    elif target or saved or not monthly or deadline_month:
        fail("INVALID_MONTHLY_ITEM")
    return {"kind": kind, "title": title, "targetCents": target,
            "savedCents": saved, "monthlyCents": monthly,
            "deadlineMonth": deadline_month}

def apply(doc, command):
    context = command.get("contextId") if type(command) is dict else None
    validate(doc, context)
    if not valid_context(context):
        fail("UNKNOWN_CONTEXT")
    action = command.get("action")
    if action == "list" and exact(command, ("action", "contextId")):
        return upgrade_in_memory(doc), False
    if action not in ("add", "update", "delete"):
        fail("INVALID_ACTION")
    if (type(command.get("expectedRevision")) is not int or
            command["expectedRevision"] != doc["revision"]):
        fail("STALE_REVISION")
    doc = upgrade_in_memory(doc)
    base = ("action", "contextId", "expectedRevision")
    if action in ("add", "update"):
        fields = ("kind", "title", "targetText", "savedText", "monthlyText")
        mandatory = base + fields + (("id",) if action == "update" else ())
        has_deadline = exact(command, mandatory + ("deadlineMonth",))
        if not has_deadline and not (action == "add" and exact(command, mandatory)):
            fail("INVALID_COMMAND")
        value = normalized_row(command["kind"], command["title"],
                               command["targetText"], command["savedText"],
                               command["monthlyText"],
                               command["deadlineMonth"] if has_deadline else "")
        if action == "add":
            if len(doc["rows"]) >= MAX_ROWS:
                fail("ROW_LIMIT")
            value["id"] = "p-" + uuid.uuid4().hex
            rows = doc["rows"] + [value]
        else:
            identifier = command["id"]
            if (type(identifier) is not str or
                    re.fullmatch(r"p-[0-9a-f]{32}", identifier) is None):
                fail("INVALID_ID")
            found = [row for row in doc["rows"] if row["id"] == identifier]
            if len(found) != 1:
                fail("NOT_FOUND")
            if value["kind"] != found[0]["kind"]:
                fail("KIND_CHANGE_REFUSED")
            value["id"] = identifier
            rows = [value if row["id"] == identifier else row for row in doc["rows"]]
    else:
        if not exact(command, base + ("id",)):
            fail("INVALID_COMMAND")
        identifier = command["id"]
        if (type(identifier) is not str or
                re.fullmatch(r"p-[0-9a-f]{32}", identifier) is None):
            fail("INVALID_ID")
        rows = [row for row in doc["rows"] if row["id"] != identifier]
        if len(rows) == len(doc["rows"]):
            fail("NOT_FOUND")
    return {"version": 2, "contextId": context,
            "revision": doc["revision"] + 1, "rows": rows}, True

def run(directory, command):
    if type(command) is not dict or not valid_context(command.get("contextId")):
        fail("INVALID_CONTEXT")
    context = command["contextId"]
    action = command.get("action")
    if action == "list":
        doc = read_doc(directory, context)
        return apply(doc, command)[0]
    if action not in ("add", "update", "delete"):
        fail("INVALID_ACTION")
    private_dir(directory, True)
    lock_path = directory / (context + ".lock")
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    except OSError:
        fail("UNSAFE_LOCK")
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            fail("UNSAFE_LOCK")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            fail("WRITE_BUSY")
        doc, dirty = apply(read_doc(directory, context), command)
        if dirty:
            write_doc(directory, doc)
        return doc
    finally:
        os.close(fd)

def main():
    raw = sys.stdin.buffer.readline(4097)
    if len(raw) > 4096 or not raw.endswith(b"\n"):
        fail("INVALID_INPUT_FRAME")
    try:
        command = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError):
        fail("INVALID_JSON")
    doc = run(directory_path(), command)
    print(PREFIX + "RESULT " + json.dumps({
        "source": "LOCAL_OPERATOR_PLANS", "identityVerified": False,
        "bankVerified": False, **doc
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
