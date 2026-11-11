#!/usr/bin/env python3
"""MACHINE // CI-ONLY crash/reply-loss journal for synthetic transfer receipts.

Stores TEST metadata only in a strictly named disposable /tmp directory.
The ephemeral fixture HMAC key is supplied by its test process, not enrolled,
independently held or installed. Neither a valid MAC nor an SQLite commit
authenticates a trusted service, a Brave client, C5 consent, or a real copy.
No interface to archives, production paths, C3e, C5, or restoration exists.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path
import sqlite3
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import MachineBraveOfflineTransferRecoveryContract as contract

KIND = "machine-fixture-recovery-journal-v1"
FILENAME = "receipt.sqlite3"
ROOT_PREFIX = "machine-ledger-ci-"
EMPTY_MAC = "0" * 64
COLUMNS = ("sequence", "plan_sha256", "record_id", "record_sha256",
           "phase", "previous_mac", "mac")


class JournalRefusal(ValueError):
    pass


def refuse():
    raise JournalRefusal("MACHINE TEST RECOVERY JOURNAL REFUSED")


def require(ok):
    if not ok:
        refuse()


def _key(key):
    require(type(key) is bytes and len(key) >= 32 and len(key) <= 64)


def _path(path, *, exists):
    """Deliberately unusable with user-selected production archive paths."""
    require(type(path) is Path and path.is_absolute()
            and path.name == FILENAME and path.parent.parent == Path("/tmp")
            and path.parent.name.startswith(ROOT_PREFIX))
    try:
        home = path.parent.lstat()
        require(stat.S_ISDIR(home.st_mode) and not path.parent.is_symlink()
                and home.st_uid == os.geteuid()
                and stat.S_IMODE(home.st_mode) == 0o700)
        try:
            info = path.lstat()
        except FileNotFoundError:
            info = None
        require((info is not None) == exists)
        if info is not None:
            require(stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid()
                    and info.st_nlink == 1 and stat.S_IMODE(info.st_mode) == 0o600)
    except (OSError, ValueError, TypeError):
        refuse()


def _open(path):
    _path(path, exists=True)
    try:
        db = sqlite3.connect(str(path), timeout=1, isolation_level=None)
        db.execute("PRAGMA busy_timeout=1000")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA trusted_schema=OFF")
        _path(path, exists=True)
        return db
    except (OSError, sqlite3.Error):
        refuse()


def _mac(key, entry):
    return hmac.new(key, contract.canonical(entry), hashlib.sha256).hexdigest()


def _anchor(sequence, mac):
    require(type(sequence) is int and sequence >= 0
            and type(mac) is str and len(mac) == 64
            and all(c in "0123456789abcdef" for c in mac))
    return {"sequence": sequence, "mac": mac}


def _check_anchor(value, expected):
    return (type(expected) is dict and set(expected) == {"sequence", "mac"}
            and type(expected["sequence"]) is int
            and type(expected["mac"]) is str
            and hmac.compare_digest(expected["mac"], value["mac"])
            and expected["sequence"] == value["sequence"])


def _verify(db, plan, key):
    proposed, _ = contract.validate_plan(plan)
    record_map = {row["record_id"]: row["sha256"] for row in proposed}
    try:
        require(db.execute("PRAGMA integrity_check").fetchone() == ("ok",))
        meta = db.execute("SELECT plan_sha256 FROM metadata").fetchall()
        require(len(meta) == 1 and meta[0] == (plan["plan_sha256"],))
        data = db.execute(
            "SELECT sequence,plan_sha256,record_id,record_sha256,"
            "phase,previous_mac,mac FROM events ORDER BY sequence").fetchall()
        require(len(data) <= 4 * len(proposed))
        phases = {}
        prior = EMPTY_MAC
        for count, values in enumerate(data, 1):
            require(len(values) == len(COLUMNS))
            item = dict(zip(COLUMNS, values))
            key_id = item["record_id"]
            require(type(item["sequence"]) is int and item["sequence"] == count)
            require(type(key_id) is str and key_id in record_map)
            require(item["record_sha256"] == record_map[key_id])
            require(item["plan_sha256"] == plan["plan_sha256"])
            require(item["previous_mac"] == prior)
            phase = item["phase"]
            require(type(phase) is str
                    and phase in contract.TRANSITIONS[phases.get(key_id)])
            signed = {name: item[name] for name in COLUMNS if name != "mac"}
            require(type(item["mac"]) is str and len(item["mac"]) == 64)
            require(hmac.compare_digest(_mac(key, signed), item["mac"]))
            prior = item["mac"]
            phases[key_id] = phase
        return _anchor(len(data), prior), phases
    except (sqlite3.Error, TypeError, KeyError, ValueError):
        refuse()


def initialize(path, plan, key):
    """Create an EMPTY disposable test ledger, never open a real archive."""
    _key(key)
    contract.validate_plan(plan)
    _path(path, exists=False)
    flags = os.O_CREAT | os.O_EXCL | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    fd = -1
    try:
        fd = os.open(path, flags, 0o600)
        os.fchmod(fd, 0o600)
    except OSError:
        refuse()
    finally:
        if fd != -1:
            os.close(fd)
    db = _open(path)
    try:
        db.execute("BEGIN IMMEDIATE")
        db.execute("CREATE TABLE metadata(plan_sha256 TEXT NOT NULL PRIMARY KEY)")
        db.execute(
            "CREATE TABLE events ("
            "sequence INTEGER PRIMARY KEY, plan_sha256 TEXT NOT NULL,"
            "record_id TEXT NOT NULL, record_sha256 TEXT NOT NULL,"
            "phase TEXT NOT NULL, previous_mac TEXT NOT NULL, mac TEXT NOT NULL)")
        db.execute("INSERT INTO metadata VALUES (?)", (plan["plan_sha256"],))
        db.execute("COMMIT")
        head, _ = _verify(db, plan, key)
        return head
    except (sqlite3.Error, JournalRefusal):
        try:
            db.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        refuse()
    finally:
        db.close()


def inspect(path, plan, key, pinned_head=None):
    """Observe DB integrity; a pinned mismatch is an explicit manual hold."""
    _key(key)
    db = _open(path)
    try:
        head, phases = _verify(db, plan, key)
    finally:
        db.close()
    pinned = pinned_head is not None
    status = ("manual_reconciliation_required" if pinned and
              not _check_anchor(head, pinned_head) else
              "fixture_pinned_head_observed" if pinned else
              "fixture_unanchored_observation")
    return {
        "kind": KIND, "status": status,
        "head": head, "phase_observations": phases,
        "plan_sha256": plan["plan_sha256"],
        "fixture_hmac_valid": True,
        "independent_floor_authenticated": False,
        "trusted_service_authenticated": False,
        "backup_verified": False,
        "operator_consent_verified": False,
        "migration_authorized": False,
        "restore_allowed": False,
        "requires_independent_human_review": True,
        "safe_actions": [],
    }


def append_fixture(path, plan, key, expected_head, record_id, phase, *,
                   crash_point=None):
    """Atomic fixture append under SQLite EXCLUSIVE writer gate.

    Internal crash points are for disposable CI child processes ONLY.
    They deliberately exit the current test process; never run on a desktop.
    """
    _key(key)
    require(crash_point in (None, "before_commit", "after_commit"))
    db = _open(path)
    try:
        db.execute("BEGIN IMMEDIATE")
        head, phases = _verify(db, plan, key)
        require(_check_anchor(head, expected_head))
        proposed, _ = contract.validate_plan(plan)
        mapping = {row["record_id"]: row["sha256"] for row in proposed}
        require(type(record_id) is str and record_id in mapping)
        require(type(phase) is str
                and phase in contract.TRANSITIONS[phases.get(record_id)])
        data = {
            "sequence": head["sequence"] + 1, "plan_sha256": plan["plan_sha256"],
            "record_id": record_id, "record_sha256": mapping[record_id],
            "phase": phase, "previous_mac": head["mac"],
        }
        mac = _mac(key, data)
        db.execute(
            "INSERT INTO events(sequence,plan_sha256,record_id,"
            "record_sha256,phase,previous_mac,mac) VALUES(?,?,?,?,?,?,?)",
            tuple(data[x] for x in COLUMNS if x != "mac") + (mac,))
        if crash_point == "before_commit":
            os._exit(91)
        db.execute("COMMIT")
        if crash_point == "after_commit":
            os._exit(92)
        return _anchor(data["sequence"], mac)
    except (sqlite3.Error, JournalRefusal, ValueError, TypeError):
        try:
            db.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        refuse()
    finally:
        db.close()


if __name__ == "__main__":
    # The only executable entrypoint is the separate synthetic test script.
    raise SystemExit(1)
