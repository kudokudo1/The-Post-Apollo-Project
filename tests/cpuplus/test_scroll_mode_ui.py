"""CPU++ Scroll Mode V1: real Sway lock vs intentionally gated autoscroll."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
MOUSE=(ROOT/"widgets/cpuplus/CpuPlusSettingsMouseScrollPane.qml").read_text()
PANE=(ROOT/"widgets/cpuplus/CpuPlusSettingsScrollModePane.qml").read_text()
OWNER=(ROOT/"services/input/ScrollModeSettings.qml").read_text()
HELPER=(ROOT/"services/input/SwayScrollLock.py").read_text()
POLICY=(ROOT/"services/input/UniversalAutoscrollPolicy.js").read_text()
DIR=(ROOT/"services/input/qmldir").read_text()
FIXTURE=(ROOT/"tests/cpuplus/fixtures/MouseScrollNative.qml").read_text()

class ScrollModeUi(unittest.TestCase):
    def test_existing_mouse_three_bays_and_other_terminal_routes_preserved(self):
        self.assertIn("CpuPlusSettingsScrollModePane {",MOUSE)
        self.assertIn("area: mousePane.area",MOUSE)
        self.assertIn("visible: ScrollModeSettings.modePage",MOUSE)
        self.assertIn('label: "MIDDLE-CLICK // SCROLL MODES"',MOUSE)
        self.assertIn("ScrollModeSettings.openModePage()",MOUSE)
        self.assertIn("ScrollModeSettings.closeModePage()",PANE)
        self.assertIn("CpuPlusSettingsKittyScrollPane {",MOUSE)
        self.assertIn("singleton ScrollModeSettings 1.0",DIR)
        for a in ('"devices"','"factor"','"apply"'):
            self.assertIn(a,PANE)

    def test_modes_and_two_click_consent(self):
        for mode in ('"off"','"lock"','"auto"'):
            self.assertIn('ScrollModeSettings.chooseMode('+mode+')',PANE)
        self.assertIn("function prepare()",OWNER)
        self.assertIn("function confirm()",OWNER)
        self.assertIn("if (!canPrepare)",OWNER)
        self.assertIn('"CONFIRM SCROLL LOCK"',PANE)
        self.assertIn('"CONFIRM RESTORE NORMAL"',PANE)
        self.assertIn("SNAPSHOT",HELPER)
        self.assertIn("function cancel()",OWNER)
        self.assertIn("restore()",HELPER)

    def test_no_false_global_scroll_claim(self):
        self.assertIn("readonly property bool autoscrollRuntimeAvailable: false",OWNER)
        self.assertIn("AUTOSCROLL ENGINE READY // GLOBAL POINTER CAPTURE NOT VERIFIED",OWNER)
        self.assertIn("PREVIEW ONLY // GLOBAL INPUT CAPTURE",PANE)
        self.assertIn("AUTOSCROLL CANNOT ACTIVATE",PANE)
        self.assertNotIn('"auto" &&',OWNER)
        self.assertIn("ENGINE_ONLY",POLICY)
        self.assertNotIn("ydotool",HELPER)

    def test_safe_snapshot_and_native_nonmutation_test(self):
        self.assertIn("os.O_EXCL",HELPER)
        self.assertIn("os.O_NOFOLLOW",HELPER)
        self.assertIn("STALE_DEVICE",HELPER)
        self.assertIn("DEVICE_CHANGED_EXTERNALLY",HELPER)
        self.assertIn("RESTORE_NOT_VERIFIED",HELPER)
        self.assertIn("SCROLL_MODE_NATIVE_PASS",FIXTURE)

if __name__=="__main__":
    unittest.main()
