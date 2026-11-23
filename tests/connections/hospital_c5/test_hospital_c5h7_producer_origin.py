#!/usr/bin/env python3
"""DOC 4 Hospital C5-H7: real Linux packet origin, false producer authority.

All tests run in disposable GitHub Linux CI with the current user, local
socketpairs and subprocesses. No installed Hospital process, user key, Room
database, Polkit, native display or genuine consent interaction is used.
"""
from __future__ import annotations

import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "services/connections/hospital"))
sys.path.insert(0, str(HERE))

import HospitalNativeIssuerCore as C
import HospitalNativeIssuerService as S
import HospitalC5H7ProducerOriginProbe as P


class C5H7OriginBoundary(unittest.TestCase):
    def setUp(self):
        self.now = 1700000000
        self.peer = (43100, 1000, 1000, 90200)

    def claim(self, *, peer=None):
        pid, uid, gid, tick = self.peer if peer is None else peer
        return {
            "schema": P.SCHEMA,
            "reviewSchema": P.REVIEW_SCHEMA,
            "audience": P.AUDIENCE,
            "reviewDigest": "a" * 64,
            "requestNonce": C.b64(bytes(range(32))),
            "writerInstance": "protected-px-001",
            "action": "TRASH",
            "roomId": "hospital-room-04",
            "operatorUid": 1000,
            "seatId": "logind-seat0-c2",
            "hostId": "b" * 64,
            "producerPid": pid,
            "producerUid": uid,
            "producerGid": gid,
            "producerStartTicks": tick,
            "producerReleaseDigest": "c" * 64,
            "historyHeadDigest": "d" * 64,
            "claimedShown": True,
            "claimedConfirmed": True,
            "issuedAt": self.now - 3,
            "shownAt": self.now - 2,
            "confirmedAt": self.now - 1,
            "expiresAt": self.now + 20,
        }

    def observe(self, claim=None, *, peer=None, now=None):
        return P.inspect_untrusted_packet(
            C.canonical(self.claim() if claim is None else claim),
            observed_peer=self.peer if peer is None else peer,
            now=self.now if now is None else now,
        )

    def assert_hold(self, result):
        for field in (
            "independentProducerReleaseEnrolled",
            "installedExecutableAuthenticated",
            "realDisplayObserved",
            "activeUnlockedSeatAuthenticated",
            "genuineOperatorGestureVerified",
            "rootAndRevocationCustodyVerified",
            "independentOneUseHistoryVerified",
            "protectedPxSourceAdmissionVerified",
            "canSatisfyNativeIssuerHardGate",
            "canLoadPrivateSigner",
            "canCommitHospitalRoom",
            "productionAuthorized",
        ):
            self.assertIs(result[field], False, field)
        self.assertEqual(result["safeActions"], [])

    def test_01_perfect_forged_packet_claim_never_authorizes(self):
        result = self.observe()
        self.assertTrue(result["kernelPeerTupleMatchesClaim"])
        self.assertTrue(result["claimedConfirmationFits"])
        self.assertEqual(result["status"], "UNTRUSTED_CLAIM_MATCHES_ORIGIN_HOLD")
        self.assert_hold(result)

    def test_02_wrong_pid_does_not_match_kernel_observation(self):
        value = self.claim()
        value["producerPid"] += 1
        result = self.observe(value)
        self.assertFalse(result["kernelPeerTupleMatchesClaim"])
        self.assert_hold(result)

    def test_03_wrong_uid_does_not_match_kernel_observation(self):
        value = self.claim()
        value["producerUid"] += 1
        result = self.observe(value)
        self.assertFalse(result["kernelPeerTupleMatchesClaim"])
        self.assert_hold(result)

    def test_04_wrong_gid_does_not_match_kernel_observation(self):
        value = self.claim()
        value["producerGid"] += 1
        result = self.observe(value)
        self.assertFalse(result["kernelPeerTupleMatchesClaim"])
        self.assert_hold(result)

    def test_05_wrong_pid_start_ticks_does_not_match(self):
        value = self.claim()
        value["producerStartTicks"] += 1
        result = self.observe(value)
        self.assertFalse(result["kernelPeerTupleMatchesClaim"])
        self.assert_hold(result)

    def test_06_future_claimed_confirmation_is_never_current(self):
        value = self.claim()
        value["confirmedAt"] = self.now + 1
        result = self.observe(value)
        self.assertFalse(result["claimedChronologyFits"])
        self.assert_hold(result)

    def test_07_expired_claim_never_matches(self):
        value = self.claim()
        value["expiresAt"] = self.now
        result = self.observe(value)
        self.assertFalse(result["claimedChronologyFits"])
        self.assert_hold(result)

    def test_08_claimed_display_before_issuance_never_matches(self):
        value = self.claim()
        value["shownAt"] = value["issuedAt"] - 1
        result = self.observe(value)
        self.assertFalse(result["claimedChronologyFits"])
        self.assert_hold(result)

    def test_09_forged_permanent_expiry_never_matches(self):
        value = self.claim()
        value["expiresAt"] = self.now + 100000
        result = self.observe(value)
        self.assertFalse(result["claimedChronologyFits"])
        self.assert_hold(result)

    def test_10_cancelled_or_not_shown_cannot_match(self):
        for field in ("claimedShown", "claimedConfirmed"):
            with self.subTest(field=field):
                value = self.claim()
                value[field] = False
                result = self.observe(value)
                self.assertFalse(result["claimedConfirmationFits"])
                self.assert_hold(result)

    def test_11_fake_release_digest_cannot_create_trust(self):
        for digest in ("0" * 64, "f" * 64):
            with self.subTest(digest=digest[:3]):
                value = self.claim()
                value["producerReleaseDigest"] = digest
                result = self.observe(value)
                self.assertTrue(result["kernelPeerTupleMatchesClaim"])
                self.assert_hold(result)

    def test_12_fake_independent_history_head_cannot_create_trust(self):
        value = self.claim()
        value["historyHeadDigest"] = "0" * 64
        self.assert_hold(self.observe(value))

    def test_13_wrong_schema_or_audience_rejected(self):
        for field, other in (
            ("schema", "postapollo.hospital.unreviewed.v2"),
            ("reviewSchema", "postapollo.hospital.c5h3.exact-room-review.v1"),
            ("audience", "postapollo.timew.consent"),
        ):
            with self.subTest(field=field):
                value = self.claim()
                value[field] = other
                with self.assertRaises(C.Refused):
                    self.observe(value)

    def test_14_extra_authority_claim_is_refused(self):
        value = self.claim()
        value["canLoadPrivateSigner"] = True
        with self.assertRaises(C.Refused):
            self.observe(value)

    def test_15_noncanonical_json_is_refused(self):
        raw = b" " + C.canonical(self.claim())
        with self.assertRaises(C.Refused):
            P.inspect_untrusted_packet(raw, observed_peer=self.peer, now=self.now)

    def test_16_duplicate_json_fields_are_refused(self):
        raw = C.canonical(self.claim()).replace(
            b'"action":', b'"action":"RESTORE","action":', 1)
        with self.assertRaises(C.Refused):
            P.inspect_untrusted_packet(raw, observed_peer=self.peer, now=self.now)

    def test_17_boolean_masquerading_as_uid_or_time_is_refused(self):
        for field in ("producerUid", "operatorUid", "confirmedAt"):
            with self.subTest(field=field):
                value = self.claim()
                value[field] = True
                with self.assertRaises(C.Refused):
                    self.observe(value)

    def test_18_noncanonical_nonce_or_bad_digest_refused(self):
        for field, value in (
            ("requestNonce", "not-a-32-byte-nonce"),
            ("historyHeadDigest", "not-a-root"),
            ("producerReleaseDigest", "z" * 64),
        ):
            with self.subTest(field=field):
                frame = self.claim()
                frame[field] = value
                with self.assertRaises(C.Refused):
                    self.observe(frame)

    def test_19_peer_tuple_cannot_be_a_caller_supplied_string(self):
        with self.assertRaises(C.Refused):
            self.observe(peer=("43100", 1000, 1000, 90200))
        with self.assertRaises(C.Refused):
            self.observe(peer=(True, 1000, 1000, 90200))

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux SCM_CREDENTIALS only")
    def test_20_real_same_process_kernel_packet_still_not_consent(self):
        self.assertNotEqual(os.getuid(), 0, "CI must be an unprivileged user")
        rx, tx = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        with rx, tx:
            rx.settimeout(4)
            rx.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
            actual = S._peer(rx)
            self.assertEqual(actual[:3], (os.getpid(), os.getuid(), os.getgid()))
            payload = C.canonical(self.claim(peer=actual))
            self.assertEqual(tx.send(payload), len(payload))
            report = P.receive_candidate_for_ci(
                rx, observed_peer=actual, now=self.now)
            self.assertTrue(report["kernelPeerTupleMatchesClaim"])
            self.assert_hold(report)

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux SCM_CREDENTIALS only")
    def test_21_inherited_fd_sent_from_other_pid_is_refused(self):
        self.assertNotEqual(os.getuid(), 0, "CI must be an unprivileged user")
        rx, tx = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        with rx, tx:
            rx.settimeout(4)
            rx.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
            origin = S._peer(rx)
            self.assertEqual(origin[0], os.getpid())
            child = (
                "import socket,sys;"
                "s=socket.socket(fileno=int(sys.argv[1]));"
                "assert s.send(b'forged-consent-packet')==len(b'forged-consent-packet')"
            )
            subprocess.run(
                [sys.executable, "-c", child, str(tx.fileno())],
                pass_fds=(tx.fileno(),), check=True, timeout=10,
            )
            # Original SO_PEERCRED still describes the opening parent.
            self.assertEqual(S._peer(rx), origin)
            # SCM_CREDENTIALS identifies actual child PID for the packet.
            with self.assertRaisesRegex(
                    C.Refused, "PACKET_SENDER_DIFFERS_FROM_PINNED_SOCKET_PEER"):
                P.receive_candidate_for_ci(
                    rx, observed_peer=origin, now=self.now)

    def test_22_missing_per_packet_credentials_refused(self):
        class NoAncillary:
            def setsockopt(self, *_args):
                pass
            def recvmsg(self, *_args):
                return (b"{}", [], 0, None)
        with self.assertRaisesRegex(
                C.Refused, "PACKET_SENDER_DIFFERS_FROM_PINNED_SOCKET_PEER"):
            P.receive_candidate_for_ci(
                NoAncillary(), observed_peer=self.peer, now=self.now)

    def test_23_truncated_or_control_truncated_packets_refused(self):
        for flag in (socket.MSG_TRUNC, socket.MSG_CTRUNC):
            with self.subTest(flag=flag):
                class Bad:
                    def setsockopt(self, *_args):
                        pass
                    def recvmsg(self, *_args):
                        return (b"{}", [], flag, None)
                with self.assertRaisesRegex(C.Refused, "BOUNDED_NATIVE_PACKET_REFUSED"):
                    P.receive_candidate_for_ci(
                        Bad(), observed_peer=self.peer, now=self.now)

    def test_24_forged_ancillary_sender_refused(self):
        class WrongSender:
            def setsockopt(self, *_args):
                pass
            def recvmsg(self, *_args):
                return (
                    b"{}",
                    [(socket.SOL_SOCKET, socket.SCM_CREDENTIALS,
                      struct.pack("3i", 43101, 1000, 1000))],
                    0, None,
                )
        with self.assertRaisesRegex(
                C.Refused, "PACKET_SENDER_DIFFERS_FROM_PINNED_SOCKET_PEER"):
            P.receive_candidate_for_ci(
                WrongSender(), observed_peer=self.peer, now=self.now)

    def test_25_no_fixture_or_callback_can_authorize(self):
        for kwargs in ({}, {"claimedSigned": True}, {"producer": object()}):
            with self.assertRaisesRegex(
                    C.Refused, "C5H7_INDEPENDENT_NATIVE_CONSENT_PRODUCER_NOT_ENROLLED"):
                P.authorize_human_consent(**kwargs)

    def test_26_disconnected_from_production_issuer_and_privileges(self):
        runtime = (
            ROOT / "services/connections/hospital/HospitalNativeIssuerService.py"
        ).read_text()
        source = (
            HERE / "HospitalC5H7ProducerOriginProbe.py"
        ).read_text()
        self.assertNotIn("HospitalC5H7ProducerOriginProbe", runtime)
        self.assertIn(
            'C.deny("INDEPENDENT_EXACT_ROOM_HUMAN_CONSENT_UNAVAILABLE")',
            runtime)
        self.assertNotIn("load_installed_key", source)
        self.assertNotIn("sign_px_grant", source)
        self.assertNotIn("subprocess.", source)
        self.assertNotIn("sqlite3.", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
