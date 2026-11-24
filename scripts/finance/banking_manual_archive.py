#!/usr/bin/env python3
"""Banking M4p // Explicit, private backup/inspect/restore of manual snapshots.

No arbitrary paths, automatic background copies, bank data, network calls,
Actual writers, credentials, or multi-person authorization. Backup contents
are sensitive PLAINTEXT protected by the local Linux account's file mode,
NOT encrypted, signed, or provider verified.
"""
from __future__ import annotations

import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

import banking_manual_store as manual

PREFIX = "FINANCEW_BANKING_BACKUP_"
ARCHIVE_VERSION = 1
MAX_BACKUPS = 8
MAX_ARCHIVE_BYTES = manual.MAX_BYTES + 2048
NAME_PATTERN = re.compile(r"^backup-([0-9a-f]{32})\.json$")


def refuse(code):
    raise manual.Refusal(code)


def compact(document):
    return json.dumps(document, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(document):
    return hashlib.sha256(compact(document)).hexdigest()


def backup_dir(directory):
    return directory / "backups"


def valid_backup_id(identifier):
    return type(identifier) is str and NAME_PATTERN.fullmatch(identifier) is not None


def validate_archive(archive, identifier):
    if not manual.exact(archive, ("archiveVersion", "backupId", "createdUtc",
                                  "document", "sha256")):
        refuse("INVALID_BACKUP")
    if (archive["archiveVersion"] != ARCHIVE_VERSION
            or type(archive["archiveVersion"]) is not int
            or archive["backupId"] != identifier
            or type(archive["createdUtc"]) is not str
            or re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
                            archive["createdUtc"]) is None):
        refuse("INVALID_BACKUP")
    try:
        moment = datetime.datetime.strptime(archive["createdUtc"],
                                             "%Y-%m-%dT%H:%M:%SZ")
        if moment.year < 2020 or moment.year > 2100:
            refuse("INVALID_BACKUP")
    except ValueError:
        refuse("INVALID_BACKUP")
    doc = manual.validate_doc(archive["document"])
    if doc["revision"] < 1 or doc["session"]["mode"] != "manual":
        refuse("BACKUP_MUST_BE_SAVED_MANUAL")
    if (type(archive["sha256"]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", archive["sha256"]) is None
            or digest(doc) != archive["sha256"]):
        refuse("BACKUP_CHECKSUM_MISMATCH")
    return archive


def archive_names(directory):
    if not manual.private_dir(directory, False):
        return []
    target = backup_dir(directory)
    if not manual.private_dir(target, False):
        return []
    names = []
    with os.scandir(target) as entries:
        for entry in entries:
            # Crash-interrupted precommit temporary files are ignored, never
            # treated as restorable backup records.
            if entry.name.startswith(".") and entry.name.endswith(".tmp"):
                continue
            if not valid_backup_id(entry.name):
                refuse("UNEXPECTED_BACKUP_FILE")
            names.append(entry.name)
            if len(names) > MAX_BACKUPS:
                refuse("BACKUP_LIMIT")
    return sorted(names)


def load_archive(directory, identifier):
    if not valid_backup_id(identifier):
        refuse("INVALID_BACKUP_ID")
    if identifier not in archive_names(directory):
        refuse("BACKUP_NOT_FOUND")
    path = backup_dir(directory) / identifier
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        refuse("UNSAFE_BACKUP")
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or info.st_size > MAX_ARCHIVE_BYTES):
            refuse("UNSAFE_BACKUP")
        with os.fdopen(fd, "rb", closefd=False) as file:
            raw = file.read(MAX_ARCHIVE_BYTES + 1)
        if len(raw) > MAX_ARCHIVE_BYTES:
            refuse("BACKUP_LIMIT")
        return validate_archive(manual.decode(raw), identifier)
    finally:
        os.close(fd)


def summary(archive):
    doc = archive["document"]
    return {"backupId": archive["backupId"], "createdUtc": archive["createdUtc"],
            "sourceRevision": doc["revision"], "sha256": archive["sha256"],
            "accountCount": len(doc["session"]["accounts"]),
            "entryCount": len(doc["session"]["entries"]),
            "connected": False, "bankVerified": False, "encrypted": False}


def store_new_archive(directory, archive):
    manual.private_dir(directory, True)
    dest = backup_dir(directory)
    manual.private_dir(dest, True)
    names = archive_names(directory)
    if len(names) >= MAX_BACKUPS:
        refuse("BACKUP_LIMIT")
    identity = archive["backupId"]
    validate_archive(archive, identity)
    final = dest / identity
    temporary = dest / ("." + uuid.uuid4().hex + ".tmp")
    raw = compact(archive) + b"\n"
    if len(raw) > MAX_ARCHIVE_BYTES:
        refuse("BACKUP_LIMIT")
    fd = None
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                     os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb", closefd=False) as file:
            file.write(raw)
            file.flush()
        os.fsync(fd)
        os.close(fd)
        fd = None
        # Hard-link creation is atomic and refuses overwriting an existing
        # name. A crash before link does not expose a partial backup.
        os.link(temporary, final, follow_symlinks=False)
        os.unlink(temporary)
        dfd = os.open(dest, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if fd is not None:
            os.close(fd)
        temporary.unlink(missing_ok=True)


def with_store_lock(directory, action):
    manual.private_dir(directory, True)
    lock = directory / "manual-session.lock"
    try:
        fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    except OSError:
        refuse("UNSAFE_LOCK")
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077):
            refuse("UNSAFE_LOCK")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            refuse("WRITE_BUSY")
        return action()
    finally:
        os.close(fd)


def run(directory, command):
    if type(command) is not dict or type(command.get("action")) is not str:
        refuse("INVALID_COMMAND")
    action = command["action"]
    if action == "list" and manual.exact(command, ("action",)):
        return {"action": "list",
                "backups": [summary(load_archive(directory, i))
                            for i in archive_names(directory)]}
    if action == "inspect" and manual.exact(command, ("action", "backupId")):
        return {"action": "inspect",
                "backup": summary(load_archive(directory, command["backupId"]))}
    if action == "create" and manual.exact(command, ("action", "expectedRevision",
                                                      "confirmBackup")):
        if command["confirmBackup"] is not True:
            refuse("CONFIRM_BACKUP_REQUIRED")
        if type(command["expectedRevision"]) is not int or \
                command["expectedRevision"] < 1:
            refuse("INVALID_REVISION")
        def create():
            doc = manual.read_doc(directory)
            if doc["revision"] != command["expectedRevision"]:
                refuse("STALE_REVISION")
            if doc["session"]["mode"] != "manual":
                refuse("ONLY_SAVED_MANUAL_CAN_BACKUP")
            identity = "backup-" + uuid.uuid4().hex + ".json"
            archive = {
                "archiveVersion": ARCHIVE_VERSION,
                "backupId": identity,
                "createdUtc": datetime.datetime.now(datetime.timezone.utc)
                    .strftime("%Y-%m-%dT%H:%M:%SZ"),
                "document": doc,
                "sha256": digest(doc)}
            store_new_archive(directory, archive)
            return {"action": "create", "backup": summary(archive)}
        return with_store_lock(directory, create)
    if action == "restore" and manual.exact(
            command, ("action", "backupId", "expectedRevision",
                      "expectedBackupSha256", "confirmRestore")):
        if command["confirmRestore"] is not True:
            refuse("CONFIRM_RESTORE_REQUIRED")
        if type(command["expectedRevision"]) is not int or \
                command["expectedRevision"] < 0:
            refuse("INVALID_REVISION")
        if (type(command["expectedBackupSha256"]) is not str
                or re.fullmatch(r"[0-9a-f]{64}", command["expectedBackupSha256"]) is None):
            refuse("INVALID_EXPECTED_BACKUP_DIGEST")
        def restore():
            current = manual.read_doc(directory)
            if current["revision"] != command["expectedRevision"]:
                refuse("STALE_REVISION")
            archive = load_archive(directory, command["backupId"])
            if archive["sha256"] != command["expectedBackupSha256"]:
                refuse("STALE_BACKUP_SELECTION")
            if current["revision"] >= manual.MAX_REVISION - 1:
                refuse("REVISION_LIMIT")
            restored = {"version": 1, "revision": current["revision"] + 1,
                        "session": archive["document"]["session"]}
            manual.write_doc(directory, restored)
            return {"action": "restore", "backup": summary(archive),
                    "newRevision": restored["revision"], "restored": True}
        return with_store_lock(directory, restore)
    if action == "delete" and manual.exact(
            command, ("action", "backupId", "expectedBackupSha256", "confirmDelete")):
        if command["confirmDelete"] is not True:
            refuse("CONFIRM_DELETE_REQUIRED")
        if type(command["expectedBackupSha256"]) is not str:
            refuse("INVALID_EXPECTED_BACKUP_DIGEST")
        def delete():
            archive = load_archive(directory, command["backupId"])
            if archive["sha256"] != command["expectedBackupSha256"]:
                refuse("STALE_BACKUP_SELECTION")
            target = backup_dir(directory)
            os.unlink(target / command["backupId"])
            fd = os.open(target, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
            return {"action": "delete", "backupId": command["backupId"],
                    "deleted": True}
        return with_store_lock(directory, delete)
    refuse("INVALID_ACTION_OR_FIELDS")


def main():
    raw = sys.stdin.buffer.readline(4097)
    if len(raw) > 4096 or not raw.endswith(b"\n"):
        refuse("INVALID_INPUT_FRAME")
    result = run(manual.store_dir(), manual.decode(raw))
    print(PREFIX + "RESULT " + json.dumps({
        "source": "LOCAL_OPERATOR_BANKING_BACKUP",
        "bankVerified": False, "connected": False, "encrypted": False,
        **result
    }, separators=(",", ":"), ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except manual.Refusal as error:
        print(PREFIX + "ERROR " + str(error), file=sys.stderr)
        raise SystemExit(1)
    except Exception:
        print(PREFIX + "ERROR OPERATION_FAILED", file=sys.stderr)
        raise SystemExit(1)
