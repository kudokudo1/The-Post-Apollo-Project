#!/usr/bin/env python3
"""DOC 2: genuine C3e per-packet sender observation + C4b signed denial.

This is a disposable Linux CI-only side-by-side consistency experiment.
The original DOC 1 #2361 packet observer and original DOC 2 #2283 signed
denial verifier stay unchanged. A local packet and signed denial tied to
the same rollbackable challenge do NOT authenticate one another or
grant enrolled host, sender, current independent history, or Sign-In.
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import os
from pathlib import Path
import socket
import sys
import unittest
from unittest import mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/identity"))
sys.path.insert(0, str(ROOT / "tests/connections/identity_silverblue"))
from signed_command_receipt_v0 import LEGACY_RECEIPT_SCHEMA, ReceiptIssuer, _canonical
import c4b_raw_challenge_evidence_candidate_ci as E


def load_original(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C4B_PACKET_ORIGINAL_DOC1_SOURCE_REQUIRED")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


DOC1 = load_original(
    "doc2_reused_doc1_exact_packet_ci",
    ROOT / "tests/connections/test_connections_c3e_identity_packet_origin_nonadmission.py",
)
P = DOC1.M


def b64(data: bytes) -> bytes:
    return base64.urlsafe_b64encode(data).rstrip(b"=")


class RealIdentityPacketAndSignedDenialStillHold(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        DOC1.IdentityPacketOriginStillNotAuthority.setUpClass()

    def setUp(self):
        # Reuse the existing DOC 1 real socketpair+fixture test setup, not a
        # duplicate kernel credential parser or an installed native service.
        self.p = DOC1.IdentityPacketOriginStillNotAuthority(
            "test_03_original_issued_challenge_observation_not_settlement")
        self.p.setUp()
        self.addCleanup(self.p.doCleanups)
        self.raw = self.p.fixture.challenge  # exactly 32 local test bytes
        self.signer = Ed25519PrivateKey.generate()  # disposable test signer only
        self.public = self.signer.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        self.nonce = E.encode_raw_challenge_ci_only(self.raw)
        body = _canonical({
            "schema": LEGACY_RECEIPT_SCHEMA, "state": "UNAVAILABLE",
            "requestId": None,
        }) + b"\n"
        self.signed_frame = ReceiptIssuer(self.signer).seal(
            "BEGIN", None, self.nonce, body)
        self.serial = self.proof(self.public, self.signed_frame)

    @staticmethod
    def proof(public: bytes, frame: bytes) -> bytes:
        return E.C4B.PROOF_PREFIX + b"pub=" + b64(public) + b" frame=" + b64(frame) + b"\n"

    def original_outcome_frame(self):
        return self.p.frame({
            **self.p.req, "op": "OUTCOME", "challengeHex": self.raw.hex(),
        })

    def check_signed(self, *, raw=None, serial=None):
        out = E.inspect_raw_challenge_denial_ci_only(
            raw_challenge=self.raw if raw is None else raw,
            serial=self.serial if serial is None else serial,
        )
        self.assertEqual(out["schema"], E.SCHEMA)
        self.assertEqual(out["status"], E.STATUS)
        self.assertTrue(out["ciOnlyOriginalSignedDenialVerified"])
        self.assertEqual(out["rawChallengeSha256"], hashlib.sha256(self.raw).hexdigest())
        for flag in E.DENIED:
            self.assertIs(out[flag], False, flag)
        return out

    def check_packet(self, *, frame=None, actual=None, boundary=None, **kwargs):
        expected = self.original_outcome_frame() if frame is None else frame
        out = self.p.inspect(expected=expected, actual=actual, boundary=boundary, **kwargs)
        self.p.denied(out)
        self.assertEqual(out["next"], "HOLD_NO_PROTECTED_IDENTITY_OR_AUTO_RETRY")
        self.assertEqual(out["packetSha256LocalComparisonOnly"],
                         hashlib.sha256(expected).hexdigest())
        return out

    def test_01_real_same_process_packet_plus_original_signed_denial_not_enrollment(self):
        out = self.check_packet()
        self.assertEqual(out["kernelSenderPidObservedOnly"], os.getpid())
        self.assertEqual(out["localReadOnlyOperation"], "OUTCOME")
        self.assertEqual(out["originalDiagnosticStatus"], P.P.S.STATUS_LOCAL)
        self.check_signed()

    def test_02_protected_custodian_hold_even_with_valid_signed_denial(self):
        frame = self.p.frame({**self.p.req, "op": "CUSTODIAN_STATUS"})
        out = self.check_packet(frame=frame, boundary=self.p.protected)
        self.assertEqual(out["originalDiagnosticStatus"], P.P.S.STATUS_HOLD)
        self.check_signed()

    def test_03_consumed_local_history_not_protected_authority(self):
        self.p.fixture.commit()
        out = self.check_packet()
        self.assertEqual(out["originalDiagnosticStatus"], P.P.S.STATUS_LOCAL)
        self.check_signed()

    def test_04_inherited_writer_with_matching_frame_is_refused_despite_valid_denial(self):
        receiver, sender = self.p.pair()
        child = os.fork()
        if child == 0:
            try:
                receiver.close()
                sender.sendall(self.original_outcome_frame())
                os._exit(0)
            except BaseException:
                os._exit(93)
        sender.close()
        try:
            with self.assertRaisesRegex(P.Refused, "KERNEL_PROVENANCE_UNKNOWN_HOLD"):
                P.inspect_ci_only(
                    receiver, expected_request_frame=self.original_outcome_frame(),
                    boundary=self.p.local)
        finally:
            pid, status = os.waitpid(child, 0)
            self.assertEqual(pid, child)
            self.assertEqual(status, 0)
        self.check_signed()

    def test_05_missing_real_per_packet_credentials_refused_but_signature_still_valid(self):
        with self.assertRaisesRegex(P.Refused, "KERNEL_PROVENANCE_UNKNOWN_HOLD"):
            self.check_packet(passcred=False)
        self.check_signed()

    def test_06_wrong_actual_packet_refused_even_if_expected_challenge_signed(self):
        wrong = self.p.frame({**self.p.req, "requestNonce": "ee" * 16})
        with self.assertRaisesRegex(P.Refused, "PACKET_OR_AUTHORITY_MISMATCH"):
            self.check_packet(actual=wrong)
        self.check_signed()

    def test_07_stream_socket_cannot_claim_per_packet_sender(self):
        with self.assertRaisesRegex(P.Refused, "KERNEL_PROVENANCE_UNKNOWN_HOLD"):
            self.check_packet(kind=socket.SOCK_STREAM)
        self.check_signed()

    def test_08_c4b_rejects_tampered_raw_challenge_after_valid_packet(self):
        self.check_packet()
        bad = bytes([self.raw[0] ^ 1]) + self.raw[1:]
        with self.assertRaises(E.Refused):
            self.check_signed(raw=bad)

    def test_09_c4b_rejects_substituted_unenrolled_receipt_key(self):
        self.check_packet()
        other = Ed25519PrivateKey.generate().public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw)
        with self.assertRaises(E.Refused):
            self.check_signed(serial=self.proof(other, self.signed_frame))

    def test_10_c4b_rejects_altered_signed_denial(self):
        self.check_packet()
        altered = bytearray(self.signed_frame)
        altered[-4] ^= 1
        with self.assertRaises(E.Refused):
            self.check_signed(serial=self.proof(self.public, bytes(altered)))

    def test_11_forged_real_packet_source_authority_refused(self):
        receiver, sender = self.p.pair()
        sender.sendall(self.original_outcome_frame())
        original = P.K.inspect_one_untrusted_packet

        def poisoned(sock):
            observed = original(sock)  # truly read kernel packet first
            return {**observed, "sourceEvidenceTrusted": True}

        with mock.patch.object(P.K, "inspect_one_untrusted_packet", side_effect=poisoned):
            with self.assertRaisesRegex(P.Refused, "UNEXPECTED_KERNEL_REPORT"):
                P.inspect_ci_only(
                    receiver, expected_request_frame=self.original_outcome_frame(),
                    boundary=self.p.local)
        self.check_signed()

    def test_12_original_protected_identity_admission_and_broker_remain_disabled(self):
        self.check_packet()
        self.check_signed()
        with self.assertRaisesRegex(P.Refused, "NO_INDEPENDENT_SIGNIN_SOURCE"):
            P.protected_identity_admission()
        broker = (ROOT / "services/connections/ConnectionsBroker.qml").read_text()
        self.assertIn("readonly property bool credentialActionsEnabled: false", broker)
        src = (ROOT / "tests/connections/c3e_release_trust/"
               "C3eIdentityPacketOriginNonAdmissionCI.py").read_text()
        self.assertIn("K.inspect_one_untrusted_packet(receiver)", src)
        self.assertIn("P._route(boundary, request)", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
