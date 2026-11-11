"""V2q test-only source service unit, script and socket pin contracts."""
import base64
import hashlib
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from scripts.trash.archive_v2_fixture_service_identity import (
    PinnedFixtureServiceFiles, ServiceFixtureError,
)
from scripts.trash.archive_v2_service_grant import (
    SCHEMA as GRANT_SCHEMA, ServiceGrantError,
    canonical_service_grant, canonical_service_policy,
    verify_fixture_service_grant,
)
from scripts.trash.archive_v2_fixture_socket import (
    WIRE_SCHEMA, encode_fixture_frame, handle_fixture_connection,
)
from scripts.trash.archive_v2_owner_trust import (
    SCHEMA as OWNER_SCHEMA, canonical_authority,
)
from scripts.trash.archive_v2_peer_evidence import _executable_digest
from scripts.trash.archive_v2_signed_capture import (
    SCHEMA as CLAIM_SCHEMA, AUDIENCE, PURPOSE, canonical_claim,
)
from scripts.trash.archive_v2_trust_history import (
    TestOwnerTrustHistory,
)

PAYLOAD = b"V2q private synthetic page, never original source data"
NOW = 1760000500000
SOURCE_MS = 1760000000000


def public_bytes(key):
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)


class ServiceIdentityV2qTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.unit = self.root / "source.service"
        self.script = self.root / "source.py"
        self.socket_file = self.root / "source.sock"
        self.unit_bytes = b"[Service]\nExecStart=/synthetic-only/source.py\n"
        self.script_bytes = b"print('synthetic fixture only')\n"
        self.unit.write_bytes(self.unit_bytes)
        self.script.write_bytes(self.script_bytes)
        self.unit.chmod(0o600)
        self.script.chmod(0o600)
        self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(self.listener.close)
        self.listener.bind(str(self.socket_file))
        self.listener.listen(2)
        self.socket_file.chmod(0o600)
        self.policy = {
            "origin": "TEST_FIXTURE_ONLY",
            "ownerId": "demo-scrape",
            "expectedUid": os.geteuid(),
            "expectedGid": os.getegid(),
            "unitName": self.unit.name,
            "scriptName": self.script.name,
            "socketName": self.socket_file.name,
            "unitSha256": hashlib.sha256(self.unit_bytes).hexdigest(),
            "scriptSha256": hashlib.sha256(self.script_bytes).hexdigest(),
        }
        self.pinned = PinnedFixtureServiceFiles(self.root, self.policy)
        self.root_key = Ed25519PrivateKey.generate()
        self.source_key = Ed25519PrivateKey.generate()
        self.trust_root = {
            "rootKeyId": "test-root",
            "publicKeyBytes": public_bytes(self.root_key),
            "origin": "EXTERNALLY_PINNED_TEST_ROOT",
        }
        self.peer_policy = {
            "ownerId": "demo-scrape", "expectedUid": os.getuid(),
            "expectedGid": os.getgid(),
            "expectedExeSha256": _executable_digest(os.getpid()),
            "origin": "TEST_FIXTURE_ONLY",
        }
        manifest = {
            "schema": OWNER_SCHEMA, "audience": AUDIENCE,
            "purpose": PURPOSE, "policyOrigin": "TEST_FIXTURE_ONLY",
            "rootKeyId": "test-root", "ownerId": "demo-scrape",
            "keyId": "test-source", "publicKeyB64":
                base64.b64encode(public_bytes(self.source_key)).decode(),
            "generation": 1, "issuedAtMs": 1760000400000,
            "validFromMs": 1750000000000,
            "validUntilMs": 1770000000000,
            "revoked": False, "previousManifestSha256": "",
        }
        self.manifest = {
            "manifest": manifest,
            "signatureB64": base64.b64encode(
                self.root_key.sign(canonical_authority(manifest))).decode(),
        }
        claim = {
            "schema": CLAIM_SCHEMA, "audience": AUDIENCE,
            "purpose": PURPOSE, "ownerId": "demo-scrape",
            "resourceId": "test-page",
            "sourceRevision": "1" * 64,
            "payloadSha256": hashlib.sha256(PAYLOAD).hexdigest(),
            "sourceCapturedAtMs": SOURCE_MS,
            "issuedAtMs": 1760000400000,
            "expiresAtMs": 1760000600000,
            "keyId": "test-source", "nonce": "a" * 32,
        }
        self.claim = {
            "claim": claim, "signatureB64": base64.b64encode(
                self.source_key.sign(canonical_claim(claim))).decode(),
        }
        self.ledger = TestOwnerTrustHistory(self.root)
        self.ledger.enroll(self.manifest, self.trust_root, now_ms=NOW)

    def packet(self):
        return {
            "schema": WIRE_SCHEMA, "ownerId": "demo-scrape",
            "resourceId": "test-page", "sourceRevision": "1" * 64,
            "sourceCapturedAtMs": SOURCE_MS,
            "payloadB64": base64.b64encode(PAYLOAD).decode(),
            "signedManifest": self.manifest,
            "signedClaim": self.claim,
        }

    def service_grant(self, grant=None, *, signer=None):
        if grant is None:
            grant = {
                "schema": GRANT_SCHEMA, "audience": AUDIENCE,
                "purpose": PURPOSE, "policyOrigin": "TEST_FIXTURE_ONLY",
                "rootKeyId": "test-root", "ownerId": "demo-scrape",
                "captureKeyId": "test-source",
                "servicePolicySha256": hashlib.sha256(
                    canonical_service_policy(self.policy)).hexdigest(),
                "sourceManifestSha256": hashlib.sha256(
                    canonical_authority(self.manifest["manifest"])).hexdigest(),
                "generation": 1, "issuedAtMs": 1760000400000,
                "validFromMs": 1760000400000,
                "validUntilMs": 1760000600000, "revoked": False,
            }
        key = self.root_key if signer is None else signer
        return {"grant": grant, "signatureB64": base64.b64encode(
            key.sign(canonical_service_grant(grant))).decode("ascii")}

    def send(self, *, service=None, signed_service_grant=None):
        if service is None:
            service = self.pinned
        elif service is False:
            service = None
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(str(self.socket_file))
            client.sendall(encode_fixture_frame(self.packet()))
            with self.listener.accept()[0] as accepted:
                return handle_fixture_connection(
                    accepted, peer_policy=self.peer_policy,
                    pinned_test_root=self.trust_root,
                    ledger=self.ledger, now_ms=NOW,
                    service_files=service,
                    signed_service_grant=signed_service_grant)

    def counts(self):
        return self.ledger.test_copy_status("demo-scrape")

    def test_fixture_matches_and_remains_non_authorizing(self):
        witness = self.pinned.require_unchanged()
        self.assertEqual(witness["state"],
                         "TEST_SERVICE_FILES_MATCHED_DENY_ONLY")
        self.assertEqual(len(witness["serviceWitnessSha256"]), 64)
        self.assertTrue(witness["fixtureFilesMatched"])
        self.assertFalse(witness["sourceServiceVerified"])
        self.assertFalse(witness["captureAllowed"])
        self.assertFalse(witness["productionAllowed"])

    def test_signed_peer_and_files_bound_to_same_synthetic_receipt(self):
        result = self.send()
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["peerLifetimeCheckedBeforeCommit"])
        self.assertTrue(result["serviceFilesMatchedBeforeCommit"])
        for key in ("sourceProcessVerified", "archiveCopyAuthorized",
                    "captureAllowed", "productionAllowed", "restoreAllowed",
                    "burnAllowed"):
            self.assertFalse(result[key])
        witness = self.pinned.require_unchanged()
        self.assertEqual(result["serviceWitnessSha256"],
                         witness["serviceWitnessSha256"])
        recovered = self.ledger.inspect_test_admission(
            "demo-scrape", "test-source", "a"*32)
        self.assertEqual(recovered["serviceWitnessSha256"],
                         result["serviceWitnessSha256"])
        self.assertEqual(recovered["requestBindingSha256"],
                         result["requestBindingSha256"])
        self.assertTrue(recovered["payloadIntegrityVerified"])
        self.assertEqual((self.counts()["testCopies"],
                          self.counts()["consumedNonces"]), (1, 1))
        self.assertFalse((self.root/"trashpp-archive-v2.sqlite3").exists())

    def test_same_bytes_new_inode_is_not_same_pinned_script(self):
        replacement = self.root / "replacement.py"
        replacement.write_bytes(self.script_bytes)
        replacement.chmod(0o600)
        os.replace(replacement, self.script)
        with self.assertRaisesRegex(ServiceFixtureError,
                                    "SERVICE_FIXTURE_CHANGED"):
            self.pinned.require_unchanged()
        result = self.send()
        self.assertEqual(result["error"], "SERVICE_FIXTURE_CHANGED")
        self.assertEqual(self.counts()["consumedNonces"], 0)

    def test_changed_bytes_or_writable_permissions_fail_before_copy(self):
        self.script.write_bytes(b"print('different fixture')\n")
        with self.assertRaisesRegex(ServiceFixtureError,
                                    "SERVICE_FILE_DIGEST_MISMATCH"):
            self.pinned.require_unchanged()
        self.assertEqual(self.send()["error"], "SERVICE_FILE_DIGEST_MISMATCH")
        self.assertEqual(self.counts()["testCopies"], 0)

    def test_symlink_and_hardlink_substitution_refused(self):
        old = self.root / "original.py"
        self.script.rename(old)
        self.script.symlink_to(old)
        with self.assertRaisesRegex(ServiceFixtureError,
                                    "SERVICE_FILE_UNSAFE"):
            self.pinned.require_unchanged()
        self.script.unlink()
        old.rename(self.script)
        extra = self.root / "extra-hardlink.py"
        os.link(self.script, extra)
        with self.assertRaisesRegex(ServiceFixtureError,
                                    "SERVICE_FILE_UNSAFE"):
            self.pinned.require_unchanged()

    def test_world_writable_file_or_socket_refused(self):
        self.unit.chmod(0o666)
        with self.assertRaisesRegex(ServiceFixtureError,
                                    "SERVICE_FILE_UNSAFE"):
            self.pinned.require_unchanged()
        self.unit.chmod(0o600)
        self.socket_file.chmod(0o666)
        with self.assertRaisesRegex(ServiceFixtureError,
                                    "SERVICE_SOCKET_UNSAFE"):
            self.pinned.require_unchanged()
        self.assertEqual(self.counts()["consumedNonces"], 0)

    def test_socket_replacement_changes_inode_and_refuses(self):
        self.socket_file.unlink()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as replacement:
            replacement.bind(str(self.socket_file))
            replacement.listen(1)
            self.socket_file.chmod(0o600)
            with self.assertRaisesRegex(ServiceFixtureError,
                                        "SERVICE_FIXTURE_CHANGED"):
                self.pinned.require_unchanged()

    def test_untrusted_policy_or_wrong_uid_is_denied(self):
        wrong = dict(self.policy, origin="PRODUCTION")
        with self.assertRaisesRegex(ServiceFixtureError,
                                    "SERVICE_TRUST_NOT_PROVISIONED"):
            PinnedFixtureServiceFiles(self.root, wrong)
        wrong = dict(self.policy, expectedUid=os.geteuid()+1)
        with self.assertRaisesRegex(ServiceFixtureError,
                                    "SERVICE_POLICY_INVALID"):
            PinnedFixtureServiceFiles(self.root, wrong)
        wrong = dict(self.policy, unitName="../secret")
        with self.assertRaisesRegex(ServiceFixtureError,
                                    "SERVICE_POLICY_INVALID"):
            PinnedFixtureServiceFiles(self.root, wrong)

    def test_wrong_socket_connection_refused_even_with_matching_files(self):
        first, second = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            with self.assertRaisesRegex(ServiceFixtureError,
                                        "SERVICE_SOCKET_CONNECTION_MISMATCH"):
                self.pinned.check_connection(first)
        finally:
            first.close()
            second.close()

    def test_commit_time_file_change_rolls_back_nonce_and_copy(self):
        original = PinnedFixtureServiceFiles.check_connection
        calls = []
        def change_at_commit(instance, connection):
            calls.append(True)
            if len(calls) == 2:
                self.script.write_bytes(b"modified while request ran")
            return original(instance, connection)
        with patch.object(PinnedFixtureServiceFiles,
                          "check_connection", change_at_commit):
            result = self.send()
        self.assertEqual(result["error"], "SERVICE_FILE_DIGEST_MISMATCH")
        self.assertGreaterEqual(len(calls), 2)
        self.assertEqual(self.counts()["consumedNonces"], 0)
        self.assertEqual(self.counts()["testCopies"], 0)
        self.assertEqual(self.ledger.inspect_test_admission(
            "demo-scrape","test-source","a"*32)["state"],
            "TEST_NOT_ADMITTED")

    def test_legacy_unbound_fixture_remains_explicitly_unbound(self):
        result = self.send(service=False)
        self.assertTrue(result["ok"])
        self.assertEqual(result["serviceWitnessSha256"], "")
        self.assertFalse(result["serviceFilesMatchedBeforeCommit"])
        recovered = self.ledger.inspect_test_admission(
            "demo-scrape","test-source","a"*32)
        self.assertEqual(recovered["serviceWitnessSha256"], "")

    def test_authority_signed_service_grant_bound_to_atomic_receipt(self):
        signed = self.service_grant()
        evidence = verify_fixture_service_grant(
            signed, self.trust_root, self.pinned, self.manifest, now_ms=NOW)
        self.assertTrue(evidence["serviceGrantSignatureVerified"])
        self.assertFalse(evidence["sourceServiceVerified"])
        self.assertFalse(evidence["captureAllowed"])
        reply = self.send(signed_service_grant=signed)
        self.assertTrue(reply["ok"], reply)
        self.assertTrue(reply["signedServiceGrantChecked"])
        self.assertEqual(reply["serviceGrantSha256"],
                         evidence["serviceGrantSha256"])
        recovered = self.ledger.inspect_test_admission(
            "demo-scrape", "test-source", "a"*32)
        self.assertEqual(recovered["serviceGrantSha256"],
                         evidence["serviceGrantSha256"])
        self.assertEqual(recovered["requestBindingSha256"],
                         reply["requestBindingSha256"])
        self.assertFalse(reply["productionAllowed"])
        self.assertFalse(reply["archiveCopyAuthorized"])

    def test_service_grant_self_signed_wrong_root_refused(self):
        stranger = Ed25519PrivateKey.generate()
        result = self.send(
            signed_service_grant=self.service_grant(signer=stranger))
        self.assertEqual(result["error"], "SERVICE_GRANT_SIGNATURE_REFUSED")
        self.assertEqual(self.counts()["testCopies"], 0)

    def test_service_grant_wrong_policy_and_key_refused(self):
        wrong = dict(self.service_grant()["grant"],
                     servicePolicySha256="c"*64)
        result = self.send(signed_service_grant=self.service_grant(wrong))
        self.assertEqual(result["error"], "SERVICE_GRANT_BINDING_MISMATCH")
        wrong = dict(self.service_grant()["grant"],
                     captureKeyId="another-key")
        result = self.send(signed_service_grant=self.service_grant(wrong))
        self.assertEqual(result["error"], "SERVICE_GRANT_BINDING_MISMATCH")
        self.assertEqual(self.counts()["consumedNonces"], 0)

    def test_revoked_and_expired_grants_refused(self):
        base = self.service_grant()["grant"]
        revoked = dict(base, revoked=True)
        self.assertEqual(
            self.send(signed_service_grant=self.service_grant(revoked))["error"],
            "SERVICE_GRANT_REVOKED")
        expired = dict(base, validUntilMs=NOW-1)
        self.assertEqual(
            self.send(signed_service_grant=self.service_grant(expired))["error"],
            "SERVICE_GRANT_EXPIRED")
        self.assertEqual(self.counts()["testCopies"], 0)

    def test_unknown_scope_type_and_extra_grant_fields_refused(self):
        base = self.service_grant()["grant"]
        for changes, code in [
            ({"purpose":"restore"}, "SERVICE_GRANT_SCOPE_INVALID"),
            ({"ownerId":"hospital"}, "SERVICE_GRANT_FIELDS_INVALID"),
            ({"generation":True}, "SERVICE_GRANT_FIELDS_INVALID"),
            ({"revoked":"false"}, "SERVICE_GRANT_FIELDS_INVALID"),
            ({"foreignKey":"unsupported"}, "SERVICE_GRANT_SCHEMA_INVALID"),
            ({"validUntilMs":1760100000000}, "SERVICE_GRANT_TIME_INVALID"),
        ]:
            with self.assertRaisesRegex(ServiceGrantError, code):
                canonical_service_grant(dict(base, **changes))

    def test_service_grant_without_file_gate_refused(self):
        result = self.send(service=False,
                           signed_service_grant=self.service_grant())
        self.assertEqual(result["error"], "SERVICE_GRANT_FILES_REQUIRED")
        self.assertEqual(self.counts()["consumedNonces"], 0)

    def test_grant_revocation_before_commit_rolls_back_nonce_and_copy(self):
        signed = self.service_grant()
        original = verify_fixture_service_grant
        calls = []
        def revoke_for_final_check(*args, **kwargs):
            calls.append(True)
            if len(calls) == 2:
                changed = dict(args[0], grant=dict(args[0]["grant"],
                                                   revoked=True))
                return original(changed, *args[1:], **kwargs)
            return original(*args, **kwargs)
        with patch("scripts.trash.archive_v2_fixture_socket."
                   "verify_fixture_service_grant",
                   side_effect=revoke_for_final_check):
            result = self.send(signed_service_grant=signed)
        self.assertEqual(result["error"], "SERVICE_GRANT_REVOKED")
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.counts()["testCopies"], 0)
        self.assertEqual(self.counts()["consumedNonces"], 0)

    def test_legacy_service_file_receipt_has_no_signed_grant(self):
        result = self.send()
        self.assertTrue(result["ok"])
        self.assertEqual(result["serviceGrantSha256"], "")
        self.assertFalse(result["signedServiceGrantChecked"])
        recovered = self.ledger.inspect_test_admission(
            "demo-scrape", "test-source", "a"*32)
        self.assertEqual(recovered["serviceGrantSha256"], "")

    def test_no_live_service_or_signer_or_archive_import(self):
        from scripts.trash import archive_v2_fixture_service_identity as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        self.assertNotIn("ArchiveStore(",source)
        self.assertNotIn("Ed25519PrivateKey",source)
        self.assertNotIn("Quickshell.dataDir",source)
        self.assertNotIn(".bind(",source)
        self.assertNotIn(".listen(",source)
        self.assertFalse(hasattr(mod,"main"))


if __name__ == "__main__":
    unittest.main()
