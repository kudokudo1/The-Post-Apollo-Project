"""Trash++ V2h capacity measurement is read-only and fails closed."""
import os
from pathlib import Path
import tempfile
import unittest

from scripts.trash.archive_v2_capacity import (
    capacity, CapacityError, DB_NAME, DEFAULT_DISK_QUOTA,
)


class ArchiveCapacityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_absent_store_has_no_creation_side_effects(self):
        before = set(self.root.iterdir())
        info = capacity(self.root)
        self.assertEqual(info["chargedBytes"], 0)
        self.assertEqual(info["databaseBytes"], 0)
        self.assertEqual(info["journalBytes"], 0)
        self.assertEqual(info["remainingBytes"], DEFAULT_DISK_QUOTA)
        self.assertEqual(info["capacityState"], "READY")
        self.assertGreaterEqual(info["filesystemAvailableBytes"], 0)
        self.assertEqual(set(self.root.iterdir()), before)

    def test_logical_and_allocated_bytes_include_rollback_journal(self):
        db = self.root / DB_NAME
        db.write_bytes(b"A" * 10000)
        db.chmod(0o600)
        journal = self.root / (DB_NAME + "-journal")
        journal.write_bytes(b"B" * 4096)
        journal.chmod(0o644)
        report = capacity(self.root, disk_quota=65536)
        self.assertEqual(report["databaseBytes"], 10000)
        self.assertEqual(report["journalBytes"], 4096)
        self.assertEqual(report["logicalBytes"], 14096)
        self.assertGreaterEqual(report["chargedBytes"], report["logicalBytes"])
        self.assertGreaterEqual(report["chargedBytes"], report["allocatedBytes"])
        self.assertEqual(report["remainingBytes"],
                         max(0, 65536 - report["chargedBytes"]))
        self.assertEqual(journal.read_bytes(), b"B" * 4096)

    def test_full_status_never_deletes_files(self):
        db = self.root / DB_NAME
        db.write_bytes(b"Z" * 70000)
        db.chmod(0o600)
        report = capacity(self.root, disk_quota=65536)
        self.assertEqual(report["capacityState"], "FULL")
        self.assertEqual(report["remainingBytes"], 0)
        self.assertEqual(db.read_bytes(), b"Z" * 70000)

    def test_symlinks_and_wrong_modes_refused(self):
        db = self.root / DB_NAME
        db.symlink_to(self.root / "out")
        with self.assertRaisesRegex(CapacityError, "ARCHIVE_FILE_UNSAFE"):
            capacity(self.root)
        db.unlink()
        db.write_bytes(b"synthetic")
        with self.assertRaisesRegex(CapacityError, "ARCHIVE_FILE_UNSAFE"):
            capacity(self.root)
        db.chmod(0o600)
        for suffix in ("-wal", "-shm"):
            sidecar = self.root / (DB_NAME + suffix)
            sidecar.symlink_to(self.root / "outside")
            with self.assertRaisesRegex(CapacityError,
                                        "ARCHIVE_UNEXPECTED_SIDECAR"):
                capacity(self.root)
            sidecar.unlink()

    def test_unsafe_root_and_invalid_capacity_rejected(self):
        os.chmod(self.root, 0o755)
        with self.assertRaisesRegex(CapacityError, "ARCHIVE_ROOT_UNSAFE"):
            capacity(self.root)
        os.chmod(self.root, 0o700)
        for invalid in (True, None, 100, 2 ** 40 + 1):
            with self.assertRaisesRegex(CapacityError,
                                        "INVALID_ARCHIVE_CAPACITY"):
                capacity(self.root, invalid)


if __name__ == "__main__":
    unittest.main()
