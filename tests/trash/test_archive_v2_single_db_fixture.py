"""V2x isolated, single-SQLite signed receipt/quota/nonce contract tests.

All keys are in-memory ephemeral test keys. All writes are confined to a
new private trashpp-v2x-fixture-* directory under the test runner's temp.
No real ArchiveStore or source data is imported into the writer.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

import test_archive_v2_external_floor_reader as floor_fixture
from test_archive_v2_fixture_service_identity import PAYLOAD
from scripts.trash.archive_v2_signed_capture import (
    PURPOSE, canonical_claim,
)
from scripts.trash.archive_v2_single_db_fixture import (
    DB_NAME, SCHEMA, TestAtomicArchiveCommit, FixtureCommitRefused,
    canonical_receipt_claim,
)

NOW = 1760000500000


def pub(key):
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)


class SignedQuotaCommitV2xTests(unittest.TestCase):
    def setUp(self):
        self.floor_fixture = floor_fixture.ReadOnlyExternalFloorV2wTests("runTest")
        self.floor_fixture.setUp()
        self.addCleanup(self.floor_fixture.doCleanups)
        self.owner = self.floor_fixture.previous.fixture
        self.floor = self.floor_fixture.reader()
        self.root = self.floor_fixture.directory / "trashpp-v2x-fixture-archive"
        self.root.mkdir(mode=0o700)
        self.store = TestAtomicArchiveCommit(self.root)
        self.receipt_private = Ed25519PrivateKey.generate()
        self.receipt_key = {
            "origin":"EXTERNALLY_PINNED_TEST_ROOT",
            "rootKeyId":"fixture-receipt-root",
            "publicKeyBytes":pub(self.receipt_private),
        }
        self.capture_policy = {
            "ownerId":"demo-scrape", "keyId":"test-source",
            "publicKeyBytes":pub(self.owner.source_key),
            "validFromMs":1750000000000,
            "validUntilMs":1770000000000,
            "revoked":False, "purpose":PURPOSE,
            "policyOrigin":"TEST_FIXTURE_ONLY",
        }
        self.floor_hash = self.floor_fixture.verify(self.floor)["externalFloorSha256"]

    def signed_pair(self, *, nonce="a"*32, revision="1"*64,
                    payload=PAYLOAD, snapshot_id="a"*32, parent="",
                    label="Private fixture", signer=None):
        base = dict(self.owner.claim["claim"],
                    nonce=nonce,sourceRevision=revision,
                    payloadSha256=hashlib.sha256(payload).hexdigest())
        signed_source={
            "claim":base,
            "signatureB64":base64.b64encode(
                self.owner.source_key.sign(canonical_claim(base))
            ).decode("ascii"),
        }
        receipt_claim={
            "schema":SCHEMA,"audience":base["audience"],
            "purpose":PURPOSE,"policyOrigin":"TEST_FIXTURE_ONLY",
            "receiptKeyId":"fixture-receipt-root",
            "snapshotId":snapshot_id,
            "ownerId":base["ownerId"],"resourceId":base["resourceId"],
            "sourceRevision":base["sourceRevision"],
            "sourceCapturedAtMs":base["sourceCapturedAtMs"],
            "archivedAtMs":NOW,
            "displayLabel":label,
            "payloadSha256":base["payloadSha256"],
            "captureKeyId":base["keyId"],
            "nonce":base["nonce"],
            "proofSha256":hashlib.sha256(canonical_claim(base)).hexdigest(),
            "externalFloorSha256":self.floor_hash,
            "previousReceiptSha256":parent,
        }
        key = self.receipt_private if signer is None else signer
        signed_receipt={
            "claim":receipt_claim,
            "signatureB64":base64.b64encode(
                key.sign(canonical_receipt_claim(receipt_claim))
            ).decode("ascii"),
        }
        return signed_source,signed_receipt

    def commit(self, *, pair=None, payload=PAYLOAD, store=None,
               on_stage=None, label="Private fixture",
               reader=None):
        if pair is None:
            pair=self.signed_pair(payload=payload,label=label)
        return (self.store if store is None else store).admit(
            pair[0],self.capture_policy,pair[1],self.receipt_key,
            payload,label,
            floor_reader=self.floor if reader is None else reader,
            release_history=self.floor_fixture.previous.history,
            signed_release=self.floor_fixture.previous.signed(),
            release_root=self.owner.trust_root,
            grant_sha256=self.floor_fixture.previous.grant_sha,
            now_ms=NOW, on_stage=on_stage,
        )

    def status(self):
        return self.store.status()

    def recovery(self, nonce="a"*32, store=None):
        return (self.store if store is None else store).inspect(
            "demo-scrape","test-source",nonce,self.receipt_key)

    def test_single_commit_contains_nonce_copy_local_and_signed_receipts(self):
        result=self.commit()
        self.assertEqual(result["state"],"TEST_SINGLE_DB_COMMITTED_DENY_ONLY")
        self.assertEqual(result["snapshotId"],"a"*32)
        self.assertEqual((self.status()["revision"],
                          self.status()["copies"],
                          self.status()["payloadBytes"]),
                         (1,1,len(PAYLOAD)))
        recovered=self.recovery()
        self.assertTrue(recovered["payloadIntegrityVerified"])
        self.assertTrue(recovered["fixtureSignatureVerified"])
        self.assertFalse(recovered["receiptSigningAuthorityVerified"])
        self.assertEqual(recovered["signedReceiptSha256"],
                         result["signedReceiptSha256"])
        self.assertEqual(recovered["localReceiptSha256"],
                         result["localReceiptSha256"])
        for flag in ("captureAllowed","productionAllowed",
                     "restoreAllowed","burnAllowed"):
            self.assertFalse(recovered[flag])
        self.assertTrue((self.root/DB_NAME).exists())
        self.assertFalse((self.root/"trashpp-archive-v2.sqlite3").exists())

    def test_repeated_nonce_cannot_reuse_quota_or_capture(self):
        self.commit()
        with self.assertRaisesRegex(FixtureCommitRefused,
                                    "FIXTURE_NONCE_OR_COPY_REPLAY"):
            self.commit()
        self.assertEqual(self.status()["revision"],1)
        self.assertEqual(self.status()["payloadBytes"],len(PAYLOAD))
        self.assertEqual(self.recovery()["state"],
                         "TEST_RECEIPT_RECOVERED_DENY_ONLY")

    def test_failure_after_nonce_rolls_back_every_row(self):
        def abort(stage):
            if stage == "after_nonce":
                raise RuntimeError("fixture injected failure")
        with self.assertRaisesRegex(RuntimeError,"fixture injected"):
            self.commit(on_stage=abort)
        self.assertEqual(self.status()["copies"],0)
        self.assertEqual(self.status()["payloadBytes"],0)
        self.assertEqual(self.recovery()["state"],"TEST_NOT_ADMITTED")
        self.assertEqual(self.commit()["state"],
                         "TEST_SINGLE_DB_COMMITTED_DENY_ONLY")

    def test_failure_after_copy_rolls_back_every_row(self):
        def abort(stage):
            if stage == "after_copy":
                raise RuntimeError("fixture injected failure")
        with self.assertRaisesRegex(RuntimeError,"fixture injected"):
            self.commit(on_stage=abort)
        self.assertEqual(self.status()["copies"],0)
        self.assertEqual(self.recovery()["state"],"TEST_NOT_ADMITTED")

    def test_failure_after_signed_receipt_rolls_back_every_row(self):
        def abort(stage):
            if stage == "after_receipt":
                raise RuntimeError("fixture injected failure")
        with self.assertRaisesRegex(RuntimeError,"fixture injected"):
            self.commit(on_stage=abort)
        self.assertEqual(self.status()["copies"],0)
        self.assertEqual(self.status()["revision"],0)
        self.assertEqual(self.recovery()["state"],"TEST_NOT_ADMITTED")

    def test_failure_after_quota_accounting_rolls_back_every_row(self):
        def abort(stage):
            if stage == "after_accounting":
                raise RuntimeError("fixture injected failure")
        with self.assertRaisesRegex(RuntimeError,"fixture injected"):
            self.commit(on_stage=abort)
        self.assertEqual(self.status()["payloadBytes"],0)
        self.assertEqual(self.recovery()["state"],"TEST_NOT_ADMITTED")

    def test_lost_reply_after_commit_recovers_with_no_replay(self):
        def lost(stage):
            if stage == "after_commit":
                raise ConnectionError("fixture lost response")
        with self.assertRaisesRegex(ConnectionError,"lost response"):
            self.commit(on_stage=lost)
        reopened=TestAtomicArchiveCommit(self.root)
        self.assertEqual(reopened.status()["revision"],1)
        self.assertTrue(self.recovery(store=reopened)["fixtureSignatureVerified"])
        with self.assertRaisesRegex(FixtureCommitRefused,
                                    "FIXTURE_NONCE_OR_COPY_REPLAY"):
            self.commit(store=reopened)
        self.assertEqual(reopened.status()["copies"],1)

    def test_payload_quota_rejects_before_nonce_then_remains_usable(self):
        limited=TestAtomicArchiveCommit(
            self.root,payload_quota=len(PAYLOAD)-1)
        with self.assertRaisesRegex(FixtureCommitRefused,
                                    "FIXTURE_PAYLOAD_QUOTA"):
            self.commit(store=limited)
        self.assertEqual(limited.status()["copies"],0)
        self.assertEqual(self.recovery()["state"],"TEST_NOT_ADMITTED")
        self.assertTrue(self.commit()["state"].endswith("DENY_ONLY"))

    def test_disk_page_limit_failure_is_atomic(self):
        limited=TestAtomicArchiveCommit(
            self.root,disk_quota=64*1024)
        large=b"fixture, never user data "*5000
        pair=self.signed_pair(payload=large)
        with self.assertRaisesRegex(FixtureCommitRefused,
                                    "FIXTURE_DISK_QUOTA"):
            self.commit(store=limited,pair=pair,payload=large)
        self.assertEqual(self.status()["revision"],0)
        self.assertEqual(self.recovery()["state"],"TEST_NOT_ADMITTED")

    def test_wrong_source_signature_or_payload_does_not_consume_nonce(self):
        source,receipt=self.signed_pair()
        altered_source=dict(source,signatureB64="A"*88)
        with self.assertRaises(Exception):
            self.commit(pair=(altered_source,receipt))
        with self.assertRaises(Exception):
            self.commit(pair=(source,receipt),payload=b"tampered payload")
        self.assertEqual(self.recovery()["state"],"TEST_NOT_ADMITTED")
        self.assertEqual(self.status()["copies"],0)

    def test_different_receipt_signer_and_label_mutation_refused(self):
        source,receipt=self.signed_pair()
        forged=self.signed_pair(signer=Ed25519PrivateKey.generate())[1]
        with self.assertRaisesRegex(FixtureCommitRefused,
                                    "FIXTURE_RECEIPT_SIGNATURE_REFUSED"):
            self.commit(pair=(source,forged))
        with self.assertRaisesRegex(FixtureCommitRefused,
                                    "FIXTURE_RECEIPT_LABEL_OR_TIME_MISMATCH"):
            self.commit(pair=(source,receipt),label="changed label")
        self.assertEqual(self.status()["copies"],0)

    def test_stale_signed_floor_at_precommit_rolls_back_all_rows(self):
        initial=self.floor_fixture.floor_file.read_bytes()
        def replace_floor(stage):
            if stage == "after_accounting":
                self.floor_fixture.write_floor(floor=dict(
                    self.floor_fixture.floor, epoch=2))
        with self.assertRaisesRegex(FixtureCommitRefused,
                                    "FIXTURE_FLOOR_REFUSED"):
            self.commit(on_stage=replace_floor)
        self.assertNotEqual(self.floor_fixture.floor_file.read_bytes(),initial)
        self.assertEqual(self.status()["revision"],0)
        self.assertEqual(self.recovery()["state"],"TEST_NOT_ADMITTED")

    def test_revoked_floor_before_admission_denies_without_writes(self):
        self.floor_fixture.write_floor(floor=dict(
            self.floor_fixture.floor,revoked=True))
        revoked=self.floor_fixture.reader()
        with self.assertRaisesRegex(FixtureCommitRefused,
                                    "FIXTURE_FLOOR_REFUSED"):
            self.commit(reader=revoked)
        self.assertEqual(self.status()["copies"],0)

    def test_receipt_chain_enforces_previous_hash_for_same_resource(self):
        first=self.commit()
        second=self.signed_pair(
            nonce="b"*32,revision="2"*64,snapshot_id="b"*32,
            parent=first["localReceiptSha256"])
        result=self.commit(pair=second)
        self.assertEqual(self.status()["revision"],2)
        self.assertEqual(self.recovery(nonce="b"*32)["localReceiptSha256"],
                         result["localReceiptSha256"])
        bad=self.signed_pair(
            nonce="c"*32,revision="3"*64,snapshot_id="c"*32,
            parent="")
        with self.assertRaisesRegex(FixtureCommitRefused,
                                    "FIXTURE_RECEIPT_PREDECESSOR_MISMATCH"):
            self.commit(pair=bad)
        self.assertEqual(self.status()["revision"],2)
        self.assertEqual(self.recovery(nonce="c"*32)["state"],
                         "TEST_NOT_ADMITTED")

    def test_recovery_detects_tampered_signed_receipt_and_payload(self):
        self.commit()
        with sqlite3.connect(str(self.root/DB_NAME)) as db:
            db.execute("""UPDATE test_receipts
                SET signature_b64=? WHERE snapshot_id=?""",
                ("A"*88,"a"*32))
        with self.assertRaises(FixtureCommitRefused):
            self.recovery()
        self.assertEqual(self.status()["revision"],1)
        with sqlite3.connect(str(self.root/DB_NAME)) as db:
            db.execute("""UPDATE test_snapshots
                SET payload=? WHERE id=?""", (b"tampered","a"*32))
        with self.assertRaisesRegex(FixtureCommitRefused,
                                    "FIXTURE_RECOVERY_INTEGRITY_INVALID"):
            self.recovery()

    def test_missing_receipt_is_corruption_not_uncaptured_nonce(self):
        self.commit()
        with sqlite3.connect(str(self.root/DB_NAME)) as db:
            db.execute("DELETE FROM test_receipts WHERE snapshot_id=?",
                       ("a"*32,))
        with self.assertRaisesRegex(FixtureCommitRefused,
                                    "FIXTURE_RECOVERY_INTEGRITY_INVALID"):
            self.recovery()

    def test_no_real_archive_root_or_cli_and_fixture_root_is_required(self):
        with self.assertRaisesRegex(FixtureCommitRefused,
                                    "FIXTURE_ARCHIVE_CONFIG_INVALID"):
            TestAtomicArchiveCommit(self.floor_fixture.directory)
        (self.root/"trashpp-archive-v2.sqlite3").write_bytes(b"sentinel")
        with self.assertRaisesRegex(FixtureCommitRefused,
                                    "FIXTURE_REAL_ARCHIVE_PRESENT"):
            TestAtomicArchiveCommit(self.root)
        self.assertEqual((self.root/"trashpp-archive-v2.sqlite3").read_bytes(),
                         b"sentinel")

    def test_no_live_capture_signer_or_archive_writer_in_contract(self):
        from scripts.trash import archive_v2_single_db_fixture as module
        text=Path(module.__file__).read_text("utf-8")
        for forbidden in (
            "ArchiveStore(", "Ed25519PrivateKey", "Quickshell.dataDir",
            ".bind(", ".listen(", "gio trash", "systemctl start",
        ):
            self.assertNotIn(forbidden,text)
        self.assertFalse(hasattr(module,"main"))
        self.assertFalse(hasattr(module,"serve_forever"))


if __name__ == "__main__":
    unittest.main()
