#!/usr/bin/env python3
"""C3d offline source contract; no package install outside disposable CI."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "tests/connections/c3d_provenance"
SPEC = DIR / "signed-status.spec"
BUILDER = DIR / "build_signed_ci_status.sh"
GATE = DIR / "guest_signed_service_gate.sh"
BOOT = ROOT / "tests/connections/c2r_selinux_domain/boot_confined_vm.sh"
GUEST = ROOT / "tests/connections/c2r_selinux_domain/guest_confined_smoke.sh"


class C3dContract(unittest.TestCase):
    def test_01_fixed_service_file_allowlist(self):
        spec = SPEC.read_text()
        file_section = spec.split("%files\n", 1)[1].split("# No %pre", 1)[0]
        actual = {x.strip() for x in file_section.splitlines() if x.startswith("/")}
        self.assertEqual(actual, {
            "/usr/libexec/post-apollo/connections-status-host",
            "/usr/lib/systemd/system/postapollo-connections-status.service",
            "/usr/share/dbus-1/system.d/org.postapollo.ConnectionsStatus1.conf",
        })
        self.assertIn("AutoReqProv:    no", spec)
        self.assertIn("LicenseRef-PostApollo-Test-Only", spec)
        self.assertIn("noarch", spec)
        self.assertNotIn("%post\n", spec)
        self.assertNotIn("%pre\n", spec)
        self.assertNotIn("%trigger\n", spec)
        self.assertNotIn("systemctl start", spec)
        self.assertNotIn("rpm --import", spec)

    def test_02_key_never_exits_disposable_fedora_builder(self):
        source = BUILDER.read_text()
        self.assertIn("rpmsign --addsign", source)
        self.assertIn("trap 'rm -rf", source)
        self.assertIn('gpg --homedir "$keydir"', source)
        self.assertNotIn("--export-secret-keys", source)
        self.assertNotIn("private.key", source)
        self.assertIn('expected_outputs=4', source)
        self.assertIn('expected_outputs=6', source)
        self.assertIn('POST_APOLLO_C3EB_EXPORT_MANIFEST', source)
        self.assertIn('"$(find /out -maxdepth 1 -type f | wc -l)" -eq "$expected_outputs"', source)
        self.assertIn("C3D_LIMITATION // DISPOSABLE_SELF_SIGNED_KEY_NOT_PRODUCTION_TRUST", source)

    def test_03_guest_requires_native_signature_rpmdb_and_negative_tamper(self):
        gate = GATE.read_text()
        for must in (
            "rpmkeys --checksig -v", "SIGNER_NOT_TRUSTED_BEFORE_TEST_IMPORT",
            "rpm --import", "rpm -Uvh", "rpm -V", "rpm -qf",
            "MODIFIED_FAKE_SERVICE_REFUSED_BY_RPM_VERIFY", "--replacepkgs",
            "rpm -e", "SIGNED_FAKE_SERVICE_ERASE_AND_TEST_KEY_CLEANUP",
            "C3D_REFUSED_NOT_DISPOSABLE_GUEST",
        ):
            self.assertIn(must, gate)
        self.assertNotIn("secret-tool", gate)
        self.assertNotIn("POST_APOLLO_FIRMS_MAP_KEY", gate)
        self.assertNotIn("systemctl enable", gate)
        self.assertNotIn("systemctl start", gate)

    def test_04_existing_guest_flow_preserved_and_new_gate_mandatory_when_staged(self):
        boot = BOOT.read_text()
        guest = GUEST.read_text()
        self.assertIn("if [[ -v C3D_SERVICE_RPM_DIR", boot)
        self.assertIn("c3d_requested=1", boot)
        self.assertIn("C3D_PROVENANCE_EVIDENCE_MISSING", boot)
        self.assertIn("C3D_PASS // SIGNED_FAKE_SERVICE_ERASE_AND_TEST_KEY_CLEANUP", boot)
        self.assertIn("if [[ -f /root/c2q/c3d-status.rpm ]]; then", guest)
        self.assertIn("else\n  # Legacy C2r and C2s", guest)
        self.assertIn("C3B_VERIFY_BEGIN", guest)
        self.assertIn("C2R_PASS // SYSTEMD_HOST_DBUS_UNDER_SELINUX_ENFORCING", guest)
        self.assertIn("C2R_PASS // SERVICE_SHUTDOWN_RELEASES_DBUS_NAME", guest)

    def test_05_production_authority_still_disabled(self):
        base = ROOT / "services/connections"
        self.assertIn("readonly property bool credentialActionsEnabled: false",
                      (base / "ConnectionsBroker.qml").read_text())
        self.assertIn("readonly property bool hostAuthenticated: false",
                      (base / "ConnectionsRequestStatus.qml").read_text())
        for path in (*base.glob("*.qml"), *base.glob("*.js"), base / "qmldir"):
            self.assertNotIn("c3d_provenance", path.read_text(), path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
