#!/usr/bin/env python3
"""C4b owner integration contracts for the unchanged C3e-AG real kernel observer.

This is a FAST source-contract suite. The real source of Linux /proc, SELinux,
RPM, two-reboot and rollback evidence is the separate official Fedora 44 KVM
workflow, NOT these static tests. No host installation or authorization.
"""
from __future__ import annotations
import ast
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
GUEST = ROOT / "tests/connections/identity_silverblue"
PROBE = (GUEST / "guest_identity_service_probe.sh").read_text()
HARNESS = (GUEST / "run_official_silverblue_identity.sh").read_text()
OBS_PATH = ROOT / "tests/connections/c3e_release_trust/C3eAGIdentityKernelObserver.py"
OBSERVER = OBS_PATH.read_text()
spec = importlib.util.spec_from_file_location("c4b_existing_c3eag_source_contract", OBS_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("C4B_C3EAG_REQUIRED_PROTECTED_OBSERVER_NOT_FOUND")
AG = importlib.util.module_from_spec(spec)
spec.loader.exec_module(AG)

class RealSilverblueC3eAGOwnerIntegration(unittest.TestCase):
    def test_01_official_kvm_stages_exact_unmodified_c3e_observer(self):
        self.assertIn('tests/connections/c3e_release_trust/C3eAGIdentityKernelObserver.py', HARNESS)
        self.assertIn("c3eag_kernel_observer_payload=", HARNESS)
        self.assertIn("postapollo_id_ci_c3eag_observer.py <<'C4B_C3EAG_OBSERVER'", HARNESS)
        self.assertIn("$c3eag_kernel_observer_payload", HARNESS)
        self.assertIn("chmod 0444 /usr/local/libexec/postapollo_id_ci_c3eag_observer.py", HARNESS)
        self.assertNotIn("Ed25519PrivateKey.generate", OBSERVER)

    def test_02_actual_running_service_imports_protected_observer_without_clone(self):
        self.assertIn("import postapollo_id_ci_c3eag_observer as C3EAG", PROBE)
        self.assertIn('C3EAG.observe_ci_only(', PROBE)
        self.assertIn('mode="c4b-guest-candidate"', PROBE)
        self.assertNotIn("def observe_ci_only(", PROBE)

    def test_03_guest_invocation_has_all_existing_c3e_scope_guards(self):
        self.assertIn("POST_APOLLO_C4B_TEST_GUEST=1 GITHUB_ACTIONS=true RUNNER_ENVIRONMENT=github-hosted",PROBE)
        self.assertEqual(AG.C4B_UNIT, "post-apollo-identity-silverblue-ci.service")
        self.assertEqual(AG.C4B_EXE,"/run/postapollo-identity-silverblue-ci-only/ci-python3")
        self.assertEqual(AG.C4B_SCRIPT,"/usr/libexec/post-apollo/identity/identity-gateway-ci")
        self.assertIn('Path("/run/ostree-booted").exists()', OBSERVER)
        self.assertIn('"/sys/fs/selinux/enforce"', OBSERVER)
        self.assertIn('"c4b-guest-candidate"',OBSERVER)

    def test_04_live_observer_inspects_real_kernel_and_systemd_not_serial(self):
        for source in (
            "os.pidfd_open(", 'Path("/proc")', 'Path(f"/proc/{pid}/status")',
            'Path(f"/proc/{pid}/cgroup")', 'Path(f"/proc/{pid}/attr/current")',
            'os.open(f"/proc/{pid}/exe"', '_main_pid_from_systemd()',
            "_script(pins)", "_cmdline(pid, pins)",
        ):
            with self.subTest(source=source):
                self.assertIn(source, OBSERVER)

    def test_05_expected_live_origin_fields_exactly_c3e_contract(self):
        self.assertEqual(AG.EXPECTED, frozenset({
            "pid","startTicks","uid","gid","unit","exePath","exeSha256",
            "scriptPath","entrypointSha256","cgroup","selinux",
        }))
        for field in AG.EXPECTED:
            with self.subTest(field=field):
                self.assertIn(f'"{field}":', PROBE)

    def test_06_observer_is_executed_before_service_stop_and_second_rollback(self):
        self.assertLess(PROBE.index('C3EAG.observe_ci_only('),
                        PROBE.index('systemctl stop "$unit" || fail "SERVICE_STOP_REFUSED"'))
        self.assertIn("'C4B_ID_PASS // REAL_C3EAG_RUNNING_GATEWAY_KERNEL_SNAPSHOT'",HARNESS)
        self.assertIn("'C4B_ID_PASS // REAL_C3EAG_MUTATED_KERNEL_AND_SCRIPT_PINS_REFUSED'",HARNESS)
        self.assertIn("REAL_OFFICIAL_SILVERBLUE_SIGNED_IDENTITY_RPM_TWO_REBOOTS_AND_ROLLBACK",HARNESS)

    def test_07_wrong_pid_start_uid_script_and_interpreter_digests_refuse(self):
        for field in ("pid","startTicks","uid","exeSha256","entrypointSha256"):
            with self.subTest(field=field):
                self.assertIn(f'("{field}",',PROBE)
        self.assertIn('except C3EAG.Refused:', PROBE)
        self.assertIn('else:\n        raise RuntimeError("C3eAG accepted substituted', PROBE)

    def test_08_only_guest_source_hashes_no_unsigned_witness_promotion(self):
        self.assertIn("hashlib.sha256(Path(C3EAG.C4B_EXE).read_bytes())",PROBE)
        self.assertIn("hashlib.sha256(Path(C3EAG.C4B_SCRIPT).read_bytes())",PROBE)
        self.assertIn("C3EAG.NEGATIVE",PROBE)
        for name in ("hostAuthenticated","canBeginSignIn",
                     "credentialActionsEnabled","productionAuthority"):
            with self.subTest(name=name):
                self.assertIs(AG.NEGATIVE[name], False)

    def test_09_bounded_existing_uart_markers_preserved_and_not_forged(self):
        self.assertIn('C4B_ID_CHALLENGE_PROOF\\ //*) printf',PROBE)
        self.assertIn('sed -n \'1,28p\' "$probe_log"',PROBE)
        for marker in ("REAL_C3EAG_RUNNING_GATEWAY_KERNEL_SNAPSHOT",
                       "REAL_C3EAG_MUTATED_KERNEL_AND_SCRIPT_PINS_REFUSED"):
            self.assertEqual(HARNESS.count("'C4B_ID_PASS // "+marker+"'"),1)
            self.assertEqual(PROBE.count('print("C4B_ID_PASS // '+marker+'")'),1)
        self.assertIn('verify_controller_challenge_ci.py" \\\n  verify',HARNESS)

    def test_10_disposable_offline_gate_and_no_production_key_export(self):
        self.assertIn("POST_APOLLO_ID_SILVERBLUE_CI_ONLY",HARNESS)
        self.assertIn('[[ -c /dev/kvm',HARNESS)
        self.assertIn("-nic none",HARNESS)
        self.assertIn("C4B_ID_LIMITATION // CI_ONLY_CONFIRMED_CONFINEMENT",HARNESS)

    def test_11_existing_guest_python_probe_compiles(self):
        # The source script's embedded interpreter is executed as root in
        # the actual guest, but syntax is safe to check without a VM.
        start = PROBE.index("import base64,hashlib,os,re,secrets,socket,stat,struct,subprocess,sys")
        end = PROBE.index("\nPY\n", start)
        code = PROBE[start:end]
        ast.parse(code)

    def test_12_external_c3e_observer_remains_deny_only_even_on_matching_guest(self):
        self.assertIn('"observedC4bGuestCandidateNotAttested": mode == "c4b-guest-candidate"',OBSERVER)
        for key in ("independentInstalledHostAttested",
                    "signedHostOriginAuthenticated","operatorReleaseRootEnrolled",
                    "externallyProtectedChallengeIssuerVerified",
                    "externalRollbackResistanceVerified","c5HumanConsentVerified"):
            self.assertFalse(AG.NEGATIVE[key])

if __name__ == "__main__":
    unittest.main(verbosity=2)
