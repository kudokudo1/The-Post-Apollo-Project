#!/usr/bin/env python3
"""DOC 4 C5-H9: actual DOC1 kernel packet + original C5 H4/H6 source.

No installed services or root keys. CI uses a disposable current-user
SOCK_SEQPACKET and an owner-source test harness to demonstrate that matching
Identity packet diagnostics and matching untrusted Hospital click claims
do NOT bypass the real C5 issuer's unconditional pre-key refusal.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import socket
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "services/connections/hospital"))

import HospitalC5H9C3eNegativeIntegration as H
import HospitalNativeIssuerCore as C
import HospitalNativeIssuerService as S


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C5H9_ORIGINAL_H4_FIXTURE_MISSING")
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


ORIGINAL_H4 = _load(
    "hospital_c5h9_original_h4_real_issuer_test",
    HERE / "test_hospital_c5_native_consent_hard_hold.py")


class C5H9RealC3eHospitalNonAdmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (sys.platform != "linux" or os.geteuid() != 0
                or os.environ.get("GITHUB_ACTIONS") != "true"
                or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
            raise RuntimeError("C5H9_DISPOSABLE_HOSTED_ROOT_LINUX_ONLY")

    def setUp(self):
        self.h4 = ORIGINAL_H4.NativeConsentHardHold(
            "test_02_valid_trash_and_polkit_success_still_hold")
        self.h4.setUp()
        self.reference = H.R.build_review(
            self.h4.request, self.h4.prepared, self.h4.policy,
            operator_uid=self.h4.policy["operatorUid"],
            seat_id="logind-seat0-c1",
            host_id=self.h4.policy["hostId"], now=self.h4.now)
        self.claim = {
            "schema": H.R.CLAIM_SCHEMA,
            "reviewDigest": self.reference["reviewDigest"],
            "requestNonce": self.h4.prepared["requestNonce"],
            "writerInstance": self.h4.prepared["writerInstance"],
            "action": self.h4.request["action"],
            "roomId": self.h4.request["roomId"],
            "operatorUid": self.h4.policy["operatorUid"],
            "seatId": "logind-seat0-c1",
            "hostId": self.h4.policy["hostId"],
            "agentReleaseDigest": "e" * 64,
            "claimedVisible": True,
            "claimedConfirmed": True,
            "shownAt": self.h4.now + 1,
            "confirmedAt": self.h4.now + 2,
        }

    def actual_c3e(self, *, op="CUSTODIAN_STATUS", expected=None,
                   actual=None, boundary=None):
        request = {
            "schema": H.M.P.SCHEMA, "op": op,
            "requestNonce": "c3" * 16,
        }
        frame = H.M.P.frame_ci_only(request) if expected is None else expected
        rx, tx = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        with rx, tx:
            rx.settimeout(0.5)
            rx.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
            body = frame if actual is None else actual
            self.assertEqual(tx.send(body), len(body))
            return H.M.inspect_ci_only(
                rx, expected_request_frame=frame,
                boundary=(H.M.P.S.TrustBoundary(
                    required_mode=H.M.P.S.PROTECTED_REQUIRED)
                    if boundary is None else boundary))

    def comparison(self, *, claim=None, identity=None, reference=None,
                   now=None):
        diag = H.R.inspect_untrusted_claim(
            self.reference if reference is None else reference,
            C.canonical(self.claim if claim is None else claim),
            now=self.h4.now + 3 if now is None else now)
        return H.compare_ci_only(
            self.actual_c3e() if identity is None else identity,
            self.reference if reference is None else reference, diag)

    def no_authority(self, report):
        self.assertEqual(report["schema"], H.SCHEMA)
        self.assertEqual(report["status"], H.STATUS)
        self.assertEqual(report["c3eStatus"], H.M.P.S.STATUS_HOLD)
        self.assertTrue(report["identityPacketObservedOnly"])
        self.assertEqual(report["next"],
                         "HOLD_UNTIL_INDEPENDENT_H0_C0_AND_PROTECTED_PX_W0_T0")
        self.assertEqual(set(report), {
            "schema", "status", "c3eStatus", "identityPacketObservedOnly",
            "untrustedDisplayClaimMatches", "reviewDigestLocalOnly",
            "next", "safeActions", *H.DENIED,
        })
        for flag in H.DENIED:
            self.assertIs(report[flag], False, flag)
        self.assertEqual(report["safeActions"], [])

    def test_01_real_c3e_kernel_packet_and_matching_claim_never_authorize(self):
        d = self.actual_c3e()
        self.assertEqual(d["kernelSenderPidObservedOnly"], os.getpid())
        self.assertEqual(d["localReadOnlyOperation"], "CUSTODIAN_STATUS")
        self.assertEqual(d["originalDiagnosticStatus"], H.M.P.S.STATUS_HOLD)
        self.assertFalse(d["humanConsentC5Verified"])
        result = self.comparison(identity=d)
        self.assertTrue(result["untrustedDisplayClaimMatches"])
        self.no_authority(result)

    def test_02_real_source_and_fake_human_claim_do_not_bypass_native_h4(self):
        self.no_authority(self.comparison())
        message, px_calls, polkit = self.h4.exercise()
        self.assertIn("INDEPENDENT_EXACT_ROOM_HUMAN_CONSENT_UNAVAILABLE", message)
        self.assertEqual(px_calls, ["prepare"])
        self.assertEqual(polkit, 1)

    def test_03_restore_still_cannot_sign_or_commit(self):
        self.h4.request["action"] = "RESTORE"
        self.h4.prepared.update(action="RESTORE", state="TRASHED",
                                canTrash=False, canRestore=True)
        self.reference = H.R.build_review(
            self.h4.request, self.h4.prepared, self.h4.policy,
            operator_uid=1000, seat_id="logind-seat0-c1",
            host_id="c" * 64, now=self.h4.now)
        self.claim.update(action="RESTORE",
                          reviewDigest=self.reference["reviewDigest"])
        self.no_authority(self.comparison())
        message, px_calls, polkit = self.h4.exercise()
        self.assertIn("INDEPENDENT_EXACT_ROOM_HUMAN_CONSENT_UNAVAILABLE", message)
        self.assertEqual(px_calls, ["prepare"])
        self.assertEqual(polkit, 1)

    def test_04_identity_diagnostic_claiming_signin_auth_is_rejected(self):
        d = self.actual_c3e()
        d["signInAllowed"] = True
        with self.assertRaisesRegex(C.Refused, "C5H9_C3E_CANNOT_ASSERT"):
            self.comparison(identity=d)

    def test_05_identity_diagnostic_claiming_current_custody_is_rejected(self):
        d = self.actual_c3e()
        d["independentlyCurrentIdentityHistory"] = True
        with self.assertRaisesRegex(C.Refused, "C5H9_C3E_CANNOT_ASSERT"):
            self.comparison(identity=d)

    def test_06_identity_diagnostic_extra_hospital_grant_field_refused(self):
        d = self.actual_c3e()
        d["hospitalCanTrash"] = True
        with self.assertRaisesRegex(C.Refused, "C5H9_C3E_CANNOT_ASSERT"):
            self.comparison(identity=d)

    def test_07_identity_local_snapshot_cannot_replace_protected_holding(self):
        d = self.actual_c3e()
        d["originalDiagnosticStatus"] = H.M.P.S.STATUS_LOCAL
        with self.assertRaisesRegex(C.Refused, "C5H9_C3E_CANNOT_ASSERT"):
            self.comparison(identity=d)

    def test_08_identity_readonly_operation_is_purpose_pinned(self):
        d = self.actual_c3e()
        d["localReadOnlyOperation"] = "SNAPSHOT"
        with self.assertRaisesRegex(C.Refused, "C5H9_C3E_CANNOT_ASSERT"):
            self.comparison(identity=d)

    def test_09_wrong_identity_operation_fails_in_original_adapter(self):
        with self.assertRaises(H.M.Refused):
            self.actual_c3e(op="BEGIN_SIGNIN")

    def test_10_real_identity_packet_mismatch_fails_kernel_comparison(self):
        other = H.M.P.frame_ci_only({
            "schema": H.M.P.SCHEMA, "op": "CUSTODIAN_STATUS",
            "requestNonce": "fe" * 16,
        })
        with self.assertRaisesRegex(H.M.Refused,
                                    "PACKET_OR_AUTHORITY_MISMATCH"):
            self.actual_c3e(actual=other)

    def test_11_claimed_hospital_seat_nonce_writer_changes_still_hold(self):
        for key, value in (
            ("seatId", "logind-seat1-c3"),
            ("requestNonce", C.b64(bytes(range(31, -1, -1)))),
            ("writerInstance", "protected-px-002"),
            ("action", "RESTORE"),
            ("claimedConfirmed", False),
        ):
            with self.subTest(key=key):
                claim = dict(self.claim, **{key: value})
                report = self.comparison(claim=claim)
                self.assertFalse(report["untrustedDisplayClaimMatches"])
                self.no_authority(report)

    def test_12_forged_release_hash_changes_no_human_proof(self):
        claim = dict(self.claim, agentReleaseDigest="0" * 64)
        result = self.comparison(claim=claim)
        self.assertTrue(result["untrustedDisplayClaimMatches"])
        self.no_authority(result)

    def test_13_spoofed_successful_human_verification_flag_refused(self):
        diag = H.R.inspect_untrusted_claim(
            self.reference, C.canonical(self.claim), now=self.h4.now + 3)
        diag["humanConsentVerified"] = True
        with self.assertRaisesRegex(C.Refused, "C5H9_UNTRUSTED_DISPLAY"):
            H.compare_ci_only(self.actual_c3e(), self.reference, diag)

    def test_14_spoofed_display_safe_actions_refused(self):
        diag = H.R.inspect_untrusted_claim(
            self.reference, C.canonical(self.claim), now=self.h4.now + 3)
        diag["safeActions"] = ["TRASH"]
        with self.assertRaisesRegex(C.Refused, "C5H9_UNTRUSTED_DISPLAY"):
            H.compare_ci_only(self.actual_c3e(), self.reference, diag)

    def test_15_spoofed_display_extra_signed_grant_refused(self):
        diag = H.R.inspect_untrusted_claim(
            self.reference, C.canonical(self.claim), now=self.h4.now + 3)
        diag["signedGrant"] = "fake"
        with self.assertRaisesRegex(C.Refused, "C5H9_UNTRUSTED_DISPLAY"):
            H.compare_ci_only(self.actual_c3e(), self.reference, diag)

    def test_16_claimed_positive_hospital_status_with_false_match_refused(self):
        diag = H.R.inspect_untrusted_claim(
            self.reference, C.canonical(self.claim), now=self.h4.now + 3)
        diag["claimMatchesReview"] = False
        with self.assertRaisesRegex(C.Refused,
                                    "C5H9_DISPLAY_STATUS_CONTRADICTS"):
            H.compare_ci_only(self.actual_c3e(), self.reference, diag)

    def test_17_changed_review_digest_source_refused(self):
        reference = dict(self.reference)
        reference["review"] = dict(reference["review"], writerInstance="protected-px-002")
        diag = H.R.inspect_untrusted_claim(
            self.reference, C.canonical(self.claim), now=self.h4.now + 3)
        with self.assertRaisesRegex(C.Refused,
                                    "C5H9_EXACT_REVIEW_REFERENCE_CHANGED"):
            H.compare_ci_only(self.actual_c3e(), reference, diag)

    def test_18_expired_untrusted_review_does_not_gain_authority(self):
        report = self.comparison(now=self.h4.prepared["expiresAt"])
        self.assertFalse(report["untrustedDisplayClaimMatches"])
        self.no_authority(report)

    def test_19_ci_admission_is_unconditionally_denied_with_any_inputs(self):
        for claim in ({}, {"signed": True, "c5_spent": True},
                      {"trusted_agent": object()}):
            with self.assertRaisesRegex(
                    C.Refused, "C5H9_NO_ENROLLED_HUMAN_CONSENT"):
                H.authorize_hospital_room(**claim)

    def test_20_non_ci_environment_never_invokes_original_c3e_adapter(self):
        rx, tx = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        with rx, tx:
            rx.settimeout(0.5)
            rx.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
            with mock.patch.object(H.M.os, "geteuid", return_value=1000):
                with self.assertRaisesRegex(
                        H.M.Refused, "C3E_IDENTITY_PACKET_HOSTED_ROOT_CI_ONLY"):
                    H.M.inspect_ci_only(
                        rx,
                        expected_request_frame=b"fake",
                        boundary=H.M.P.S.TrustBoundary(
                            required_mode=H.M.P.S.PROTECTED_REQUIRED))

    def test_21_actual_issuer_still_imports_no_ci_cross_origin_helper(self):
        text = (ROOT / "services/connections/hospital/"
                "HospitalNativeIssuerService.py").read_text()
        self.assertNotIn("HospitalC5H9C3eNegativeIntegration", text)
        self.assertNotIn("C3eIdentityPacketOriginNonAdmissionCI", text)
        self.assertNotIn("HospitalC5ExactConsentProbe", text)
        self.assertIn(
            'C.deny("INDEPENDENT_EXACT_ROOM_HUMAN_CONSENT_UNAVAILABLE")', text)
        start = text.index("def _native_step(client, policy):")
        body = text[start:]
        self.assertLess(
            body.index("_require_independent_room_consent(request, prepared, peer, first_seat)"),
            body.index("key = C.load_installed_key()"))
        self.assertLess(body.index("key = C.load_installed_key()"),
                        body.index('"kind": "commit"'))


if __name__ == "__main__":
    unittest.main(verbosity=2)
