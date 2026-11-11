"""Synthetic V2j full-chain audit, read-only and unsigned by design."""
from contextlib import redirect_stdout
from unittest.mock import patch
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from scripts.trash.archive_store_v2 import ArchiveStore, DB_NAME, SCHEMA
from scripts.trash.archive_v2_provenance import (
    RECEIPT_SCHEMA, create_receipt,
)
from scripts.trash import archive_v2_chain_audit as checker

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/trash/archive_v2_chain_audit.py"


class ChainAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def store(self):
        return ArchiveStore(self.root)

    def save(self, store, resource, revision, owner="demo-scrape"):
        return store.save(owner, resource, revision,
                          ("PRIVATE:"+resource+revision).encode(),
                          display_label="test sample",
                          captured_ms=1760000000000)

    def report(self):
        return checker.audit(str(self.root))

    def test_empty_reader_creates_no_archive(self):
        before = set(self.root.iterdir())
        self.assertEqual(self.report()["state"], "NOT_INSTALLED")
        self.assertEqual(set(self.root.iterdir()), before)

    def test_global_chain_across_sources_counts_legacy_and_receipts(self):
        store = self.store()
        a = self.save(store, "demo-1", "rev1")
        b = self.save(store, "demo-1", "rev2")
        self.save(store, "demo-2", "rev1")
        self.save(store, "weather-1", "rev1", "weather-events")
        report = self.report()
        self.assertEqual(report["state"], "CHAIN_CONSISTENT")
        self.assertEqual(report["receiptCount"], 4)
        self.assertEqual(report["snapshotCount"], 4)
        self.assertEqual(report["legacyCount"], 0)
        self.assertEqual(report["sourceCount"], 3)
        self.assertFalse(report["payloadVerified"])
        self.assertEqual(report["authentication"], "UNSIGNED_LOCAL")
        self.assertEqual(report["completeness"], "DATABASE_LOCAL_ONLY")
        self.assertNotIn("PRIVATE", json.dumps(report))
        self.assertEqual(b["provenance"]["previousReceiptHash"],
                         a["provenance"]["receiptSha256"])

    def test_skipped_predecessor_with_recomputed_receipt_is_detected(self):
        store = self.store()
        self.save(store, "demo-1", "rev1")
        b = self.save(store, "demo-1", "rev2")
        with sqlite3.connect(store.path) as db:
            current = db.execute("""SELECT s.id,s.owner_id,s.resource_id,
                s.source_revision,s.captured_ms,r.archived_ms,s.display_label,
                s.sha256 FROM snapshots s JOIN snapshot_receipts r
                ON r.snapshot_id=s.id WHERE s.id=?""",
                (b["id"],)).fetchone()
            forged = create_receipt(*current, previous="")
            # Rehashing a record can pass a single-receipt verification.
            db.execute("""UPDATE snapshot_receipts
                SET previous_receipt_sha256='',receipt_sha256=?
                WHERE snapshot_id=?""", (forged["receiptSha256"], b["id"]))
        with self.assertRaisesRegex(checker.ChainAuditError,
                                    "ARCHIVE_CHAIN_LINK_INVALID"):
            self.report()

    def test_cross_source_predecessor_is_detected_even_with_valid_hash(self):
        store = self.store()
        earlier = self.save(store, "source-A", "rev1")
        second = self.save(store, "source-B", "rev1")
        with sqlite3.connect(store.path) as db:
            current = db.execute("""SELECT s.id,s.owner_id,s.resource_id,
                s.source_revision,s.captured_ms,r.archived_ms,s.display_label,
                s.sha256 FROM snapshots s JOIN snapshot_receipts r
                ON r.snapshot_id=s.id WHERE s.id=?""",
                (second["id"],)).fetchone()
            foreign = earlier["provenance"]["receiptSha256"]
            forged = create_receipt(*current, previous=foreign)
            db.execute("""UPDATE snapshot_receipts
                SET previous_receipt_sha256=?,receipt_sha256=?
                WHERE snapshot_id=?""",
                (foreign, forged["receiptSha256"], second["id"]))
        with self.assertRaisesRegex(checker.ChainAuditError,
                                    "ARCHIVE_CHAIN_LINK_INVALID"):
            self.report()

    def test_missing_required_receipt_fails_closed(self):
        store = self.store()
        snap = self.save(store, "item", "rev1")
        with sqlite3.connect(store.path) as db:
            db.execute("DELETE FROM snapshot_receipts WHERE snapshot_id=?",
                       (snap["id"],))
        with self.assertRaisesRegex(checker.ChainAuditError,
                                    "SNAPSHOT_PROVENANCE_INVALID"):
            self.report()

    def test_orphan_receipt_is_rejected(self):
        store = self.store()
        self.save(store, "item", "rev1")
        with sqlite3.connect(store.path) as db:
            db.execute("""INSERT INTO snapshot_receipts
                (snapshot_id,owner_id,resource_id,source_revision,
                source_captured_ms,archived_ms,display_label,payload_sha256,
                previous_receipt_sha256,receipt_sha256,receipt_schema)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                ("f"*32,"demo-scrape","orphan","rev1",1760000000000,
                 1760000000001,"orphan",hashlib.sha256(b"orphan").hexdigest(),
                 "","f"*64,RECEIPT_SCHEMA))
        with self.assertRaisesRegex(checker.ChainAuditError,
                                    "ARCHIVE_ORPHAN_RECEIPT"):
            self.report()

    def test_tampered_owner_resource_or_receipt_fails(self):
        store = self.store()
        snap = self.save(store, "item", "rev1")
        with sqlite3.connect(store.path) as db:
            db.execute("""UPDATE snapshot_receipts SET resource_id='other'
                WHERE snapshot_id=?""", (snap["id"],))
        with self.assertRaisesRegex(checker.ChainAuditError,
                                    "SNAPSHOT_PROVENANCE_INVALID"):
            self.report()

    def test_legacy_database_is_read_without_schema_writes(self):
        path = self.root / DB_NAME
        payload = b"legacy synthetic"
        with sqlite3.connect(path) as db:
            db.execute("""CREATE TABLE archive_meta
                (id INTEGER PRIMARY KEY, schema_id TEXT,
                 revision INTEGER,payload_bytes INTEGER)""")
            db.execute("INSERT INTO archive_meta VALUES (1,?,?,?)",
                       (SCHEMA,1,len(payload)))
            db.execute("""CREATE TABLE snapshots (
                id TEXT PRIMARY KEY,owner_id TEXT,resource_id TEXT,
                source_revision TEXT,captured_ms INTEGER,display_label TEXT,
                sha256 TEXT,payload BLOB,
                UNIQUE(owner_id,resource_id,source_revision))""")
            db.execute("INSERT INTO snapshots VALUES (?,?,?,?,?,?,?,?)",
                       ("a"*32,"demo-scrape","legacy","rev1",
                        1760000000000,"Legacy page",
                        hashlib.sha256(payload).hexdigest(),payload))
        path.chmod(0o600)
        before = path.read_bytes()
        result = self.report()
        self.assertEqual(result["state"], "LEGACY_ONLY")
        self.assertEqual(result["snapshotCount"], 1)
        self.assertEqual(result["legacyCount"], 1)
        self.assertEqual(result["receiptCount"], 0)
        self.assertEqual(result["sourceCount"], 1)
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse((self.root / (DB_NAME+"-journal")).exists())

    def test_legacy_after_receipt_refused(self):
        store = self.store()
        self.save(store, "source-1", "rev1")
        with sqlite3.connect(store.path) as db:
            payload = b"unexpected unsigned row"
            db.execute("""INSERT INTO snapshots
                (id,owner_id,resource_id,source_revision,captured_ms,
                 display_label,sha256,payload,provenance_required)
                VALUES(?,?,?,?,?,?,?,?,0)""",
                ("b"*32,"demo-scrape","source-1","rev2",
                 1760000000001,"Unsanctioned legacy",
                 hashlib.sha256(payload).hexdigest(),payload))
        with self.assertRaisesRegex(checker.ChainAuditError, "ARCHIVE_CHAIN_GAP"):
            self.report()

    def test_mixed_preexisting_legacy_then_v2i_receipts(self):
        store = self.store()
        early = self.save(store, "source-1", "rev1")
        # Simulate a legacy source with its own earlier row in a *different*
        # owner/resource. No fake receipt added to that row.
        with sqlite3.connect(store.path) as db:
            payload = b"older"
            db.execute("""INSERT INTO snapshots
                (id,owner_id,resource_id,source_revision,captured_ms,
                 display_label,sha256,payload,provenance_required)
                VALUES(?,?,?,?,?,?,?,?,0)""",
                ("c"*32,"demo-scrape","legacy-only","rev0",
                 1760000000000,"Legacy",
                 hashlib.sha256(payload).hexdigest(),payload))
        result = self.report()
        self.assertEqual((result["snapshotCount"],result["receiptCount"],
                          result["legacyCount"],result["sourceCount"]),
                         (2,1,1,2))

    def test_limit_refuses_instead_of_partial_success(self):
        store = self.store()
        self.save(store, "item", "rev1")
        self.save(store, "item", "rev2")
        with patch.object(checker, "MAX_RECORDS", 1):
            with self.assertRaisesRegex(checker.ChainAuditError,
                                        "ARCHIVE_AUDIT_LIMIT"):
                self.report()
        self.assertEqual(self.report()["receiptCount"], 2)

    def test_cli_isolated_and_only_has_read_only_audit_verb(self):
        store = self.store()
        self.save(store, "item", "rev1")
        command = [sys.executable, "-I", "-B", str(SCRIPT),
                   "audit", str(self.root)]
        proc = subprocess.run(command, capture_output=True, text=True,
                              timeout=10)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        reply = json.loads(proc.stdout)
        self.assertEqual(reply["receiptCount"], 1)
        for verb in ("burn", "restore", "archive", "save", "migrate"):
            out = io.StringIO()
            with redirect_stdout(out):
                status = checker.main(["audit.py", verb, str(self.root)])
            self.assertNotEqual(status, 0)
            self.assertEqual(json.loads(out.getvalue())["error"],
                             "READ_ONLY_AUDIT_ONLY")

    def test_malformed_schema_fails_without_migration(self):
        store = self.store()
        self.save(store, "item", "rev1")
        with sqlite3.connect(store.path) as db:
            db.execute("DROP TABLE snapshot_receipts")
        with self.assertRaisesRegex(checker.ChainAuditError,
                                    "ARCHIVE_PROVENANCE_SCHEMA_INVALID"):
            self.report()


if __name__ == "__main__":
    unittest.main()
