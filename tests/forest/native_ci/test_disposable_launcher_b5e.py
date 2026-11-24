"""B5e real installed candidate launcher tests; fixed public denial only."""
import fcntl
import json
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

# The verification container stages this exact CI module beside this test.
# Python isolated mode excludes the script directory from sys.path.
import sys
sys.path.insert(0, "/ci-b5e")
import disposable_launcher_b5e as launcher

EXPECTED = {
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


class NativeLauncherTests(unittest.TestCase):
    def assert_hold(self, peer):
        self.assertEqual(json.loads(peer.recv(4096)), EXPECTED)
        self.assertEqual(peer.recv(4096), b"")

    def test_exact_installed_child_and_single_channel(self):
        with launcher.launch_disposable_host() as (peer, proc, fd, inode):
            root = Path("/proc") / str(proc.pid)
            self.assertEqual(os.readlink(root / "exe"),
                             os.path.realpath(launcher.PYTHON))
            self.assertEqual((root / "cmdline").read_bytes().split(b"\0")[:-1],
                             [x.encode() for x in (launcher.PYTHON, "-I", "-B",
                               launcher.HOST, "--disposable-test-fd", str(fd))])
            self.assertEqual(os.readlink(root / "fd" / str(fd)),
                             f"socket:[{inode}]")
            self.assertNotEqual(os.fstat(peer.fileno()).st_ino, inode)
            for std in range(3):
                self.assertEqual(os.readlink(root / "fd" / str(std)), "/dev/null")
            peer.sendall(b"STATUS")
            self.assert_hold(peer)
        self.assertEqual(proc.returncode, 0)

    def test_inheritable_file_pipe_socket_and_memfd_are_excluded(self):
        # Exercise deliberately inheritable unrelated descriptors, not merely
        # Python's default non-inheritable descriptors.
        with tempfile.TemporaryFile() as file, socket.socket() as unrelated:
            read_fd, write_fd = os.pipe()
            memfd = os.memfd_create("forest-ci-synthetic")
            originals = (file.fileno(), unrelated.fileno(), read_fd,
                         write_fd, memfd)
            sentinels = []
            try:
                for original in originals:
                    fd = fcntl.fcntl(original, fcntl.F_DUPFD, 100)
                    os.set_inheritable(fd, True)
                    sentinels.append(fd)
                    self.assertTrue(os.get_inheritable(fd))
                with launcher.launch_disposable_host() as (peer, proc, fd, inode):
                    fd_dir = Path("/proc") / str(proc.pid) / "fd"
                    self.assertNotIn(fd, sentinels)
                    for sentinel in sentinels:
                        # readlink, rather than exists(), detects broken symlinks.
                        with self.assertRaises(FileNotFoundError):
                            os.readlink(fd_dir / str(sentinel))
                        os.fstat(sentinel)  # parent descriptor remains open
                    self.assertEqual(os.readlink(fd_dir / str(fd)),
                                     f"socket:[{inode}]")
                    peer.sendall(b"LIST_SESSIONS")
                    self.assert_hold(peer)
                self.assertEqual(proc.returncode, 0)
            finally:
                for fd in sentinels + [read_fd, write_fd, memfd]:
                    os.close(fd)

    def test_parent_environment_is_not_inherited(self):
        with patch.dict(os.environ, {"FOREST_SYNTHETIC_SECRET": "CI-only",
                                     "PYTHONPATH": "/unexpected",
                                     "OLLAMA_HOST": "http://invalid"}):
            with launcher.launch_disposable_host() as (peer, proc, _, _):
                observed = (Path("/proc") / str(proc.pid) / "environ").read_bytes()
                entries = dict(entry.split(b"=", 1) for entry in
                               observed.split(b"\0") if entry)
                self.assertEqual(entries, {
                    b"PATH": b"/usr/bin:/bin", b"HOME": b"/nonexistent",
                    b"LC_ALL": b"C"})
                peer.sendall(b"STATUS")
                self.assert_hold(peer)

    def test_protected_operations_remain_public_hold(self):
        for token in (b"LIST_SESSIONS", b"DISCLOSE_SESSION_TITLES",
                      b"READ_SESSION", b"GENERATE", b"DISCLOSE_PROVISIONAL",
                      b"COMMIT_GENERATE", b"SEND", b"VOICE"):
            with self.subTest(token=token):
                with launcher.launch_disposable_host() as (peer, proc, _, _):
                    peer.sendall(token)
                    self.assert_hold(peer)
                self.assertEqual(proc.returncode, 0)

    def test_caller_cannot_choose_executable_or_descriptor(self):
        for kwargs in ({"executable": "/bin/sh"}, {"fd": 4}, {"uid": 0},
                       {"env": {"SECRET": "synthetic"}}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(TypeError):
                    with launcher.launch_disposable_host(**kwargs):
                        self.fail("unexpected launch")

    def test_missing_ci_guard_refuses_before_spawn(self):
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}):
            with patch.object(launcher.subprocess, "Popen") as spawn:
                with self.assertRaisesRegex(RuntimeError, "DISPOSABLE_NONROOT"):
                    with launcher.launch_disposable_host():
                        self.fail("unexpected launch")
                spawn.assert_not_called()

    def test_context_exit_closes_channel_and_reaps_child(self):
        with launcher.launch_disposable_host() as (peer, proc, _, _):
            pid = proc.pid
        self.assertEqual(peer.fileno(), -1)
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(Path("/proc", str(pid)).exists())

    def test_exception_also_closes_and_reaps(self):
        with self.assertRaisesRegex(ValueError, "synthetic failure"):
            with launcher.launch_disposable_host() as (peer, proc, _, _):
                raise ValueError("synthetic failure")
        self.assertEqual(peer.fileno(), -1)
        self.assertIsNotNone(proc.returncode)

    def test_no_second_send_after_single_exchange(self):
        with launcher.launch_disposable_host() as (peer, proc, _, _):
            peer.sendall(b"STATUS")
            self.assert_hold(peer)
            self.assertEqual(proc.wait(timeout=5), 0)
            with self.assertRaises((BrokenPipeError, ConnectionResetError)):
                peer.sendall(b"LIST_SESSIONS")

    def test_spawn_failure_closes_both_socket_endpoints(self):
        pair = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        try:
            with patch.object(launcher.socket, "socketpair", return_value=pair):
                with patch.object(launcher.subprocess, "Popen",
                                  side_effect=OSError("synthetic spawn failure")):
                    with self.assertRaises(OSError):
                        with launcher.launch_disposable_host():
                            self.fail("unexpected launch")
            self.assertEqual([s.fileno() for s in pair], [-1, -1])
        finally:
            for endpoint in pair:
                endpoint.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
