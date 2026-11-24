#!/usr/bin/env python3
"""FinanceW Banking M4o: private, revisioned, explicit manual account snapshots.

This stores only operator-entered cash-like accounts and manual transaction
history. It is NOT an authenticated bank connection, credential store,
Actual transaction writer, payment system, or identity boundary.
"""
from __future__ import annotations

import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

PREFIX = "FINANCEW_BANKING_MANUAL_"
MAX_BYTES = 262144
MAX_ACCOUNTS = 12
MAX_ENTRIES = 300
MAX_CENTS = 999999999
MAX_ID = 1000000
MAX_REVISION = 2**53 - 1
CATALOG = {
    "cashapp": {"cash-balance"},
    "chime": {"chime-checking", "chime-savings"},
    "paypal": {"paypal-wallet"},
    "bank": {"bank-checking", "bank-savings"},
}


class Refusal(Exception):
    pass


def fail(reason: str):
    raise Refusal(reason)


def exact(value, names):
    return type(value) is dict and set(value) == set(names)


def valid_text(value, limit):
    return (type(value) is str and value == value.strip()
            and 1 <= len(value) <= limit
            and re.search(r"[\x00-\x1f\x7f]", value) is None)


def cents(value, allow_null=False):
    return ((allow_null and value is None)
            or (type(value) is int and abs(value) <= MAX_CENTS))


def ident(value, prefix):
    return (type(value) is str
            and re.fullmatch(re.escape(prefix) + r"-[1-9]\d*", value) is not None
            and int(value[len(prefix) + 1:]) < MAX_ID)


def ident_num(value):
    return int(value.rsplit("-", 1)[1])


def valid_date(value):
    if type(value) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        d = datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return 1900 <= d.year <= 2100


def empty_session():
    return {"mode": "empty", "accounts": [], "entries": [], "nextId": 1}


def validate_session(session):
    if not exact(session, ("mode", "accounts", "entries", "nextId")):
        fail("INVALID_MANUAL_SESSION")
    mode = session["mode"]
    accounts, entries, next_id = session["accounts"], session["entries"], session["nextId"]
    if (mode not in ("manual", "empty") or type(mode) is not str
            or type(accounts) is not list or len(accounts) > MAX_ACCOUNTS
            or type(entries) is not list or len(entries) > MAX_ENTRIES
            or type(next_id) is not int or not 1 <= next_id <= MAX_ID
            or (mode == "empty" and (accounts or entries))
            or (mode == "manual" and not accounts)):
        fail("INVALID_MANUAL_SESSION")
    known, names, amounts, entry_ids, pairs = {}, set(), {}, set(), {}
    max_id = 0
    for a in accounts:
        if (not exact(a, ("id", "providerId", "productId", "nickname",
                          "openingCents", "origin"))
                or not ident(a["id"], "acct")
                or a["id"] in known
                or type(a["providerId"]) is not str
                or type(a["productId"]) is not str
                or a["productId"] not in CATALOG.get(a["providerId"], set())
                or not valid_text(a["nickname"], 42)
                or not cents(a["openingCents"], True)
                or a["origin"] != "manual"):
            fail("INVALID_MANUAL_ACCOUNT")
        name_key = (a["providerId"], a["nickname"].lower())
        if name_key in names:
            fail("DUPLICATE_MANUAL_ACCOUNT")
        names.add(name_key)
        known[a["id"]] = a
        max_id = max(max_id, ident_num(a["id"]))

    for e in entries:
        basic = ("id", "accountId", "date", "description", "amountCents", "origin")
        linked = basic + ("transferId", "transferSide")
        if (not exact(e, basic) and not exact(e, linked)):
            fail("INVALID_MANUAL_ENTRY")
        if (not ident(e["id"], "entry") or e["id"] in entry_ids
                or type(e["accountId"]) is not str or e["accountId"] not in known
                or not valid_date(e["date"])
                or not valid_text(e["description"], 120)
                or not cents(e["amountCents"]) or e["amountCents"] == 0
                or e["origin"] != "manual"):
            fail("INVALID_MANUAL_ENTRY")
        entry_ids.add(e["id"])
        max_id = max(max_id, ident_num(e["id"]))
        amounts[e["accountId"]] = amounts.get(e["accountId"], 0) + e["amountCents"]
        if abs(amounts[e["accountId"]]) > MAX_CENTS:
            fail("MANUAL_AMOUNT_LIMIT")
        if "transferId" in e:
            side = e["transferSide"]
            tid = e["transferId"]
            if (not ident(tid, "transfer") or side not in ("in", "out")
                    or (side == "out" and e["amountCents"] >= 0)
                    or (side == "in" and e["amountCents"] <= 0)):
                fail("INVALID_MANUAL_TRANSFER")
            max_id = max(max_id, ident_num(tid))
            pair = pairs.setdefault(tid, {})
            if side in pair:
                fail("DUPLICATE_MANUAL_TRANSFER_LEG")
            pair[side] = e

    for tid, pair in pairs.items():
        outgoing = pair.get("out")
        incoming = pair.get("in")
        if (outgoing is None or incoming is None
                or outgoing["accountId"] == incoming["accountId"]
                or outgoing["date"] != incoming["date"]
                or outgoing["description"] != incoming["description"]
                or outgoing["amountCents"] != -incoming["amountCents"]):
            fail("BROKEN_MANUAL_TRANSFER_PAIR")
    for account_id, a in known.items():
        opening = a["openingCents"]
        if opening is not None and abs(opening + amounts.get(account_id, 0)) > MAX_CENTS:
            fail("MANUAL_BALANCE_LIMIT")
    if max_id >= next_id:
        fail("STALE_MANUAL_NEXT_ID")
    return session


def validate_doc(doc):
    if not exact(doc, ("version", "revision", "session")):
        fail("INVALID_STORE")
    if (type(doc["version"]) is not int or doc["version"] != 1
            or type(doc["revision"]) is not int
            or not 0 <= doc["revision"] < MAX_REVISION):
        fail("INVALID_STORE")
    validate_session(doc["session"])
    return doc


def empty_doc():
    return {"version": 1, "revision": 0, "session": empty_session()}


def store_dir():
    base = os.environ.get("XDG_DATA_HOME")
    if not base or not Path(base).is_absolute():
        base = str(Path.home() / ".local" / "share")
    return Path(base) / "post-apollo" / "finance" / "banking-manual"


def private_dir(directory: Path, create: bool):
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


def pairs_no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail("DUPLICATE_JSON_FIELD")
        result[key] = value
    return result


def decode(raw):
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs_no_duplicates,
                          parse_constant=lambda _: fail("INVALID_JSON"))
    except (UnicodeError, ValueError, TypeError, RecursionError):
        fail("INVALID_JSON")


def read_doc(directory: Path):
    if not private_dir(directory, False):
        return empty_doc()
    path = directory / "manual-session.json"
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return empty_doc()
    except OSError:
        fail("UNSAFE_RECORD")
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or info.st_size > MAX_BYTES):
            fail("UNSAFE_RECORD")
        with os.fdopen(fd, "rb", closefd=False) as file:
            raw = file.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            fail("STORE_LIMIT")
        return validate_doc(decode(raw))
    finally:
        os.close(fd)


def write_doc(directory: Path, doc):
    validate_doc(doc)
    private_dir(directory, True)
    path = directory / "manual-session.json"
    temp = directory / ("." + uuid.uuid4().hex + ".tmp")
    raw = (json.dumps(doc, ensure_ascii=False, separators=(",", ":"), allow_nan=False) +
           "\n").encode("utf-8")
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
            info = path.lstat()
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or info.st_mode & 0o077 or info.st_size > MAX_BYTES):
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


def run(directory: Path, command):
    if not exact(command, ("action",)) and not exact(
            command, ("action", "expectedRevision", "session")) and not exact(
            command, ("action", "expectedRevision", "confirmClear")):
        fail("INVALID_COMMAND")
    action = command["action"]
    if action == "list":
        if not exact(command, ("action",)):
            fail("INVALID_COMMAND")
        return read_doc(directory)
    if action not in ("save", "clear"):
        fail("INVALID_ACTION")
    if (type(command.get("expectedRevision")) is not int
            or command["expectedRevision"] < 0):
        fail("INVALID_REVISION")
    if action == "save":
        if not exact(command, ("action", "expectedRevision", "session")):
            fail("INVALID_COMMAND")
        session = validate_session(command["session"])
        if session["mode"] != "manual":
            fail("ONLY_MANUAL_ACCOUNTS_CAN_BE_SAVED")
    else:
        if not exact(command, ("action", "expectedRevision", "confirmClear")) or \
                command["confirmClear"] is not True:
            fail("CLEAR_CONFIRMATION_REQUIRED")
        session = empty_session()

    private_dir(directory, True)
    lock = directory / "manual-session.lock"
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
        previous = read_doc(directory)
        if previous["revision"] != command["expectedRevision"]:
            fail("STALE_REVISION")
        if action == "clear" and (previous["revision"] == 0
                                   or previous["session"]["mode"] != "manual"):
            fail("NOTHING_SAVED")
        if previous["revision"] >= MAX_REVISION - 1:
            fail("REVISION_LIMIT")
        doc = {"version": 1, "revision": previous["revision"] + 1, "session": session}
        write_doc(directory, doc)
        return doc
    finally:
        os.close(fd)


def main():
    raw = sys.stdin.buffer.readline(MAX_BYTES + 2)
    if len(raw) > MAX_BYTES + 1 or not raw.endswith(b"\n"):
        fail("INVALID_INPUT_FRAME")
    command = decode(raw)
    doc = run(store_dir(), command)
    print(PREFIX + "RESULT " + json.dumps({
        "source": "LOCAL_OPERATOR_BANKING", "bankVerified": False,
        "identityVerified": False, "connected": False,
        "savedOnDisk": doc["revision"] > 0, **doc
    }, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    try:
        main()
    except Refusal as error:
        print(PREFIX + "ERROR " + str(error), file=sys.stderr)
        raise SystemExit(1)
    except Exception:
        print(PREFIX + "ERROR OPERATION_FAILED", file=sys.stderr)
        raise SystemExit(1)
