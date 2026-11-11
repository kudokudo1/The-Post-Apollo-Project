"""V2l source-owner enrollment, pinned root, generation/revocation and replay.

All Ed25519 private keys are ephemeral Python test fixtures only. No live
Weather/demo signing service, host key files, Quickshell or ArchiveStore writes.
"""
import base64
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from scripts.trash.archive_v2_signed_capture import (
    AUDIENCE, PURPOSE, SCHEMA as CLAIM_SCHEMA, canonical_claim,
)
from scripts.trash.archive_v2_owner_trust import (
    SCHEMA, OwnerTrustError, canonical_authority,
    verify_fixture_authority, verify_enrolled_test_claim,
)
from scripts.trash.archive_v2_trust_history import (
    FILE_NAME, TestOwnerTrustHistory, TrustHistoryError,
)


def raw_pub(key):
    return key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw)


class SourceOwnerV2lTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.root_key = Ed25519PrivateKey.generate()
        self.owner_key = Ed25519PrivateKey.generate()
        self.pinned = {
            "rootKeyId": "fixture-root-01",
            "publicKeyBytes": raw_pub(self.root_key),
            "origin": "EXTERNALLY_PINNED_TEST_ROOT",
        }
        self.now = 1760000500000
        self.manifest = {
            "schema": SCHEMA,
            "audience": AUDIENCE,
            "purpose": PURPOSE,
            "policyOrigin": "TEST_FIXTURE_ONLY",
            "rootKeyId": "fixture-root-01",
            "ownerId": "demo-scrape",
            "keyId": "owner-demo-fixture-01",
            "publicKeyB64": base64.b64encode(
                raw_pub(self.owner_key)).decode("ascii"),
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
            "resourceId": "page-demo",
            "sourceRevision": "1"*64,
            "payloadSha256": "2"*64,
            "sourceCapturedAtMs": 1760000000000,
            "issuedAtMs": 1760000400000,
            "expiresAtMs": 1760000600000,
            "keyId": "owner-demo-fixture-01",
            "nonce": "a"*32,
        }

    def signed(self, manifest=None, root=None):
        manifest = self.manifest if manifest is None else manifest
        root = self.root_key if root is None else root
        return {"manifest": manifest, "signatureB64":
                base64.b64encode(root.sign(
                    canonical_authority(manifest))).decode("ascii")}

    def proof(self, claim=None, owner=None):
        claim = self.claim if claim is None else claim
        owner = self.owner_key if owner is None else owner
        return {"claim": claim, "signatureB64":
                base64.b64encode(owner.sign(canonical_claim(claim))).decode("ascii")}

    def enroll(self, ledger=None, manifest=None, pinned=None, signing_root=None):
        ledger = TestOwnerTrustHistory(self.root) if ledger is None else ledger
        signed = self.signed(manifest, signing_root)
        return ledger.enroll(signed,
                             self.pinned if pinned is None else pinned,
                             now_ms=self.now)

    def use(self, ledger, *, statement=None, claim=None, signer=None,
            pin=None, now=None, revision="1"*64):
        return verify_enrolled_test_claim(
            self.signed() if statement is None else statement,
            self.pinned if pin is None else pin,
            self.proof(claim, signer), ledger=ledger,
            owner_id="demo-scrape", resource_id="page-demo",
            source_revision=revision, payload_sha256="2"*64,
            now_ms=self.now if now is None else now)

    def test_root_signature_and_owner_signature_are_independent(self):
        signed = self.signed()
        checked = verify_fixture_authority(signed,self.pinned,
                                           now_ms=self.now)
        self.assertEqual(checked["state"],
                         "TEST_AUTHORITY_SIGNATURE_MATCHED_DENY_ONLY")
        self.assertEqual(checked["generation"],1)
        self.assertEqual(checked["rootFingerprint"],
                         hashlib.sha256(raw_pub(self.root_key)).hexdigest())
        self.assertEqual(checked["policy"]["publicKeyBytes"],
                         raw_pub(self.owner_key))
        self.assertFalse(checked["sourceAuthorityVerified"])
        self.assertFalse(checked["captureAllowed"])
        self.assertNotIn("privateKey", str(checked))

    def test_durable_enroll_then_consumption_is_still_deny_only(self):
        ledger=TestOwnerTrustHistory(self.root)
        enrolled=self.enroll(ledger)
        self.assertEqual(enrolled["generation"],1)
        self.assertFalse(enrolled["productionAllowed"])
        result=self.use(ledger)
        self.assertEqual(result["state"],
                         "TEST_ENROLLED_CAPTURE_RECORDED_DENY_ONLY")
        self.assertTrue(result["signatureVerified"])
        self.assertTrue(result["authorityManifestSignatureVerified"])
        self.assertTrue(result["replayConsumed"])
        for field in ("sourceAuthorityVerified","humanConsentVerified",
                      "captureAllowed","restoreAllowed","burnAllowed",
                      "productionAllowed"):
            self.assertFalse(result[field])
        reopened=TestOwnerTrustHistory(self.root)
        self.assertEqual(reopened.status("demo-scrape")["consumedNonces"],1)
        self.assertEqual(reopened.status("demo-scrape")["generation"],1)
        with self.assertRaisesRegex(TrustHistoryError,
                                    "SOURCE_NONCE_ALREADY_CONSUMED"):
            self.use(reopened)
        self.assertFalse((self.root/"trashpp-archive-v2.sqlite3").exists())

    def test_claim_cannot_use_self_published_owner_key(self):
        ledger=TestOwnerTrustHistory(self.root)
        self.enroll(ledger)
        wrong=Ed25519PrivateKey.generate()
        from scripts.trash.archive_v2_signed_capture import SignedCaptureError
        with self.assertRaisesRegex(SignedCaptureError,
                                    "CAPTURE_SIGNATURE_REFUSED"):
            self.use(ledger,signer=wrong)
        self.assertEqual(ledger.status("demo-scrape")["consumedNonces"],0)

    def test_root_manifest_tamper_wrong_root_and_untrusted_origin_refused(self):
        statement=self.signed()
        forged=copy.deepcopy(statement)
        forged["manifest"]["keyId"]="malicious-key"
        with self.assertRaisesRegex(OwnerTrustError,
                                    "SOURCE_AUTHORITY_SIGNATURE_REFUSED"):
            verify_fixture_authority(forged,self.pinned,now_ms=self.now)
        other=Ed25519PrivateKey.generate()
        wrong_root=dict(self.pinned,publicKeyBytes=raw_pub(other))
        with self.assertRaisesRegex(OwnerTrustError,
                                    "SOURCE_AUTHORITY_SIGNATURE_REFUSED"):
            verify_fixture_authority(statement,wrong_root,now_ms=self.now)
        wrong_origin=dict(self.pinned,origin="LIVE_TRUST_ROOT")
        with self.assertRaisesRegex(OwnerTrustError,
                                    "SOURCE_TRUST_NOT_PROVISIONED"):
            verify_fixture_authority(statement,wrong_origin,now_ms=self.now)
        own_public=copy.deepcopy(statement)
        own_public["publicKeyBytes"]="self-published"
        with self.assertRaisesRegex(OwnerTrustError,
                                    "SOURCE_AUTHORITY_ENVELOPE_INVALID"):
            verify_fixture_authority(own_public,self.pinned,now_ms=self.now)

    def test_expired_claims_and_malformed_manifests_fail_closed(self):
        for field,value,error in (
            ("ownerId","hospital","SOURCE_AUTHORITY_FIELDS_INVALID"),
            ("purpose","burn","SOURCE_TRUST_NOT_PROVISIONED"),
            ("policyOrigin","PRODUCTION","SOURCE_TRUST_NOT_PROVISIONED"),
            ("generation",True,"SOURCE_AUTHORITY_FIELDS_INVALID"),
            ("previousManifestSha256","f"*64,"SOURCE_AUTHORITY_LINEAGE_INVALID"),
            ("publicKeyB64","A"*44,"SOURCE_AUTHORITY_KEY_INVALID"),
            ("validUntilMs",1750000000000,"SOURCE_AUTHORITY_TIME_INVALID"),
        ):
            payload=dict(self.manifest,**{field:value})
            with self.assertRaisesRegex(OwnerTrustError,error):
                canonical_authority(payload)
        with self.assertRaisesRegex(OwnerTrustError,"SOURCE_AUTHORITY_EXPIRED"):
            verify_fixture_authority(self.signed(),self.pinned,
                                     now_ms=1770000000000)

    def test_floor_and_lineage_prevent_rollback_or_skipped_generation(self):
        ledger=TestOwnerTrustHistory(self.root)
        first=self.enroll(ledger)
        with self.assertRaisesRegex(TrustHistoryError,
                                    "SOURCE_AUTHORITY_GENERATION_REPLAY"):
            self.enroll(ledger)
        second=dict(self.manifest,generation=2,
                    issuedAtMs=1760000400001,
                    previousManifestSha256=first["manifestSha256"])
        accepted=self.enroll(ledger,second)
        self.assertEqual(accepted["generation"],2)
        with self.assertRaisesRegex(TrustHistoryError,
                                    "SOURCE_AUTHORITY_GENERATION_REPLAY"):
            self.enroll(ledger,second)
        skipped=dict(second,generation=4,
                     issuedAtMs=1760000400002,
                     previousManifestSha256="b"*64)
        with self.assertRaisesRegex(TrustHistoryError,
                                    "SOURCE_AUTHORITY_GENERATION_REPLAY"):
            self.enroll(ledger,skipped)
        wrong_link=dict(second,generation=3,
                        issuedAtMs=1760000400002,
                        previousManifestSha256="c"*64)
        with self.assertRaisesRegex(TrustHistoryError,
                                    "SOURCE_AUTHORITY_LINEAGE_REFUSED"):
            self.enroll(ledger,wrong_link)
        self.assertEqual(ledger.status("demo-scrape")["generation"],2)

    def test_root_pin_is_sticky_across_restart(self):
        ledger=TestOwnerTrustHistory(self.root)
        first=self.enroll(ledger)
        other=Ed25519PrivateKey.generate()
        newpin=dict(self.pinned,publicKeyBytes=raw_pub(other))
        changed=dict(self.manifest,generation=2,
                     issuedAtMs=1760000400001,
                     previousManifestSha256=first["manifestSha256"])
        reopened=TestOwnerTrustHistory(self.root)
        with self.assertRaisesRegex(TrustHistoryError,
                                    "SOURCE_AUTHORITY_ROOT_CHANGED"):
            self.enroll(reopened,changed,pinned=newpin,signing_root=other)
        self.assertEqual(reopened.status("demo-scrape")["generation"],1)

    def test_rotation_retires_old_key_and_refuses_stale_policy(self):
        ledger=TestOwnerTrustHistory(self.root)
        first=self.enroll(ledger)
        old_statement=self.signed()
        newkey=Ed25519PrivateKey.generate()
        second=dict(self.manifest,generation=2,
                    issuedAtMs=1760000400001,
                    keyId="owner-demo-fixture-02",
                    publicKeyB64=base64.b64encode(raw_pub(newkey)).decode("ascii"),
                    previousManifestSha256=first["manifestSha256"])
        self.enroll(ledger,second)
        with self.assertRaisesRegex(TrustHistoryError,
                                    "SOURCE_AUTHORITY_STALE_OR_REVOKED"):
            self.use(ledger,statement=old_statement)
        claim2=dict(self.claim,keyId="owner-demo-fixture-02",nonce="b"*32)
        result=self.use(ledger,statement=self.signed(second),
                        claim=claim2,signer=newkey)
        self.assertFalse(result["captureAllowed"])
        third=dict(second,generation=3,issuedAtMs=1760000400002,
                   keyId="owner-demo-fixture-01",
                   publicKeyB64=self.manifest["publicKeyB64"],
                   previousManifestSha256=self.signed(second)
                      and hashlib.sha256(canonical_authority(second)).hexdigest())
        with self.assertRaisesRegex(TrustHistoryError,
                                    "SOURCE_AUTHORITY_REVOKED_KEY_REUSED"):
            self.enroll(ledger,third)

    def test_explicit_revocation_disables_claim_and_cannot_be_undone(self):
        ledger=TestOwnerTrustHistory(self.root)
        first=self.enroll(ledger)
        revoked=dict(self.manifest,generation=2,
                     issuedAtMs=1760000400001,
                     revoked=True,
                     previousManifestSha256=first["manifestSha256"])
        self.enroll(ledger,revoked)
        from scripts.trash.archive_v2_signed_capture import SignedCaptureError
        with self.assertRaisesRegex(SignedCaptureError,
                                    "CAPTURE_SIGNER_REVOKED"):
            self.use(ledger,statement=self.signed(revoked))
        third=dict(revoked,generation=3,issuedAtMs=1760000400002,
                   revoked=False,
                   previousManifestSha256=hashlib.sha256(
                       canonical_authority(revoked)).hexdigest())
        with self.assertRaisesRegex(TrustHistoryError,
                                    "SOURCE_AUTHORITY_REVOKED_KEY_REUSED"):
            self.enroll(ledger,third)

    def test_not_enrolled_cannot_consume_even_with_both_valid_signatures(self):
        ledger=TestOwnerTrustHistory(self.root)
        with self.assertRaisesRegex(TrustHistoryError,
                                    "SOURCE_TRUST_NOT_ENROLLED"):
            self.use(ledger)
        self.assertEqual(ledger.status("demo-scrape")["consumedNonces"],0)

    def test_symlinked_root_file_and_world_access_refused(self):
        link=self.root/"link"
        link.symlink_to(self.root,target_is_directory=True)
        with self.assertRaisesRegex(TrustHistoryError,
                                    "SOURCE_TRUST_ROOT_UNSAFE"):
            TestOwnerTrustHistory(link)
        outside=self.root/"other"
        outside.write_bytes(b"do not touch")
        (self.root/FILE_NAME).symlink_to(outside)
        with self.assertRaisesRegex(TrustHistoryError,
                                    "SOURCE_TRUST_LEDGER_UNSAFE"):
            TestOwnerTrustHistory(self.root)
        self.assertEqual(outside.read_bytes(),b"do not touch")
        (self.root/FILE_NAME).unlink()
        self.root.chmod(0o755)
        with self.assertRaisesRegex(TrustHistoryError,
                                    "SOURCE_TRUST_ROOT_UNSAFE"):
            TestOwnerTrustHistory(self.root)

    def test_no_keygen_or_livestream_access_in_runtime_modules(self):
        from scripts.trash import archive_v2_owner_trust as owner
        from scripts.trash import archive_v2_trust_history as history
        for module in (owner,history):
            source=Path(module.__file__).read_text(encoding="utf-8")
            self.assertNotIn("Ed25519PrivateKey",source)
            self.assertNotIn("BEGIN PRIVATE KEY",source)
            self.assertNotIn("ArchiveStore(",source)
            self.assertNotIn("Quickshell.dataDir",source)
            self.assertFalse(hasattr(module,"main"))
            self.assertFalse(hasattr(module,"restore"))
            self.assertFalse(hasattr(module,"burn"))


if __name__ == "__main__":
    unittest.main()
