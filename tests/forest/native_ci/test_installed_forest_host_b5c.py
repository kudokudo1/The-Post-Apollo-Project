"""Installed Forest CI package probe, not an installed-origin authenticator."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import unittest

HOST = Path("/usr/libexec/post-apollo/forest-ci/forest-host")
PYTHON = "/usr/bin/python3"
EXPECTED_SHA = ""
# Deliberately independent of imported candidate code.
HOLD = {
    "schema": "post-apollo.forest.b5b-ci-only",
    "status": "UNKNOWN_HOLD",
    "sourceAuthenticated": False,
    "recipientAuthenticated": False,
    "permissionGranted": False,
    "productionAuthority": False,
    "privateBytesSubmitted": 0,
    "revocationFencedAck": False,
    "safeActions": [],
}


class InstalledCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.getuid() == 0 or os.geteuid() == 0:
            raise RuntimeError("UNPRIVILEGED_TEST_REQUIRED")
        if len(EXPECTED_SHA) != 64:
            raise RuntimeError("EXPECTED_SOURCE_DIGEST_REQUIRED")

    def test_exact_root_owned_nonwritable_installed_file(self):
        info = HOST.lstat()
        self.assertTrue(stat.S_ISREG(info.st_mode))
        self.assertEqual((info.st_uid, info.st_gid), (0, 0))
        self.assertEqual(stat.S_IMODE(info.st_mode), 0o555)
        self.assertFalse(os.access(HOST, os.W_OK))
        self.assertFalse(os.access(HOST.parent, os.W_OK))
        self.assertEqual(hashlib.sha256(HOST.read_bytes()).hexdigest(),
                         EXPECTED_SHA)

    def launch(self):
        left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.addCleanup(left.close)
        self.addCleanup(right.close)
        left.settimeout(5)
        fd = right.fileno()
        inode = os.fstat(fd).st_ino
        argv = [PYTHON, "-I", "-B", str(HOST),
                "--disposable-test-fd", str(fd)]
        process = subprocess.Popen(argv, pass_fds=(fd,), cwd="/",
                                   stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        self.addCleanup(self.reap, process)
        right.close()
        return left, process, fd, inode, argv

    @staticmethod
    def reap(process):
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)

    def finish(self, process, code):
        stdout, stderr = process.communicate(timeout=5)
        self.assertEqual(process.returncode, code)
        self.assertEqual((stdout, stderr), (b"", b""))

    def assert_public_hold(self, channel):
        wire = channel.recv(4096)
        self.assertEqual(json.loads(wire), HOLD)
        self.assertEqual(channel.recv(4096), b"")

    def test_actual_installed_child_process_and_socket_inode(self):
        channel, process, fd, inode, argv = self.launch()
        proc = Path("/proc") / str(process.pid)
        self.assertNotEqual(process.pid, os.getpid())
        self.assertEqual(os.readlink(proc / "exe"),
                         os.path.realpath(PYTHON))
        observed = (proc / "cmdline").read_bytes().rstrip(b"\0").split(b"\0")
        self.assertEqual(observed, [item.encode() for item in argv])
        uid_line = next(line for line in (proc / "status").read_text().splitlines()
                        if line.startswith("Uid:"))
        self.assertEqual([int(n) for n in uid_line.split()[1:]],
                         [os.getuid()] * 4)
        self.assertEqual(os.readlink(proc / "fd" / str(fd)),
                         f"socket:[{inode}]")
        channel.sendall(b"STATUS")
        self.assert_public_hold(channel)
        self.finish(process, 0)

    def test_all_protected_operations_remain_public_hold(self):
        for token in (b"LIST_SESSIONS", b"DISCLOSE_SESSION_TITLES",
                      b"READ_SESSION", b"GENERATE", b"DISCLOSE_PROVISIONAL",
                      b"COMMIT_GENERATE", b"SEND", b"VOICE"):
            with self.subTest(token=token):
                channel, process, _, _, _ = self.launch()
                channel.sendall(token)
                self.assert_public_hold(channel)
                self.finish(process, 0)

    def test_private_payload_and_stop_close_without_response(self):
        for token in (b"STOP", b"LIST_SESSIONS synthetic private title",
                      b'{"permissionGranted":true}'):
            with self.subTest(token=token):
                channel, process, _, _, _ = self.launch()
                channel.sendall(token)
                self.assertEqual(channel.recv(4096), b"")
                self.finish(process, 2)

    def test_no_default_activation(self):
        result = subprocess.run(
            [PYTHON, "-I", "-B", str(HOST)],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=5,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual((result.stdout, result.stderr), (b"", b""))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(2)
    EXPECTED_SHA = sys.argv.pop()
    unittest.main(verbosity=2)
