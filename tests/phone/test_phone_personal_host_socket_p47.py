"""P47 actual Linux Unix-socket/peer-credentials transport matrix.

Runs against a real AF_UNIX socket on an ephemeral CI temp directory. The
remote interface remains STATUS-ONLY and never accesses keys, contacts or
private data. Actual SO_PEERCRED proves only peer OS credentials, NOT an
installed trusted Identity/C3e/C5 runtime.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import stat
import struct
import sys
from tempfile import TemporaryDirectory
from threading import Event, Thread
import time
from unittest.mock import Mock
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
import PhonePersonalHostSocketP47 as Host


@unittest.skipUnless(sys.platform == "linux", "Linux SO_PEERCRED required")
class RealUnixBoundaryTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory(prefix="p47-linux-socket-")
        self.addCleanup(tmp.cleanup)
        self.directory = Path(tmp.name)
        self.sockpath = self.directory / Host.SOCKET_NAME
        self.stop = Event()
        self.started = Event()
        self.thread = Thread(
            target=Host.serve_status_only,
            args=(self.directory,),
            kwargs={"stop": self.stop, "started": self.started},
            daemon=True,
        )
        self.thread.start()
        self.assertTrue(self.started.wait(2), "socket server not ready")
        self.addCleanup(self.close_host)
        self.assertTrue(self.sockpath.is_socket())

    def close_host(self):
        self.stop.set()
        self.thread.join(timeout=3)
        self.assertFalse(self.thread.is_alive(), "socket server did not stop")
        self.assertFalse(self.sockpath.exists())

    def exchange(self, value: bytes, *, shutdown=False) -> dict[str, object]:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(2)
            client.connect(str(self.sockpath))
            if value:
                client.sendall(value)
            if shutdown:
                client.shutdown(socket.SHUT_WR)
            answer = bytearray()
            while True:
                item = client.recv(4096)
                if not item:
                    break
                answer.extend(item)
        self.assertLessEqual(len(answer), 512)
        self.assertTrue(answer.endswith(b"\n"))
        return json.loads(answer)

    def test_actual_linux_peer_validated_but_all_authority_remains_false(self):
        reply = self.exchange(Host.REQUEST_FRAME)
        self.assertEqual(reply, Host.STATUS)
        self.assertEqual(reply["status"], "HOST_UNTRUSTED_STATUS_ONLY")
        self.assertIs(reply["linuxPeerCredentialsObserved"], True)
        for key in (
            "installedIdentityVerified", "independentChallengeVerified",
            "c5OneUseConsentVerified", "keyReadAuthorized",
            "productionEnabled", "personalSaveAuthorized",
            "readbackTrusted", "retryAuthorized",
        ):
            self.assertIs(reply[key], False)
        self.assertNotIn("pid", str(reply).lower())
        self.assertNotIn("profile", str(reply).lower())
        self.assertNotIn("contact", str(reply).lower())
        self.assertNotIn("note", str(reply).lower())

    def test_kernel_socket_is_owner_only_and_restored_on_shutdown(self):
        self.assertEqual(stat.S_IMODE(self.sockpath.lstat().st_mode), 0o600)
        self.assertEqual(self.sockpath.stat().st_uid, os.geteuid())
        self.assertEqual(stat.S_IMODE(self.directory.stat().st_mode), 0o700)
        self.assertTrue(self.sockpath.is_socket())
        self.assertIs(self.exchange(Host.REQUEST_FRAME)["personalSaveAuthorized"], False)

    def test_no_private_actions_and_no_client_supplied_grant_fields(self):
        invalid = (
            b'{"schema":"post-apollo.phone.personal-host-status.p47.v1","operation":"SAVE"}\n',
            b'{"schema":"post-apollo.phone.personal-host-status.p47.v1","operation":"STATUS","trusted":true}\n',
            b'{"schema":"post-apollo.phone.personal-host-status.p47.v1","operation":"STATUS","note":"PRIVATE"}\n',
            b'{"schema":"post-apollo.phone.personal-host-status.p47.v1","operation":"STATUS","hostVerified":true}\n',
            b'{"schema":"post-apollo.phone.personal-host-status.p47.v1","operation":"STATUS","humanConsentVerified":true}\n',
            b'{"schema":"post-apollo.phone.personal-host-status.p47.v1","operation":"STATUS","keyId":"a"}\n',
            b'{"schema":"post-apollo.phone.personal-host-status.p47.v1","operation":"STATUS","productionEnabled":true}\n',
            b'{"schema":"post-apollo.phone.personal-host-status.p47.v1","operation":"STATUS","operation":"STATUS"}\n',
            b'{"operation":"STATUS","schema":"post-apollo.phone.personal-host-status.p47.v1"}\r\n',
            Host.REQUEST_FRAME + Host.REQUEST_FRAME,
            Host.REQUEST_FRAME + b'{"action":"SAVE"}\n',
            b"",
            b"false\n",
            b"{bad-json}\n",
            b"A" * 513 + b"\n",
        )
        for request in invalid:
            with self.subTest(sample=request[:45]):
                result = self.exchange(request, shutdown=True)
                self.assertEqual(result, Host.DENIED)
                self.assertIs(result["personalSaveAuthorized"], False)
                self.assertIs(result["keyReadAuthorized"], False)
                self.assertIs(result["linuxPeerCredentialsObserved"], False)

    def test_canonical_request_is_accepted_over_multiple_recv_packets(self):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(2)
            client.connect(str(self.sockpath))
            client.sendall(Host.REQUEST_FRAME[:8])
            client.sendall(Host.REQUEST_FRAME[8:22])
            client.sendall(Host.REQUEST_FRAME[22:])
            client.shutdown(socket.SHUT_WR)
            data = bytearray()
            while True:
                chunk = client.recv(1024)
                if not chunk:
                    break
                data.extend(chunk)
        self.assertEqual(json.loads(data), Host.STATUS)

    def test_missing_newline_times_out_denied_without_server_stall(self):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(3)
            client.connect(str(self.sockpath))
            client.sendall(Host.REQUEST_FRAME[:-1])
            answer = client.recv(4096)
        self.assertEqual(json.loads(answer), Host.DENIED)
        self.assertEqual(self.exchange(Host.REQUEST_FRAME), Host.STATUS)

    def test_repeated_requests_do_not_authorize_save_or_break_server(self):
        for _ in range(20):
            self.assertEqual(
                self.exchange(Host.REQUEST_FRAME)["status"],
                "HOST_UNTRUSTED_STATUS_ONLY"
            )
        self.assertFalse(self.stop.is_set())
        self.assertTrue(self.thread.is_alive())

    def test_kernel_uid_mismatch_denied_in_unit_only_mock(self):
        class FakeSocket:
            def getsockopt(self, level, name, length):
                self_args = (level, name, length)
                self.assertIsNotNone if False else None
                return struct.pack("3i", os.getpid(), os.geteuid() + 1, os.getegid())
        self.assertFalse(Host._kernel_same_uid_peer(FakeSocket()))

    def test_source_never_links_keyring_blueferry_or_vault(self):
        text = (ROOT / "services/phone/PhonePersonalHostSocketP47.py").read_text()
        for needle in (
            "def serve_status_only(", "socket.SO_PEERCRED",
            "0o600", "0o700", "client",
            "installedIdentityVerified", "False",
        ):
            self.assertIn(needle, text)
        for prohibited in (
            "PhonePersonalProtectedKeyP45", "PhonePersonalContactVault",
            "PhonePersonalKeyProvisionP46", "PhonePersonalRecoveryEnvelopeP46",
            "PhonePersonalHostGateP36", "import dbus",
            "subprocess", "secret-tool", "Vault.commit(",
            "os.environ", "print(", "import QtQuick",
            "if __name__ ==", "def main(",
        ):
            self.assertNotIn(prohibited, text)


@unittest.skipUnless(sys.platform == "linux", "Linux SO_PEERCRED required")
class SocketSetupRefusalTests(unittest.TestCase):
    def test_directory_must_be_abs_owner_mode_700_and_not_symlink(self):
        with TemporaryDirectory(prefix="p47-private-") as temp:
            root = Path(temp)
            symlink = root.parent / (root.name + "-link")
            symlink.symlink_to(root, target_is_directory=True)
            self.addCleanup(lambda: symlink.unlink(missing_ok=True))
            invalid = (
                "relative", root.as_posix(), symlink, Path("/not-exist-p47"),
                Path("/"),
            )
            for path in invalid:
                with self.subTest(path=path):
                    with self.assertRaises(Host.HostBoundaryRefused):
                        Host._private_directory(path)
            os.chmod(root, 0o750)
            with self.assertRaises(Host.HostBoundaryRefused):
                Host._private_directory(root)
            os.chmod(root, 0o700)
            self.assertEqual(Host._private_directory(root), root)

    def test_existing_socket_name_never_overwritten_or_deleted(self):
        with TemporaryDirectory(prefix="p47-private-") as temp:
            root = Path(temp)
            target = root / Host.SOCKET_NAME
            target.write_text("protected-existing-file", encoding="utf-8")
            with self.assertRaises(Host.HostBoundaryRefused):
                Host.serve_status_only(root, stop=Event())
            self.assertEqual(target.read_text(encoding="utf-8"),
                             "protected-existing-file")

    def test_non_event_controls_refuse_before_socket(self):
        with TemporaryDirectory(prefix="p47-private-") as temp:
            root = Path(temp)
            with self.assertRaises(Host.HostBoundaryRefused):
                Host.serve_status_only(root, stop=True)
            self.assertFalse((root / Host.SOCKET_NAME).exists())


if __name__ == "__main__":
    unittest.main()
