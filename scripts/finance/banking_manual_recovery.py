#!/usr/bin/env python3
"""M4q: offline recovery of a damaged private manual Banking file.

Cooperating writers share the M4o lock. No same-UID hostile-writer protection,
bank access, automatic retry, or UI activation. Close every Banking client
before recovery; an unreadable revision cannot establish a complete history.
"""
import hashlib
import json
import os
import re
import stat
import sys
import uuid

import banking_manual_store as manual
import banking_manual_archive as archive

PREFIX = "FINANCEW_BANKING_RECOVERY_"
MAX_REVISION = 2147483646  # existing QML signed int property
MAX_QUARANTINES = 8
HEX = re.compile(r"[0-9a-f]{64}")


def fail(reason):
    raise manual.Refusal(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fingerprint(info):
    return (info.st_dev, info.st_ino, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns, info.st_mode,
            info.st_uid, info.st_nlink)


def read_private(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        fail("RECOVERY_FILE_UNAVAILABLE")
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or info.st_nlink != 1
                or info.st_size > manual.MAX_BYTES):
            fail("UNSAFE_RECOVERY_FILE")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(manual.MAX_BYTES + 1)
        if (len(raw) > manual.MAX_BYTES
                or len(raw) != info.st_size
                or fingerprint(os.fstat(fd)) != fingerprint(info)
                or fingerprint(path.lstat()) != fingerprint(info)):
            fail("RECOVERY_FILE_CHANGED")
        return raw, fingerprint(info)
    finally:
        os.close(fd)


def damaged_primary(directory):
    if not manual.private_dir(directory, False):
        fail("NO_PRIMARY_TO_RECOVER")
    raw, identity = read_private(directory / "manual-session.json")
    revision_hint = None
    try:
        doc = manual.decode(raw)
    except manual.Refusal:
        return raw, identity, revision_hint
    # Never treat a newer/unknown schema as corrupt v1 data.
    if type(doc) is dict and "version" in doc:
        if type(doc["version"]) is not int or doc["version"] != 1:
            fail("UNKNOWN_PRIMARY_VERSION")
        revision = doc.get("revision")
        if type(revision) is int and 0 <= revision < manual.MAX_REVISION:
            revision_hint = revision
    try:
        manual.validate_doc(doc)
    except (manual.Refusal, TypeError, ValueError, KeyError, OverflowError):
        return raw, identity, revision_hint
    fail("PRIMARY_IS_VALID_USE_NORMAL_RESTORE")


def selection(directory, backup_id):
    raw, identity, hint = damaged_primary(directory)
    selected = archive.load_archive(directory, backup_id)
    # Refuse unreadable archives; do not silently ignore a known revision.
    revisions = [archive.load_archive(directory, name)["document"]["revision"]
                 for name in archive.archive_names(directory)]
    floor = max([0, hint or 0] + revisions)
    return raw, identity, hint, selected, floor


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def preserve(directory, raw):
    dest = directory / "recovery-quarantine"
    manual.private_dir(dest, True)
    # Persist the newly created child directory before replacing the primary.
    sync_dir(directory)
    name = "damaged-" + sha(raw) + ".bin"
    target = dest / name
    names = []
    for entry in dest.iterdir():
        if re.fullmatch(r"damaged-[0-9a-f]{64}\.bin", entry.name):
            names.append(entry.name)
        elif not re.fullmatch(r"\.[0-9a-f]{32}\.tmp", entry.name):
            fail("UNEXPECTED_QUARANTINE_FILE")
    if name in names:
        previous, _ = read_private(target)
        if previous != raw:
            fail("QUARANTINE_MISMATCH")
        sync_dir(dest)
        return name
    if len(names) >= MAX_QUARANTINES:
        fail("QUARANTINE_LIMIT")
    temporary = dest / ("." + uuid.uuid4().hex + ".tmp")
    fd = None
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                     os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(raw)
            stream.flush()
        os.fsync(fd)
        os.close(fd)
        fd = None
        os.link(temporary, target, follow_symlinks=False)
        os.unlink(temporary)
        sync_dir(dest)
        return name
    finally:
        if fd is not None:
            os.close(fd)
        temporary.unlink(missing_ok=True)


def valid_hash(value):
    return type(value) is str and HEX.fullmatch(value) is not None


def run(directory, command):
    if manual.exact(command, ("action", "backupId")) and command["action"] == "preview":
        raw, _, hint, selected, floor = selection(directory, command["backupId"])
        return {"action": "preview", "primarySha256": sha(raw),
                "primaryBytes": len(raw), "primaryRevisionHint": hint,
                "observedRevisionFloor": floor, "backup": archive.summary(selected),
                "requiresClosedClients": True, "revisionHistoryVerified": False}
    if not manual.exact(command, ("action", "backupId", "expectedPrimarySha256",
                                  "expectedBackupSha256", "lastKnownRevision",
                                  "confirmRecovery", "confirmClientsClosed")):
        fail("INVALID_COMMAND")
    if command["action"] != "recover":
        fail("INVALID_ACTION")
    if command["confirmRecovery"] is not True or command["confirmClientsClosed"] is not True:
        fail("EXPLICIT_RECOVERY_CONFIRMATION_REQUIRED")
    if not all(valid_hash(command[key]) for key in
               ("expectedPrimarySha256", "expectedBackupSha256")):
        fail("INVALID_EXPECTED_DIGEST")
    floor = command["lastKnownRevision"]
    if type(floor) is not int or not 0 <= floor < MAX_REVISION:
        fail("INVALID_REVISION_FLOOR")
    # Missing storage is not corruption. Do not create an empty recovery root.
    if not manual.private_dir(directory, False):
        fail("NO_PRIMARY_TO_RECOVER")

    def recover():
        raw, identity, _, selected, observed = selection(directory, command["backupId"])
        if sha(raw) != command["expectedPrimarySha256"]:
            fail("STALE_PRIMARY_SELECTION")
        if selected["sha256"] != command["expectedBackupSha256"]:
            fail("STALE_BACKUP_SELECTION")
        if floor < observed:
            fail("REVISION_FLOOR_TOO_LOW")
        restored = {"version": 1, "revision": floor + 1,
                    "session": selected["document"]["session"]}
        manual.validate_doc(restored)
        name = preserve(directory, raw)
        # Keep primary in place until the original bytes are safely copied.
        # Recheck under the same lock before the atomic M4o replacement.
        latest, current_identity, _ = damaged_primary(directory)
        if latest != raw or identity != current_identity:
            fail("PRIMARY_CHANGED_AFTER_QUARANTINE")
        manual.write_doc(directory, restored)
        return {"action": "recover", "quarantineId": name,
                "primarySha256": sha(raw), "newRevision": restored["revision"],
                "backup": archive.summary(selected), "revisionHistoryVerified": False}

    return archive.with_store_lock(directory, recover)


def main():
    raw = sys.stdin.buffer.readline(4097)
    if len(raw) > 4096 or not raw.endswith(b"\n"):
        fail("INVALID_INPUT_FRAME")
    result = run(manual.store_dir(), manual.decode(raw))
    print(PREFIX + "RESULT " + json.dumps({
        "source": "LOCAL_OPERATOR_BANKING_RECOVERY",
        "connected": False, "bankVerified": False, "encrypted": False,
        **result}, separators=(",", ":")))


if __name__ == "__main__":
    try:
        main()
    except manual.Refusal as error:
        print(PREFIX + "ERROR " + str(error), file=sys.stderr)
        raise SystemExit(1)
    except Exception:
        print(PREFIX + "ERROR OPERATION_FAILED", file=sys.stderr)
        raise SystemExit(1)
