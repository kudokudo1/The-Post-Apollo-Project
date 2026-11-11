"""CPU++ Kitty scroll controls: actual config, staged actions, no hidden writes."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
MOUSE=(ROOT/"widgets/cpuplus/CpuPlusSettingsMouseScrollPane.qml").read_text()
KITTY=(ROOT/"widgets/cpuplus/CpuPlusSettingsKittyScrollPane.qml").read_text()
OWNER=(ROOT/"services/input/KittyScrollSettings.qml").read_text()
HELPER=(ROOT/"services/input/KittyScrollConfig.py").read_text()
QMLDIR=(ROOT/"services/input/qmldir").read_text()
FIXTURE=(ROOT/"tests/cpuplus/fixtures/MouseScrollNative.qml").read_text()


class KittyScrollUiContract(unittest.TestCase):
    def test_existing_mouse_bays_mount_kitty_without_host_edits(self):
        self.assertIn("CpuPlusSettingsKittyScrollPane {",MOUSE)
        self.assertIn("area: mousePane.area",MOUSE)
        self.assertIn("visible: KittyScrollSettings.terminalMode",MOUSE)
        self.assertIn('label: "KITTY // TERMINAL SCROLL"',MOUSE)
        self.assertIn("KittyScrollSettings.chooseMode(true)",MOUSE)
        self.assertIn("KittyScrollSettings.chooseMode(false)",KITTY)
        self.assertIn("singleton KittyScrollSettings 1.0 KittyScrollSettings.qml",QMLDIR)

    def test_two_independent_native_kitty_factors(self):
        self.assertIn('wheel_scroll_multiplier',HELPER)
        self.assertIn('touch_scroll_multiplier',HELPER)
        self.assertIn('KittyScrollSettings.stage("wheel", modelData)',KITTY)
        self.assertIn('KittyScrollSettings.stage("touch", modelData)',KITTY)
        self.assertIn("property real stagedWheel: 5.0",OWNER)
        self.assertIn("property real stagedTouch: 1.0",OWNER)
        self.assertIn("KittyScrollSettings.stagedWheel.toFixed(2)",KITTY)
        self.assertIn("KittyScrollSettings.stagedTouch.toFixed(2)",KITTY)

    def test_no_side_effect_until_explicit_confirmation(self):
        self.assertIn("function prepare()",OWNER)
        self.assertIn("function confirm()",OWNER)
        self.assertIn('if (!canInstall || !hasChanges)',OWNER)
        self.assertIn('activeAction, stagedWheel.toFixed(2), stagedTouch.toFixed(2)',OWNER)
        self.assertIn('label: "PREPARE KITTY SCROLL"',KITTY)
        self.assertIn("CONFIRM INCLUDE & SAVE",KITTY)
        self.assertIn("CONFIRM KITTY SAVE",KITTY)
        self.assertNotIn("Component.onCompleted: KittyScrollSettings.confirm()",MOUSE)
        self.assertNotIn("onPanelVisibleChanged: KittyScrollSettings.confirm()",KITTY)
        self.assertNotIn("subprocess",HELPER)
        self.assertNotIn("swaymsg",HELPER)
        self.assertNotIn("os.system", HELPER)
        self.assertIn("No Kitty/Sway process", HELPER)
        self.assertIn("KITTY_NATIVE_PASS // TWO_FACTORS_STAGED_NO_CONFIG_WRITE",FIXTURE)

    def test_no_fullscreen_tui_claim(self):
        self.assertIn("ZELLIJ AND OTHER FULL-SCREEN TERMINAL PROGRAMS",KITTY)
        self.assertIn("NOT PROOF OF LIVE KITTY EFFECT",KITTY)
        self.assertIn("SCROLL EVENTS THEMSELVES", KITTY)


if __name__=="__main__":
    unittest.main()
