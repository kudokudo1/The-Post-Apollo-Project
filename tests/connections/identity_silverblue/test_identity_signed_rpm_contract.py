#!/usr/bin/env python3
"""C4b Identity-only Fedora signed RPM source contract, no workstation writes."""
from __future__ import annotations

import ast
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "tests/identity/fixtures/identity_gateway_installed_ci"
IDENTITY = ROOT / "services/identity"
AREA = ROOT / "tests/connections/identity_silverblue"
SPEC = AREA / "signed_identity_gateway.spec"
UNIT = AREA / "post-apollo-identity-silverblue-ci.service"
BUILDER = AREA / "build_signed_identity_gateway.sh"
VERIFY = AREA / "verify_signed_identity_gateway.sh"
WORKFLOW = ROOT / ".github/workflows/connections-identity-silverblue-rpm-contract.yml"
MODULES = (
    "desktop_command_gateway_v0.py",
    "desktop_host_lifecycle_v0.py",
    "desktop_context_projection_v0.py",
    "desktop_session_host_v0.py",
    "native_loopback_callback_v0.py",
    "private_context_ipc_v0.py",
    "signed_command_receipt_v0.py",
)
FILES = {"identity-gateway-ci", *MODULES}
PREFIX = "/usr/libexec/post-apollo/identity/"


class IdentitySilverblueSignedRpmContract(unittest.TestCase):
    def test_01_exact_real_identity_gateway_reused(self):
        self.assertTrue(FIXTURE.is_file())
        source = FIXTURE.read_text()
        self.assertIn("from desktop_command_gateway_v0 import IdentityCommandGateway", source)
        self.assertIn("from signed_command_receipt_v0 import ReceiptIssuer", source)
        for needle in (
            'verified_peer=lambda _peer: False',
            'active_seat=lambda: False',
            'approved_intent=lambda _peer, _action: False',
            'raise RuntimeError("Disposable installed fixture explicitly forbids login")',
            'os.environ.get("POST_APOLLO_ID_INSTALL_CI_ONLY") != "1"',
        ):
            self.assertIn(needle, source)
        for name in MODULES:
            self.assertTrue((IDENTITY / name).is_file(), name)
        installed_witness = (IDENTITY / "installed_gateway_witness_v1.py").read_text()
        self.assertIn("REQUIRED_FILES = frozenset(PREFIX + name for name in (", installed_witness)
        self.assertIn('PACKAGE = "post-apollo-identity-ci-fixture"', installed_witness)
        self.assertNotEqual("post-apollo-identity-ci-fixture",
                            "post-apollo-identity-silverblue-ci")

    def test_02_spec_exact_module_roster_no_exec_scripts(self):
        text = SPEC.read_text()
        self.assertIn("Name:           post-apollo-identity-silverblue-ci", text)
        self.assertIn("BuildArch:      noarch", text)
        self.assertIn("AutoReqProv:    no", text)
        self.assertIn("%undefine __brp_mangle_shebangs", text)
        payload = {x.strip() for x in text.split("%files\n", 1)[1].splitlines()
                   if x.strip().startswith("/")}
        expected = {PREFIX + name for name in FILES}
        expected.add("/usr/lib/systemd/system/post-apollo-identity-silverblue-ci.service")
        self.assertEqual(payload, expected)
        for name in FILES:
            self.assertIn(
                "install -D -m 0555 %{_sourcedir}/" + name +
                " %{buildroot}" + PREFIX + name, text,
            )
        self.assertIn("install -D -m 0644 %{_sourcedir}/post-apollo-identity-silverblue-ci.service", text)
        self.assertNotRegex(text, r"(?m)^%(pre|post|preun|postun|trigger|transfiletrigger)\b")

    def test_03_systemd_inert_by_default_and_deny_only(self):
        text = UNIT.read_text()
        self.assertNotIn("[Install]", text.split("# Deliberately no [Install]")[0])
        self.assertIn("ConditionPathExists=/run/postapollo-identity-silverblue-ci-only/authorized-test.marker", text)
        self.assertIn("User=postapollo-identity-ci", text)
        self.assertIn("Group=postapollo-identity-ci", text)
        self.assertIn("EnvironmentFile=/run/postapollo-identity-silverblue-ci-only/runtime.env", text)
        self.assertIn("ExecStart=/usr/bin/python3 -I -B " + PREFIX + "identity-gateway-ci", text)
        for guard in ("NoNewPrivileges=true", "ProtectSystem=strict",
                      "RestrictAddressFamilies=AF_UNIX"):
            self.assertIn(guard, text)

    def test_04_builder_exact_source_no_signing_custody_export(self):
        script = BUILDER.read_text()
        self.assertIn('POST_APOLLO_ID_SILVERBLUE_CI_ONLY', script)
        self.assertIn('RUNNER_ENVIRONMENT', script)
        self.assertIn('cp /src/tests/identity/fixtures/identity_gateway_installed_ci', script)
        for name in MODULES:
            self.assertIn(name, script)
        for required in ("rpmbuild", "rpmsign --addsign",
                         'rpm -qpl "$rpmfile"', "cmp -s",
                         'rpm -qp --scripts "$rpmfile"',
                         'rpm -qp --triggers "$rpmfile"',
                         "identity-disposable-rpm-public.asc",
                         "identity-artifact-manifest.sha256",
                         "--undefine __brp_mangle_shebangs",
                         'cmp -s "$original" "$prefix/$name"',
                         "BUILT_RPM_MUTATED_OR_REMODED_IDENTITY_",
                         "EXACT_SOURCE_BYTES_AND_MODES_VERIFIED_FROM_REAL_RPM_PAYLOAD"):
            self.assertIn(required, script)
        self.assertNotIn("rpm-ostree install", script)
        self.assertNotIn("systemctl enable", script)
        self.assertNotIn("private-key.asc", script)

    def test_05_separate_signer_refuses_pretrust(self):
        text = VERIFY.read_text()
        self.assertIn('rpm --dbpath "$keydb" --initdb', text)
        self.assertLess(text.index('SIGNER_PRETRUSTED_BEFORE_IMPORT'),
                        text.index('rpmkeys --dbpath "$keydb" --import "$public"'))
        self.assertLess(text.index('rpmkeys --dbpath "$keydb" --import "$public"'),
                        text.index('after="$(rpmkeys --dbpath "$keydb" --checksig -v "$rpmfile" 2>&1)"'))
        self.assertIn("UNTRUSTED_SIGNATURE_RESULT", text)
        self.assertIn("NO_SELINUX_SYSTEMD_PROCESS_OR_OSTREE_ADMISSION", text)

    def test_06_workflow_is_explicitly_test_only(self):
        src = WORKFLOW.read_text()
        self.assertIn("runs-on: ubuntu-latest", src)
        self.assertIn("POST_APOLLO_ID_SILVERBLUE_CI_ONLY: '1'", src)
        self.assertIn("RUNNER_ENVIRONMENT", src)
        self.assertIn("fedora:44", src)
        self.assertIn("verify_signed_identity_gateway.sh", src)
        self.assertNotIn("sudo rpm-ostree install", src)
        self.assertNotIn("deploy", src.lower())
        self.assertNotIn("productionAuthority: true", src)


    def test_07_official_silverblue_host_is_separate_and_networkless(self):
        script = (AREA / "run_official_silverblue_identity.sh").read_text()
        c2v = (ROOT / "tests/connections/c2v_silverblue/boot_official_silverblue.sh").read_text()
        for line in (
            "iso=Fedora-Silverblue-ostree-x86_64-44-1.7.iso",
            "iso_sha=9ccec9b075a0a4358a7209b2667156aaeeec3a6a3c8d71cada45b57fca9b4682",
            "inst.repo=cdrom inst.ks=hd:LABEL=ID4BCI:/ks.cfg inst.cmdline rd.neednet=0",
            "ostreesetup --osname=fedora --remote=fedora",
            "C4B_ID_PASS // REAL_OFFICIAL_SILVERBLUE_SIGNED_IDENTITY_RPM_TWO_REBOOTS_AND_ROLLBACK",
            "identity-silverblue-ci.rpm",
            "guest_identity_ostree_cycle.sh",
        ):
            self.assertIn(line, script)
        self.assertIn("iso_sha=9ccec9b075a0a4358a7209b2667156aaeeec3a6a3c8d71cada45b57fca9b4682", c2v)
        self.assertEqual(script.count("-nic none"), 2, "Installer AND actual persistent boot must remain offline")
        self.assertIn("RPM_VERIFY_RC|RPM_VERIFY_DETAIL", script)
        self.assertIn("test -c /dev/kvm", (ROOT / ".github/workflows/connections-identity-silverblue-real-boot.yml").read_text())
        self.assertNotIn("/tests/connections/c2v_silverblue/", script)
        self.assertNotIn("source " + str(ROOT / "tests/connections/c2v_silverblue"), script)
        for forbidden in ("rpm-ostree install --apply-live", "rpm-ostree reset", "systemctl enable post-apollo-identity-silverblue-ci.service"):
            self.assertNotIn(forbidden, script)

    def test_08_real_guest_has_signed_gate_and_phase_fencing(self):
        script = (AREA / "guest_identity_ostree_cycle.sh").read_text()
        for required in (
            'case "$phase" in',
            "initial)",
            "installing)",
            "layer_pending)",
            "rollback_pending)",
            "C4B_ID_FAIL //",
            "REAL_ENFORCING_OSTREE_REQUIRED",
            "OFFLINE_NO_NETWORK_REQUIRED",
            "SIGNED_RPM_PRETRUST_MUST_FAIL",
            "ISOLATED_SIGNED_RPM_VERIFICATION_FAILED",
            'rpm-ostree install --cache-only',
            "C4B_ID_PENDING_EXACT_IDENTITY_DEPLOYMENT",
            "REAL_SILVERBLUE_BOOTED_SIGNED_IDENTITY_RPM_INERT",
            "REAL_SILVERBLUE_IDENTITY_RPM_LAYER_REMOVED",
            "TEST_KEYRING_REMOVED_AND_PRODUCTION_DISABLED",
            '[[ "$enabled_state" == static || "$enabled_state" == disabled ]]',
            'timeout --signal=TERM --kill-after=3s 35s rpm -V "$pkg" >"$verify_file" 2>&1',
            "C4B_ID_RPM_VERIFY_RC",
            "C4B_ID_RPM_VERIFY_DETAIL",
            "SIGNED_IDENTITY_BOOTED_RPM_VERIFY_REFUSED",
            '[[ "$observed" =~ ^0:0:555:[1-9][0-9]*$ ]]',
            "C4B_ID_INSTALLED_FILE_OBSERVED",
            'rpm-ostree rollback --reboot',
        ):
            self.assertIn(required, script)
        self.assertLess(script.index("SIGNED_IDENTITY_RPM_VERIFIED_OFFLINE_BEFORE_LAYER"),
                        script.index("rpm-ostree install --cache-only"))
        self.assertLess(script.index('echo rollback_pending > "$stage"'),
                        script.index("rpm-ostree rollback --reboot"))
        self.assertNotIn('"0:0:555:1"', script)
        self.assertIn("SIGNED_INSTALLED_IDENTITY_RPM_FILE_DIGESTS_AND_MODES", script)
        self.assertNotIn('systemctl start "$unit"', script)
        self.assertNotIn("canBeginSignIn=true", script)

    def test_09_real_boot_ci_is_strict_and_never_deploys_to_workstation(self):
        path = ROOT / ".github/workflows/connections-identity-silverblue-real-boot.yml"
        workflow = path.read_text()
        self.assertIn("runs-on: ubuntu-24.04", workflow)
        self.assertIn("sudo chmod a+rw /dev/kvm", workflow)
        self.assertIn("timeout-minutes: 75", workflow)
        self.assertIn("POST_APOLLO_ID_SILVERBLUE_CI_ONLY: '1'", workflow)
        self.assertIn("fedora:44", workflow)
        self.assertIn("run_official_silverblue_identity.sh", workflow)
        self.assertIn("Confirm test did not activate sign-in or production authority", workflow)
        self.assertNotIn("sudo rpm-ostree install", workflow)
        self.assertNotIn("ssh ", workflow)


    def test_10_real_signed_denial_is_supervised_and_removed_before_rollback(self):
        guest = (AREA / "guest_identity_ostree_cycle.sh").read_text()
        host = (AREA / "run_official_silverblue_identity.sh").read_text()
        probe = (AREA / "guest_identity_service_probe.sh").read_text()
        workflow = (ROOT / ".github/workflows/connections-identity-silverblue-real-boot.yml").read_text()
        for needle in (
            "GUEST_RPM_VERIFIER_HELPER_MISSING_OR_MODIFIED_MODE",
            'service_probe=/usr/local/libexec/postapollo-id-ci-service-probe.sh',
            "REAL_SYSTEMD_DENY_ONLY_IDENTITY_SERVICE_PROBE_REFUSED",
            "REAL_IDENTITY_SERVICE_PROBE_FINISHED_BEFORE_ROLLBACK",
            "POSTROLLBACK_DISPOSABLE_TEST_USER_LEFTOVER",
            "POSTROLLBACK_TEST_PRIVATE_KEY_OR_RUNTIME_LEFTOVER",
        ):
            self.assertIn(needle, guest)
        self.assertLess(guest.index('REAL_IDENTITY_SERVICE_PROBE_FINISHED_BEFORE_ROLLBACK'),
                        guest.index('rpm-ostree rollback --reboot'))
        for needle in (
            'guest_identity_service_probe.sh',
            'chmod 0700 /usr/local/libexec/postapollo-id-ci-service-probe.sh',
            'REAL_SYSTEMD_UNIT_REFUSED_WITHOUT_MARKER',
            'REAL_SYSTEMD_IDENTITY_GATEWAY_SOCKET_AND_PROCESS_OBSERVED',
            'REAL_RUNNING_IDENTITY_DENY_ONLY_SERVICE_CLEANUP',
        ):
            self.assertIn(needle, host)
        for action in ("BEGIN", "STATUS", "CANCEL", "RECOVER"):
            self.assertIn(f"INSTALLED_SIGNED_UNAVAILABLE_{action}", host)
        for needle in (
            '[[ "$(id -u)" == 0 && -e /run/ostree-booted',
            '"$(getenforce)" == Enforcing',
            'post-apollo-identity-silverblue-ci.service',
            'REAL_SYSTEMD_UNIT_REFUSED_WITHOUT_MARKER',
            'systemctl show "$unit" --property=MainPID',
            'systemctl show "$unit" --property=ControlGroup',
            '"/proc/$pid/status"',
            '"/proc/$pid/attr/current"',
            'signed_command_receipt_v0 import build_request,verify_receipt',
            '("BEGIN","STATUS","CANCEL","RECOVER")',
            'receipt["state"]!="UNAVAILABLE"',
            'chmod 0600 "$signer"',
            'systemctl stop "$unit"',
            'rm -rf -- "$base"',
            'userdel "$name"',
            'REAL_RUNNING_IDENTITY_DENY_ONLY_SERVICE_CLEANUP',
            'NO_PRODUCTION_RELEASE_ENROLLMENT_OR_C5_OPERATOR_CONSENT',
            'socket.SO_PEERCRED',
            'pinned_start=start_ticks()',
            'check_origin(f"before {action}")',
            'check_origin(f"after {action}")',
            'KERNEL_PEER_PID_START_AND_SUPERVISOR_RECHECKED_FOR_FOUR_SIGNED_DENIALS',
            'C4B_ID_SERVICE_PROBE_DETAIL',
            'C4B_ID_SERVICE_PROBE_RC',
            'KERNEL_OR_SIGNED_RECEIPT_CONTINUITY_REFUSED',
        ):
            self.assertIn(needle, probe)
        self.assertIn("SERVICE_PROBE_DETAIL|SERVICE_PROBE_RC", host)
        self.assertNotIn("https://", probe)
        self.assertNotIn("curl ", probe)
        self.assertNotIn("pip install", probe)
        self.assertNotIn("oauth", probe.lower())
        self.assertIn('bash -n tests/connections/identity_silverblue/guest_identity_service_probe.sh', workflow)


    def test_11_offline_fedora_runtime_is_separately_signed_and_rollback_bound(self):
        downloader = (AREA / "fetch_offline_fedora_crypto.sh").read_text()
        guest = (AREA / "guest_identity_ostree_cycle.sh").read_text()
        host = (AREA / "run_official_silverblue_identity.sh").read_text()
        workflow = (ROOT / ".github/workflows/connections-identity-silverblue-real-boot.yml").read_text()
        for required in (
            'fingerprint=36F612DCF27F7D1A48A835E4DBFCF71C6D9F90A6',
            'rpm_name=python3-cryptography-50.0.0-1.fc44.x86_64.rpm',
            'python3-cffi|2.0.0|3.fc44|x86_64',
            'python3-pycparser|2.22|8.fc44|noarch',
            'identity-python3-cffi-f44.rpm',
            'identity-python3-pycparser-f44.rpm',
            'python3-cffi-2.0.0-3.fc44.x86_64.rpm',
            'python3-pycparser-2.22-8.fc44.noarch.rpm',
            'RPM-GPG-KEY-fedora-44-primary',
            'FEDORA44_KEY_FINGERPRINT_MISMATCH',
            'FEDORA_SIGNER_PRETRUST_REFUSAL_MISSING',
            'FEDORA_SIGNED_RUNTIME_INVALID',
            'FEDORA_RUNTIME_SIGNATURE_NOT_TRUSTED',
            'identity-fedora44-runtime-manifest.sha256',
            'OFFICIAL_FEDORA44_ED25519_RUNTIME_RPM_INDEPENDENTLY_SIGNED_AND_PINNED',
        ):
            self.assertIn(required, downloader)
        for required in (
            'identity-fedora44-runtime-manifest.sha256',
            'VENDOR_SIGNER_PRETRUST_REFUSAL_MISSING',
            'VENDOR_RPM_SIGNATURE_INVALID',
            'identity-python3-cryptography-f44.rpm',
            'rpm-ostree install --cache-only',
            'OFFLINE_SIGNED_FEDORA_ED25519_RUNTIME_BOOTED_AND_VERIFIED',
            'rpm -V --nomtime "$name"',
            'python3-cffi|2.0.0|3.fc44|x86_64',
            'python3-pycparser|2.22|8.fc44|noarch',
            'identity-python3-cffi-f44.rpm',
            'identity-python3-pycparser-f44.rpm',
            'for vendorpkg in python3-cryptography python3-cffi python3-pycparser; do',
            'FEDORA_ED25519_TEST_RUNTIME_REMAINS_AFTER_ROLLBACK',
        ):
            self.assertIn(required, guest)
        self.assertLess(guest.index('SIGNED_OFFLINE_FEDORA44_ED25519_DEPENDENCY_VERIFIED'),
                        guest.index('rpm-ostree install --cache-only'))
        self.assertLess(guest.index('OFFLINE_SIGNED_FEDORA_ED25519_RUNTIME_BOOTED_AND_VERIFIED'),
                        guest.index('REAL_IDENTITY_SERVICE_PROBE_FINISHED_BEFORE_ROLLBACK'))
        self.assertLess(guest.index('FEDORA_ED25519_TEST_RUNTIME_REMAINS_AFTER_ROLLBACK'),
                        guest.index('REAL_SILVERBLUE_IDENTITY_RPM_LAYER_REMOVED'))
        for required in (
            'runtime_dir="$2"',
            'identity-fedora44-runtime-manifest.sha256',
            'identity-fedora44-runtime-public.asc',
            'identity-python3-cryptography-f44.rpm',
            'identity-python3-cffi-f44.rpm',
            'identity-python3-pycparser-f44.rpm',
            'SIGNED_OFFLINE_FEDORA44_ED25519_DEPENDENCY_VERIFIED',
            'OFFLINE_SIGNED_FEDORA_ED25519_RUNTIME_BOOTED_AND_VERIFIED',
        ):
            self.assertIn(required, host)
        for required in (
            'fetch_offline_fedora_crypto.sh',
            'Obtain exact official Fedora 44 signed offline Ed25519 runtime',
            '"$RUNNER_TEMP/c4b-identity-fedora-crypto"',
        ):
            self.assertIn(required, workflow)
        self.assertIn('rpm-ostree install --cache-only', guest)
        self.assertIn('for pattern in (expected,vendor,cffi,pycparser)', guest)
        self.assertEqual(host.count("-nic none"), 2)
        self.assertNotIn("pip install", guest)
        self.assertNotIn("pip install", host)


    def test_12_embedded_kernel_peer_python_compiles_without_vm(self):
        # Catch Python heredoc regressions BEFORE an expensive offline boot.
        probe = (AREA / "guest_identity_service_probe.sh").read_text()
        prefix = "<<'PY' || probe_rc=\"$?\"\n"
        self.assertEqual(probe.count(prefix), 1)
        program = probe.split(prefix, 1)[1].split("\nPY\n", 1)[0]
        self.assertIn("socket.SO_PEERCRED", program)
        self.assertIn('if peer!=(pid,uid,gid):', program)
        self.assertIn("check_origin(f\"before {action}\")", program)
        self.assertIn("check_origin(f\"after {action}\")", program)
        compile(program, "guest_identity_service_probe.sh:kernel-peer-python", "exec")
        module = ast.parse(program)
        lsm_function = next(
            node for node in module.body
            if isinstance(node, ast.FunctionDef) and node.name == "read_kernel_lsm"
        )
        scope = {}
        exec(compile(ast.Module(body=[lsm_function], type_ignores=[]),
                     "<isolated-kernel-lsm-decoder>", "exec"), scope)
        decoder = scope["read_kernel_lsm"]

        class KernelBytes:
            def __init__(self, value):
                self.value = value

            def read_bytes(self):
                return self.value

        expected = "system_u:system_r:postapollo_identity_ci_t:s0"
        self.assertEqual(decoder(KernelBytes(expected.encode() + b"\x00")), expected)
        self.assertEqual(decoder(KernelBytes(expected.encode())), expected)
        for malformed in (b"", b"\x00", b"label\x00suffix",
                          b"label\n", b"label\x00\x00",
                          b"label\xff"):
            with self.subTest(malformed=malformed):
                with self.assertRaises((RuntimeError, UnicodeError)):
                    decoder(KernelBytes(malformed))


    def test_13_real_selinux_domain_is_offline_loaded_and_removed(self):
        probe = (AREA / "guest_identity_service_probe.sh").read_text()
        guest = (AREA / "guest_identity_ostree_cycle.sh").read_text()
        host = (AREA / "run_official_silverblue_identity.sh").read_text()
        workflow = (ROOT / ".github/workflows/connections-identity-silverblue-real-boot.yml").read_text()
        policy_build = (AREA / "selinux/build_policy_ci.sh").read_text()
        policy = (AREA / "selinux/postapollo_identity_ci.te").read_text()
        for required in (
            'postapollo_identity_ci_t',
            'postapollo_identity_ci_exec_t',
            'init_daemon_domain(postapollo_identity_ci_t, postapollo_identity_ci_exec_t)',
            'init_nnp_daemon_domain(postapollo_identity_ci_t)',
            'manage_sock_files_pattern(postapollo_identity_ci_t',
        ):
            self.assertIn(required, policy)
        for denied in ('permissive postapollo_identity_ci_t',
                       'unconfined_domain(postapollo_identity_ci_t)',
                       'allow postapollo_identity_ci_t self:tcp_socket'):
            self.assertNotIn(denied, policy)
        for required in (
            'postapollo_identity_ci.pp',
            'postapollo_identity_ci.sha256',
            'EXACT_COMPILED_POLICY_STAGED_FOR_READONLY_OFFLINE_GUEST',
        ):
            self.assertIn(required, policy_build)
        for required in (
            'OFFLINE_TEST_SELINUX_MODULE_HASH_BOUND_BEFORE_LAYER',
            'POSTROLLBACK_TEST_SELINUX_MODULE_REMAINS',
            'POSTROLLBACK_SELINUX_UNIT_OVERRIDE_LEFTOVER',
        ):
            self.assertIn(required, guest)
        for required in (
            'policy_dir="$3"',
            'postapollo_identity_ci.pp',
            'COMPILED_TEST_SELINUX_POLICY_DIGEST_REFUSED',
            'REAL_ENFORCING_DEDICATED_SELINUX_DOMAIN_OBSERVED',
            'DEDICATED_SELINUX_MODULE_REMOVED_AFTER_SERVICE_STOP',
        ):
            self.assertIn(required, host)
        for required in (
            'Compile test-only SELinux daemon domain into verified offline VM seed',
            'c4b-identity-selinux-policy',
            'postapollo_identity_ci.sha256',
        ):
            self.assertIn(required, workflow)
        for required in (
            'semodule -i "$policyfile"',
            'semodule -r postapollo_identity_ci',
            'chcon -t postapollo_identity_ci_exec_t "$launcher"',
            'chcon -t postapollo_identity_ci_run_t',
            'install -m 0555 /usr/bin/python3 "$launcher"',
            'cmp -s /usr/bin/python3 "$launcher"',
            'ExecStart=/run/postapollo-identity-silverblue-ci-only/ci-python3',
            "system_u:system_r:postapollo_identity_ci_t:s0",
            'REAL_ENFORCING_DEDICATED_SELINUX_DOMAIN_OBSERVED',
            'DEDICATED_SELINUX_MODULE_REMOVED_AFTER_SERVICE_STOP',
        ):
            self.assertIn(required, probe)
        self.assertLess(probe.index('semodule -i "$policyfile"'),
                        probe.index('systemctl start "$unit" ||\n  fail "ACTUAL_SIGNED_INSTALLED_SERVICE_START_REFUSED"'))
        self.assertNotIn('setenforce 0', probe)
        signed_unit = (AREA / "post-apollo-identity-silverblue-ci.service").read_text()
        self.assertIn('NoNewPrivileges=true', signed_unit)
        self.assertNotIn('NoNewPrivileges=false', signed_unit)
        self.assertNotIn('NoNewPrivileges=false', probe)
        self.assertNotIn('SELinuxContext=-', probe)
        self.assertNotIn('allow postapollo_identity_ci_t self:tcp_socket', policy)
        self.assertIn('init_nnp_daemon_domain(postapollo_identity_ci_t)', policy)
        self.assertIn('[[ "$selinux" == \'system_u:system_r:postapollo_identity_ci_t:s0\' &&', probe)
        self.assertNotIn('semodule -DB', probe)
        self.assertNotIn('permissive ', probe)


    def test_14_real_selinux_negative_probe_is_independent_and_syntax_valid(self):
        probe = (AREA / "guest_identity_service_probe.sh").read_text()
        host = (AREA / "run_official_silverblue_identity.sh").read_text()
        prefix = 'cat >"$denial" <<\'PY\'\n'
        self.assertEqual(probe.count(prefix), 1)
        program = probe.split(prefix, 1)[1].split("\nPY\n", 1)[0]
        compile(program, "disposable-selinux-negative.py", "exec")
        for needle in (
            'socket.AF_INET', 'socket.SOCK_STREAM', 'errno.EACCES',
            'errno.EPERM', 'postapollo_identity_ci_t:s0',
            'SELINUX_DOMAIN_ALLOWED_INET_SOCKET_CREATE'
        ):
            self.assertIn(needle, program)
        self.assertIn('REAL_SELINUX_DOMAIN_DENIED_INET_SOCKET_CREATE', host)
        self.assertIn('DEDICATED_SELINUX_MODULE_REMOVED_AFTER_SERVICE_STOP', host)
        self.assertNotIn('systemd-run --wait --pipe --collect \\\n', probe)
        self.assertIn('negative_unit_file="/run/systemd/system/$negative_unit"', probe)
        self.assertIn('Type=oneshot', probe)
        self.assertIn('NoNewPrivileges=true', probe)
        self.assertIn('StandardOutput=journal', probe)
        self.assertIn('StandardError=journal', probe)
        self.assertIn('journalctl -b -u "$negative_unit"', probe)
        self.assertIn('systemctl start "$negative_unit"', probe)
        self.assertIn('systemctl stop "$negative_unit"', probe)
        self.assertIn('negative_result="$(systemctl show "$negative_unit" --property=Result --value)"', probe)
        self.assertIn('"$negative_result" == success', probe)
        self.assertIn('"$(grep -Fc \'C4B_ID_NEGATIVE_WITNESS // KERNEL_AF_INET_CREATE_DENIED\' "$negative_journal")" == 1', probe)
        self.assertIn('C4B_ID_NEGATIVE_WITNESS // KERNEL_AF_INET_CREATE_DENIED', program)
        self.assertNotIn('C4B_ID_PASS // REAL_SELINUX_DOMAIN_DENIED_INET_SOCKET_CREATE', program)
        self.assertEqual(
            probe.count('echo "C4B_ID_PASS // REAL_SELINUX_DOMAIN_DENIED_INET_SOCKET_CREATE" >/dev/ttyS0'),
            1,
        )
        self.assertIn('! grep -Fq \'C4B_ID_FAIL //\' "$negative_journal"', probe)
        self.assertIn('[[ ! -e "$base" && ! -e "$dropindir" && ! -e "$negative_unit_file" ]]', probe)
        # A deny-only proof cannot rely on any other network sandbox.
        transient = probe.split("cat >\"$negative_unit_file\" <<'CI_ID_NEGATIVE_UNIT'\n", 1)[1].split(
            "\nCI_ID_NEGATIVE_UNIT", 1)[0]
        for forbidden in (
            'RestrictAddressFamilies', 'PrivateNetwork', 'NetworkNamespace',
            'SystemCallFilter', 'SocketBindAllow', 'IPAddressDeny'
        ):
            self.assertNotIn(forbidden, transient)
        self.assertIn('ExecStart=/run/postapollo-identity-silverblue-ci-only/ci-python3', transient)


    def test_15_real_selinux_policy_load_is_bounded_and_diagnostic(self):
        probe = (AREA / "guest_identity_service_probe.sh").read_text()
        host = (AREA / "run_official_silverblue_identity.sh").read_text()
        for marker in (
            'C4B_ID_SELINUX_STAGE // before_module_install',
            'C4B_ID_SELINUX_STAGE // after_module_install rc=%s',
            'C4B_ID_SELINUX_STAGE // before_module_unload',
            'C4B_ID_SELINUX_STAGE // after_module_unload rc=%s',
            'timeout --signal=TERM --kill-after=4s 150s semodule -i',
            'timeout --signal=TERM --kill-after=4s 150s semodule -r',
            'COMPILED_SELINUX_MODULE_LOAD_REFUSED',
        ):
            self.assertIn(marker, probe)
        for marker in (
            'C4B_ID_BLOCKED // REAL_ENFORCING_SELINUX_POLICY_LOAD_STALLED',
            'selinux_load_started=0',
            'SECONDS - selinux_load_started > 205',
            'SELINUX_STAGE|SELINUX_MODULE_DETAIL|SELINUX_LOAD_DETAIL|SELINUX_UNLOAD_DETAIL',
        ):
            self.assertIn(marker, host)
        self.assertNotIn('setenforce 0', probe)


    def test_16_selinux_module_list_failure_is_serial_visible_and_fail_closed(self):
        probe = (AREA / "guest_identity_service_probe.sh").read_text()
        host = (AREA / "run_official_silverblue_identity.sh").read_text()
        self.assertIn("printf 'C4B_ID_FAIL // IDENTITY_SERVICE_%s", probe)
        self.assertIn('"$1" >/dev/ttyS0 || true', probe)
        for token in (
            'module_list=/var/tmp/c4b-id-selinux-module-list.log',
            'timeout --signal=TERM --kill-after=3s 25s semodule -l',
            'C4B_ID_SELINUX_STAGE // module_list_rc=%s',
            'C4B_ID_SELINUX_MODULE_DETAIL',
            'COMPILED_SELINUX_MODULE_LIST_REFUSED',
            'COMPILED_SELINUX_MODULE_NOT_ACTIVE',
            'C4B_ID_SELINUX_STAGE // module_name_verified',
            'C4B_ID_SELINUX_STAGE // enforcing_state=%.40s',
        ):
            self.assertIn(token, probe)
        self.assertIn('SELINUX_STAGE|SELINUX_MODULE_DETAIL|SELINUX_LOAD_DETAIL', host)
        self.assertIn("grep -Eq '^postapollo_identity_ci([[:space:]]|$)'", probe)
        self.assertLess(probe.index('semodule -i "$policyfile"'), probe.index('module_list=/var/tmp'))
        self.assertLess(probe.index('module_name_verified'), probe.index('DEDICATED_TEST_SELINUX_MODULE_LOADED_ENFORCING'))


    def test_17_unhandled_selinux_guest_error_is_serial_visible_and_bounded(self):
        probe = (AREA / "guest_identity_service_probe.sh").read_text()
        host = (AREA / "run_official_silverblue_identity.sh").read_text()
        self.assertIn("trap 'on_unhandled_error \"$?\" \"$LINENO\"' ERR", probe)
        for line in (
            'C4B_ID_FAIL // IDENTITY_SERVICE_UNHANDLED_SHELL_ERROR line=%s rc=%s',
            'C4B_ID_SELINUX_STAGE // before_nonroot_runtime_preparation',
            'C4B_ID_SELINUX_STAGE // nonroot_user_prepared',
            'C4B_ID_SELINUX_STAGE // runtime_and_signer_prepared',
            'C4B_ID_SELINUX_STAGE // before_confined_systemd_start',
        ):
            self.assertIn(line, probe)
        self.assertLess(probe.index('before_nonroot_runtime_preparation'),
                        probe.index('nonroot_user_prepared'))
        self.assertLess(probe.index('nonroot_user_prepared'),
                        probe.index('runtime_and_signer_prepared'))
        self.assertLess(probe.index('runtime_and_signer_prepared'),
                        probe.index('before_confined_systemd_start'))
        self.assertIn("C4B_ID_(PASS|FAIL|STAGE|BLOCKED", host)


    def test_18_observed_kernel_selinux_witness_goes_to_durable_guest_uart(self):
        probe = (AREA / "guest_identity_service_probe.sh").read_text()
        host = (AREA / "run_official_silverblue_identity.sh").read_text()
        required = (
            'C4B_ID_SELINUX_OBSERVED // %.180s\\n',
            'REAL_ENFORCING_DEDICATED_SELINUX_DOMAIN_OBSERVED',
            'C4B_ID_SERVICE_OBSERVED // pid=%s',
            'REAL_SYSTEMD_IDENTITY_GATEWAY_SOCKET_AND_PROCESS_OBSERVED',
        )
        for marker in required:
            self.assertIn(marker, probe)
        self.assertIn(
            """printf 'C4B_ID_SELINUX_OBSERVED // %.180s\\n' "$selinux" >/dev/ttyS0""",
            probe,
        )
        self.assertIn(
            'echo "C4B_ID_PASS // REAL_ENFORCING_DEDICATED_SELINUX_DOMAIN_OBSERVED" >/dev/ttyS0',
            probe,
        )
        self.assertIn('C4B_ID_(PASS|FAIL|STAGE|BLOCKED', host)
        self.assertIn('SELINUX_OBSERVED|SELINUX_STAGE', host)
        for marker in (
            'C4B_ID_PASS\\ //*) echo "$line" >/dev/ttyS0 ;;',
            'C4B_ID_SERVICE_PROBE_RC // $probe_rc" >/dev/ttyS0',
            'C4B_ID_PASS // REAL_SELINUX_DOMAIN_DENIED_INET_SOCKET_CREATE" >/dev/ttyS0',
            'C4B_ID_PASS // DEDICATED_SELINUX_MODULE_REMOVED_AFTER_SERVICE_STOP" >/dev/ttyS0',
            'C4B_ID_PASS // REAL_RUNNING_IDENTITY_DENY_ONLY_SERVICE_CLEANUP" >/dev/ttyS0',
        ):
            self.assertIn(marker, probe)
        # An observed label must precede the unchanged full-domain comparison.
        self.assertLess(probe.index('printf \'C4B_ID_SELINUX_OBSERVED'),
                        probe.index("system_u:system_r:postapollo_identity_ci_t:s0' &&"))


    def test_19_fedora44_kvm_container_survives_unavailable_ubuntu_mirror(self):
        workflow = (ROOT / ".github/workflows/connections-identity-silverblue-real-boot.yml").read_text()
        guest = (AREA / "run_official_silverblue_identity.sh").read_text()
        for token in (
            'Real official offline Silverblue VM in disposable Fedora 44 KVM container',
            'test "$GITHUB_ACTIONS" = true',
            'test "$RUNNER_ENVIRONMENT" = github-hosted',
            'test "$GITHUB_ACTOR" = kudokudo1',
            'test -c /dev/kvm && test -r /dev/kvm && test -w /dev/kvm',
            '--device=/dev/kvm',
            '--env RUNNER_TEMP=/tmp',
            '--env POST_APOLLO_ID_SILVERBLUE_CI_ONLY=1',
            '--mount "type=bind,src=$PWD,dst=/src,readonly"',
            'dst=/evidence/rpm,readonly',
            'dst=/evidence/crypto,readonly',
            'dst=/evidence/selinux,readonly',
            'fedora:44 /usr/bin/bash -c',
            'dnf -y --setopt=install_weak_deps=False --setopt=gpgcheck=1 install',
            'curl qemu-system-x86 qemu-img xorriso genisoimage',
            'C4B_ID_PASS // FEDORA44_SIGNED_QEMU_TOOLING_READY',
            '/src/tests/connections/identity_silverblue/run_official_silverblue_identity.sh',
            '/evidence/rpm /evidence/crypto /evidence/selinux',
        ):
            self.assertIn(token, workflow)
        for forbidden in (
            'apt-get', '--privileged', '--network=host', '--network host',
            'AllowUnauthenticated', 'Verify-Peer=false', 'setenforce 0',
            '--security-opt seccomp=unconfined'
        ):
            self.assertNotIn(forbidden, workflow)
        self.assertIn('-nic none', guest)
        self.assertIn('[[ -c /dev/kvm && -r /dev/kvm && -w /dev/kvm ]]', guest)
        self.assertLess(workflow.index('FEDORA44_SIGNED_QEMU_TOOLING_READY'),
                        workflow.index('/src/tests/connections/identity_silverblue/run_official_silverblue_identity.sh'))


    def test_20_failure_retains_bounded_guest_markers_without_exposing_vm_transcript(self):
        workflow = (ROOT / ".github/workflows/connections-identity-silverblue-real-boot.yml").read_text()
        for required in (
            'vm_evidence="$RUNNER_TEMP/c4b-identity-vm-guest-markers.log"',
            'vm_raw="$RUNNER_TEMP/c4b-identity-vm-full-ci.log"',
            '2>&1 | tee "$vm_raw"',
            'vm_rc="${PIPESTATUS[0]}"',
            'C4B_ID_(PASS|FAIL|BLOCKED|STAGE|SELINUX_[A-Z_]+|SERVICE_[A-Z_]+)',
            'tail -n 180 >"$vm_evidence"',
            'C4B_ID_VM_PROCESS_EXIT // %s',
            'exit "$vm_rc"',
            'Preserve bounded real-guest C4b marker evidence',
            'if: always()',
            'actions/upload-artifact@v4',
            'name: c4b-identity-silverblue-guest-markers',
            'path: ${{ runner.temp }}/c4b-identity-vm-guest-markers.log',
            'retention-days: 1',
        ):
            self.assertIn(required, workflow)
        self.assertNotIn('path: ${{ runner.temp }}/c4b-identity-vm-full-ci.log', workflow)
        self.assertNotIn('upload-artifact@v3', workflow)
        self.assertLess(workflow.index('exit "$vm_rc"'),
                        workflow.index('Preserve bounded real-guest C4b marker evidence'))


    def test_21_final_success_limitations_match_real_confinement_evidence(self):
        host = (AREA / "run_official_silverblue_identity.sh").read_text()
        document = (ROOT / "docs/connections-identity-silverblue-install-contract-v1.md").read_text()
        self.assertIn(
            'C4B_ID_LIMITATION // CI_ONLY_CONFIRMED_CONFINEMENT_NO_INDEPENDENT_RELEASE_ROOT_SEAT_OR_C5_CONSENT',
            host,
        )
        self.assertNotIn('INERT_GATEWAY_ONLY_NO_SYSTEMD_SELINUX_PROCESS_ATTESTATION', host)
        self.assertLess(
            host.index('C4B_ID_PASS // REAL_ENFORCING_DEDICATED_SELINUX_DOMAIN_OBSERVED'),
            host.index('C4B_ID_LIMITATION // CI_ONLY_CONFIRMED_CONFINEMENT'),
        )
        for required in (
            'postapollo_identity_ci_t',
            'independent AF_INET SELinux denial',
            'combined two-boot rollback remain unverified together',
            'startup_failure',
            'C5 human consent',
        ):
            self.assertIn(required, document)
        self.assertNotIn(
            'Current C4b process-continuity checks and separate compile-only custom policy prototype are pending',
            document,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
