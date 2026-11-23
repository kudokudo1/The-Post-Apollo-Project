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

    def test_fragment_drip_exhausts_total_transaction_deadline(self):
        # A peer returning one byte before each fresh idle timeout must not
        # extend the command indefinitely. No real browser/login is started.
        class DrippingSocket:
            def __init__(self):
                self.reads = 0
                self.timeouts = []

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def settimeout(self, value):
                self.timeouts.append(value)

            def connect(self, _):
                return None

            def sendall(self, _):
                return None

            def recv(self, _):
                self.reads += 1
                return b"x"

        fake = DrippingSocket()
        peer = KernelPeer(os.getpid(), os.geteuid(), os.getegid())
        with patch("desktop_signed_command_client_v0.socket.socket",
                   return_value=fake), \
             patch("desktop_signed_command_client_v0._peer",
                   return_value=peer), \
             patch("desktop_signed_command_client_v0.time.monotonic",
                   side_effect=[0.0, 0.0, 0.0, 0.25, 0.75, 1.25, 1.75, 2.25]):
            with self.assertRaises(ReceiptRejected):
                self.client.begin()
        self.assertEqual(fake.reads, 4)
        self.assertTrue(self.client.faulted)
        self.assertEqual(self.base.factory_calls, 0)
        self.assertEqual(len(fake.timeouts), 6)

    def test_complete_receipt_after_deadline_never_updates_client_state(self):
        # A complete frame received just before expiry is not enough if
        # signature verification itself crosses the total deadline.
        class TimelyBytesLateVerification:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def settimeout(self, _):
                return None

            def connect(self, _):
                return None

            def sendall(self, _):
                return None

            def recv(self, _):
                return b"completed-frame\n"

        peer = KernelPeer(os.getpid(), os.geteuid(), os.getegid())
        apparently_valid = {
            "state": "REQUESTED",
            "requestId": "TEST_HOST_REQUEST_0001",
            "hostInstance": "TEST_HOST_INSTANCE_0001",
            "sequence": 1,
        }
        with patch("desktop_signed_command_client_v0.socket.socket",
                   return_value=TimelyBytesLateVerification()), \
             patch("desktop_signed_command_client_v0._peer",
                   return_value=peer), \
             patch("desktop_signed_command_client_v0.verify_receipt",
                   return_value=apparently_valid), \
             patch("desktop_signed_command_client_v0.time.monotonic",
                   side_effect=[0.0, 0.1, 0.2, 0.3, 2.1]):
            with self.assertRaises(ReceiptRejected):
                self.client.begin()
        self.assertTrue(self.client.faulted)
        self.assertIsNone(self.client._request_id)
        self.assertIsNone(self.client._instance)
        self.assertEqual(self.client._sequence, 0)
        self.assertEqual(self.base.factory_calls, 0)

    def test_local_status_cancel_recover_refusals_all_mark_no_send(self):
        # These three commands are rejected without any host-issued request.
        # Earlier client telemetry must not imply this call got a signed reply.
        for action in (self.client.status, self.client.cancel, self.client.recover):
            with self.subTest(action=action.__name__):
                with self.assertRaises(ReceiptRejected):
                    action()
                self.assertEqual(self.client.last_wire_outcome, "NO_SEND_ATTEMPT")
                self.assertFalse(self.client.faulted)
        self.assertEqual(self.base.factory_calls, 0)
        self.assertEqual(self.base.urls, [])

    def test_duplicate_begin_resets_previous_signed_frame_marker(self):
        original = self.client.begin()
        self.assertEqual(original.phase, "REQUESTED")
        self.assertEqual(self.client.last_wire_outcome, "SIGNED_FRAME_SEEN")
        with self.assertRaises(ReceiptRejected):
            self.client.begin()
        self.assertEqual(self.client.last_wire_outcome, "NO_SEND_ATTEMPT")
        self.assertFalse(self.client.faulted)
        self.assertEqual(self.base.factory_calls, 1)
        self.assertEqual(len(self.base.urls), 1)

    def test_recover_while_pending_marks_no_send_without_host_change(self):
        original = self.client.begin()
        self.assertEqual(self.client.last_wire_outcome, "SIGNED_FRAME_SEEN")
        with self.assertRaises(ReceiptRejected):
            self.client.recover()
        self.assertEqual(self.client.last_wire_outcome, "NO_SEND_ATTEMPT")
        self.assertEqual(self.base.factory_calls, 1)
        self.assertEqual(len(self.base.urls), 1)
        self.assertFalse(self.client.faulted)
        # A later valid STATUS still uses the existing host-issued request.
        self.assertEqual(self.client.status().request_id, original.request_id)
        self.assertEqual(self.client.last_wire_outcome, "SIGNED_FRAME_SEEN")

    def test_cancel_after_cancelled_marks_no_send_not_old_signed_status(self):
        self.client.begin()
        self.assertEqual(self.client.cancel().phase, "CANCELLED")
        self.assertEqual(self.client.last_wire_outcome, "SIGNED_FRAME_SEEN")
        with self.assertRaises(ReceiptRejected):
            self.client.cancel()
        self.assertEqual(self.client.last_wire_outcome, "NO_SEND_ATTEMPT")
        self.assertFalse(self.client.faulted)
        self.assertEqual(self.base.factory_calls, 1)
        self.assertEqual(len(self.base.urls), 1)

    def test_nonce_collision_pre_send_fault_has_no_wire_attempt(self):
        repeated = secrets.token_urlsafe(32)
        self.client._nonces.add(repeated)
        with patch("desktop_signed_command_client_v0.secrets.token_urlsafe",
                   return_value=repeated):
            with self.assertRaises(ReceiptRejected):
                self.client.begin()
        self.assertEqual(self.client.last_wire_outcome, "NO_SEND_ATTEMPT")
        self.assertTrue(self.client.faulted)
        self.assertEqual(self.base.factory_calls, 0)
        self.assertEqual(self.base.urls, [])

    def test_ambiguous_send_stays_unknown_after_faulted_retry_denials(self):
        # A lost signed response after the real fake-browser BEGIN is not
        # overwritten by later local refusals of BEGIN/STATUS/CANCEL/RECOVER.
        with patch("desktop_signed_command_client_v0.verify_receipt",
                   side_effect=ReceiptRejected("signed reply unavailable")):
            with self.assertRaises(ReceiptRejected):
                self.client.begin()
        self.assertEqual(self.client.last_wire_outcome, "UNKNOWN_HOLD")
        self.assertEqual(self.base.factory_calls, 1)
        self.assertEqual(len(self.base.urls), 1)
        for action in (self.client.begin, self.client.status,
                       self.client.cancel, self.client.recover):
            with self.subTest(action=action.__name__):
                with self.assertRaises(ReceiptRejected):
                    action()
                self.assertEqual(self.client.last_wire_outcome, "UNKNOWN_HOLD")
        self.assertTrue(self.client.faulted)
        self.assertEqual(self.base.factory_calls, 1)
        self.assertEqual(len(self.base.urls), 1)

    def test_transport_marker_pre_send_refusal_has_no_dispatch_evidence(self):
        self.assertEqual(self.client.last_wire_outcome, "UNOBSERVED")
        self.accept_server = False
        with self.assertRaises(ReceiptRejected):
            self.client.begin()
        self.assertTrue(self.client.faulted)
        self.assertEqual(self.client.last_wire_outcome, "NO_SEND_ATTEMPT")
        self.assertEqual(self.base.factory_calls, 0)
        # A new client has NO observations about prior processes or commands.
        self.assertEqual(self._client().last_wire_outcome, "UNOBSERVED")

    def test_real_begin_with_lost_receipt_is_unknown_and_not_retried(self):
        # The real disposable native gateway executes BEGIN and launches the
        # fake browser, but the client loses the signed acknowledgement.
        with patch("desktop_signed_command_client_v0.verify_receipt",
                   side_effect=ReceiptRejected("lost signed response")):
            with self.assertRaises(ReceiptRejected):
                self.client.begin()
        self.assertEqual(len(self.base.urls), 1)
        self.assertEqual(self.base.factory_calls, 1)
        self.assertTrue(self.client.faulted)
        self.assertEqual(self.client.last_wire_outcome, "UNKNOWN_HOLD")
        with self.assertRaises(ReceiptRejected):
            self.client.begin()
        with self.assertRaises(ReceiptRejected):
            self.client.status()
        self.assertEqual(self.base.factory_calls, 1)
        self.assertEqual(len(self.base.urls), 1)

    def test_started_send_that_fails_is_unknown_even_without_ack(self):
        # A failed sendall does NOT prove that zero bytes reached the peer.
        class BrokenSend:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def settimeout(self, _):
                pass

            def connect(self, _):
                pass

            def sendall(self, _):
                raise BrokenPipeError("partial write")

        peer = KernelPeer(os.getpid(), os.geteuid(), os.getegid())
        with patch("desktop_signed_command_client_v0.socket.socket",
                   return_value=BrokenSend()), \
             patch("desktop_signed_command_client_v0._peer",
                   return_value=peer):
            with self.assertRaises(ReceiptRejected):
                self.client.begin()
        self.assertEqual(self.client.last_wire_outcome, "UNKNOWN_HOLD")
        self.assertTrue(self.client.faulted)
        self.assertEqual(self.base.factory_calls, 0)

    def test_signed_receipt_is_observation_not_safe_retry_authority(self):
        self.assertEqual(self.client.last_wire_outcome, "UNOBSERVED")
        begin = self.client.begin()
        self.assertEqual(begin.phase, "REQUESTED")
        self.assertEqual(self.client.last_wire_outcome, "SIGNED_FRAME_SEEN")
        self.assertEqual(self.client.status().phase, "PENDING")
        self.assertEqual(self.client.last_wire_outcome, "SIGNED_FRAME_SEEN")
        self.assertFalse(hasattr(self.client, "safe_to_retry"))
        self.assertFalse(hasattr(self.client, "production_authority"))
        self.assertFalse(hasattr(self.client, "can_begin_sign_in"))

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
