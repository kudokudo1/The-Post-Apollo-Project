"""P49 actual separate Linux status-host process lifecycle tests.

Spawns an actual Python -I child in the GitHub runner, requiring explicit
CI-only environment and private socket directory. Never installs the systemd
unit, invokes the user's keyring or touches any real Personal contact.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import socket
import stat
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services/phone/PhonePersonalStatusHostP49.py"
UNIT = ROOT / "services/phone/systemd/post-apollo-phone-personal-status-ci.service"
sys.path.insert(0, str(ROOT / "services" / "phone"))
import PhonePersonalHostSocketP47 as SocketHost

ENV = {
    "POST_APOLLO_PHONE_STATUS_CI_ONLY": "1",
    "POST_APOLLO_PHONE_STATUS_NO_SAVE": "1",
}


@unittest.skipUnless(sys.platform == "linux", "Linux socket/pidfd required")
class ActualSubprocessTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory(prefix="p49-status-host-")
        self.addCleanup(tmp.cleanup)
        self.directory = Path(tmp.name)
        self.sock = self.directory / SocketHost.SOCKET_NAME
        self.children = []
        self.addCleanup(self.cleanup_children)

    def cleanup_children(self):
        for p in self.children:
            if p.poll() is None:
                p.send_signal(signal.SIGTERM)
                try:
                    p.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait(timeout=3)
            if p.stdout:
                p.stdout.close()
            if p.stderr:
                p.stderr.close()

    def child(self, *, directory=None, overrides=None, argv=None):
        env = os.environ.copy()
        env.update(ENV)
        if overrides is not None:
            for k, v in overrides.items():
                if v is None:
                    env.pop(k, None)
                else:
                    env[k] = v
        args = (
            [sys.executable, "-I", "-B", str(SERVICE)]
            + (["--private-status-dir", str(
                self.directory if directory is None else directory)]
               if argv is None else argv)
        )
        proc = subprocess.Popen(
            args, cwd=str(ROOT), env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.children.append(proc)
        return proc

    def start(self):
        proc = self.child()
        until = time.monotonic() + 8
        while time.monotonic() < until:
            if self.sock.is_socket():
                return proc
            if proc.poll() is not None:
                err = proc.stderr.read().decode("utf-8", errors="replace")
                self.fail("P49 child exited before private socket: " + err[:700])
            time.sleep(0.04)
        self.fail("P49 did not create its private status-only socket")

    def exchange(self, raw):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(3)
            client.connect(str(self.sock))
            client.sendall(raw)
            client.shutdown(socket.SHUT_WR)
            payload = bytearray()
            while True:
                data = client.recv(2048)
                if not data:
                    break
                payload.extend(data)
        return json.loads(payload)

    def test_spawned_process_status_only_no_keys_and_clean_shutdown(self):
        proc = self.start()
        self.assertIsNone(proc.poll())
        self.assertEqual(stat.S_IMODE(self.sock.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.directory.stat().st_mode), 0o700)
        status = self.exchange(SocketHost.REQUEST_FRAME)
        self.assertEqual(status, SocketHost.STATUS)
        for name in (
            "installedIdentityVerified", "independentChallengeVerified",
            "c5OneUseConsentVerified", "keyReadAuthorized",
            "productionEnabled", "personalSaveAuthorized",
            "readbackTrusted", "retryAuthorized",
        ):
            self.assertIs(status[name], False)
        self.assertEqual(self.exchange(
            b'{"operation":"SAVE","schema":"fake","note":"PRIVATE"}\n'
        ), SocketHost.DENIED)
        self.assertEqual(self.exchange(SocketHost.REQUEST_FRAME), SocketHost.STATUS)
        proc.send_signal(signal.SIGTERM)
        out, err = proc.communicate(timeout=5)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(out, b"")
        self.assertEqual(err, b"")
        self.assertFalse(self.sock.exists())

    def test_missing_test_flags_abort_before_socket(self):
        for overrides in (
            {"POST_APOLLO_PHONE_STATUS_CI_ONLY": None},
            {"POST_APOLLO_PHONE_STATUS_NO_SAVE": None},
            {"POST_APOLLO_PHONE_STATUS_CI_ONLY": "false"},
            {"POST_APOLLO_PHONE_STATUS_NO_SAVE": "true"},
        ):
            with self.subTest(flags=overrides):
                proc = self.child(overrides=overrides)
                out, err = proc.communicate(timeout=5)
                self.assertEqual(proc.returncode, 78)
                self.assertEqual(out, b"")
                self.assertEqual(err, b"")
                self.assertFalse(self.sock.exists())

    def test_invalid_directory_and_args_abort_without_overwrite(self):
        for args in (
            [],
            ["--private-status-dir", "relative/path"],
            ["--private-status-dir", str(self.directory), "--enable-save"],
            ["--enable-save", str(self.directory)],
        ):
            with self.subTest(args=args):
                proc = self.child(argv=args)
                out, err = proc.communicate(timeout=5)
                self.assertEqual(proc.returncode, 78)
                self.assertFalse(self.sock.exists())
                self.assertEqual(out + err, b"")
        self.sock.write_text("EXISTING PRIVATE CONTENT")
        proc = self.child()
        proc.wait(timeout=5)
        self.assertEqual(proc.returncode, 78)
        self.assertEqual(self.sock.read_text(), "EXISTING PRIVATE CONTENT")

    def test_mode_750_refused_and_does_not_change_permissions(self):
        self.directory.chmod(0o750)
        proc = self.child()
        out, err = proc.communicate(timeout=5)
        self.assertEqual(proc.returncode, 78)
        self.assertFalse(self.sock.exists())
        self.assertEqual(out + err, b"")
        self.assertEqual(stat.S_IMODE(self.directory.stat().st_mode), 0o750)


class StaticPackageTests(unittest.TestCase):
    def test_service_unit_inert_no_install_and_never_production_key_access(self):
        source = UNIT.read_text()
        self.assertIn("User=postapollo-phone-status-ci", source)
        self.assertIn("Group=postapollo-phone-status-ci", source)
        self.assertIn("RuntimeDirectoryMode=0700", source)
        self.assertIn("NoNewPrivileges=true", source)
        self.assertIn("ProtectSystem=strict", source)
        self.assertIn("ProtectHome=true", source)
        self.assertIn("RestrictAddressFamilies=AF_UNIX", source)
        self.assertIn("CapabilityBoundingSet=", source)
        self.assertIn("ConditionPathExists=", source)
        self.assertIn("ExecStart=/usr/bin/python3 -I -B", source)
        self.assertNotIn("\n[Install]", source)
        self.assertNotIn("WantedBy=", source)
        self.assertNotIn("systemctl enable", source)
        for forbidden in ("--enable-save", "PHONE_MASTER_KEY",
                          "secret-tool", "ExecStartPost=", "Keyring"):
            self.assertNotIn(forbidden, source)

    def test_entrypoint_only_imports_source_status_and_kernel_observer(self):
        code = SERVICE.read_text()
        self.assertIn("SocketHost.serve_status_only(directory, stop=stop)", code)
        self.assertIn("Peer.observe_socket_peer(a)", code)
        self.assertIn("_self_source_snapshot() != expected", code)
        for forbidden in (
            "PhonePersonalContactVault", "PhonePersonalContactIdentity",
            "PhonePersonalProtectedKey", "PhonePersonalKeyProvision",
            "PhonePersonalRecoveryEnvelope", "PhonePersonalSignedTrust",
            "Vault.commit(", "import dbus", "secret-tool",
            "QtQuick", "console.log", "print(",
        ):
            self.assertNotIn(forbidden, code)
        self.assertIn('if __name__ == "__main__":', code)


if __name__ == "__main__":
    unittest.main()
