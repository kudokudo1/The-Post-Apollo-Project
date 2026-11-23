#!/usr/bin/env python3
"""DOC 1 real Linux peer-credential negative matrix. No authority or daemon."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tests/connections/c3e_release_trust/C3eUnixPeerCredentialsNegativeCI.py"
spec = importlib.util.spec_from_file_location("c3e_peer_negative_ci", SOURCE)
if spec is None or spec.loader is None:
    raise RuntimeError("C3E_PEER_TEST_SOURCE_MISSING")
M = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = M
spec.loader.exec_module(M)


class KernelPeerObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Real kernel test: two forked, UID-dropped Linux children.
        cls.inherited = M.inherited_socketpair_ci_only()
        cls.accepted = M.fresh_accepted_connection_ci_only()

    def assert_denied(self, value):
        self.assertEqual(value["schema"], M.SCHEMA)
        for key in M.DENIED:
            self.assertIs(value[key], False, key)
        self.assertNotIn("canBeginSignIn", value.keys() - M.DENIED.keys())

    def test_01_inherited_socketpair_reports_original_creator(self):
        report = self.inherited
        self.assertEqual(report["status"], M.CREATOR_NOT_SENDER)
        self.assertEqual(report["socketPeerPid"], report["socketCreationPid"])
        self.assert_denied(report)

    def test_02_inherited_socketpair_sender_is_different_real_pid(self):
        report = self.inherited
        self.assertNotEqual(report["socketPeerPid"], report["childSenderPid"])
        self.assertIs(report["socketPeerIdentityMatchesSender"], False)
        self.assert_denied(report)

    def test_03_inherited_root_socket_peer_uid_does_not_follow_setuid(self):
        report = self.inherited
        self.assertEqual(report["socketPeerUid"], 0)
        self.assertEqual(report["childSenderExpectedUid"], M.NOBODY_UID)
        self.assertNotEqual(report["socketPeerUid"],
                            report["childSenderExpectedUid"])
        self.assert_denied(report)

    def test_04_inherited_kernel_credential_observation_still_holds(self):
        self.assert_denied(
            M.assert_observation_not_authority_ci_only(self.inherited))

    def test_05_fresh_accepted_peer_matches_child_pid(self):
        report = self.accepted
        self.assertEqual(report["status"], M.ACCEPTED_PEER_ONLY)
        self.assertEqual(report["acceptedPeerPid"], report["childSenderPid"])
        self.assertIs(report["socketPeerIdentityMatchesSender"], True)
        self.assert_denied(report)

    def test_06_fresh_accepted_connection_sees_unprivileged_uid(self):
        report = self.accepted
        self.assertEqual(report["acceptedPeerUid"], M.NOBODY_UID)
        self.assert_denied(report)

    def test_07_correct_kernel_peer_is_not_trust_enrollment(self):
        out = M.assert_observation_not_authority_ci_only(self.accepted)
        self.assertEqual(out["status"], M.NOT_AUTHORITY)
        self.assert_denied(out)

    def test_08_both_kernel_observation_modes_prohibit_credentials(self):
        for report in (self.inherited, self.accepted):
            self.assertIs(report["credentialActionsEnabled"], False)
            self.assertIs(report["productionAuthority"], False)
            self.assertIs(report["hostAuthenticated"], False)
            self.assertIs(report["realReleaseAttested"], False)
            self.assertIs(report["activeSeatAuthenticated"], False)
            self.assertIs(report["protectedCustodianEnrolled"], False)

    def test_09_both_observations_refuse_production_admission(self):
        with self.assertRaisesRegex(M.Refused, "NEVER_GRANTS_HOST"):
            M.production_admission(self.inherited)
        with self.assertRaisesRegex(M.Refused, "NEVER_GRANTS_HOST"):
            M.production_admission(self.accepted)

    def test_10_test_fixture_disabled_without_hosted_runner(self):
        with mock.patch.dict(os.environ, {"RUNNER_ENVIRONMENT": "self-hosted"}):
            with self.assertRaisesRegex(M.Refused, "DISPOSABLE_HOSTED"):
                M._guard()

    def test_11_test_fixture_disabled_without_github_ci(self):
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}):
            with self.assertRaisesRegex(M.Refused, "DISPOSABLE_HOSTED"):
                M._guard()

    def test_12_caller_forced_host_grant_refused(self):
        fake = dict(self.accepted, hostAuthenticated=True)
        with self.assertRaisesRegex(M.Refused, "AUTHORITY_PROMOTION"):
            M.assert_observation_not_authority_ci_only(fake)

    def test_13_extra_fake_service_claim_refused(self):
        fake = dict(self.inherited, trustedRemoteService=True)
        with self.assertRaisesRegex(M.Refused, "OBSERVATION_FIELDS"):
            M.assert_observation_not_authority_ci_only(fake)

    def test_14_spoofed_socketpair_sender_pid_as_creator_refused(self):
        fake = dict(self.inherited,
                    childSenderPid=self.inherited["socketPeerPid"])
        with self.assertRaisesRegex(M.Refused, "CREATOR_MISMATCH"):
            M.assert_observation_not_authority_ci_only(fake)

    def test_15_boolean_kernel_pid_refused(self):
        fake = dict(self.inherited, socketPeerPid=True)
        with self.assertRaisesRegex(M.Refused, "CREATOR_MISMATCH"):
            M.assert_observation_not_authority_ci_only(fake)

    def test_16_forged_accepted_peer_pid_refused(self):
        fake = dict(self.accepted, acceptedPeerPid=123456789)
        with self.assertRaisesRegex(M.Refused, "ACCEPTED_MATCH_INVALID"):
            M.assert_observation_not_authority_ci_only(fake)

    def test_17_forged_purpose_status_refused(self):
        fake = dict(self.accepted, status="C3E_HOST_AUTHENTICATED")
        with self.assertRaises(M.Refused):
            M.assert_observation_not_authority_ci_only(fake)

    def test_18_fake_protected_history_false_to_true_refused(self):
        fake = dict(self.accepted, independentCurrentHistoryVerified=True)
        with self.assertRaisesRegex(M.Refused, "AUTHORITY_PROMOTION"):
            M.assert_observation_not_authority_ci_only(fake)

    def test_19_missing_kernel_observation_refused(self):
        fake = dict(self.inherited)
        fake.pop("socketPeerPid")
        with self.assertRaisesRegex(M.Refused, "OBSERVATION_FIELDS"):
            M.assert_observation_not_authority_ci_only(fake)

    def test_20_unknown_server_signer_or_seat_cannot_be_inferred(self):
        for report in (self.inherited, self.accepted):
            self.assertNotIn("signedReleaseFingerprint", report)
            self.assertNotIn("operatorRoot", report)
            self.assertNotIn("seatSession", report)
            self.assertNotIn("trustAnchor", report)
            self.assert_denied(report)


if __name__ == "__main__":
    unittest.main(verbosity=2)
