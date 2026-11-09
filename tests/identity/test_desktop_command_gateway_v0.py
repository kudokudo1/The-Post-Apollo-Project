"""Disposable Linux end-to-end BEGIN gateway → existing Identity host tests.

The gateway binds a REAL AF_UNIX command socket and calls the REAL existing
host lifecycle; the browser callback, token verification and IdP are injected
CI fakes. No production service, workstation accounts or secrets are used.
"""
from __future__ import annotations

import http.client
import json
import os
from pathlib import Path
import socket
import stat
import sys
import tempfile
import unittest
from urllib.parse import parse_qs, urlencode, urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "identity"))

from desktop_command_gateway_v0 import (
    COMMAND_SOCKET, COMMAND_SCHEMA, RECEIPT_SCHEMA,
    IdentityCommandGateway, KernelPeer,
)
from desktop_context_projection_v0 import HostContextReply
from desktop_host_lifecycle_v0 import DesktopHostLifecycle, HostLifecycleConfig
from desktop_session_host_v0 import VerifiedCodeExchange
from private_context_ipc_v0 import read_private_display


ISSUER = "https://issuer.example.test/realms/demo"
NOW = 1_800_000_000


class GatewayIntegrationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="id-command-ci-")
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        os.chmod(self.dir, 0o700)
        self.urls = []
        self.hosts = []
        self.factory_calls = 0
        self.verifier_calls = []
        self.consent_calls = []
        self.seat = True
        self.time = NOW
        self.peer_allowed = False
        self.consent_allowed = False
        self.secret = "CI-PRIVATE-FAKE-TOKEN"
        self.gateway = self._gateway()
        self.addCleanup(self.gateway.close)

    def _factory(self):
        self.factory_calls += 1
        host = DesktopHostLifecycle(
            config=HostLifecycleConfig(
                issuer=ISSUER,
                authorization_endpoint=ISSUER + "/protocol/openid-connect/auth",
                client_id="ci-native",
                api_audience="ci-api",
                runtime_directory=self.dir,
            ),
            browser_open=lambda url: self.urls.append(url),
            exchange_and_verify=self._exchange,
            api_get=self._get,
            clock=lambda: self.time,
            session_is_active=lambda: self.seat,
        )
        self.hosts.append(host)
        return host

    def _exchange(self, code, verifier, nonce, redirect):
        if code != "ci-one-use-code" or not verifier:
            raise ValueError("Invalid fake authorization code")
        return VerifiedCodeExchange(
            access_token=self.secret, issuer=ISSUER, client_id="ci-native",
            nonce=nonce, subject="hidden-ci-person", expires_at=NOW + 180,
            token_type="Bearer", signed_id_token_verified=True,
        )

    def _get(self, bearer):
        self.assertEqual(bearer, self.secret)
        response = {
            "schema": "post-apollo.identity.context-summary.v0",
            "status": "OK",
            "organizations": [{
                "organizationId": "ci_llc",
                "kind": "llc",
                "scopeGrants": [{
                    "action": "records.read", "divisionId": None,
                    "unitId": None, "expiresAt": NOW + 120,
                }],
            }],
            "portfolios": [{
                "portfolioId": "ci_portfolio",
                "organizationIds": ["ci_llc"],
            }],
        }
        return HostContextReply(
            200, "application/json", json.dumps(response).encode("utf-8"),
        )

    def _verify_peer(self, peer):
        self.verifier_calls.append(peer)
        return self.peer_allowed and (
            isinstance(peer, KernelPeer)
            and peer.uid == os.geteuid()
            and peer.pid == os.getpid()
        )

    def _approve(self, peer, action):
        self.consent_calls.append((peer, action))
        return self.consent_allowed and action in ("BEGIN", "STATUS", "CANCEL")

    def _gateway(self):
        return IdentityCommandGateway(
            runtime_directory=self.dir,
            host_factory=self._factory,
            verified_peer=self._verify_peer,
            active_seat=lambda: self.seat,
            approved_intent=self._approve,
        )

    def _request(self, data):
        if isinstance(data, dict):
            data = json.dumps(data, separators=(",", ":")).encode() + b"\n"
        conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        conn.settimeout(3.0)
        conn.connect(str(self.gateway.socket_path))
        try:
            conn.sendall(data)
            received = b""
            while not received.endswith(b"\n"):
                block = conn.recv(1024)
                if not block:
                    break
                received += block
        finally:
            conn.close()
        return json.loads(received)

    def _begin(self):
        return self._request({
            "schema": COMMAND_SCHEMA,
            "action": "BEGIN",
            "requestId": None,
        })

    def _status(self, request_id):
        return self._request({
            "schema": COMMAND_SCHEMA,
            "action": "STATUS",
            "requestId": request_id,
        })

    def _cancel(self, request_id):
        return self._request({
            "schema": COMMAND_SCHEMA,
            "action": "CANCEL",
            "requestId": request_id,
        })

    def _check_rejected(self, result):
        self.assertEqual(result, {
            "schema": RECEIPT_SCHEMA,
            "state": "UNAVAILABLE",
            "requestId": None,
        })
        for forbidden in [
            self.secret, "issuer.example.test", "authorization_url",
            "code_challenge", "hidden-ci-person", "client_secret",
        ]:
            self.assertNotIn(forbidden, json.dumps(result))

    def _callback(self):
        auth = urlsplit(self.urls[-1])
        state = parse_qs(auth.query)["state"][0]
        redirect = urlsplit(self.hosts[-1].redirect_uri)
        conn = http.client.HTTPConnection("127.0.0.1", redirect.port, timeout=2)
        conn.request(
            "GET", redirect.path + "?" + urlencode({
                "code": "ci-one-use-code",
                "state": state,
                "iss": ISSUER,
            }),
            headers={"Host": f"127.0.0.1:{redirect.port}"},
        )
        reply = conn.getresponse()
        result = (reply.status, reply.read())
        conn.close()
        return result

    def test_no_implicit_service_or_browser(self):
        self.assertFalse(self.gateway.socket_path.exists())
        self.assertFalse(self.urls)
        self.assertEqual(self.factory_calls, 0)

    def test_real_socket_gate_requires_kernel_peer_and_separate_consent(self):
        self.gateway.start()
        info = self.gateway.socket_path.lstat()
        self.assertTrue(stat.S_ISSOCK(info.st_mode))
        self.assertEqual(stat.S_IMODE(info.st_mode), 0o600)
        self._check_rejected(self._begin())
        self.assertEqual(self.factory_calls, 0)
        self.peer_allowed = True
        self._check_rejected(self._begin())
        self.assertEqual(self.factory_calls, 0)
        self.consent_allowed = True
        self.seat = False
        self._check_rejected(self._begin())
        self.assertEqual(self.factory_calls, 0)
        self.seat = True
        receipt = self._begin()
        self.assertEqual(receipt["schema"], RECEIPT_SCHEMA)
        self.assertEqual(receipt["state"], "REQUESTED")
        self.assertIsInstance(receipt["requestId"], str)
        self.assertGreaterEqual(len(receipt["requestId"]), 16)
        self.assertEqual(self.factory_calls, 1)
        self.assertEqual(len(self.urls), 1)
        self.assertTrue(self.verifier_calls)
        self.assertTrue(self.consent_calls)
        self.assertEqual(self.consent_calls[-1][1], "BEGIN")
        self._check_rejected(self._begin())
        self.assertEqual(self.factory_calls, 1, "No double browser login")

    def test_actual_host_callback_and_private_display_are_not_in_receipt(self):
        self.peer_allowed = self.consent_allowed = True
        self.gateway.start()
        receipt = self._begin()
        self.assertEqual(receipt["state"], "REQUESTED")
        self.assertNotIn(self.secret, json.dumps(receipt))
        self.assertNotIn("issuer", json.dumps(receipt))
        auth_url = urlsplit(self.urls[0])
        self.assertEqual(auth_url.scheme, "https")
        self.assertEqual(parse_qs(auth_url.query)["code_challenge_method"], ["S256"])
        status, response = self._callback()
        self.assertEqual(status, 200)
        self.assertNotIn(self.secret.encode(), response)
        display = read_private_display(self.hosts[0].display_socket_path,
                                       clock=lambda: NOW)
        self.assertEqual(display["status"], "READY")
        self.assertEqual(display["organizations"][0]["organizationId"], "ci_llc")
        self.assertNotIn(self.secret, json.dumps(display))
        # CANCEL is not logout. An already authenticated host must not be
        # revoked by a merely shaped or source-unauthenticated CANCEL packet.
        self._check_rejected(self._request({
            "schema": COMMAND_SCHEMA, "action": "CANCEL",
            "requestId": receipt["requestId"],
        }))
        self.assertEqual(
            read_private_display(self.hosts[0].display_socket_path,
                                 clock=lambda: NOW)["status"], "READY",
        )
        self.gateway.close()
        self.assertFalse(self.gateway.socket_path.exists())
        self.assertFalse(self.dir.joinpath("identity-display-v0.sock").exists())

    def test_every_unsupported_or_spoofed_command_refused_before_host(self):
        self.peer_allowed = self.consent_allowed = True
        self.gateway.start()
        candidate = {
            "schema": COMMAND_SCHEMA, "action": "BEGIN", "requestId": None,
        }
        malformed = [
            b"garbage\n", b"\xff\n", b"\n", b"{}\n", b"[]\n",
            b'{"schema":"x","schema":"x","action":"BEGIN","requestId":null}\n',
            json.dumps(candidate).encode(),
            b"x" * 1025 + b"\n",
            {**candidate, "token": "forged"},
            {**candidate, "hostAuthenticated": True},
            {**candidate, "operatorConsentVerified": True},
            {**candidate, "issuer": ISSUER},
            {**candidate, "requestId": "client-invented"},
            {**candidate, "action": "RECOVER"},
            {**candidate, "action": "CANCEL"},
            {**candidate, "action": "STATUS"},
            {**candidate, "action": "CONNECT_ALL"},
        ]
        for item in malformed:
            with self.subTest(item=str(item)[:35]):
                self._check_rejected(self._request(item))
        self.assertEqual(self.factory_calls, 0)
        self.assertEqual(self.urls, [])

    def test_failed_callback_policy_never_boots_host(self):
        self.gateway = self._gateway()
        self.peer_allowed = True
        self.consent_allowed = True
        self.gateway._verify_peer = lambda peer: (_ for _ in ()).throw(
            RuntimeError("untrusted runtime"))
        self.gateway.start()
        self._check_rejected(self._begin())
        self.assertEqual(self.factory_calls, 0)

    def test_lost_seat_during_begin_revokes_host_and_denies_receipt(self):
        self.peer_allowed = self.consent_allowed = True
        def lost_seat(_url):
            self.urls.append("HOST-ONLY")
            self.seat = False
        self.gateway._factory = lambda: DesktopHostLifecycle(
            config=HostLifecycleConfig(
                issuer=ISSUER, authorization_endpoint=ISSUER + "/protocol/openid-connect/auth",
                client_id="ci-native", api_audience="ci-api", runtime_directory=self.dir,
            ),
            browser_open=lost_seat, exchange_and_verify=self._exchange,
            api_get=self._get, clock=lambda: NOW,
            session_is_active=lambda: True,
        )
        self.gateway.start()
        self._check_rejected(self._begin())
        self.assertFalse((self.dir / "identity-display-v0.sock").exists())

    def test_untrusted_path_refusal_and_safe_inode_cleanup(self):
        self.dir.chmod(0o755)
        with self.assertRaises(ValueError):
            self.gateway.start()
        self.assertFalse(self.gateway.socket_path.exists())
        self.dir.chmod(0o700)
        self.assertFalse(self.gateway.socket_path.exists())
        # Fresh object: fail closed on pre-existing command path.
        other = self._gateway()
        self.gateway.socket_path.write_text("DO NOT OVERWRITE", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            other.start()
        self.assertEqual(self.gateway.socket_path.read_text(), "DO NOT OVERWRITE")

    def test_gateway_close_does_not_reanimate_old_host(self):
        self.peer_allowed = self.consent_allowed = True
        self.gateway.start()
        receipt = self._begin()
        self.assertEqual(receipt["state"], "REQUESTED")
        self.gateway.close()
        self.gateway.close()
        self.assertFalse(self.gateway.socket_path.exists())
        self.assertEqual(self.hosts[0].begin_login(), {"status": "UNAVAILABLE"})
        self.assertFalse((self.dir / "identity-display-v0.sock").exists())
        with self.assertRaises(RuntimeError):
            self.gateway.start()

    def test_pending_status_cancel_late_callback_and_terminal_replay(self):
        self.peer_allowed = self.consent_allowed = True
        self.gateway.start()
        self._check_rejected(self._status("HOST_REQUEST_ID_123456"))
        receipt = self._begin()
        rid = receipt["requestId"]
        self.assertEqual(self._status(rid), {
            "schema": RECEIPT_SCHEMA, "state": "PENDING", "requestId": rid,
        })
        self.assertEqual(self.hosts[0].command_phase(), "PENDING")
        self.assertEqual(self._cancel(rid), {
            "schema": RECEIPT_SCHEMA, "state": "CANCELLED", "requestId": rid,
        })
        self.assertEqual(self._status(rid)["state"], "CANCELLED")
        self._check_rejected(self._cancel(rid))
        self._check_rejected(self._begin())
        status, body = self._callback()
        self.assertEqual(status, 400, "Late OAuth callback after CANCEL must fail")
        self.assertNotIn(self.secret.encode(), body)
        self.assertEqual(self._status(rid)["state"], "CANCELLED")
        display = read_private_display(
            self.hosts[0].display_socket_path, clock=lambda: NOW)
        self.assertNotEqual(display["status"], "READY")
        self.assertEqual(display["organizations"], [])
        self.assertEqual(self.hosts[0].begin_login(), {"status": "UNAVAILABLE"})
        self.assertIn("CANCEL", [action for _, action in self.consent_calls])
        self.assertIn("STATUS", [action for _, action in self.consent_calls])

    def test_verified_callback_is_not_cancelled_by_late_request(self):
        self.peer_allowed = self.consent_allowed = True
        self.gateway.start()
        rid = self._begin()["requestId"]
        self.assertEqual(self._status(rid)["state"], "PENDING")
        status, body = self._callback()
        self.assertEqual(status, 200)
        self.assertNotIn(self.secret.encode(), body)
        self.assertEqual(self._status(rid), {
            "schema": RECEIPT_SCHEMA,
            "state": "AUTHENTICATED", "requestId": rid,
        })
        self.assertEqual(self.hosts[0].command_phase(), "AUTHENTICATED")
        self._check_rejected(self._cancel(rid))
        self.assertEqual(self._status(rid)["state"], "AUTHENTICATED")
        self.assertEqual(read_private_display(
            self.hosts[0].display_socket_path,
            clock=lambda: NOW)["status"], "READY")
        self._check_rejected(self._request({
            "schema": COMMAND_SCHEMA, "action": "RECOVER", "requestId": rid,
        }))

    def test_request_id_peer_and_admission_are_rechecked_per_command(self):
        self.peer_allowed = self.consent_allowed = True
        self.gateway.start()
        rid = self._begin()["requestId"]
        self._check_rejected(self._status("MISMATCHED_REQUEST_ID_1234"))
        self._check_rejected(self._cancel("MISMATCHED_REQUEST_ID_1234"))
        wrong_id = rid[:-1] + ("A" if rid[-1] != "A" else "B")
        self._check_rejected(self._status(wrong_id))
        self._check_rejected(self._cancel(wrong_id))
        self._check_rejected(self._status(None))
        self._check_rejected(self._cancel(None))
        for action in ("STATUS", "CANCEL"):
            self._check_rejected(self._request({
                "schema": COMMAND_SCHEMA,
                "action": action,
                "requestId": rid,
                "signed": True,
            }))
            self._check_rejected(self._request({
                "schema": COMMAND_SCHEMA,
                "action": action,
                "requestId": rid,
                "token": self.secret,
            }))
        self.peer_allowed = False
        self._check_rejected(self._status(rid))
        self._check_rejected(self._cancel(rid))
        self.peer_allowed = True
        self.consent_allowed = False
        self._check_rejected(self._status(rid))
        self._check_rejected(self._cancel(rid))
        self.consent_allowed = True
        self.seat = False
        self._check_rejected(self._status(rid))
        self._check_rejected(self._cancel(rid))
        self.seat = True
        original_peer = self.gateway._owner_peer
        self.gateway._owner_peer = KernelPeer(
            pid=original_peer.pid + 1, uid=original_peer.uid,
            gid=original_peer.gid)
        self._check_rejected(self._status(rid))
        self._check_rejected(self._cancel(rid))
        self.gateway._owner_peer = original_peer
        self.assertEqual(self._status(rid)["state"], "PENDING")
        self.assertEqual(self._cancel(rid)["state"], "CANCELLED")

    def test_invalid_callback_reports_failed_and_denies_cancel(self):
        self.peer_allowed = self.consent_allowed = True
        self.gateway.start()
        rid = self._begin()["requestId"]
        self.assertEqual(self._status(rid)["state"], "PENDING")
        auth = urlsplit(self.urls[0])
        redirect = urlsplit(self.hosts[0].redirect_uri)
        conn = http.client.HTTPConnection("127.0.0.1", redirect.port, timeout=2)
        conn.request(
            "GET", redirect.path + "?" + urlencode({
                "code": "ci-one-use-code", "state": "forged", "iss": ISSUER,
            }),
            headers={"Host": f"127.0.0.1:{redirect.port}"})
        response = conn.getresponse()
        self.assertEqual(response.status, 400)
        response.read()
        conn.close()
        self.assertEqual(self._status(rid)["state"], "FAILED")
        self._check_rejected(self._cancel(rid))
        self._check_rejected(self._begin())

    def test_host_status_expires_local_session_without_token_disclosure(self):
        self.peer_allowed = self.consent_allowed = True
        self.gateway.start()
        rid = self._begin()["requestId"]
        status, _ = self._callback()
        self.assertEqual(status, 200)
        self.assertEqual(self._status(rid)["state"], "AUTHENTICATED")
        self.time = NOW + 181
        self.assertEqual(self._status(rid)["state"], "FAILED")
        self._check_rejected(self._cancel(rid))
        self.assertEqual(read_private_display(
            self.hosts[0].display_socket_path,
            clock=lambda: self.time)["organizations"], [])
        self.assertNotIn(self.secret, json.dumps(self._status(rid)))

    def test_host_lost_is_never_reported_as_authenticated(self):
        self.peer_allowed = self.consent_allowed = True
        self.gateway.start()
        rid = self._begin()["requestId"]
        self.assertEqual(self._status(rid)["state"], "PENDING")
        self.hosts[0].session_event("session-end")
        self.assertEqual(self._status(rid)["state"], "HOST_LOST")
        self._check_rejected(self._cancel(rid))
        self._check_rejected(self._begin())

    def test_no_direct_qml_activation_and_existing_owner_guards(self):
        cpu = (ROOT / "widgets/cpuplus/CpuPlusUniversalSignInHeaderPane.qml").read_text()
        bridge = (ROOT / "services/connections/ConnectionsSignInHostBoundary.js").read_text()
        request = (ROOT / "services/connections/ConnectionsRequestStatus.qml").read_text()
        self.assertIn("HostBoundary.offline()", cpu)
        self.assertIn("canBeginSignIn: false", bridge)
        self.assertIn("readonly property bool hostAuthenticated: false", request)
        self.assertNotIn("desktop_command_gateway_v0", cpu)
        self.assertNotIn("requestSignIn(", cpu)


if __name__ == "__main__":
    unittest.main()
