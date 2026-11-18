#!/usr/bin/env python3
"""C4b: 24 adversarial host-controller nonce / signed-denial evidence tests."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/identity"))
from signed_command_receipt_v0 import (
    LEGACY_RECEIPT_SCHEMA, ReceiptIssuer, _canonical,
)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_controller_challenge_ci as V

def encoded(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=")

class ControllerFreshChallengeTests(unittest.TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        self.public = self.key.public_key().public_bytes_raw()
        self.challenge = V.generate_controller_challenge()
        self.denial = _canonical({
            "schema": LEGACY_RECEIPT_SCHEMA,
            "state": "UNAVAILABLE",
            "requestId": None,
        }) + b"\n"
        self.frame = ReceiptIssuer(self.key).seal(
            "BEGIN", None, self.challenge, self.denial,
        )
        self.serial = self.proof(self.public, self.frame)

    @staticmethod
    def proof(pub, frame):
        return (V.PROOF_PREFIX + b"pub=" + encoded(pub) +
                b" frame=" + encoded(frame) + b"\n")

    _MISSING=object()

    def check(self, serial=None, challenge=_MISSING):
        return V.inspect_ci_only(
            serial=self.serial if serial is None else serial,
            # Explicit None is an adversarial value and must not be replaced
            # with the ordinary challenge. Only absence selects the default.
            controller_challenge=(
                self.challenge if challenge is self._MISSING else challenge
            ),
        )

    def refused(self, **changed):
        with self.assertRaises(V.Refused):
            self.check(**changed)

    def test_01_actual_ed25519_begin_denial_proves_nonce_without_grants(self):
        report = self.check()
        self.assertTrue(report["freshControllerNonceInActualSignedBeginDenialInCI"])
        self.assertTrue(report["publicKeyVerifiedOnlyForThisCIReceipt"])
        self.assertEqual(report["controllerChallengeSha256"],
                         hashlib.sha256(self.challenge.encode()).hexdigest())
        for key in V.NEGATIVE:
            self.assertIs(report[key], False, key)

    def test_02_old_signed_receipt_cannot_satisfy_fresh_new_controller_nonce(self):
        self.refused(challenge=V.generate_controller_challenge())

    def test_03_different_public_key_refused_even_with_valid_old_receipt(self):
        other = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
        self.refused(serial=self.proof(other, self.frame))

    def test_04_changed_signed_frame_byte_refused(self):
        frame = self.frame.replace(b'"state":"UNAVAILABLE"', b'"state":"REQUESTED"')
        self.refused(serial=self.proof(self.public, frame))

    def test_05_different_action_refused(self):
        other = ReceiptIssuer(self.key).seal(
            "STATUS", "CI_NO_LOGIN_REQUEST_01234567", self.challenge, self.denial,
        )
        self.refused(serial=self.proof(self.public, other))

    def test_06_valid_signed_non_denial_cannot_grant_begin(self):
        requested = _canonical({
            "schema": LEGACY_RECEIPT_SCHEMA,
            "state": "REQUESTED",
            "requestId": "CI_NO_LOGIN_REQUEST_01234567",
        }) + b"\n"
        other = ReceiptIssuer(self.key).seal(
            "BEGIN", None, self.challenge, requested,
        )
        self.refused(serial=self.proof(self.public, other))

    def test_07_duplicate_proof_markers_refused(self):
        self.refused(serial=self.serial + self.serial)

    def test_08_missing_proof_marker_refused(self):
        self.refused(serial=b"C4B_ID_PASS // OTHER_TEST_ONLY\n")

    def test_09_host_marker_must_be_full_line_not_log_message_fragment(self):
        self.refused(serial=b"SPOOF " + self.serial)

    def test_10_control_in_public_proof_line_refused(self):
        self.refused(serial=self.serial[:-1] + b"\x1b\n")

    def test_11_malformed_pub_encoding_refused(self):
        self.refused(serial=V.PROOF_PREFIX + b"pub=???? frame=" +
                     encoded(self.frame) + b"\n")

    def test_12_malformed_frame_base64_refused(self):
        self.refused(serial=V.PROOF_PREFIX + b"pub=" + encoded(self.public) +
                     b" frame=!!!!\n")

    def test_13_empty_signature_frame_refused(self):
        self.refused(serial=self.proof(self.public, b"\n"))

    def test_14_receipt_frame_without_terminal_newline_refused(self):
        self.refused(serial=self.proof(self.public, self.frame.rstrip(b"\n")))

    def test_15_replay_signed_frame_twice_refused(self):
        self.refused(serial=b"junk\n"+self.serial+self.serial)

    def test_16_arbitrary_extra_non_proof_marker_does_not_grant_status(self):
        report=self.check(serial=self.serial+
            b"C4B_ID_PASS // CAN_BEGIN_SIGN_IN_TRUE\n")
        self.assertIs(report["hostAuthenticated"], False)
        self.assertIs(report["canBeginSignIn"], False)

    def test_17_non_ascii_nonce_refused(self):
        self.refused(challenge="\u2728" * 43)

    def test_18_noncanonical_nonce_length_refused(self):
        self.refused(challenge="z" * 42)
        self.refused(challenge="z" * 44)

    def test_19_boolean_and_none_nonce_refused(self):
        self.refused(challenge=True)
        self.refused(challenge=None)

    def test_20_oversize_serial_log_refused(self):
        self.refused(serial=b"x" * (V.MAX_SERIAL_BYTES+1))

    def test_21_issue_and_read_fixed_owner_only_nonce_file_in_disposable_ci(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"controller-nonce.txt"
            with mock.patch.dict(os.environ, {
                "GITHUB_ACTIONS":"true",
                "RUNNER_ENVIRONMENT":"github-hosted",
                "POST_APOLLO_ID_SILVERBLUE_CI_ONLY":"1",
                "GITHUB_ACTOR":"kudokudo1",
            }):
                digest=V._create_nonce_file(p)
                self.assertEqual(len(digest), 64)
                actual=V._read_nonce_file(p)
                self.assertEqual(len(actual), 43)
                self.assertEqual(digest, hashlib.sha256(actual.encode()).hexdigest())
                with self.assertRaises(V.Refused):
                    V._create_nonce_file(p)

    def test_22_symlink_nonce_file_refused(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/"nonce"
            a.write_bytes(self.challenge.encode()+b"\n")
            a.chmod(0o600)
            b=Path(d)/"swapped"
            b.symlink_to(a)
            with self.assertRaises(V.Refused):
                V._read_nonce_file(b)

    def test_23_challenge_file_wrong_permissions_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"nonce"
            p.write_bytes(self.challenge.encode()+b"\n")
            p.chmod(0o644)
            with self.assertRaises(V.Refused):
                V._read_nonce_file(p)

    def test_24_command_issuer_scope_and_no_private_enrollment_keys(self):
        with mock.patch.dict(os.environ, {
            "GITHUB_ACTIONS":"false",
            "RUNNER_ENVIRONMENT":"github-hosted",
            "POST_APOLLO_ID_SILVERBLUE_CI_ONLY":"1",
            "GITHUB_ACTOR":"kudokudo1",
        }):
            with self.assertRaises(V.Refused):
                V._ci_guard()
        source=(Path(__file__).parent/"verify_controller_challenge_ci.py").read_text()
        for needle in ("Ed25519PrivateKey.generate(", "POST_APOLLO_ID_CI_SIGNING_KEY=",
                       '"productionAuthority": True', '"hostAuthenticated": True',
                       "systemctl start", "rpm-ostree install"):
            self.assertNotIn(needle, source)

    def test_25_guest_uart_emits_proof_on_new_line_after_unterminated_console(self):
        # Reproduce the real transport class: a kernel/systemd console
        # fragment and then a genuine, correctly signed proof. No helper
        # changes to verifier parsing are permitted; the sender must
        # create the record boundary on the shared serial byte stream.
        probe=(Path(__file__).parent/"guest_identity_service_probe.sh").read_text()
        self.assertIn(
            r"""C4B_ID_CHALLENGE_PROOF\ //*) printf '\n%s\n' "$line" >/dev/ttyS0 ;;""",
            probe,
        )
        self.assertNotIn(
            r"""C4B_ID_CHALLENGE_PROOF\ //*) echo "$line" >/dev/ttyS0 ;;""",
            probe,
        )
        proof=self.serial.rstrip(b"\n").decode("ascii")
        write=subprocess.run(
            ["bash", "-c", r"""printf '\n%s\n' "$1" """, "_", proof],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=True, timeout=5,
        ).stdout
        self.assertEqual(write, b"\n"+self.serial)
        report=self.check(serial=b"unterminated systemd console text"+write)
        self.assertIs(report["freshControllerNonceInActualSignedBeginDenialInCI"], True)

    def test_26_prefixed_proof_still_strictly_refused(self):
        # An arbitrary firmware, kernel or attacker prefix remains invalid.
        # The fix is at the producer, NOT permissive prefix-stripping.
        self.refused(serial=b"unterminated systemd console text"+self.serial)
        self.refused(serial=b"\x1b[31m"+self.serial)

    def test_27_duplicate_is_still_refused_after_uart_record_boundary(self):
        self.refused(serial=b"unfinished prior output\n"+self.serial+self.serial)

if __name__ == "__main__":
    unittest.main(verbosity=2)
