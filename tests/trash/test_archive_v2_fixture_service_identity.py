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

    def send(self, *, service=None):
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
                    service_files=service)

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
