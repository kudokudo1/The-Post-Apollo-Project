#!/usr/bin/env python3
"""DOC 2 C4b: real accepted AF_UNIX sender ambiguity + signed BEGIN denial.

This integrates *unchanged* DOC 1 #2355 actual socket and DOC 2 #2283
signed-denial source in disposable hosted Linux CI. The two diagnostics
refer to the same LOCAL TEST challenge, but do not authenticate each
other, their producer, message sender, current custodian, or Sign-In.
No production service, trust root, socket protocol, or grant is added.
"""
from __future__ import annotations

import base64
import importlib.util
import os
from pathlib import Path
import sys
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/identity"))
sys.path.insert(0, str(ROOT / "tests/connections/identity_silverblue"))
from signed_command_receipt_v0 import LEGACY_RECEIPT_SCHEMA, ReceiptIssuer, _canonical
import c4b_raw_challenge_evidence_candidate_ci as C4B


def load_original(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C4B_ACCEPTED_PEER_ORIGINAL_DOC1_SOURCE_MISSING")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


DOC1 = load_original(
    "c4b_owner_doc1_original_accepted_socket_tests",
    ROOT / "tests/connections/test_connections_c3e_accepted_unix_readonly_peer.py",
)
M = DOC1.M


def b64(raw: bytes) -> bytes:
    return base64.urlsafe_b64encode(raw).rstrip(b"=")


class C4bAcceptedSocketAndSignedDenialCI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # This also refuses local desktop/root execution outside disposable CI.
        DOC1.AcceptedUnixReadOnlyPeerTests.setUpClass()

    def setUp(self):
        self.peer = DOC1.AcceptedUnixReadOnlyPeerTests(
            "test_19_fd_inheritance_after_connect_breaks_sender_pid_claim")
        self.peer.setUp()
        self.addCleanup(self.peer.doCleanups)
        self.raw = self.peer.fixture.challenge
        self.signer = Ed25519PrivateKey.generate()  # disposable CI only
        self.pub = self.signer.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        self.nonce = C4B.encode_raw_challenge_ci_only(self.raw)
        body = _canonical({
            "schema": LEGACY_RECEIPT_SCHEMA,
            "state": "UNAVAILABLE",
            "requestId": None,
        }) + b"\n"
        self.frame = ReceiptIssuer(self.signer).seal(
            "BEGIN", None, self.nonce, body)
        self.serial = self.proof(self.pub, self.frame)

    @staticmethod
    def proof(pub, frame):
        return C4B.C4B.PROOF_PREFIX + b"pub=" + b64(pub) + b" frame=" + b64(frame) + b"\n"

    def signed(self, *, raw=None, serial=None):
        out = C4B.inspect_raw_challenge_denial_ci_only(
            raw_challenge=self.raw if raw is None else raw,
            serial=self.serial if serial is None else serial,
        )
        self.assertEqual(set(out), {
            "schema", "status", "rawChallengeSha256", "encodedCommandNonceSha256",
            "receiptFrameSha256", "runtimePublicKeySha256",
            "ciOnlyOriginalSignedDenialVerified", *C4B.DENIED})
        self.assertEqual(out["status"], C4B.STATUS)
        self.assertIs(out["ciOnlyOriginalSignedDenialVerified"], True)
        for flag in C4B.DENIED:
            self.assertIs(out[flag], False, flag)
        return out

    def assert_no_sender_or_custodian_authority(self):
        report = M.denial_only_observation_ci_only()
        self.assertIs(M.assert_accepted_observation_no_authority_ci_only(report), report)
        for flag in M.DENIED:
            self.assertIs(report[flag], False, flag)
        self.assertIsNone(report["trustedTerminalOutcome"])
        self.assertEqual(report["peerObservedFrom"], "SO_PEERCRED_AT_ACCEPT")

    def outcome_request(self):
        return self.peer.framed({
            **self.peer.request,
            "op": "OUTCOME",
            "challengeHex": self.raw.hex(),
        })

    def test_01_real_inherited_fd_sender_and_same_challenge_signed_denial_hold(self):
        result = self.peer.start_one(raw=self.outcome_request(), fork_sender=True)
        self.assertNotEqual(result["senderPid"], result["connectingPid"])
        self.assertEqual(result["reply"]["status"], "IPC_CI_DIAGNOSTIC_ONLY")
        self.assertEqual(result["reply"]["result"]["testState"], "issued")
        self.peer.denied(result["reply"])
        self.signed()
        self.assert_no_sender_or_custodian_authority()

    def test_02_normal_connector_and_signed_denial_still_not_host_enrollment(self):
        result = self.peer.start_one(raw=self.outcome_request())
        self.assertEqual(result["senderPid"], result["connectingPid"])
        self.assertEqual(result["reply"]["result"]["testState"], "issued")
        self.signed()
        self.assert_no_sender_or_custodian_authority()

    def test_03_consumed_local_challenge_still_not_protected_commit(self):
        self.peer.fixture.commit()
        result = self.peer.start_one(raw=self.outcome_request(), fork_sender=True)
        self.assertNotEqual(result["senderPid"], result["connectingPid"])
        self.assertEqual(result["reply"]["result"]["testState"], "consumed")
        self.signed()
        self.assert_no_sender_or_custodian_authority()

    def test_04_protected_custodian_status_and_valid_signed_denial_still_hold(self):
        result = self.peer.start_one(
            raw=self.peer.framed({**self.peer.request, "op": "CUSTODIAN_STATUS"}),
            boundary=self.peer.protected)
        self.assertEqual(result["reply"]["result"]["status"], M.P.S.STATUS_HOLD)
        self.peer.denied(result["reply"])
        self.signed()
        self.assert_no_sender_or_custodian_authority()

    def test_05_wrong_connecting_pid_is_dropped_with_no_reply(self):
        result = self.peer.start_one(
            raw=self.outcome_request(), pid_override=os.getpid(),
            expect_peer_drop=True)
        self.assertNotIn("reply", result)
        self.signed()
        self.assert_no_sender_or_custodian_authority()

    def test_06_wrong_original_c3e_raw_challenge_refused_by_c4b(self):
        with self.assertRaises(C4B.Refused):
            self.signed(raw=bytes([self.raw[0] ^ 1]) + self.raw[1:])

    def test_07_replaced_guest_receipt_key_refused(self):
        other = Ed25519PrivateKey.generate().public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw)
        with self.assertRaises(C4B.Refused):
            self.signed(serial=self.proof(other, self.frame))

    def test_08_modified_signed_denial_refused(self):
        bad = bytearray(self.frame)
        bad[-4] ^= 1
        with self.assertRaises(C4B.Refused):
            self.signed(serial=self.proof(self.pub, bytes(bad)))

    def test_09_duplicate_uart_proofs_refused(self):
        with self.assertRaises(C4B.Refused):
            self.signed(serial=self.serial * 2)

    def test_10_forged_doc1_peer_authentication_flag_refused(self):
        report = M.denial_only_observation_ci_only()
        with self.assertRaisesRegex(M.Refused, "AUTHORITY_INJECTION_REFUSED"):
            M.assert_accepted_observation_no_authority_ci_only(
                {**report, "originalMessageSenderAuthenticated": True})

    def test_11_forged_terminal_status_or_extra_claim_refused(self):
        report = M.denial_only_observation_ci_only()
        with self.assertRaises(M.Refused):
            M.assert_accepted_observation_no_authority_ci_only(
                {**report, "status": "PROTECTED_COMMITTED"})
        with self.assertRaises(M.Refused):
            M.assert_accepted_observation_no_authority_ci_only(
                {**report, "protectedReceipt": "fake"})

    def test_12_protected_admission_does_not_follow_both_diagnostics(self):
        self.signed()
        self.assert_no_sender_or_custodian_authority()
        with self.assertRaisesRegex(M.Refused, "NO_ENROLLED_SOURCE"):
            M.protected_admission()
        hold = self.peer.protected.protected_required_status()
        self.assertEqual(hold["status"], M.P.S.STATUS_HOLD)
        for key in M.P.S.DENIED:
            self.assertIs(hold[key], False, key)

    def test_13_no_runtime_gate_enabled_and_original_implementations_unchanged(self):
        broker = (ROOT / "services/connections/ConnectionsBroker.qml").read_text()
        self.assertIn("readonly property bool credentialActionsEnabled: false", broker)
        self.assertIn("P.serve_one_ci_only(conn, boundary)", Path(M.__file__).read_text())
        self.assertIn("verify_controller_challenge_ci as C4B",
                      (ROOT / "tests/connections/identity_silverblue/"
                       "c4b_raw_challenge_evidence_candidate_ci.py").read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
