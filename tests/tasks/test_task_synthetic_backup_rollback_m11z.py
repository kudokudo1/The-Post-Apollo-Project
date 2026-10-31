#!/usr/bin/env python3
"""M11z synthetic source/backup/code-only rollback rejection matrix.

Every write is in a freshly created TemporaryDirectory, never user tasks.
"""
from __future__ import annotations

import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import stat
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "tests/tasks/fixtures/TaskSyntheticBackupRollbackM11z.py"
spec = importlib.util.spec_from_file_location("m11z_backup_test", PATH)
m11z = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m11z
spec.loader.exec_module(m11z)


def task_bytes(title="M11Z_TEST_ONLY"):
    return (json.dumps({
        "version": 3, "nextId": 2, "nextProjectId": 1,
        "projects": [], "tasks": [{
            "id": "t1", "title": title, "done": False,
            "createdAtMs": 1000, "updatedAtMs": 1000,
            "priority": "none", "description": "", "dueDate": None,
            "projectId": None,
        }]}, indent=2) + "\n").encode()


class BackupRollbackAcceptance(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="m11z-private-")
        self.folder = Path(self.tmp.name) / "m11z-synthetic-copy"
        self.folder.mkdir(mode=0o700)
        self.source_path = self.folder / m11z.SOURCE
        self.backup_path = self.folder / m11z.BACKUP
        self.current_path = self.folder / m11z.CURRENT
        self.previous_path = self.folder / m11z.PREVIOUS
        self.journal_path = self.folder / m11z.JOURNAL
        self.lock_path = self.folder / m11z.LOCK
        self.original = task_bytes()
        self.put(self.source_path, self.original)
        self.put(self.current_path, m11z.CODE_AFTER)
        self.put(self.previous_path, m11z.CODE_BEFORE)
        self.put(self.lock_path, b"M11Z_TEST_LOCK\n")
        self.pin_source = m11z.digest(self.original)
        self.pin_current = m11z.digest(m11z.CODE_AFTER)
        self.pin_previous = m11z.digest(m11z.CODE_BEFORE)

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, path, data):
        path.write_bytes(data)
        path.chmod(0o600)

    def journal(self, phase="QUIESCED", pending=False, source_hash=None,
                backup_hash=None):
        data = {
            "version": 1, "phase": phase, "pending": pending,
            "sourceHash": self.pin_source if source_hash is None else source_hash,
            "backupHash": self.pin_source if backup_hash is None else backup_hash,
        }
        self.put(self.journal_path, (json.dumps(data, sort_keys=True) + "\n").encode())

    def prepared(self):
        evidence = m11z.prepare_backup(self.folder, self.pin_source)
        self.journal()
        return evidence

    def inspect(self, evidence):
        return m11z.inspect_code_rollback(
            self.folder, evidence, self.pin_current, self.pin_previous)

    def rollback(self, evidence, **extra):
        return m11z.rollback_synthetic_code_only(
            self.folder, evidence, self.pin_current, self.pin_previous, **extra)

    def test_valid_backup_and_readonly_rollback_review(self):
        ev = self.prepared()
        self.assertEqual(ev.source_hash, self.pin_source)
        self.assertEqual(ev.backup_hash, self.pin_source)
        self.assertEqual(self.backup_path.read_bytes(), self.original)
        self.assertEqual(self.backup_path.stat().st_mode & 0o777, 0o600)
        out = self.inspect(ev)
        self.assertEqual(out["status"], "SYNTHETIC_CODE_ROLLBACK_READY")
        self.assertFalse(out["productionWriterAuthorized"])
        self.assertFalse(out["dataRestoreAuthorized"])
        self.assertEqual(self.current_path.read_bytes(), m11z.CODE_AFTER)

    def test_wrong_digest_never_creates_backup(self):
        with self.assertRaisesRegex(m11z.SafetyRefusal, "SOURCE_BASELINE_MISMATCH"):
            m11z.prepare_backup(self.folder, "0" * 64)
        with self.assertRaisesRegex(m11z.SafetyRefusal, "INDEPENDENT_DIGEST_REQUIRED"):
            m11z.prepare_backup(self.folder, "from-source-folder")
        self.assertFalse(self.backup_path.exists())
        self.assertEqual(self.original, self.source_path.read_bytes())

    def test_changed_source_before_backup_denied_without_creating_backup(self):
        def external_editor():
            self.put(self.source_path, task_bytes("M11Z_EXTERNAL_EDIT"))
        with self.assertRaisesRegex(m11z.SafetyRefusal, "SOURCE_CHANGED_BEFORE_BACKUP"):
            m11z.prepare_backup(self.folder, self.pin_source,
                                before_write=external_editor)
        self.assertFalse(self.backup_path.exists())
        self.assertEqual(self.source_path.read_bytes(), task_bytes("M11Z_EXTERNAL_EDIT"))

    def test_source_changes_while_backup_is_read_back_and_evidence_kept(self):
        def edit_after_backup():
            self.put(self.source_path, task_bytes("M11Z_EXTERNAL_EDIT"))
        with self.assertRaisesRegex(m11z.SafetyRefusal, "SOURCE_CHANGED_DURING_BACKUP"):
            m11z.prepare_backup(self.folder, self.pin_source,
                                before_readback=edit_after_backup)
        self.assertEqual(self.backup_path.read_bytes(), self.original)
        self.assertEqual(self.source_path.read_bytes(), task_bytes("M11Z_EXTERNAL_EDIT"))

    def test_backup_corruption_is_detected_not_silently_restored(self):
        def corrupt_backup():
            self.put(self.backup_path, task_bytes("M11Z_CORRUPTED"))
        with self.assertRaisesRegex(m11z.SafetyRefusal, "BACKUP_READBACK_MISMATCH"):
            m11z.prepare_backup(self.folder, self.pin_source,
                                before_readback=corrupt_backup)
        self.assertEqual(self.source_path.read_bytes(), self.original)
        self.assertEqual(self.backup_path.read_bytes(), task_bytes("M11Z_CORRUPTED"))

    def test_second_backup_never_overwrites_original_evidence(self):
        self.prepared()
        with self.assertRaisesRegex(m11z.SafetyRefusal, "BACKUP_ALREADY_EXISTS"):
            m11z.prepare_backup(self.folder, self.pin_source)
        self.assertEqual(self.backup_path.read_bytes(), self.original)

    def test_unsupported_schema_never_creates_backup(self):
        self.put(self.source_path, b'{"version": 99, "nextId": 1, "tasks": []}\n')
        with self.assertRaisesRegex(m11z.SafetyRefusal, "SYNTHETIC_SCHEMA_REFUSED"):
            m11z.prepare_backup(self.folder, m11z.digest(self.source_path.read_bytes()))
        self.assertFalse(self.backup_path.exists())

    def test_missing_source_symlink_hardlink_or_loose_permissions(self):
        original = self.source_path.read_bytes()
        self.source_path.unlink()
        with self.assertRaisesRegex(m11z.SafetyRefusal, "SYNTHETIC_FILE_UNAVAILABLE"):
            m11z.prepare_backup(self.folder, self.pin_source)
        another = self.folder / "another"
        self.put(another, original)
        self.source_path.symlink_to(another)
        with self.assertRaisesRegex(m11z.SafetyRefusal, "SYNTHETIC_FILE_UNAVAILABLE"):
            m11z.prepare_backup(self.folder, self.pin_source)
        self.source_path.unlink()
        self.put(self.source_path, original)
        link = self.folder / "another-hardlink"
        os.link(self.source_path, link)
        with self.assertRaisesRegex(m11z.SafetyRefusal, "SYNTHETIC_FILE_UNAVAILABLE"):
            m11z.prepare_backup(self.folder, self.pin_source)
        link.unlink()
        self.source_path.chmod(0o644)
        with self.assertRaisesRegex(m11z.SafetyRefusal, "SYNTHETIC_FILE_UNAVAILABLE"):
            m11z.prepare_backup(self.folder, self.pin_source)

    def test_directory_scope_refuses_wrong_name_and_symlinks(self):
        with self.assertRaisesRegex(m11z.SafetyRefusal, "SYNTHETIC_DIRECTORY_ONLY"):
            m11z.prepare_backup(Path(self.tmp.name), self.pin_source)
        self.folder.chmod(0o755)
        with self.assertRaisesRegex(m11z.SafetyRefusal, "SYNTHETIC_DIRECTORY_UNSAFE"):
            m11z.prepare_backup(self.folder, self.pin_source)
        self.folder.chmod(0o700)
        moved = Path(self.tmp.name) / "actual"
        self.folder.rename(moved)
        self.folder.symlink_to(moved, target_is_directory=True)
        with self.assertRaisesRegex(m11z.SafetyRefusal, "SYNTHETIC_DIRECTORY_UNSAFE"):
            m11z.prepare_backup(self.folder, self.pin_source)

    def test_valid_code_only_rollback_preserves_three_data_files_byte_for_byte(self):
        ev = self.prepared()
        captured = tuple(p.read_bytes() for p in
                         (self.source_path, self.backup_path, self.journal_path))
        out = self.rollback(ev, approved=True)
        self.assertEqual(out["status"], "SYNTHETIC_CODE_ONLY_ROLLED_BACK")
        self.assertTrue(out["sourceUnchanged"])
        self.assertTrue(out["journalUnchanged"])
        self.assertTrue(out["backupUnchanged"])
        self.assertFalse(out["dataRestoreAuthorized"])
        self.assertFalse(out["productionWriterAuthorized"])
        self.assertEqual(self.current_path.read_bytes(), m11z.CODE_BEFORE)
        self.assertEqual(captured, tuple(p.read_bytes() for p in
                         (self.source_path, self.backup_path, self.journal_path)))

    def test_without_explicit_approval_code_remains_unchanged(self):
        ev = self.prepared()
        with self.assertRaisesRegex(m11z.SafetyRefusal,
                                    "EXPLICIT_SYNTHETIC_APPROVAL_REQUIRED"):
            self.rollback(ev)
        self.assertEqual(self.current_path.read_bytes(), m11z.CODE_AFTER)

    def test_quiescence_required_and_pending_journal_blocks_rollback(self):
        ev = self.prepared()
        for phase, pending in (("ACTIVE", False), ("QUIESCED", True),
                               ("RECOVERY_REVIEW", False)):
            self.journal(phase=phase, pending=pending)
            with self.assertRaisesRegex(m11z.SafetyRefusal,
                                        "SYNTHETIC_JOURNAL_NOT_QUIESCED"):
                self.rollback(ev, approved=True)
            self.assertEqual(self.current_path.read_bytes(), m11z.CODE_AFTER)

    def test_wrong_journal_hash_refuses_before_code_change(self):
        ev = self.prepared()
        self.journal(source_hash="f" * 64)
        with self.assertRaisesRegex(m11z.SafetyRefusal, "JOURNAL_DIGEST_CONFLICT"):
            self.rollback(ev, approved=True)
        self.assertEqual(self.current_path.read_bytes(), m11z.CODE_AFTER)

    def test_late_external_task_edit_refuses_code_rollback_without_overwrite(self):
        ev = self.prepared()
        later = task_bytes("M11Z_EDIT_AFTER_BACKUP")
        self.put(self.source_path, later)
        with self.assertRaisesRegex(m11z.SafetyRefusal,
                                    "SOURCE_CHANGED_SINCE_PREFLIGHT"):
            self.rollback(ev, approved=True)
        self.assertEqual(self.source_path.read_bytes(), later)
        self.assertEqual(self.backup_path.read_bytes(), self.original)
        self.assertEqual(self.current_path.read_bytes(), m11z.CODE_AFTER)

    def test_corrupted_backup_and_wrong_code_pin_refuse(self):
        ev = self.prepared()
        self.put(self.backup_path, task_bytes("M11Z_BACKUP_CHANGED"))
        with self.assertRaisesRegex(m11z.SafetyRefusal,
                                    "BACKUP_CHANGED_SINCE_PREFLIGHT"):
            self.rollback(ev, approved=True)
        self.put(self.backup_path, self.original)
        with self.assertRaisesRegex(m11z.SafetyRefusal, "CURRENT_CODE_CHANGED"):
            m11z.rollback_synthetic_code_only(
                self.folder, ev, "0" * 64, self.pin_previous, approved=True)
        with self.assertRaisesRegex(m11z.SafetyRefusal, "PREVIOUS_CODE_UNTRUSTED"):
            m11z.rollback_synthetic_code_only(
                self.folder, ev, self.pin_current, "0" * 64, approved=True)

    def test_concurrent_code_or_source_change_injection_refused(self):
        ev = self.prepared()
        def change_current():
            self.put(self.current_path, b"M11Z-ALTERED-CODE\n")
        with self.assertRaisesRegex(m11z.SafetyRefusal, "CURRENT_CODE_CHANGED"):
            self.rollback(ev, approved=True, before_commit=change_current)
        self.assertEqual(self.current_path.read_bytes(), b"M11Z-ALTERED-CODE\n")
        self.put(self.current_path, m11z.CODE_AFTER)
        def change_source():
            self.put(self.source_path, task_bytes("M11Z_EXTERNAL_DURING_ROLLBACK"))
        with self.assertRaisesRegex(m11z.SafetyRefusal,
                                    "SOURCE_CHANGED_SINCE_PREFLIGHT"):
            self.rollback(ev, approved=True, before_commit=change_source)
        self.assertEqual(self.current_path.read_bytes(), m11z.CODE_AFTER)

    def test_second_code_rollback_refused_without_replaying(self):
        ev = self.prepared()
        self.rollback(ev, approved=True)
        with self.assertRaisesRegex(m11z.SafetyRefusal, "CURRENT_CODE_CHANGED"):
            self.rollback(ev, approved=True)
        self.assertEqual(self.current_path.read_bytes(), m11z.CODE_BEFORE)

    def test_lock_contender_refused_without_overwrite(self):
        ev = self.prepared()
        fd = os.open(self.lock_path, os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(m11z.SafetyRefusal, "ROLLBACK_LOCK_CONTENDED"):
                self.rollback(ev, approved=True)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        self.assertEqual(self.current_path.read_bytes(), m11z.CODE_AFTER)

    def test_no_live_tasks_mount_or_new_writer(self):
        body = PATH.read_text(encoding="utf-8")
        live_store = (ROOT / "services/hub/ApolloHubTodoStore.qml"
                      ).read_text(encoding="utf-8")
        shell = (ROOT / "shell.qml").read_text(encoding="utf-8")
        for forbidden in ("apollo-hub-todo-v1.json", "Quickshell.dataDir",
                          "TodoStore.qml", "TaskJsonGateTransportM11m"):
            self.assertNotIn(forbidden, body)
        self.assertIn("readonly property bool guardedWriterEnabled: false",
                      live_store)
        self.assertEqual(live_store.count("FileView {"), 1)
        self.assertNotIn("TaskSyntheticBackupRollbackM11z", live_store + shell)


if __name__ == "__main__":
    unittest.main(verbosity=2)
