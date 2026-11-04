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
        self.assertIn("TimeSettings.prepareResync()", timew)
        self.assertIn("TimeSettings.requestResync()", (
            ROOT / "widgets/TimeSettingsPane.qml").read_text())
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
        self.assertIn('"set-timezone", zoneChoice', service)
        self.assertNotIn("set-timezone", policy)
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

    def test_disabled_daemon_uses_one_shot_without_enabling_ntp(self):
        with patch.object(host.os.path, "isfile", return_value=True), \
                patch.object(host.subprocess, "run", side_effect=[
                    subprocess.CompletedProcess([], 1, "", "not running"),
                    subprocess.CompletedProcess([], 3, "inactive\n", ""),
                    subprocess.CompletedProcess([], 0, "corrected", ""),
                ]) as run:
            outcome = host.resync()
        self.assertEqual(outcome["status"], "completed")
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(commands[1], ["systemctl", "is-active", "chronyd.service"])
        self.assertEqual(commands[2], [
            host.PKEXEC, host.CHRONYD_PATHS[0], "-q", "-t", "15"])
        self.assertFalse(any("set-ntp" in command for command in commands))

    def test_running_service_not_duplicated_when_probe_fails(self):
        with patch.object(host.os.path, "isfile", return_value=True), \
                patch.object(host.subprocess, "run", side_effect=[
                    subprocess.CompletedProcess([], 1, "", "no socket"),
                    subprocess.CompletedProcess([], 0, "active\n", ""),
                ]) as run:
            outcome = host.resync()
        self.assertEqual(outcome["status"], "unavailable")
        self.assertEqual(run.call_count, 2)

    def test_auth_cancelled_is_distinct_from_execution_failure(self):
        cancel = host.classify_failure(126, "User dismissed the dialogue")
        self.assertEqual(cancel["status"], "cancelled")
        self.assertEqual(cancel["errorCode"], "AUTH_CANCELLED")
        exec_error = host.classify_failure(127, "Not authorized")
        self.assertEqual(exec_error["errorCode"], "POLKIT_OR_EXEC_ERROR")

    def test_chrony_reports_specific_source_failures_safely(self):
        unavailable = host.classify_failure(
            1, "No suitable source for synchronisation: 10.1.2.3")
        self.assertEqual(unavailable["errorCode"], "SOURCE_UNAVAILABLE")
        self.assertNotIn("10.1.2.3", unavailable["message"])
        dns = host.classify_failure(
            1, "Temporary failure in name resolution for private.example")
        self.assertEqual(dns["errorCode"], "SOURCE_DNS")
        self.assertNotIn("private.example", dns["message"])
        generic = host.classify_failure(3, "other failure")
        self.assertEqual(generic["errorCode"], "CHRONY_FAILED")
        self.assertEqual(generic["exitCode"], 3)

    def test_failed_privileged_attempt_is_not_reported_as_completed(self):
        with patch.object(host.subprocess, "run", return_value=
                          subprocess.CompletedProcess([], 126, "", "Dismissed")):
            value = host.privileged([host.CHRONYC, "burst", "4/4"],
                                    "requested", "SAMPLES REQUESTED", 45)
        self.assertEqual(value["status"], "cancelled")

    def test_readonly_diagnostic_of_inactive_service(self):
        with patch.object(host.os.path, "isfile", return_value=True), \
                patch.object(host.subprocess, "run", return_value=
                             subprocess.CompletedProcess([], 3, "inactive\n", "")) as run:
            value = host.diagnose()
        self.assertEqual(value["status"], "ready")
        self.assertIn("ONE-SHOT", value["message"])
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0],
                         ["systemctl", "is-active", "chronyd.service"])

    def test_diagnostic_is_available_without_actuation(self):
        service = (ROOT / "services/time/TimeSettings.qml").read_text()
        pane = (ROOT / "widgets/TimeSettingsPane.qml").read_text()
        self.assertIn("function diagnoseResync()", service)
        self.assertIn('TimeHostControl.py"), "diagnose"', service)
        self.assertIn("TimeSettings.diagnoseResync()", pane)
        self.assertIn('label: "DIAGNOSE"', pane)
        self.assertIn("TimeSettings.resyncErrorCode", pane)

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
