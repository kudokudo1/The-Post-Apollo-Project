#!/usr/bin/env python3
"""DOC 5 / real Linux packet + C5/native original-operation recovery denies."""
from __future__ import annotations

import array
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from TimeWC5KernelObservedRecoveryCI import (  # noqa: E402
    C5_ROLE, NATIVE_ROLE, K, KernelRecoveryObservation,
    fixture_packet_ci_only, inspect_dual_packet_returns_ci_only,
)
from TimeWC5ReadOnlyRecoveryPlanReference import (  # noqa: E402
    prepare_unknown_recovery_intents,
)
from test_timew_c5_review_shadow_reference import original_fixture  # noqa: E402
from test_timew_c5_custodian_boundary_reference import snapshot  # noqa: E402
from test_timew_c5_dual_recovery_return_reference import native_snapshot  # noqa: E402

CI_ONLY = (
    sys.platform == "linux" and os.geteuid() == 0
    and os.environ.get("GITHUB_ACTIONS") == "true"
    and os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted"
)


@unittest.skipUnless(CI_ONLY, "DOC 5 real kernel packet tests: GitHub hosted root CI only")
class KernelTimeWRecoveryDenyTests(unittest.TestCase):
    def setUp(self):
        self.original = original_fixture()
        self.plan = prepare_unknown_recovery_intents(
            original=self.original, uncertainty="NATIVE_RESIZE_ACK_LOST")
        self.c5 = snapshot(self.original)
        self.native = native_snapshot(self.original)

    def pair(self, *, kind=socket.SOCK_SEQPACKET, passcred=True, timeout=0.5):
        reader, writer = socket.socketpair(socket.AF_UNIX, kind)
        self.addCleanup(reader.close)
        self.addCleanup(writer.close)
        reader.settimeout(timeout)
        if passcred:
            reader.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        return reader, writer

    def denied(self, out):
        self.assertIs(type(out), KernelRecoveryObservation)
        self.assertEqual(out.safe_actions, ())
        for field in (
            "source_authenticated", "enrolled_custodian_verified",
            "independent_current_history_verified",
            "original_human_consent_verified", "protected_spent_verified",
            "native_selected_xdg_verified", "native_terminal_receipt_verified",
            "production_authorized", "native_action_allowed",
            "retry_allowed", "undo_allowed",
        ):
            self.assertIs(getattr(out, field), False, field)

    def compare(self, *, c5=None, native=None,
                packet_c5=None, packet_native=None,
                plan=None, c5_kind=socket.SOCK_SEQPACKET,
                native_kind=socket.SOCK_SEQPACKET, passcred_c5=True,
                passcred_native=True, expect=""):
        c = self.c5 if c5 is None else c5
        n = self.native if native is None else native
        r1, w1 = self.pair(kind=c5_kind, passcred=passcred_c5)
        r2, w2 = self.pair(kind=native_kind, passcred=passcred_native)
        w1.send(fixture_packet_ci_only(C5_ROLE, c) if packet_c5 is None
                else packet_c5)
        w2.send(fixture_packet_ci_only(NATIVE_ROLE, n) if packet_native is None
                else packet_native)
        out = inspect_dual_packet_returns_ci_only(
            c5_receiver=r1, native_receiver=r2,
            expected_c5_return=c, expected_native_return=n,
            original_recovery_plan=self.plan if plan is None else plan)
        self.denied(out)
        if expect:
            self.assertEqual(out.status, expect)
        return out

    def test_exact_two_kernel_observed_returns_are_still_not_custody(self):
        z = self.compare(expect="KERNEL_OBSERVED_UNENROLLED_TWO_RETURNS_UNKNOWN_HOLD")
        self.assertEqual(z.comparison_diagnostic,
                         "MATCHED_BUT_UNENROLLED_C5_NATIVE_UNKNOWN_HOLD")
        self.assertEqual(z.c5_sender_pid_observed, os.getpid())
        self.assertEqual(z.native_sender_pid_observed, os.getpid())
        self.assertIs(z.different_local_pid_observed, False)

    def test_private_role_tag_swapping_refused_by_packet_hash(self):
        c5_packet = fixture_packet_ci_only(C5_ROLE, self.c5)
        native_packet = fixture_packet_ci_only(NATIVE_ROLE, self.native)
        z = self.compare(packet_c5=native_packet, packet_native=c5_packet)
        self.assertEqual(z.status, "C5_KERNEL_PACKET_UNKNOWN_HOLD")

    def test_different_actual_packet_than_caller_expected_c5_refuses(self):
        wrong = snapshot(self.original, state="ACTIVE")
        z = self.compare(packet_c5=fixture_packet_ci_only(C5_ROLE, wrong))
        self.assertEqual(z.status, "C5_KERNEL_PACKET_UNKNOWN_HOLD")

    def test_different_actual_packet_than_caller_expected_native_refuses(self):
        wrong = native_snapshot(self.original, resize="TIMEOUT")
        z = self.compare(packet_native=fixture_packet_ci_only(NATIVE_ROLE, wrong))
        self.assertEqual(z.status, "NATIVE_KERNEL_PACKET_UNKNOWN_HOLD")

    def test_wrong_transport_stream_refused(self):
        z = self.compare(c5_kind=socket.SOCK_STREAM)
        self.assertEqual(z.status, "C5_KERNEL_PACKET_UNKNOWN_HOLD")
        z = self.compare(native_kind=socket.SOCK_STREAM)
        self.assertEqual(z.status, "NATIVE_KERNEL_PACKET_UNKNOWN_HOLD")

    def test_missing_per_packet_creds_refused(self):
        z = self.compare(passcred_c5=False)
        self.assertEqual(z.status, "C5_KERNEL_PACKET_UNKNOWN_HOLD")
        z = self.compare(passcred_native=False)
        self.assertEqual(z.status, "NATIVE_KERNEL_PACKET_UNKNOWN_HOLD")

    def test_kernel_peer_pidfd_unavailable_refused(self):
        with patch.object(K, "SO_PEERPIDFD", 0x7fffffff):
            z = self.compare()
        self.assertEqual(z.status, "C5_KERNEL_PACKET_UNKNOWN_HOLD")

    def test_missing_or_closed_socket_never_promotes(self):
        r, w = self.pair()
        r.close()
        other, writer = self.pair()
        writer.send(fixture_packet_ci_only(NATIVE_ROLE, self.native))
        z = inspect_dual_packet_returns_ci_only(
            c5_receiver=r, native_receiver=other,
            expected_c5_return=self.c5,
            expected_native_return=self.native,
            original_recovery_plan=self.plan)
        self.denied(z)
        self.assertEqual(z.status, "TWO_DISTINCT_CONNECTED_RECEIVERS_REQUIRED_HOLD")

    def test_one_socket_reused_for_both_roles_refused_before_read(self):
        r, w = self.pair()
        z = inspect_dual_packet_returns_ci_only(
            c5_receiver=r, native_receiver=r,
            expected_c5_return=self.c5,
            expected_native_return=self.native,
            original_recovery_plan=self.plan)
        self.denied(z)
        self.assertEqual(z.status, "TWO_DISTINCT_CONNECTED_RECEIVERS_REQUIRED_HOLD")

    def test_invalid_local_expected_response_cannot_be_transmitted(self):
        r1, _ = self.pair()
        r2, _ = self.pair()
        z = inspect_dual_packet_returns_ci_only(
            c5_receiver=r1, native_receiver=r2,
            expected_c5_return={"not-json": object()},
            expected_native_return=self.native,
            original_recovery_plan=self.plan)
        self.denied(z)
        self.assertEqual(z.status, "MALFORMED_EXPECTED_LOCAL_FIXTURE_HOLD")

    def test_oversize_expected_local_response_refused(self):
        big = dict(self.c5, bogus="X" * 7000)
        r1, _ = self.pair()
        r2, _ = self.pair()
        z = inspect_dual_packet_returns_ci_only(
            c5_receiver=r1, native_receiver=r2,
            expected_c5_return=big,
            expected_native_return=self.native,
            original_recovery_plan=self.plan)
        self.denied(z)
        self.assertEqual(z.status, "MALFORMED_EXPECTED_LOCAL_FIXTURE_HOLD")

    def test_wrong_native_original_selected_window_is_detected_after_kernel(self):
        n = dict(self.native, window_key=str(uuid.uuid4()))
        z = self.compare(native=n)
        self.assertEqual(z.comparison_diagnostic,
                         "NATIVE_ORIGINAL_WINDOW_MISMATCH_UNKNOWN_HOLD")

    def test_c5_spent_candidate_with_local_snapshot_remains_unknown(self):
        c = dict(self.c5, source_mode="LOCAL_DEVELOPMENT")
        z = self.compare(c5=c)
        self.assertEqual(z.comparison_diagnostic,
                         "LOCAL_DEVELOPMENT_EVIDENCE_UNKNOWN_HOLD")

    def test_c5_active_with_claimed_native_effect_never_authorizes(self):
        c = dict(self.c5, ledger_state="ACTIVE")
        z = self.compare(c5=c)
        self.assertEqual(z.comparison_diagnostic,
                         "NATIVE_EFFECT_WITHOUT_PROVEN_SPENT_UNKNOWN_HOLD")

    def test_real_kernel_packet_cannot_redeem_contradictory_timeout(self):
        n = native_snapshot(self.original, resize="READY_AND_TIMEOUT",
                            present=True)
        z = self.compare(native=n)
        self.assertEqual(z.comparison_diagnostic,
                         "CONTRADICTORY_RESIZE_UNKNOWN_HOLD")

    def test_output_present_not_selected_window_settlement(self):
        n = native_snapshot(self.original, present=True)
        z = self.compare(native=n)
        self.assertEqual(z.comparison_diagnostic,
                         "OUTPUT_PRESENT_NOT_SELECTED_FRAME_UNKNOWN_HOLD")

    def test_claimed_selected_window_frame_flag_is_not_signed(self):
        n = native_snapshot(self.original, selected=True, present=True)
        z = self.compare(native=n)
        self.assertEqual(z.comparison_diagnostic,
                         "CLAIMED_SELECTED_FRAME_NOT_VERIFIED_UNKNOWN_HOLD")

    def test_unsupported_move_after_timeout_is_still_blocked(self):
        n = native_snapshot(self.original, resize="TIMEOUT", move="READY_ONLY",
                            present=True)
        z = self.compare(native=n)
        self.assertEqual(z.comparison_diagnostic,
                         "MOVE_WITHOUT_SETTLED_RESIZE_UNKNOWN_HOLD")

    def test_cross_domain_c5_response_cannot_be_laundered_by_packet(self):
        c = dict(self.c5, audience="post-apollo.connections.c3e.identity")
        z = self.compare(c5=c)
        self.assertEqual(z.comparison_diagnostic,
                         "C5_ORIGINAL_INTENT_MISMATCH_UNKNOWN_HOLD")

    def test_injected_production_authority_field_rejected(self):
        for role in ("c5", "native"):
            with self.subTest(role=role):
                changed = dict(self.c5 if role == "c5" else self.native,
                               production_authorized=True)
                z = self.compare(**{role: changed})
                self.assertEqual(
                    z.comparison_diagnostic,
                    "MALFORMED_C5_RESPONSE_UNKNOWN_HOLD"
                    if role == "c5" else "MALFORMED_NATIVE_RESPONSE_UNKNOWN_HOLD",
                )

    def test_inherited_sender_process_cannot_borrow_original_pidfd(self):
        reader, writer = self.pair()
        native_reader, native_writer = self.pair()
        native_writer.send(fixture_packet_ci_only(NATIVE_ROLE, self.native))
        pid = os.fork()
        if pid == 0:
            try:
                reader.close()
                native_reader.close()
                native_writer.close()
                writer.send(fixture_packet_ci_only(C5_ROLE, self.c5))
                os._exit(0)
            except BaseException:
                os._exit(9)
        writer.close()
        try:
            z = inspect_dual_packet_returns_ci_only(
                c5_receiver=reader, native_receiver=native_reader,
                expected_c5_return=self.c5,
                expected_native_return=self.native,
                original_recovery_plan=self.plan)
            self.denied(z)
            self.assertEqual(z.status, "C5_KERNEL_PACKET_UNKNOWN_HOLD")
        finally:
            _child, status = os.waitpid(pid, 0)
            self.assertEqual(status, 0)

    def test_unexpected_scm_rights_rejected_by_reused_observer(self):
        reader, writer = self.pair()
        native_reader, native_writer = self.pair()
        native_writer.send(fixture_packet_ci_only(NATIVE_ROLE, self.native))
        read_fd, write_fd = os.pipe()
        self.addCleanup(os.close, read_fd)
        self.addCleanup(os.close, write_fd)
        payload = fixture_packet_ci_only(C5_ROLE, self.c5)
        writer.sendmsg([payload], [(socket.SOL_SOCKET, socket.SCM_RIGHTS,
                                    array.array("i", [read_fd]))])
        z = inspect_dual_packet_returns_ci_only(
            c5_receiver=reader, native_receiver=native_reader,
            expected_c5_return=self.c5,
            expected_native_return=self.native,
            original_recovery_plan=self.plan)
        self.denied(z)
        self.assertEqual(z.status, "C5_KERNEL_PACKET_UNKNOWN_HOLD")

    def test_actual_distinct_connector_processes_are_still_unenrolled(self):
        # Two separate forked connectors create AFTER-FORK pathname socket
        # connections. This avoids pretending the parent's socketpair pidfd
        # is the child's original peer, and still cannot prove remote custody.
        children = []
        pipes = []
        with tempfile.TemporaryDirectory(prefix="doc5-recovery-ci-") as root:
            listeners = []
            for name in ("c5.sock", "native.sock"):
                listener = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
                listener.bind(os.path.join(root, name))
                listener.listen(1)
                listener.settimeout(3)
                listeners.append(listener)
            try:
                for i, expected in enumerate((
                    fixture_packet_ci_only(C5_ROLE, self.c5),
                    fixture_packet_ci_only(NATIVE_ROLE, self.native),
                )):
                    rd, wr = os.pipe()
                    pid = os.fork()
                    if pid == 0:
                        try:
                            os.close(wr)
                            for listener in listeners:
                                listener.close()
                            sender = socket.socket(socket.AF_UNIX,
                                                   socket.SOCK_SEQPACKET)
                            sender.connect(os.path.join(root, ("c5.sock", "native.sock")[i]))
                            sender.send(expected)
                            os.read(rd, 1)  # stay alive until observation
                            sender.close()
                            os.close(rd)
                            os._exit(0)
                        except BaseException:
                            os._exit(8)
                    os.close(rd)
                    children.append(pid)
                    pipes.append(wr)
                accepted = []
                for listener in listeners:
                    conn, _ = listener.accept()
                    conn.settimeout(0.5)
                    conn.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
                    accepted.append(conn)
                try:
                    z = inspect_dual_packet_returns_ci_only(
                        c5_receiver=accepted[0], native_receiver=accepted[1],
                        expected_c5_return=self.c5,
                        expected_native_return=self.native,
                        original_recovery_plan=self.plan)
                    self.denied(z)
                    self.assertEqual(z.status,
                                     "KERNEL_OBSERVED_UNENROLLED_TWO_RETURNS_UNKNOWN_HOLD")
                    self.assertEqual(z.comparison_diagnostic,
                                     "MATCHED_BUT_UNENROLLED_C5_NATIVE_UNKNOWN_HOLD")
                    self.assertTrue(z.different_local_pid_observed)
                    self.assertEqual(
                        {z.c5_sender_pid_observed, z.native_sender_pid_observed},
                        set(children))
                finally:
                    for conn in accepted:
                        conn.close()
            finally:
                for listener in listeners:
                    listener.close()
                for wr in pipes:
                    try:
                        os.write(wr, b"x")
                    except OSError:
                        pass
                    os.close(wr)
                for pid in children:
                    _child, status = os.waitpid(pid, 0)
                    self.assertEqual(status, 0)

    def test_non_hosted_runtime_never_reads_packets_or_returns_authority(self):
        r1, w1 = self.pair()
        r2, w2 = self.pair()
        with patch.dict(os.environ, {"RUNNER_ENVIRONMENT": "operator-desktop"}):
            z = inspect_dual_packet_returns_ci_only(
                c5_receiver=r1, native_receiver=r2,
                expected_c5_return=self.c5,
                expected_native_return=self.native,
                original_recovery_plan=self.plan)
        self.denied(z)
        self.assertEqual(z.status,
                         "HOSTED_ROOT_ONLY_NO_PRODUCTION_ACCESS_HOLD")

    def test_caller_plan_not_a_receipt_even_for_real_kernel_packets(self):
        z = self.compare(plan=object())
        self.assertEqual(z.comparison_diagnostic,
                         "INVALID_ORIGINAL_RECOVERY_PLAN_UNKNOWN_HOLD")


if __name__ == "__main__":
    unittest.main()
