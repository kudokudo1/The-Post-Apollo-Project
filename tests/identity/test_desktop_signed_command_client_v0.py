"""Real signed AF_UNIX client ↔ existing Identity Center host integration tests.

All private keys, issuer, browser, human intent and installed-host decisions
are disposable CI fixtures. These tests DO NOT enroll a production service.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import socket
import sys
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "identity"))
sys.path.insert(0, str(ROOT / "tests" / "identity"))

from desktop_command_gateway_v0 import (
    COMMAND_SCHEMA, IdentityCommandGateway, KernelPeer,
)
from desktop_signed_command_client_v0 import (
    SignedIdentityCommandClient,
)
from signed_command_receipt_v0 import (
    ReceiptIssuer, ReceiptRejected, build_request, parse_request,
    verify_receipt,
)
from test_desktop_command_gateway_v0 import GatewayIntegrationTests


class SignedNativeCommandTests(unittest.TestCase):
    def setUp(self):
        # Reuse the original real PKCE/AF_UNIX test host and fake IdP setup.
        # Do not inherit the old test class or replay its legacy-mode tests.
        self.base = GatewayIntegrationTests("test_no_implicit_service_or_browser")
        self.base.setUp()
        self.addCleanup(self.base.doCleanups)
        self.key = Ed25519PrivateKey.generate()
        self.issuer = ReceiptIssuer(self.key)
        self.accept_server = True
        self.accept_seat = True
        self.base.peer_allowed = True
        self.base.consent_allowed = True
        self.base.recover_allowed = True
        self.base.gateway = self._gateway(self.issuer)
        self.addCleanup(self.base.gateway.close)
        self.client = self._client()
        self.base.gateway.start()

    def _gateway(self, issuer):
        return IdentityCommandGateway(
            runtime_directory=self.base.dir,
            host_factory=self.base._factory,
            verified_peer=self.base._verify_peer,
            active_seat=lambda: self.base.seat,
            approved_intent=self.base._approve,
            secure_receipt_issuer=issuer,
        )

    def _client(self, *, key=None, guard=None, seat=None, origin=None):
        return SignedIdentityCommandClient(
            socket_path=self.base.gateway.socket_path,
            pinned_host_public_key=key or self.key.public_key(),
            trusted_server_peer=guard or (
                lambda peer: self.accept_server
                and isinstance(peer, KernelPeer)
                and peer.uid == os.geteuid() and peer.pid == os.getpid()),
            active_seat=seat or (lambda: self.accept_seat),
            enrolled_origin_consistent=origin,
        )

    def test_real_signed_request_to_actual_host_through_callback_recovery(self):
        begin = self.client.begin()
        self.assertEqual(begin.phase, "REQUESTED")
        self.assertEqual(begin.sequence, 1)
        self.assertIsInstance(begin.request_id, str)
        self.assertEqual(len(self.base.urls), 1)
        pending = self.client.status()
        self.assertEqual(pending.phase, "PENDING")
        self.assertGreater(pending.sequence, begin.sequence)
        cancelled = self.client.cancel()
        self.assertEqual(cancelled.phase, "CANCELLED")
        self.assertEqual(self.client.status().phase, "CANCELLED")
        old = self.base.hosts[0]
        recovered = self.client.recover()
        self.assertEqual(recovered.phase, "REQUESTED")
        self.assertNotEqual(recovered.request_id, begin.request_id)
        self.assertEqual(self.base.factory_calls, 2)
        self.assertFalse(old.started)
        self.assertEqual(self.client.status().phase, "PENDING")
        status, body = self.base._callback()
        self.assertEqual(status, 200)
        self.assertNotIn(self.base.secret.encode(), body)
        result = self.client.status()
        self.assertEqual(result.phase, "AUTHENTICATED")
        self.assertEqual(result.request_id, recovered.request_id)
        self.assertEqual(result.instance, begin.instance)
        with self.assertRaises(ReceiptRejected):
            self.client.cancel()
        with self.assertRaises(ReceiptRejected):
            self.client.recover()
        self.assertFalse(self.client.faulted,
                         "Local misuse does not turn into a signed-in claim")
        for record in (begin, pending, cancelled, recovered, result):
            self.assertFalse(hasattr(record, "hostAuthenticated"))
            self.assertFalse(hasattr(record, "access_token"))
            self.assertFalse(hasattr(record, "canConnectProvider"))
        self.assertEqual(len(self.base.hosts), 2)

    def test_host_pinning_or_seat_guard_denies_before_sending_begin(self):
        self.accept_server = False
        with self.assertRaises(ReceiptRejected):
            self.client.begin()
        self.assertTrue(self.client.faulted)
        self.assertEqual(self.base.factory_calls, 0)
        self.accept_server = True
        another = self._client(seat=lambda: False)
        with self.assertRaises(ReceiptRejected):
            another.begin()
        self.assertEqual(self.base.factory_calls, 0)

    def test_signed_client_requires_optional_enrolled_origin_on_every_command(self):
        calls = []
        allowed = [False]
        def independent_process_observation(peer):
            calls.append(peer)
            return allowed[0]
        client = self._client(origin=independent_process_observation)
        with self.assertRaises(ReceiptRejected):
            client.begin()
        self.assertTrue(client.faulted)
        self.assertEqual(self.base.factory_calls, 0)
        self.assertTrue(calls)
        allowed[0] = True
        fresh = self._client(origin=independent_process_observation)
        self.assertEqual(fresh.begin().phase, "REQUESTED")
        allowed[0] = False
        with self.assertRaises(ReceiptRejected):
            fresh.status()
        self.assertTrue(fresh.faulted)
        allowed[0] = True
        with self.assertRaises(ReceiptRejected):
            fresh.status()
        self.assertEqual(self.base.factory_calls, 1)

    def test_signed_client_rejects_wrong_pinned_key_no_fallback(self):
        wrong = self._client(key=Ed25519PrivateKey.generate().public_key())
        with self.assertRaises(ReceiptRejected):
            wrong.begin()
        self.assertTrue(wrong.faulted)
        self.assertEqual(len(self.base.urls), 1)
        # Even a signed 'REQUESTED' from another key is not login authority.
        with self.assertRaises(ReceiptRejected):
            wrong.status()
        self.assertFalse(hasattr(wrong, "hostAuthenticated"))

    def test_malformed_signed_request_never_dispatches_or_uses_legacy(self):
        nonce = secrets.token_urlsafe(32)
        for raw in [
            b'{}\n', b'invalid\n',
            b'{"schema":"x","action":"BEGIN","requestId":null,"clientNonce":"'
            + nonce.encode() + b'"}\n',
            build_request("BEGIN", None, nonce)[:-1],
            build_request("BEGIN", None, nonce).replace(
                b',"clientNonce":', b',"token":"secret","clientNonce":'),
            build_request("BEGIN", None, nonce).replace(
                b'"action":"BEGIN"', b'"action":"CANCEL"'),
            build_request("BEGIN", None, nonce).replace(
                b'"clientNonce":', b'"clientNonce":"dup","clientNonce":'),
            json.dumps({"schema": COMMAND_SCHEMA, "action": "BEGIN",
                        "requestId": None}).encode() + b"\n",
        ]:
            with self.subTest(raw=raw[:70]):
                self.assertIsNone(parse_request(raw))
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
                    conn.settimeout(3)
                    conn.connect(str(self.base.gateway.socket_path))
                    conn.sendall(raw)
                    response = b""
                    while not response.endswith(b"\n"):
                        part = conn.recv(1024)
                        if not part:
                            break
                        response += part
                    # Signed gateway denies legacy; unsigned UNAVAILABLE
                    # can never pass the pinned signature verification.
                    if response:
                        with self.assertRaises(ReceiptRejected):
                            verify_receipt(response,
                                pinned_key=self.key.public_key(),
                                action="BEGIN", command_request_id=None,
                                client_nonce=nonce)
        self.assertEqual(self.base.factory_calls, 0)
        self.assertEqual(self.base.urls, [])

    def test_receipt_signature_action_nonce_and_id_tampering(self):
        nonce = secrets.token_urlsafe(32)
        server = ReceiptIssuer(self.key)
        begin = server.seal("BEGIN", None, nonce,
                            b'{"schema":"post-apollo.identity.command-receipt.experimental-v0",'
                            b'"state":"REQUESTED","requestId":"SIGNED_HOST_REQUEST_0001"}\n')
        body = verify_receipt(begin, pinned_key=self.key.public_key(),
                              action="BEGIN", command_request_id=None,
                              client_nonce=nonce)
        self.assertEqual(body["state"], "REQUESTED")
        self.assertEqual(body["sequence"], 1)
        for kwargs in [
            {"action": "STATUS", "command_request_id": "SIGNED_HOST_REQUEST_0001",
             "client_nonce": nonce},
            {"action": "BEGIN", "command_request_id": None,
             "client_nonce": secrets.token_urlsafe(32)},
        ]:
            with self.assertRaises(ReceiptRejected):
                verify_receipt(begin, pinned_key=self.key.public_key(), **kwargs)
        forged = json.loads(begin)
        for field, new_value in [
            ("state", "AUTHENTICATED"), ("requestId", "OTHER_SIGNED_REQUEST_01"),
            ("sequence", 999), ("hostInstance", secrets.token_urlsafe(32)),
        ]:
            change = json.loads(begin)
            change["body"][field] = new_value
            with self.subTest(field=field), self.assertRaises(ReceiptRejected):
                verify_receipt(json.dumps(change).encode() + b"\n",
                               pinned_key=self.key.public_key(),
                               action="BEGIN", command_request_id=None,
                               client_nonce=nonce)
        forged["unexpected"] = True
        with self.assertRaises(ReceiptRejected):
            verify_receipt(json.dumps(forged).encode() + b"\n",
                           pinned_key=self.key.public_key(),
                           action="BEGIN", command_request_id=None,
                           client_nonce=nonce)

    def test_replaying_old_signed_frame_to_fresh_challenge_faults_client(self):
        begin = self.client.begin()
        self.assertEqual(begin.phase, "REQUESTED")
        self.assertEqual(self.client.status().phase, "PENDING")
        old_frame = self.issuer.seal(
            "STATUS", begin.request_id, secrets.token_urlsafe(32),
            b'{"schema":"post-apollo.identity.command-receipt.experimental-v0",'
            b'"state":"PENDING","requestId":"' + begin.request_id.encode() + b'"}\n')
        original = self.issuer.seal
        self.issuer.seal = lambda action, rid, nonce, raw: old_frame
        with self.assertRaises(ReceiptRejected):
            self.client.status()
        self.assertTrue(self.client.faulted)
        self.assertEqual(self.base.factory_calls, 1)
        self.issuer.seal = original

    def test_post_send_seat_loss_invalidates_client_permanently(self):
        self.assertEqual(self.client.begin().phase, "REQUESTED")
        self.accept_seat = False
        with self.assertRaises(ReceiptRejected):
            self.client.status()
        self.assertTrue(self.client.faulted)
        self.accept_seat = True
        with self.assertRaises(ReceiptRejected):
            self.client.status()

    def test_signer_failure_revokes_host_instead_of_orphan_login(self):
        # Existing gateway bound socket and signed mode. Fail signing after
        # successful side-effect-bearing host BEGIN.
        self.issuer.seal = lambda *_: (_ for _ in ()).throw(
            RuntimeError("Hardware signer not available"))
        with self.assertRaises(ReceiptRejected):
            self.client.begin()
        self.assertTrue(self.client.faulted)
        self.assertEqual(self.base.factory_calls, 1)
        self.assertFalse(self.base.hosts[0].started)
        self.assertFalse((self.base.dir / "identity-display-v0.sock").exists())
        self.assertIsNone(self.base.gateway._request_id)

    def test_wrong_host_instance_or_stale_sequence_rejected(self):
        self.assertEqual(self.client.begin().phase, "REQUESTED")
        self.assertEqual(self.client.status().phase, "PENDING")
        previous = self.issuer
        self.base.gateway._secure_issuer = ReceiptIssuer(self.key)
        with self.assertRaises(ReceiptRejected):
            self.client.status()
        self.assertTrue(self.client.faulted)
        self.base.gateway._secure_issuer = previous


if __name__ == "__main__":
    unittest.main()
