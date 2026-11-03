"""Guarantee native structure smoke is isolated and never mounted in live QS."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
QML = (ROOT / "LocalOrganizationStructureNativeSmokeV1.qml").read_text()
RUNNER = (ROOT / "tests/identity/native_local_organization_structure_smoke_v1.py").read_text()
SHELL = (ROOT / "shell.qml").read_text()
WORKFLOW = (ROOT / ".github/workflows/identity-org-structure-native-smoke-v1.yml").read_text()


class NativeStructureGuardTests(unittest.TestCase):
    def test_fixture_is_unmounted_and_gated(self):
        self.assertNotIn("LocalOrganizationStructureNativeSmokeV1.qml", SHELL)
        self.assertIn('=== "CI_DISPOSABLE_ONLY"', QML)
        self.assertIn("Quickshell.watchFiles = false;", QML)
        self.assertIn("IdentityCenterSettingsSections {", QML)
        self.assertIn("localStructureStore: SocialLocalOrganizationStructureStore", QML)
        for forbidden in ("PanelWindow {", "FloatingWindow {",
                          "canSwitchOrganization: true", "accessToken",
                          "refreshToken", "scopeGrants"):
            self.assertNotIn(forbidden, QML)

    def test_private_temp_roots_and_two_independent_qs_processes(self):
        self.assertIn("tempfile.TemporaryDirectory(", RUNNER)
        for key in ("XDG_RUNTIME_DIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME",
                    "XDG_CACHE_HOME", "XDG_STATE_HOME", "HOME",
                    "WAYLAND_DISPLAY", "QT_QPA_PLATFORM"):
            self.assertIn(key, RUNNER)
        self.assertIn('for phase in ("create", "reload"):', RUNNER)
        self.assertIn("assert data == previous", RUNNER)
        self.assertIn('== 0o600', RUNNER)
        self.assertIn('== 0o700', RUNNER)
        for name in ("organization", "portfolio", "links"):
            self.assertIn('original["' + name + '"]', RUNNER)
        self.assertNotIn('ROOT / "shell.qml"', RUNNER)
        self.assertNotIn("os.system(", RUNNER)
        self.assertNotIn("sudo ", RUNNER)

    def test_native_job_runs_inside_disposable_container(self):
        self.assertIn("debian:unstable-slim", WORKFLOW)
        self.assertIn("quickshell=0.3.2-1", WORKFLOW)
        self.assertIn("native_local_organization_structure_smoke_v1.py", WORKFLOW)
        self.assertNotIn("systemctl", WORKFLOW)
        self.assertNotIn("swaymsg", WORKFLOW)


if __name__ == "__main__":
    unittest.main()
