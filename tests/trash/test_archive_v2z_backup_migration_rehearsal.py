"""V2z ArchiveStore safety backup, staged migration and rollback tests.

All SQLite writes are made in temporary 0700 fixtures. There is no
production Archive path, service, capture, private key or authority here.
"""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from scripts.trash.archive_store_v2 import ArchiveStore, DB_NAME
from scripts.trash.archive_v2z_backup_migration_rehearsal import (
    BACKUP, MANIFEST, SOURCE_MARKER, SOURCE_MARKER_BYTES,
    MigrationSafetyRefused, TestMigrationSafetyV2z,
)

# Legacy records were initially stored without a V2i signature or receipt.
TEST_BYTES = b"private disposable Archive snapshot, never owner material"
SECOND_BYTES = b"second owner fixture, different source record"


class TestBackupAndMigrationSafetyV2z(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.parent = Path(t.name)
        self.src = self.parent / "trashpp-v2z-fixture-source"
        self.dst = self.parent / "trashpp-v2z-backups-separate"
        self.src.mkdir(mode=0o700)
        self.dst.mkdir(mode=0o700)
        self.marker = self.src / SOURCE_MARKER
        self.marker.write_bytes(SOURCE_MARKER_BYTES)
        self.marker.chmod(0o600)
        self.archive = ArchiveStore(self.src)
        self.first = self.archive.save(
            "demo-scrape", "legacy-page", "version1", TEST_BYTES,
            display_label="Original local receipt",
            captured_ms=1760000000000)
        self.second = self.archive.save(
            "weather-events", "weather-page", "version1", SECOND_BYTES,
            display_label="Second independent owner",
            captured_ms=1760000000001)
        self.before = self.archive.verify()
        self.plan = TestMigrationSafetyV2z(self.archive,self.dst)

    def test_seal_backup_and_migrate_stage_without_touching_original(self):
        sealed = self.plan.seal_backup()
        self.assertEqual(sealed["state"],
                         "TEST_SEALED_BACKUP_VERIFIED_DENY_ONLY")
        self.assertEqual(sealed["items"],2)
        self.assertEqual(sealed["payloadBytes"],
                         len(TEST_BYTES)+len(SECOND_BYTES))
        self.assertEqual(len(sealed["backupSha256"]),64)
        self.assertFalse(sealed["productionAllowed"])
        staged = self.plan.rehearse_schema()
        self.assertTrue(staged["stageSchemaVerified"])
        self.assertTrue(staged["legacyRecordsPreserved"])
        self.assertFalse(staged["captureAllowed"])
        self.assertFalse(staged["productionAllowed"])
        stage_db=self.dst/"trashpp-v2y-fixture-stage"/DB_NAME
        with sqlite3.connect(stage_db) as db:
            count=db.execute("SELECT count(*) FROM fixture_signed_admissions").fetchone()[0]
            self.assertEqual(count,0)
            self.assertEqual(db.execute(
                "SELECT count(*) FROM snapshots").fetchone()[0],2)
        self.assertEqual(self.archive.verify(),self.before)
        self.assertEqual(self.archive.read_verified(self.first["id"]),TEST_BYTES)
        self.assertEqual(self.archive.read_verified(self.second["id"]),SECOND_BYTES)

    def test_recover_from_unchanged_sealed_backup_without_touching_stage(self):
        sealed=self.plan.seal_backup()
        self.plan.rehearse_schema()
        stage=self.dst/"trashpp-v2y-fixture-stage"/DB_NAME
        with sqlite3.connect(stage) as db:
            db.execute("UPDATE snapshots SET payload=? WHERE id=?",
                       (b"damaged-stage",self.first["id"]))
        recovered=self.plan.rehearse_recovery()
        self.assertEqual(recovered["state"],
                         "TEST_ISOLATED_RECOVERY_VERIFIED_DENY_ONLY")
        self.assertEqual(recovered["restoredItems"],2)
        self.assertEqual(recovered["backupSha256"],sealed["backupSha256"])
        self.assertTrue((self.dst/"trashpp-v2y-fixture-recovery"/DB_NAME).exists())
        self.assertEqual(self.archive.verify(),self.before)
        self.assertFalse(recovered["restoreAllowed"])

    def test_prior_pre_v2i_snapshot_remains_explicitly_unattested(self):
        with sqlite3.connect(self.src/DB_NAME) as db:
            db.execute("DELETE FROM snapshot_receipts WHERE snapshot_id=?",
                       (self.first["id"],))
            db.execute("UPDATE snapshots SET provenance_required=0 WHERE id=?",
                       (self.first["id"],))
        self.assertTrue(self.archive.verify()["verified"])
        self.plan.seal_backup()
        self.plan.rehearse_schema()
        staged=self.dst/"trashpp-v2y-fixture-stage"/DB_NAME
        with sqlite3.connect(staged) as db:
            status=db.execute("""SELECT provenance_required FROM snapshots
                WHERE id=?""",(self.first["id"],)).fetchone()
            receipt=db.execute("""SELECT count(*) FROM snapshot_receipts
                WHERE snapshot_id=?""",(self.first["id"],)).fetchone()
        self.assertEqual(status,(0,))
        self.assertEqual(receipt,(0,))
        self.assertEqual(self.archive.read_verified(self.first["id"]),TEST_BYTES)

    def test_aborted_backup_cannot_be_misrepresented_as_sealed(self):
        def crash(step):
            if step == "before_seal":
                raise RuntimeError("simulated backup crash")
        with self.assertRaisesRegex(RuntimeError,"backup crash"):
            self.plan.seal_backup(on_stage=crash)
        self.assertTrue((self.dst/BACKUP).exists())
        self.assertFalse((self.dst/MANIFEST).exists())
        with self.assertRaises(MigrationSafetyRefused):
            self.plan.verify_backup()
        with self.assertRaises(MigrationSafetyRefused):
            self.plan.rehearse_schema()
        self.assertEqual(self.archive.verify(),self.before)

    def test_source_changed_during_backup_refused_even_after_copy(self):
        def concurrent_writer(step):
            if step == "after_backup_copy":
                self.archive.save(
                    "demo-scrape","new-resource","new-version",
                    b"concurrent synthetic update",
                    captured_ms=1760000001000)
        with self.assertRaisesRegex(MigrationSafetyRefused,
                                    "V2Z_SOURCE_CHANGED_DURING_BACKUP"):
            self.plan.seal_backup(on_stage=concurrent_writer)
        self.assertFalse((self.dst/MANIFEST).exists())
        self.assertEqual(self.archive.verify()["items"],3)

    def test_migration_exception_leaves_source_and_backup_safe_to_recover(self):
        sealed=self.plan.seal_backup()
        def abort(step):
            if step=="after_stage_migration":
                raise RuntimeError("injected migration failure")
        with self.assertRaisesRegex(RuntimeError,"migration failure"):
            self.plan.rehearse_schema(on_stage=abort)
        self.assertEqual(self.plan.verify_backup()["backupSha256"],
                         sealed["backupSha256"])
        self.assertEqual(self.plan.rehearse_recovery()["restoredItems"],2)
        self.assertEqual(self.archive.verify(),self.before)

    def test_tampered_backup_bytes_refused_even_with_valid_manifest(self):
        self.plan.seal_backup()
        with sqlite3.connect(self.dst/BACKUP) as db:
            db.execute("UPDATE snapshots SET payload=? WHERE id=?",
                       (b"wrong contents",self.first["id"]))
        with self.assertRaisesRegex(MigrationSafetyRefused,
                                    "V2Z_BACKUP_HASH_MISMATCH"):
            self.plan.verify_backup()
        self.assertEqual(self.archive.verify(),self.before)

    def test_manifest_tampering_or_missing_fields_refused(self):
        self.plan.seal_backup()
        path=self.dst/MANIFEST
        content=json.loads(path.read_text("ascii"))
        content["backupSha256"]="a"*64
        path.write_text(json.dumps(content,sort_keys=True,
                     separators=(",",":")),encoding="ascii")
        path.chmod(0o600)
        with self.assertRaisesRegex(MigrationSafetyRefused,
                                    "V2Z_BACKUP_HASH_MISMATCH"):
            self.plan.verify_backup()
        del content["backupSha256"]
        path.write_text(json.dumps(content,sort_keys=True,
                     separators=(",",":")),encoding="ascii")
        with self.assertRaisesRegex(MigrationSafetyRefused,
                                    "V2Z_MANIFEST_INVALID"):
            self.plan.verify_backup()

    def test_unknown_schema_or_payload_corruption_refuses_before_backup(self):
        with sqlite3.connect(self.src/DB_NAME) as db:
            db.execute("CREATE TABLE unrelated_owner_table(id INTEGER)")
        with self.assertRaisesRegex(MigrationSafetyRefused,"V2Z_SCHEMA_UNKNOWN"):
            self.plan.seal_backup()
        self.assertFalse((self.dst/BACKUP).exists())
        with sqlite3.connect(self.src/DB_NAME) as db:
            db.execute("DROP TABLE unrelated_owner_table")
            db.execute("UPDATE snapshots SET payload=? WHERE id=?",
                       (b"corrupted",self.first["id"]))
        with self.assertRaisesRegex(MigrationSafetyRefused,
                                    "V2Z_PAYLOAD_CORRUPT"):
            self.plan.seal_backup()
        self.assertFalse((self.dst/BACKUP).exists())

    def test_receipt_and_chain_tampering_refuses_preflight(self):
        with sqlite3.connect(self.src/DB_NAME) as db:
            db.execute("UPDATE snapshot_receipts SET receipt_sha256=? WHERE snapshot_id=?",
                       ("0"*64,self.first["id"]))
        with self.assertRaisesRegex(MigrationSafetyRefused,
                                    "V2Z_RECEIPT_CORRUPT"):
            self.plan.seal_backup()
        self.assertFalse((self.dst/BACKUP).exists())

    def test_missing_source_marker_wrong_root_and_workspace_refused(self):
        self.marker.unlink()
        with self.assertRaises(MigrationSafetyRefused):
            TestMigrationSafetyV2z(self.archive,self.dst)
        self.marker.write_bytes(SOURCE_MARKER_BYTES)
        self.marker.chmod(0o600)
        wrong=self.parent/"ordinary-user-archive"
        wrong.mkdir(mode=0o700)
        with self.assertRaisesRegex(MigrationSafetyRefused,
                                    "V2Z_TEST_ROOT_REQUIRED"):
            TestMigrationSafetyV2z(ArchiveStore(wrong),self.dst)
        nested=self.src/"trashpp-v2z-backups-nested"
        nested.mkdir(mode=0o700)
        with self.assertRaisesRegex(MigrationSafetyRefused,
                                    "V2Z_WORKSPACE_NOT_SEPARATE"):
            TestMigrationSafetyV2z(self.archive,nested)

    def test_symlink_marker_or_world_writable_workspace_refused(self):
        self.marker.unlink()
        target=self.src/"marker-target"
        target.write_bytes(SOURCE_MARKER_BYTES)
        target.chmod(0o600)
        self.marker.symlink_to(target)
        with self.assertRaises(MigrationSafetyRefused):
            TestMigrationSafetyV2z(self.archive,self.dst)
        self.marker.unlink()
        self.marker.write_bytes(SOURCE_MARKER_BYTES)
        self.marker.chmod(0o600)
        self.dst.chmod(0o777)
        self.addCleanup(self.dst.chmod,0o700)
        with self.assertRaisesRegex(MigrationSafetyRefused,
                                    "V2Z_TEST_ROOT_UNSAFE"):
            TestMigrationSafetyV2z(self.archive,self.dst)

    def test_repeat_backup_rehearsal_or_recovery_never_overwrites(self):
        self.plan.seal_backup()
        with self.assertRaisesRegex(MigrationSafetyRefused,"V2Z_ARTIFACT_EXISTS"):
            self.plan.seal_backup()
        self.plan.rehearse_schema()
        with self.assertRaisesRegex(MigrationSafetyRefused,"V2Z_STAGE_EXISTS"):
            self.plan.rehearse_schema()
        self.plan.rehearse_recovery()
        with self.assertRaisesRegex(MigrationSafetyRefused,"V2Z_STAGE_EXISTS"):
            self.plan.rehearse_recovery()
        self.assertEqual(self.archive.verify(),self.before)

    def test_recovery_does_not_need_production_authority_or_delete_staging(self):
        self.plan.seal_backup()
        result=self.plan.rehearse_recovery()
        self.assertFalse(result["productionAllowed"])
        self.assertFalse(result["captureAllowed"])
        self.assertFalse(result["restoreAllowed"])
        self.assertFalse(result["burnAllowed"])
        self.assertFalse(result["originalArchiveModified"])
        self.assertFalse((self.src/"fixture_signed_admissions").exists())
        self.assertFalse((self.src/"trashpp-v2y-fixture-stage").exists())

    def test_no_cli_live_service_backup_writer_or_authorization(self):
        from scripts.trash import archive_v2z_backup_migration_rehearsal as module
        source=Path(module.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "Ed25519PrivateKey", "systemctl", "Quickshell.dataDir",
            "gio trash", ".bind(", ".listen(", "archive_v2_capture_cli",
        ):
            self.assertNotIn(forbidden,source)
        self.assertFalse(hasattr(module,"main"))
        self.assertFalse(hasattr(module,"serve_forever"))


if __name__=="__main__":
    unittest.main()
