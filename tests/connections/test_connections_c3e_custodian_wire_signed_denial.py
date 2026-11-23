#!/usr/bin/env python3
"""DOC 1: real separate-process signed candidate packets still deny authority."""
from __future__ import annotations

import array
import base64
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import signal
import socket
import struct
import sys
import unittest
from unittest import mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "tests/connections/c3e_release_trust"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3E_WIRE_EXPECTED_ORIGINAL_SOURCE_REQUIRED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


M = _load("c3e_custodian_wire_under_test",
          HERE / "C3eCustodianWireDenialCI.py")
S = _load("c3e_custodian_wire_original_boundary",
          HERE / "C3eStorageIndependentTrustBoundary.py")


def _packet(response):
    payload = json.dumps(response, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True).encode("ascii")
    return struct.pack(">I", len(payload)) + payload


def _send_child(sender, receiver, data, behavior):
    receiver.close()
    try:
        if behavior == "kill_before":
            os.kill(os.getpid(), signal.SIGKILL)
        if behavior == "close_before":
            return
        if behavior == "with_fd":
            fd = os.open("/dev/null", os.O_RDONLY)
            try:
                sender.sendmsg([data], [(socket.SOL_SOCKET, socket.SCM_RIGHTS,
                                         array.array("i", [fd]))])
            finally:
                os.close(fd)
        else:
            sender.sendall(data)
        if behavior == "kill_after":
            os.kill(os.getpid(), signal.SIGKILL)
    finally:
        sender.close()


class RealProcessCustodianWireDenialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (sys.platform != "linux" or os.geteuid() != 0
                or os.environ.get("GITHUB_ACTIONS") != "true"
                or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
            raise RuntimeError("C3E_WIRE_GITHUB_HOSTED_ROOT_ONLY")
        cls.ctx = multiprocessing.get_context("fork")

    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        self.pub = self.key.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw)
        self.request = {
            "schema": M.C.REQUEST_SCHEMA, "purpose": M.C.PURPOSE,
            "requestId": "1a"*16, "challengeHex": "2b"*32,
            "epoch": "3c"*16, "previousHeadSha256": "4d"*32,
            "previousSequence": 40,
        }
        self.response = self.sign()

    def sign(self, *, key=None, request=None, **changes):
        req = self.request if request is None else request
        body = {
            **req, "schema": M.C.RESPONSE_SCHEMA,
            "signerRole": M.C.ROLE,
            "kind": "UNAVAILABLE", "settlement": "NONE",
            "challengeState": "UNKNOWN",
            "observedHeadSha256": req["previousHeadSha256"],
            "observedSequence": req["previousSequence"], **changes,
        }
        sig = (self.key if key is None else key).sign(
            b"POSTAPOLLO_C3E_CUSTODIAN_CANDIDATE_CI_V1\x00"
            + M.C._canonical(body))
        return {
            **body, "signatureB64url": base64.urlsafe_b64encode(sig)
                     .decode("ascii").rstrip("="),
        }

    def run_one(self, *, response=None, raw=None, request=None, pub=None,
                behavior="send"):
        receiver, sender = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        receiver.settimeout(2.0)
        data = _packet(self.response if response is None else response) \
            if raw is None else raw
        child = self.ctx.Process(
            target=_send_child, args=(sender, receiver, data, behavior))
        child.start()
        sender.close()
        try:
            result = M.verify_one_denial_ci_only(
                receiver,
                request=self.request if request is None else request,
                prior_test_public_key=self.pub if pub is None else pub)
            return result
        finally:
            receiver.close()
            child.join(timeout=3)
            if child.is_alive():
                child.kill()
                child.join(timeout=3)
            if behavior in ("kill_before", "kill_after"):
                self.assertEqual(child.exitcode, -signal.SIGKILL)
            else:
                self.assertEqual(child.exitcode, 0)

    def denied(self, result):
        self.assertEqual(result["schema"], M.SCHEMA)
        self.assertEqual(result["status"], M.STATUS)
        self.assertEqual(result["next"],
                         "HOLD_UNENROLLED_TEST_KEY_NO_TERMINAL_SETTLEMENT")
        self.assertTrue(result["testSignatureValid"])
        self.assertFalse(result["messageSenderEnrolled"])
        self.assertIsNone(result["winner"])
        self.assertEqual(result["safeActions"], [])
        for k in M.DENIED:
            self.assertIs(result[k], False, k)
        self.assertEqual(set(result), {
            "schema", "status", "relation", "candidateDigestSha256",
            "testPublicKeySha256", "testSignatureValid",
            "messageSenderEnrolled", "winner", "safeActions", "next", *M.DENIED,
        })

    def test_01_real_separate_process_signed_denial_still_holds(self):
        out = self.run_one()
        self.assertEqual(out["relation"],
                         "SIGNED_TEST_RESPONSE_EQUAL_NOT_TRUSTED_HOLD")
        self.denied(out)

    def test_02_real_process_signed_stale_head_still_holds(self):
        out = self.run_one(response=self.sign(observedSequence=39))
        self.assertEqual(out["relation"],
                         "SIGNED_TEST_RESPONSE_STALE_HEAD_HOLD")
        self.denied(out)

    def test_03_real_process_signed_ahead_head_still_holds(self):
        out = self.run_one(response=self.sign(observedSequence=41))
        self.assertEqual(out["relation"],
                         "SIGNED_TEST_RESPONSE_AHEAD_UNVERIFIED_HOLD")
        self.denied(out)

    def test_04_real_process_signed_equal_sequence_fork_holds(self):
        out = self.run_one(
            response=self.sign(observedHeadSha256="f"*64))
        self.assertEqual(out["relation"],
                         "SIGNED_TEST_RESPONSE_EQUAL_SEQUENCE_FORK_HOLD")
        self.denied(out)

    def test_05_same_key_two_conflicting_real_process_packets_no_winner(self):
        left = self.sign(observedSequence=41, observedHeadSha256="a"*64)
        right = self.sign(observedSequence=41, observedHeadSha256="b"*64)
        self.denied(self.run_one(response=left))
        self.denied(self.run_one(response=right))
        comparison = M.C.compare_signed_candidates_ci_only(
            request=self.request, left=left, right=right,
            test_public_key=self.pub)
        self.assertEqual(comparison["relation"],
                         "SIGNED_TEST_CANDIDATES_SAME_SEQUENCE_FORK_HOLD")
        self.assertIsNone(comparison["winner"])
        for name in M.C.DENIED:
            self.assertIs(comparison[name], False)

    def test_06_repeat_same_signed_packet_is_not_independent_quorum(self):
        self.denied(self.run_one())
        self.denied(self.run_one())
        result = M.C.compare_signed_candidates_ci_only(
            request=self.request, left=self.response, right=self.response,
            test_public_key=self.pub)
        self.assertIn("STILL_NOT_QUORUM_HOLD", result["relation"])
        self.assertEqual(result["safeActions"], [])

    def test_07_wrong_separately_supplied_test_pin_refuses(self):
        other = Ed25519PrivateKey.generate()
        wrong = other.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        with self.assertRaisesRegex(M.Refused, "ORIGINAL_SIGNED_CANDIDATE"):
            self.run_one(pub=wrong)

    def test_08_correct_signed_packet_under_wrong_signer_refused(self):
        other = Ed25519PrivateKey.generate()
        with self.assertRaisesRegex(M.Refused, "ORIGINAL_SIGNED_CANDIDATE"):
            self.run_one(response=self.sign(key=other))

    def test_09_tampered_signed_head_refused(self):
        bad = dict(self.response, observedHeadSha256="e"*64)
        with self.assertRaisesRegex(M.Refused, "ORIGINAL_SIGNED_CANDIDATE"):
            self.run_one(response=bad)

    def test_10_wrong_request_id_refused(self):
        req = dict(self.request, requestId="e"*32)
        with self.assertRaisesRegex(M.Refused, "ORIGINAL_SIGNED_CANDIDATE"):
            self.run_one(request=req)

    def test_11_wrong_challenge_refused(self):
        req = dict(self.request, challengeHex="e"*64)
        with self.assertRaisesRegex(M.Refused, "ORIGINAL_SIGNED_CANDIDATE"):
            self.run_one(request=req)

    def test_12_wrong_epoch_refused(self):
        req = dict(self.request, epoch="e"*32)
        with self.assertRaisesRegex(M.Refused, "ORIGINAL_SIGNED_CANDIDATE"):
            self.run_one(request=req)

    def test_13_cross_purpose_request_refused(self):
        req = dict(self.request, purpose="postapollo.timew.restore")
        with self.assertRaises(M.C.Refused):
            self.run_one(request=req)

    def test_14_resigned_cross_purpose_response_refused(self):
        with self.assertRaisesRegex(M.Refused, "ORIGINAL_SIGNED_CANDIDATE"):
            self.run_one(response=self.sign(purpose="postapollo.hospital"))

    def test_15_signed_committed_receipt_refused(self):
        with self.assertRaisesRegex(M.Refused, "ORIGINAL_SIGNED_CANDIDATE"):
            self.run_one(response=self.sign(kind="COMMITTED"))

    def test_16_signed_spent_challenge_claim_refused(self):
        with self.assertRaisesRegex(M.Refused, "ORIGINAL_SIGNED_CANDIDATE"):
            self.run_one(response=self.sign(challengeState="CONSUMED"))

    def test_17_positive_credential_action_field_refused(self):
        with self.assertRaisesRegex(M.Refused, "ORIGINAL_SIGNED_CANDIDATE"):
            self.run_one(response=self.sign(productionSignInAllowed=True))

    def test_18_reject_duplicate_json_field_in_wire_packet(self):
        body = json.dumps(self.response, separators=(",", ":")).encode("ascii")
        poisoned = b'{"kind":"UNAVAILABLE",' + body[1:]
        raw = struct.pack(">I", len(poisoned)) + poisoned
        with self.assertRaisesRegex(M.Refused, "DUPLICATE_JSON_KEY_REFUSED"):
            self.run_one(raw=raw)

    def test_19_reject_short_length_prefix(self):
        wire = _packet(self.response)
        wrong = struct.pack(">I", len(wire)) + wire[4:]
        with self.assertRaisesRegex(M.Refused, "EXACT_FRAME_SIZE_REQUIRED"):
            self.run_one(raw=wrong)

    def test_20_reject_trailing_bytes_after_declared_payload(self):
        with self.assertRaisesRegex(M.Refused, "EXACT_FRAME_SIZE_REQUIRED"):
            self.run_one(raw=_packet(self.response) + b"extra")

    def test_21_peer_closes_without_reply_unknown_no_retry(self):
        with self.assertRaisesRegex(M.UnknownAfterSend, "UNKNOWN_HOLD"):
            self.run_one(behavior="close_before")

    def test_22_peer_sigkill_before_reply_unknown_no_retry(self):
        with self.assertRaisesRegex(M.UnknownAfterSend, "UNKNOWN_HOLD"):
            self.run_one(behavior="kill_before")

    def test_23_process_killed_after_sending_valid_denial_no_authority(self):
        self.denied(self.run_one(behavior="kill_after"))

    def test_24_unexpected_rights_descriptor_is_closed_and_refused(self):
        before = len(os.listdir("/proc/self/fd"))
        with self.assertRaisesRegex(M.Refused, "UNEXPECTED_ANCILLARY"):
            self.run_one(behavior="with_fd")
        self.assertEqual(len(os.listdir("/proc/self/fd")), before)

    def test_25_stream_socket_is_not_exact_packet_connection(self):
        a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(a.close)
        self.addCleanup(b.close)
        with self.assertRaisesRegex(M.Refused, "REAL_SEQPACKET"):
            M.verify_one_denial_ci_only(
                a, request=self.request, prior_test_public_key=self.pub)

    def test_26_wrong_test_public_key_length_refused(self):
        a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.addCleanup(a.close)
        self.addCleanup(b.close)
        with self.assertRaisesRegex(M.Refused, "TEST_PUBLIC_KEY_REQUIRED"):
            M.verify_one_denial_ci_only(
                a, request=self.request, prior_test_public_key=b"\0"*31)

    def test_27_missing_reply_timeout_means_unknown_not_replay(self):
        a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.addCleanup(a.close)
        self.addCleanup(b.close)
        a.settimeout(0.1)
        with self.assertRaisesRegex(M.UnknownAfterSend, "UNKNOWN_HOLD"):
            M.verify_one_denial_ci_only(
                a, request=self.request, prior_test_public_key=self.pub)

    def test_28_cannot_use_self_hosted_runner_as_security_evidence(self):
        a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.addCleanup(a.close)
        self.addCleanup(b.close)
        with mock.patch.dict(os.environ, {"RUNNER_ENVIRONMENT": "self-hosted"}):
            with self.assertRaisesRegex(M.Refused, "DISPOSABLE_HOSTED_ROOT"):
                M.verify_one_denial_ci_only(
                    a, request=self.request, prior_test_public_key=self.pub)

    def test_29_original_protected_boundary_still_has_no_local_fallback(self):
        protected = S.TrustBoundary(required_mode=S.PROTECTED_REQUIRED)
        self.assertEqual(
            protected.protected_required_status()["status"], S.STATUS_HOLD)
        with self.assertRaisesRegex(S.Refused, "HOLD_NO_FALLBACK"):
            protected.read_current_snapshot()

    def test_30_valid_test_wire_denial_cannot_activate_production(self):
        self.denied(self.run_one())
        with self.assertRaisesRegex(M.Refused, "NO_INDEPENDENT_CUSTODIAN"):
            M.protected_admission()


if __name__ == "__main__":
    unittest.main(verbosity=2)
