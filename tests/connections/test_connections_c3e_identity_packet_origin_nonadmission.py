#!/usr/bin/env python3
"""DOC 1: Linux per-packet identity cannot promote a C3e local diagnostic."""
from __future__ import annotations

import array
import hashlib
import importlib.util
import os
from pathlib import Path
import socket
import struct
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "tests/connections/c3e_release_trust"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3E_PACKET_TEST_ORIGINAL_SOURCE_REQUIRED")
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


M = _load("c3e_packet_identity_under_test",
          SRC / "C3eIdentityPacketOriginNonAdmissionCI.py")
F = _load("c3e_packet_original_ledger_fixture",
          ROOT / "tests/connections/test_connections_c3e_local_development_history_ledger.py")


class IdentityPacketOriginStillNotAuthority(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (sys.platform != "linux" or os.geteuid() != 0
                or os.environ.get("GITHUB_ACTIONS") != "true"
                or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
            raise RuntimeError("C3E_IDENTITY_PACKET_DISPOSABLE_HOSTED_ROOT_ONLY")

    def setUp(self):
        self.fixture = F.LocalHistoryLedgerTests(
            "test_01_true_signed_continuity_advances_only_dev_head")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.local = M.P.S.TrustBoundary(
            required_mode=M.P.S.LOCAL_DEVELOPMENT,
            local_adapter=M.P.S.LocalSQLiteTestAdapter(
                M.P.S.L.DevelopmentLedger(self.fixture.work)))
        self.protected = M.P.S.TrustBoundary(
            required_mode=M.P.S.PROTECTED_REQUIRED)
        self.req = {"schema": M.P.SCHEMA, "op": "SNAPSHOT",
                    "requestNonce": "c3" * 16}

    def frame(self, request=None):
        return M.P.frame_ci_only(self.req if request is None else request)

    def pair(self, *, kind=socket.SOCK_SEQPACKET, passcred=True):
        receiver, sender = socket.socketpair(socket.AF_UNIX, kind)
        receiver.settimeout(0.5)
        if passcred:
            receiver.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        self.addCleanup(receiver.close)
        self.addCleanup(sender.close)
        return receiver, sender

    def inspect(self, *, expected=None, actual=None, boundary=None,
                kind=socket.SOCK_SEQPACKET, passcred=True):
        frame = self.frame() if expected is None else expected
        receiver, sender = self.pair(kind=kind, passcred=passcred)
        sender.sendall(frame if actual is None else actual)
        return M.inspect_ci_only(
            receiver, expected_request_frame=frame,
            boundary=self.local if boundary is None else boundary)

    def denied(self, result):
        self.assertEqual(result["schema"], M.SCHEMA)
        self.assertEqual(result["status"], M.STATUS)
        self.assertEqual(result["next"],
                         "HOLD_NO_PROTECTED_IDENTITY_OR_AUTO_RETRY")
        self.assertEqual(set(result), {
            "schema", "status", "packetSha256LocalComparisonOnly",
            "kernelSenderPidObservedOnly", "localReadOnlyOperation",
            "originalDiagnosticStatus", "next", *M.DENIED,
        })
        for name in M.DENIED:
            self.assertIs(result[name], False, name)

    def test_01_exact_local_readonly_snapshot_still_untrusted(self):
        out = self.inspect()
        self.assertEqual(out["localReadOnlyOperation"], "SNAPSHOT")
        self.assertEqual(out["originalDiagnosticStatus"], M.P.S.STATUS_LOCAL)
        self.assertEqual(out["kernelSenderPidObservedOnly"], os.getpid())
        self.assertEqual(out["packetSha256LocalComparisonOnly"],
                         hashlib.sha256(self.frame()).hexdigest())
        self.denied(out)

    def test_02_protected_status_is_hold_even_with_actual_packet_identity(self):
        frame = self.frame({**self.req, "op": "CUSTODIAN_STATUS"})
        out = self.inspect(expected=frame, boundary=self.protected)
        self.assertEqual(out["originalDiagnosticStatus"],
                         M.P.S.STATUS_HOLD)
        self.denied(out)

    def test_03_original_issued_challenge_observation_not_settlement(self):
        frame = self.frame({**self.req, "op": "OUTCOME",
                            "challengeHex": self.fixture.challenge.hex()})
        out = self.inspect(expected=frame)
        self.assertEqual(out["localReadOnlyOperation"], "OUTCOME")
        self.denied(out)

    def test_04_original_consumed_development_challenge_still_not_grant(self):
        self.fixture.commit()
        frame = self.frame({**self.req, "op": "OUTCOME",
                            "challengeHex": self.fixture.challenge.hex()})
        self.denied(self.inspect(expected=frame))

    def test_05_protected_snapshot_cannot_fallback_to_local(self):
        with self.assertRaisesRegex(M.Refused, "READONLY_ROUTE_REFUSED"):
            self.inspect(boundary=self.protected)

    def test_06_unknown_identity_command_cannot_become_readonly_diagnostic(self):
        frame = self.frame({**self.req, "op": "BEGIN_SIGNIN"})
        with self.assertRaisesRegex(M.Refused, "READONLY_ROUTE_REFUSED"):
            self.inspect(expected=frame)

    def test_07_commit_history_command_refused(self):
        frame = self.frame({**self.req, "op": "COMMIT_SIGNED_HISTORY"})
        with self.assertRaisesRegex(M.Refused, "READONLY_ROUTE_REFUSED"):
            self.inspect(expected=frame)

    def test_08_extra_production_grant_field_refused(self):
        frame = self.frame({**self.req, "productionAuthority": True})
        with self.assertRaisesRegex(M.Refused, "READONLY_ROUTE_REFUSED"):
            self.inspect(expected=frame)

    def test_09_unknown_outcome_challenge_refused(self):
        frame = self.frame({**self.req, "op": "OUTCOME",
                            "challengeHex": "ff" * 32})
        with self.assertRaisesRegex(M.Refused, "READONLY_ROUTE_REFUSED"):
            self.inspect(expected=frame)

    def test_10_actual_packet_different_from_expected_frame_refused(self):
        actual = self.frame({**self.req, "requestNonce": "a1" * 16})
        with self.assertRaisesRegex(M.Refused, "PACKET_OR_AUTHORITY_MISMATCH"):
            self.inspect(actual=actual)

    def test_11_timew_packet_cannot_be_swapped_for_identity_request(self):
        with self.assertRaisesRegex(M.Refused, "PACKET_OR_AUTHORITY_MISMATCH"):
            self.inspect(actual=b'{"timewGrant":"SPENT"}')

    def test_12_wrong_declared_frame_length_refused_before_route(self):
        good = self.frame()
        wrong = struct.pack(">I", len(good)) + good[4:]
        receiver, sender = self.pair()
        sender.sendall(good)
        with self.assertRaisesRegex(M.Refused, "EXACT_FRAMING"):
            M.inspect_ci_only(
                receiver, expected_request_frame=wrong, boundary=self.local)

    def test_13_duplicate_json_operation_refused_before_route(self):
        raw = (b'{"schema":"' + M.P.SCHEMA.encode() +
               b'","op":"SNAPSHOT","op":"BEGIN_SIGNIN",'
               b'"requestNonce":"' + b"c3" * 16 + b'"}')
        frame = struct.pack(">I", len(raw)) + raw
        with self.assertRaisesRegex(M.Refused, "REQUEST_ENCODING_REFUSED"):
            self.inspect(expected=frame)

    def test_14_inherited_socket_fd_sender_is_not_original_peer(self):
        receiver, sender = self.pair()
        child = os.fork()
        if child == 0:
            try:
                receiver.close()
                sender.sendall(self.frame())
                os._exit(0)
            except BaseException:
                os._exit(91)
        sender.close()
        try:
            with self.assertRaisesRegex(
                M.Refused, "KERNEL_PROVENANCE_UNKNOWN_HOLD"
            ):
                M.inspect_ci_only(
                    receiver, expected_request_frame=self.frame(),
                    boundary=self.local)
        finally:
            pid, status = os.waitpid(child, 0)
            self.assertEqual(pid, child)
            self.assertEqual(status, 0)

    def test_15_stream_socket_has_no_packet_provenance(self):
        with self.assertRaisesRegex(M.Refused,
                                    "KERNEL_PROVENANCE_UNKNOWN_HOLD"):
            self.inspect(kind=socket.SOCK_STREAM)

    def test_16_missing_per_packet_credentials_holds(self):
        with self.assertRaisesRegex(M.Refused,
                                    "KERNEL_PROVENANCE_UNKNOWN_HOLD"):
            self.inspect(passcred=False)

    def test_17_peer_pidfd_unavailable_holds(self):
        with mock.patch.object(M.K, "SO_PEERPIDFD", 0x7fffffff):
            with self.assertRaisesRegex(
                M.Refused, "KERNEL_PROVENANCE_UNKNOWN_HOLD"
            ):
                self.inspect()

    def test_18_unexpected_real_scm_rights_fd_closes_and_holds(self):
        receiver, sender = self.pair()
        fd = os.open("/dev/null", os.O_RDONLY)
        try:
            sender.sendmsg(
                [self.frame()],
                [(socket.SOL_SOCKET, socket.SCM_RIGHTS,
                  array.array("i", [fd]))])
            with self.assertRaisesRegex(
                M.Refused, "KERNEL_PROVENANCE_UNKNOWN_HOLD"
            ):
                M.inspect_ci_only(
                    receiver, expected_request_frame=self.frame(),
                    boundary=self.local)
        finally:
            os.close(fd)

    def test_19_kernel_observer_positive_authority_flag_refused(self):
        receiver, _ = self.pair()
        fake = {
            "kind": M.K.OBSERVATION_KIND,
            "status": "KERNEL_PACKET_PEER_OBSERVED_BUT_SWAYPX_UNENROLLED",
            "packetSha256Untrusted": hashlib.sha256(self.frame()).hexdigest(),
            "packetLength": len(self.frame()),
            "kernelPeerPidObserved": os.getpid(),
            "kernelPeerUidObserved": os.getuid(),
            "kernelPeerGidObserved": os.getgid(),
            "exactPeerPidfdAliveAtRead": True,
            "rawPacketUntrusted": True,
            **M.K.NO_AUTHORITY, "safeActions": [],
        }
        fake["sourceEvidenceTrusted"] = True
        with mock.patch.object(M.K, "inspect_one_untrusted_packet",
                               return_value=fake):
            with self.assertRaisesRegex(
                M.Refused, "PACKET_OR_AUTHORITY_MISMATCH"
            ):
                M.inspect_ci_only(
                    receiver, expected_request_frame=self.frame(),
                    boundary=self.local)

    def test_20_original_route_positive_authority_flag_refused(self):
        receiver, sender = self.pair()
        sender.sendall(self.frame())
        original = M.P._route
        def poison(boundary, request):
            return dict(original(boundary, request), productionAuthority=True)
        with mock.patch.object(M.P, "_route", side_effect=poison):
            with self.assertRaisesRegex(M.Refused, "ROUTE_PROMOTION"):
                M.inspect_ci_only(
                    receiver, expected_request_frame=self.frame(),
                    boundary=self.local)

    def test_21_untrusted_sender_report_extra_field_refused(self):
        receiver, _ = self.pair()
        fake = {
            "kind": M.K.OBSERVATION_KIND,
            "status": "KERNEL_PACKET_PEER_OBSERVED_BUT_SWAYPX_UNENROLLED",
            "packetSha256Untrusted": hashlib.sha256(self.frame()).hexdigest(),
            "packetLength": len(self.frame()),
            "kernelPeerPidObserved": os.getpid(),
            "kernelPeerUidObserved": os.getuid(),
            "kernelPeerGidObserved": os.getgid(),
            "exactPeerPidfdAliveAtRead": True,
            "rawPacketUntrusted": True,
            **M.K.NO_AUTHORITY, "safeActions": [],
            "signInApproved": True,
        }
        with mock.patch.object(M.K, "inspect_one_untrusted_packet",
                               return_value=fake):
            with self.assertRaisesRegex(M.Refused, "UNEXPECTED_KERNEL_REPORT"):
                M.inspect_ci_only(
                    receiver, expected_request_frame=self.frame(),
                    boundary=self.local)

    def test_22_production_admission_is_unconditional_refusal(self):
        with self.assertRaisesRegex(M.Refused, "NO_INDEPENDENT_SIGNIN_SOURCE"):
            M.protected_identity_admission()
        self.denied(self.inspect())


if __name__ == "__main__":
    unittest.main(verbosity=2)
