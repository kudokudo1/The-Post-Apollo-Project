#!/usr/bin/env python3
"""M10n fake cutover review on 100% disposable files, no live TASKS."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services/projects"
def load(name, suffix):
    spec = importlib.util.spec_from_file_location(suffix, SERVICE / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

gate = load("TaskSqliteCutoverReview.py", "m10n_cutover_gate")
migration = load("LegacySqliteMigrationPreview.py", "m10n_preview")
sqlite = load("ExperimentalTaskSqliteRecordsV2.py", "m10n_records")
NOW = 1771521000000
legacy = {
    "version": 3, "nextId": 52, "nextProjectId": 8,
    "projects": [
        {"id": "p2", "name": "Tasks 🏥", "createdAtMs": NOW,
         "updatedAtMs": NOW + 30},
        {"id": "p7", "name": "Review", "createdAtMs": NOW + 5,
         "updatedAtMs": NOW + 15},
    ],
    "tasks": [
        {"id": "t5", "title": "Review SQLite", "done": False,
         "priority": "medium", "description": "Do not erase source",
         "dueDate": "2026-10-23", "projectId": "p2",
         "createdAtMs": NOW, "updatedAtMs": NOW + 100},
        {"id": "t51", "title": "Plain note", "done": True,
         "priority": "none", "description": "Original formatting preserved",
         "dueDate": None, "projectId": None,
         "createdAtMs": NOW, "updatedAtMs": NOW + 70},
    ],
}
raw = (json.dumps(legacy, ensure_ascii=False, indent=3)+"\n").encode("utf8")
source_sha = hashlib.sha256(raw).hexdigest()
candidate = migration.preview(raw)["candidate"]
attested = {key: True for key in gate.EVIDENCE_GATES}

def verify_clean(result):
    assert result["reviewReady"] is True, result
    assert result["status"] == "READY_FOR_OPERATOR_REVIEW"
    assert result["activate"] is False
    assert result["writeReady"] is False
    assert result["remoteWriteAuthorized"] is False
    assert result["rollbackExecuted"] is False
    assert result["counts"] == {"projects": 2, "tasks": 2}
    assert result["revision"] == 0
    assert "candidate" not in result and "document" not in result

with tempfile.TemporaryDirectory(prefix="pa-task-cutover-m10n-") as folder:
    root = Path(folder)
    original = root / "legacy.json"
    original.write_bytes(raw)
    source_original = original.read_bytes()

    # A real offline SQLite backup *exercise*, not a live backup procedure.
    shadow_dir = root / "shadow"
    backup_dir = root / "independent-sqlite-backup"
    shadow_dir.mkdir(mode=0o700)
    backup_dir.mkdir(mode=0o700)
    shadow = shadow_dir / "tasks.db"
    sql_backup = backup_dir / "tasks.db"
    # SQLite's normal CREATE honors the process umask. Ensure the throwaway
    # backup is private before invoking SQLite's online backup API.
    import os
    fd = os.open(sql_backup, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    saved = sqlite.initialize(shadow, candidate)
    assert saved["localSaved"] is True
    assert sqlite.read(shadow)["document"] == candidate
    with sqlite3.connect(f"file:{shadow}?mode=ro", uri=True) as reader:
        with sqlite3.connect(sql_backup) as writer:
            reader.backup(writer)
    assert sqlite.read(sql_backup)["document"] == candidate
    assert sqlite.read(sql_backup)["hash"] == sqlite.read(shadow)["hash"]

    # Raw-byte backup must remain untouched, and restore occurs at yet
    # another throwaway path, never over the initial legacy source.
    legacy_backup = root / "source-backup.bytes"
    with legacy_backup.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        import os
        os.fsync(stream.fileno())
    restored = root / "source-restored.json"
    restored.write_bytes(legacy_backup.read_bytes())
    assert original.read_bytes() == source_original
    assert restored.read_bytes() == source_original

    def review(*, original_bytes=raw, current_bytes=raw,
               backup_bytes=raw, restored_bytes=raw,
               original_hash=source_sha, shadow_path=shadow,
               backup_path=sql_backup, evidence=attested):
        return gate.review(original_bytes, current_bytes, backup_bytes,
                           restored_bytes, original_hash, shadow_path,
                           backup_path, evidence)

    verify_clean(review())
    assert gate.rollback_review(shadow, sqlite._hash(candidate)) == {
        "rollbackReviewEligible": True,
        "restore": False, "reason": "EXTERNAL_REVIEW_STILL_REQUIRED"}

    missing = review(evidence={})
    assert missing["status"] == "REVIEW_INCOMPLETE"
    assert missing["activate"] is False
    assert len(missing["blockers"]) == len(gate.EVIDENCE_GATES)
    # Passing self-reported gates is not a deployment credential.
    fake_approval = {**attested, "operatorApproval": True,
                     "forceActivate": True, "ignoreSafety": True}
    verify_clean(review(evidence=fake_approval))
    assert review(backup_bytes=raw+b"changed")["status"] == "BLOCKED"
    assert "ORIGINAL_BACKUP_MISMATCH" in review(
        backup_bytes=raw+b"changed")["blockers"]
    assert "RESTORE_COPY_MISMATCH" in review(
        restored_bytes=b"not identical")["blockers"]
    assert "LEGACY_SOURCE_CHANGED" in review(
        current_bytes=raw+b"\n")["blockers"]
    assert "BASELINE_HASH_MISMATCH" in review(
        original_hash="a"*64)["blockers"]
    assert "SQLITE_BACKUP_NOT_INDEPENDENT" in review(
        backup_path=shadow)["blockers"]
    assert "EXPLICIT_TEST_DB_PATHS_REQUIRED" in review(
        backup_path=root)["blockers"]
    assert "SQLITE_BACKUP_NOT_CLEAN" in review(
        backup_path=root/"missing"/"tasks.db")["blockers"]
    assert review(original_bytes=b"{broken")["status"] == "BLOCKED"
    assert review(evidence={"legacyWriterQuiescenceReviewed": "true"}
                 )["status"] == "REVIEW_INCOMPLETE"

    # Destructive manual changes, added task edits and local operations
    # make the old JSON snapshot an unsafe rollback target.
    first = sqlite.read(shadow)
    changed = sqlite.edit_task(
        shadow, expected_revision=first["revision"],
        expected_hash=first["hash"], task_id="t5", field="done",
        value=True, now_ms=NOW+200)
    assert changed["localSaved"] is True
    assert sqlite.read(shadow)["revision"] == 1
    assert gate.rollback_review(shadow, sqlite._hash(candidate)) == {
        "rollbackReviewEligible": False,
        "restore": False, "reason": "POST_CUTOVER_CHANGES_OR_UNCERTAINTY"}
    assert "SHADOW_PARITY_FAILED" in review()["blockers"]
    # An exact matching database backup does not make rollback safe after
    # the candidate has accepted a new edit.
    with sqlite3.connect(f"file:{shadow}?mode=ro", uri=True) as reader:
        # Separate second temp target, because SQLite backup may overwrite
        # the previous copy and its WAL; do not modify the original backup.
        later_dir = root / "later-copy"
        later_dir.mkdir(mode=0o700)
        later = later_dir / "tasks.db"
        fd = os.open(later, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        with sqlite3.connect(later) as writer:
            reader.backup(writer)
    assert sqlite.read(later)["revision"] == 1
    assert gate.rollback_review(later, sqlite._hash(candidate))[
        "rollbackReviewEligible"] is False

    # Restored original JSON remains the exact original despite DB edits.
    assert original.read_bytes() == source_original
    assert legacy_backup.read_bytes() == source_original
    assert restored.read_bytes() == source_original
    assert not hasattr(gate, "activate")
    assert not hasattr(gate, "restore_live")
    assert not hasattr(gate, "stop_quickshell")
    assert not hasattr(gate, "connect_github")

print("TASKS M10n SQLite shadow cutover review, WAL-safe online test backup and rollback gate: PASS")
