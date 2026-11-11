"""V2p live Linux pidfd lease and commit-time process-exit refusal.

The only payload is an isolated synthetic fixture; no owner signing keys,
ArchiveStore, real source files, Quickshell or production service.
"""
import base64
import hashlib
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from scripts.trash.archive_v2_peer_evidence import (
    _executable_digest, inspect_fixture_peer,
)
from scripts.trash.archive_v2_peer_lifecycle import (
    FixturePeerLease, PeerLeaseError, pin_fixture_peer,
)
from scripts.trash.archive_v2_fixture_socket import (
    WIRE_SCHEMA, encode_fixture_frame, handle_fixture_connection,
)
from scripts.trash.archive_v2_owner_trust import (
    SCHEMA as OWNER_SCHEMA, canonical_authority,
)
from scripts.trash.archive_v2_signed_capture import (
    SCHEMA as CLAIM_SCHEMA, AUDIENCE, PURPOSE, canonical_claim,
)
from scripts.trash.archive_v2_trust_history import TestOwnerTrustHistory

PAYLOAD = b"V2p ephemeral synthetic source; not an actual archive record"
NOW = 1760000500000
SOURCE_TIME = 1760000000000


def pub(key):
    return key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw)


class PeerLifetimeV2pTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.root_key = Ed25519PrivateKey.generate()
        self.owner_key = Ed25519PrivateKey.generate()
        self.pin = {
            "rootKeyId": "fixture-root",
            "publicKeyBytes": pub(self.root_key),
            "origin": "EXTERNALLY_PINNED_TEST_ROOT",
        }
        self.policy = {
            "ownerId": "demo-scrape",
            "expectedUid": os.getuid(),
            "expectedGid": os.getgid(),
            "expectedExeSha256": _executable_digest(os.getpid()),
            "origin": "TEST_FIXTURE_ONLY",
        }
        manifest = {
            "schema": OWNER_SCHEMA, "audience": AUDIENCE, "purpose": PURPOSE,
            "policyOrigin": "TEST_FIXTURE_ONLY", "rootKeyId": "fixture-root",
            "ownerId": "demo-scrape", "keyId": "fixture-signer",
            "publicKeyB64": base64.b64encode(pub(self.owner_key)).decode(),
            "generation": 1, "issuedAtMs": 1760000400000,
            "validFromMs": 1750000000000, "validUntilMs": 1770000000000,
            "revoked": False, "previousManifestSha256": "",
        }
        self.manifest = {
            "manifest": manifest,
            "signatureB64": base64.b64encode(
                self.root_key.sign(canonical_authority(manifest))).decode(),
        }
        claim = {
            "schema": CLAIM_SCHEMA, "audience": AUDIENCE, "purpose": PURPOSE,
            "ownerId": "demo-scrape", "resourceId": "ephemeral-source",
            "sourceRevision": "1" * 64,
            "payloadSha256": hashlib.sha256(PAYLOAD).hexdigest(),
            "sourceCapturedAtMs": SOURCE_TIME,
            "issuedAtMs": 1760000400000, "expiresAtMs": 1760000600000,
            "keyId": "fixture-signer", "nonce": "a" * 32,
        }
        self.proof = {
            "claim": claim, "signatureB64": base64.b64encode(
                self.owner_key.sign(canonical_claim(claim))).decode(),
        }
        self.ledger = TestOwnerTrustHistory(self.root)
        self.ledger.enroll(self.manifest, self.pin, now_ms=NOW)
        self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(self.listener.close)
        self.socket_path = str(self.root / "fixture-lifetime.sock")
        self.listener.bind(self.socket_path)
        self.listener.listen(2)

    def packet(self):
        return {
            "schema": WIRE_SCHEMA, "ownerId": "demo-scrape",
            "resourceId": "ephemeral-source",
            "sourceRevision": "1" * 64,
            "sourceCapturedAtMs": SOURCE_TIME,
            "payloadB64": base64.b64encode(PAYLOAD).decode(),
            "signedManifest": self.manifest,
            "signedClaim": self.proof,
        }

    def counted(self):
        return self.ledger.test_copy_status("demo-scrape")

    def connect_self(self):
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.connect(self.socket_path)
        server, _ = self.listener.accept()
        self.addCleanup(client.close)
        self.addCleanup(server.close)
        return client, server

    def test_live_kernel_lease_and_closed_lease_refuses(self):
        _, server = self.connect_self()
        witness = inspect_fixture_peer(server, self.policy)
        with pin_fixture_peer(server, witness) as lease:
            valid = lease.require_alive()
            self.assertEqual(valid["state"], "TEST_PEER_ALIVE_DENY_ONLY")
            self.assertEqual(valid["peerWitnessSha256"],
                             witness["peerWitnessSha256"])
            self.assertFalse(valid["sourceProcessVerified"])
            self.assertFalse(valid["captureAllowed"])
            fd = lease._fd
            self.assertIsInstance(fd, int)
        with self.assertRaisesRegex(PeerLeaseError, "PEER_LEASE_CLOSED"):
            lease.require_alive()
        with self.assertRaises(OSError):
            os.fstat(fd)

    def test_mutated_process_incarnation_and_exec_digest_refuse(self):
        _, server = self.connect_self()
        witness = inspect_fixture_peer(server, self.policy)
        forged = dict(witness, startTicks=witness["startTicks"] + 1)
        with self.assertRaisesRegex(PeerLeaseError,
                                    "PEER_LEASE_PROCESS_CHANGED"):
            pin_fixture_peer(server, forged)
        with pin_fixture_peer(server, witness) as lease:
            with patch("scripts.trash.archive_v2_peer_lifecycle._executable_digest",
                       return_value="f" * 64):
                with self.assertRaisesRegex(PeerLeaseError,
                                            "PEER_LEASE_PROCESS_CHANGED"):
                    lease.require_alive()

    def test_missing_pidfd_is_fail_closed_not_polling_fallback(self):
        _, server = self.connect_self()
        witness = inspect_fixture_peer(server, self.policy)
        with patch("scripts.trash.archive_v2_peer_lifecycle.os.pidfd_open",
                   side_effect=OSError(38, "function unavailable")):
            with self.assertRaisesRegex(PeerLeaseError,
                                        "PEER_PIDFD_UNAVAILABLE"):
                pin_fixture_peer(server, witness)

    def test_real_child_exit_invalidates_same_kernel_pidfd(self):
        # A real process connects; its open socket remains in server even
        # after child exit. Checking the pidfd must still refuse the lease.
        code = (
            "import socket,sys,time\n"
            "s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)\n"
            "s.connect(sys.argv[1]);time.sleep(60)\n"
        )
        child = subprocess.Popen(
            [sys.executable, "-I", "-B", "-c", code, self.socket_path],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            with self.listener.accept()[0] as server:
                witness = inspect_fixture_peer(server, self.policy)
                self.assertEqual(witness["pid"], child.pid)
                with pin_fixture_peer(server, witness) as lease:
                    self.assertEqual(lease.require_alive()["state"],
                                     "TEST_PEER_ALIVE_DENY_ONLY")
                    child.kill()
                    child.wait(timeout=10)
                    with self.assertRaisesRegex(
                            PeerLeaseError, "PEER_LEASE_PROCESS_EXITED"):
                        lease.require_alive()
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=10)
            child.stderr.close()

    def test_child_exit_before_broker_commit_refuses_nonce_and_copy(self):
        code = (
            "import socket,sys,time\n"
            "s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)\n"
            "s.connect(sys.argv[1]);s.sendall(sys.stdin.buffer.read())\n"
            "sys.stdout.write('sent\\n');sys.stdout.flush()\n"
            "time.sleep(60)\n"
        )
        child = subprocess.Popen(
            [sys.executable, "-I", "-B", "-c", code, self.socket_path],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        try:
            child.stdin.write(encode_fixture_frame(self.packet()))
            child.stdin.close()
            self.assertEqual(child.stdout.readline().strip(), b"sent")
            with self.listener.accept()[0] as server:
                child.kill()
                child.wait(timeout=10)
                result = handle_fixture_connection(
                    server, peer_policy=self.policy,
                    pinned_test_root=self.pin, ledger=self.ledger,
                    now_ms=NOW)
                self.assertFalse(result["ok"])
                self.assertIn(result["error"], (
                    "PEER_LEASE_PROCESS_EXITED",
                    "PEER_PROCESS_UNAVAILABLE",
                    "PEER_EXECUTABLE_UNAVAILABLE",
                    "PEER_PIDFD_UNAVAILABLE",
                    "PEER_LEASE_PROCESS_CHANGED"))
            self.assertEqual(self.counted()["testCopies"], 0)
            self.assertEqual(self.counted()["consumedNonces"], 0)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=10)
            child.stderr.close()
            child.stdout.close()

    def test_commit_boundary_guard_failure_rolls_back_both_records(self):
        # The same-UID test client remains alive, but a simulated pidfd
        # exit at the final guard must roll back both nonce and test copy.
        client, server = self.connect_self()
        client.sendall(encode_fixture_frame(self.packet()))
        original = FixturePeerLease.require_alive
        calls = []

        def force_exit_at_commit(lease):
            calls.append(True)
            if len(calls) == 3:
                raise PeerLeaseError("PEER_LEASE_PROCESS_EXITED")
            return original(lease)

        with patch.object(FixturePeerLease, "require_alive",
                          force_exit_at_commit):
            result = handle_fixture_connection(
                server, peer_policy=self.policy,
                pinned_test_root=self.pin, ledger=self.ledger, now_ms=NOW)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "PEER_LEASE_PROCESS_EXITED")
        self.assertGreaterEqual(len(calls), 3)
        self.assertEqual(self.counted()["testCopies"], 0)
        self.assertEqual(self.counted()["consumedNonces"], 0)
        self.assertEqual(self.ledger.inspect_test_admission(
            "demo-scrape", "fixture-signer", "a" * 32)["state"],
            "TEST_NOT_ADMITTED")

    def test_valid_test_socket_is_still_deny_only(self):
        client, server = self.connect_self()
        client.sendall(encode_fixture_frame(self.packet()))
        result = handle_fixture_connection(
            server, peer_policy=self.policy,
            pinned_test_root=self.pin, ledger=self.ledger,
            now_ms=NOW)
        self.assertTrue(result["ok"])
        self.assertTrue(result["peerLifetimeCheckedBeforeCommit"])
        for key in ("captureAllowed", "productionAllowed",
                    "sourceProcessVerified", "archiveCopyAuthorized",
                    "restoreAllowed", "burnAllowed"):
            self.assertFalse(result[key])
        self.assertEqual(self.counted()["testCopies"], 1)

    def test_ledger_no_live_archive_or_signer_api(self):
        from scripts.trash import archive_v2_peer_lifecycle as module
        source = Path(module.__file__).read_text("utf-8")
        self.assertFalse(hasattr(module, "main"))
        self.assertNotIn("from scripts.trash.archive_store_v2", source)
        self.assertNotIn("ArchiveStore(", source)
        self.assertNotIn("Ed25519PrivateKey", source)
        self.assertNotIn("Quickshell.dataDir", source)
        self.assertFalse((self.root / "trashpp-archive-v2.sqlite3").exists())


if __name__ == "__main__":
    unittest.main()
