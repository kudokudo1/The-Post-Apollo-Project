#!/usr/bin/env python3
"""M10n read-only TASKS cutover review. NEVER activates, migrates or restores.

This module accepts caller-provided source/backup/restore bytes and explicit
SQLite test paths. It does not discover Quickshell data, write files, stop
writers, change tasks, contact GitHub, or honor a self-reported approval as
activation authority. Database reads use the experimental M10l validator.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVIDENCE_GATES = (
    "legacyWriterQuiescenceReviewed",
    "exclusiveNewWriterReviewed",
    "hostRuntimeAcceptanceReviewed",
    "sqliteOnlineBackupReviewed",
    "restartRecoveryReviewed",
    "rollbackProcedureReviewed",
)


def _load(file, name):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    if not spec or not spec.loader:
        raise RuntimeError("MISSING_POLICY")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _result(status, blockers, *, revision=None, counts=None):
    return {
        "status": status,
        "blockers": blockers,
        "reviewReady": status == "READY_FOR_OPERATOR_REVIEW",
        "activate": False,
        "writeReady": False,
        "remoteWriteAuthorized": False,
        "rollbackExecuted": False,
        "revision": revision,
        "counts": counts,
    }


def review(original_bytes, current_bytes, legacy_backup_bytes,
           restored_legacy_bytes, expected_source_sha256, shadow_path,
           sqlite_backup_path, evidence=None):
    """Perform *read-only* candidate and independent-backup checks.

    External evidence gates are review notes ONLY. Passing every gate still
    does not grant writer authority or approve a production cutover.
    """
    blockers = []
    if any(type(value) is not bytes for value in (
            original_bytes, current_bytes, legacy_backup_bytes,
            restored_legacy_bytes)):
        return _result("BLOCKED", ["INVALID_BYTE_INPUT"])
    actual_hash = hashlib.sha256(original_bytes).hexdigest()
    if (type(expected_source_sha256) is not str
            or actual_hash != expected_source_sha256):
        blockers.append("BASELINE_HASH_MISMATCH")
    if original_bytes != current_bytes:
        blockers.append("LEGACY_SOURCE_CHANGED")
    if original_bytes != legacy_backup_bytes:
        blockers.append("ORIGINAL_BACKUP_MISMATCH")
    if original_bytes != restored_legacy_bytes:
        blockers.append("RESTORE_COPY_MISMATCH")
    if (not isinstance(shadow_path, Path)
            or not isinstance(sqlite_backup_path, Path)
            or not shadow_path.is_absolute() or not sqlite_backup_path.is_absolute()
            or shadow_path.name != "tasks.db"
            or sqlite_backup_path.name != "tasks.db"):
        blockers.append("EXPLICIT_TEST_DB_PATHS_REQUIRED")
        return _result("BLOCKED", blockers)
    if (shadow_path.resolve() == sqlite_backup_path.resolve()
            or (shadow_path.exists() and sqlite_backup_path.exists()
                and shadow_path.samefile(sqlite_backup_path))):
        blockers.append("SQLITE_BACKUP_NOT_INDEPENDENT")
        return _result("BLOCKED", blockers)
    if blockers:
        return _result("BLOCKED", blockers)

    try:
        migrator = _load("LegacySqliteMigrationPreview.py",
                         "m10n_legacy_preview")
        candidate = migrator.preview(original_bytes)
        if candidate["originalSha256"] != actual_hash:
            blockers.append("MIGRATION_SOURCE_CHANGED")
        sqlite = _load("ExperimentalTaskSqliteRecordsV2.py",
                       "m10n_sqlite_records")
        primary = sqlite.read(shadow_path)
        backup = sqlite.read(sqlite_backup_path)
    except (Exception,):
        # Deliberately do not expose paths or task content in the response.
        blockers.append("MIGRATION_OR_SQLITE_VALIDATION_FAILED")
        return _result("BLOCKED", blockers)

    if (primary.get("status") != "READY"
            or not primary.get("available")
            or primary.get("blockedOperations")):
        blockers.append("SHADOW_NOT_CLEAN")
    if (backup.get("status") != "READY"
            or not backup.get("available")
            or backup.get("blockedOperations")):
        blockers.append("SQLITE_BACKUP_NOT_CLEAN")
    expected = candidate["candidate"]
    if (primary.get("document") != expected
            or primary.get("revision") != 0
            or primary.get("hash") != sqlite._hash(expected)):
        blockers.append("SHADOW_PARITY_FAILED")
    if (backup.get("document") != expected
            or backup.get("hash") != primary.get("hash")):
        blockers.append("SQLITE_BACKUP_PARITY_FAILED")
    if blockers:
        return _result("BLOCKED", blockers)

    # Neither a UI boolean nor test-supplied evidence substitutes for
    # operator approval or durable workstation runtime acceptance.
    attestations = evidence if type(evidence) is dict else {}
    pending = [key for key in EVIDENCE_GATES if attestations.get(key) is not True]
    if pending:
        return _result("REVIEW_INCOMPLETE",
                       ["UNREVIEWED_" + key for key in pending],
                       revision=0, counts=candidate["counts"])
    return _result("READY_FOR_OPERATOR_REVIEW", [],
                   revision=0, counts=candidate["counts"])


def rollback_review(shadow_path, baseline_model_hash):
    """Determine only whether rollback *review* is blocked by new edits.

    Never restores the original JSON. New local revisions, pending remote
    operations or unknown database states prohibit restoring old data.
    """
    if (not isinstance(shadow_path, Path)
            or shadow_path.name != "tasks.db" or not shadow_path.is_absolute()
            or type(baseline_model_hash) is not str or len(baseline_model_hash) != 64
            or any(c not in "0123456789abcdef" for c in baseline_model_hash)):
        return {"rollbackReviewEligible": False, "restore": False,
                "reason": "INVALID_BASELINE"}
    try:
        records = _load("ExperimentalTaskSqliteRecordsV2.py",
                        "m10n_rollback_records")
        current = records.read(shadow_path)
    except Exception:
        return {"rollbackReviewEligible": False, "restore": False,
                "reason": "UNKNOWN_SQLITE_STATE"}
    if (current.get("status") != "READY"
            or current.get("revision") != 0
            or current.get("hash") != baseline_model_hash
            or current.get("document", {}).get("operations")):
        return {"rollbackReviewEligible": False, "restore": False,
                "reason": "POST_CUTOVER_CHANGES_OR_UNCERTAINTY"}
    return {"rollbackReviewEligible": True, "restore": False,
            "reason": "EXTERNAL_REVIEW_STILL_REQUIRED"}
