#!/usr/bin/env python3
"""FinanceW FP1e: operator-entered schedules, no bank/Actual/identity access.

A bill record references a monthly plan expense without duplicating its cost.
A purchase is a separate dated planning payment, optionally funded from one
manual savings goal. No transfers or financial account operations are made.
"""
from __future__ import annotations

import calendar
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

CONTEXTS = frozenset(("mine", "shared", "mom", "granny", "family"))
MAX_ROWS = 60
MAX_BYTES = 32768
MAX_CENTS = 10_000_000_000
PREFIX = "FINANCEW_HOUSEHOLD_SCHEDULE_"
ID_PATTERN = r"p-[0-9a-f]{32}"

class Refusal(Exception):
    pass

def fail(reason):
    raise Refusal(reason)

def exact(value, names):
    return type(value) is dict and set(value) == set(names)

def valid_context(context):
    return type(context) is str and context in CONTEXTS

def valid_id(identifier):
    return type(identifier) is str and re.fullmatch(ID_PATTERN, identifier) is not None

def valid_title(title):
    return (type(title) is str and 1 <= len(title) <= 80
            and title == title.strip()
            and re.search(r"[\x00-\x1f\x7f]", title) is None)

def valid_date(date):
    if type(date) is not str or re.fullmatch(r"(?:19|20)\d{2}-\d{2}-\d{2}", date) is None:
        return False
    year, month, day = map(int, date.split("-"))
    if month < 1 or month > 12:
        return False
    return 1 <= day <= calendar.monthrange(year, month)[1]

def cents_of(value):
    if type(value) is not str or re.fullmatch(
            r"(?:0|[1-9][0-9]{0,8})(?:\.[0-9]{1,2})?", value) is None:
        fail("INVALID_MONEY")
    major, _, minor = value.partition(".")
    amount = int(major)*100 + int(minor.ljust(2, "0") or "0")
    if amount > MAX_CENTS:
        fail("AMOUNT_LIMIT")
    return amount

def valid_record(row):
    keys = ("id", "kind", "title", "expenseId", "dueDay", "date",
            "amountCents", "fundingGoalId")
    if not exact(row, keys) or not valid_id(row["id"]):
        return False
    if row["kind"] == "bill_due":
        return (row["title"] == "" and valid_id(row["expenseId"])
                and type(row["dueDay"]) is int and 1 <= row["dueDay"] <= 31
                and row["date"] == "" and row["amountCents"] == 0
                and row["fundingGoalId"] == "")
    if row["kind"] == "purchase":
        return (valid_title(row["title"]) and row["expenseId"] == ""
                and type(row["dueDay"]) is int and row["dueDay"] == 0
                and valid_date(row["date"])
                and type(row["amountCents"]) is int
                and 1 <= row["amountCents"] <= MAX_CENTS
                and (row["fundingGoalId"] == "" or valid_id(row["fundingGoalId"])))
    return False

def empty(context):
    if not valid_context(context):
        fail("INVALID_CONTEXT")
    return {"version": 1, "contextId": context, "revision": 0, "rows": []}

def validate(doc, context):
    if not exact(doc, ("version", "contextId", "revision", "rows")):
        fail("INVALID_STORE")
    if type(doc["version"]) is not int or doc["version"] != 1 or doc["contextId"] != context:
        fail("INVALID_STORE")
    if type(doc["revision"]) is not int or not 0 <= doc["revision"] < 2**53:
        fail("INVALID_STORE")
    rows = doc["rows"]
    if type(rows) is not list or len(rows) > MAX_ROWS or not all(valid_record(r) for r in rows):
        fail("INVALID_STORE")
    if len({r["id"] for r in rows}) != len(rows):
        fail("INVALID_STORE")
    bills = [r["expenseId"] for r in rows if r["kind"] == "bill_due"]
    if len(set(bills)) != len(bills):
        fail("INVALID_STORE")
    return doc

def directory_path():
    base = os.environ.get("XDG_DATA_HOME")
    if not base or not Path(base).is_absolute():
        base = str(Path.home() / ".local" / "share")
    return Path(base) / "post-apollo" / "finance" / "household-schedules"

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
            fail("INVALID_STORE")
        try:
            doc = json.loads(raw.decode("utf-8"))
        except (UnicodeError, ValueError):
            fail("INVALID_STORE")
        return validate(doc, context)
    finally:
        os.close(fd)

def write_doc(directory, doc):
    validate(doc, doc["contextId"])
    private_dir(directory, True)
    path = directory / (doc["contextId"] + ".json")
    temp = directory / ("." + uuid.uuid4().hex + ".tmp")
    raw = (json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    if len(raw) > MAX_BYTES:
        fail("STORE_LIMIT")
    fd = None
    try:
        fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(raw)
            stream.flush()
        os.fsync(fd)
        os.close(fd)
        fd = None
        try:
            old = path.lstat()
            if not stat.S_ISREG(old.st_mode) or old.st_uid != os.getuid() or old.st_mode & 0o077:
                fail("UNSAFE_RECORD")
        except FileNotFoundError:
            pass
        os.replace(temp, path)
        dfd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if fd is not None:
            os.close(fd)
        temp.unlink(missing_ok=True)

def apply(doc, command):
    context = command.get("contextId") if type(command) is dict else None
    validate(doc, context)
    action = command.get("action")
    if action == "list" and exact(command, ("action", "contextId")):
        return doc, False
    if action not in ("add_bill", "add_purchase", "delete"):
        fail("INVALID_ACTION")
    if (type(command.get("expectedRevision")) is not int
            or command["expectedRevision"] != doc["revision"]):
        fail("STALE_REVISION")
    base = ("action", "contextId", "expectedRevision")
    rows = list(doc["rows"])
    if action == "add_bill":
        if not exact(command, base + ("expenseId", "dueDay")):
            fail("INVALID_COMMAND")
        expense_id, due = command["expenseId"], command["dueDay"]
        if not valid_id(expense_id) or type(due) is not int or not 1 <= due <= 31:
            fail("INVALID_BILL")
        if any(r["kind"] == "bill_due" and r["expenseId"] == expense_id for r in rows):
            fail("BILL_ALREADY_SCHEDULED")
        row = {"id": "p-" + uuid.uuid4().hex, "kind": "bill_due",
               "title": "", "expenseId": expense_id, "dueDay": due,
               "date": "", "amountCents": 0, "fundingGoalId": ""}
    elif action == "add_purchase":
        if not exact(command, base + ("title", "date", "amountText", "fundingGoalId")):
            fail("INVALID_COMMAND")
        amount = cents_of(command["amountText"])
        if (not valid_title(command["title"]) or not valid_date(command["date"])
                or amount == 0 or (command["fundingGoalId"] != "" and
                                    not valid_id(command["fundingGoalId"]))):
            fail("INVALID_PURCHASE")
        row = {"id": "p-" + uuid.uuid4().hex, "kind": "purchase",
               "title": command["title"], "expenseId": "", "dueDay": 0,
               "date": command["date"], "amountCents": amount,
               "fundingGoalId": command["fundingGoalId"]}
    else:
        if not exact(command, base + ("id",)) or not valid_id(command["id"]):
            fail("INVALID_COMMAND")
        rows = [r for r in rows if r["id"] != command["id"]]
        if len(rows) == len(doc["rows"]):
            fail("NOT_FOUND")
        return {"version": 1, "contextId": context,
                "revision": doc["revision"]+1, "rows": rows}, True
    if len(rows) >= MAX_ROWS:
        fail("ROW_LIMIT")
    rows.append(row)
    return {"version": 1, "contextId": context,
            "revision": doc["revision"]+1, "rows": rows}, True

def run(directory, command):
    if type(command) is not dict or not valid_context(command.get("contextId")):
        fail("INVALID_CONTEXT")
    context = command["contextId"]
    if command.get("action") == "list":
        return apply(read_doc(directory, context), command)[0]
    if command.get("action") not in ("add_bill", "add_purchase", "delete"):
        fail("INVALID_ACTION")
    private_dir(directory, True)
    lock_file = directory / (context + ".lock")
    try:
        fd = os.open(lock_file, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
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
        result, changed = apply(read_doc(directory, context), command)
        if changed:
            write_doc(directory, result)
        return result
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
        "source": "LOCAL_OPERATOR_SCHEDULES", "bankVerified": False,
        "identityVerified": False, **doc
    }, separators=(",", ":"), ensure_ascii=False))

if __name__ == "__main__":
    try:
        main()
    except Refusal as e:
        print(PREFIX + "ERROR " + str(e), file=sys.stderr)
        raise SystemExit(1)
    except Exception:
        print(PREFIX + "ERROR OPERATION_FAILED", file=sys.stderr)
        raise SystemExit(1)
