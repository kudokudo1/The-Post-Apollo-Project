#!/usr/bin/env python3
"""M11z disposable-only source backup and code-reference rollback rehearsal.

This test module has no CLI, service, Quickshell integration, production path,
or TASKS data access. All filesystem writes require explicit path segment
'm11z-synthetic-copy'. The caller-provided digest is an assertion, NOT an
independent production trust root. Existing M11l parses synthetic task schema.
"""
from __future__ import annotations

from dataclasses import dataclass
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import tempfile

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
M11L_FILE = ROOT / "services/projects/TaskJsonGateCandidateM11l.py"
_spec = importlib.util.spec_from_file_location("m11z_disposable_schema", M11L_FILE)
schema = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(schema)

FOLDER = "m11z-synthetic-copy"
SOURCE = "todo-copy.json"
BACKUP = "source-before-rollback.bak"
JOURNAL = "synthetic-quiesced-journal.json"
CURRENT = "active-code.ref"
PREVIOUS = "previous-code.ref"
LOCK = "synthetic-rollback.lock"
CODE_BEFORE = b"M11Z-SYNTHETIC-CODE-V1\n"
CODE_AFTER = b"M11Z-SYNTHETIC-CODE-V2\n"
SHA = re.compile(r"[0-9a-f]{64}\Z")


class SafetyRefusal(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise SafetyRefusal(reason)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def private_folder(folder):
    require(isinstance(folder, Path) and folder.is_absolute() and
            folder.name == FOLDER and ".." not in folder.parts,
            "SYNTHETIC_DIRECTORY_ONLY")
    try:
        meta = folder.lstat()
    except OSError:
        raise SafetyRefusal("SYNTHETIC_DIRECTORY_MISSING") from None
    require(stat.S_ISDIR(meta.st_mode) and not folder.is_symlink() and
            meta.st_uid == os.geteuid() and
            stat.S_IMODE(meta.st_mode) & 0o077 == 0,
            "SYNTHETIC_DIRECTORY_UNSAFE")
    return folder


def stable(folder, name):
    private_folder(folder)
    require(name in (SOURCE, BACKUP, JOURNAL, CURRENT, PREVIOUS, LOCK),
            "SYNTHETIC_FILE_ONLY")
    try:
        return schema.stable_source(folder / name)
    except (schema.GateError, OSError):
        raise SafetyRefusal("SYNTHETIC_FILE_UNAVAILABLE") from None


def source(folder):
    raw = stable(folder, SOURCE)
    try:
        schema.parse_task_document(raw)
    except schema.GateError:
        raise SafetyRefusal("SYNTHETIC_SCHEMA_REFUSED") from None
    return raw


def pin(expected):
    require(type(expected) is str and SHA.fullmatch(expected),
            "INDEPENDENT_DIGEST_REQUIRED")


@dataclass(frozen=True)
class BackupEvidence:
    source_hash: str
    backup_hash: str


def prepare_backup(folder, expected_source_hash, *,
                   before_write=None, before_readback=None):
    """Copy only exact pinned synthetic source into an O_EXCL private backup.

    Injection hooks are only for synthetic tests. If source moves during
    backup, refuse and preserve the newly created backup as evidence. Never
    delete it on failure or overwrite a preexisting backup.
    """
    private_folder(folder)
    pin(expected_source_hash)
    before = source(folder)
    require(digest(before) == expected_source_hash,
            "SOURCE_BASELINE_MISMATCH")
    require(not (folder / BACKUP).exists() and
            not (folder / BACKUP).is_symlink(), "BACKUP_ALREADY_EXISTS")
    if before_write is not None:
        before_write()
    require(source(folder) == before, "SOURCE_CHANGED_BEFORE_BACKUP")
    fd = -1
    try:
        fd = os.open(folder / BACKUP,
                     os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                     0o600)
        written = 0
        while written < len(before):
            chunk = os.write(fd, before[written:])
            require(chunk > 0, "BACKUP_WRITE_FAILED")
            written += chunk
        os.fsync(fd)
    except OSError:
        raise SafetyRefusal("BACKUP_WRITE_FAILED") from None
    finally:
        if fd >= 0:
            os.close(fd)
    if before_readback is not None:
        before_readback()
    observed = stable(folder, BACKUP)
    require(observed == before, "BACKUP_READBACK_MISMATCH")
    require(source(folder) == before, "SOURCE_CHANGED_DURING_BACKUP")
    dfd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)
    return BackupEvidence(expected_source_hash, digest(observed))


def journal_state(folder):
    try:
        state = json.loads(stable(folder, JOURNAL).decode("utf-8"),
                           object_pairs_hook=schema.no_duplicates)
    except (ValueError, UnicodeError, schema.GateError):
        raise SafetyRefusal("SYNTHETIC_JOURNAL_INVALID") from None
    require(type(state) is dict and set(state) ==
            {"version", "phase", "pending", "sourceHash", "backupHash"} and
            type(state["version"]) is int and state["version"] == 1 and
            type(state["phase"]) is str and state["phase"] == "QUIESCED" and
            state["pending"] is False and
            type(state["sourceHash"]) is str and SHA.fullmatch(state["sourceHash"]) and
            type(state["backupHash"]) is str and SHA.fullmatch(state["backupHash"]),
            "SYNTHETIC_JOURNAL_NOT_QUIESCED")
    return state


def _inspect(folder, backup_evidence, expected_current, expected_previous):
    private_folder(folder)
    require(isinstance(backup_evidence, BackupEvidence),
            "BACKUP_EVIDENCE_REQUIRED")
    for item in (backup_evidence.source_hash, backup_evidence.backup_hash,
                 expected_current, expected_previous):
        pin(item)
    require(backup_evidence.source_hash == backup_evidence.backup_hash,
            "BACKUP_DIGEST_DISAGREES")
    actual_source = source(folder)
    actual_backup = stable(folder, BACKUP)
    require(digest(actual_source) == backup_evidence.source_hash,
            "SOURCE_CHANGED_SINCE_PREFLIGHT")
    require(actual_backup == actual_source and
            digest(actual_backup) == backup_evidence.backup_hash,
            "BACKUP_CHANGED_SINCE_PREFLIGHT")
    journal = journal_state(folder)
    require(journal["sourceHash"] == backup_evidence.source_hash and
            journal["backupHash"] == backup_evidence.backup_hash,
            "JOURNAL_DIGEST_CONFLICT")
    active = stable(folder, CURRENT)
    previous = stable(folder, PREVIOUS)
    require(active == CODE_AFTER and digest(active) == expected_current,
            "CURRENT_CODE_CHANGED")
    require(previous == CODE_BEFORE and digest(previous) == expected_previous,
            "PREVIOUS_CODE_UNTRUSTED")
    return (actual_source, actual_backup, stable(folder, JOURNAL), active, previous)


def inspect_code_rollback(folder, evidence, expected_current, expected_previous):
    """No changes; require quiesced synthetic journal and matched source."""
    _inspect(folder, evidence, expected_current, expected_previous)
    return {"status": "SYNTHETIC_CODE_ROLLBACK_READY",
            "sourceUnchanged": True, "dataRestoreAuthorized": False,
            "productionWriterAuthorized": False}


def rollback_synthetic_code_only(folder, evidence, expected_current,
                                  expected_previous, *,
                                  approved=False, before_commit=None):
    """Only active-code.ref may change; task source, backup, journal preserved.

    This is a rehearsal in an explicitly named disposable folder. Advisory
    locking and precommit rechecks do not exclude arbitrary hostile writers.
    """
    require(approved is True, "EXPLICIT_SYNTHETIC_APPROVAL_REQUIRED")
    private_folder(folder)
    fd = -1
    tmp = None
    try:
        fd = os.open(folder / LOCK, os.O_RDONLY | os.O_NOFOLLOW)
        meta = os.fstat(fd)
        require(stat.S_ISREG(meta.st_mode) and meta.st_uid == os.geteuid() and
                meta.st_nlink == 1 and stat.S_IMODE(meta.st_mode) & 0o077 == 0,
                "UNSAFE_ROLLBACK_LOCK")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SafetyRefusal("ROLLBACK_LOCK_CONTENDED") from None
        before = _inspect(folder, evidence, expected_current, expected_previous)
        if before_commit is not None:
            before_commit()
        require(_inspect(folder, evidence, expected_current, expected_previous)
                == before, "ROLLBACK_CONCURRENT_CHANGE")
        tempfd, tmp = tempfile.mkstemp(prefix=".m11z-code-only-", dir=folder)
        try:
            os.fchmod(tempfd, 0o600)
            n = os.write(tempfd, before[4])
            require(n == len(before[4]), "ROLLBACK_CODE_WRITE_FAILED")
            os.fsync(tempfd)
        finally:
            os.close(tempfd)
        require(_inspect(folder, evidence, expected_current, expected_previous)
                == before, "ROLLBACK_CONCURRENT_CHANGE")
        os.replace(tmp, folder / CURRENT)
        tmp = None
        dirfd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
        require(stable(folder, CURRENT) == before[4], "ROLLBACK_CODE_READBACK")
        require(source(folder) == before[0] and
                stable(folder, BACKUP) == before[1] and
                stable(folder, JOURNAL) == before[2], "ROLLBACK_DATA_MODIFIED")
        return {"status": "SYNTHETIC_CODE_ONLY_ROLLED_BACK",
                "sourceUnchanged": True, "journalUnchanged": True,
                "backupUnchanged": True, "dataRestoreAuthorized": False,
                "productionWriterAuthorized": False}
    except OSError:
        raise SafetyRefusal("SYNTHETIC_ROLLBACK_UNAVAILABLE") from None
    finally:
        if tmp is not None:
            os.unlink(tmp)
        if fd >= 0:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
