"""CPU++ Mouse mount: three existing bays, real controls, no shared-rail edits."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
CPU = (ROOT / "widgets/CpuPlusW.qml").read_text(encoding="utf-8")
MOUSE = (ROOT / "widgets/cpuplus/CpuPlusSettingsMouseScrollPane.qml").read_text(
    encoding="utf-8")


def mounted(marker):
    anchor = "        CpuPlusSettingsMouseScrollPane {\n            id: " + marker
    if CPU.count(anchor) != 1:
        raise AssertionError("Expected unique Mouse mount: " + marker)
    return CPU.split(anchor, 1)[1].split("\n        }", 1)[0]


class MouseSettingsMount(unittest.TestCase):
    def test_all_three_bays_use_real_mouse_component(self):
        self.assertEqual(CPU.count("CpuPlusSettingsMouseScrollPane {"), 3)
        for marker, area, top in (
            ("settingsMouseScrollFactorPane", "factor", "sharedStateHeader.bottom"),
            ("settingsMouseScrollDevicePane", "devices", "targetSubModeStrip.bottom"),
            ("settingsMouseScrollApplyPane", "apply", "actuatorHeader.bottom"),
        ):
            body = mounted(marker)
            self.assertIn('area: "' + area + '"', body)
            self.assertIn('cpuPlusWindow.settingsSubMode === "MOUSE"', body)
            self.assertIn("cpuPlusWindow.selectedModeIndex === 6", body)
            self.assertIn("anchors.top: " + top, body)
            self.assertIn("anchors.bottom: parent.bottom", body)

    def test_placeholders_not_overlapping_live_mouse(self):
        # Two middle-bay "SECTION RESERVED" labels should be absent for Mouse.
        guard = '&& cpuPlusWindow.settingsSubMode !== "MOUSE"'
        self.assertEqual(CPU.count(guard), 2)
        self.assertIn('text: "SECTION RESERVED"', CPU)
        self.assertIn('text: "NO DEVICE CHANGES"', CPU)
        self.assertIn("ACCESSIBILITY and LIGHTING stay reserved", CPU)

    def test_keyboard_and_existing_routes_preserved(self):
        self.assertEqual(CPU.count("CpuPlusSettingsKeyboardPane {"), 3)
        for name in ("LOCATION", "TIME", "CONNECTIONS", "KEYBOARD", "MOUSE",
                     "ACCESSIBILITY", "LIGHTING"):
            self.assertIn('key: "' + name + '"', CPU)
        self.assertIn("NeonScrollBar {\n            flickable: sharedInstrumentScroll", CPU)
        self.assertIn('id: settingsLocationSelectionPane', CPU)
        self.assertIn('id: settingsConnectionsList', CPU)
        self.assertIn('id: settingsTimeActivePane', CPU)

    def test_real_scroll_controls_not_replaced_with_fake_widgets(self):
        self.assertIn("import qs.services.input", MOUSE)
        self.assertIn("SwayScrollSettings.selectDevice(", MOUSE)
        self.assertIn("SwayScrollSettings.stageFactor(modelData)", MOUSE)
        self.assertIn("SwayScrollSettings.prepareApply()", MOUSE)
        self.assertIn("SwayScrollSettings.confirmApply()", MOUSE)
        self.assertIn("SwayScrollSettings.stageRestore()", MOUSE)


if __name__ == "__main__":
    unittest.main()
