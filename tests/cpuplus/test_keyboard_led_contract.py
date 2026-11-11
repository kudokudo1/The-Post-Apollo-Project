"""Keyboard LED observation is opt-in, bounded and cannot write to Sway."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PANE = (ROOT / "widgets/cpuplus/CpuPlusSettingsKeyboardPane.qml").read_text()
SERVICE = (ROOT / "services/input/KeyboardLedObservation.qml").read_text()
POLICY = (ROOT / "services/input/KeyboardLedPolicy.js").read_text()
PROBE = (ROOT / "services/input/KeyboardLedProbe.py").read_text()
STARTUP = (ROOT / "services/input/SwayKeyboardStartup.py").read_text()
QMLDIR = (ROOT / "services/input/qmldir").read_text()


class LedObservationContracts(unittest.TestCase):
    def test_new_service_is_singleton_without_cpu_host_changes(self):
        self.assertIn("singleton KeyboardLedObservation 1.0", QMLDIR)
        self.assertIn("KeyboardLedObservation.monitoringEnabled", PANE)
        self.assertIn('label: "SAMPLE LED ONCE"', PANE)
        self.assertIn('label: "COPY FRESH LED VALUES"', PANE)
        self.assertIn("KeyboardLedObservation.copyObservedToStartup()", PANE)

    def test_led_observation_cannot_be_mistaken_for_true_lock_state(self):
        self.assertIn("LED PROXY // NOT VERIFIED XKB STATE", PANE)
        self.assertIn("SAVED LED NUM", PANE)
        self.assertIn("SAVED LED CAPS", PANE)
        self.assertIn("linux-led-brightness-proxy", SERVICE)
        self.assertIn('property string sourceStatus: "not_checked"', SERVICE)
        self.assertIn('property string candidateNum: "unknown"', SERVICE)
        self.assertIn('property string candidateCaps: "unknown"', SERVICE)
        self.assertIn("stableNum >= 2", SERVICE)
        self.assertIn("stableCaps >= 2", SERVICE)
        self.assertIn("lastSampleAtMs <= 6000", SERVICE)

    def test_monitoring_explicit_and_persistent(self):
        self.assertIn("running: ledMonitor.monitoringEnabled && ledMonitor.canEdit", SERVICE)
        self.assertIn('enabled: false', POLICY)
        self.assertIn("atomicWrites: true", SERVICE)
        self.assertIn("queuedDocument", SERVICE)
        self.assertIn("setMonitoringEnabled(enabled)", SERVICE)
        self.assertIn("storageState === \"saving\"", SERVICE)

    def test_copies_only_to_saved_preferences(self):
        self.assertIn('KeyboardLockSettings.choose("num", currentNum)', SERVICE)
        self.assertIn('KeyboardLockSettings.choose("caps", currentCaps)', SERVICE)
        self.assertIn("if (!canCopyToStartup)", SERVICE)
        self.assertIn("COPY UPDATES SAVED PREFERENCES ONLY", PANE)
        self.assertIn("PREPARE STARTUP RULES", PANE)
        self.assertIn("CONFIRM INSTALL", PANE)
        for forbidden in ("swaymsg", "pkexec", "setxkbmap",
                          "xdotool", "sudo", "import Quickshell.Wayland"):
            self.assertNotIn(forbidden, SERVICE)
            self.assertNotIn(forbidden, PROBE)
        self.assertIn("Only an explicit apply action", STARTUP)

    def test_bounded_source_no_keystrokes(self):
        self.assertIn('PRODUCTION_ROOT = Path("/sys/class/leds")', PROBE)
        self.assertIn('MAX_ENTRIES = 64', PROBE)
        self.assertIn('MAX_READ_BYTES = 16', PROBE)
        self.assertNotIn("keycode", PROBE)


if __name__ == "__main__":
    unittest.main()
