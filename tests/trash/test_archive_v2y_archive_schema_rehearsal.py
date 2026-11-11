"""V2y migration rehearsal against actual ArchiveStore tables in a fixture.

This module never opens the user's Archive. Only a separately initialized
private, named test directory plus explicit marker is accepted.
"""
import hashlib
import os
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

import test_archive_v2_single_db_fixture as v2x_fixture
from test_archive_v2_fixture_service_identity import PAYLOAD
from scripts.trash.archive_store_v2 import ArchiveStore, DB_NAME
from scripts.trash.archive_v2y_archive_schema_rehearsal import (
    ArchiveMigrationRefused, MARKER, MARKER_CONTENT,
    TestArchiveStoreAdmissionV2y,
)

NOW = 1760000500000
OLD_PAYLOAD = b"preserve-this-older-source-copy"


class ArchiveStoreMigrationV2yTests(unittest.TestCase):
    def setUp(self):
        self.v2x = v2x_fixture.SignedQuotaCommitV2xTests("runTest")
        self.v2x.setUp()
        self.addCleanup(self.v2x.doCleanups)
        self.root = self.v2x.floor_fixture.directory / "trashpp-v2y-fixture-archive"
        self.root.mkdir(mode=0o700)
        self.marker = self.root / MARKER
        self.marker.write_bytes(MARKER_CONTENT)
        self.marker.chmod(0o600)
        self.archive = ArchiveStore(self.root)
        self.old = self.archive.save(
            "demo-scrape","legacy-resource","old-revision",
            OLD_PAYLOAD,display_label="Older archive copy",
            captured_ms=1760000000000)
        self.bridge = TestArchiveStoreAdmissionV2y(self.archive)
        self.baseline = self.archive.status()

    def pair(self, **kwargs):
        return self.v2x.signed_pair(**kwargs)

    def admit(self, *, pair=None, payload=PAYLOAD, bridge=None,
              label="Private fixture", on_stage=None, reader=None):
        if pair is None:
            pair=self.pair(payload=payload,label=label)
        return (self.bridge if bridge is None else bridge).admit(
            pair[0],self.v2x.capture_policy,
            pair[1],self.v2x.receipt_key,payload,label,
            floor_reader=self.v2x.floor if reader is None else reader,
            history=self.v2x.floor_fixture.previous.history,
            signed_release=self.v2x.floor_fixture.previous.signed(),
            release_root=self.v2x.owner.trust_root,
            grant_sha256=self.v2x.floor_fixture.previous.grant_sha,
            now_ms=NOW,on_stage=on_stage)

    def recovered(self, nonce="a"*32, bridge=None):
        return (self.bridge if bridge is None else bridge).inspect(
            "demo-scrape","test-source",nonce,self.v2x.receipt_key)

    def counts(self):
        with sqlite3.connect(self.root/DB_NAME) as db:
            return tuple(db.execute("SELECT COUNT(*) FROM "+t).fetchone()[0]
                         for t in (
                             "snapshots","snapshot_receipts",
                             "fixture_signed_admissions"))

    def test_additive_migration_preserves_old_bytes_and_unsigned_status(self):
        self.assertEqual(self.archive.read_verified(self.old["id"]),OLD_PAYLOAD)
        self.assertEqual(self.archive.status()["revision"],
                         self.baseline["revision"])
        self.assertEqual(self.counts(),(1,1,0))
        with sqlite3.connect(self.root/DB_NAME) as db:
            legacy=db.execute("""SELECT s.provenance_required,r.receipt_schema
                FROM snapshots s JOIN snapshot_receipts r
                ON s.id=r.snapshot_id WHERE s.id=?""",
                (self.old["id"],)).fetchone()
        self.assertEqual(legacy[0],1)
        self.assertEqual(legacy[1],"post-apollo.trash-archive.receipt.v2i")
        self.assertEqual(
            TestArchiveStoreAdmissionV2y(self.archive).archive.status(),
            self.baseline)

    def test_one_transaction_adds_signed_fixture_to_actual_archive_schema(self):
        result=self.admit()
        self.assertEqual(result["state"],
                         "TEST_ARCHIVESTORE_SCHEMA_ADMITTED_DENY_ONLY")
        self.assertEqual(self.archive.read_verified("a"*32),PAYLOAD)
        self.assertEqual(self.counts(),(2,2,1))
        status=self.archive.status()
        self.assertEqual(status["revision"],self.baseline["revision"]+1)
        self.assertEqual(status["payloadBytes"],
                         self.baseline["payloadBytes"]+len(PAYLOAD))
        recovered=self.recovered()
        self.assertTrue(recovered["payloadIntegrityVerified"])
        self.assertEqual(recovered["signedReceiptSha256"],
                         result["signedReceiptSha256"])
        self.assertFalse(recovered["sourceAuthorityVerified"])
        self.assertFalse(recovered["archiveCopyAuthorized"])
        self.assertFalse(recovered["productionAllowed"])
        self.assertEqual(self.archive.read_verified(self.old["id"]),OLD_PAYLOAD)
        self.assertFalse((self.root/"trashpp-v2x-test-archive.sqlite3").exists())

    def test_migration_only_adds_tables_and_does_not_backfill_old_snapshots(self):
        before=self.archive.read_verified(self.old["id"])
        self.admit()
        with sqlite3.connect(self.root/DB_NAME) as db:
            legacy=db.execute("""SELECT COUNT(*) FROM fixture_signed_admissions
                WHERE snapshot_id=?""",(self.old["id"],)).fetchone()[0]
            tables={r[0] for r in db.execute("""SELECT name FROM sqlite_master
                WHERE type='table'""")}
        self.assertEqual(legacy,0)
        self.assertIn("fixture_signed_admissions",tables)
        self.assertIn("archive_meta",tables)
        self.assertEqual(self.archive.read_verified(self.old["id"]),before)

    def test_replay_refuses_and_preserves_existing_quota_and_record(self):
        self.admit()
        with self.assertRaisesRegex(ArchiveMigrationRefused,
                                    "V2Y_NONCE_ALREADY_CONSUMED"):
            self.admit()
        self.assertEqual(self.counts(),(2,2,1))
        self.assertEqual(self.archive.status()["revision"],
                         self.baseline["revision"]+1)

    def test_transaction_rolls_back_each_injected_precommit_failure(self):
        for stage in ("after_copy","after_local_receipt",
                      "after_signed_receipt","after_accounting"):
            with self.subTest(stage=stage):
                def abort(current):
                    if current==stage:
                        raise RuntimeError("injected "+stage)
                with self.assertRaisesRegex(RuntimeError,"injected"):
                    self.admit(on_stage=abort)
                self.assertEqual(self.counts(),(1,1,0))
                self.assertEqual(self.archive.status(),self.baseline)
                self.assertEqual(self.recovered()["state"],
                                 "TEST_NOT_ADMITTED")
        self.assertTrue(self.admit()["state"].endswith("DENY_ONLY"))

    def test_lost_reply_after_commit_is_recovered_without_duplicate(self):
        def disconnect(stage):
            if stage=="after_commit":
                raise ConnectionError("reply lost after commit")
        with self.assertRaisesRegex(ConnectionError,"reply lost"):
            self.admit(on_stage=disconnect)
        reopened_archive=ArchiveStore(self.root)
        reopened=TestArchiveStoreAdmissionV2y(reopened_archive)
        result=self.recovered(bridge=reopened)
        self.assertTrue(result["payloadIntegrityVerified"])
        with self.assertRaisesRegex(ArchiveMigrationRefused,
                                    "V2Y_NONCE_ALREADY_CONSUMED"):
            self.admit(bridge=reopened)
        self.assertEqual(self.counts(),(2,2,1))

    def test_payload_quota_enforced_with_old_snapshot_bytes_in_same_counter(self):
        self.archive.payload_quota = (
            self.baseline["payloadBytes"]+len(PAYLOAD)-1)
        with self.assertRaisesRegex(ArchiveMigrationRefused,
                                    "V2Y_ARCHIVE_PAYLOAD_QUOTA"):
            self.admit()
        self.assertEqual(self.archive.status(),self.baseline)
        self.archive.payload_quota = 512*1024*1024
        self.assertEqual(self.admit()["snapshotId"],"a"*32)

    def test_low_disk_quota_fails_before_any_signed_copy(self):
        self.archive.disk_quota=64*1024
        huge = b"synthetic but never user bytes" * 2000
        pair=self.pair(payload=huge)
        with self.assertRaisesRegex(ArchiveMigrationRefused,
                                    "V2Y_ARCHIVE_DISK_QUOTA"):
            self.admit(pair=pair,payload=huge)
        self.assertEqual(self.counts(),(1,1,0))
        self.assertEqual(self.archive.status()["revision"],
                         self.baseline["revision"])

    def test_external_floor_change_inside_transaction_rolls_back(self):
        def revoke(stage):
            if stage=="after_accounting":
                self.v2x.floor_fixture.write_floor(
                    floor=dict(self.v2x.floor_fixture.floor,epoch=2))
        with self.assertRaisesRegex(ArchiveMigrationRefused,
                                    "V2Y_FLOOR_REFUSED"):
            self.admit(on_stage=revoke)
        self.assertEqual(self.counts(),(1,1,0))
        self.assertEqual(self.archive.status(),self.baseline)

    def test_signed_label_and_source_mismatch_never_write(self):
        pair=self.pair()
        with self.assertRaisesRegex(ArchiveMigrationRefused,
                                    "V2Y_SOURCE_RECEIPT_BINDING_INVALID"):
            self.admit(pair=pair,label="modified after signing")
        with self.assertRaises(Exception):
            self.admit(pair=pair,payload=b"changed")
        self.assertEqual(self.counts(),(1,1,0))

    def test_source_revision_conflict_does_not_destroy_legacy_copy(self):
        first=self.admit()
        pair=self.pair(nonce="b"*32,revision="1"*64,
                       snapshot_id="b"*32,
                       parent=first["localReceiptSha256"])
        with self.assertRaisesRegex(ArchiveMigrationRefused,
                                    "V2Y_NONCE_OR_SNAPSHOT_REPLAY"):
            self.admit(pair=pair)
        self.assertEqual(self.counts(),(2,2,1))
        self.assertEqual(self.archive.read_verified(self.old["id"]),OLD_PAYLOAD)

    def test_recovery_rejects_broken_linked_provenance_or_signed_receipt(self):
        self.admit()
        with sqlite3.connect(self.root/DB_NAME) as db:
            db.execute("""UPDATE fixture_signed_admissions
                SET signature_b64='invalid' WHERE snapshot_id=?""",
                ("a"*32,))
        with self.assertRaises(Exception):
            self.recovered()
        with sqlite3.connect(self.root/DB_NAME) as db:
            db.execute("""UPDATE snapshots SET payload=? WHERE id=?""",
                       (b"corrupted","a"*32))
        with self.assertRaisesRegex(ArchiveMigrationRefused,
                                    "V2Y_RECOVERY_INTEGRITY_INVALID"):
            self.recovered()

    def test_missing_snapshots_or_receipts_after_nonce_is_corruption(self):
        self.admit()
        with sqlite3.connect(self.root/DB_NAME) as db:
            db.execute("PRAGMA foreign_keys=OFF")
            db.execute("DELETE FROM snapshot_receipts WHERE snapshot_id=?",
                       ("a"*32,))
        with self.assertRaisesRegex(ArchiveMigrationRefused,
                                    "V2Y_RECOVERY_INTEGRITY_INVALID"):
            self.recovered()

    def test_marker_missing_symlink_or_unmarked_root_never_migrates(self):
        self.marker.unlink()
        with self.assertRaisesRegex(ArchiveMigrationRefused,
                                    "V2Y_FIXTURE_MARKER_MISSING"):
            TestArchiveStoreAdmissionV2y(self.archive)
        self.marker.symlink_to(self.root/DB_NAME)
        with self.assertRaisesRegex(ArchiveMigrationRefused,
                                    "V2Y_FIXTURE_MARKER_MISSING"):
            TestArchiveStoreAdmissionV2y(self.archive)
        self.marker.unlink()
        with self.assertRaisesRegex(ArchiveMigrationRefused,
                                    "V2Y_FIXTURE_ROOT_REQUIRED"):
            TestArchiveStoreAdmissionV2y(ArchiveStore(
                self.v2x.floor_fixture.directory))

    def test_malformed_existing_signed_admission_schema_refused(self):
        with sqlite3.connect(self.root/DB_NAME) as db:
            db.execute("DROP TABLE fixture_signed_admissions")
            db.execute("CREATE TABLE fixture_signed_admissions("
                       "snapshot_id TEXT PRIMARY KEY)")
        with self.assertRaisesRegex(ArchiveMigrationRefused,
                                    "V2Y_ADMISSION_SCHEMA_UNSUPPORTED"):
            TestArchiveStoreAdmissionV2y(self.archive)
        self.assertEqual(self.archive.read_verified(self.old["id"]),OLD_PAYLOAD)

    def test_no_live_archive_writer_or_production_activation(self):
        from scripts.trash import archive_v2y_archive_schema_rehearsal as module
        source=Path(module.__file__).read_text("utf-8")
        for blocked in ("Ed25519PrivateKey", "quickshell", "systemctl",
                        "gio trash","archive_v2_capture_cli"):
            self.assertNotIn(blocked,source)
        self.assertFalse(hasattr(module,"main"))
        self.assertFalse(hasattr(module,"serve_forever"))
        self.assertFalse((self.root/"trashpp-v2x-test-archive.sqlite3").exists())


if __name__=="__main__":
    unittest.main()
