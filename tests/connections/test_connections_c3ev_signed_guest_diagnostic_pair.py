#!/usr/bin/env python3
"""C3e-V: actual GPG-signed Q claim vs C4d/U diagnostic, denial-only.

All records and signing keys in this suite are disposable CI fixtures. A
matching pair does NOT establish a trusted guest signer or process authority.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "tests/connections/c3e_release_trust"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V = load("c3ev_pair", HERE / "C3eVSignedGuestDiagnosticPair.py")
QTEST = load("c3ev_qfixture", ROOT / "tests/connections/test_connections_c3eq_signed_guest_evidence.py")
AUTHORITY_FLAGS = (
    "externalIssuerCustodyVerified", "durableChallengeConsumptionVerified",
    "signedGuestOriginAuthenticated", "evidenceCryptographicallyAttested",
    "installedGuestMeasured", "hostAuthenticated", "canApprove",
    "credentialActionsEnabled", "productionAuthority",
)


class C3eVSignedPairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        QTEST.C3eQSignedEvidenceTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        QTEST.C3eQSignedEvidenceTests.tearDownClass()

    def setUp(self):
        self.fixture = QTEST.C3eQSignedEvidenceTests(
            "test_01_actual_detached_signed_test_report_and_one_use_receipt")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        self.guest = {
            "schema": V.U.SCHEMA,
            "signed_rpm_sha256": f.rpm,
            "signed_script_sha256": f.script,
            "running_script_sha256": f.script,
            "interpreter_sha256": f.interpreter,
            "service_pid": 4881,
            "dbus_owner_pid": 4881,
            "process_start_ticks": "991337",
            "service_uid": 997,
            "service_gid": 997,
            "systemd_unit": V.U.UNIT,
            "selinux_enforcing": True,
            "signedGuestOriginAuthenticated": False,
            "evidenceCryptographicallyAttested": False,
            "hostAuthenticated": False,
            "canApprove": False,
            "credentialActionsEnabled": False,
            "productionAuthority": False,
        }

    def line(self):
        return (V.U.PREFIX + json.dumps(
            self.guest, sort_keys=True,
            separators=(",", ":"), ensure_ascii=True).encode("ascii") + b"\n")

    def arguments(self):
        f = self.fixture
        return dict(
            diagnostic_line=self.line(), challenge=f.challenge,
            signed_evidence=f.report, signature=f.sig,
            public_key=f.pub, pinned_signer=f.fpr,
            expected_rpm_sha256=f.rpm,
            expected_script_sha256=f.script,
            expected_interpreter_sha256=f.interpreter,
            expected_service_pid=4881,
            expected_start_ticks="991337",
            expected_service_uid=997,
            expected_service_gid=997,
        )

    def run_pair(self, **changes):
        return V.inspect_pair(**{**self.arguments(), **changes})

    def refuse(self, expected, **changes):
        with self.assertRaises(V.Refused) as caught:
            self.run_pair(**changes)
        self.assertEqual(str(caught.exception), expected)

    def test_01_real_disposable_signed_and_plain_report_pair_never_grants(self):
        reply = self.run_pair()
        self.assertEqual(reply["schema"], V.SCHEMA)
        self.assertTrue(reply["signedClaimAndPlainGuestReportAgreeInCI"])
        self.assertTrue(reply["c3eqSignedClaimVerifiedInCI"])
        for field in AUTHORITY_FLAGS:
            with self.subTest(field=field):
                self.assertIs(reply[field], False)

    def test_02_guest_report_cannot_supply_independent_rpm_or_pid_pins(self):
        self.refuse("C4D_DIAGNOSTIC_REFUSED:"
                    "C4C_SIGNED_ARTIFACT_OR_RUNNING_BYTES_PIN_MISMATCH",
                    expected_rpm_sha256="d" * 64)
        self.refuse("C4D_DIAGNOSTIC_REFUSED:"
                    "C4C_SYSTEMD_DBUS_PROCESS_PIN_MISMATCH",
                    expected_service_pid=4882)

    def test_03_signed_message_with_different_uid_is_not_the_guest_record(self):
        self.fixture.data["service_uid"] = 998
        self.fixture._sign()
        self.refuse("SIGNED_CLAIM_AND_GUEST_REPORT_DISAGREE")

    def test_04_signed_message_with_different_gid_or_dbus_pid_refused(self):
        for name, value in (("service_gid", 998),
                            ("dbus_owner_pid", 4882)):
            with self.subTest(name=name):
                self.fixture.data[name] = value
                self.fixture._sign()
                # The second field also fails the Q protocol's own
                # supervisor-identity check before comparison.
                if name == "dbus_owner_pid":
                    self.refuse("C3EQ_SIGNED_CLAIM_REFUSED:"
                                "DBUS_SYSTEMD_PROCESS_MISMATCH")
                else:
                    self.refuse("SIGNED_CLAIM_AND_GUEST_REPORT_DISAGREE")
                self.fixture.data[name] = self.guest[name]

    def test_05_unsigned_tamper_and_wrong_signer_refused(self):
        self.fixture.report.write_bytes(b"tampered")
        self.refuse("C3EQ_SIGNED_CLAIM_REFUSED:SIGNED_EVIDENCE_CRYPTO_REFUSED")
        self.fixture._sign(signer=self.fixture.bad_home)
        self.refuse("C3EQ_SIGNED_CLAIM_REFUSED:SIGNED_EVIDENCE_CRYPTO_REFUSED")

    def test_06_wrong_challenge_or_signer_pin_is_not_acceptance(self):
        self.refuse("C3EQ_SIGNED_CLAIM_REFUSED:"
                    "CHALLENGE_NOT_BOUND_TO_SIGNED_EVIDENCE",
                    challenge=b"Z" * 32)
        self.refuse("C3EQ_SIGNED_CLAIM_REFUSED:"
                    "SIGNED_EVIDENCE_SIGNER_MISMATCH",
                    pinned_signer=self.fixture.bad_fpr)

    def test_07_guest_cannot_claim_auth_or_exceed_single_line(self):
        self.guest["hostAuthenticated"] = True
        self.refuse("C4D_DIAGNOSTIC_REFUSED:C4C_CLAIMED_UNAUTHORIZED_AUTHORITY")
        self.guest["hostAuthenticated"] = False
        self.refuse("C4D_DIAGNOSTIC_REFUSED:"
                    "C4C_LINE_PREFIX_OR_DELIMITER_REFUSED",
                    diagnostic_line=self.line() + self.line())

    def test_08_signed_production_claim_stays_refused(self):
        self.fixture.data["canApprove"] = True
        self.fixture._sign()
        self.refuse("C3EQ_SIGNED_CLAIM_REFUSED:EVIDENCE_CLAIMS_AUTHORITY")

    def test_09_identity_gateway_role_is_not_connections_guest_role(self):
        self.guest["systemd_unit"] = "post-apollo-identity-silverblue-ci.service"
        self.refuse("C4D_DIAGNOSTIC_REFUSED:C4C_ROLE_OR_SELINUX_REFUSED")
        self.guest["systemd_unit"] = V.U.UNIT
        self.fixture.data["guest_provenance"] = "identity-gateway-silverblue"
        self.fixture._sign()
        self.refuse("C3EQ_SIGNED_CLAIM_REFUSED:EVIDENCE_ROLE_OR_DOMAIN_REFUSED")

    def test_10_changed_preverified_snapshot_never_matches_signed_digest(self):
        # Simulates the file changing between the first snapshot and Q's
        # separate real verification; never parse the wrong snapshot.
        original = V.Q.safe_bytes
        calls = [0]

        def first_snapshot_differs(path, ceiling, code):
            raw = original(path, ceiling, code)
            calls[0] += 1
            if calls[0] == 1:
                return raw + b" "
            return raw

        with mock.patch.object(V.Q, "safe_bytes", first_snapshot_differs):
            self.refuse("VERIFIED_SIGNED_SNAPSHOT_DISAGREES")
        self.assertGreaterEqual(calls[0], 2)

    def test_11_no_reopening_caller_path_after_signature_verification(self):
        # Replacing the caller's path after successful signature check
        # cannot change the previously captured, verified byte snapshot.
        real = V.Q.OneUseTestChallenge.verify
        signed_file = self.fixture.report

        def change_after_verify(verifier, **kwargs):
            reply = real(verifier, **kwargs)
            signed_file.write_bytes(b"untrusted replacement after verification")
            return reply

        with mock.patch.object(V.Q.OneUseTestChallenge,
                               "verify", change_after_verify):
            reply = self.run_pair()
        self.assertTrue(reply["signedClaimAndPlainGuestReportAgreeInCI"])
        for key in AUTHORITY_FLAGS:
            self.assertIs(reply[key], False)

    def test_12_missing_independent_key_material_refuses(self):
        self.refuse("C3EQ_SIGNED_CLAIM_REFUSED:PINNED_TEST_SIGNER_INVALID",
                    pinned_signer="")
        self.refuse("C4D_DIAGNOSTIC_REFUSED:INDEPENDENT_HASH_PIN_INVALID",
                    expected_interpreter_sha256="")

    def test_13_no_broker_activation_or_alternate_identity_bridge(self):
        source = (HERE / "C3eVSignedGuestDiagnosticPair.py").read_text()
        for forbidden in ("ConnectionsBroker.qml", "SignedIdentityCommandClient",
                          "InstalledIdentityCommandAdapterV1",
                          "subprocess.run(", "socket.socket("):
            self.assertNotIn(forbidden, source)
        broker = (ROOT / "services/connections/ConnectionsBroker.qml").read_text()
        self.assertIn("readonly property bool credentialActionsEnabled: false",
                      broker)
        for field in AUTHORITY_FLAGS:
            self.assertIn('"' + field + '": False', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
