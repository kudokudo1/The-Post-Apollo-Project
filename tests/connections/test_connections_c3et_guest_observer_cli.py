#!/usr/bin/env python3
"""C3e-T: exercise CLI with the existing *real running* C3e-P Linux fixture."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
P_TEST = ROOT / "tests/connections/test_connections_c3ep_running_python_source.py"
CLI = ROOT / "tests/connections/c3e_release_trust/C3eTGuestObserverCLI.py"
SPEC = importlib.util.spec_from_file_location("c3et_real_p_fixture", P_TEST)
assert SPEC and SPEC.loader
PT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PT)


class C3eTGuestCLIContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        PT.C3ePActualProcessTests.setUpClass()

    def setUp(self):
        self.fx = PT.C3ePActualProcessTests(
            "test_01_live_process_has_exact_script_interpreter_and_nonroot_uid")
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.fx._run_client()

    def call(self, **override):
        args = dict(self.fx.args)
        args.update(override)
        argv = [
            sys.executable, "-B", str(CLI),
            "--pid", str(args["pid"]),
            "--start-ticks", args["expected_start"],
            "--uid", str(args["expected_uid"]),
            "--gid", str(args["expected_gid"]),
            "--python", args["expected_interpreter_path"],
            "--script", args["expected_script_path"],
            "--signed-script-sha256", args["expected_signed_script_sha256"],
        ]
        result = subprocess.run(argv, capture_output=True, text=True,
                                timeout=8, env=os.environ.copy())
        lines = result.stdout.splitlines()
        self.assertEqual(len(lines), 1, result.stderr)
        return result.returncode, json.loads(lines[0])

    def reject(self, expected, **override):
        rc, doc = self.call(**override)
        self.assertEqual(rc, 3, doc)
        self.assertEqual(doc["error"], expected, doc)
        self.assertIs(doc["hostAuthenticated"], False)
        self.assertIs(doc["credentialActionsEnabled"], False)

    def test_01_real_running_script_cli_observation(self):
        rc, doc = self.call()
        self.assertEqual(rc, 0, doc)
        self.assertEqual(doc["schema"],
                         "postapollo.connections.c3et-ci-guest-observation.v1")
        self.assertEqual(doc["observed_pid"], self.fx.proc.pid)
        self.assertEqual(doc["running_script_sha256"], self.fx.sha)
        self.assertTrue(doc["script_file_matches_supplied_signed_payload"])
        self.assertTrue(doc["commandline_matches_installed_entrypoint"])
        for k in ("installedGuestMeasured", "evidenceCryptographicallyAttested",
                  "hostAuthenticated", "canApprove", "credentialActionsEnabled",
                  "productionAuthority"):
            self.assertIs(doc[k], False)

    def test_02_wrong_signed_source_digest_refused(self):
        self.reject("RUNNING_SCRIPT_SIGNED_PAYLOAD_MISMATCH",
                    expected_signed_script_sha256="0" * 64)

    def test_03_wrong_process_start_refused(self):
        self.reject("PROCESS_START_MISMATCH", expected_start="1")

    def test_04_wrong_dedicated_uid_refused(self):
        self.reject("PROCESS_OS_IDENTITY_MISMATCH", expected_uid=2002)

    def test_05_wrong_dedicated_gid_refused(self):
        self.reject("PROCESS_OS_IDENTITY_MISMATCH", expected_gid=2002)

    def test_06_false_interpreter_refused(self):
        self.reject("PROCESS_INTERPRETER_MISMATCH",
                    expected_interpreter_path="/bin/true")

    def test_07_no_guest_path_self_attestation(self):
        self.reject("NO_REAL_C4B_GUEST_SCOPE",
                    expected_script_path="/usr/libexec/post-apollo/connections-status-host")

    def test_08_modified_loaded_file_refused(self):
        self.fx.script.write_text(PT.SCRIPT + "# post-exec tamper\n")
        self.fx.script.chmod(0o555)
        self.reject("RUNNING_SCRIPT_SIGNED_PAYLOAD_MISMATCH")

    def test_09_unapproved_test_scope_refused(self):
        self.reject("UNAPPROVED_TEST_SCRIPT_SCOPE",
                    expected_script_path="/tmp/status-host")

    def test_10_false_CI_origin_refused(self):
        original = os.environ.get("GITHUB_ACTIONS")
        os.environ["GITHUB_ACTIONS"] = "false"
        try:
            self.reject("DISPOSABLE_CI_ROOT_ONLY")
        finally:
            if original is None:
                os.environ.pop("GITHUB_ACTIONS", None)
            else:
                os.environ["GITHUB_ACTIONS"] = original

    def test_11_failed_script_cannot_emit_success(self):
        self.fx.script.unlink()
        self.reject("RUNNING_SCRIPT_OPEN_REFUSED")

    def test_12_never_promote_to_production_QML_authority(self):
        rc, doc = self.call()
        self.assertEqual(rc, 0)
        self.assertNotIn("approvalToken", doc)
        self.assertNotIn("providerConnected", doc)
        root = ROOT / "services/connections"
        self.assertIn("readonly property bool credentialActionsEnabled: false",
                      (root / "ConnectionsBroker.qml").read_text())
        self.assertIn("readonly property bool hostAuthenticated: false",
                      (root / "ConnectionsRequestStatus.qml").read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
