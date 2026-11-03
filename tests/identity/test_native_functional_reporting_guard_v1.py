"""Functional reporting native QML must remain isolated from a real desktop."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
QML = (ROOT / "LocalFunctionalReportingNativeSmokeV1.qml").read_text()
RUNNER = (ROOT / "tests/identity/native_local_functional_reporting_smoke_v1.py").read_text()
WORKFLOW = (ROOT / ".github/workflows/social-functional-reporting-native-v1.yml").read_text()
SHELL = (ROOT / "shell.qml").read_text()


class FunctionalReportingNativeGuards(unittest.TestCase):
    def test_fixture_unmounted_and_explicitly_gated(self):
        self.assertNotIn("LocalFunctionalReportingNativeSmokeV1.qml", SHELL)
        self.assertIn('=== "CI_DISPOSABLE_ONLY"', QML)
        self.assertIn("Quickshell.watchFiles = false;", QML)
        self.assertIn("IdentityCenterSettingsSections {", QML)
        self.assertIn("localFunctionalReportingStore: SocialLocalFunctionalReportingStore",
                      QML)
        for forbidden in ("PanelWindow {", "FloatingWindow {",
                          "accessToken", "scopeGrants", "canSwitchOrganization: true"):
            self.assertNotIn(forbidden, QML)

    def test_private_temporary_roots_and_two_independent_qs_processes(self):
        self.assertIn("tempfile.TemporaryDirectory(", RUNNER)
        for key in ("HOME", "XDG_RUNTIME_DIR", "XDG_CONFIG_HOME",
                    "XDG_STATE_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME",
                    "QT_QPA_PLATFORM", "WAYLAND_DISPLAY"):
            self.assertIn(key, RUNNER)
        self.assertIn('for phase in ("create", "reload"):', RUNNER)
        self.assertIn("data == first_bytes", RUNNER)
        self.assertIn("source_path.read_bytes() == original[name]", RUNNER)
        self.assertIn("== 0o700", RUNNER)
        self.assertIn("== 0o600", RUNNER)
        self.assertNotIn('ROOT / "shell.qml"', RUNNER)
        self.assertNotIn("os.system(", RUNNER)
        self.assertNotIn("sudo ", RUNNER)

    def test_native_container_is_disposable_and_pinned(self):
        self.assertIn("debian:unstable-slim", WORKFLOW)
        self.assertIn("quickshell=0.3.2-1", WORKFLOW)
        self.assertIn("native_local_functional_reporting_smoke_v1.py", WORKFLOW)
        self.assertNotIn("systemctl", WORKFLOW)
        self.assertNotIn("swaymsg", WORKFLOW)


if __name__ == "__main__":
    unittest.main()
