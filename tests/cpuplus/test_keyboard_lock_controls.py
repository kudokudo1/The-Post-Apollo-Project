"""CPU++ keyboard controls and Settings icon-only structural contracts."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
CPU = (ROOT / "widgets/CpuPlusW.qml").read_text(encoding="utf-8")
PANE = (ROOT / "widgets/cpuplus/CpuPlusSettingsKeyboardPane.qml").read_text(
    encoding="utf-8")
SERVICE = (ROOT / "services/input/KeyboardLockSettings.qml").read_text(
    encoding="utf-8")
HOST = (ROOT / "services/input/SwayKeyboardStartup.py").read_text(
    encoding="utf-8")


class KeyboardLockControls(unittest.TestCase):
    def test_only_settings_buttons_hide_labels(self):
        self.assertIn("visible: cpuPlusWindow.selectedModeIndex !== 6", CPU)
        self.assertIn("(targetSubModeStrip.width - 12) / 4", CPU)
        self.assertIn("? 88 : 0", CPU)
        self.assertIn('=== "LOCATION"', CPU)
        self.assertIn('=== "KEYBOARD"', CPU)
        self.assertIn("? 30", CPU)
        self.assertIn("selectSettingsSubMode(modelData.key)", CPU)

    def test_controls_in_three_bays_without_duplicate_writers(self):
        self.assertEqual(CPU.count("CpuPlusSettingsKeyboardPane {"), 3)
        self.assertIn('area: "controls"', CPU)
        self.assertIn('area: "status"', CPU)
        self.assertIn('area: "apply"', CPU)
        self.assertIn('settingsSubMode === "KEYBOARD"', CPU)
        self.assertIn("qs.services.input", PANE)
        self.assertIn('KeyboardLockSettings.choose("num", modelData.mode)', PANE)
        self.assertIn('KeyboardLockSettings.choose("caps", modelData.mode)', PANE)

    def test_saved_preferences_not_fake_live_state(self):
        self.assertIn("atomicWrites: true", SERVICE)
        self.assertIn("pendingDocument", SERVICE)
        self.assertIn("queuedDocument", SERVICE)
        self.assertIn("profileInstalled", SERVICE)
        self.assertIn("LED PROXY // NOT VERIFIED XKB STATE", PANE)
        self.assertIn("LAST-USED KEY STATE // NOT IMPLEMENTED", PANE)
        self.assertIn("NEXT_SWAY_START", HOST)
        self.assertIn("runtime_changed", HOST)

    def test_opt_in_no_sway_reload_and_explicit_confirm(self):
        self.assertIn("function prepareApply()", SERVICE)
        self.assertIn("function requestApply()", SERVICE)
        self.assertIn("if (!confirmRequired || !canApply)", SERVICE)
        self.assertIn('label: "CONFIRM INSTALL"', PANE)
        self.assertIn("KeyboardLockSettings.requestApply()", PANE)
        self.assertIn('Quickshell.shellPath("services/input/SwayKeyboardStartup.py")', SERVICE)
        self.assertNotIn("swaymsg", SERVICE)
        self.assertNotIn("swaymsg", HOST)
        self.assertNotIn("pkexec", SERVICE)


if __name__ == "__main__":
    unittest.main()
