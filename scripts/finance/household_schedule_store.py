#!/usr/bin/env python3
"""FinanceW FP1g: versioned schedules with optional explicit deferred bill payment, no bank/Actual/identity access.

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

def valid_month(value):
    return (type(value) is str and
            re.fullmatch(r"(?:19|20)\d{2}-(?:0[1-9]|1[0-2])", value) is not None)

def valid_record(row, version):
    keys = ("id", "kind", "title", "expenseId", "dueDay", "date",
            "amountCents", "fundingGoalId")
    if version == 3:
        keys += ("sourceMonth",)
    if not exact(row, keys) or not valid_id(row["id"]):
        return False
    if version == 3 and (type(row["sourceMonth"]) is not str or
            (row["kind"] != "bill_defer" and row["sourceMonth"] != "")):
        return False
    if version == 3 and row["kind"] == "bill_defer":
        return (row["title"] == "" and valid_id(row["expenseId"])
                and type(row["dueDay"]) is int and row["dueDay"] == 0
                and valid_month(row["sourceMonth"]) and valid_date(row["date"])
                and row["date"][:7] > row["sourceMonth"]
                and type(row["amountCents"]) is int and row["amountCents"] == 0
                and row["fundingGoalId"] == "")
    if row["kind"] == "bill_due":
        return (row["title"] == "" and valid_id(row["expenseId"])
                and type(row["dueDay"]) is int and 1 <= row["dueDay"] <= 31
                and row["date"] == "" and type(row["amountCents"]) is int
                and row["amountCents"] == 0 and row["fundingGoalId"] == "")
    if row["kind"] == "purchase":
        return (valid_title(row["title"]) and row["expenseId"] == ""
                and type(row["dueDay"]) is int and row["dueDay"] == 0
                and valid_date(row["date"])
                and type(row["amountCents"]) is int
                and 1 <= row["amountCents"] <= MAX_CENTS
                and (row["fundingGoalId"] == "" or valid_id(row["fundingGoalId"])))
    if version in (2, 3) and row["kind"] == "bill_skip":
        return (row["title"] == "" and valid_id(row["expenseId"])
                and type(row["dueDay"]) is int and row["dueDay"] == 0
                and valid_month(row["date"]) and type(row["amountCents"]) is int
                and row["amountCents"] == 0 and row["fundingGoalId"] == "")
    return False

def empty(context):
    if not valid_context(context):
        fail("INVALID_CONTEXT")
    return {"version": 2, "contextId": context, "revision": 0, "rows": []}

def validate(doc, context):
    if not exact(doc, ("version", "contextId", "revision", "rows")):
        fail("INVALID_STORE")
    if (type(doc["version"]) is not int or doc["version"] not in (1, 2, 3)
            or doc["contextId"] != context):
        fail("INVALID_STORE")
    if type(doc["revision"]) is not int or not 0 <= doc["revision"] < 2**53:
        fail("INVALID_STORE")
    rows = doc["rows"]
    if (type(rows) is not list or len(rows) > MAX_ROWS
            or not all(valid_record(row, doc["version"]) for row in rows)):
        fail("INVALID_STORE")
    if len({r["id"] for r in rows}) != len(rows):
        fail("INVALID_STORE")
    bills = [r["expenseId"] for r in rows if r["kind"] == "bill_due"]
    if len(set(bills)) != len(bills):
        fail("INVALID_STORE")
    skips = [(r["expenseId"], r["date"])
             for r in rows if r["kind"] == "bill_skip"]
    if len(set(skips)) != len(skips) or any(expense not in bills for expense, _ in skips):
        fail("INVALID_STORE")
    defers = [(r["expenseId"], r["sourceMonth"])
              for r in rows if r["kind"] == "bill_defer"]
    if (len(set(defers)) != len(defers)
            or any(expense not in bills for expense, _ in defers)
            or any(pair in skips for pair in defers)):
        fail("INVALID_STORE")
    return doc

def upgrade_in_memory(doc):
    # Reading an FP1e v1 schedule never rewrites it.
    return doc if doc["version"] in (2, 3) else {
        "version": 2, "contextId": doc["contextId"],
        "revision": doc["revision"], "rows": list(doc["rows"])
    }

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

def make_bill(expense, due):
    if not valid_id(expense) or type(due) is not int or not 1 <= due <= 31:
        fail("INVALID_BILL")
    return {"kind": "bill_due", "title": "", "expenseId": expense,
            "dueDay": due, "date": "", "amountCents": 0, "fundingGoalId": ""}

def make_purchase(title, date, amount_text, goal):
    amount = cents_of(amount_text)
    if (not valid_title(title) or not valid_date(date) or not amount
            or type(goal) is not str or (goal != "" and not valid_id(goal))):
        fail("INVALID_PURCHASE")
    return {"kind": "purchase", "title": title, "expenseId": "",
            "dueDay": 0, "date": date, "amountCents": amount,
            "fundingGoalId": goal}

def make_skip(expense, month):
    if not valid_id(expense) or not valid_month(month):
        fail("INVALID_EXCEPTION")
    return {"kind": "bill_skip", "title": "", "expenseId": expense,
            "dueDay": 0, "date": month, "amountCents": 0, "fundingGoalId": ""}

def make_defer(expense, source_month, target_date):
    if (not valid_id(expense) or not valid_month(source_month)
            or not valid_date(target_date) or target_date[:7] <= source_month):
        fail("INVALID_DEFERRAL")
    return {"kind": "bill_defer", "title": "", "expenseId": expense,
            "dueDay": 0, "date": target_date, "amountCents": 0,
            "fundingGoalId": "", "sourceMonth": source_month}

def apply(doc, command):
    context = command.get("contextId") if type(command) is dict else None
    validate(doc, context)
    action = command.get("action")
    if action == "list" and exact(command, ("action", "contextId")):
        return upgrade_in_memory(doc), False
    choices = ("add_bill", "add_purchase", "add_skip", "add_defer",
               "update_bill", "update_purchase", "update_skip",
               "update_defer", "delete")
    if action not in choices:
        fail("INVALID_ACTION")
    if (type(command.get("expectedRevision")) is not int
            or command["expectedRevision"] != doc["revision"]):
        fail("STALE_REVISION")
    doc = upgrade_in_memory(doc)
    if action in ("add_defer", "update_defer") and doc["version"] != 3:
        doc = {"version": 3, "contextId": doc["contextId"],
               "revision": doc["revision"],
               "rows": [{**row, "sourceMonth": ""} for row in doc["rows"]]}
    base = ("action", "contextId", "expectedRevision")
    rows = list(doc["rows"])
    kind = ("bill_due" if action.endswith("bill") else
            "bill_skip" if action.endswith("skip") else
            "bill_defer" if action.endswith("defer") else "purchase")
    if action in ("add_bill", "update_bill"):
        expected = base + (("id",) if action.startswith("update") else ()) + ("expenseId", "dueDay")
        if not exact(command, expected):
            fail("INVALID_COMMAND")
        record = make_bill(command["expenseId"], command["dueDay"])
    elif action in ("add_purchase", "update_purchase"):
        expected = base + (("id",) if action.startswith("update") else ()) + (
            "title", "date", "amountText", "fundingGoalId")
        if not exact(command, expected):
            fail("INVALID_COMMAND")
        record = make_purchase(command["title"], command["date"],
                               command["amountText"], command["fundingGoalId"])
    elif action in ("add_skip", "update_skip"):
        expected = base + (("id",) if action.startswith("update") else ()) + ("expenseId", "month")
        if not exact(command, expected):
            fail("INVALID_COMMAND")
        record = make_skip(command["expenseId"], command["month"])
    elif action in ("add_defer", "update_defer"):
        expected = base + (("id",) if action.startswith("update") else ()) + (
            "expenseId", "sourceMonth", "targetDate")
        if not exact(command, expected):
            fail("INVALID_COMMAND")
        record = make_defer(command["expenseId"], command["sourceMonth"],
                            command["targetDate"])
    else:
        if not exact(command, base + ("id",)) or not valid_id(command["id"]):
            fail("INVALID_COMMAND")
        found = [r for r in rows if r["id"] == command["id"]]
        if len(found) != 1:
            fail("NOT_FOUND")
        if (found[0]["kind"] == "bill_due" and any(
                r["kind"] in ("bill_skip", "bill_defer") and
                r["expenseId"] == found[0]["expenseId"] for r in rows)):
            fail("BILL_HAS_EXCEPTIONS")
        rows = [r for r in rows if r["id"] != command["id"]]
        next_doc = {"version": doc["version"], "contextId": context,
                    "revision": doc["revision"]+1, "rows": rows}
        validate(next_doc, context)
        return next_doc, True
    if doc["version"] == 3 and kind != "bill_defer":
        record["sourceMonth"] = ""
    if action.startswith("update"):
        if not valid_id(command["id"]):
            fail("INVALID_ID")
        found = [r for r in rows if r["id"] == command["id"]]
        if len(found) != 1:
            fail("NOT_FOUND")
        if found[0]["kind"] != kind:
            fail("KIND_CHANGE_REFUSED")
        if (kind == "bill_due" and record["expenseId"] != found[0]["expenseId"]
                and any(r["kind"] in ("bill_skip", "bill_defer")
                        and r["expenseId"] == found[0]["expenseId"] for r in rows)):
            fail("BILL_HAS_EXCEPTIONS")
        record["id"] = command["id"]
        rows = [record if r["id"] == command["id"] else r for r in rows]
    else:
        if len(rows) >= MAX_ROWS:
            fail("ROW_LIMIT")
        record["id"] = "p-" + uuid.uuid4().hex
        rows.append(record)
    next_doc = {"version": doc["version"], "contextId": context,
                "revision": doc["revision"]+1, "rows": rows}
    # This validation rejects duplicate bill schedules, duplicate skip months,
    # and skipping a bill absent from this same local context.
    validate(next_doc, context)
    return next_doc, True

def run(directory, command):
    if type(command) is not dict or not valid_context(command.get("contextId")):
        fail("INVALID_CONTEXT")
    context = command["contextId"]
    if command.get("action") == "list":
        return apply(read_doc(directory, context), command)[0]
    if command.get("action") not in ("add_bill", "add_purchase", "add_skip",
                                   "add_defer", "update_bill", "update_purchase",
                                   "update_skip", "update_defer", "delete"):
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
