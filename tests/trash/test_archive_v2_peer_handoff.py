"""V2n Linux peer evidence + Ed25519 owner claim + test-only atomic binding."""
import base64
import hashlib
import os
from pathlib import Path
import socket
import sqlite3
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from scripts.trash.archive_v2_broker_handoff import (
    BrokerHandoffError, admit_peer_bound_fixture,
)
from scripts.trash.archive_v2_peer_evidence import (
    BrokerPeerError, _executable_digest, inspect_fixture_peer,
)
from scripts.trash.archive_v2_owner_trust import (
    SCHEMA as OWNER_SCHEMA, canonical_authority,
)
from scripts.trash.archive_v2_signed_capture import (
    SCHEMA as CLAIM_SCHEMA, AUDIENCE, PURPOSE, canonical_claim,
    SignedCaptureError,
)
from scripts.trash.archive_v2_trust_history import (
    FILE_NAME, TestOwnerTrustHistory, TrustHistoryError,
)

PAYLOAD = b"V2n synthetic signed copy bytes -- not Weather source data"
SOURCE_MS = 1760000000000
NOW_MS = 1760000500000


def raw_public(key):
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)


class ProtectedPeerHandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.owner_key = Ed25519PrivateKey.generate()
        self.root_key = Ed25519PrivateKey.generate()
        self.pin = {
            "rootKeyId":"test-trust-root",
            "publicKeyBytes":raw_public(self.root_key),
            "origin":"EXTERNALLY_PINNED_TEST_ROOT",
        }
        self.peer_policy = {
            "ownerId":"demo-scrape",
            "expectedUid":os.getuid(),
            "expectedGid":os.getgid(),
            "expectedExeSha256":_executable_digest(os.getpid()),
            "origin":"TEST_FIXTURE_ONLY",
        }
        self.manifest={
            "schema":OWNER_SCHEMA,
            "audience":AUDIENCE,
            "purpose":PURPOSE,
            "policyOrigin":"TEST_FIXTURE_ONLY",
            "rootKeyId":"test-trust-root",
            "ownerId":"demo-scrape",
            "keyId":"fixture-src-01",
            "publicKeyB64":base64.b64encode(
                raw_public(self.owner_key)).decode("ascii"),
            "generation":1,
            "issuedAtMs":1760000400000,
            "validFromMs":1750000000000,
            "validUntilMs":1770000000000,
            "revoked":False,
            "previousManifestSha256":"",
        }
        self.claim={
            "schema":CLAIM_SCHEMA,
            "audience":AUDIENCE,
            "purpose":PURPOSE,
            "ownerId":"demo-scrape",
            "resourceId":"synthetic-resource",
            "sourceRevision":"1"*64,
            "payloadSha256":hashlib.sha256(PAYLOAD).hexdigest(),
            "sourceCapturedAtMs":SOURCE_MS,
            "issuedAtMs":1760000400000,
            "expiresAtMs":1760000600000,
            "keyId":"fixture-src-01",
            "nonce":"a"*32,
        }
        self.ledger=TestOwnerTrustHistory(self.root)
        self.ledger.enroll(self.signed_manifest(),self.pin,now_ms=NOW_MS)
        left,right=socket.socketpair(socket.AF_UNIX,socket.SOCK_STREAM)
        self.addCleanup(left.close)
        self.addCleanup(right.close)
        self.peer=left
        self.other=right

    def signed_manifest(self, manifest=None):
        m=self.manifest if manifest is None else manifest
        return {"manifest":m,
                "signatureB64":base64.b64encode(
                    self.root_key.sign(canonical_authority(m))).decode("ascii")}

    def signed_claim(self, claim=None, signer=None):
        c=self.claim if claim is None else claim
        signing=self.owner_key if signer is None else signer
        return {"claim":c,
                "signatureB64":base64.b64encode(
                    signing.sign(canonical_claim(c))).decode("ascii")}

    def admit(self, *, peer=None, peer_policy=None, proof=None,
              on_stage=None, ledger=None, owner_id="demo-scrape"):
        return admit_peer_bound_fixture(
            self.peer if peer is None else peer,
            self.peer_policy if peer_policy is None else peer_policy,
            self.signed_manifest(),self.pin,
            self.signed_claim() if proof is None else proof,
            ledger=self.ledger if ledger is None else ledger,
            owner_id=owner_id,resource_id="synthetic-resource",
            source_revision="1"*64,
            source_captured_ms=SOURCE_MS,payload=PAYLOAD,
            now_ms=NOW_MS,on_stage=on_stage)

    def inspect(self, ledger=None):
        x=self.ledger if ledger is None else ledger
        return x.inspect_test_admission(
            "demo-scrape","fixture-src-01","a"*32)

    def test_kernel_socket_peer_is_not_from_request_fields(self):
        result=inspect_fixture_peer(self.peer,self.peer_policy)
        self.assertEqual(result["state"],"TEST_KERNEL_PEER_MATCHED_DENY_ONLY")
        self.assertEqual(result["pid"],os.getpid())
        self.assertEqual(result["uid"],os.getuid())
        self.assertEqual(result["gid"],os.getgid())
        self.assertGreater(result["startTicks"],0)
        self.assertEqual(len(result["peerWitnessSha256"]),64)
        self.assertFalse(result["sourceProcessVerified"])
        self.assertFalse(result["captureAllowed"])
        self.assertFalse(result["productionAllowed"])

    def test_request_digest_is_stored_with_same_nonce_copy(self):
        result=self.admit()
        self.assertEqual(result["state"],"TEST_KERNEL_PEER_BOUND_COPY_DENY_ONLY")
        self.assertEqual(result["kernelPeerMatchedFixture"],True)
        self.assertFalse(result["sourceProcessVerified"])
        self.assertFalse(result["captureAllowed"])
        self.assertFalse(result["productionAllowed"])
        recovered=self.inspect()
        self.assertEqual(recovered["snapshotId"],result["snapshotId"])
        self.assertEqual(recovered["peerWitnessSha256"],
                         result["peerWitnessSha256"])
        self.assertEqual(recovered["requestBindingSha256"],
                         result["requestBindingSha256"])
        self.assertTrue(recovered["payloadIntegrityVerified"])
        self.assertEqual(self.ledger.test_copy_status("demo-scrape")["testCopies"],1)
        with sqlite3.connect(self.root/FILE_NAME) as db:
            stored=db.execute(
                "SELECT peer_witness_sha256,request_binding_sha256 FROM test_copies"
            ).fetchone()
        self.assertEqual(stored,(result["peerWitnessSha256"],
                                 result["requestBindingSha256"]))
        self.assertFalse((self.root/"trashpp-archive-v2.sqlite3").exists())

    def test_peer_policy_denies_wrong_uid_gid_executable_and_origin(self):
        for change,expected in (
            ({"expectedUid":os.getuid()+1},"PEER_IDENTITY_MISMATCH"),
            ({"expectedGid":os.getgid()+1},"PEER_IDENTITY_MISMATCH"),
            ({"expectedExeSha256":"f"*64},"PEER_EXECUTABLE_MISMATCH"),
            ({"origin":"LIVE_SIGNED_OWNER"},"PEER_TRUST_NOT_PROVISIONED"),
            ({"ownerId":"weather-events"},"BROKER_OWNER_PEER_MISMATCH"),
        ):
            policy=dict(self.peer_policy,**change)
            error=BrokerHandoffError if change.get("ownerId") else BrokerPeerError
            with self.assertRaisesRegex(error,expected):
                self.admit(peer_policy=policy)
        self.assertEqual(self.ledger.status("demo-scrape")["consumedNonces"],0)

    def test_reject_non_unix_connection_and_self_declared_peer_metadata(self):
        with self.assertRaisesRegex(BrokerPeerError,"PEER_SOCKET_UNSUPPORTED"):
            self.admit(peer=object())
        policy=dict(self.peer_policy,expectedPid=os.getpid())
        with self.assertRaisesRegex(BrokerPeerError,"PEER_TRUST_NOT_PROVISIONED"):
            self.admit(peer_policy=policy)
        self.assertEqual(self.inspect()["state"],"TEST_NOT_ADMITTED")

    def test_mismatched_signatures_and_scope_rejected_before_nonce(self):
        bad_signer=Ed25519PrivateKey.generate()
        with self.assertRaisesRegex(SignedCaptureError,"CAPTURE_SIGNATURE_REFUSED"):
            self.admit(proof=self.signed_claim(signer=bad_signer))
        with self.assertRaisesRegex(BrokerHandoffError,"BROKER_OWNER_PEER_MISMATCH"):
            self.admit(owner_id="weather-events")
        wrong_resource=dict(self.claim,resourceId="another-source")
        with self.assertRaisesRegex(BrokerHandoffError,"BROKER_REQUEST_SCOPE_MISMATCH"):
            self.admit(proof=self.signed_claim(wrong_resource))
        changed=dict(self.claim,payloadSha256="0"*64)
        with self.assertRaisesRegex(SignedCaptureError,"CAPTURE_SOURCE_MISMATCH"):
            self.admit(proof=self.signed_claim(changed))
        self.assertEqual(self.inspect()["state"],"TEST_NOT_ADMITTED")

    def test_failure_before_commit_rolls_back_peer_binding_and_nonce(self):
        for stage in ("after_nonce","after_copy"):
            def fail(label):
                if label==stage:
                    raise RuntimeError("injected interruption")
            with self.assertRaises(RuntimeError):
                self.admit(on_stage=fail)
            restarted=TestOwnerTrustHistory(self.root)
            self.assertEqual(self.inspect(restarted)["state"],"TEST_NOT_ADMITTED")
            self.assertEqual(restarted.test_copy_status("demo-scrape")["testCopies"],0)
        self.admit()
        self.assertEqual(self.ledger.test_copy_status("demo-scrape")["testCopies"],1)

    def test_lost_reply_recovery_preserves_bound_receipt_replay_refused(self):
        def die_after_commit(label):
            if label=="after_commit":
                raise RuntimeError("reply lost")
        with self.assertRaises(RuntimeError):
            self.admit(on_stage=die_after_commit)
        restarted=TestOwnerTrustHistory(self.root)
        recovered=self.inspect(restarted)
        self.assertEqual(recovered["state"],"TEST_COPY_COMMITTED")
        self.assertEqual(len(recovered["requestBindingSha256"]),64)
        self.assertEqual(len(recovered["peerWitnessSha256"]),64)
        with self.assertRaisesRegex(TrustHistoryError,"SOURCE_NONCE_ALREADY_CONSUMED"):
            self.admit(ledger=restarted)

    def test_tampered_peer_witness_format_fails_readonly_recovery(self):
        self.admit()
        with sqlite3.connect(self.root/FILE_NAME) as db:
            # SQLite itself refuses wrong length; a 64-character non-hex
            # rewrite reaches the read-only recovery's stricter validation.
            db.execute("UPDATE test_copies SET peer_witness_sha256=?",
                       ("g"*64,))
        with self.assertRaisesRegex(TrustHistoryError,
                                    "TEST_ADMISSION_INTEGRITY_INVALID"):
            self.inspect()
        self.assertEqual(self.ledger.status("demo-scrape")["consumedNonces"],1)

    def test_legacy_v2m_fixture_rows_do_not_claim_peer_process(self):
        from scripts.trash.archive_v2_atomic_admission import (
            admit_fixture_signed_copy,
        )
        result=admit_fixture_signed_copy(
            self.signed_manifest(),self.pin,self.signed_claim(),
            ledger=self.ledger,owner_id="demo-scrape",
            resource_id="synthetic-resource",source_revision="1"*64,
            source_captured_ms=SOURCE_MS,payload=PAYLOAD,now_ms=NOW_MS)
        self.assertEqual(result["peerWitnessSha256"],"")
        self.assertEqual(self.inspect()["requestBindingSha256"],"")
        self.assertFalse(result["sourceProcessVerified"])

    def test_no_runtime_issuer_service_or_archive_writer(self):
        from scripts.trash import archive_v2_peer_evidence as peer
        from scripts.trash import archive_v2_broker_handoff as broker
        for module in (peer,broker):
            text=Path(module.__file__).read_text(encoding="utf-8")
            self.assertNotIn("ArchiveStore(",text)
            self.assertNotIn("from scripts.trash.archive_store_v2 import",text)
            self.assertNotIn("Quickshell.dataDir",text)
            self.assertNotIn("Ed25519PrivateKey",text)
            self.assertFalse(hasattr(module,"main"))
            self.assertFalse(hasattr(module,"serve"))
        self.assertFalse((self.root/"trashpp-archive-v2.sqlite3").exists())


if __name__=="__main__":
    unittest.main()
