#!/usr/bin/env python3
"""Real connected Linux TimeW peer image/LSM candidate, never SwayPX admission."""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    if spec is None or spec.loader is None:
        raise AssertionError("EXACT_C3E_TEST_SOURCE_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

P = load("c3e_real_image_candidate",
         "services/connections/ConnectionsTimeWNativePeerImageCandidate.py")
E = load("c3e_original_peer_fixture",
         "tests/connections/test_connections_c3e_timew_native_external_sender.py")


@unittest.skipUnless(sys.platform == "linux", "real Linux peer image only")
class RealOriginalPeerImageTests(unittest.TestCase):

    def test_01_independent_child_process_image_real_kernel_observed(self):
        with E.independent_linux_packet_sender(stay_alive=True) as (reader, child):
            result = P.observe_untrusted_peer_process_image(reader)
            self.assertEqual(result["kernelPeerPidObserved"], child)
            self.assertNotEqual(child, os.getpid())
            self.assertEqual(result["kernelPeerUidObserved"], os.getuid())
            self.assertEqual(result["kernelPeerGidObserved"], os.getgid())
            self.assertGreater(result["kernelProcessStartTicksObserved"], 0)
            self.assertTrue(result["kernelCgroupObservedUntrusted"].startswith("/"))
            self.assertTrue(result["kernelLsmObservedUntrusted"])
            self.assertEqual(result["executableSha256ObservedUntrusted"],
                hashlib.sha256(Path("/proc/self/exe").read_bytes()).hexdigest())
            self.assertGreater(result["executableInodeObservedUntrusted"], 0)
            self.assertTrue(result["sourceMetadataIsNotPacketBound"])
            self.assertEqual(result["safeActions"], [])
            for key in P.NO_AUTHORITY:
                self.assertIs(result[key], False, key)

    def test_02_exited_exact_socket_peer_refused_no_pid_reuse(self):
        with E.independent_linux_packet_sender(stay_alive=False) as (reader, _):
            with self.assertRaises(P.PeerImageHold):
                P.observe_untrusted_peer_process_image(reader)

    def test_03_missing_kernel_original_pidfd_holds(self):
        with E.independent_linux_packet_sender(stay_alive=True) as (reader, _):
            with patch.object(P, "SO_PEERPIDFD", 0x7fffffff):
                with self.assertRaisesRegex(
                        P.PeerImageHold, "KERNEL_OR_PROC_UNAVAILABLE"):
                    P.observe_untrusted_peer_process_image(reader)

    def test_04_no_timeout_and_wrong_socket_type_refused(self):
        a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.addCleanup(a.close)
        self.addCleanup(b.close)
        with self.assertRaisesRegex(P.PeerImageHold,
                                    "BOUNDED_CONNECTED_UNIX_SEQPACKET_REQUIRED"):
            P.observe_untrusted_peer_process_image(a)
        a.settimeout(0.4)
        with self.assertRaisesRegex(P.PeerImageHold,
                                    "BOUNDED_CONNECTED_UNIX_SEQPACKET_REQUIRED"):
            P.observe_untrusted_peer_process_image("not a kernel socket")
        stream, other = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(stream.close)
        self.addCleanup(other.close)
        stream.settimeout(0.2)
        with self.assertRaises(P.PeerImageHold):
            P.observe_untrusted_peer_process_image(stream)

    def test_05_start_ticks_change_mid_snapshot_is_hold(self):
        with E.independent_linux_packet_sender(stay_alive=True) as (reader, _):
            with patch.object(P, "_start_ticks", side_effect=[111, 112]):
                with self.assertRaisesRegex(P.PeerImageHold,
                                            "PROCESS_CHANGED_DURING_OBSERVATION"):
                    P.observe_untrusted_peer_process_image(reader)

    def test_06_cgroup_change_mid_snapshot_is_hold(self):
        with E.independent_linux_packet_sender(stay_alive=True) as (reader, _):
            with patch.object(P, "_cgroup", side_effect=["/first", "/other"]):
                with self.assertRaisesRegex(P.PeerImageHold,
                                            "PROCESS_CHANGED_DURING_OBSERVATION"):
                    P.observe_untrusted_peer_process_image(reader)

    def test_07_exec_inode_drift_refused(self):
        with E.independent_linux_packet_sender(stay_alive=True) as (reader, _):
            with patch.object(P, "_image",
                              return_value=("a" * 64, (0, 0, 0, 0, 0))):
                with self.assertRaisesRegex(P.PeerImageHold,
                                            "PROCESS_EXECUTABLE_CHANGED"):
                    P.observe_untrusted_peer_process_image(reader)

    def test_08_an_observed_image_is_never_trusted_selection(self):
        a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.addCleanup(a.close)
        self.addCleanup(b.close)
        a.settimeout(0.4)
        b.send(b'{"timewSelection":true,"releaseEnrolled":true,"C5":"SPENT"}')
        observed = P.observe_untrusted_peer_process_image(a)
        self.assertFalse(observed["compositorSelectionAuthenticated"])
        self.assertFalse(observed["c5HumanConsentAndSpendVerified"])
        self.assertFalse(observed["installedSwayPXReleaseEnrolled"])
        self.assertFalse(observed["sourceEvidenceTrusted"])
        self.assertFalse(observed["nativeGeometryAllowed"])
        self.assertFalse(observed["timewRestoreAllowed"])
        self.assertFalse(observed["productionAuthority"])


if __name__ == "__main__":
    unittest.main()
