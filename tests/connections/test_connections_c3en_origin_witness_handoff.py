#!/usr/bin/env python3
"""C3e-N: two distinct installed-service and root-witness *test* boundaries.

The C3b/C4b origin snapshot is an offline fixture. Its data are NOT
authenticated simply by passing this contract. The positive Linux peer
integration uses C3e-L's real AF_UNIX kernel identity tests in disposable CI.
"""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tests/connections/c3e_release_trust/C3eNOriginWitnessHandoff.py"
CTEST = ROOT / "tests/connections/test_connections_c3b_origin.py"
LTEST = ROOT / "tests/connections/test_connections_c3el_host_status_observation.py"


def load(filename, name):
    spec = importlib.util.spec_from_file_location(name, filename)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


N = load(SOURCE, "c3en_handoff")
C = load(CTEST, "c3en_c3b_fixtures")
L = load(LTEST, "c3en_c3el_real")


class C3eNOriginWitnessContract(unittest.TestCase):
    def setUp(self):
        self.snapshot, self.opt = C.C3bOriginPolicyTests("test_10a_c4b_canonical_opt_is_only_exception")._c4b_opt_snapshot()
        self.sha = "a" * 64
        self.status = {
            "schema": "postapollo.connections.c3el.host-observation.v1",
            "transport_peer_verified": True,
            "host_uid_observed": 0,
            "observed_policy_epoch": 4,
            "observed_release_sequence": 9,
            "enrollment_sha256": self.sha,
            "hostAuthenticated": False,
            "canApprove": False,
            "credentialActionsEnabled": False,
            "productionAuthority": False,
        }
        self.params = {
            "installed_os_evidence": self.snapshot,
            "c4b_opt_proof": self.opt,
            "read_only_witness_status": self.status,
            "expected_installed_pid": 4567,
            "expected_witness_pid": 8765,
            "expected_witness_enrollment_sha256": self.sha,
            "minimum_policy_epoch": 4,
            "minimum_release_sequence": 9,
        }

    def evaluate(self, **changes):
        args = {**self.params, **changes}
        return N.inspect(**args)

    def denied(self, reason, **changes):
        result = self.evaluate(**changes)
        self.assertEqual(result["status"], reason, result)
        self.assertFalse(result["testEvidenceCompatible"])
        for name in ("hostAuthenticated", "canApprove",
                     "credentialActionsEnabled", "productionAuthority"):
            self.assertIs(result[name], False)
        self.assertEqual(result["installed_status_service_pid"], 0)
        self.assertEqual(result["separate_witness_process_pid"], 0)

    def test_01_coherent_two_process_fixture_is_not_authentication(self):
        result = self.evaluate()
        self.assertEqual(result["status"], N.STATUS)
        self.assertTrue(result["testEvidenceCompatible"])
        self.assertNotEqual(result["installed_status_service_pid"],
                            result["separate_witness_process_pid"])
        self.assertEqual(result["witness_floor_epoch"], 4)
        self.assertEqual(result["witness_floor_sequence"], 9)
        self.assertFalse(result["hostAuthenticated"])
        self.assertFalse(result["canApprove"])
        self.assertFalse(result["credentialActionsEnabled"])
        self.assertFalse(result["productionAuthority"])

    def test_02_real_nonroot_kernel_client_to_root_witness_input(self):
        if os.geteuid() != 0:
            self.skipTest("real separate-UID process test requires disposable sudo CI")
        # Reusing L's subprocess fixture directly (outside its unittest
        # runner) requires the parent K fixture class initialization.
        L.C3eLHostStatusObservationTests.setUpClass()
        fx = L.C3eLHostStatusObservationTests(
            "test_01_reverse_kernel_host_identity_and_floor_observed")
        fx.setUp()
        self.addCleanup(fx.doCleanups)
        client = fx._start_client()
        host = fx.fx._server(client)
        pins = fx._pins(host)
        actual = fx._ask(client, pins)["evidence"]
        actual_os = deepcopy(self.snapshot)
        fake_status_pid = host.pid + 10000
        actual_os["bus_pid"] = fake_status_pid
        actual_os["main_pid"] = fake_status_pid
        result = self.evaluate(
            installed_os_evidence=actual_os,
            expected_installed_pid=fake_status_pid,
            read_only_witness_status=actual,
            expected_witness_pid=host.pid,
            expected_witness_enrollment_sha256=pins["expected_enrollment_sha256"])
        self.assertEqual(result["status"], N.STATUS)
        self.assertTrue(result["testEvidenceCompatible"])
        self.assertEqual(host.wait(timeout=5), 0)
        self.assertFalse(result["hostAuthenticated"])

    def test_03_os_status_wrong_dbus_pid_refuses(self):
        bad = deepcopy(self.snapshot)
        bad["bus_pid"] += 1
        self.denied("C3EN_INSTALLED_ORIGIN_REFUSED",
                    installed_os_evidence=bad)

    def test_04_os_status_valid_but_different_expected_pid_refuses(self):
        self.denied("C3EN_INSTALLED_PID_CHANGED",
                    expected_installed_pid=4590)

    def test_05_missing_or_wrong_c4b_link_proof_refuses(self):
        for proof in (None, {}, {"before": self.opt["before"]}):
            with self.subTest(proof=repr(proof)[:40]):
                self.denied("C3EN_INSTALLED_ORIGIN_REFUSED",
                            c4b_opt_proof=proof)

    def test_06_installed_service_unit_changed_refuses(self):
        changed = deepcopy(self.snapshot)
        changed["unit_fragment"] = "/tmp/not-installed.service"
        self.denied("C3EN_INSTALLED_ORIGIN_REFUSED",
                    installed_os_evidence=changed)

    def test_07_non_enforcing_selinux_refuses(self):
        changed = deepcopy(self.snapshot)
        changed["kernel_enforcing"] = "0"
        self.denied("C3EN_INSTALLED_ORIGIN_REFUSED",
                    installed_os_evidence=changed)

    def test_08_untrusted_install_parent_directory_refuses(self):
        changed = deepcopy(self.snapshot)
        changed["protected_dirs"]["/opt"]["owner"] = 1000
        self.denied("C3EN_INSTALLED_ORIGIN_REFUSED",
                    installed_os_evidence=changed)

    def test_09_witness_missing_or_extra_field_refuses(self):
        for status in (None, {}, {**self.status, "grantActive": True}):
            with self.subTest(status=repr(status)[:35]):
                self.denied("C3EN_WITNESS_STATUS_UNTRUSTED",
                            read_only_witness_status=status)

    def test_10_witness_claims_approval_refuses(self):
        for k in ("hostAuthenticated", "canApprove",
                  "credentialActionsEnabled", "productionAuthority"):
            changed = {**self.status, k: True}
            with self.subTest(field=k):
                self.denied("C3EN_WITNESS_STATUS_UNTRUSTED",
                            read_only_witness_status=changed)

    def test_11_client_flag_cannot_be_integer_one(self):
        changed = {**self.status, "host_uid_observed": True}
        self.denied("C3EN_WITNESS_STATUS_UNTRUSTED",
                    read_only_witness_status=changed)
        changed = {**self.status, "transport_peer_verified": 1}
        self.denied("C3EN_WITNESS_STATUS_UNTRUSTED",
                    read_only_witness_status=changed)

    def test_12_stale_witness_release_floor_refuses(self):
        self.denied("C3EN_WITNESS_FLOOR_OR_ENROLLMENT_REFUSED",
                    minimum_release_sequence=10)
        changed = {**self.status, "observed_policy_epoch": 3}
        self.denied("C3EN_WITNESS_FLOOR_OR_ENROLLMENT_REFUSED",
                    read_only_witness_status=changed)

    def test_13_mismatched_witness_enrollment_refuses(self):
        self.denied("C3EN_WITNESS_FLOOR_OR_ENROLLMENT_REFUSED",
                    expected_witness_enrollment_sha256="b" * 64)

    def test_14_bool_and_negative_floor_are_not_valid_evidence(self):
        for k, value in (
            ("minimum_policy_epoch", True),
            ("minimum_release_sequence", 0),
            ("expected_installed_pid", False),
            ("expected_witness_pid", -1),
        ):
            with self.subTest(field=k):
                self.denied("C3EN_INVALID_TEST_PINS", **{k: value})
        changed = {**self.status, "observed_release_sequence": True}
        self.denied("C3EN_WITNESS_FLOOR_OR_ENROLLMENT_REFUSED",
                    read_only_witness_status=changed)

    def test_15_one_pid_cannot_identify_both_separate_processes(self):
        self.denied("C3EN_INVALID_TEST_PINS",
                    expected_witness_pid=self.params["expected_installed_pid"])

    def test_16_wrong_witness_uid_or_schema_refuses(self):
        for k, value in (("host_uid_observed", 1000),
                         ("schema", "postapollo.connections.fake.v1"),
                         ("transport_peer_verified", False)):
            with self.subTest(field=k):
                self.denied("C3EN_WITNESS_STATUS_UNTRUSTED",
                            read_only_witness_status={**self.status, k: value})

    def test_17_no_promotion_to_production_or_provider_grants(self):
        qml = ROOT / "services/connections"
        self.assertIn("readonly property bool credentialActionsEnabled: false",
                      (qml / "ConnectionsBroker.qml").read_text())
        self.assertIn("readonly property bool hostAuthenticated: false",
                      (qml / "ConnectionsRequestStatus.qml").read_text())
        for path in (*qml.glob("*.qml"), *qml.glob("*.js"), qml / "qmldir"):
            self.assertNotIn("C3eNOriginWitnessHandoff", path.read_text())

    def test_18_untrusted_status_claim_is_not_an_installed_origin(self):
        for v in (None, "", "C3B_OS_ORIGIN_COHERENT_TEST_ONLY", {"status": "C3B_OS_ORIGIN_COHERENT_TEST_ONLY"}):
            with self.subTest(value=repr(v)):
                self.denied("C3EN_INSTALLED_ORIGIN_REFUSED",
                            installed_os_evidence=v)

    def test_19_testing_two_host_boundaries_cannot_authorize_any_operation(self):
        result = self.evaluate()
        self.assertEqual(set(result), {
            "schema", "status", "installed_status_service_pid",
            "separate_witness_process_pid", "witness_floor_epoch",
            "witness_floor_sequence", "testEvidenceCompatible",
            "hostAuthenticated", "canApprove", "credentialActionsEnabled",
            "productionAuthority",
        })
        self.assertNotIn("allowed", result)
        self.assertNotIn("credential", result)
        self.assertNotIn("grant", result)
        self.assertNotIn("approvalToken", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
