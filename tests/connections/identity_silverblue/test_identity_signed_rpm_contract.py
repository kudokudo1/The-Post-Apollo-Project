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
                        text.index('rpmkeys --dbpath "$keydb" --checksig -v "$rpmfile" 2>&1)"'))
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
        self.assertNotIn("production", src.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
