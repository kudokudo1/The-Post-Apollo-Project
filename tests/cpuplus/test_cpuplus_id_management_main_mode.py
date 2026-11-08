"""CPU++ ID Management follows Favorites and precedes Settings on the main rail."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
CPU = (ROOT / "widgets/CpuPlusW.qml").read_text(encoding="utf-8")
PANE = (ROOT / "widgets/cpuplus/CpuPlusIdManagementPane.qml").read_text(
    encoding="utf-8")
SOCIAL = (ROOT / "widgets/messanger/IdentityCenterSettingsSections.qml").read_text(
    encoding="utf-8")


class CpuPlusIdManagementMainModeContracts(unittest.TestCase):
    def test_seven_main_modes_favorites_id_management_settings_order(self):
        segment = CPU.split("readonly property var modes: [", 1)[1].split(
            "function open()", 1)[0]
        names = ["OVERVIEW", "PROCESS", "THERMAL", "SYSTEM",
                 "FAVORITES", "ID MANAGEMENT", "SETTINGS"]
        positions = [segment.index('name: "' + item + '"') for item in names]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(segment.count('name: "ID MANAGEMENT"'), 1)
        self.assertIn("model: cpuPlusWindow.modes", CPU)
        self.assertIn("cpuPlusWindow.selectMode(index);", CPU)
        self.assertIn("Math.min(modes.length - 1", CPU)

    def test_chassis_geometry_and_existing_settings_unchanged(self):
        for snippet in ("implicitWidth: 1000", "implicitHeight: 834",
                        "id: modeRail", "height: 110",
                        "id: sharedInstrumentPane", "width: 390",
                        "id: targetPane", "width: 260",
                        "id: actuatorPane", "id: settingsLocationPane",
                        "id: settingsTimeBasicsPane",
                        "id: settingsConnectionsOverview"):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, CPU)
        self.assertIn("TimeSettings.cancelResync()", CPU)
        self.assertIn('selectedModeIndex === 6', CPU)
        self.assertIn('settingsSubMode === "CONNECTIONS"', CPU)

    def test_id_mode_reuses_three_existing_bays_not_a_new_window(self):
        left = CPU.split("id: sharedInstrumentPane", 1)[1].split(
            "id: targetPane", 1)[0]
        middle = CPU.split("id: targetPane", 1)[1].split(
            "id: actuatorPane", 1)[0]
        right = CPU.split("id: actuatorPane", 1)[1]
        for source, slot, identifier in (
            (left, "overview", "idManagementOverviewPane"),
            (middle, "selector", "idManagementSelectorPane"),
            (right, "details", "idManagementDetailsPane"),
        ):
            with self.subTest(slot=slot):
                self.assertIn("CpuPlusIdManagementPane {", source)
                self.assertIn('area: "' + slot + '"', source)
                self.assertIn("id: " + identifier, source)
                self.assertIn("visible: cpuPlusWindow.selectedModeIndex === 5",
                              source)
        self.assertIn("cpuPlusWindow.selectedModeIndex !== 5", CPU)
        self.assertNotIn("PanelWindow {", PANE)
        self.assertNotIn("FloatingWindow {", PANE)

    def test_local_id_editor_uses_owner_stores_without_host_actions(self):
        for snippet in ("SocialIdentityStore.snapshot",
                        "SocialAccountDetailsStore.recordFor(",
                        "idRequested(idRow.modelData.id)",
                        "SocialIdentityStore.createIdentity(",
                        "CpuPlusIdDetailsEditor {",
                        "NEW ID SAVED // LOCAL",
                        "SELECT LOCAL ID // EDIT DETAILS",
                        "LOCAL IDS ARE LAYOUT LABELS"):
            self.assertIn(snippet, PANE)
        self.assertIn("selectedLocalIdForManagement = localId;", CPU)
        self.assertIn("idManagementDetailsPane.editingText", CPU)
        self.assertIn("idManagementSelectorPane.editingText", CPU)
        for forbidden in ("FileView {", "Process {",
                          "SocialIdentityStore.selectIdentity(",
                          "Qt.openUrlExternally("):
            self.assertNotIn(forbidden, PANE)
        self.assertNotIn('id: "ID MANAGEMENT"', SOCIAL)


if __name__ == "__main__":
    unittest.main()
