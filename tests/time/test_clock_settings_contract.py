"""Contract checks for Clock calibration and guarded host time controls."""
from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
HOST = ROOT / "services/time/TimeHostControl.py"
SPEC = importlib.util.spec_from_file_location("time_host_control", HOST)
host = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(host)


class ClockTimeSettingsContract(unittest.TestCase):
    def test_clock_module_reads_single_shared_offset(self):
        clock = (ROOT / "modules/Clock.qml").read_text()
        timew = (ROOT / "widgets/TimeW.qml").read_text()
        self.assertIn("TimeSettings.displayOffsetMs", clock)
        self.assertIn("clockArea.adjustedDate", clock)
        self.assertIn("TimeSettings.adjustedEpochMs", timew)
        self.assertIn('id: "settings", name: "SETTINGS"', timew)
        self.assertIn('id: "planned", name: "NEXT"', timew)
        self.assertIn('label: "⟳"', timew)

    def test_shared_service_persists_only_display_offset(self):
        service = (ROOT / "services/time/TimeSettings.qml").read_text()
        policy = (ROOT / "services/time/TimeSettingsPolicy.js").read_text()
        self.assertIn("atomicWrites: true", service)
        self.assertIn("time-settings-v1.json", service)
        self.assertIn("MAX_OFFSET_MS = 300000", policy)
        self.assertIn("adjustDisplayMs", service)
        self.assertNotIn("set-timezone", service)
        self.assertNotIn("set-ntp", service)

    def test_status_is_observation_not_actuation(self):
        with patch.object(host, "system_properties", return_value={
                "Timezone": "America/New_York", "NTP": "no",
                "NTPSynchronized": "no", "LocalRTC": "yes"}):
            data = host.status()
        self.assertEqual(data["status"], "ready")
        self.assertEqual(data["timezone"], "America/New_York")
        self.assertEqual(data["ntpEnabled"], "no")
        self.assertEqual(data["rtcLocal"], "yes")
        self.assertIn("dstActive", data)

    def test_chrony_absent_does_not_change_clock(self):
        with patch.object(host.os.path, "isfile", return_value=False), \
                patch.object(host.subprocess, "run") as run:
            result = host.resync()
        self.assertEqual(result["status"], "unavailable")
        run.assert_not_called()

    def test_resync_only_requests_fresh_samples(self):
        with patch.object(host.os.path, "isfile", return_value=True), \
                patch.object(host.subprocess, "run", side_effect=[
                    subprocess.CompletedProcess([], 0, "tracking", ""),
                    subprocess.CompletedProcess([], 0, "200 OK", ""),
                ]) as run:
            result = host.resync()
        self.assertEqual(result["status"], "requested")
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(commands[0], [host.CHRONYC, "tracking"])
        self.assertEqual(
            commands[1], [host.PKEXEC, host.CHRONYC, "burst", "4/4"])
        for command in commands:
            self.assertNotIn("set-ntp", command)
            self.assertNotIn("makestep", command)
            self.assertNotIn("set-timezone", command)


if __name__ == "__main__":
    unittest.main()
