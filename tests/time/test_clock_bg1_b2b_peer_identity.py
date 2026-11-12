"""BG1-B2B1: real Linux SO_PEERPIDFD socket-peers and fail-closed role boundary.

All processes and files are disposable. This does not touch the user's Clock.
"""
from __future__ import annotations
from contextlib import ExitStack
import importlib.util
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
PEERS = ROOT / "services/time/AlarmPeerIdentity.py"
BROKER = ROOT / "services/time/AlarmOwnershipBroker.py"
LIVE = ROOT / "services/time/AlarmManagerService.qml"
B0 = ROOT / "services/time/AlarmBackgroundObserver.py"
spec = importlib.util.spec_from_file_location("clock_bg1_peer_identity", PEERS)
identity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(identity)


class PeerKernelIdentityTests(unittest.TestCase):
    def assert_denied(self, callback, reason):
        with self.assertRaises(identity.Refused) as raised:
            callback()
        self.assertEqual(str(raised.exception), reason)

    def test_kernel_socketpair_pins_exact_process_and_closes_fd(self):
        with ExitStack() as sockets:
            a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
            sockets.enter_context(a)
            sockets.enter_context(b)
            witness = identity.capture(a, sys.executable)
            fd = witness["pidfd"]
            try:
                self.assertEqual(witness["pid"], os.getpid())
                self.assertEqual(witness["uid"], os.getuid())
                self.assertEqual(witness["gid"], os.getgid())
                self.assertFalse(os.get_inheritable(fd))
                self.assertTrue(identity.verify(a, witness, sys.executable))
                self.assert_denied(
                    lambda: identity.verify(a, witness, "/bin/not-the-peer"),
                    "UNEXPECTED_SYNTHETIC_PEER_EXE")
            finally:
                identity.close(witness)
            self.assertNotIn("pidfd", witness)
            with self.assertRaises(OSError):
                os.fstat(fd)
            identity.close(witness)  # idempotent cleanup

    def test_pidfd_required_no_fallback_to_pid_lookup(self):
        with ExitStack() as sockets:
            a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
            sockets.enter_context(a)
            sockets.enter_context(b)
            class NoPidfd:
                def getsockopt(self, level, option, size):
                    if option == identity.SO_PEERPIDFD:
                        raise OSError("unsupported pidfd")
                    return a.getsockopt(level, option, size)
            self.assert_denied(
                lambda: identity.capture(NoPidfd(), sys.executable),
                "SO_PEERPIDFD_UNAVAILABLE")

    def _accepted_child(self, script):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        address = str(Path(temp.name) / "peer.sock")
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(server.close)
        server.bind(address)
        server.listen(1)
        server.settimeout(6)
        child = subprocess.Popen(
            [sys.executable, "-I", "-B", "-c", script, address],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=False)
        self.addCleanup(self._reap, child)
        accepted, _ = server.accept()
        accepted.settimeout(3)
        self.addCleanup(accepted.close)
        self.assertEqual(accepted.recv(1), b"R")
        witness = identity.capture(accepted, sys.executable)
        self.addCleanup(identity.close, witness)
        self.assertEqual(witness["pid"], child.pid)
        return child, accepted, witness

    @staticmethod
    def _reap(child):
        if child.poll() is None:
            child.terminate()
        try:
            child.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            child.kill()
            child.communicate(timeout=3)

    def test_real_connected_peer_exit_invalidates_pidfd(self):
        script = (
            "import socket,sys,time\n"
            "s=socket.socket(socket.AF_UNIX)\n"
            "s.connect(sys.argv[1]);s.sendall(b'R');time.sleep(30)\n")
        child, connection, witness = self._accepted_child(script)
        self.assertTrue(identity.verify(connection, witness, sys.executable))
        child.terminate()
        child.wait(timeout=3)
        self.assert_denied(
            lambda: identity.verify(connection, witness, sys.executable),
            "PEER_PROCESS_EXITED")

    def test_real_same_pid_exec_replacement_refused(self):
        sleeper = shutil.which("sleep")
        self.assertIsNotNone(sleeper)
        script = (
            "import os,socket,sys\n"
            "s=socket.socket(socket.AF_UNIX)\n"
            "s.connect(sys.argv[1]);s.sendall(b'R')\n"
            "sys.stdin.buffer.read(1)\n"
            "os.execv(" + repr(sleeper) + ",[" + repr(sleeper) + ",'5'])\n")
        child, connection, witness = self._accepted_child(script)
        self.assertTrue(identity.verify(connection, witness, sys.executable))
        child.stdin.write(b"X")
        child.stdin.flush()
        observed = []
        for _ in range(120):
            try:
                identity.verify(connection, witness, sys.executable)
            except identity.Refused as exc:
                observed.append(str(exc))
                break
            time.sleep(0.02)
        self.assertEqual(observed, ["UNEXPECTED_SYNTHETIC_PEER_EXE"])
        self.assertEqual(child.poll(), None, "Peer must still be alive after exec")

    def test_exact_peer_witness_shape_fails_closed(self):
        with ExitStack() as sockets:
            a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
            sockets.enter_context(a)
            sockets.enter_context(b)
            witness = identity.capture(a, sys.executable)
            try:
                altered = dict(witness, ticks=witness["ticks"] + 1)
                self.assert_denied(
                    lambda: identity.verify(a, altered, sys.executable),
                    "PEER_PROCESS_CHANGED")
                altered = dict(witness, uid=witness["uid"] + 1)
                self.assert_denied(
                    lambda: identity.verify(a, altered, sys.executable),
                    "PEER_CREDENTIALS_CHANGED")
                self.assert_denied(
                    lambda: identity.verify(a, {"pid": os.getpid()},
                                            sys.executable),
                    "PEER_WITNESS_INVALID")
            finally:
                identity.close(witness)

    def test_synthetic_broker_only_no_prod_role_licensing_or_live_tissue(self):
        src = BROKER.read_text(encoding="utf-8")
        peer = PEERS.read_text(encoding="utf-8")
        live = LIVE.read_text(encoding="utf-8")
        b0 = B0.read_text(encoding="utf-8")
        self.assertIn('roleAuthenticated": False', src)
        self.assertIn('_peer_identity.verify(self.request, self.peer', src)
        self.assertIn('_peer_identity.close(self.peer)', src)
        self.assertIn("_socket_peer_pidfd(connection)", peer)
        self.assertIn("SO_PEERPIDFD = 77", peer)
        self.assertIn('"--serve-synthetic"', src)
        self.assertNotIn('"--serve-production"', src)
        self.assertNotIn("AlarmOwnershipBroker", live)
        self.assertNotIn("AlarmOwnershipBroker", b0)
        for forbidden in ["notify-send", "SoundEffect", "systemctl"]:
            self.assertNotIn(forbidden, src)
            self.assertNotIn(forbidden, peer)


if __name__ == "__main__":
    unittest.main()
