"""V2m signed fixture copy admission: crash atomicity and replay recovery.

All keys are ephemeral in memory. All SQLite stores live under a synthetic
private test directory, never Quickshell or any owner source file.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from scripts.trash.archive_v2_atomic_admission import (
    AtomicAdmissionError, admit_fixture_signed_copy,
)
from scripts.trash.archive_v2_owner_trust import (
    SCHEMA as OWNER_SCHEMA, canonical_authority,
)
from scripts.trash.archive_v2_signed_capture import (
    SCHEMA as CLAIM_SCHEMA, AUDIENCE, PURPOSE,
    SignedCaptureError, canonical_claim,
)
from scripts.trash.archive_v2_trust_history import (
    TestOwnerTrustHistory, TrustHistoryError, FILE_NAME,
)

ROOT = Path(__file__).resolve().parents[2]
PAYLOAD = b"synthetic fixture snapshot, not an original user record"
SOURCE_MS = 1760000000000
NOW = 1760000500000


def pub(key):
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)


class AtomicSignedAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.root_key = Ed25519PrivateKey.generate()
        self.owner_key = Ed25519PrivateKey.generate()
        self.pinned = {
            "rootKeyId": "test-root-v2m",
            "publicKeyBytes": pub(self.root_key),
            "origin": "EXTERNALLY_PINNED_TEST_ROOT",
        }
        self.manifest = {
            "schema": OWNER_SCHEMA,
            "audience": AUDIENCE,
            "purpose": PURPOSE,
            "policyOrigin": "TEST_FIXTURE_ONLY",
            "rootKeyId": "test-root-v2m",
            "ownerId": "demo-scrape",
            "keyId": "test-source-v2m",
            "publicKeyB64": base64.b64encode(pub(self.owner_key)).decode(),
            "generation": 1,
            "issuedAtMs": 1760000400000,
            "validFromMs": 1750000000000,
            "validUntilMs": 1770000000000,
            "revoked": False,
            "previousManifestSha256": "",
        }
        self.claim = {
            "schema": CLAIM_SCHEMA,
            "audience": AUDIENCE,
            "purpose": PURPOSE,
            "ownerId": "demo-scrape",
            "resourceId": "synthetic-page",
            "sourceRevision": "1"*64,
            "payloadSha256": hashlib.sha256(PAYLOAD).hexdigest(),
            "sourceCapturedAtMs": SOURCE_MS,
            "issuedAtMs": 1760000400000,
            "expiresAtMs": 1760000600000,
            "keyId": "test-source-v2m",
            "nonce": "a"*32,
        }
        self.ledger = TestOwnerTrustHistory(self.root)
        self.ledger.enroll(self.manifest_proof(), self.pinned, now_ms=NOW)

    def manifest_proof(self, manifest=None):
        m = self.manifest if manifest is None else manifest
        return {"manifest": m, "signatureB64": base64.b64encode(
            self.root_key.sign(canonical_authority(m))).decode()}

    def source_proof(self, claim=None, signer=None):
        c = self.claim if claim is None else claim
        key = self.owner_key if signer is None else signer
        return {"claim": c, "signatureB64": base64.b64encode(
            key.sign(canonical_claim(c))).decode()}

    def call(self, *, on_stage=None, payload=PAYLOAD,
             claim=None, manifest=None, ledger=None, source_ms=SOURCE_MS):
        return admit_fixture_signed_copy(
            self.manifest_proof(manifest), self.pinned,
            self.source_proof(claim), ledger=self.ledger if ledger is None else ledger,
            owner_id="demo-scrape", resource_id="synthetic-page",
            source_revision="1"*64, source_captured_ms=source_ms,
            payload=payload, now_ms=NOW, on_stage=on_stage)

    def inspect(self, ledger=None, nonce="a"*32):
        use=self.ledger if ledger is None else ledger
        return use.inspect_test_admission("demo-scrape","test-source-v2m",nonce)

    def test_valid_signatures_store_single_test_copy_and_nonce_atomically(self):
        result=self.call()
        self.assertEqual(result["state"], "TEST_ATOMIC_COPY_COMMITTED_DENY_ONLY")
        self.assertEqual(result["payloadSha256"],
                         hashlib.sha256(PAYLOAD).hexdigest())
        self.assertTrue(result["receiptIsTestOnly"])
        for gate in ("captureAllowed","sourceProcessVerified",
                     "trustedTimeVerified","sourceAuthorityVerified",
                     "humanConsentVerified","productionAllowed",
                     "restoreAllowed","burnAllowed"):
            self.assertFalse(result[gate])
        stat=self.ledger.test_copy_status("demo-scrape")
        self.assertEqual((stat["testCopies"],stat["consumedNonces"]),(1,1))
        witnessed=self.inspect()
        self.assertEqual(witnessed["state"],"TEST_COPY_COMMITTED")
        self.assertEqual(witnessed["snapshotId"],result["snapshotId"])
        self.assertEqual(witnessed["proofSha256"],result["proofSha256"])
        self.assertFalse((self.root/"trashpp-archive-v2.sqlite3").exists())
        with sqlite3.connect(self.root/FILE_NAME) as db:
            row=db.execute("SELECT payload FROM test_copies").fetchone()
        self.assertEqual(row[0],PAYLOAD)

    def test_replay_rejected_even_after_ledger_reopens(self):
        self.call()
        reopened=TestOwnerTrustHistory(self.root)
        with self.assertRaisesRegex(TrustHistoryError,
                                    "SOURCE_NONCE_ALREADY_CONSUMED"):
            self.call(ledger=reopened)
        self.assertEqual(reopened.test_copy_status("demo-scrape")["testCopies"],1)

    def test_exception_before_copy_insertion_rolls_back_nonce(self):
        def fail(stage):
            if stage == "after_nonce":
                raise RuntimeError("injected before synthetic copy")
        with self.assertRaises(RuntimeError):
            self.call(on_stage=fail)
        self.assertEqual(self.inspect()["state"],"TEST_NOT_ADMITTED")
        self.assertEqual(self.ledger.test_copy_status("demo-scrape")["consumedNonces"],0)
        self.assertEqual(self.call()["state"],"TEST_ATOMIC_COPY_COMMITTED_DENY_ONLY")

    def test_exception_after_copy_insertion_rolls_back_both(self):
        def fail(stage):
            if stage == "after_copy":
                raise RuntimeError("injected before commit")
        with self.assertRaises(RuntimeError):
            self.call(on_stage=fail)
        self.assertEqual(self.inspect()["state"],"TEST_NOT_ADMITTED")
        self.assertEqual(self.ledger.test_copy_status("demo-scrape")["testCopies"],0)
        self.call()
        self.assertEqual(self.ledger.test_copy_status("demo-scrape")["testCopies"],1)

    def test_failure_after_commit_requires_recovery_not_replay(self):
        def fail(stage):
            if stage == "after_commit":
                raise RuntimeError("reply lost after durable commit")
        with self.assertRaises(RuntimeError):
            self.call(on_stage=fail)
        restarted=TestOwnerTrustHistory(self.root)
        self.assertEqual(self.inspect(restarted)["state"],"TEST_COPY_COMMITTED")
        self.assertEqual(restarted.test_copy_status("demo-scrape")["consumedNonces"],1)
        with self.assertRaisesRegex(TrustHistoryError,
                                    "SOURCE_NONCE_ALREADY_CONSUMED"):
            self.call(ledger=restarted)

    def test_hard_process_exit_recovers_before_and_after_commit(self):
        # This launches a separate Python process and uses os._exit, not an
        # exception. Only public proof bytes, public key and payload are
        # passed to the subprocess. No private key leaves this test process.
        script=r"""
import base64, json, os, sys
sys.path.insert(0,sys.argv[1])
from scripts.trash.archive_v2_atomic_admission import admit_fixture_signed_copy
from scripts.trash.archive_v2_trust_history import TestOwnerTrustHistory
data=json.loads(base64.urlsafe_b64decode(sys.argv[3].encode()).decode())
pinned=dict(data["pinned"],publicKeyBytes=base64.b64decode(data["rootB64"]))
ledger=TestOwnerTrustHistory(sys.argv[2])
admit_fixture_signed_copy(data["manifest"],pinned,data["proof"],
    ledger=ledger,owner_id="demo-scrape",resource_id="synthetic-page",
    source_revision="1"*64,source_captured_ms=1760000000000,
    payload=base64.b64decode(data["payloadB64"]),now_ms=1760000500000,
    on_stage=lambda stage:os._exit(83) if stage==sys.argv[4] else None)
"""
        data={
            "pinned":{"rootKeyId":self.pinned["rootKeyId"],
                      "origin":self.pinned["origin"]},
            "rootB64":base64.b64encode(self.pinned["publicKeyBytes"]).decode(),
            "manifest":self.manifest_proof(),
            "proof":self.source_proof(),
            "payloadB64":base64.b64encode(PAYLOAD).decode(),
        }
        encoded=base64.urlsafe_b64encode(json.dumps(data).encode()).decode()
        for stage in ("after_nonce","after_copy","after_commit"):
            # Restart the ledger each iteration with a fresh test nonce.
            # Earlier crashes must never leave partial admissions behind.
            claim=dict(self.claim,nonce=("%032x" % (len(stage)+1)))
            data["proof"]=self.source_proof(claim)
            encoded=base64.urlsafe_b64encode(json.dumps(data).encode()).decode()
            run=subprocess.run(
                [sys.executable,"-I","-B","-c",script,str(ROOT),
                 str(self.root),encoded,stage],
                capture_output=True,text=True,timeout=15)
            self.assertEqual(run.returncode,83,run.stderr)
            restarted=TestOwnerTrustHistory(self.root)
            expected=("TEST_COPY_COMMITTED" if stage=="after_commit"
                      else "TEST_NOT_ADMITTED")
            actual=restarted.inspect_test_admission(
                "demo-scrape","test-source-v2m",claim["nonce"])
            self.assertEqual(actual["state"],expected)
        self.assertEqual(self.ledger.test_copy_status("demo-scrape"),
                         {"testCopies":1,"consumedNonces":1,"productionAllowed":False})

    def test_modified_payload_and_source_time_rejected_before_any_nonce(self):
        with self.assertRaisesRegex(SignedCaptureError,"CAPTURE_SOURCE_MISMATCH"):
            self.call(payload=b"modified fixture payload")
        with self.assertRaisesRegex(AtomicAdmissionError,
                                    "TEST_ADMISSION_SOURCE_TIME_MISMATCH"):
            self.call(source_ms=SOURCE_MS+1)
        self.assertEqual(self.ledger.test_copy_status("demo-scrape")["testCopies"],0)

    def test_invalid_signature_does_not_consume_or_store(self):
        fake=Ed25519PrivateKey.generate()
        proof=self.source_proof(signer=fake)
        with self.assertRaisesRegex(SignedCaptureError,"CAPTURE_SIGNATURE_REFUSED"):
            admit_fixture_signed_copy(
                self.manifest_proof(),self.pinned,proof,
                ledger=self.ledger,owner_id="demo-scrape",
                resource_id="synthetic-page",source_revision="1"*64,
                source_captured_ms=SOURCE_MS,payload=PAYLOAD,now_ms=NOW)
        self.assertEqual(self.inspect()["state"],"TEST_NOT_ADMITTED")

    def test_revoked_or_stale_authority_cannot_admit_test_copy(self):
        first_sha=hashlib.sha256(canonical_authority(self.manifest)).hexdigest()
        retired=dict(self.manifest,generation=2,issuedAtMs=1760000400001,
                     previousManifestSha256=first_sha,revoked=True)
        self.ledger.enroll(self.manifest_proof(retired),self.pinned,now_ms=NOW)
        from scripts.trash.archive_v2_signed_capture import SignedCaptureError
        with self.assertRaisesRegex(SignedCaptureError,"CAPTURE_SIGNER_REVOKED"):
            self.call(manifest=retired)
        with self.assertRaisesRegex(TrustHistoryError,
                                    "SOURCE_AUTHORITY_STALE_OR_REVOKED"):
            self.call()
        self.assertEqual(self.inspect()["state"],"TEST_NOT_ADMITTED")

    def test_existing_v2l_nonce_not_mistaken_for_saved_test_copy(self):
        # Preserve old fixture V2l tests / rows during additive table change.
        legacy_proof=self.source_proof()
        from scripts.trash.archive_v2_owner_trust import verify_enrolled_test_claim
        verify_enrolled_test_claim(
            self.manifest_proof(),self.pinned,legacy_proof,
            ledger=self.ledger,owner_id="demo-scrape",
            resource_id="synthetic-page",source_revision="1"*64,
            payload_sha256=hashlib.sha256(PAYLOAD).hexdigest(),now_ms=NOW)
        self.assertEqual(self.inspect()["state"],"TEST_NONCE_WITHOUT_COPY")
        self.assertEqual(self.ledger.test_copy_status("demo-scrape")["testCopies"],0)

    def test_recovery_lookup_never_returns_payload_or_archive_privileges(self):
        self.call()
        details=self.inspect()
        self.assertEqual(details["state"],"TEST_COPY_COMMITTED")
        self.assertNotIn("payload",details)
        self.assertNotIn("payloadB64",details)
        self.assertFalse(details["productionAllowed"])
        self.assertEqual(self.ledger.status("demo-scrape")["consumedNonces"],1)

    def test_no_production_cli_source_import_or_quickshell_access(self):
        from scripts.trash import archive_v2_atomic_admission as gateway
        from scripts.trash import archive_v2_trust_history as history
        for module in (gateway,history):
            source=Path(module.__file__).read_text(encoding="utf-8")
            self.assertNotIn("from scripts.trash.archive_store_v2",source)
            self.assertNotIn("ArchiveStore(",source)
            self.assertNotIn("Quickshell.dataDir",source)
            self.assertFalse(hasattr(module,"main"))
            self.assertFalse(hasattr(module,"restore"))
            self.assertFalse(hasattr(module,"burn"))
        self.assertFalse((self.root/"trashpp-archive-v2.sqlite3").exists())


if __name__=="__main__":
    unittest.main()
