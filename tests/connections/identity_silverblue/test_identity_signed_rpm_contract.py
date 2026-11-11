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
                         "identity-artifact-manifest.sha256"):
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
            'rpm-ostree install --cache-only /var/lib/postapollo-id-ci-assets/identity-silverblue-ci.rpm',
            "C4B_ID_PENDING_EXACT_IDENTITY_DEPLOYMENT",
            "REAL_SILVERBLUE_BOOTED_SIGNED_IDENTITY_RPM_INERT",
            "REAL_SILVERBLUE_IDENTITY_RPM_LAYER_REMOVED",
            "TEST_KEYRING_REMOVED_AND_PRODUCTION_DISABLED",
            '[[ "$enabled_state" == static || "$enabled_state" == disabled ]]',
            'verify_output="$(rpm -V "$pkg" 2>&1)"',
            "SIGNED_IDENTITY_BOOTED_RPM_VERIFY_DIFFERENCE",
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
