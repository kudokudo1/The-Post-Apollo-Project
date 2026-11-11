"""V2s signed fixture release floors and durable revocation, no live keys.

Uses V2q's synthetic Unix socket and in-memory Ed25519 keys. The test-only
release DB is separate from the synthetic copy DB and ArchiveStore.
"""
import base64
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

import test_archive_v2_fixture_service_identity as base_fixture
from scripts.trash.archive_v2_service_grant import canonical_service_grant
from scripts.trash.archive_v2_service_release_history import (
    SCHEMA, FILE_NAME, ServiceReleaseError, TestServiceReleaseHistory,
    canonical_release, verify_fixture_release,
)
from scripts.trash.archive_v2_signed_capture import AUDIENCE, PURPOSE

NOW = 1760000500000


class SignedServiceReleaseV2sTests(unittest.TestCase):
    def setUp(self):
        self.fixture = base_fixture.ServiceIdentityV2qTests(methodName="runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.history = TestServiceReleaseHistory(self.fixture.root)
        self.grant = self.fixture.service_grant()
        self.grant_sha = hashlib.sha256(
            canonical_service_grant(self.grant["grant"])).hexdigest()
        self.release = {
            "schema": SCHEMA,
            "audience": AUDIENCE,
            "purpose": PURPOSE,
            "policyOrigin": "TEST_FIXTURE_ONLY",
            "rootKeyId": "test-root",
            "ownerId": "demo-scrape",
            "sequence": 1,
            "grantSha256": self.grant_sha,
            "previousReleaseSha256": "",
            "issuedAtMs": 1760000400000,
            "validFromMs": 1760000400000,
            "validUntilMs": 1760000600000,
            "revoked": False,
        }

    def signed(self, record=None, *, key=None):
        record = self.release if record is None else record
        key = self.fixture.root_key if key is None else key
        return {"release": record, "signatureB64": base64.b64encode(
            key.sign(canonical_release(record))).decode("ascii")}

    def next_release(self, previous, *, grant_sha=None, revoked=False):
        return dict(self.release,
                    sequence=previous["sequence"] + 1,
                    previousReleaseSha256=hashlib.sha256(
                        canonical_release(previous)).hexdigest(),
                    issuedAtMs=previous["issuedAtMs"] + 1,
                    grantSha256=self.grant_sha if grant_sha is None else grant_sha,
                    revoked=revoked)

    def enroll(self, signed=None, *, history=None, pin=None):
        return (self.history if history is None else history).enroll(
            self.signed() if signed is None else signed,
            self.fixture.trust_root if pin is None else pin,
            now_ms=NOW)

    def send(self, signed=None, *, grant=None, history=None):
        return self.fixture.send(
            signed_service_grant=self.grant if grant is None else grant,
            signed_service_release=self.signed() if signed is None else signed,
            service_release_history=self.history if history is None else history)

    def status(self):
        return self.fixture.ledger.test_copy_status("demo-scrape")

    def test_enrolled_signed_release_recorded_with_atomic_fixture_copy(self):
        enrolled = self.enroll()
        self.assertEqual(enrolled["sequence"], 1)
        self.assertFalse(enrolled["productionAllowed"])
        reply = self.send()
        self.assertTrue(reply["ok"], reply)
        self.assertTrue(reply["releaseFloorChecked"])
        self.assertTrue(reply["signedServiceGrantChecked"])
        self.assertFalse(reply["archiveCopyAuthorized"])
        self.assertFalse(reply["captureAllowed"])
        self.assertFalse(reply["productionAllowed"])
        digest = hashlib.sha256(canonical_release(self.release)).hexdigest()
        self.assertEqual(reply["serviceReleaseSha256"], digest)
        copy = self.fixture.ledger.inspect_test_admission(
            "demo-scrape", "test-source", "a"*32)
        self.assertEqual(copy["serviceReleaseSha256"], digest)
        self.assertTrue(copy["payloadIntegrityVerified"])
        self.assertEqual(self.status()["testCopies"], 1)
        self.assertTrue((self.fixture.root / FILE_NAME).exists())
        self.assertFalse((self.fixture.root / "trashpp-archive-v2.sqlite3").exists())

    def test_reopen_preserves_signed_highwater_and_refuses_sequence_replay(self):
        self.enroll()
        reopened = TestServiceReleaseHistory(self.fixture.root)
        self.assertEqual(reopened.status("demo-scrape")["sequence"], 1)
        matched = reopened.require_current(
            self.signed(), self.fixture.trust_root, owner_id="demo-scrape",
            grant_sha256=self.grant_sha, now_ms=NOW)
        self.assertEqual(matched["state"], "TEST_RELEASE_CURRENT_DENY_ONLY")
        with self.assertRaisesRegex(ServiceReleaseError,
                                    "RELEASE_SEQUENCE_ROLLBACK"):
            self.enroll(history=reopened)
        self.assertEqual(reopened.status("demo-scrape")["sequence"], 1)

    def test_not_enrolled_signature_never_authorizes_test_copy(self):
        result = self.send()
        self.assertEqual(result["error"], "RELEASE_NOT_ENROLLED")
        self.assertEqual(self.status()["consumedNonces"], 0)

    def test_missing_history_grant_or_release_refuses_broker(self):
        signed = self.signed()
        missing_history = self.fixture.send(
            signed_service_grant=self.grant,
            signed_service_release=signed)
        self.assertEqual(missing_history["error"], "RELEASE_FLOOR_REQUIRED")
        missing_grant = self.fixture.send(
            signed_service_release=signed,
            service_release_history=self.history)
        self.assertEqual(missing_grant["error"], "RELEASE_FLOOR_REQUIRED")
        history_alone = self.fixture.send(
            signed_service_grant=self.grant,
            service_release_history=self.history)
        self.assertEqual(history_alone["error"], "RELEASE_FLOOR_REQUIRED")
        self.assertEqual(self.status()["testCopies"], 0)

    def test_skip_predecessor_and_old_release_refused(self):
        first = self.enroll()
        skipped = dict(self.release, sequence=3,
                       previousReleaseSha256="a"*64,
                       issuedAtMs=1760000400002)
        with self.assertRaisesRegex(ServiceReleaseError,
                                    "RELEASE_SEQUENCE_ROLLBACK"):
            self.enroll(self.signed(skipped))
        wrong_link = dict(self.release, sequence=2,
                          previousReleaseSha256="b"*64,
                          issuedAtMs=1760000400001)
        with self.assertRaisesRegex(ServiceReleaseError,
                                    "RELEASE_PREDECESSOR_MISMATCH"):
            self.enroll(self.signed(wrong_link))
        second = self.next_release(self.release)
        self.enroll(self.signed(second))
        old_result = self.send()
        self.assertEqual(old_result["error"], "RELEASE_STALE_OR_CHANGED")
        self.assertEqual(self.status()["consumedNonces"], 0)
        self.assertEqual(first["sequence"], 1)
        self.assertEqual(self.history.status("demo-scrape")["sequence"], 2)

    def test_revocation_is_sticky_after_process_reopen(self):
        self.enroll()
        revoke = self.next_release(self.release, revoked=True)
        self.enroll(self.signed(revoke))
        reopened = TestServiceReleaseHistory(self.fixture.root)
        result = self.send(signed=self.signed(revoke), history=reopened)
        self.assertEqual(result["error"], "RELEASE_REVOKED")
        self.assertEqual(self.send(history=reopened)["error"],
                         "RELEASE_STALE_OR_CHANGED")
        restored = self.next_release(revoke, revoked=False)
        with self.assertRaisesRegex(ServiceReleaseError,
                                    "RELEASE_GRANT_RETIRED"):
            reopened.enroll(self.signed(restored), self.fixture.trust_root,
                            now_ms=NOW)
        self.assertEqual(reopened.status("demo-scrape")["sequence"], 2)
        self.assertEqual(self.status()["testCopies"], 0)

    def test_rotated_grant_retires_old_digest_and_accepts_new_fixture(self):
        self.enroll()
        new_grant_fields = dict(self.grant["grant"], issuedAtMs=1760000400001)
        new_grant = self.fixture.service_grant(new_grant_fields)
        new_sha = hashlib.sha256(
            canonical_service_grant(new_grant_fields)).hexdigest()
        release2 = self.next_release(self.release, grant_sha=new_sha)
        self.enroll(self.signed(release2))
        reply_old = self.send()
        self.assertEqual(reply_old["error"], "RELEASE_STALE_OR_CHANGED")
        reply_new = self.send(signed=self.signed(release2),grant=new_grant)
        self.assertTrue(reply_new["ok"], reply_new)
        self.assertFalse(reply_new["productionAllowed"])
        release3 = self.next_release(release2, grant_sha=self.grant_sha)
        with self.assertRaisesRegex(ServiceReleaseError,
                                    "RELEASE_GRANT_RETIRED"):
            self.enroll(self.signed(release3))

    def test_independently_pinned_root_refuses_self_signed_release(self):
        forged = Ed25519PrivateKey.generate()
        with self.assertRaisesRegex(ServiceReleaseError,
                                    "RELEASE_SIGNATURE_REFUSED"):
            self.enroll(self.signed(key=forged))
        self.assertEqual(self.history.status("demo-scrape")["sequence"], 0)

    def test_root_substitution_not_accepted_after_valid_first_release(self):
        self.enroll()
        stranger = Ed25519PrivateKey.generate()
        new_pin = dict(self.fixture.trust_root, publicKeyBytes=
                       stranger.public_key().public_bytes(
                           serialization.Encoding.Raw,
                           serialization.PublicFormat.Raw))
        second = self.next_release(self.release)
        with self.assertRaisesRegex(ServiceReleaseError,
                                    "RELEASE_ROOT_CHANGED"):
            self.enroll(self.signed(second,key=stranger), pin=new_pin)
        self.assertEqual(self.history.status("demo-scrape")["sequence"], 1)

    def test_grant_mismatch_and_expired_release_refuse_without_nonce(self):
        self.enroll()
        wrong = dict(self.release, grantSha256="f"*64)
        result = self.send(signed=self.signed(wrong))
        self.assertEqual(result["error"], "RELEASE_GRANT_BINDING_MISMATCH")
        expired = dict(self.release, validUntilMs=NOW-1)
        result = self.send(signed=self.signed(expired))
        self.assertEqual(result["error"], "RELEASE_EXPIRED")
        self.assertEqual(self.status()["consumedNonces"], 0)

    def test_scope_fields_types_lineage_and_oversized_time_denied(self):
        for change,code in (
            ({"ownerId":"hospital"}, "RELEASE_FIELDS_INVALID"),
            ({"purpose":"burn"}, "RELEASE_SCOPE_INVALID"),
            ({"policyOrigin":"LIVE"}, "RELEASE_SCOPE_INVALID"),
            ({"sequence":True}, "RELEASE_FIELDS_INVALID"),
            ({"revoked":"false"}, "RELEASE_FIELDS_INVALID"),
            ({"previousReleaseSha256":"a"*64}, "RELEASE_LINEAGE_INVALID"),
            ({"validUntilMs":1760200000000}, "RELEASE_TIME_INVALID"),
            ({"unknownKey":"smuggle"}, "RELEASE_SCHEMA_INVALID"),
        ):
            with self.assertRaisesRegex(ServiceReleaseError, code):
                canonical_release(dict(self.release,**change))

    def test_release_revoked_after_preflight_rolls_back_both_fixture_rows(self):
        self.enroll()
        original = self.history.require_current
        calls=[]
        revoke = self.next_release(self.release, revoked=True)
        def invalidate_at_final(*args, **kwargs):
            calls.append(True)
            if len(calls) == 2:
                self.history.enroll(self.signed(revoke),
                                    self.fixture.trust_root, now_ms=NOW)
            return original(*args, **kwargs)
        with patch.object(self.history,"require_current",
                          side_effect=invalidate_at_final):
            reply = self.send()
        self.assertEqual(reply["error"], "RELEASE_STALE_OR_CHANGED")
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.status()["testCopies"], 0)
        self.assertEqual(self.status()["consumedNonces"], 0)
        self.assertEqual(self.history.status("demo-scrape")["sequence"], 2)

    def test_synthetic_archive_without_release_has_no_release_attestation(self):
        plain = self.fixture.send(signed_service_grant=self.grant)
        self.assertTrue(plain["ok"],plain)
        self.assertEqual(plain["serviceReleaseSha256"], "")
        self.assertFalse(plain["releaseFloorChecked"])
        copy = self.fixture.ledger.inspect_test_admission(
            "demo-scrape", "test-source", "a"*32)
        self.assertEqual(copy["serviceReleaseSha256"], "")

    def test_symlinked_root_or_history_file_denied(self):
        link = self.fixture.root / "linked-root"
        link.symlink_to(self.fixture.root, target_is_directory=True)
        with self.assertRaisesRegex(ServiceReleaseError,
                                    "RELEASE_ROOT_UNSAFE"):
            TestServiceReleaseHistory(link)
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            other = root / "outside"
            other.write_bytes(b"sentinel")
            (root / FILE_NAME).symlink_to(other)
            with self.assertRaisesRegex(ServiceReleaseError,
                                        "RELEASE_HISTORY_UNSAFE"):
                TestServiceReleaseHistory(root)
            self.assertEqual(other.read_bytes(), b"sentinel")

    def test_no_live_service_key_import_or_archive_writer(self):
        from scripts.trash import archive_v2_service_release_history as mod
        source = Path(mod.__file__).read_text("utf-8")
        self.assertNotIn("Ed25519PrivateKey", source)
        self.assertNotIn("ArchiveStore(", source)
        self.assertNotIn("Quickshell.dataDir", source)
        self.assertFalse(hasattr(mod,"main"))
        self.assertFalse(hasattr(mod,"serve_forever"))


if __name__=="__main__":
    unittest.main()
