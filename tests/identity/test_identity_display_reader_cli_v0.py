"""Real CLI child process -> private Unix socket, no OAuth or QML runtime.

The CLI is the only subprocess Quickshell may launch. It receives only
--json, never a token, path, user ID, company selector or authorization code.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "identity"))
from identity_display_reader_cli_v0 import (
    RUNTIME_CHILD, _runtime_socket, snapshot,
)
from private_context_ipc_v0 import (
    DISPLAY_SCHEMA, SOCKET_NAME, PrivateContextSocket,
)

NOW = 2_000_000_000
CLI = ROOT / "services/identity/identity_display_reader_cli_v0.py"


def synthetic_context():
    return {
        "schema": DISPLAY_SCHEMA, "status": "READY",
        "organizations": [
            {"organizationId": "llc_a", "kind": "llc",
             "scopeGrants": [{"action": "records.read", "divisionId": "health",
                              "unitId": "maryland", "expiresAt": None}]},
            {"organizationId": "llc_b", "kind": "llc", "scopeGrants": []},
        ],
        "portfolios": [{
            "portfolioId": "family", "organizationIds": ["llc_a", "llc_b"]
        }],
        "canSwitchOrganization": False,
    }


class PrivateDisplayReaderCLIContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="identity-cli-ci-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.root.chmod(0o700)
        self.child = self.root / RUNTIME_CHILD
        self.child.mkdir(mode=0o700)
        self.sock = self.child / SOCKET_NAME

    def run_cli(self, *args, env=None):
        params = {**os.environ, "XDG_RUNTIME_DIR": str(self.root)}
        if env:
            params.update(env)
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=5, env=params, check=False,
        )

    def test_cli_requires_exact_json_command(self):
        for args in ((), ("--help",), ("--json", "--socket", str(self.sock)),
                     ("LOGIN",), ("LOGOUT",), ("SELECT", "llc_a"),
                     ("--access-token", "SECRET")):
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, "")

    def test_missing_host_returns_empty_json_with_success_exit(self):
        result = self.run_cli("--json")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout.count("\n"), 1)
        self.assertEqual(json.loads(result.stdout), {
            "schema": DISPLAY_SCHEMA, "status": "UNAVAILABLE",
            "organizations": [], "portfolios": [],
            "canSwitchOrganization": False,
        })

    def test_actual_socket_in_other_process_returns_only_display_fields(self):
        with PrivateContextSocket(
            runtime_directory=self.child,
            snapshot_provider=synthetic_context,
            clock=lambda: NOW,
        ):
            result = self.run_cli("--json")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        display = json.loads(result.stdout)
        self.assertEqual(display["status"], "READY")
        self.assertEqual([x["organizationId"] for x in display["organizations"]],
                         ["llc_a", "llc_b"])
        self.assertEqual(display["portfolios"][0]["organizationIds"],
                         ["llc_a", "llc_b"])
        self.assertFalse(display["canSwitchOrganization"])
        self.assertEqual(set(display), {
            "schema", "status", "organizations", "portfolios",
            "canSwitchOrganization",
        })
        for forbidden in ("accessToken", "refreshToken", "principalId",
                          "sessionId", "Bearer", "password", "subject",
                          "SECRET", "authorizationCode"):
            self.assertNotIn(forbidden, result.stdout)

    def test_shutdown_immediately_returns_empty_not_stale(self):
        with PrivateContextSocket(
            runtime_directory=self.child,
            snapshot_provider=synthetic_context,
            clock=lambda: NOW,
        ):
            self.assertEqual(json.loads(self.run_cli("--json").stdout)["status"],
                             "READY")
        empty = json.loads(self.run_cli("--json").stdout)
        self.assertEqual(empty["status"], "UNAVAILABLE")
        self.assertEqual(empty["organizations"], [])

    def test_signed_out_host_returns_empty(self):
        signed_out = {
            "schema": DISPLAY_SCHEMA, "status": "SIGNED_OUT",
            "organizations": [], "portfolios": [],
            "canSwitchOrganization": False,
        }
        with PrivateContextSocket(
            runtime_directory=self.child,
            snapshot_provider=lambda: signed_out,
            clock=lambda: NOW,
        ):
            view = json.loads(self.run_cli("--json").stdout)
        self.assertEqual(view["status"], "SIGNED_OUT")
        self.assertEqual(view["organizations"], [])

    def test_invalid_backend_extra_token_never_surfaces_in_stdout(self):
        data = {**synthetic_context(), "accessToken": "CI_PRIVATE_SECRET"}
        with PrivateContextSocket(
            runtime_directory=self.child,
            snapshot_provider=lambda: data,
            clock=lambda: NOW,
        ):
            reply = self.run_cli("--json")
        self.assertEqual(reply.returncode, 0)
        self.assertNotIn("CI_PRIVATE_SECRET", reply.stdout + reply.stderr)
        self.assertEqual(json.loads(reply.stdout)["status"], "UNAVAILABLE")

    def test_missing_runtime_dir_never_falls_back_to_home_or_tmp(self):
        self.assertIsNone(_runtime_socket({}))
        self.assertIsNone(_runtime_socket({"XDG_RUNTIME_DIR": "relative"}))
        self.assertIsNone(_runtime_socket({"XDG_RUNTIME_DIR": "../tmp"}))
        self.assertIsNone(_runtime_socket({"XDG_RUNTIME_DIR": "/tmp"}))
        result = self.run_cli("--json", env={"XDG_RUNTIME_DIR": ""})
        self.assertEqual(json.loads(result.stdout)["organizations"], [])

    def test_group_accessible_runtime_dir_is_rejected(self):
        self.root.chmod(0o750)
        try:
            self.assertIsNone(_runtime_socket({"XDG_RUNTIME_DIR": str(self.root)}))
            self.assertEqual(json.loads(self.run_cli("--json").stdout)["status"],
                             "UNAVAILABLE")
        finally:
            self.root.chmod(0o700)

    def test_symlinked_runtime_root_is_rejected(self):
        link = self.root.parent / (self.root.name + "-symlink")
        link.symlink_to(self.root)
        self.addCleanup(lambda: link.unlink(missing_ok=True))
        self.assertIsNone(_runtime_socket({"XDG_RUNTIME_DIR": str(link)}))

    def test_cli_never_creates_runtime_files_or_socket(self):
        self.assertFalse(self.sock.exists())
        self.run_cli("--json")
        self.assertFalse(self.sock.exists())
        self.assertEqual(stat.S_IMODE(self.child.stat().st_mode), 0o700)

    def test_view_cannot_expose_other_tenant_from_fake_portfolio(self):
        forged = synthetic_context()
        forged["portfolios"][0]["organizationIds"].append("nonprofit")
        with PrivateContextSocket(
            runtime_directory=self.child,
            snapshot_provider=lambda: forged,
            clock=lambda: NOW,
        ):
            reply = self.run_cli("--json")
        self.assertEqual(json.loads(reply.stdout)["organizations"], [])
        self.assertNotIn("nonprofit", reply.stdout)


if __name__ == "__main__":
    unittest.main()
