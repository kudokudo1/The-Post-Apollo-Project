"""Trash++ V2a isolated storage tests. All records are synthetic temporary data."""
import importlib.util
from pathlib import Path
import os
import sqlite3
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "trash_archive_store_v2", ROOT / "scripts/trash/archive_store_v2.py")
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class ArchiveV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = mod.ArchiveStore(self.root)

    def save(self, i=1, **kwargs):
        return self.store.save("demo-scrape", "page-1", str(i),
                               b"synthetic-" + str(i).encode(),
                               display_label="Test page", **kwargs)

    def test_durable_restart_and_exact_digest(self):
        row = self.save()
        restarted = mod.ArchiveStore(self.root)
        self.assertEqual(restarted.read_verified(row["id"]), b"synthetic-1")
        self.assertEqual(restarted.verify(),
                         {"verified": True, "items": 1, "payloadBytes": 11})
        self.assertEqual(restarted.status()["revision"], 1)

    def test_duplicate_revision_refused_without_updating_original(self):
        first = self.save()
        with self.assertRaisesRegex(mod.ArchiveError, "SNAPSHOT_ALREADY_EXISTS"):
            self.store.save("demo-scrape", "page-1", "1", b"changed")
        self.assertEqual(self.store.read_verified(first["id"]), b"synthetic-1")
        self.assertEqual(self.store.status()["total"], 1)

    def test_source_revision_is_part_of_identity(self):
        a, b = self.save(1), self.save(2)
        self.assertNotEqual(a["id"], b["id"])
        self.assertEqual(self.store.status()["total"], 2)

    def test_paged_large_index_is_stable_and_does_not_export_payload(self):
        for i in range(235):
            self.store.save("demo-scrape", "page-1", str(i), b"private-body",
                            display_label=f"Page {i}", captured_ms=1760000000000)
        cursor = None
        seen = []
        while True:
            page = self.store.list_page(limit=40, cursor=cursor)
            for entry in page["items"]:
                self.assertNotIn("payload", entry)
                self.assertNotIn("private-body", str(entry))
                seen.append(entry["id"])
            if not page["hasMore"]:
                self.assertIsNone(page["nextCursor"])
                break
            cursor = page["nextCursor"]
        self.assertEqual(len(seen), 235)
        self.assertEqual(len(set(seen)), 235)

    def test_list_page_validation(self):
        for limit, cursor in [(0, None), (101, None), (True, None),
                              (2, "1:../bad"), (2, "99999999999999:" + "a"*32)]:
            with self.assertRaises(mod.ArchiveError):
                self.store.list_page(limit, cursor)

    def test_unapproved_owner_cannot_save(self):
        for owner in ("hospital", "finance-transactions", "apollo-hub-notes",
                      "identity", "time-machine", []):
            with self.assertRaisesRegex(mod.ArchiveError, "OWNER_NOT_AUTHORIZED"):
                self.store.save(owner, "r1", "1", b"record")
        self.assertEqual(self.store.status()["total"], 0)

    def test_malformed_identity_and_payload_refused(self):
        for rid, rev, data in [("../source", "1", b"ok"), ("r", "../old", b"ok"),
                               ("r", "1", b""), ("r", "1", "not bytes"),
                               ("r", "1", b"x" * (mod.MAX_ITEM_BYTES + 1))]:
            with self.assertRaises(mod.ArchiveError):
                self.store.save("demo-scrape", rid, rev, data)
        self.assertEqual(self.store.status()["total"], 0)

    def test_quota_refuses_without_eviction(self):
        limited = mod.ArchiveStore(self.root, payload_quota=mod.MAX_ITEM_BYTES)
        first = limited.save("demo-scrape", "r1", "1", b"x"*5000000)
        with self.assertRaisesRegex(mod.ArchiveError, "ARCHIVE_PAYLOAD_QUOTA"):
            limited.save("demo-scrape", "r2", "1", b"y"*4000000)
        self.assertEqual(limited.read_verified(first["id"]), b"x"*5000000)
        self.assertEqual(limited.status()["total"], 1)

    def test_corrupted_payload_detected_not_silently_fixed(self):
        snap = self.save()
        with sqlite3.connect(self.store.path) as db:
            db.execute("UPDATE snapshots SET payload=? WHERE id=?",
                       (b"corrupt-data", snap["id"]))
        with self.assertRaisesRegex(mod.ArchiveError, "SNAPSHOT_INTEGRITY_FAILED"):
            self.store.read_verified(snap["id"])
        with self.assertRaisesRegex(mod.ArchiveError, "SNAPSHOT_INTEGRITY_FAILED"):
            self.store.verify()

    def test_accounting_corruption_detected(self):
        self.save()
        with sqlite3.connect(self.store.path) as db:
            db.execute("UPDATE archive_meta SET payload_bytes=0")
        with self.assertRaisesRegex(mod.ArchiveError, "ARCHIVE_ACCOUNTING_MISMATCH"):
            self.store.verify()

    def test_transaction_rollback_preserves_store(self):
        self.save()
        db = sqlite3.connect(self.store.path)
        db.execute("BEGIN IMMEDIATE")
        db.execute("UPDATE archive_meta SET payload_bytes=90000000")
        db.close()  # simulate interrupted writer: SQLite rolls it back
        restarted = mod.ArchiveStore(self.root)
        self.assertEqual(restarted.verify()["payloadBytes"], 11)

    def test_root_and_database_symlinks_are_refused(self):
        another = self.root / "outside"
        another.mkdir(mode=0o700)
        link = self.root / "symlink"
        link.symlink_to(another, target_is_directory=True)
        with self.assertRaisesRegex(mod.ArchiveError, "ARCHIVE_ROOT_UNSAFE"):
            mod.ArchiveStore(link)
        self.store.path.unlink()
        self.store.path.symlink_to(self.root / "elsewhere")
        with self.assertRaisesRegex(mod.ArchiveError, "ARCHIVE_FILE_UNSAFE"):
            mod.ArchiveStore(self.root)

    def test_unexpected_sqlite_sidecars_and_journal_symlink_refused(self):
        for suffix in ("-wal", "-shm"):
            sidecar = self.root / (mod.DB_NAME + suffix)
            sidecar.symlink_to(self.root / "outside")
            with self.assertRaisesRegex(mod.ArchiveError,
                                        "ARCHIVE_UNEXPECTED_SIDECAR"):
                mod.ArchiveStore(self.root)
            sidecar.unlink()
        journal = self.root / (mod.DB_NAME + "-journal")
        journal.symlink_to(self.root / "outside")
        with self.assertRaisesRegex(mod.ArchiveError, "ARCHIVE_FILE_UNSAFE"):
            mod.ArchiveStore(self.root)
        journal.unlink()
        self.assertEqual(mod.ArchiveStore(self.root).verify()["items"], 0)

    def test_unsafe_permissions_refused(self):
        os.chmod(self.root, 0o777)
        with self.assertRaisesRegex(mod.ArchiveError, "ARCHIVE_ROOT_UNSAFE"):
            mod.ArchiveStore(self.root)
        os.chmod(self.root, 0o700)

    def test_parallel_writers_serialize_with_unique_revisions(self):
        failures = []
        def writer(i):
            try:
                self.save(i)
            except Exception as exc:
                failures.append(type(exc).__name__ + ":" + str(exc))
        threads = [threading.Thread(target=writer, args=(i,)) for i in range(20)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(failures, [])
        self.assertEqual(self.store.status()["total"], 20)
        self.assertEqual(self.store.verify()["items"], 20)

    def test_no_delete_restore_burn_or_external_source_read_api(self):
        for method in ("trash", "burn", "delete", "restore", "migrate", "read_source"):
            self.assertFalse(hasattr(self.store, method))
        self.assertFalse(hasattr(mod, "main"))
        self.assertEqual(self.store.status()["total"], 0)


if __name__ == "__main__":
    unittest.main()
