#!/usr/bin/env python3
"""Denial-only Hospital staffing uncertain-COMMIT outcome policy tests."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import unittest

if (os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("CI") != "true"
        or not os.environ.get("RUNNER_TEMP")
        or not Path(os.environ["RUNNER_TEMP"]).is_dir()
        or not sys.platform.startswith("linux")):
    raise SystemExit("STAFFING_UNKNOWN_COMMIT_GITHUB_CI_ONLY")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/connections/hospital/staffing"))
sys.path.insert(0, str(ROOT / "tests/connections"))
sys.path.insert(0, str(ROOT / "hospital-source/bin"))
import StaffingUnknownCommitPreflight as U
import StaffingTransportPreflight as T
import test_connections_hospital_staffing_receipt_identity_preflight as ReceiptFixtureModule


class UnknownCommitPreflightTests(unittest.TestCase):
    def setUp(self):
        fixture = ReceiptFixtureModule.StaffingReceiptIdentityTests("test_02_valid_fixture_is_never_native")
        fixture.setUp()
        self.fixture = fixture
        self.base = dict(
            original_prepare_raw=fixture.original_raw,
            prepared_raw=fixture.prepared_raw,
            commit_raw=fixture.commit_raw,
        )

    def check(self, stage=U.ATTEMPTED, observation="TIMEOUT", **changes):
        return U.inspect_unknown_commit_ci_only(
            **{**self.base, "stage": stage, "observation": observation,
               **changes})

    def refused(self, reason, **kwargs):
        with self.assertRaisesRegex(U.UnknownCommitHold, reason):
            self.check(**kwargs)

    def assert_no_authority(self, out):
        self.assertTrue(out["neverAutoRetryThisGrant"])
        self.assertEqual(out["status"], U.STATUS)
        for key in U.DENIED:
            self.assertIs(out[key], False, key)

    def test_01_local_composition_refusal_never_grants_or_retries(self):
        out = self.check(U.LOCAL, "COMPOSITION_REFUSED")
        self.assert_no_authority(out)
        self.assertFalse(out["manualHospitalReconciliationNeededInCI"])
        self.assertEqual(out["uncertainty"], "NO_SEND_OBSERVED_IN_CALLER_CI_TRACE")

    def test_02_local_scope_refusal_never_grants(self):
        self.assert_no_authority(self.check(U.LOCAL, "LOCAL_SCOPE_REFUSED"))

    def test_03_cancelled_before_send_never_grants(self):
        self.assert_no_authority(self.check(U.LOCAL, "CANCELLED_BEFORE_SEND"))

    def test_04_all_post_send_errors_remain_ambiguous(self):
        for observation in sorted(U.ALLOWED_OBSERVATIONS[U.ATTEMPTED]):
            with self.subTest(observation=observation):
                out = self.check(U.ATTEMPTED, observation)
                self.assert_no_authority(out)
                self.assertTrue(out["manualHospitalReconciliationNeededInCI"])
                self.assertEqual(
                    out["uncertainty"], "POST_SEND_UNKNOWN_MAY_HAVE_COMMITTED")

    def test_05_unverified_committed_claim_never_commits(self):
        out = self.check(U.RESPONSE, "RESPONSE_BYTES_OBSERVED",
                         unverified_response_raw=b'{"status":"COMMITTED"}')
        self.assert_no_authority(out)
        self.assertTrue(out["manualHospitalReconciliationNeededInCI"])

    def test_06_unverified_refused_claim_cannot_prove_refusal(self):
        out = self.check(U.RESPONSE, "RESPONSE_BYTES_OBSERVED",
                         unverified_response_raw=b'{"status":"REFUSED"}')
        self.assert_no_authority(out)

    def test_07_unverified_already_applied_claim_cannot_prove_replay(self):
        out = self.check(U.RESPONSE, "RESPONSE_BYTES_OBSERVED",
                         unverified_response_raw=b'{"status":"ALREADY_APPLIED"}')
        self.assert_no_authority(out)

    def test_08_arbitrary_binary_reply_is_not_a_writer_receipt(self):
        out = self.check(U.RESPONSE, "RESPONSE_BYTES_OBSERVED",
                         unverified_response_raw=b"\xff"*51)
        self.assert_no_authority(out)

    def test_09_repeat_check_never_consumes_grant(self):
        first = self.check()
        second = self.check()
        self.assertEqual(first, second)
        self.assert_no_authority(second)

    def test_10_unrecognized_stage_refused(self):
        for stage in ("COMMITTED", "REFUSED", "RETRY", "NATIVE", "", None, True):
            with self.subTest(stage=stage):
                self.refused("UNRECOGNIZED_STAGE_OR_OBSERVATION", stage=stage)

    def test_11_cross_stage_observation_refused(self):
        for stage, obs in (
            (U.LOCAL, "TIMEOUT"),
            (U.ATTEMPTED, "COMPOSITION_REFUSED"),
            (U.RESPONSE, "TIMEOUT"),
            (U.ATTEMPTED, "RESPONSE_BYTES_OBSERVED"),
            (U.RESPONSE, "COMMITTED"),
        ):
            with self.subTest(stage=stage, obs=obs):
                self.refused("UNRECOGNIZED_STAGE_OR_OBSERVATION",
                             stage=stage, observation=obs)

    def test_12_bool_or_nonstring_observation_refused(self):
        for value in (True, 123, None, {}, [], b"TIMEOUT"):
            with self.subTest(value=value):
                self.refused("UNRECOGNIZED_STAGE_OR_OBSERVATION",
                             observation=value)

    def test_13_response_stage_requires_bytes(self):
        for payload in (None, "", "COMMITTED", {}, [], 1, True):
            with self.subTest(payload=payload):
                self.refused("BOUNDED_RESPONSE_BYTES_REQUIRED", stage=U.RESPONSE,
                             observation="RESPONSE_BYTES_OBSERVED",
                             unverified_response_raw=payload)

    def test_14_empty_response_refused(self):
        self.refused("BOUNDED_RESPONSE_BYTES_REQUIRED", stage=U.RESPONSE,
                     observation="RESPONSE_BYTES_OBSERVED",
                     unverified_response_raw=b"")

    def test_15_oversized_response_refused(self):
        self.refused("BOUNDED_RESPONSE_BYTES_REQUIRED", stage=U.RESPONSE,
                     observation="RESPONSE_BYTES_OBSERVED",
                     unverified_response_raw=b"x"*(U.MAX_REPLY_BYTES+1))

    def test_16_exact_bound_response_still_unverified(self):
        out = self.check(U.RESPONSE, "RESPONSE_BYTES_OBSERVED",
                         unverified_response_raw=b"x"*U.MAX_REPLY_BYTES)
        self.assert_no_authority(out)

    def test_17_unexpected_response_bytes_in_other_stages_refused(self):
        for stage, obs in ((U.LOCAL, "COMPOSITION_REFUSED"),
                           (U.ATTEMPTED, "TIMEOUT")):
            with self.subTest(stage=stage):
                self.refused("RESPONSE_BYTES_IN_WRONG_STAGE",stage=stage,
                             observation=obs,unverified_response_raw=b"COMMITTED")

    def test_18_changed_original_request_refused(self):
        modified = dict(self.fixture.original, requestNonce="Q"*43)
        self.refused("UNTRUSTED_REQUEST_CONTEXT_REFUSED",
                     original_prepare_raw=T.canonical(modified))

    def test_19_changed_prepared_writer_refused(self):
        altered = dict(self.fixture.prepared,writerInstance="foreign-writer-001")
        self.refused("UNTRUSTED_REQUEST_CONTEXT_REFUSED",
                     prepared_raw=T.canonical(altered))

    def test_20_forged_commit_action_refused(self):
        changed = dict(json.loads(self.fixture.commit_raw), action="DOCTOR_SUCCEED")
        self.refused("UNTRUSTED_REQUEST_CONTEXT_REFUSED",
                     commit_raw=T.canonical(changed))

    def test_21_changed_prepared_graph_refused(self):
        changed = dict(self.fixture.prepared, expectedDigest="f"*64)
        self.refused("UNTRUSTED_REQUEST_CONTEXT_REFUSED",
                     prepared_raw=T.canonical(changed))

    def test_22_response_hash_is_diagnostic_not_permission(self):
        output=self.check(U.RESPONSE,"RESPONSE_BYTES_OBSERVED",
                          unverified_response_raw=b'{"permission":true}')
        self.assertEqual(len(output["unverifiedResponseSha256"]),64)
        self.assert_no_authority(output)

    def test_23_native_recovery_remains_disabled(self):
        with self.assertRaisesRegex(U.UnknownCommitHold,
                                    "NATIVE_HOSPITAL_WRITER_RECOVERY_NOT_INSTALLED"):
            U.run_native_staffing_recovery(signedApproval=True)

    def test_24_no_status_promoted_to_verified_writer_state(self):
        for stage, obs in ((U.LOCAL,"LOCAL_SCOPE_REFUSED"),
                           (U.ATTEMPTED,"DISCONNECT"),
                           (U.RESPONSE,"RESPONSE_BYTES_OBSERVED")):
            with self.subTest(stage=stage):
                args={"unverified_response_raw":b'{"status":"COMMITTED"}'} if stage==U.RESPONSE else {}
                out=self.check(stage,obs,**args)
                self.assert_no_authority(out)
                self.assertNotIn(out["uncertainty"],
                                 ("COMMITTED", "REFUSED", "ALREADY_APPLIED"))
                self.assertFalse(out["canReplayCommit"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
