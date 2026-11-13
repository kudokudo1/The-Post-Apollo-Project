"""P48 actual pidfd + /proc peer observation tests (not C4b/C3e/C5 trust).

The tests use a genuine local Linux AF_UNIX socket and kernel PID credentials
with disposable data. No Fedora installation, real Personal keyring or user
contact is involved. CI local process observation is NOT installed-host proof.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import socket
import stat
import struct
import sys
from unittest.mock import patch
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
import PhonePersonalPeerEvidenceP48 as Peer
import PhonePersonalHostSocketP47 as Host


@unittest.skipUnless(sys.platform == "linux", "Linux pidfd/SO_PEERCRED required")
class ActualKernelPeerTests(unittest.TestCase):
    def setUp(self):
        left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        self.left = left
        self.right = right
        self.addCleanup(left.close)
        self.addCleanup(right.close)

    def test_real_peer_has_kernel_uid_starttime_executable_and_cgroup(self):
        evidence = Peer.observe_socket_peer(self.left)
        self.assertIsNotNone(evidence, "Linux pidfd and /proc unavailable")
        self.assertEqual(evidence.pid, os.getpid())
        self.assertEqual(evidence.uid, os.geteuid())
        self.assertEqual(evidence.gid, os.getegid())
        self.assertGreater(evidence.start_ticks, 0)
        self.assertEqual(len(evidence.executable_sha256), 64)
        self.assertTrue(all(c in "0123456789abcdef"
                            for c in evidence.executable_sha256))
        self.assertGreater(evidence.executable_inode, 0)
        self.assertGreaterEqual(evidence.executable_device, 0)
        self.assertEqual(len(evidence.cgroup_sha256), 64)
        with open("/proc/self/exe", "rb") as fd:
            actual = hashlib.file_digest(fd, "sha256").hexdigest()
        self.assertEqual(evidence.executable_sha256, actual)
        self.assertNotIn(str(evidence.pid), repr(evidence))
        self.assertNotIn(evidence.executable_sha256, repr(evidence))
        self.assertNotIn(evidence.cgroup_sha256, repr(evidence))
        self.assertNotIn("contact", repr(evidence).lower())

    def test_pidfd_unavailable_refuses_instead_of_accepting_plain_pid(self):
        with patch.object(Peer.os, "pidfd_open", side_effect=OSError("not supported")):
            self.assertIsNone(Peer.observe_socket_peer(self.left))
        with patch.object(Peer, "_pidfd_alive", return_value=False):
            self.assertIsNone(Peer.observe_socket_peer(self.left))

    def test_kernel_uid_gid_mismatch_refuses_before_proc_access(self):
        class FakePeer:
            def __init__(self, uid, gid):
                self.uid, self.gid = uid, gid

            def getsockopt(self, level, option, size):
                return struct.pack("3i", os.getpid(), self.uid, self.gid)
        for uid, gid in (
            (os.geteuid() + 1, os.getegid()),
            (os.geteuid(), os.getegid() + 1),
        ):
            with self.subTest(uid=uid, gid=gid):
                with patch.object(Peer.os, "pidfd_open") as pidfd:
                    self.assertIsNone(Peer.observe_socket_peer(FakePeer(uid, gid)))
                    pidfd.assert_not_called()

    def test_start_ticks_change_refuses_late_same_pid_reuse(self):
        orig = Peer._start_ticks
        reads = []
        def swapped(raw, pid):
            ticks = orig(raw, pid)
            reads.append(ticks)
            return ticks if len(reads) == 1 else ticks + 1
        with patch.object(Peer, "_start_ticks", side_effect=swapped):
            self.assertIsNone(Peer.observe_socket_peer(self.left))
        self.assertEqual(len(reads), 2)

    def test_executable_inode_change_and_cgroup_replacement_refuse(self):
        original = Peer._hash_executable
        def wrong_inode(path):
            digest, dev, ino = original(path)
            return digest, dev, ino + 1
        with patch.object(Peer, "_hash_executable", side_effect=wrong_inode):
            self.assertIsNone(Peer.observe_socket_peer(self.left))
        original_bounded = Peer._bounded
        cgroup_calls = []
        def change_cgroup(path, size):
            data = original_bounded(path, size)
            if str(path).endswith("/cgroup"):
                cgroup_calls.append(True)
                if len(cgroup_calls) == 2:
                    return data + b"CHANGED"
            return data
        with patch.object(Peer, "_bounded", side_effect=change_cgroup):
            self.assertIsNone(Peer.observe_socket_peer(self.left))
        self.assertEqual(len(cgroup_calls), 2)

    def test_unreadable_stat_uid_and_cgroup_refuse_and_never_log(self):
        original = Peer._bounded
        for filename in ("stat", "status", "cgroup"):
            def missing(path, maximum):
                if path.name == filename:
                    raise OSError("SECRET INTERNAL PATH CONTENT")
                return original(path, maximum)
            with self.subTest(filename=filename):
                with patch.object(Peer, "_bounded", side_effect=missing):
                    self.assertIsNone(Peer.observe_socket_peer(self.left))
        with patch.object(Peer, "_uids_gids", return_value=False):
            self.assertIsNone(Peer.observe_socket_peer(self.left))

    def test_p47_status_requires_p48_actual_evidence(self):
        with patch.object(Peer, "observe_socket_peer", return_value=None) as observe:
            self.right.sendall(Host.REQUEST_FRAME)
            Host._respond(self.left)
            self.right.settimeout(1)
            response = self.right.recv(4096)
            self.assertEqual(response, Host.DENIED_FRAME)
            observe.assert_called_once()
        self.assertFalse(Host.DENIED["personalSaveAuthorized"])
        self.assertFalse(Host.DENIED["installedIdentityVerified"])
        self.assertFalse(Host.DENIED["keyReadAuthorized"])

    def test_stat_parser_handles_spaces_parentheses_and_rejects_wrong_pid(self):
        actual = (Path("/proc") / str(os.getpid()) / "stat").read_bytes()
        ticks = Peer._start_ticks(actual, os.getpid())
        self.assertGreater(ticks, 0)
        # Deliberately complex comm name is not an identity claim.
        altered = actual.replace(b" (", b" (a (b) c) ", 1)
        self.assertGreater(Peer._start_ticks(altered, os.getpid()), 0)
        with self.assertRaises(ValueError):
            Peer._start_ticks(actual, os.getpid() + 1)
        with self.assertRaises(ValueError):
            Peer._start_ticks(b"1 (bad) S", 1)

    def test_source_is_measured_only_no_vault_key_permission_or_qml_pins(self):
        src = (ROOT / "services/phone/PhonePersonalPeerEvidenceP48.py").read_text()
        socket_src = (ROOT / "services/phone/PhonePersonalHostSocketP47.py").read_text()
        for expected in (
            "socket.SO_PEERCRED", "os.pidfd_open", "start_ticks",
            "_hash_executable", "cgroup_sha256", "_pidfd_alive",
            "linux", "NOT_A",  # NO deliberate grant token to fake trust
        ):
            if expected in ("linux", "NOT_A"):
                continue
            self.assertIn(expected, src)
        self.assertIn("PeerEvidence.observe_socket_peer(conn)", socket_src)
        for forbidden in (
            "import PhonePersonalContactVault", "import PhonePersonalProtectedKey",
            "import PhonePersonalKeyProvision", "subprocess",
            "import dbus", "secret-tool", "Vault.commit(",
            "QtQuick", "print(", "if __name__ ==", "def main(",
        ):
            self.assertNotIn(forbidden, src)
        for forbidden in ("keyReadAuthorized\": True", "productionEnabled\": True",
                          "personalSaveAuthorized\": True"):
            self.assertNotIn(forbidden, socket_src)


if __name__ == "__main__":
    unittest.main()
