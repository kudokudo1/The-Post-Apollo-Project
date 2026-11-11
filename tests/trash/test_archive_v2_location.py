"""Trash++ V2g archive-location security, synthetic roots only."""
import os
from pathlib import Path
import tempfile
import unittest

from scripts.trash.archive_v2_location import (
    ArchiveRootError, PRIVATE_SUBDIR, archive_directory, DB_NAME
)
from scripts.trash.archive_store_v2 import ArchiveStore
from scripts.trash.archive_v2_index import index as read_index, ReadIndexError


class PrivateArchiveLocationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / "quickshell-data"
        self.data.mkdir(mode=0o700)

    def test_preview_read_only_missing_store_creates_nothing(self):
        os.chmod(self.data, 0o755)
        before = set(self.data.iterdir())
        self.assertIsNone(archive_directory(self.data, create=False))
        self.assertEqual(read_index(str(self.data))["state"], "NOT_INSTALLED")
        self.assertEqual(set(self.data.iterdir()), before)

    def test_private_child_without_parent_chmod(self):
        os.chmod(self.data, 0o755)
        mode = self.data.stat().st_mode & 0o777
        place = archive_directory(self.data, create=True)
        self.assertEqual(place, self.data / PRIVATE_SUBDIR)
        self.assertEqual(place.stat().st_mode & 0o777, 0o700)
        self.assertEqual(self.data.stat().st_mode & 0o777, mode)
        self.assertIs(archive_directory(self.data, create=False), place)
        store = ArchiveStore(place)
        saved = store.save("demo-scrape", "fixture-1", "r1", b"synthetic")
        items = read_index(str(self.data))["items"]
        self.assertEqual([r["id"] for r in items], [saved["id"]])
        self.assertFalse((self.data / DB_NAME).exists())

    def test_insecure_parent_is_rejected_and_not_modified(self):
        os.chmod(self.data, 0o775)
        before = set(self.data.iterdir())
        for creates in (False, True):
            with self.assertRaisesRegex(ArchiveRootError, "ARCHIVE_PARENT_WRITABLE"):
                archive_directory(self.data, create=creates)
        self.assertEqual(set(self.data.iterdir()), before)
        self.assertEqual(self.data.stat().st_mode & 0o777, 0o775)

    def test_symlinked_child_refused_without_chmod_or_follow(self):
        outside = self.root / "outside"
        outside.mkdir(mode=0o700)
        (self.data / PRIVATE_SUBDIR).symlink_to(outside, target_is_directory=True)
        before = set(outside.iterdir())
        with self.assertRaisesRegex(ArchiveRootError, "ARCHIVE_PRIVATE_ROOT_UNSAFE"):
            archive_directory(self.data, create=True)
        with self.assertRaisesRegex(ReadIndexError, "ARCHIVE_PRIVATE_ROOT_UNSAFE"):
            read_index(str(self.data))
        self.assertEqual(set(outside.iterdir()), before)

    def test_legacy_private_root_visible_and_reused(self):
        original = ArchiveStore(self.data)
        snap = original.save("demo-scrape", "legacy-1", "r1", b"old-data")
        self.assertEqual(archive_directory(self.data, create=True), self.data)
        self.assertEqual(read_index(str(self.data))["items"][0]["id"], snap["id"])
        self.assertFalse((self.data / PRIVATE_SUBDIR).exists())
        self.assertEqual(original.read_verified(snap["id"]), b"old-data")

    def test_insecure_legacy_database_refused_not_silently_migrated(self):
        original = ArchiveStore(self.data)
        original.save("demo-scrape", "legacy-1", "r1", b"old-data")
        before = original.path.read_bytes()
        os.chmod(self.data, 0o755)
        with self.assertRaisesRegex(ArchiveRootError, "ARCHIVE_LEGACY_ROOT_UNSAFE"):
            archive_directory(self.data, create=True)
        with self.assertRaisesRegex(ReadIndexError, "ARCHIVE_LEGACY_ROOT_UNSAFE"):
            read_index(str(self.data))
        self.assertEqual(original.path.read_bytes(), before)
        self.assertFalse((self.data / PRIVATE_SUBDIR).exists())

    def test_ambiguous_store_roots_refused(self):
        ArchiveStore(self.data)
        (self.data / PRIVATE_SUBDIR).mkdir(mode=0o700)
        with self.assertRaisesRegex(ArchiveRootError, "ARCHIVE_MULTIPLE_ROOTS"):
            archive_directory(self.data)
        with self.assertRaisesRegex(ReadIndexError, "ARCHIVE_MULTIPLE_ROOTS"):
            read_index(str(self.data))

    def test_symlinked_quickshell_parent_refused(self):
        link = self.root / "quickshell-link"
        link.symlink_to(self.data, target_is_directory=True)
        with self.assertRaisesRegex(ArchiveRootError, "ARCHIVE_ROOT_UNSAFE"):
            archive_directory(link, create=True)
        self.assertFalse((self.data / PRIVATE_SUBDIR).exists())

    def test_existing_child_permissions_never_relaxed(self):
        child = self.data / PRIVATE_SUBDIR
        child.mkdir(mode=0o755)
        with self.assertRaisesRegex(ArchiveRootError, "ARCHIVE_PRIVATE_ROOT_UNSAFE"):
            archive_directory(self.data, create=True)
        self.assertEqual(child.stat().st_mode & 0o777, 0o755)

    def test_path_traversal_refused_before_create(self):
        for bad in ("/tmp/a/../b", "relative", "", "\x00", None, 3):
            with self.assertRaisesRegex(ArchiveRootError, "INVALID_ARCHIVE_ROOT"):
                archive_directory(bad, create=True)


if __name__ == "__main__":
    unittest.main()
