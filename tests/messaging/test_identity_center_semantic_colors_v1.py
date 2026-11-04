"""Semantic action-color roles on the original one-page Organizations UI."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
Q = ROOT / "widgets" / "messanger"
ROLE = (Q / "IdentityCenterLocalActionButton.qml").read_text()
PANE = (Q / "IdentityCenterSettingsSections.qml").read_text()
FILE_ROLES = {
    "IdentityCenterLocalOrganizationEditor.qml":
        ["refresh","add","navigate","manage","manage","manage","manage","manage","add"],
    "IdentityCenterLocalPortfolioEditor.qml":
        ["refresh","add","manage","manage","manage","danger","add"],
    "IdentityCenterLocalStructureEditor.qml":
        ["refresh","navigate","manage","navigate","add","manage","manage","manage"],
    "IdentityCenterLocalRelationshipModifiers.qml":
        ["navigate","navigate","navigate","navigate","navigate","navigate","navigate",
         "primary","navigate","refresh","danger"],
    "IdentityCenterLocalRecordsSearch.qml":
        ["danger","manage","navigate","primary"],
    "IdentityCenterLocalRefreshAll.qml": ["refresh"],
    "IdentityCenterLocalOrgBackup.qml":
        ["manage","navigate","neutral","refresh","danger"],
    "IdentityCenterLocalSessionActivity.qml":
        ["navigate","danger"],
}
FOCUS_INPUTS = {
    "IdentityCenterLocalOrganizationEditor.qml":
        ["newOrgName","orgName","branchName","newBranchName"],
    "IdentityCenterLocalPortfolioEditor.qml": ["createName","portfolioName"],
    "IdentityCenterLocalStructureEditor.qml": ["newUnitName","unitName"],
    "IdentityCenterLocalRelationshipModifiers.qml": ["subjectSearch"],
    "IdentityCenterLocalRecordsSearch.qml": ["searchInput"],
}


class SemanticOrganizationColors(unittest.TestCase):
    def test_local_wrapper_not_global_theme_rewrite(self):
        for expression in (
            'property string role: "navigate"',
            'role === "danger" ? Colors.red',
            'role === "refresh" ? Colors.green',
            'role === "manage" ? Colors.yellow',
            'role === "primary" ? Colors.orange',
            'role === "add" ? Colors.magenta',
            'role === "focus" ? Colors.magenta',
            'role === "neutral" ? Colors.white',
            ': Colors.blue',
            'pressedFillColor: destructive ? Colors.red : Colors.magenta',
            'Preserve base selected/keyboard-selected fill, glow and border rules.',
            'unavailableOpacity: 0.38',
            "hoverFillColor: Qt.rgba(",
        ):
            self.assertIn(expression, ROLE)
        self.assertNotIn("width:", ROLE)
        self.assertNotIn("height:", ROLE)
        self.assertNotIn("onTriggered:", ROLE)
        self.assertNotIn("signal triggered", ROLE)
        self.assertIn('import "../../components"', ROLE)
        # Open/selected retains the inherited base yellow fill/magenta edge,
        # rather than a custom all-magenta open-state fill.
        for override in ("selectedFillColor:", "selectedBorderColor:",
                         "selectedForegroundColor:", "selectedSoftGlowColor:",
                         "keyboardSelectedFillColor:", "wideGlowEnabled:"):
            self.assertNotIn(override, ROLE)

    def test_each_existing_action_has_a_reviewed_role(self):
        for path, expected in FILE_ROLES.items():
            source = (Q / path).read_text()
            actual = re.findall(r'^\s*role: "([^"]+)"', source, re.M)
            self.assertEqual(actual, expected, path)
            self.assertEqual(
                source.count("IdentityCenterLocalActionButton {"),
                len(expected), path)
            self.assertNotRegex(source, r'(^|\n)\s*(delegate: )?ActionButton \{')
            self.assertNotIn("accentColor: Colors.orange", source)
        self.assertEqual(
            PANE.count("IdentityCenterLocalActionButton {"), 2)
        # The shared settings navigation and disabled trusted switch retain
        # their existing architecture, only local editing selectors are themed.
        self.assertIn("delegate: ActionButton {", PANE)
        self.assertIn('label: "SWITCH ORGANIZATION // UNAVAILABLE"', PANE)
        self.assertIn("interactive: false", PANE.split(
            'label: "SWITCH ORGANIZATION // UNAVAILABLE"')[1][:160])
        for component in (
            "IdentityCenterLocalRecordsSearch {",
            "IdentityCenterLocalSaveFeedback {",
            "IdentityCenterLocalRefreshAll {",
            "IdentityCenterLocalOrgBackup {",
            "IdentityCenterLocalSessionActivity {",
            "IdentityCenterLocalOrganizationEditor {",
            "IdentityCenterLocalPortfolioEditor {",
            "IdentityCenterLocalStructureEditor {",
            "IdentityCenterLocalRelationshipModifiers {",
        ):
            self.assertEqual(PANE.count(component), 1)

    def test_magenta_inputs_use_existing_bounds_and_accessible_cues(self):
        for path, names in FOCUS_INPUTS.items():
            source = (Q / path).read_text()
            for name in names:
                self.assertIn("id: " + name, source)
                self.assertIn("selectionColor: Colors.magenta", source)
                self.assertRegex(source,
                    r"id: " + name + r"\n\s*cursorDelegate: Rectangle \{\n"
                    r"\s*width: 2\n\s*color: Colors.orange")
                # Typed text itself is magenta, not just the border/selection.
                self.assertRegex(source,
                    r"id: " + name + r"[\s\S]{0,850}?color: Colors.magenta")
                self.assertIn("selectedTextColor: Colors.black", source)
                self.assertIn(name + ".activeFocus", source)
                self.assertIn("? Colors.magenta : Colors.blue", source)
                self.assertIn("Qt.rgba(Colors.magenta.r", source)
        source = (Q / "IdentityCenterLocalRecordsSearch.qml").read_text()
        self.assertIn('objectName: "orgSearchInputFrame"', source)
        self.assertIn('objectName: "orgSearchInput"', source)
        self.assertIn("border.color: focusBorderColor", source)
        self.assertIn("intentFocused ? Colors.magenta : Colors.blue", source)
        self.assertIn("maximumLength: 80", source)

    def test_roles_align_with_high_value_actions_and_status(self):
        refresh = (Q / "IdentityCenterLocalRefreshAll.qml").read_text()
        backup = (Q / "IdentityCenterLocalOrgBackup.qml").read_text()
        activity = (Q / "IdentityCenterLocalSessionActivity.qml").read_text()
        feedback = (Q / "IdentityCenterLocalSaveFeedback.qml").read_text()
        self.assertIn('role: "refresh"\n        objectName: "orgRefreshAllButton"', refresh)
        self.assertIn('role: "manage"\n            objectName: "orgBackupCreateButton"', backup)
        self.assertIn('role: "refresh"\n            objectName: "orgBackupValidateButton"', backup)
        self.assertIn('role: "danger"\n            objectName: "orgBackupRestoreLockedButton"', backup)
        self.assertIn('role: "danger"\n            objectName: "orgSessionClearView"', activity)
        self.assertIn('role: "navigate"\n            objectName: "orgSessionShowAll"', activity)
        self.assertIn('feedback.lastKind === "saved"', feedback)
        self.assertIn("? Colors.green : Colors.white", feedback)
        self.assertIn("? Colors.red", backup)
        self.assertIn('height: 28', refresh)
        self.assertIn('width: 150', refresh)
        self.assertIn('height: 28', backup)
        self.assertIn('labelPixelSize: 9', backup)
        self.assertIn('interactive: false', backup.split(
            'label: "RESTORE // LOCKED"')[1][:100])
        self.assertIn('signal activityObserved', backup)
        self.assertIn('snapshotSignature', feedback)


    def test_every_add_or_plus_action_is_magenta(self):
        expected = {
            "IdentityCenterLocalOrganizationEditor.qml":
                ['label: "+ ORGANIZATION"', 'label: "+ BRANCH"'],
            "IdentityCenterLocalPortfolioEditor.qml":
                ['label: "+ PORTFOLIO"', 'label: "+ " + modelData.name'],
            "IdentityCenterLocalStructureEditor.qml":
                ['label: "+ ADD UNIT"'],
        }
        for path, labels in expected.items():
            src = (Q / path).read_text()
            for label in labels:
                self.assertIn(label, src)
                # The corresponding button declaration is the closest
                # preceding locally themed button, even in Repeater delegates.
                index = src.index(label)
                previous = src.rfind("IdentityCenterLocalActionButton {", 0, index)
                self.assertGreater(previous, 0)
                self.assertIn('role: "add"', src[previous:index])

    def test_no_new_privileged_or_unreviewed_operations(self):
        for forbidden in (
            "Process {", "FileView {", "PanelWindow {",
            "save(", "archive(", "unlink(", "delete(",
            "accessToken", "refreshToken", "scopeGrants",
            "createSession", "switchTenant(",
        ):
            self.assertNotIn(forbidden, ROLE)


if __name__ == "__main__":
    unittest.main()
