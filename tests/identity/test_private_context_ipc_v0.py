"""CI-only Linux Unix-socket identity display tests; NO desktop changes.

The host test generates a bearer only inside a separate spawned Python
process. A parent viewer can send exactly "SNAPSHOT\\n" but cannot request a
different person, company, login, logout, OAuth token or privileged action.
"""
from __future__ import annotations

import json
import multiprocessing
import os
from pathlib import Path
import secrets
import socket
import stat
import sys
import tempfile
import time
import unittest
from urllib.parse import parse_qs, urlencode, urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "identity"))
from desktop_context_projection_v0 import HostContextReply
from desktop_session_host_v0 import DesktopSessionHost, TrustedHostConfig, VerifiedCodeExchange
from private_context_ipc_v0 import (
    DISPLAY_SCHEMA, SOCKET_NAME, PrivateContextSocket, _clean,
    empty_display, read_private_display,
)

NOW = 1_700_000_100


def sample(status="READY"):
    orgs = [
        {"organizationId": "llc_a", "kind": "llc",
         "scopeGrants": [{"action": "records.read", "divisionId": "health",
                          "unitId": "maryland", "expiresAt": NOW + 600}]},
        {"organizationId": "llc_b", "kind": "llc", "scopeGrants": []},
    ]
    ports = [{"portfolioId": "family", "organizationIds": ["llc_a", "llc_b"]}]
    return {
        "schema": DISPLAY_SCHEMA, "status": status,
        "organizations": orgs if status == "READY" else [],
        "portfolios": ports if status == "READY" else [],
        "canSwitchOrganization": False,
    }


def _child_host(directory: str, ready, revoke, stop) -> None:
    """No token is sent to the parent, disk or the Unix-socket reader."""
    from private_context_ipc_v0 import PrivateContextSocket
    from desktop_session_host_v0 import (
        DesktopSessionHost, TrustedHostConfig, VerifiedCodeExchange,
    )
    from desktop_context_projection_v0 import HostContextReply
    from urllib.parse import parse_qs, urlencode, urlsplit
    import secrets
    import json
    import time

    clock = lambda: int(time.time())
    opened = []
    # This private bearer exists ONLY in the spawned host process.
    secret = "CI-CHILD-ONLY-" + secrets.token_urlsafe(32)
    audience = "ci-api"
    issuer = "https://synthetic-idp.invalid/realms/test"
    config = TrustedHostConfig(
        issuer=issuer, authorization_endpoint=issuer + "/protocol/openid-connect/auth",
        client_id="ci-native", api_audience=audience,
        redirect_uri="http://127.0.0.1:8765/callback",
    )

    def exchange(code, verifier, nonce, redirect):
        if code != "ci-disposable-code":
            raise AssertionError("Wrong code in host-only callback")
        return VerifiedCodeExchange(
            access_token=secret, issuer=issuer, client_id="ci-native",
            nonce=nonce, subject="private-ci-person",
            expires_at=clock() + 180, token_type="Bearer",
            signed_id_token_verified=True,
        )

    def api_get(bearer):
        if bearer != secret:
            return HostContextReply(401, "application/json",
                                    b'{"status":"DENIED"}')
        body = {
            "schema": "post-apollo.identity.context-summary.v0", "status": "OK",
            "organizations": [
                {"organizationId": "llc_a", "kind": "llc", "scopeGrants": []}
            ],
            "portfolios": [],
        }
        return HostContextReply(
            200, "application/json", json.dumps(body).encode("utf-8"),
        )

    host = DesktopSessionHost(
        config=config, browser_open=lambda url: opened.append(url),
        exchange_and_verify=exchange, api_get=api_get, clock=clock,
    )
    if host.start_login()["status"] != "LOGIN_PENDING":
        raise AssertionError("Test-only PKCE login did not start")
    state = parse_qs(urlsplit(opened[0]).query)["state"][0]
    callback = config.redirect_uri + "?" + urlencode({
        "code": "ci-disposable-code", "state": state, "iss": issuer,
    })
    if host.complete_callback(callback)["status"] != "SIGNED_IN":
        raise AssertionError("Host rejected disposable verified session")

    try:
        with PrivateContextSocket(
            runtime_directory=Path(directory),
            snapshot_provider=lambda: host.refresh_context(),
            clock=clock,
        ):
            ready.set()
            while not stop.wait(0.025):
                if revoke.is_set():
                    host.logout()
                    revoke.clear()
    finally:
        host.logout()


class PrivateContextIPCTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="post-apollo-ipc-v0-")
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        os.chmod(self.path, 0o700)
        self.sock = self.path / SOCKET_NAME

    def test_construct_does_not_start_or_bind_socket(self):
        server = PrivateContextSocket(
            runtime_directory=self.path,
            snapshot_provider=sample, clock=lambda: NOW,
        )
        self.assertFalse(self.sock.exists())
        with self.assertRaises(RuntimeError):
            _ = server.socket_path
        server.close()
        self.assertFalse(self.sock.exists())

    def test_linux_private_socket_and_readonly_view(self):
        with PrivateContextSocket(
            runtime_directory=self.path,
            snapshot_provider=sample, clock=lambda: NOW,
        ) as server:
            self.assertEqual(server.socket_path, self.sock)
            meta = self.sock.lstat()
            self.assertTrue(stat.S_ISSOCK(meta.st_mode))
            self.assertEqual(stat.S_IMODE(meta.st_mode), 0o600)
            self.assertEqual(meta.st_uid, os.geteuid())
            output = read_private_display(self.sock, clock=lambda: NOW)
            self.assertEqual(output["status"], "READY")
            self.assertEqual([x["organizationId"] for x in output["organizations"]],
                             ["llc_a", "llc_b"])
            self.assertFalse(output["canSwitchOrganization"])
        self.assertFalse(self.sock.exists())

    def test_no_socket_or_dead_host_fails_closed(self):
        self.assertEqual(read_private_display(
            self.sock, clock=lambda: NOW,
        )["status"], "UNAVAILABLE")
        with PrivateContextSocket(
            runtime_directory=self.path,
            snapshot_provider=sample, clock=lambda: NOW,
        ):
            self.assertEqual(read_private_display(
                self.sock, clock=lambda: NOW,
            )["status"], "READY")
        self.assertEqual(read_private_display(
            self.sock, clock=lambda: NOW,
        )["organizations"], [])

    def test_no_client_data_can_select_tenant_or_change_host(self):
        calls = []
        def provider():
            calls.append(True)
            return sample()
        with PrivateContextSocket(
            runtime_directory=self.path, snapshot_provider=provider,
            clock=lambda: NOW,
        ):
            for data in (b"LOGIN\n", b"LOGOUT\n", b"SELECT llc_b\n",
                         b'{"organizationId":"nonprofit"}\n',
                         b"SNAPSHOT\nEXTRA", b"SNAPSHOT", b""):
                with self.subTest(data=data):
                    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                        client.settimeout(2)
                        client.connect(str(self.sock))
                        client.sendall(data)
                        response = client.recv(2048)
                        if response:
                            parsed = json.loads(response.strip())
                            self.assertEqual(parsed["organizations"], [])
            self.assertEqual(calls, [])
            self.assertEqual(read_private_display(
                self.sock, clock=lambda: NOW,
            )["status"], "READY")
            self.assertEqual(calls, [True])

    def test_client_does_not_accept_portfolio_escalation(self):
        payload = sample()
        payload["portfolios"][0]["organizationIds"].append("nonprofit")
        with PrivateContextSocket(
            runtime_directory=self.path, snapshot_provider=lambda: payload,
            clock=lambda: NOW,
        ):
            view = read_private_display(self.sock, clock=lambda: NOW)
            self.assertEqual(view["status"], "UNAVAILABLE")
            self.assertEqual(view["organizations"], [])

    def test_client_does_not_accept_token_role_or_subject(self):
        for key, value in (("accessToken", "SECRET"), ("role", "owner"),
                           ("principalId", "private"), ("session", {})):
            with self.subTest(key=key):
                snapshot = {**sample(), key: value}
                with PrivateContextSocket(
                    runtime_directory=self.path,
                    snapshot_provider=lambda s=snapshot: s, clock=lambda: NOW,
                ):
                    result = read_private_display(self.sock, clock=lambda: NOW)
                    self.assertEqual(result["status"], "UNAVAILABLE")
                    self.assertNotIn("SECRET", repr(result))

    def test_no_refresh_of_stale_scope(self):
        with PrivateContextSocket(
            runtime_directory=self.path, snapshot_provider=sample,
            clock=lambda: NOW + 600,
        ):
            self.assertEqual(read_private_display(
                self.sock, clock=lambda: NOW + 600,
            )["status"], "UNAVAILABLE")

    def test_wrong_display_schema_fails_closed(self):
        item = sample()
        item["schema"] = "unexpected-version"
        with PrivateContextSocket(
            runtime_directory=self.path, snapshot_provider=lambda: item,
            clock=lambda: NOW,
        ):
            self.assertEqual(read_private_display(
                self.sock, clock=lambda: NOW,
            )["organizations"], [])

    def test_nonready_and_no_memberships_are_distinct(self):
        for status in ("NOT_CONNECTED", "SIGNED_OUT",
                       "UNAVAILABLE", "NO_MEMBERSHIPS"):
            with self.subTest(status=status):
                with PrivateContextSocket(
                    runtime_directory=self.path,
                    snapshot_provider=lambda s=status: sample(s),
                    clock=lambda: NOW,
                ):
                    item = read_private_display(self.sock, clock=lambda: NOW)
                    self.assertEqual(item["status"], status)
                    self.assertEqual(item["organizations"], [])
                    self.assertEqual(item["portfolios"], [])

    def test_invalid_ready_with_no_orgs_fails_closed(self):
        item = sample("NO_MEMBERSHIPS")
        item["status"] = "READY"
        self.assertEqual(_clean_failure(item), "UNAVAILABLE")

    def test_invalid_nonready_with_previous_company_fails_closed(self):
        item = sample()
        item["status"] = "SIGNED_OUT"
        self.assertEqual(_clean_failure(item), "UNAVAILABLE")

    def test_forged_org_switch_is_rejected(self):
        item = sample()
        item["canSwitchOrganization"] = True
        self.assertEqual(_clean_failure(item), "UNAVAILABLE")

    def test_invalid_clock_and_producer_exceptions_fail_closed(self):
        with PrivateContextSocket(
            runtime_directory=self.path,
            snapshot_provider=lambda: (_ for _ in ()).throw(
                RuntimeError("private bearer string must not leak")
            ), clock=lambda: NOW,
        ):
            self.assertEqual(read_private_display(
                self.sock, clock=lambda: NOW,
            )["status"], "UNAVAILABLE")
        with PrivateContextSocket(
            runtime_directory=self.path,
            snapshot_provider=sample, clock=lambda: True,
        ):
            self.assertEqual(read_private_display(
                self.sock, clock=lambda: NOW,
            )["status"], "UNAVAILABLE")

    def test_client_clock_failure_hides_data(self):
        with PrivateContextSocket(
            runtime_directory=self.path,
            snapshot_provider=sample, clock=lambda: NOW,
        ):
            self.assertEqual(read_private_display(
                self.sock, clock=lambda: True,
            )["organizations"], [])

    def test_runtime_dir_must_be_private_no_symlinks(self):
        os.chmod(self.path, 0o755)
        with self.assertRaises(ValueError):
            PrivateContextSocket(
                runtime_directory=self.path,
                snapshot_provider=sample, clock=lambda: NOW,
            )
        os.chmod(self.path, 0o700)
        link = self.path.parent / (self.path.name + "-link")
        link.symlink_to(self.path)
        self.addCleanup(lambda: link.unlink(missing_ok=True))
        with self.assertRaises(ValueError):
            PrivateContextSocket(
                runtime_directory=link,
                snapshot_provider=sample, clock=lambda: NOW,
            )

    def test_existing_socket_path_cannot_be_overwritten(self):
        self.sock.write_text("unrelated file", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            PrivateContextSocket(
                runtime_directory=self.path,
                snapshot_provider=sample, clock=lambda: NOW,
            ).start()
        self.assertEqual(self.sock.read_text(), "unrelated file")

    def test_cannot_restart_closed_server(self):
        server = PrivateContextSocket(
            runtime_directory=self.path,
            snapshot_provider=sample, clock=lambda: NOW,
        )
        server.start()
        server.close()
        with self.assertRaises(RuntimeError):
            server.start()
        self.assertFalse(self.sock.exists())

    def test_oversized_snapshot_returns_no_company_data(self):
        sample_large = sample()
        sample_large["organizations"][0]["organizationId"] = "x" * 90000
        with PrivateContextSocket(
            runtime_directory=self.path,
            snapshot_provider=lambda: sample_large, clock=lambda: NOW,
        ):
            view = read_private_display(self.sock, clock=lambda: NOW)
            self.assertEqual(view["organizations"], [])
            self.assertEqual(view["status"], "UNAVAILABLE")

    def test_separate_host_process_keeps_private_bearer_off_socket(self):
        ctx = multiprocessing.get_context("spawn")
        ready, revoke, stop = ctx.Event(), ctx.Event(), ctx.Event()
        process = ctx.Process(
            target=_child_host, args=(str(self.path), ready, revoke, stop),
            name="identity-ci-isolated-host",
        )
        process.start()
        try:
            self.assertTrue(ready.wait(timeout=12), "Host child failed to start")
            self.assertNotEqual(process.pid, os.getpid())
            good = read_private_display(self.sock, clock=lambda: int(time.time()))
            self.assertEqual(good["status"], "READY")
            self.assertEqual([o["organizationId"] for o in good["organizations"]],
                             ["llc_a"])
            self.assertFalse(good["canSwitchOrganization"])
            for secret_marker in ("CI-CHILD-ONLY", "private-ci-person",
                                  "accessToken", "refreshToken", "code_verifier"):
                self.assertNotIn(secret_marker, repr(good))
            revoke.set()
            for _ in range(60):
                if not revoke.is_set():
                    break
                time.sleep(0.05)
            denied = read_private_display(self.sock, clock=lambda: int(time.time()))
            self.assertIn(denied["status"], ("SIGNED_OUT", "NOT_CONNECTED"))
            self.assertEqual(denied["organizations"], [])
        finally:
            stop.set()
            process.join(timeout=8)
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
        self.assertEqual(process.exitcode, 0)
        self.assertEqual(read_private_display(
            self.sock, clock=lambda: int(time.time()),
        )["organizations"], [])


def _clean_failure(item):
    try:
        _clean(item, NOW)
    except ValueError:
        return "UNAVAILABLE"
    return "INCORRECTLY_ACCEPTED"


if __name__ == "__main__":
    unittest.main()
