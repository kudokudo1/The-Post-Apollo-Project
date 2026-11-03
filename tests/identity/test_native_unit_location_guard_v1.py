"""Native unit/location smoke must be isolated from live Post-Apollo shell."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
QML = (ROOT / "LocalUnitLocationNativeSmokeV1.qml").read_text()
RUNNER = (ROOT / "tests/identity/native_local_unit_location_smoke_v1.py").read_text()
WORKFLOW = (ROOT / ".github/workflows/identity-unit-location-native-smoke-v1.yml").read_text()
SHELL = (ROOT / "shell.qml").read_text()


class UnitLocationNativeGuards(unittest.TestCase):
    def test_unmounted_and_disposable_only(self):
        self.assertNotIn("LocalUnitLocationNativeSmokeV1.qml", SHELL)
        self.assertIn('=== "CI_DISPOSABLE_ONLY"', QML)
        self.assertIn("Quickshell.watchFiles = false;", QML)
        self.assertIn("IdentityCenterSettingsSections {", QML)
        self.assertIn("localUnitLocationLinksStore: SocialLocalUnitLocationLinksStore", QML)
        for forbidden in ("FloatingWindow {", "PanelWindow {",
                          "accessToken", "scopeGrants",
                          "canSwitchOrganization: true"):
            self.assertNotIn(forbidden, QML)

    def test_independent_real_processes_with_all_private_roots(self):
        self.assertIn("tempfile.TemporaryDirectory(", RUNNER)
        for key in ("HOME", "XDG_RUNTIME_DIR", "XDG_CONFIG_HOME",
                    "XDG_STATE_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME",
                    "QT_QPA_PLATFORM", "WAYLAND_DISPLAY"):
            self.assertIn(key, RUNNER)
        self.assertIn('for phase in ("create", "reload"):', RUNNER)
        self.assertIn("data == first_payload", RUNNER)
        self.assertIn("path.read_bytes() == original[name]", RUNNER)
        self.assertIn("== 0o700", RUNNER)
        self.assertIn("== 0o600", RUNNER)
        self.assertNotIn('ROOT / "shell.qml"', RUNNER)
        self.assertNotIn("os.system(", RUNNER)
        self.assertNotIn("sudo ", RUNNER)

    def test_ci_uses_pinned_disposable_quickshell_container(self):
        self.assertIn("debian:unstable-slim", WORKFLOW)
        self.assertIn("quickshell=0.3.2-1", WORKFLOW)
        self.assertIn("native_local_unit_location_smoke_v1.py", WORKFLOW)
        self.assertNotIn("systemctl", WORKFLOW)
        self.assertNotIn("swaymsg", WORKFLOW)


if __name__ == "__main__":
    unittest.main()
