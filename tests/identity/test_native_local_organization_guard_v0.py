"""Source guards for isolated, test-only Quickshell local organization writes."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
QML = (ROOT / "LocalOrganizationNativeSmokeV0.qml").read_text()
RUNNER = (ROOT / "tests/identity/native_local_organization_smoke_v0.py").read_text()
SHELL = (ROOT / "shell.qml").read_text()
WORKFLOW = (ROOT / ".github/workflows/identity-local-organization-native-smoke.yml").read_text()


class NativeLocalOrganizationGuards(unittest.TestCase):
    def test_not_mounted_and_only_disposable_gate(self):
        self.assertNotIn("LocalOrganizationNativeSmokeV0.qml", SHELL)
        self.assertIn('=== "CI_DISPOSABLE_ONLY"', QML)
        self.assertIn("Quickshell.watchFiles = false;", QML)
        self.assertNotIn("PanelWindow {", QML)
        self.assertNotIn("FloatingWindow {", QML)
        self.assertIn("IdentityCenterSettingsSections {", QML)
        self.assertIn("localDirectoryStore: SocialOrganizationDirectoryStore", QML)
        self.assertNotIn("canSwitchOrganization: true", QML)

    def test_temporary_home_runtime_and_no_live_wayland(self):
        self.assertIn("tempfile.TemporaryDirectory(", RUNNER)
        for name in ("XDG_RUNTIME_DIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME",
                     "XDG_STATE_HOME", "XDG_CACHE_HOME", "HOME", "WAYLAND_DISPLAY",
                     "QT_QPA_PLATFORM", "CI_DISPOSABLE_ONLY"):
            self.assertIn(name, RUNNER)
        self.assertIn('("create", "reload")', RUNNER)
        self.assertIn("assert data == saved", RUNNER)
        self.assertIn('== 0o600', RUNNER)
        self.assertNotIn("shell.qml", RUNNER)
        self.assertNotIn("sudo ", RUNNER)
        self.assertNotIn("os.system(", RUNNER)

    def test_native_ci_bound_to_disposable_container(self):
        self.assertIn("debian:unstable-slim", WORKFLOW)
        self.assertIn("quickshell=0.3.2-1", WORKFLOW)
        self.assertIn("native_local_organization_smoke_v0.py", WORKFLOW)
        self.assertNotIn("systemctl", WORKFLOW)
        self.assertNotIn("swaymsg", WORKFLOW)


if __name__ == "__main__":
    unittest.main()
