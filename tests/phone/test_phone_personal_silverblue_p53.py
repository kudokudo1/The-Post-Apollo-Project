"""P53 official Fedora Silverblue PHONE real-KVM static safety and shape guards.

The expensive real VM lifecycle has a separate dedicated GitHub CI workflow.
These checks never install anything on the operator workstation.
"""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "tests" / "phone"
FILES = (
    DIR / "p53_run_official_silverblue_phone.sh",
    DIR / "p53_guest_phone_ostree_cycle.sh",
    DIR / "p53_guest_phone_service_probe.sh",
    DIR / "p53_selinux/build_policy_ci.sh",
)
TE = DIR / "p53_selinux/postapollo_phone_ci.te"
PACKAGE = DIR / "p52_signed_phone_status.spec"
UNIT = ROOT / "services/phone/systemd/post-apollo-phone-personal-status-ci.service"


class SilverblueGuestSafety(unittest.TestCase):
    def test_all_guest_scripts_have_valid_bash_syntax(self):
        for f in FILES:
            self.assertTrue(f.is_file(), f)
            result = subprocess.run(
                ["/usr/bin/bash", "-n", str(f)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                check=False, timeout=4,
            )
            with self.subTest(f=f.name):
                self.assertEqual(result.returncode, 0, result.stderr.decode()[:600])
                self.assertIn("set -Eeuo pipefail", f.read_text())

    def test_official_iso_pin_and_host_guest_nonnetwork_boundaries(self):
        host = FILES[0].read_text()
        for required in (
            "GITHUB_ACTOR", "RUNNER_ENVIRONMENT",
            "POST_APOLLO_PHONE_RPM_CI_ONLY",
            "9ccec9b075a0a4358a7209b2667156aaeeec3a6a3c8d71cada45b57fca9b4682",
            "Fedora-Silverblue-ostree-x86_64-44-1.7.iso",
            "inst.repo=cdrom", "inst.ks=hd:LABEL=PH53CI:/ks.cfg",
            "-nic none", "-machine accel=kvm",
            "sha256sum --check --status",
            "P53_PASS // OFFICIAL_SILVERBLUE_SIGNED_PHONE_RPM_CONFINED_SERVICE_TWO_BOOT_ROLLBACK",
        ):
            self.assertIn(required, host)
        self.assertNotIn("POST_APOLLO_ID_SILVERBLUE_CI_ONLY", host)
        self.assertNotIn("identity-gateway", host.lower())
        self.assertNotIn("secret-tool", host)
        self.assertNotIn("PhonePersonalContactVault", host)
        self.assertIn("ConditionPathExists=/run/ostree-booted", host)

    def test_guest_requires_exact_pending_deployment_before_reboot(self):
        cycle = FILES[1].read_text()
        for exact in (
            "rpm-ostree status --json",
            "requested-local-packages",
            "rpm-ostree install --cache-only",
            "systemd-run --quiet --unit=p53-phone-layer-monitor",
            "systemd-run --quiet --unit=p53-phone-layer-worker",
            "P53_PASS // REAL_PHONE_RPM_OSTREE_PENDING_DEPLOYMENT",
            "rpm-ostree rollback --reboot",
            "rpm -V --nomtime",
            "P53_PASS // REAL_SILVERBLUE_PHONE_RPM_LAYER_REMOVED_AFTER_TWO_REBOOTS",
        ):
            self.assertIn(exact, cycle)
        self.assertIn("post-apollo-phone-status-ci", cycle)
        self.assertIn("phone-status-disposable-rpm-public.asc", cycle)
        self.assertNotIn("post-apollo-identity-silverblue-ci", cycle)
        self.assertNotIn("PhonePersonalSaveOrchestrator", cycle)
        self.assertNotIn("C5OneUseConsentVerified\": True", cycle)

    def test_distinct_no_network_selinux_policy_compiler_and_real_guest_process(self):
        policy = TE.read_text()
        self.assertIn("policy_module(postapollo_phone_ci, 1.0.0)", policy)
        self.assertIn("init_daemon_domain(postapollo_phone_ci_t", policy)
        self.assertIn("init_nnp_daemon_domain(postapollo_phone_ci_t)", policy)
        self.assertIn("create_stream_socket_perms", policy)
        for forbidden in (
            "unconfined_domain(", "permissive ", "tcp_socket",
            "udp_socket", "allow postapollo_phone_ci_t domain:process",
        ):
            self.assertNotIn(forbidden, policy)
        probe = FILES[2].read_text()
        for required in (
            "semodule -i", "semodule -r",
            "postapollo_phone_ci_t:s0",
            "systemctl show", '"/proc/$pid/status"',
            "ExecStart=/run/postapollo-phone-status-test-only/ci-python3",
            "HOST_UNTRUSTED_STATUS_ONLY",
            '"personalSaveAuthorized"',
            "P53_PASS // REAL_ENFORCING_PHONE_DOMAIN_AND_SYSTEMD_PROCESS_OBSERVED",
        ):
            self.assertIn(required, probe)
        self.assertIn("NoNewPrivileges=true", UNIT.read_text())
        self.assertNotIn("[Install]", UNIT.read_text().split("# Deliberately")[0])
        self.assertIn("post-apollo-phone-status-ci", PACKAGE.read_text())
        self.assertNotIn("PhonePersonalContactVault", probe)

    def test_no_prod_root_or_operator_host_write_authorization(self):
        for f in FILES:
            text = f.read_text()
            self.assertNotIn("HOME/.config", text)
            self.assertNotIn("systemctl enable post-apollo-phone-personal-status-ci", text)
            self.assertNotIn("rpm-ostree override replace", text)
            self.assertNotIn("import dbus", text)
            self.assertNotIn("PhonePersonalKeyProvision", text)
            self.assertNotIn("Vault.commit(", text)
        host = FILES[0].read_text()
        self.assertIn("run_official", FILES[0].name)
        self.assertIn("run_official", FILES[0].name)
        self.assertIn("GITHUB_ACTIONS", host)


if __name__ == "__main__":
    unittest.main()
