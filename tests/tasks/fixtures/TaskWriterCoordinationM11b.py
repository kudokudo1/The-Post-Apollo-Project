#!/usr/bin/env python3
"""M11b disposable coordination of simulated FileView saves and OS-flock owner.

No production TASKS DB/JSON, no CLI, no Quickshell mounting, no actual
save/migration, no rearm, no SQLite task writes, no GitHub transport.
Uses the existing M10p authority fixture for its real test-only durable lock.
An explicitly private directory may contain only the synthetic
handoff-test.db and legacy-test.json that this coordinator may read.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parents[3]
AUTH_FILE = ROOT / "tests/tasks/fixtures/TaskSqliteWriterAuthorityFixture.py"
_spec = importlib.util.spec_from_file_location("m11b_existing_authority", AUTH_FILE)
authority_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(authority_module)
AdmissionError = authority_module.AdmissionError

MAX_SOURCE = 1048576


def _safe_source(db: Path):
    if (not isinstance(db, Path) or not db.is_absolute()
            or db.name != "handoff-test.db"):
        raise AdmissionError("EXPLICIT_TEST_DB_REQUIRED")
    source = db.parent / "legacy-test.json"
    try:
        metadata = source.lstat()
    except FileNotFoundError as exc:
        raise AdmissionError("TEST_SOURCE_MISSING") from exc
    if (source.is_symlink() or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) & 0o077
            or metadata.st_size < 1 or metadata.st_size > MAX_SOURCE
            or metadata.st_nlink != 1):
        raise AdmissionError("UNSAFE_TEST_SOURCE")
    return source


def _read_exact(source: Path):
    # Open through O_NOFOLLOW and confirm inode/metadata again through fd.
    before = source.lstat()
    fd = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        meta = os.fstat(fd)
        if (not stat.S_ISREG(meta.st_mode) or meta.st_uid != os.geteuid()
                or stat.S_IMODE(meta.st_mode) & 0o077
                or meta.st_nlink != 1
                or (meta.st_dev, meta.st_ino) != (before.st_dev, before.st_ino)
                or not 0 < meta.st_size <= MAX_SOURCE):
            raise AdmissionError("SOURCE_REPLACED_OR_UNSAFE")
        content = os.read(fd, MAX_SOURCE + 1)
        after = os.fstat(fd)
        if (not content or len(content) > MAX_SOURCE
                or len(content) != meta.st_size
                or (after.st_dev, after.st_ino, after.st_mtime_ns,
                    after.st_ctime_ns, after.st_size)
                != (meta.st_dev, meta.st_ino, meta.st_mtime_ns,
                    meta.st_ctime_ns, meta.st_size)):
            raise AdmissionError("SOURCE_CHANGED_DURING_READ")
    finally:
        os.close(fd)
    latest = source.lstat()
    if (latest.st_dev, latest.st_ino) != (before.st_dev, before.st_ino):
        raise AdmissionError("SOURCE_PATH_REPLACED")
    return content


class Coordinator:
    """Lifetime-bound test-only facade, not an actual FileView stage gate.

    All stage/freeze/settle events pass through M10p's durable authority.
    On a restart, the existing authority forces RECOVERY_REVIEW.
    """

    def __init__(self, db: Path, owner: str, *, bootstrap=False):
        if not isinstance(db, Path):
            raise AdmissionError("EXPLICIT_TEST_DB_REQUIRED")
        # _safe_source performs a strict fixture-only name/security check.
        self._source = _safe_source(db)
        self._owner = authority_module.Authority(db, owner, bootstrap=bootstrap)
        self._closed = False

    def inspect(self):
        state = self._owner.snapshot()
        return {
            "phase": state["phase"], "epoch": state["epoch"],
            "pendingStage": state["pendingStage"],
            "sourceHash": state["sourceHash"],
            "simulatedJsonStagePermitted": state["simulatedJsonStagePermitted"],
            "legacyWriterEnforced": False,
            "sqliteWriteAuthorized": False,
            "remoteWriteAuthorized": False,
            "liveChangePerformed": False,
        }

    def simulated_stage(self, stage_id: str):
        self._owner.admit_stage(stage_id)
        return self.inspect()

    def freeze(self, expected_epoch: int):
        self._owner.freeze(expected_epoch)
        return self.inspect()

    def simulated_callback(self, stage_id: str, saved: bool):
        self._owner.settle_stage(stage_id, saved=saved)
        return self.inspect()

    def review_source_drain(self, *, between_reads=None):
        state = self._owner.snapshot()
        if state["phase"] != "FREEZE_REQUESTED":
            raise AdmissionError("FREEZE_NOT_REQUESTED")
        if state["pendingStage"] is not None:
            raise AdmissionError("SAVE_NOT_DRAINED")
        first = _read_exact(self._source)
        # Only used by isolated tests to model a competing filesystem write.
        if between_reads is not None:
            between_reads()
        second = _read_exact(self._source)
        if first != second:
            raise AdmissionError("SOURCE_READBACK_MISMATCH")
        # The actual durable authority independently rechecks freeze/pending,
        # and records the test-only hash in a single SQLite transaction.
        self._owner.record_quiescence(first, second)
        confirmed = self.inspect()
        assert confirmed["phase"] == "JSON_QUIESCED"
        assert confirmed["sourceHash"] == hashlib.sha256(first).hexdigest()
        # A hypothetical writer cannot be admitted after quiescence; still
        # no real FileView or SQLite write authorization.
        return confirmed

    def close(self):
        if self._closed:
            return
        self._closed = True
        self._owner.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
