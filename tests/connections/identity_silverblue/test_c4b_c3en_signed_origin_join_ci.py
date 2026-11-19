#!/usr/bin/env python3
"""Cross-owner C4b / existing C3e-N CI source composition and refusal."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import c4b_c3en_signed_origin_join_ci as J
import test_c4b_witness_transport_consumer_ci as C4B

C3EN_TEST = ROOT / "tests/connections/test_connections_c3en_origin_witness_handoff.py"


def _load_existing_test():
    spec = importlib.util.spec_from_file_location("c4b_original_c3en_test", C3EN_TEST)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


C3EN = _load_existing_test()


class C4bC3eNSignedOriginJoinTests(unittest.TestCase):
    def setUp(self):
        self.c4b = C4B.WitnessUnixPeerTests(
            "test_01_nonroot_real_socket_peer_and_signed_witness_match")
        self.c4b.setUp()
        self.addCleanup(self.c4b.doCleanups)

        self.c3e = C3EN.C3eNOriginWitnessContract(
            "test_01_coherent_two_process_fixture_is_not_authentication")
        self.c3e.setUp()
        self.addCleanup(self.c3e.doCleanups)
        self.state = self.c4b.fixture._state()
        self.c3e.status["observed_policy_epoch"] = self.state["minimumReleaseEpoch"]
        self.c3e.status["observed_release_sequence"] = self.state[
            "minimumReleaseSequence"]

    def args(self, **overrides):
        c3e = dict(self.c3e.params)
        del c3e["minimum_policy_epoch"]
        del c3e["minimum_release_sequence"]
        args = {**self.c4b.args(), **c3e}
        args.update(overrides)
        return args

    def good(self, **changes):
        return J.inspect_ci_only(**self.args(**changes))

    def deny(self, **changes):
        with self.assertRaises(J.Refused):
            self.good(**changes)

    def test_01_real_nonroot_signed_witness_and_original_c3en_compatible(self):
        self.c4b.server()
        result = self.good()
        self.assertEqual(result["status"], J.STATUS)
        self.assertTrue(result["threeDistinctProcessPinsComparedInCI"])
        self.assertTrue(result["signedCheckpointAndOriginalC3eFloorsMatchInCI"])
        self.assertEqual(result["controllerHostId"], self.state["hostId"])
        self.assertEqual(result["matchingFloorEpoch"],
                         self.state["minimumReleaseEpoch"])
        self.assertEqual(result["matchingFloorSequence"],
                         self.state["minimumReleaseSequence"])
        self.assertTrue(all(x is False for x in J.NEGATIVE.values()))

    def test_02_c3en_higher_floor_rejects_stale_c4b_signed_release(self):
        self.c4b.server()
        status = dict(self.c3e.status)
        status["observed_release_sequence"] += 1
        self.deny(read_only_witness_status=status)

    def test_03_c3en_lower_floor_rejects_stale_protected_witness(self):
        self.c4b.server()
        status = dict(self.c3e.status)
        status["observed_release_sequence"] -= 1
        self.deny(read_only_witness_status=status)

    def test_04_c3en_policy_epoch_mismatch_refuses(self):
        self.c4b.server()
        status = dict(self.c3e.status)
        status["observed_policy_epoch"] += 1
        self.deny(read_only_witness_status=status)

    def test_05_real_c4b_peer_pid_mismatch_refuses(self):
        self.c4b.server()
        self.deny(separately_pinned_peer_pid=self.c4b.server_pid + 1)

    def test_06_separate_protected_witness_and_c4b_signer_pid_required(self):
        self.c4b.server()
        self.deny(expected_witness_pid=self.c4b.server_pid)

    def test_07_installed_service_and_c4b_signer_pid_must_differ(self):
        self.c4b.server()
        self.deny(expected_installed_pid=self.c4b.server_pid)

    def test_08_protected_c3en_requires_distinct_two_original_pids(self):
        self.c4b.server()
        self.deny(expected_installed_pid=self.c3e.params["expected_witness_pid"])

    def test_09_forged_original_c3en_status_claim_cannot_replace_evidence(self):
        self.c4b.server()
        self.deny(installed_os_evidence={
            "status": "C3B_OS_ORIGIN_COHERENT_TEST_ONLY"})

    def test_10_original_c3b_selinux_enforcing_policy_is_not_bypassed(self):
        self.c4b.server()
        fake = deepcopy(self.c3e.snapshot)
        fake["kernel_enforcing"] = "0"
        self.deny(installed_os_evidence=fake)

    def test_11_original_c3b_installed_unit_policy_is_not_bypassed(self):
        self.c4b.server()
        fake = deepcopy(self.c3e.snapshot)
        fake["unit_fragment"] = "/tmp/forged.service"
        self.deny(installed_os_evidence=fake)

    def test_12_original_c3en_prohibits_witness_claimed_authority(self):
        self.c4b.server()
        status = dict(self.c3e.status)
        status["hostAuthenticated"] = True
        self.deny(read_only_witness_status=status)

    def test_13_original_c3en_requires_correct_enrollment_digest(self):
        self.c4b.server()
        self.deny(expected_witness_enrollment_sha256="b" * 64)

    def test_14_forged_c4b_signed_state_is_refused_before_c3e_grant(self):
        self.c4b.server("bad_sig")
        self.deny()

    def test_15_replayed_c4b_signed_challenge_is_refused(self):
        self.c4b.server()
        self.deny(fresh_challenge=b"z" * 32)

    def test_16_original_c4b_transport_peer_owner_spoof_refuses(self):
        self.c4b.server("root_peer_spoofs_socket_owner")
        self.deny()

    def test_17_old_c4b_checkpoint_after_local_rotation_refuses(self):
        self.c4b.fixture.base.stage()
        self.c4b.fixture.commit()
        self.c4b.server()
        self.deny()

    def test_18_no_production_authority_even_when_all_fixtures_agree(self):
        self.c4b.server()
        result = self.good()
        for key, value in J.NEGATIVE.items():
            self.assertIs(value, False, key)
            self.assertIs(result[key], False, key)
        self.assertNotIn("grant", result)
        self.assertNotIn("approvalToken", result)
        self.assertNotIn("witnessInputs", result)
        self.assertNotIn("credential", result)

    def test_19_owner_sources_are_read_only_and_not_imported_by_live_broker(self):
        src = Path(J.__file__).read_text()
        broker = (ROOT / "services/connections/ConnectionsBroker.qml").read_text()
        self.assertIn("C3eNOriginWitnessHandoff.py", src)
        self.assertNotIn("C4bC3eNSignedOriginJoin", broker)
        self.assertIn("readonly property bool credentialActionsEnabled: false", broker)
        self.assertTrue(all(x is False for x in J.NEGATIVE.values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
