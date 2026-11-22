#!/usr/bin/env python3
"""C3e TimeW: real distinct Linux sender and hostile ancillary/timeout CI tests.

All producers are disposable test children. None is a signed/enrolled SwayPX
compositor, real selection source, active-seat authority or C5 issuer.
"""
from __future__ import annotations

import array
from contextlib import contextmanager
import hashlib
import importlib.util
import os
from pathlib import Path
import socket
import sys
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "c3e_timew_observer_external",
    ROOT / "services/connections/ConnectionsTimeWNativePacketObservation.py")
if spec is None or spec.loader is None:
    raise RuntimeError("CONNECTIONS_NATIVE_OBSERVER_MISSING")
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)

FAKE_PACKET = b'{"swaypxSelected":true,"c5Spend":"SPENT","productionAuthority":true}'


@contextmanager
def independent_linux_packet_sender(*, stay_alive: bool):
    """Child connects its *own* Unix socket: not parent's inherited socketpair."""
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    listener.settimeout(1.5)
    # Linux abstract address, no filesystem path/service and no installed socket.
    address = "\0postapollo-c3e-timew-ci-" + uuid.uuid4().hex
    listener.bind(address)
    listener.listen(1)
    release_read, release_write = os.pipe()
    child = os.fork()
    if child == 0:
        try:
            os.close(release_write)
            listener.close()
            sender = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
            sender.settimeout(1.0)
            sender.connect(address)
            sender.send(FAKE_PACKET)
            if stay_alive:
                os.read(release_read, 1)
            sender.close()
            os.close(release_read)
            os._exit(0)
        except BaseException:
            os._exit(9)

    os.close(release_read)
    accepted = None
    waited = False
    try:
        accepted, _ = listener.accept()
        accepted.settimeout(0.5)
        accepted.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        if not stay_alive:
            waited_pid, status = os.waitpid(child, 0)
            waited = True
            if waited_pid != child or status != 0:
                raise AssertionError("DISPOSABLE_CHILD_FAILED")
        yield accepted, child
    finally:
        if accepted is not None:
            accepted.close()
        listener.close()
        try:
            os.write(release_write, b"x")
        except BrokenPipeError:
            pass
        os.close(release_write)
        if not waited:
            waited_pid, status = os.waitpid(child, 0)
            if waited_pid != child or status != 0:
                raise AssertionError("DISPOSABLE_CHILD_FAILED")


@unittest.skipUnless(sys.platform == "linux", "requires genuine Linux socket API")
class C3eTimeWExternalPeerTests(unittest.TestCase):

    def test_01_real_distinct_process_sender_observed_but_untrusted(self):
        with independent_linux_packet_sender(stay_alive=True) as (receiver, child):
            observed = P.inspect_one_untrusted_packet(receiver)
            self.assertNotEqual(child, os.getpid())
            self.assertEqual(observed["kernelPeerPidObserved"], child)
            self.assertEqual(observed["kernelPeerUidObserved"], os.getuid())
            self.assertEqual(observed["packetSha256Untrusted"],
                             hashlib.sha256(FAKE_PACKET).hexdigest())
            self.assertTrue(observed["exactPeerPidfdAliveAtRead"])
            self.assertEqual(observed["safeActions"], [])
            self.assertTrue(observed["rawPacketUntrusted"])
            for flag in P.NO_AUTHORITY:
                self.assertIs(observed[flag], False, flag)

    def test_02_exited_original_separate_sender_is_not_lifetime_proof(self):
        with independent_linux_packet_sender(stay_alive=False) as (receiver, child):
            self.assertNotEqual(child, os.getpid())
            with self.assertRaises(P.ObservationHold):
                P.inspect_one_untrusted_packet(receiver)

    def test_03_idle_packet_timeout_holds_without_blocking_indefinitely(self):
        receiver, sender = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.addCleanup(receiver.close)
        self.addCleanup(sender.close)
        receiver.settimeout(0.05)
        receiver.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        # Live same-process peer but no packet. A caller cannot turn silence
        # into an authenticated source record by waiting indefinitely.
        with self.assertRaisesRegex(P.ObservationHold,
                                    "KERNEL_PEER_OBSERVATION_UNAVAILABLE"):
            P.inspect_one_untrusted_packet(receiver)

    def test_04_actual_ancillary_truncation_from_scm_rights_is_refused(self):
        receiver, sender = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.addCleanup(receiver.close)
        self.addCleanup(sender.close)
        receiver.settimeout(0.5)
        receiver.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        # The observer has room for one credential cmsg, not credentials
        # PLUS SCM_RIGHTS. Linux sets MSG_CTRUNC; this must never be read
        # as a valid native selected-surface proof.
        source_fd = os.open("/dev/null", os.O_RDONLY)
        try:
            sender.sendmsg([FAKE_PACKET], [
                (socket.SOL_SOCKET, socket.SCM_RIGHTS,
                 array.array("i", [source_fd]))])
        finally:
            os.close(source_fd)
        with self.assertRaisesRegex(P.ObservationHold,
                                    "PACKET_TRUNCATED_OVERSIZED_OR_EMPTY"):
            P.inspect_one_untrusted_packet(receiver)

    def test_05_external_packet_does_not_upgrade_native_admission(self):
        with independent_linux_packet_sender(stay_alive=True) as (receiver, _):
            self.assertFalse(P.inspect_one_untrusted_packet(
                receiver)["productionAuthority"])
            with self.assertRaisesRegex(P.ObservationHold,
                                        "PROTECTED_SWAYPX_SOURCE_AND_C5_NOT_ENROLLED"):
                P.run_native_timew_source_admission(
                    packet_digest="fake",
                    independently_enrolled_compositor=True,
                    c5_spend_claim="SPENT")


if __name__ == "__main__":
    unittest.main()
