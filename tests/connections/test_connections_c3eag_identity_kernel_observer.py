#!/usr/bin/env python3
"""C3e-AG: genuine disposable Linux process observations, deny-only."""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import pwd
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tests/connections/c3e_release_trust"
_spec = importlib.util.spec_from_file_location(
    "c3eag_observer", SOURCE / "C3eAGIdentityKernelObserver.py")
assert _spec and _spec.loader
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)


def _nonroot():
    def drop():
        os.setgroups([])
        os.setgid(65534)
        os.setuid(65534)
    return drop


class C3eAGIdentityKernelObserverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (sys.platform != "linux" or os.geteuid() != 0 or
                os.environ.get("GITHUB_ACTIONS") != "true" or
                os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
            raise RuntimeError("C3EAG_DISPOSABLE_ROOT_GITHUB_CI_ONLY")
        if not Path("/proc/self/cgroup").read_text().startswith("0::"):
            raise RuntimeError("C3EAG_CGROUP_V2_CI_REQUIRED")
        cls.test_user = pwd.getpwuid(65534)

    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(prefix=A.FIXTURE_PREFIX, dir="/run"))
        self.directory.chmod(0o755)
        self.addCleanup(lambda: shutil.rmtree(self.directory, ignore_errors=True))
        self.script = self.directory / "identity-gateway-ci"
        self.script.write_text("import time\ntime.sleep(55)\n", encoding="ascii")
        self.script.chmod(0o555)
        self.proc = subprocess.Popen(
            ["/usr/bin/python3", "-I", "-B", str(self.script)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, preexec_fn=_nonroot(),
        )
        self.addCleanup(self._stop)
        for _ in range(80):
            if self.proc.poll() is not None:
                raise AssertionError("C3EAG_TEST_PROCESS_EXITED_BEFORE_OBSERVATION")
            try:
                cmd = (Path("/proc") / str(self.proc.pid) / "cmdline").read_bytes()
                if str(self.script).encode() in cmd and cmd.endswith(b"\0"):
                    break
            except OSError:
                pass
            time.sleep(0.025)
        else:
            raise AssertionError("C3EAG_TEST_PROCESS_NOT_READY")
        exe = Path(f"/proc/{self.proc.pid}/exe")
        with exe.open("rb") as fd:
            exe_hash = hashlib.file_digest(fd, "sha256").hexdigest()
        self.pins = {
            "pid": self.proc.pid,
            "startTicks": A._start(self.proc.pid),
            "uid": 65534,
            "gid": 65534,
            "unit": A.FIXTURE_UNIT,
            "exePath": "/usr/bin/python3",
            "exeSha256": exe_hash,
            "scriptPath": str(self.script),
            "entrypointSha256": hashlib.sha256(self.script.read_bytes()).hexdigest(),
            "cgroup": A._cgroup(self.proc.pid),
            "selinux": A._selinux_or_lsm(self.proc.pid),
        }

    def _stop(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=3)

    def observe(self, **changes):
        p = {**self.pins, **changes}
        return A.observe_ci_only(expected=p)

    def refused(self, **changes):
        with self.assertRaises(A.Refused):
            self.observe(**changes)

    def test_01_real_nonroot_linux_python_process_matches_caller_pins_no_grants(self):
        result = self.observe()
        self.assertTrue(result["realLinuxPidAndExecutableObservedInDisposableCI"])
        self.assertTrue(result["kernelProcessFieldsMatchCallerPinsInCI"])
        self.assertTrue(result["sourceScriptFileMatchesCallerPinInCI"])
        self.assertFalse(result["observedC4bGuestCandidateNotAttested"])
        for name in A.NEGATIVE:
            self.assertIs(result[name], False, name)

    def test_02_wrong_pid_refused(self):
        self.refused(pid=self.proc.pid + 999999)

    def test_03_wrong_kernel_start_refused(self):
        self.refused(startTicks=self.pins["startTicks"] + 1)

    def test_04_wrong_kernel_uid_refused(self):
        self.refused(uid=self.pins["uid"] + 1)

    def test_05_wrong_kernel_gid_refused(self):
        self.refused(gid=self.pins["gid"] + 1)

    def test_06_wrong_interpreter_hash_refused(self):
        self.refused(exeSha256="0" * 64)

    def test_07_wrong_interpreter_path_refused(self):
        self.refused(exePath="/usr/bin/env")

    def test_08_mutated_script_hash_refused(self):
        self.refused(entrypointSha256="a" * 64)

    def test_09_modified_running_script_bytes_refused(self):
        self.script.chmod(0o755)
        self.script.write_text("import time\ntime.sleep(57)\n", encoding="ascii")
        self.script.chmod(0o555)
        self.refused()

    def test_10_script_symlink_refused(self):
        relocated = self.directory / "saved"
        self.script.rename(relocated)
        self.script.symlink_to(relocated)
        self.refused()

    def test_11_wrong_script_file_mode_refused(self):
        self.script.chmod(0o775)
        self.refused()

    def test_12_missing_script_path_refused(self):
        self.script.unlink()
        self.refused()

    def test_13_parent_directory_writable_refused(self):
        self.directory.chmod(0o777)
        self.refused()

    def test_14_wrong_cgroup_refused(self):
        self.refused(cgroup="/system.slice/forged.service")

    def test_15_wrong_selinux_or_lsm_context_refused(self):
        self.refused(selinux="system_u:system_r:postapollo_identity_ci_t:s0")

    def test_16_wrong_unit_scope_refused(self):
        self.refused(unit="some-other.service")

    def test_17_wrong_script_path_scope_refused(self):
        self.refused(scriptPath="/tmp/identity-gateway-ci")

    def test_18_real_c4b_guest_cannot_be_impersonated_on_ubuntu_ci(self):
        with self.assertRaises(A.Refused):
            A.observe_ci_only(expected=self.pins, mode="c4b-guest-candidate")

    def test_19_exited_process_pidfd_refused(self):
        self._stop()
        with self.assertRaises(A.Refused):
            self.observe()

    def test_20_boolean_and_partial_kernel_identity_refused(self):
        for key in ("pid", "startTicks", "uid", "gid"):
            with self.subTest(key=key):
                self.refused(**{key: True})
        d = dict(self.pins)
        d.pop("cgroup")
        with self.assertRaises(A.Refused):
            A.observe_ci_only(expected=d)

    def test_21_not_ci_or_not_root_guard_refused(self):
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}):
            with self.assertRaises(A.Refused):
                self.observe()

    def test_23_script_file_mutated_after_hashing_refused(self):
        original = A._script

        def change_after_hash(pins):
            old_metadata = original(pins)
            self.script.chmod(0o755)
            self.script.write_text("import time\\ntime.sleep(58)\\n", encoding="ascii")
            self.script.chmod(0o555)
            return old_metadata

        with patch.object(A, "_script", side_effect=change_after_hash):
            self.refused()

    def test_24_cgroup_changed_between_two_kernel_reads_refused(self):
        original = A._cgroup
        seen = [0]

        def changed_later(pid):
            seen[0] += 1
            if seen[0] == 1:
                return original(pid)
            return "/system.slice/forged-replacement.service"

        with patch.object(A, "_cgroup", side_effect=changed_later):
            self.refused()

    def test_22_no_real_c4b_install_or_login_side_effects(self):
        source = (SOURCE / "C3eAGIdentityKernelObserver.py").read_text()
        for unsafe in ("systemctl start", "systemctl stop", "rpm-ostree install",
                       "subprocess.Popen(", "open_browser(", "BEGIN_LOGIN(",
                       '"hostAuthenticated": True', '"productionAuthority": True',
                       '"canBeginSignIn": True', '"credentialActionsEnabled": True'):
            self.assertNotIn(unsafe, source)
        self.assertEqual(A.C4B_UNIT, "post-apollo-identity-silverblue-ci.service")
        self.assertEqual(A.C4B_SCRIPT,
                         "/usr/libexec/post-apollo/identity/identity-gateway-ci")

if __name__ == "__main__":
    unittest.main(verbosity=2)
