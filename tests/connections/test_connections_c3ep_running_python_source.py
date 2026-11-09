#!/usr/bin/env python3
"""Real Linux process tests for C3e-P's read-only Python-source observer.

CI-only (root inside disposable GitHub Actions), NO Fedora workstation use.
The test program is purposefully inert; this does not claim C4b service
confinement, actual DBus operation, signed enrollment or live user consent.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tests/connections/c3e_release_trust/C3ePRunningPythonSource.py"
SPEC = importlib.util.spec_from_file_location("c3ep", SOURCE)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)

SCRIPT = """#!/usr/bin/python3
import sys, time
print("C3EP_READY // INERT_TEST_SCRIPT", flush=True)
time.sleep(20)
"""


class C3ePActualProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (os.geteuid() != 0 or
                os.environ.get("GITHUB_ACTIONS") != "true" or
                not sys.platform.startswith("linux")):
            raise RuntimeError("C3EP_REQUIRES_EPHEMERAL_CI_ROOT")
        cls.nobody = pwd.getpwnam("nobody")
        cls.interpreter = Path("/usr/bin/python3")
        if not cls.interpreter.exists():
            raise RuntimeError("C3EP_TEST_INTERPRETER_MISSING")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="c3ep-ci-", dir="/run")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.base.chmod(0o755)
        self.script = self.base / "status-host"
        self.script.write_text(SCRIPT)
        self.script.chmod(0o555)
        self.sha = hashlib.sha256(self.script.read_bytes()).hexdigest()
        self.pid = None

    @staticmethod
    def _stop(proc):
        if proc.poll() is None:
            proc.terminate()
        try:
            proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate(timeout=3)

    def _run_client(self, *, script=None, operation="--read-only"):
        target = script or self.script
        uid, gid = self.nobody.pw_uid, self.nobody.pw_gid

        def drop():
            os.setgroups([])
            os.setgid(gid)
            os.setuid(uid)

        p = subprocess.Popen(
            [str(target), operation], preexec_fn=drop,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1)
        self.addCleanup(self._stop, p)
        ready = p.stdout.readline().strip()
        if ready != "C3EP_READY // INERT_TEST_SCRIPT":
            self.fail("C3EP_TEST_PROCESS_START_FAILED pid=%r stderr=%r" %
                      (p.pid, p.stderr.read()[-1200:]))
        self.proc = p
        self.args = {
            "pid": p.pid, "expected_start": M._proc_start(p.pid),
            "expected_uid": uid, "expected_gid": gid,
            "expected_script_path": str(self.script),
            "expected_interpreter_path": str(self.interpreter),
            "expected_signed_script_sha256": self.sha,
        }
        return p

    def _observe(self, **changes):
        return M.observe(**{**self.args, **changes})

    def _refused(self, code, **changes):
        with self.assertRaises(M.Refused) as result:
            self._observe(**changes)
        self.assertEqual(str(result.exception), code)

    def test_01_live_process_has_exact_script_interpreter_and_nonroot_uid(self):
        self._run_client()
        result = self._observe()
        self.assertEqual(result["schema"], M.SCHEMA)
        self.assertTrue(result["script_file_matches_supplied_signed_payload"])
        self.assertTrue(result["kernel_interpreter_inode_matches_expected"])
        self.assertTrue(result["commandline_matches_installed_entrypoint"])
        self.assertEqual(result["running_script_sha256"], self.sha)
        self.assertEqual(result["observed_pid"], self.proc.pid)
        self.assertIs(result["installedGuestMeasured"], False)
        self.assertIs(result["evidenceCryptographicallyAttested"], False)
        for name in ("hostAuthenticated", "canApprove",
                     "credentialActionsEnabled", "productionAuthority"):
            self.assertIs(result[name], False)

    def test_02_modified_python_file_while_running_refused(self):
        self._run_client()
        self.script.write_text(SCRIPT + "# modified since exec\n")
        self.script.chmod(0o555)
        self._refused("RUNNING_SCRIPT_SIGNED_PAYLOAD_MISMATCH")

    def test_03_expected_hash_substitution_refused(self):
        self._run_client()
        self._refused("RUNNING_SCRIPT_SIGNED_PAYLOAD_MISMATCH",
                      expected_signed_script_sha256="0" * 64)

    def test_04_different_unpinned_nonroot_uid_refused(self):
        self._run_client()
        self._refused("PROCESS_OS_IDENTITY_MISMATCH", expected_uid=2001)

    def test_05_different_unpinned_group_refused(self):
        self._run_client()
        self._refused("PROCESS_OS_IDENTITY_MISMATCH", expected_gid=2001)

    def test_06_mismatched_process_start_refused(self):
        self._run_client()
        self._refused("PROCESS_START_MISMATCH", expected_start="1")

    def test_07_wrong_python_executable_refused(self):
        self._run_client()
        self._refused("PROCESS_INTERPRETER_MISMATCH",
                      expected_interpreter_path="/bin/true")

    def test_08_altered_process_command_refused(self):
        self._run_client(operation="--write")
        self._refused("PROCESS_COMMANDLINE_NOT_INSTALLED_ENTRYPOINT")

    def test_09_symlink_script_refused(self):
        self._run_client()
        target = self.base / "original"
        self.script.rename(target)
        self.script.symlink_to(target)
        self._refused("RUNNING_SCRIPT_OPEN_REFUSED")

    def test_10_group_writable_script_refused(self):
        self._run_client()
        self.script.chmod(0o775)
        self._refused("RUNNING_SCRIPT_FILE_UNSAFE")

    def test_11_unlinked_script_refused(self):
        self._run_client()
        self.script.unlink()
        self._refused("RUNNING_SCRIPT_OPEN_REFUSED")

    def test_12_excessively_broad_ci_scope_refused(self):
        self._run_client()
        self._refused("SCRIPT_SCOPE_REFUSED",
                      expected_script_path="/tmp/status-host")

    def test_13_actual_silverblue_entrypoint_requires_real_ci_guest(self):
        self._run_client()
        self._refused("GUEST_ONLY_SCRIPT_SCOPE",
                      expected_script_path=str(M.SIGNED_SCRIPT_PATH))

    def test_14_non_ci_environment_is_refused(self):
        self._run_client()
        was = os.environ.get("GITHUB_ACTIONS")
        os.environ["GITHUB_ACTIONS"] = "false"
        try:
            self._refused("CI_ONLY_ROOT_OBSERVER_REQUIRED")
        finally:
            if was is None:
                os.environ.pop("GITHUB_ACTIONS", None)
            else:
                os.environ["GITHUB_ACTIONS"] = was

    def test_15_malformed_expected_hash_is_refused(self):
        self._run_client()
        for bad in (None, True, "", "0" * 63, "G" * 64):
            with self.subTest(value=repr(bad)):
                self._refused("INVALID_EXPECTED_MEASUREMENT",
                              expected_signed_script_sha256=bad)

    def test_16_root_uid_not_a_valid_dedicated_service(self):
        self._run_client()
        self._refused("INVALID_EXPECTED_MEASUREMENT", expected_uid=0)

    def test_17_negative_attestation_not_a_provider_grant(self):
        self._run_client()
        result = self._observe()
        self.assertNotIn("approvalToken", result)
        self.assertNotIn("allowed", result)
        self.assertNotIn("grantActive", result)
        services = ROOT / "services/connections"
        self.assertIn("readonly property bool credentialActionsEnabled: false",
                      (services / "ConnectionsBroker.qml").read_text())
        self.assertIn("readonly property bool hostAuthenticated: false",
                      (services / "ConnectionsRequestStatus.qml").read_text())
        for path in (*services.glob("*.qml"), *services.glob("*.js"),
                     services / "qmldir"):
            self.assertNotIn("C3ePRunningPythonSource", path.read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
