"""CPU++ Zellij integration is real config controls, never a fake speed knob."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
KITTY = (ROOT / "widgets/cpuplus/CpuPlusSettingsKittyScrollPane.qml").read_text()
ZELLIJ = (ROOT / "widgets/cpuplus/CpuPlusSettingsZellijScrollPane.qml").read_text()
SETTINGS = (ROOT / "services/input/ZellijScrollSettings.qml").read_text()
HELPER = (ROOT / "services/input/ZellijScrollConfig.py").read_text()
QMLDIR = (ROOT / "services/input/qmldir").read_text()
FIXTURE = (ROOT / "tests/cpuplus/fixtures/MouseScrollNative.qml").read_text()


class ZellijIntegrationContracts(unittest.TestCase):
    def test_three_bay_nested_route_without_shared_host_edits(self):
        self.assertIn("CpuPlusSettingsZellijScrollPane {", KITTY)
        self.assertIn("area: kittyPane.area", KITTY)
        self.assertIn("visible: ZellijScrollSettings.active", KITTY)
        self.assertIn('label: "ZELLIJ // PANE SCROLL"', KITTY)
        self.assertIn("ZellijScrollSettings.open()", KITTY)
        self.assertIn("ZellijScrollSettings.close()", ZELLIJ)
        self.assertIn("singleton ZellijScrollSettings 1.0", QMLDIR)

    def test_real_zellij_options_not_fake_speed(self):
        for option in ("mouse_mode", "mouse_scroll_resize",
                       "scroll_mode_sync", "scroll_buffer_size"):
            self.assertIn(option, HELPER)
        for name in ("mouse", "resize", "sync", "buffer"):
            self.assertIn('ZellijScrollSettings.stage("' + name + '",', ZELLIJ)
        self.assertIn("BUFFER SIZE CHANGES HISTORY CAPACITY, NOT SCROLL SPEED", ZELLIJ)
        self.assertIn("NO NUMERIC ZELLIJ WHEEL SPEED EXISTS", ZELLIJ)
        self.assertNotIn('scroll_speed', HELPER)

    def test_explicit_gate_and_no_runtime_changes(self):
        self.assertIn("function prepare()", SETTINGS)
        self.assertIn("function confirm()", SETTINGS)
        self.assertIn("if (!confirmRequired || busy", SETTINGS)
        self.assertIn('"apply", observedRevision, stagedMouse,', SETTINGS)
        self.assertIn("confirmRequired = false;", SETTINGS)
        self.assertIn('label: "PREPARE ZELLIJ OPTIONS"', ZELLIJ)
        self.assertIn('label: "CONFIRM SAVE KDL"', ZELLIJ)
        self.assertIn("REFUSED // ", SETTINGS)
        self.assertIn("runtime_verified", HELPER)
        for forbidden in ("subprocess", "swaymsg", "pkexec", "kitty @", "zellij action"):
            self.assertNotIn(forbidden, HELPER)

    def test_no_auto_install_on_import_or_mode_switch(self):
        self.assertIn("return true;", SETTINGS)
        self.assertIn("READING ZELLIJ CONFIG // NO WRITES", SETTINGS)
        self.assertNotIn("Component.onCompleted: ZellijScrollSettings.confirm()", KITTY)
        self.assertIn("ZELLIJ_NATIVE_PASS // STAGED_NO_CONFIG_WRITE", FIXTURE)


if __name__ == "__main__":
    unittest.main()
