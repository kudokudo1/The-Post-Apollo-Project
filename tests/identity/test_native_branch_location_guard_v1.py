"""Synthetic branch/location Quickshell must never mount live or use user data."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
QML = (ROOT / "LocalBranchLocationNativeSmokeV1.qml").read_text()
RUNNER = (ROOT / "tests/identity/native_local_branch_location_smoke_v1.py").read_text()
WORKFLOW = (ROOT / ".github/workflows/social-local-branch-location-native-v1.yml").read_text()
SHELL = (ROOT / "shell.qml").read_text()


class BranchLocationNativeGuards(unittest.TestCase):
    def test_separate_synthetic_unmounted_root(self):
        self.assertNotIn("LocalBranchLocationNativeSmokeV1.qml", SHELL)
        self.assertIn('=== "CI_DISPOSABLE_ONLY"', QML)
        self.assertIn("Quickshell.watchFiles = false;", QML)
        self.assertIn("IdentityCenterSettingsSections {", QML)
        self.assertIn("localBranchLocationLinksStore: SocialLocalBranchLocationLinksStore", QML)
        for forbidden in ("PanelWindow {", "FloatingWindow {",
                          "accessToken", "scopeGrants",
                          "canSwitchOrganization: true"):
            self.assertNotIn(forbidden, QML)

    def test_two_real_qs_processes_and_all_private_roots(self):
        self.assertIn("tempfile.TemporaryDirectory(", RUNNER)
        for token in ("HOME", "XDG_RUNTIME_DIR", "XDG_CONFIG_HOME",
                      "XDG_STATE_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME",
                      "QT_QPA_PLATFORM", "WAYLAND_DISPLAY"):
            self.assertIn(token, RUNNER)
        self.assertIn('for phase in ("create", "reload"):', RUNNER)
        self.assertIn("data == first_bytes", RUNNER)
        self.assertIn("original_path.read_bytes() == source_bytes[name]", RUNNER)
        self.assertIn("== 0o700", RUNNER)
        self.assertIn("== 0o600", RUNNER)
        self.assertNotIn('ROOT / "shell.qml"', RUNNER)
        self.assertNotIn("os.system(", RUNNER)
        self.assertNotIn("sudo ", RUNNER)

    def test_pinned_disposable_genuine_quickshell_job(self):
        self.assertIn("debian:unstable-slim", WORKFLOW)
        self.assertIn("quickshell=0.3.2-1", WORKFLOW)
        self.assertIn("native_local_branch_location_smoke_v1.py", WORKFLOW)
        self.assertNotIn("systemctl", WORKFLOW)
        self.assertNotIn("swaymsg", WORKFLOW)


if __name__ == "__main__":
    unittest.main()
