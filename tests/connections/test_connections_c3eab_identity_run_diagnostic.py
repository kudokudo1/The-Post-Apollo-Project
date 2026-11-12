#!/usr/bin/env python3
"""C3e-AB: independently exercise C4b full-run versus partial-run diagnostics."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent / "c3e_release_trust"
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "c3eab_deny_only_diagnostic", HERE / "C3eABIdentityRunDiagnostic.py")
assert spec and spec.loader
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)


def bundle(*lines):
    return ("\n".join(lines) + "\n").encode("ascii")


def completed():
    return bundle(*D.REQUIRED_ORDER, "C4B_ID_VM_PROCESS_EXIT // 0")


def partial_actual_run_43144030036():
    """Strictly a bounded synthetic transcription of publicly observed stages.

    The actual GitHub run 43144030036 FAILED (VM exit 2); we deliberately
    omit rollback_pending, layer removal, test-keyring removal and host PASS.
    No external artifact is downloaded, trusted, imported or tampered with.
    """
    markers = D.REQUIRED_ORDER[:16]
    return bundle(*markers, "C4B_ID_VM_PROCESS_EXIT // 2")


class C3eABIdentityRunDiagnosticTests(unittest.TestCase):
    def check(self, artifact=None, conclusion="success"):
        return D.assess_untrusted_markers(
            artifact=completed() if artifact is None else artifact,
            caller_reported_workflow_conclusion=conclusion)

    def refused(self, artifact=None, conclusion="success"):
        with self.assertRaises(D.Refused):
            D.require_complete_untrusted_markers(
                artifact=completed() if artifact is None else artifact,
                caller_reported_workflow_conclusion=conclusion)

    def test_01_full_synthetic_chain_only_returns_consistency_not_host_trust(self):
        out = self.check()
        self.assertTrue(out["completeMarkerSequenceConsistentInCI"])
        self.assertTrue(out["requiredMarkerOrderSatisfied"])
        self.assertEqual(out["missingRequiredMarkers"], [])
        self.assertEqual(out["guestVmProcessExit"], 0)
        self.assertEqual(out["diagnosticState"],
                         "COMPLETE_MARKER_SEQUENCE_ONLY_NO_HOST_ATTESTATION")
        for flag in D.NEGATIVE:
            self.assertIs(out[flag], False)
        self.assertTrue(
            D.require_complete_untrusted_markers(
                artifact=completed(),
                caller_reported_workflow_conclusion="success"
            )["completeMarkerSequenceConsistentInCI"])

    def test_02_actual_failed_run_stage_pattern_is_partial_even_after_selinux_cleanup(self):
        out = self.check(partial_actual_run_43144030036(), "failure")
        self.assertFalse(out["completeMarkerSequenceConsistentInCI"])
        self.assertIn(
            "C4B_ID_PASS // REAL_SILVERBLUE_IDENTITY_RPM_LAYER_REMOVED",
            out["missingRequiredMarkers"])
        self.assertIn("C4B_ID_STAGE // rollback_pending", out["missingRequiredMarkers"])
        self.assertTrue(all(out[name] is False for name in D.NEGATIVE))
        self.refused(partial_actual_run_43144030036(), "failure")

    def test_03_failed_job_refuses_even_if_untrusted_log_has_every_pass_marker(self):
        out = self.check(conclusion="failure")
        self.assertFalse(out["completeMarkerSequenceConsistentInCI"])
        self.assertEqual(out["missingRequiredMarkers"], [])
        self.refused(conclusion="failure")

    def test_04_nonzero_exit_refuses_even_with_all_guest_pass_markers(self):
        data = bundle(*D.REQUIRED_ORDER, "C4B_ID_VM_PROCESS_EXIT // 2")
        out = self.check(data)
        self.assertEqual(out["guestVmProcessExit"], 2)
        self.assertFalse(out["completeMarkerSequenceConsistentInCI"])
        self.refused(data)

    def test_05_missing_rollback_stage_is_not_a_complete_run(self):
        lines = [x for x in D.REQUIRED_ORDER if x !=
                 "C4B_ID_STAGE // rollback_pending"]
        lines.append("C4B_ID_VM_PROCESS_EXIT // 0")
        out = self.check(bundle(*lines))
        self.assertFalse(out["requiredMarkerOrderSatisfied"])
        self.assertIn("C4B_ID_STAGE // rollback_pending",
                      out["missingRequiredMarkers"])
        self.refused(bundle(*lines))

    def test_06_missing_independent_kernel_network_denial_refuses(self):
        skipped = "C4B_ID_PASS // REAL_SELINUX_DOMAIN_DENIED_INET_SOCKET_CREATE"
        lines = [x for x in D.REQUIRED_ORDER if x != skipped]
        out = self.check(bundle(*lines, "C4B_ID_VM_PROCESS_EXIT // 0"))
        self.assertIn(skipped, out["missingRequiredMarkers"])
        self.assertFalse(out["completeMarkerSequenceConsistentInCI"])

    def test_07_missing_one_signed_unavailable_action_is_incomplete(self):
        skipped = "C4B_ID_PASS // INSTALLED_SIGNED_UNAVAILABLE_CANCEL"
        out = self.check(bundle(
            *(x for x in D.REQUIRED_ORDER if x != skipped),
            "C4B_ID_VM_PROCESS_EXIT // 0"))
        self.assertIn(skipped, out["missingRequiredMarkers"])
        self.refused(bundle(*(x for x in D.REQUIRED_ORDER if x != skipped),
                           "C4B_ID_VM_PROCESS_EXIT // 0"))

    def test_08_permissive_or_wrong_selinux_domain_does_not_substitute(self):
        lines = list(D.REQUIRED_ORDER)
        lines[5] = "C4B_ID_SELINUX_STAGE // enforcing_state=Permissive"
        lines[6] = "C4B_ID_SELINUX_OBSERVED // unconfined_u:unconfined_r:unconfined_t:s0"
        out = self.check(bundle(*lines, "C4B_ID_VM_PROCESS_EXIT // 0"))
        self.assertFalse(out["completeMarkerSequenceConsistentInCI"])
        self.refused(bundle(*lines, "C4B_ID_VM_PROCESS_EXIT // 0"))

    def test_09_reordered_rollback_before_confined_service_refuses(self):
        lines = list(D.REQUIRED_ORDER)
        lines[7], lines[17] = lines[17], lines[7]
        out = self.check(bundle(*lines, "C4B_ID_VM_PROCESS_EXIT // 0"))
        self.assertFalse(out["requiredMarkerOrderSatisfied"])
        self.assertEqual(out["missingRequiredMarkers"], [])
        self.refused(bundle(*lines, "C4B_ID_VM_PROCESS_EXIT // 0"))

    def test_10_guest_fail_or_blocked_marker_refuses_complete_chain(self):
        for marker in ("C4B_ID_FAIL // GUEST_REPORTED_FAILURE",
                       "C4B_ID_BLOCKED // ROLLBACK_NEVER_VERIFIED"):
            with self.subTest(marker=marker):
                data = bundle(*D.REQUIRED_ORDER, marker,
                              "C4B_ID_VM_PROCESS_EXIT // 0")
                out = self.check(data)
                self.assertTrue(out["guestFailureMarkerObserved"])
                self.assertFalse(out["completeMarkerSequenceConsistentInCI"])
                self.refused(data)

    def test_11_detail_line_cannot_spoof_nested_pass_marker(self):
        missing = "C4B_ID_PASS // REAL_SELINUX_DOMAIN_DENIED_INET_SOCKET_CREATE"
        lines = [
            "C4B_ID_SELINUX_NEGATIVE_DETAIL // " + missing
            if x == missing else x for x in D.REQUIRED_ORDER
        ]
        out = self.check(bundle(*lines, "C4B_ID_VM_PROCESS_EXIT // 0"))
        self.assertIn(missing, out["missingRequiredMarkers"])
        self.assertFalse(out["completeMarkerSequenceConsistentInCI"])

    def test_12_duplicate_heartbeats_do_not_invent_or_remove_real_stages(self):
        lines = []
        for item in D.REQUIRED_ORDER:
            lines.extend([item, item])
        out = self.check(bundle(*lines, "C4B_ID_VM_PROCESS_EXIT // 0"))
        self.assertTrue(out["completeMarkerSequenceConsistentInCI"])
        self.assertTrue(all(out[k] is False for k in D.NEGATIVE))

    def test_13_missing_duplicate_or_malformed_exit_marker_fails_closed(self):
        for data in (
            bundle(*D.REQUIRED_ORDER),
            bundle(*D.REQUIRED_ORDER,"C4B_ID_VM_PROCESS_EXIT // 0",
                   "C4B_ID_VM_PROCESS_EXIT // 0"),
            bundle(*D.REQUIRED_ORDER,"C4B_ID_VM_PROCESS_EXIT // negative"),
            bundle(*D.REQUIRED_ORDER,"C4B_ID_VM_PROCESS_EXIT // 999"),
        ):
            with self.subTest(data=data[-45:]):
                with self.assertRaises(D.Refused):
                    self.check(data)

    def test_14_invalid_artifact_frame_refuses(self):
        for data in (b"", b"plain\n", b"C4B_ID_STAGE // initial",
                     completed() + b"\0",
                     completed().replace(b"\n",b"\r\n"),
                     b"\xff\n",
                     b"C4B_ID_PASS // "+b"x"*D.MAX_BYTES+b"\n"):
            with self.subTest(length=len(data)):
                with self.assertRaises(D.Refused):
                    self.check(data)

    def test_15_unknown_or_forged_runner_conclusion_refuses(self):
        for conclusion in ("in_progress", "SUCCESS", "", 1, None, True):
            with self.subTest(conclusion=conclusion):
                with self.assertRaises(D.Refused):
                    self.check(conclusion=conclusion)
        self.assertFalse(self.check(conclusion="startup_failure")[
            "completeMarkerSequenceConsistentInCI"])

    def test_16_guest_serial_console_prefix_is_diagnostic_only(self):
        original = list(D.REQUIRED_ORDER)
        lines = [("fedora login: "+s if i%2 else s)
                 for i,s in enumerate(original)]
        out = self.check(bundle(*lines,"C4B_ID_VM_PROCESS_EXIT // 0"))
        self.assertTrue(out["completeMarkerSequenceConsistentInCI"])
        self.assertIs(out["artifactOriginCryptographicallyAuthenticated"],False)

    def test_17_no_real_issuer_os_access_or_production_authorization(self):
        code = (HERE/"C3eABIdentityRunDiagnostic.py").read_text()
        for disallowed in ("socket.socket(", "subprocess.run(", "rpm-ostree install",
                           "HostBoundary.authenticated(", "productionAuthority\": True",
                           "canBeginSignIn\": True", "canApprove\": True"):
            self.assertNotIn(disallowed, code)
        for key,val in D.NEGATIVE.items():
            self.assertIs(val,False)
            self.assertIn('"' + key + '": False',code)

    def test_18_log_with_false_prefix_marker_is_still_not_an_attestor(self):
        lines = ["UNVERIFIED REPORT: " + s for s in D.REQUIRED_ORDER]
        out=self.check(bundle(*lines, "C4B_ID_VM_PROCESS_EXIT // 0"))
        self.assertTrue(out["completeMarkerSequenceConsistentInCI"])
        self.assertFalse(out["artifactOriginCryptographicallyAuthenticated"])
        self.assertFalse(out["githubWorkflowResultIndependentlyAuthenticated"])
        self.assertFalse(out["installedIdentityHostAuthenticated"])


    def test_19_nested_guest_failure_inside_journal_detail_refuses(self):
        data = bundle(
            *D.REQUIRED_ORDER,
            "C4B_ID_SELINUX_NEGATIVE_DETAIL // C4B_ID_FAIL // GUEST_FAILED",
            "C4B_ID_VM_PROCESS_EXIT // 0",
        )
        outcome = self.check(data)
        self.assertTrue(outcome["guestFailureMarkerObserved"])
        self.assertFalse(outcome["completeMarkerSequenceConsistentInCI"])
        self.refused(data)

    def test_20_vm_exit_must_be_final_runner_artifact_line(self):
        data = bundle(
            *D.REQUIRED_ORDER[:10],
            "C4B_ID_VM_PROCESS_EXIT // 0",
            *D.REQUIRED_ORDER[10:],
        )
        with self.assertRaises(D.Refused):
            self.check(data)

    def test_21_no_rollback_from_shutdown_cleanup_only(self):
        lines = [x for x in D.REQUIRED_ORDER if x not in (
            "C4B_ID_PASS // REAL_IDENTITY_SERVICE_PROBE_FINISHED_BEFORE_ROLLBACK",
            "C4B_ID_STAGE // rollback_pending",
            "C4B_ID_PASS // REAL_SILVERBLUE_IDENTITY_RPM_LAYER_REMOVED",
            "C4B_ID_PASS // TEST_KEYRING_REMOVED_AND_PRODUCTION_DISABLED",
            "C4B_ID_PASS // REAL_OFFICIAL_SILVERBLUE_SIGNED_IDENTITY_RPM_TWO_REBOOTS_AND_ROLLBACK",
        )]
        result=self.check(bundle(*lines,"C4B_ID_VM_PROCESS_EXIT // 0"))
        self.assertFalse(result["completeMarkerSequenceConsistentInCI"])
        self.assertIs(result["productionAuthority"], False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
