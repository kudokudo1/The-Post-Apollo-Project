"""Trash++ V3a // actual disposable V2z outputs and hostile cutover claims.

The existing V2z fixture creates the only SQLite files; this new module
performs no writes, signer setup, service activation, or real migration.
"""
import copy
from pathlib import Path
import tempfile
import unittest

from scripts.trash.archive_store_v2 import ArchiveStore
from scripts.trash.archive_v2z_backup_migration_rehearsal import (
    SOURCE_MARKER, SOURCE_MARKER_BYTES, TestMigrationSafetyV2z,
)
from scripts.trash.archive_v3a_cutover_readiness_review import (
    OBS_KIND, ReadinessRefused, review,
)

SIGNATURE_SHA = "a" * 64
RELEASE_SHA = "b" * 64


class TestV3aReadinessHolds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="trashpp-v3a-ci-")
        base = Path(cls.temp.name)
        source = base / "trashpp-v2z-fixture-source"
        workspace = base / "trashpp-v2z-backups-separate"
        source.mkdir(mode=0o700)
        workspace.mkdir(mode=0o700)
        marker = source / SOURCE_MARKER
        marker.write_bytes(SOURCE_MARKER_BYTES)
        marker.chmod(0o600)

        archive = ArchiveStore(source)
        archive.save(
            "demo-scrape", "fixture-page-1", "revision-1",
            b"V3a disposable synthetic archive payload 1",
            captured_ms=1760000000000)
        archive.save(
            "weather-events", "fixture-page-2", "revision-2",
            b"V3a disposable synthetic archive payload 2",
            captured_ms=1760000000001)
        cls.plan = TestMigrationSafetyV2z(archive, workspace)
        cls.backup = cls.plan.seal_backup()
        cls.stage = cls.plan.rehearse_schema()
        cls.recovered = cls.plan.rehearse_recovery()
        cls.source_snapshot = archive.verify()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.backup = copy.deepcopy(type(self).backup)
        self.stage = copy.deepcopy(type(self).stage)
        self.recovered = copy.deepcopy(type(self).recovered)
        # Shape follows actual V2w require_current response. A fabricated
        # *observation* is NOT a cryptographically verified authority.
        self.floor = {
            "state": "TEST_EXTERNAL_FLOOR_MATCHED_DENY_ONLY",
            "ownerId": "demo-scrape",
            "epoch": 2,
            "sequence": 7,
            "externalFloorSha256": SIGNATURE_SHA,
            "releaseSha256": RELEASE_SHA,
            "signatureVerified": True,
            "offUidFileObserved": False,
            "externallyProtectedMonotonicAuthorityVerified": False,
            "trustedClockVerified": False,
            "sourceAuthorityVerified": False,
            "captureAllowed": False,
            "productionAllowed": False,
            "restoreAllowed": False,
            "burnAllowed": False,
        }
        self.cutover = {
            "kind": OBS_KIND,
            "ownerId": self.floor["ownerId"],
            "sourceRevisionObserved": self.backup["revision"],
            "sourceSnapshotDigestObserved": self.backup["snapshotDigest"],
            "sourceItemCountObserved": self.backup["items"],
            "activeWritersObserved": 0,
            "postBackupWritesObserved": 0,
            "floorEpochObserved": self.floor["epoch"],
            "floorSequenceObserved": self.floor["sequence"],
            "floorReleaseSha256Observed": self.floor["releaseSha256"],
            "writerFreezeState": "not_requested",
            "signerCustodyState": "unprovisioned",
            "backupCustodyState": "same_uid_fixture",
            "trustedTimeState": "unverified",
            "monotonicWitnessState": "unverified",
            "sourceOwnerApprovalState": "not_obtained",
            "rollbackState": "isolated_copy_only",
            "c3eState": "unverified",
            "c5State": "unverified",
            "productionAllowed": False,
        }

    def evaluate(self):
        return review(self.floor, self.backup, self.stage,
                      self.recovered, self.cutover)

    def assertDenial(self, result):
        self.assertEqual(result["state"], "PRODUCTION_CUTOVER_HOLD")
        self.assertTrue(result["readOnly"])
        self.assertTrue(result["requiresIndependentReview"])
        self.assertTrue(result["syntheticV2zShapeAccepted"])
        self.assertFalse(result["snapshotDataInspectedByV3a"])
        for item in (
            "sourceAuthorityVerified", "trustedClockVerified",
            "independentReleaseFloorVerified", "offHostBackupCustodyVerified",
            "writerFreezeVerified", "productionAllowed", "captureAllowed",
            "restoreAllowed", "burnAllowed", "automaticCutoverAllowed",
            "automaticRollbackAllowed", "deleteOriginalAllowed",
        ):
            self.assertIs(result[item], False, item)
        self.assertEqual(result["safeActions"], [])

    def test_real_v2z_backup_stage_and_recovery_never_activate(self):
        self.assertEqual(self.backup["state"],
                         "TEST_SEALED_BACKUP_VERIFIED_DENY_ONLY")
        self.assertEqual(self.stage["state"],
                         "TEST_STAGE_SCHEMA_MIGRATED_DENY_ONLY")
        self.assertEqual(self.recovered["state"],
                         "TEST_ISOLATED_RECOVERY_VERIFIED_DENY_ONLY")
        self.assertEqual(self.backup["items"], 2)
        result = self.evaluate()
        self.assertDenial(result)
        self.assertIn("source_owner_authorization_missing",
                      result["holdReasons"])
        self.assertIn("off_host_backup_custody_unverified",
                      result["holdReasons"])
        self.assertIn("floor_is_same_uid_test_fixture",
                      result["holdReasons"])
        self.assertIn("c3e_authenticated_source_unverified",
                      result["holdReasons"])
        self.assertIn("c5_one_use_human_consent_unverified",
                      result["holdReasons"])
        self.assertEqual(type(self).source_snapshot,
                         self.plan.source.verify())

    def test_off_uid_floor_is_still_not_monotonic_authority(self):
        self.floor["state"] = "OFF_UID_FLOOR_OBSERVED_DENY_ONLY"
        self.floor["offUidFileObserved"] = True
        result = self.evaluate()
        self.assertDenial(result)
        self.assertIn("off_uid_floor_not_monotonic_proof",
                      result["holdReasons"])
        self.assertNotIn("floor_is_same_uid_test_fixture",
                         result["holdReasons"])

    def test_source_writer_and_revision_drift_block_cutover(self):
        cases = [
            ("activeWritersObserved", 2, "active_archive_writers_observed"),
            ("postBackupWritesObserved", 1, "post_backup_writes_observed"),
            ("sourceRevisionObserved", self.backup["revision"] + 1,
             "backup_source_revision_disagreement"),
            ("sourceSnapshotDigestObserved", "c" * 64,
             "backup_source_digest_disagreement"),
            ("sourceItemCountObserved", self.backup["items"] + 1,
             "backup_source_item_count_disagreement"),
        ]
        for field, value, reason in cases:
            with self.subTest(field=field):
                old = self.cutover[field]
                self.cutover[field] = value
                result = self.evaluate()
                self.assertDenial(result)
                self.assertIn(reason, result["holdReasons"])
                self.cutover[field] = old

    def test_release_replay_or_changed_floor_remains_hold(self):
        cases = [
            ("floorEpochObserved", 1, "release_epoch_disagreement"),
            ("floorSequenceObserved", 6, "release_sequence_disagreement"),
            ("floorReleaseSha256Observed", "d" * 64,
             "release_digest_disagreement"),
            ("writerFreezeState", "expired",
             "writer_lease_expired_or_contested"),
            ("writerFreezeState", "contested",
             "writer_lease_expired_or_contested"),
        ]
        for field, value, reason in cases:
            with self.subTest(field=field):
                prior = self.cutover[field]
                self.cutover[field] = value
                self.assertIn(reason, self.evaluate()["holdReasons"])
                self.cutover[field] = prior

    def test_forged_trusted_source_flags_refuse(self):
        for name in (
            "externallyProtectedMonotonicAuthorityVerified",
            "trustedClockVerified", "sourceAuthorityVerified",
            "captureAllowed", "productionAllowed",
            "restoreAllowed", "burnAllowed",
        ):
            with self.subTest(name=name):
                self.floor[name] = True
                with self.assertRaises(ReadinessRefused):
                    self.evaluate()
                self.floor[name] = False
        for name in ("captureAllowed", "productionAllowed",
                     "restoreAllowed", "burnAllowed"):
            with self.subTest(source="backup", name=name):
                self.backup[name] = True
                with self.assertRaises(ReadinessRefused):
                    self.evaluate()
                self.backup[name] = False

    def test_unsupported_positive_authority_and_cutover_claims_refuse(self):
        fields = {
            "writerFreezeState": "locked",
            "signerCustodyState": "production_key_installed",
            "backupCustodyState": "off_host_signed",
            "trustedTimeState": "verified",
            "monotonicWitnessState": "anchored",
            "sourceOwnerApprovalState": "approved",
            "rollbackState": "verified_lossless",
            "c3eState": "verified",
            "c5State": "approved",
            "productionAllowed": True,
        }
        for name, forged in fields.items():
            with self.subTest(field=name):
                old = self.cutover[name]
                self.cutover[name] = forged
                with self.assertRaises(ReadinessRefused):
                    self.evaluate()
                self.cutover[name] = old

    def test_malformed_unknown_and_boolean_integer_inputs_refuse(self):
        changes = [
            ("cutover", "activeWritersObserved", True),
            ("cutover", "sourceRevisionObserved", -1),
            ("cutover", "floorEpochObserved", True),
            ("cutover", "floorSequenceObserved", 0),
            ("cutover", "sourceSnapshotDigestObserved", "NOT_A_SHA"),
            ("floor", "signatureVerified", 1),
            ("floor", "offUidFileObserved", True),
            ("floor", "epoch", -1),
            ("floor", "sequence", True),
            ("backup", "revision", True),
            ("backup", "backupSha256", "0xdeadbeef"),
            ("backup", "backupBytes", 0),
            ("stage", "stageSchemaVerified", False),
            ("stage", "legacyRecordsPreserved", False),
            ("stage", "backupSha256", "e" * 64),
            ("recovered", "restoredItems", self.backup["items"] + 1),
            ("recovered", "originalArchiveModified", True),
            ("recovered", "backupSha256", "f" * 64),
        ]
        for object_name, field, mutated in changes:
            with self.subTest(object=object_name, field=field):
                target = getattr(self, object_name)
                original = target[field]
                target[field] = mutated
                with self.assertRaises(ReadinessRefused):
                    self.evaluate()
                target[field] = original
        for name in ("floor", "backup", "stage", "recovered", "cutover"):
            with self.subTest(extra_field=name):
                target = getattr(self, name)
                target["grantPermission"] = True
                with self.assertRaises(ReadinessRefused):
                    self.evaluate()
                del target["grantPermission"]

    def test_no_file_actions_or_production_api_in_reviewer(self):
        import scripts.trash.archive_v3a_cutover_readiness_review as module
        text = Path(module.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "sqlite3.connect(", "os.open(", "os.chown(",
            "os.unlink(", ".write_bytes(", "subprocess.",
            "Ed25519PrivateKey", "systemctl", "archive_store.save(",
        ):
            self.assertNotIn(forbidden, text)
        self.assertFalse(hasattr(module, "main"))
        self.assertFalse(hasattr(module, "apply"))
        self.assertFalse(hasattr(module, "migrate"))
        self.assertFalse(hasattr(module, "restore"))


if __name__ == "__main__":
    unittest.main()
