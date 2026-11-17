"""P52 static allowlisted Fedora RPM / CI-only admission checks.

Real Fedora build, independent signature verification, package install,
rpm -V and erase execute in separate disposable containers in CI.
No operator Silverblue, Identity signer, C3e, C5, or personal keyring access.
"""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
PHONE = ROOT / "services" / "phone"
DIR = ROOT / "tests" / "phone"
SPEC = DIR / "p52_signed_phone_status.spec"
BUILD = DIR / "p52_build_signed_phone_status.sh"
VERIFY = DIR / "p52_verify_installed_phone_rpm.sh"
SERVICE = PHONE / "systemd" / "post-apollo-phone-personal-status-ci.service"
CODE = (
    "PhonePersonalHostSocketP47.py",
    "PhonePersonalPeerEvidenceP48.py",
    "PhonePersonalStatusHostP49.py",
    "PhonePersonalInstalledReleaseP50.py",
)
INSTALLED_FILES = {
    *(f"/usr/libexec/post-apollo/phone/{x}" for x in CODE),
    "/usr/libexec/post-apollo/phone/systemd/post-apollo-phone-personal-status-ci.service",
    "/usr/lib/systemd/system/post-apollo-phone-personal-status-ci.service",
}


class SignedPackageSourceTests(unittest.TestCase):
    def test_spec_exact_six_paths_and_no_auto_action(self):
        text = SPEC.read_text()
        self.assertIn("Name:           post-apollo-phone-status-ci", text)
        self.assertIn("BuildArch:      noarch", text)
        self.assertIn("AutoReqProv:    no", text)
        self.assertIn("%undefine __brp_mangle_shebangs", text)
        self.assertNotRegex(
            text, r"(?m)^%(pre|post|preun|postun|trigger|transfiletrigger)\b",
        )
        paths = set(re.findall(r"(?m)^/usr/(?:libexec|lib)/[^\r\n\s]+$", text))
        self.assertEqual(paths, INSTALLED_FILES)
        self.assertEqual(text.count("install -D -m 0555"), 4)
        self.assertEqual(text.count("install -D -m 0644"), 2)
        self.assertNotIn("systemctl enable", text)
        self.assertNotIn("secret-tool", text)
        self.assertNotIn("PHONE_MASTER_KEY", text)

    def test_inert_unit_contains_only_status_command(self):
        source = SERVICE.read_text()
        self.assertIn("User=postapollo-phone-status-ci", source)
        self.assertIn("Group=postapollo-phone-status-ci", source)
        self.assertIn("NoNewPrivileges=true", source)
        self.assertIn("RestrictAddressFamilies=AF_UNIX", source)
        self.assertIn("CapabilityBoundingSet=", source)
        self.assertIn("POST_APOLLO_PHONE_STATUS_NO_SAVE=1", source)
        self.assertNotRegex(source, r"(?m)^\[Install\]$")
        self.assertNotRegex(source, r"(?m)^WantedBy=")
        self.assertNotIn("ExecStartPost=", source)
        self.assertNotIn("PhonePersonalContactVault.py", source)

    def test_scripts_parse_and_require_true_ephemeral_ci(self):
        for script in (BUILD, VERIFY):
            with self.subTest(script=script.name):
                check = subprocess.run(
                    ["/usr/bin/bash", "-n", str(script)],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    timeout=3, check=False,
                )
                self.assertEqual(check.returncode, 0, check.stderr.decode()[:600])
                src = script.read_text()
                self.assertIn('GITHUB_ACTIONS:-', src)
                self.assertIn('RUNNER_ENVIRONMENT:-', src)
                self.assertIn('POST_APOLLO_PHONE_RPM_CI_ONLY:-', src)
                self.assertIn('$(id -u)', src)
                self.assertNotIn('POST_APOLLO_ID_SILVERBLUE_CI_ONLY', src)
                self.assertNotIn('systemctl enable', src)
                self.assertNotIn('PhonePersonalSaveOrchestratorP44', src)
                self.assertNotIn('PhonePersonalContactVault.py', src)

    def test_exact_source_protected_in_build_and_verified_again_after_install(self):
        build = BUILD.read_text()
        verify = VERIFY.read_text()
        for path in CODE:
            self.assertTrue((PHONE / path).is_file())
            self.assertIn(path, build)
            self.assertIn(path, verify)
        self.assertIn('rpm2cpio "$rpmfile"', build)
        self.assertIn('cmp -s "$dst"', build)
        self.assertIn('rpmsign --addsign', build)
        self.assertIn('phone-status-disposable-rpm-public.asc', build)
        self.assertIn('rpmkeys --dbpath "$db" --checksig', verify)
        self.assertIn('rpmkeys --dbpath "$db" --import "$public"', verify)
        self.assertIn('rpm -ivh --nodeps "$rpmfile"', verify)
        self.assertIn('rpm -V --nomtime "$package"', verify)
        self.assertIn('rpm -e "$package"', verify)
        self.assertIn('P52_LIMITATION // NO_SILVERBLUE_OSTREE_BOOT', verify)

    def test_original_public_runtime_status_does_not_grant_save(self):
        import sys
        sys.path.insert(0, str(PHONE))
        import PhonePersonalHostSocketP47 as socket_host
        import PhonePersonalInstalledReleaseP50 as release
        for field in (
            "installedIdentityVerified",
            "independentChallengeVerified", "c5OneUseConsentVerified",
            "keyReadAuthorized", "productionEnabled",
            "personalSaveAuthorized", "readbackTrusted", "retryAuthorized",
        ):
            self.assertIs(socket_host.STATUS[field], False)
        self.assertIs(release.RESULT["personalSaveAuthorized"], False)
        self.assertIs(release.RESULT["installedHostVerified"], False)


if __name__ == "__main__":
    unittest.main()
