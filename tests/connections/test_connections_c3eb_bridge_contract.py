#!/usr/bin/env python3
"""C3e-B test-only binding of independently signed policy to *staged* RPM."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "tests/connections/c3d_provenance/build_signed_ci_status.sh"
ROOT_BUILDER = ROOT / "tests/connections/c3e_release_trust/build_c3eb_policy_ci.sh"
GUEST = ROOT / "tests/connections/c3d_provenance/guest_signed_service_gate.sh"
BOOT = ROOT / "tests/connections/c2r_selinux_domain/boot_confined_vm.sh"
WORKFLOW = ROOT / ".github/workflows/connections-c3eb-approved-signed-rpm.yml"


class C3eBRpmPolicyBridgeContract(unittest.TestCase):
    def test_01_release_manifest_is_opt_in_and_signed_by_rpm_builder_key(self):
        s = BUILDER.read_text()
        self.assertIn('POST_APOLLO_C3EB_EXPORT_MANIFEST', s)
        self.assertIn('gpg --homedir "$keydir"', s)
        self.assertIn('rpmsign --addsign', s)
        self.assertIn('c3eb-release-manifest.sig', s)
        self.assertIn('expected_outputs=4', s)
        self.assertIn('expected_outputs=6', s)
        self.assertNotIn("--export-secret-keys", s)

    def test_02_runner_root_created_outside_candidate_builder(self):
        s = ROOT_BUILDER.read_text()
        self.assertIn('root_dir="$(realpath "$2")"', s)
        self.assertIn('candidate="$(realpath "$1")"', s)
        self.assertIn('gpg --homedir "$home"', s)
        self.assertIn('root-policy.sig', s)
        self.assertIn('root-pin.txt', s)
        self.assertIn('C3EB_LIMITATION // ROOT_PIN_CREATED_BY_CI_NOT_OPERATOR_ENROLLED', s)
        self.assertNotIn('rpm --import', s)
        self.assertNotIn('systemctl start', s)

    def test_03_guest_pin_is_distinct_input_and_required_before_import(self):
        boot = BOOT.read_text()
        guest = GUEST.read_text()
        self.assertIn('if [[ -v C3EB_APPROVED_SHA256 ]]; then', boot)
        self.assertIn('C3EB_GUEST_ADMISSION_EVIDENCE_MISSING', boot)
        self.assertIn('C3EB_STAGED // ROOT_ADMITTED_RPM_DIGEST_SEPARATE_FROM_CANDIDATE', boot)
        assert_loc = guest.index('sha256sum --check --status c3eb-approved.sha256')
        rpm_import = guest.index('rpm --import "$root/c3d-disposable-public.asc"')
        rpm_install = guest.index('rpm -Uvh "$root/c3d-status.rpm"')
        self.assertLess(assert_loc, rpm_import)
        self.assertLess(assert_loc, rpm_install)
        self.assertIn('C3EB_PASS // GUEST_RPM_DIGEST_MATCHES_ROOT_ADMITTED_BYTES', guest)

    def test_04_ci_verifies_before_staging_and_blocks_substitution(self):
        w = WORKFLOW.read_text()
        self.assertIn('C3eReleaseAdmission.py', w)
        self.assertIn('C3E_PASS // C3E_TEST_POLICY_ACCEPTED_NO_PRODUCTION_AUTH', w)
        self.assertIn('C3E_REFUSED // ROOT_PIN_MISMATCH', w)
        self.assertIn('C3E_REFUSED // ARTIFACT_SIZE_MISMATCH', w)
        self.assertIn('C3E_REFUSED // REVOKED_SIGNER', w)
        self.assertIn('C3EB_APPROVED_SHA256=', w)
        self.assertIn('C3D_SERVICE_RPM_DIR=', w)
        self.assertIn('timeout 570s bash tests/connections/c2r_selinux_domain/boot_confined_vm.sh', w)
        self.assertIn('sha256sum --check --status', w)

    def test_05_no_production_credentials_or_authentication_enabled(self):
        base = ROOT / "services/connections"
        self.assertIn('readonly property bool hostAuthenticated: false',
                      (base / "ConnectionsRequestStatus.qml").read_text())
        self.assertIn('readonly property bool credentialActionsEnabled: false',
                      (base / "ConnectionsBroker.qml").read_text())
        for p in (*base.glob("*.qml"), *base.glob("*.js"), base / "qmldir"):
            self.assertNotIn("C3EB", p.read_text(), p)


if __name__ == "__main__":
    unittest.main(verbosity=2)
