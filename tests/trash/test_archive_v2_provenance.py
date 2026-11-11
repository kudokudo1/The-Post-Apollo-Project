"""V2i provenance: unsigned metadata receipts, safe legacy migration, no payload export."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from scripts.trash.archive_store_v2 import (
    ArchiveError, ArchiveStore, DB_NAME, SCHEMA
)
from scripts.trash.archive_v2_index import index as read_index, ReadIndexError
from scripts.trash.archive_v2_provenance import (
    RECEIPT_SCHEMA, ProvenanceError, create_receipt, verify_receipt,
)


class ProvenanceV2iTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def store(self):
        return ArchiveStore(self.root)

    def save(self, store, revision, payload=b"synthetic", resource="source-1"):
        return store.save("demo-scrape", resource, revision, payload,
                          display_label="Synthetic title",
                          captured_ms=1760000000000)

    def test_receipt_binds_source_metadata_time_payload_and_copy(self):
        archive = self.store()
        saved = self.save(archive, "rev1")
        evidence = saved["provenance"]
        self.assertEqual(evidence["state"], "RECEIPT_MATCHED")
        self.assertEqual(evidence["authentication"], "UNSIGNED_LOCAL")
        self.assertEqual(evidence["sourceCapturedAtMs"], 1760000000000)
        self.assertGreaterEqual(evidence["archivedAtMs"], 1760000000000)
        self.assertEqual(evidence["previousReceiptHash"], "")
        self.assertEqual(len(evidence["receiptSha256"]), 64)
        with sqlite3.connect(archive.path) as db:
            flags = db.execute("""SELECT provenance_required FROM snapshots
                WHERE id=?""", (saved["id"],)).fetchone()
            self.assertEqual(flags, (1,))
            self.assertEqual(db.execute(
                "SELECT count(*) FROM snapshot_receipts").fetchone()[0], 1)
        page = read_index(str(self.root))["items"]
        self.assertEqual(len(page), 1)
        self.assertEqual(page[0]["provenance"]["receiptSha256"],
                         evidence["receiptSha256"])
        self.assertFalse(page[0]["verified"])
        self.assertIn("PAYLOAD NOT VERIFIED", page[0]["details"])
        self.assertEqual(archive.read_verified(saved["id"]), b"synthetic")
        self.assertEqual(archive.verify(),
                         {"verified": True, "items": 1, "payloadBytes": 9})

    def test_same_source_receipts_link_without_cross_owner_leakage(self):
        archive = self.store()
        first = self.save(archive, "rev1")
        second = self.save(archive, "rev2", payload=b"changed")
        other = self.save(archive, "rev3", resource="other-record")
        self.assertEqual(second["provenance"]["previousReceiptHash"],
                         first["provenance"]["receiptSha256"])
        self.assertEqual(other["provenance"]["previousReceiptHash"], "")
        listing = read_index(str(self.root))
        self.assertEqual(listing["total"], 3)
        self.assertEqual(archive.verify()["items"], 3)

    def test_invalid_metadata_and_receipt_digest_fail_closed(self):
        archive = self.store()
        saved = self.save(archive, "rev1")
        with sqlite3.connect(archive.path) as db:
            db.execute("""UPDATE snapshots SET display_label='tampered'
                WHERE id=?""", (saved["id"],))
        with self.assertRaisesRegex(ReadIndexError, "SNAPSHOT_PROVENANCE_INVALID"):
            read_index(str(self.root))
        with self.assertRaisesRegex(ArchiveError, "SNAPSHOT_PROVENANCE_INVALID"):
            archive.read_verified(saved["id"])
        with self.assertRaisesRegex(ArchiveError, "SNAPSHOT_PROVENANCE_INVALID"):
            archive.verify()
        with sqlite3.connect(archive.path) as db:
            db.execute("""UPDATE snapshots SET display_label='Synthetic title'
                WHERE id=?""", (saved["id"],))
            db.execute("""UPDATE snapshot_receipts SET archived_ms=archived_ms+1
                WHERE snapshot_id=?""", (saved["id"],))
        with self.assertRaisesRegex(ReadIndexError, "SNAPSHOT_PROVENANCE_INVALID"):
            read_index(str(self.root))

    def test_missing_required_receipt_refuses_instead_of_downgrading(self):
        archive = self.store()
        saved = self.save(archive, "rev1")
        with sqlite3.connect(archive.path) as db:
            db.execute("DELETE FROM snapshot_receipts WHERE snapshot_id=?",
                       (saved["id"],))
        with self.assertRaisesRegex(ReadIndexError, "SNAPSHOT_PROVENANCE_INVALID"):
            read_index(str(self.root))
        with self.assertRaisesRegex(ArchiveError, "SNAPSHOT_PROVENANCE_INVALID"):
            archive.read_verified(saved["id"])

    def test_provenance_does_not_mask_corrupted_payload(self):
        archive = self.store()
        saved = self.save(archive, "rev1")
        with sqlite3.connect(archive.path) as db:
            db.execute("UPDATE snapshots SET payload=? WHERE id=?",
                       (b"changed private payload", saved["id"]))
        page = read_index(str(self.root))["items"][0]
        self.assertEqual(page["provenance"]["state"], "RECEIPT_MATCHED")
        self.assertFalse(page["verified"])
        with self.assertRaisesRegex(ArchiveError, "SNAPSHOT_INTEGRITY_FAILED"):
            archive.read_verified(saved["id"])

    def legacy_archive(self):
        """Build a real V2a schema before V2i exists, with one old payload."""
        path = self.root / DB_NAME
        payload = b"untouched old snapshot"
        with sqlite3.connect(path) as db:
            db.execute("""CREATE TABLE archive_meta
                (id INTEGER PRIMARY KEY CHECK(id=1),schema_id TEXT NOT NULL,
                 revision INTEGER NOT NULL,payload_bytes INTEGER NOT NULL)""")
            db.execute("INSERT INTO archive_meta VALUES(1,?,?,?)",
                       (SCHEMA, 1, len(payload)))
            db.execute("""CREATE TABLE snapshots
                (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL,
                 resource_id TEXT NOT NULL,source_revision TEXT NOT NULL,
                 captured_ms INTEGER NOT NULL,display_label TEXT NOT NULL,
                 sha256 TEXT NOT NULL,payload BLOB NOT NULL,
                 UNIQUE(owner_id,resource_id,source_revision))""")
            db.execute("""INSERT INTO snapshots VALUES(?,?,?,?,?,?,?,?)""",
                       ("a" * 32, "demo-scrape", "old-page", "old-rev",
                        1760000000000, "Historical copy",
                        hashlib.sha256(payload).hexdigest(), payload))
        path.chmod(0o600)
        return payload

    def test_read_only_old_schema_lists_without_creating_receipts(self):
        payload = self.legacy_archive()
        before = (self.root / DB_NAME).read_bytes()
        indexed = read_index(str(self.root))
        self.assertEqual(indexed["total"], 1)
        self.assertEqual(indexed["items"][0]["provenance"]["state"],
                         "LEGACY_UNATTESTED")
        self.assertIn("LEGACY // NO RECEIPT", indexed["items"][0]["details"])
        self.assertEqual((self.root / DB_NAME).read_bytes(), before)
        self.assertNotIn("snapshot_receipts", before.decode("utf-8", errors="ignore"))

    def test_old_schema_migration_preserves_old_data_and_marks_legacy(self):
        payload = self.legacy_archive()
        archive = self.store()
        self.assertEqual(archive.read_verified("a" * 32), payload)
        old = read_index(str(self.root))["items"][0]
        self.assertEqual(old["provenance"], {"state": "LEGACY_UNATTESTED"})
        with sqlite3.connect(archive.path) as db:
            old_row = db.execute("""SELECT provenance_required FROM snapshots
                WHERE id=?""", ("a" * 32,)).fetchone()
            self.assertEqual(old_row, (0,))
            self.assertEqual(db.execute(
                "SELECT count(*) FROM snapshot_receipts").fetchone()[0], 0)
        new = self.save(archive, "rev2")
        page = read_index(str(self.root))["items"]
        states = {row["id"]: row["provenance"]["state"] for row in page}
        self.assertEqual(states["a" * 32], "LEGACY_UNATTESTED")
        self.assertEqual(states[new["id"]], "RECEIPT_MATCHED")
        self.assertEqual(archive.read_verified("a" * 32), payload)
        self.assertEqual(archive.verify()["items"], 2)

    def test_canonical_receipts_deterministic_and_not_signed(self):
        args = ("b" * 32, "demo-scrape", "source-1", "rev1",
                1760000000000, 1760001000000, "Title", "c" * 64, "")
        a = create_receipt(*args)
        b = create_receipt(*args)
        self.assertEqual(a, b)
        self.assertEqual(a["schema"], RECEIPT_SCHEMA)
        self.assertNotIn("signature", a)
        snapshot = (args[0], args[1], args[2], args[3], args[4], args[6],
                    args[7], 1)
        fields = (args[0], args[1], args[2], args[3], args[4], args[5],
                  args[6], args[7], args[8], a["receiptSha256"], RECEIPT_SCHEMA)
        self.assertEqual(verify_receipt(snapshot, fields)["state"],
                         "RECEIPT_MATCHED")
        with self.assertRaisesRegex(ProvenanceError,
                                    "SNAPSHOT_PROVENANCE_INVALID"):
            create_receipt(*args[:6], "bad\nlabel", *args[7:])

    def test_no_copy_restore_burn_or_signer(self):
        from scripts.trash import archive_v2_provenance as codec
        for action in ("delete", "trash", "restore", "burn", "sign", "migrate"):
            self.assertFalse(hasattr(codec, action))
        self.assertFalse(hasattr(codec, "main"))


if __name__ == "__main__":
    unittest.main()
