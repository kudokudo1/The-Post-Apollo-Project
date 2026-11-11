"""Stage-0 CPU++ Settings input-category navigation, no device writes."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "widgets/CpuPlusW.qml").read_text(encoding="utf-8")


class InputCategoryNavigation(unittest.TestCase):
    def test_existing_and_new_settings_routes(self):
        for key in ("LOCATION", "TIME", "CONNECTIONS",
                    "KEYBOARD", "MOUSE", "ACCESSIBILITY", "LIGHTING"):
            self.assertIn('key: "' + key + '"', SOURCE)
        self.assertIn('function selectSettingsSubMode(key)', SOURCE)
        self.assertIn('cpuPlusWindow.selectSettingsSubMode(modelData.key)', SOURCE)
        self.assertIn('cpuPlusWindow.settingsSubModes', SOURCE)

    def test_new_categories_are_navigation_only(self):
        model = SOURCE.split("readonly property var settingsSubModes:", 1)[1].split(
            "// Rail-face animation state", 1)[0]
        for title in ("KEYBOARD", "MOUSE & TOUCHPAD", "ACCESSIBILITY", "LIGHTING / RGB"):
            self.assertIn(title, model)
        self.assertIn("Stage 0: navigation only", model)
        self.assertIn('text: "SECTION RESERVED"', SOURCE)
        self.assertIn('text: "NO DEVICE CHANGES"', SOURCE)
        self.assertIn("settingsInputPreviewSelected", SOURCE)
        for forbidden in ("setxkbmap", "numlockx", "OpenRGB", "libinput", "swaymsg"):
            self.assertNotIn(forbidden, model)

    def test_settings_strip_has_room_for_seven_buttons(self):
        self.assertIn("? 168 : 0", SOURCE)
        self.assertIn("(targetSubModeStrip.width - 4) / 2", SOURCE)
        self.assertIn('settingsInputPreviewTitle + " // SELECT"', SOURCE)
        self.assertIn('settingsInputPreviewTitle + " // OVERVIEW"', SOURCE)
        self.assertIn('settingsInputPreviewTitle + " // CONTROL"', SOURCE)
        self.assertIn("&& !(cpuPlusWindow.selectedModeIndex === 6", SOURCE)


if __name__ == "__main__":
    unittest.main()
