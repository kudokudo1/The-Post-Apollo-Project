"""Source/authority regression for independent Remember Last State mode."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SETTINGS = (ROOT / "services/input/KeyboardLockSettings.qml").read_text()
LED = (ROOT / "services/input/KeyboardLedObservation.qml").read_text()
PANE = (ROOT / "widgets/cpuplus/CpuPlusSettingsKeyboardPane.qml").read_text()
POLICY = (ROOT / "services/input/KeyboardLockPolicy.js").read_text()
HELPER = (ROOT / "services/input/SwayKeyboardStartup.py").read_text()


class RememberUiContract(unittest.TestCase):
    def test_four_modes_each_lock(self):
        self.assertIn('["system", "on", "off", "remember"]', POLICY)
        self.assertEqual(PANE.count('{label:"REMEMBER",mode:"remember"}'), 2)
        self.assertIn('(numChoices.width - 3 * numChoices.spacing) / 4', PANE)
        self.assertIn('(capsChoices.width - 3 * capsChoices.spacing) / 4', PANE)

    def test_confirm_controls_remember_authority(self):
        self.assertIn("function prepareApply(savedNum, savedCaps)", SETTINGS)
        self.assertIn("confirmedSnapshotNum", SETTINGS)
        self.assertIn("confirmedSnapshotCaps", SETTINGS)
        self.assertIn('"apply-policy", document.num, document.caps,', SETTINGS)
        self.assertIn("if (!confirmRequired || !canApply)", SETTINGS)
        self.assertIn("KeyboardLockSettings.prepareApply(", PANE)
        self.assertIn("KeyboardLedObservation.savedNum", PANE)
        self.assertIn("KeyboardLedObservation.savedCaps", PANE)
        self.assertIn("NUM REMEMBER REQUIRES A SAVED LED OBSERVATION", SETTINGS)
        self.assertIn("CAPS REMEMBER REQUIRES A SAVED LED OBSERVATION", SETTINGS)

    def test_initial_sample_does_not_rewrite_startup(self):
        self.assertIn('property string witnessNum: "unknown"', LED)
        self.assertIn('property string witnessCaps: "unknown"', LED)
        self.assertIn('previous !== "unknown" && previous !== value', LED)
        self.assertIn("KeyboardLockSettings.rememberLedTransition(lock, value)", LED)
        self.assertIn('witnessStableTransition("num", candidateNum)', LED)
        self.assertIn('witnessStableTransition("caps", candidateCaps)', LED)

    def test_sync_requires_arm_and_cas(self):
        self.assertIn("hostRememberNum", SETTINGS)
        self.assertIn("hostRememberCaps", SETTINGS)
        self.assertIn("rememberSuspended", SETTINGS)
        self.assertIn("rememberSyncing", SETTINGS)
        self.assertIn("queuedRememberNum", SETTINGS)
        self.assertIn("queuedRememberCaps", SETTINGS)
        self.assertIn('"sync-remember", lockName, value, previous', SETTINGS)
        self.assertIn("REMEMBER_NOT_AUTHORIZED", HELPER)
        self.assertIn("STALE_FRAGMENT", HELPER)
        self.assertIn("read_config_without_writes", HELPER)
        self.assertIn('APPROVED_INCLUDE = "include ~/.config/sway/', HELPER)
        self.assertIn("atomic_write(fragment,", HELPER)
        self.assertNotIn("swaymsg", HELPER)
        self.assertNotIn("swaymsg", SETTINGS)

    def test_no_fake_live_restore_claim(self):
        self.assertIn("LED PROXY // NOT VERIFIED XKB STATE", PANE)
        self.assertIn("NO SWAY RELOAD OR KEY INJECTION", PANE)
        self.assertIn("NEXT SWAY START", PANE)


if __name__ == "__main__":
    unittest.main()
