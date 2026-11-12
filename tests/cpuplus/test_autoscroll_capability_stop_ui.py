"""Stage 4: Autoscroll capability inquiry and STOP never activate input."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
OWNER = (ROOT / "services/input/ScrollModeSettings.qml").read_text()
PANE = (ROOT / "widgets/cpuplus/CpuPlusSettingsScrollModePane.qml").read_text()
PROBE = (ROOT / "services/input/AutoscrollOriginProbe.py").read_text()
CLI = (ROOT / "services/input/AutoscrollStop.py").read_text()
FIXTURE = (ROOT / "tests/cpuplus/fixtures/MouseScrollNative.qml").read_text()


class CapabilityStopUi(unittest.TestCase):
    def test_capability_inventory_is_read_only_and_on_demand(self):
        self.assertIn("function inspectAutoscrollCapabilities()", OWNER)
        self.assertIn("AutoscrollOriginProbe.py", OWNER)
        self.assertIn('"--inspect"', OWNER)
        self.assertIn("originProcess.exec(", OWNER)
        self.assertIn('label: ScrollModeSettings.originProbeBusy', PANE)
        self.assertIn("CHECK GLOBAL INPUT SUPPORT", PANE)
        self.assertIn("onLeftClicked: ScrollModeSettings.inspectAutoscrollCapabilities()", PANE)
        self.assertNotIn("Component.onCompleted: ScrollModeSettings.inspectAutoscrollCapabilities()", PANE)
        self.assertNotIn("run_live(", PROBE)

    def test_stop_is_explicit_and_does_not_claim_full_exit(self):
        self.assertIn("function requestEmergencyStop()", OWNER)
        self.assertIn("AutoscrollStop.py", OWNER)
        self.assertIn('"--stop"', OWNER)
        self.assertIn("stopProcess.exec(", OWNER)
        self.assertIn("EMERGENCY STOP EXPERIMENT", PANE)
        self.assertIn("onLeftClicked: ScrollModeSettings.requestEmergencyStop()", PANE)
        self.assertIn("STOP REQUEST ACKNOWLEDGED // EXIT NOT YET VERIFIED", OWNER)
        self.assertNotIn("onVisibleChanged: ScrollModeSettings.requestEmergencyStop()", PANE)

    def test_untrusted_probe_cannot_enable_autoscroll(self):
        self.assertIn("readonly property bool autoscrollRuntimeAvailable: false", OWNER)
        self.assertIn("reply.pointer_origin_verified !== false", OWNER)
        self.assertIn("reply.runtime_enabled !== false", OWNER)
        self.assertIn("UNTRUSTED PROBE RESULT", OWNER)
        self.assertIn('originProbeStatus = "inventory_only"', OWNER)
        self.assertIn("CURSOR POSITION STILL UNVERIFIED", OWNER)
        self.assertIn("pointer_origin_verified", PROBE)
        self.assertIn('"overlay_allowed": False', PROBE)
        self.assertIn('"runtime_enabled": False', PROBE)

    def test_native_fixture_includes_both_inert_result_paths(self):
        self.assertIn("AUTOSCROLL_CAPABILITY_NATIVE_PASS", FIXTURE)
        self.assertIn("ScrollModeSettings.acceptOrigin(", FIXTURE)
        self.assertIn("ScrollModeSettings.acceptStop(", FIXTURE)


if __name__ == "__main__":
    unittest.main()
