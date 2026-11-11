"""CPU++ Mouse/Touchpad control is a real, staged Sway input surface."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PANE=(ROOT/"widgets/cpuplus/CpuPlusSettingsMouseScrollPane.qml").read_text()
SERVICE=(ROOT/"services/input/SwayScrollSettings.qml").read_text()
HOST=(ROOT/"services/input/SwayScrollControl.py").read_text()
DIR=(ROOT/"services/input/qmldir").read_text()


class MouseScrollContracts(unittest.TestCase):
    def test_three_bays_and_exact_device_selection(self):
        for area in ('"devices"','"factor"','"apply"'):
            self.assertIn(area,PANE)
        self.assertIn("SwayScrollSettings.selectDevice(",PANE)
        self.assertIn("SwayScrollSettings.stageFactor(modelData)",PANE)
        self.assertIn("SwayScrollSettings.devices",PANE)
        self.assertIn("singleton SwayScrollSettings 1.0",DIR)

    def test_real_effect_only_after_second_confirmation(self):
        self.assertIn("function prepareApply()",SERVICE)
        self.assertIn("function confirmApply()",SERVICE)
        self.assertIn("if (!confirmationRequired || busy || !selectedDevice",SERVICE)
        self.assertIn('label: "CONFIRM APPLY TO SWAY"',PANE)
        self.assertIn('"apply", applyId,',SERVICE)
        self.assertIn('"scope": "live_sway_only"',HOST)
        self.assertIn('"scroll_factor"',HOST)
        self.assertNotIn("swaymsg reload",HOST)

    def test_no_fake_persistence_after_reboot(self):
        self.assertIn("FileView",SERVICE)
        self.assertIn("atomicWrites: true",SERVICE)
        self.assertIn("STAGED ONLY // NOT APPLIED TO SWAY",SERVICE)
        self.assertIn("STARTUP NOT YET WIRED",SERVICE)
        self.assertIn("NOT AUTOMATICALLY APPLIED AFTER REBOOT YET",PANE)
        self.assertIn("KITTY / ZELLIJ-SPECIFIC SCROLLING",PANE)
        self.assertNotIn("onLoaded: { settings.confirmApply()",SERVICE)
        self.assertNotIn("Component.onCompleted: settings.confirmApply()",SERVICE)

    def test_reversible_and_stale_guarded(self):
        self.assertIn("undoFactor",SERVICE)
        self.assertIn("canRestore",SERVICE)
        self.assertIn("stageRestore()",SERVICE)
        self.assertIn("STALE_DEVICE_FACTOR",HOST)
        self.assertIn("CHANGE_NOT_VERIFIED",HOST)
        self.assertIn("DEVICE_NOT_FOUND",HOST)
        self.assertIn("MAX_DEVICES = 64",HOST)
        self.assertNotIn("shell=True",HOST)
        self.assertNotIn("pkexec",SERVICE)


if __name__=="__main__":
    unittest.main()
