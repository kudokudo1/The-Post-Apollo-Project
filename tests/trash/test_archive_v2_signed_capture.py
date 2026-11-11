"""V2k real Ed25519 fixtures, strict capture claim and deny-only replay tests."""
import base64
import copy
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from scripts.trash.archive_v2_signed_capture import (
    AUDIENCE, PURPOSE, SCHEMA, SignedCaptureError, canonical_claim,
    verify_test_proof, verify_test_and_record,
)
from scripts.trash.archive_v2_replay_ledger import (
    NAME, ReplayLedgerError, TestReplayLedger,
)


class SignedCaptureV2kTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.private = Ed25519PrivateKey.generate()  # generated in CI only
        pub = self.private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw)
        self.claim = {
            "schema": SCHEMA,
            "audience": AUDIENCE,
            "purpose": PURPOSE,
            "ownerId": "demo-scrape",
            "resourceId": "page-test",
            "sourceRevision": "1" * 64,
            "payloadSha256": "2" * 64,
            "sourceCapturedAtMs": 1760000000000,
            "issuedAtMs": 1760000400000,
            "expiresAtMs": 1760000600000,
            "keyId": "fixture-key-01",
            "nonce": "a" * 32,
        }
        self.policy = {
            "ownerId": "demo-scrape",
            "keyId": "fixture-key-01",
            "publicKeyBytes": pub,
            "validFromMs": 1750000000000,
            "validUntilMs": 1770000000000,
            "revoked": False,
            "purpose": PURPOSE,
            "policyOrigin": "TEST_FIXTURE_ONLY",
        }
        self.now = 1760000500000

    def proof(self, claim=None, signer=None):
        claim = self.claim if claim is None else claim
        signer = self.private if signer is None else signer
        signature = signer.sign(canonical_claim(claim))
        return {
            "claim": claim,
            "signatureB64": base64.b64encode(signature).decode("ascii"),
        }

    def verify(self, proof=None, policy=None, **overrides):
        args = dict(
            owner_id="demo-scrape",
            resource_id="page-test",
            source_revision="1" * 64,
            payload_sha256="2" * 64,
            now_ms=self.now,
        )
        args.update(overrides)
        return verify_test_proof(self.proof() if proof is None else proof,
                                 self.policy if policy is None else policy,
                                 **args)

    def test_valid_signature_is_never_live_authority(self):
        report = self.verify()
        self.assertEqual(report["state"], "TEST_SIGNATURE_VALID_DENY_ONLY")
        self.assertTrue(report["signatureVerified"])
        self.assertFalse(report["replayConsumed"])
        for field in ("sourceAuthorityVerified", "humanConsentVerified",
                      "captureAllowed", "restoreAllowed", "burnAllowed",
                      "productionAllowed"):
            self.assertFalse(report[field])
        self.assertEqual(report["proofSha256"],
                         hashlib.sha256(canonical_claim(self.claim)).hexdigest())
        self.assertNotIn("signatureB64", report)
        self.assertNotIn("publicKeyBytes", report)
        self.assertFalse((self.root / NAME).exists())

    def test_signature_tamper_wrong_key_and_noncanonical_base64_rejected(self):
        proof = self.proof()
        changed = copy.deepcopy(proof)
        changed["claim"]["payloadSha256"] = "3" * 64
        with self.assertRaisesRegex(SignedCaptureError,
                                    "CAPTURE_SIGNATURE_REFUSED"):
            self.verify(changed, payload_sha256="3" * 64)
        different = Ed25519PrivateKey.generate()
        with self.assertRaisesRegex(SignedCaptureError,
                                    "CAPTURE_SIGNATURE_REFUSED"):
            self.verify(self.proof(signer=different))
        broken = self.proof()
        broken["signatureB64"] = "!" * 88
        with self.assertRaisesRegex(SignedCaptureError,
                                    "CAPTURE_SIGNATURE_INVALID"):
            self.verify(broken)
        broken = self.proof()
        broken["signatureB64"] += "A"
        with self.assertRaisesRegex(SignedCaptureError,
                                    "CAPTURE_SIGNATURE_INVALID"):
            self.verify(broken)

    def test_source_identity_revision_and_payload_bound(self):
        for mismatch in (
            {"owner_id": "weather-events"},
            {"resource_id": "other-record"},
            {"source_revision": "3" * 64},
            {"payload_sha256": "f" * 64},
        ):
            with self.assertRaisesRegex(SignedCaptureError,
                                        "CAPTURE_SOURCE_MISMATCH"):
                self.verify(**mismatch)

    def test_schema_scope_unknown_fields_and_weak_nonce_fail(self):
        for field, value, code in (
            ("audience", "post-apollo.hospital", "CAPTURE_CLAIM_SCOPE_INVALID"),
            ("purpose", "restore", "CAPTURE_CLAIM_SCOPE_INVALID"),
            ("ownerId", "hospital", "CAPTURE_CLAIM_FIELDS_INVALID"),
            ("sourceRevision", "x"*64, "CAPTURE_CLAIM_FIELDS_INVALID"),
            ("nonce", "short", "CAPTURE_CLAIM_FIELDS_INVALID"),
            ("resourceId", "file:///etc/passwd", "CAPTURE_CLAIM_FIELDS_INVALID"),
            ("issuedAtMs", True, "CAPTURE_CLAIM_TIME_INVALID"),
        ):
            claim = dict(self.claim)
            claim[field] = value
            with self.assertRaisesRegex(SignedCaptureError, code):
                canonical_claim(claim)
        extra = dict(self.claim, publicKeyBytes="self-published")
        with self.assertRaisesRegex(SignedCaptureError,
                                    "CAPTURE_CLAIM_SCHEMA_INVALID"):
            canonical_claim(extra)

    def test_expired_future_and_overlong_time_window_rejected(self):
        with self.assertRaisesRegex(SignedCaptureError,
                                    "CAPTURE_PROOF_EXPIRED"):
            self.verify(now_ms=self.claim["expiresAtMs"])
        with self.assertRaisesRegex(SignedCaptureError,
                                    "CAPTURE_PROOF_EXPIRED"):
            self.verify(now_ms=self.claim["issuedAtMs"] - 30001)
        claim = dict(self.claim, expiresAtMs=self.claim["issuedAtMs"] + 300001)
        with self.assertRaisesRegex(SignedCaptureError,
                                    "CAPTURE_CLAIM_TIME_INVALID"):
            self.proof(claim)
        claim = dict(self.claim, sourceCapturedAtMs=self.claim["issuedAtMs"]+1)
        with self.assertRaisesRegex(SignedCaptureError,
                                    "CAPTURE_CLAIM_TIME_INVALID"):
            self.proof(claim)

    def test_policy_can_only_be_fixture_and_revocation_is_absolute(self):
        for change, code in (
            ({"policyOrigin": "LIVE_SOURCE"}, "SOURCE_TRUST_NOT_PROVISIONED"),
            ({"revoked": True}, "CAPTURE_SIGNER_REVOKED"),
            ({"ownerId": "weather-events"}, "CAPTURE_SIGNER_SCOPE_REFUSED"),
            ({"keyId": "forged-key"}, "CAPTURE_SIGNER_SCOPE_REFUSED"),
            ({"purpose": "burn"}, "CAPTURE_SIGNER_SCOPE_REFUSED"),
            ({"validUntilMs": self.claim["expiresAtMs"]-1},
                "CAPTURE_SIGNER_KEY_EXPIRED"),
        ):
            policy = dict(self.policy, **change)
            with self.assertRaisesRegex(SignedCaptureError, code):
                self.verify(policy=policy)
        with self.assertRaisesRegex(SignedCaptureError,
                                    "SOURCE_TRUST_NOT_PROVISIONED"):
            self.verify(policy={})

    def test_crypto_missing_is_fail_closed(self):
        with patch("scripts.trash.archive_v2_signed_capture.Ed25519PublicKey", None):
            with self.assertRaisesRegex(SignedCaptureError,
                                        "CAPTURE_CRYPTO_UNAVAILABLE"):
                self.verify()

    def test_durable_nonce_consumption_then_replay_rejection(self):
        ledger = TestReplayLedger(self.root)
        proof = self.proof()
        kwargs = dict(ledger=ledger, owner_id="demo-scrape",
                      resource_id="page-test", source_revision="1"*64,
                      payload_sha256="2"*64, now_ms=self.now)
        result = verify_test_and_record(proof, self.policy, **kwargs)
        self.assertTrue(result["replayConsumed"])
        self.assertFalse(result["captureAllowed"])
        self.assertEqual(ledger.count(),1)
        reopened = TestReplayLedger(self.root)
        with self.assertRaisesRegex(ReplayLedgerError,
                                    "CAPTURE_NONCE_ALREADY_CONSUMED"):
            verify_test_and_record(proof, self.policy, **dict(kwargs,ledger=reopened))
        self.assertEqual(reopened.count(),1)

    def test_rejected_signature_never_consumes_nonce(self):
        ledger = TestReplayLedger(self.root)
        invalid = self.proof(signer=Ed25519PrivateKey.generate())
        with self.assertRaisesRegex(SignedCaptureError,
                                    "CAPTURE_SIGNATURE_REFUSED"):
            verify_test_and_record(
                invalid, self.policy, ledger=ledger, owner_id="demo-scrape",
                resource_id="page-test", source_revision="1"*64,
                payload_sha256="2"*64, now_ms=self.now)
        self.assertEqual(ledger.count(),0)
        valid = verify_test_and_record(
            self.proof(), self.policy, ledger=ledger, owner_id="demo-scrape",
            resource_id="page-test", source_revision="1"*64,
            payload_sha256="2"*64, now_ms=self.now)
        self.assertEqual(valid["state"], "TEST_RECORDED_DENY_ONLY")

    def test_private_test_root_and_file_symlinks_refused(self):
        bad = self.root / "link"
        bad.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ReplayLedgerError,
                                    "CAPTURE_LEDGER_ROOT_UNSAFE"):
            TestReplayLedger(bad)
        outside = self.root / "outside"
        outside.write_bytes(b"protected")
        (self.root / NAME).symlink_to(outside)
        with self.assertRaisesRegex(ReplayLedgerError,
                                    "CAPTURE_LEDGER_UNSAFE"):
            TestReplayLedger(self.root)
        self.assertEqual(outside.read_bytes(),b"protected")
        (self.root / NAME).unlink()
        self.root.chmod(0o755)
        with self.assertRaisesRegex(ReplayLedgerError,
                                    "CAPTURE_LEDGER_ROOT_UNSAFE"):
            TestReplayLedger(self.root)

    def test_replay_ledger_rejects_duplicate_nonce_across_relaunch(self):
        ledger=TestReplayLedger(self.root)
        ledger.consume("demo-scrape","fixture-key-01","a"*32,"b"*64)
        with self.assertRaisesRegex(ReplayLedgerError,
                                    "CAPTURE_NONCE_ALREADY_CONSUMED"):
            TestReplayLedger(self.root).consume(
                "demo-scrape","fixture-key-01","a"*32,"c"*64)
        self.assertEqual(ledger.count(),1)

    def test_no_live_cli_writer_signer_or_hardcoded_private_key(self):
        from scripts.trash import archive_v2_signed_capture as verifier
        for action in ("main","capture","sign","restore","burn","delete",
                       "write_archive","create_private_key"):
            self.assertFalse(hasattr(verifier,action))
        source = Path(verifier.__file__).read_text(encoding="utf-8")
        self.assertNotIn("Ed25519PrivateKey",source)
        self.assertNotIn("BEGIN PRIVATE KEY",source)
        self.assertNotIn("from scripts.trash.archive_store_v2 import",source)
        self.assertNotIn("ArchiveStore(",source)


if __name__ == "__main__":
    unittest.main()
