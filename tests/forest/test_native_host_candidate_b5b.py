"""B5b native process/FD tests, no installation, private data or Ollama."""
import array
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "forest"
sys.path.insert(0, str(SCRIPTS))
import native_host_candidate_b5b as host


@unittest.skipUnless(sys.platform.startswith("linux"), "Linux socket contract")
class NativeHostCandidateTests(unittest.TestCase):
    def launch(self, endpoint=None):
        parent, child = (socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
                         if endpoint is None else endpoint)
        self.addCleanup(parent.close)
        self.addCleanup(child.close)
        parent.settimeout(5)
        fd = child.fileno()
        inode = os.fstat(fd).st_ino
        proc = subprocess.Popen(
            [sys.executable, "-I", "-B", str(SCRIPTS /
             "native_host_candidate_b5b.py"), "--disposable-test-fd", str(fd)],
            pass_fds=(fd,), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.addCleanup(self.reap, proc)
        child.close()
        return parent, proc, fd, inode

    @staticmethod
    def reap(proc):
        if proc.poll() is None:
            proc.kill()
        proc.communicate(timeout=5)

    def finish(self, proc, expected):
        out, err = proc.communicate(timeout=5)
        self.assertEqual(proc.returncode, expected)
        self.assertEqual((out, err), (b"", b""))

    def read_closed(self, channel):
        try:
            self.assertEqual(channel.recv(4096), b"")
        except ConnectionResetError:
            # Unread queued control packets can cause reset on close.
            pass

    def assert_hold(self, wire):
        self.assertEqual(wire, host._PUBLIC_HOLD)
        report = json.loads(wire)
        self.assertEqual(report["status"], "UNKNOWN_HOLD")
        self.assertEqual(report["privateBytesSubmitted"], 0)
        for field in ("sourceAuthenticated", "recipientAuthenticated",
                      "permissionGranted", "productionAuthority",
                      "revocationFencedAck"):
            self.assertIs(report[field], False)
        self.assertEqual(report["safeActions"], [])

    def test_real_child_owns_exact_socket_inode_and_emits_public_hold(self):
        channel, proc, fd, inode = self.launch()
        self.assertNotEqual(proc.pid, os.getpid())
        self.assertEqual(os.readlink(f"/proc/{proc.pid}/fd/{fd}"),
                         f"socket:[{inode}]")
        channel.sendall(b"STATUS")
        self.assert_hold(channel.recv(4096))
        self.read_closed(channel)
        self.finish(proc, 0)

    def test_each_protected_control_refuses_with_identical_public_hold(self):
        for token in sorted(host._CONTROL - {b"STATUS"}):
            with self.subTest(token=token):
                channel, proc, _, _ = self.launch()
                channel.sendall(token)
                self.assert_hold(channel.recv(4096))
                self.read_closed(channel)
                self.finish(proc, 0)

    def test_stop_before_submission_closes_without_ack(self):
        channel, proc, _, _ = self.launch()
        channel.sendall(b"STOP")
        self.read_closed(channel)
        self.finish(proc, 2)

    def test_unknown_or_private_payload_never_echoed(self):
        for packet in (b"LIST_SESSIONS private-title", b'{"grant":true}',
                       b"\xff\x00", b"x" * 1024):
            with self.subTest(packet=packet):
                channel, proc, _, _ = self.launch()
                channel.sendall(packet)
                self.read_closed(channel)
                self.finish(proc, 2)

    def test_second_control_cannot_trigger_second_submission(self):
        channel, proc, _, _ = self.launch()
        channel.sendall(b"STATUS")
        self.assert_hold(channel.recv(4096))
        self.finish(proc, 0)
        # The first exchange has ended. A later control cannot reopen it.
        with self.assertRaises((BrokenPipeError, ConnectionResetError)):
            channel.sendall(b"LIST_SESSIONS")
        self.read_closed(channel)

    def test_pipelined_controls_at_most_one_public_packet(self):
        channel, proc, _, _ = self.launch()
        channel.sendall(b"STATUS")
        try:
            channel.sendall(b"LIST_SESSIONS")
        except (BrokenPipeError, ConnectionResetError):
            pass
        # Closing with unread SEQPACKET input can reset the peer and
        # discard its first response. Receipt is not guaranteed by send.
        frames = []
        try:
            while True:
                packet = channel.recv(4096)
                if not packet:
                    break
                frames.append(packet)
                self.assertLessEqual(len(frames), 1)
                self.assert_hold(packet)
        except ConnectionResetError:
            pass
        self.finish(proc, 0)

    def test_empty_packet_refuses(self):
        channel, proc, _, _ = self.launch()
        channel.send(b"")
        self.read_closed(channel)
        self.finish(proc, 2)

    def test_peer_disconnect_refuses_without_retry(self):
        channel, proc, _, _ = self.launch()
        channel.close()
        self.finish(proc, 2)

    def test_idle_timeout_is_bounded_and_no_output(self):
        channel, proc, _, _ = self.launch()
        self.read_closed(channel)
        self.finish(proc, 2)

    def test_wrong_socket_type_refused(self):
        channel, proc, _, _ = self.launch(
            socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM))
        self.read_closed(channel)
        self.finish(proc, 2)

    def test_descriptor_transfer_refuses_even_valid_control(self):
        channel, proc, _, _ = self.launch()
        read_fd, write_fd = os.pipe()
        try:
            channel.sendmsg([b"STATUS"], [(socket.SOL_SOCKET,
                 socket.SCM_RIGHTS, array.array("i", [read_fd]))])
            self.read_closed(channel)
            self.finish(proc, 2)
        finally:
            os.close(read_fd)
            os.close(write_fd)

    def test_empty_and_truncated_packets_close_received_rights_before_return(self):
        # Exercise the real recvmsg helper inside the test process so exit
        # cannot hide a descriptor leak. All payloads and FDs are disposable.
        for packet in (b"", b"x" * 1024, b"STATUS"):
            with self.subTest(packet=packet):
                left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
                with left, right:
                    read_fd, write_fd = os.pipe()
                    try:
                        before = len(os.listdir("/proc/self/fd"))
                        # Also exercises ancillary truncation, not just payload
                        # truncation. Linux closes undisclosed excess rights.
                        left.sendmsg([packet], [(socket.SOL_SOCKET, socket.SCM_RIGHTS,
                            array.array("i", [read_fd] * 32))])
                        self.assertIsNone(host._receive_control(right))
                        self.assertEqual(len(os.listdir("/proc/self/fd")), before)
                    finally:
                        os.close(read_fd)
                        os.close(write_fd)

    def test_no_default_cli_activation(self):
        proc = subprocess.run(
            [sys.executable, "-I", "-B", str(SCRIPTS /
             "native_host_candidate_b5b.py")],
            capture_output=True, timeout=5,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertEqual((proc.stdout, proc.stderr), (b"", b""))


if __name__ == "__main__":
    unittest.main()
