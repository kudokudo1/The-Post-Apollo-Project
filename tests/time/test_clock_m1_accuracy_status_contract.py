"""Clock M1: accuracy header, source evidence and sync verification.

All Chrony calls are mocked or pure parser checks. This test never changes
host time, NTP, RTC, timezone, or local persistent settings.
"""
import datetime
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
HOST_PATH = ROOT / "services/time/TimeHostControl.py"
SPEC = importlib.util.spec_from_file_location("clock_m1_host", HOST_PATH)
host = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(host)

SERVICE = (ROOT / "services/time/TimeSettings.qml").read_text()
TIMEW = (ROOT / "widgets/TimeW.qml").read_text()
DOCK = (ROOT / "modules/Clock.qml").read_text()


def tracking(*, timestamp="Wed Nov 04 05:00:00 2026",
             system="0.050000000 seconds slow of NTP time",
             delay="0.020000", dispersion="0.010000",
             leap="Normal", reference="CB00710F (source)", stratum="3"):
    return (
        f"Reference ID : {reference}\n"
        f"Stratum : {stratum}\n"
        f"Ref time (UTC) : {timestamp}\n"
        f"System time : {system}\n"
        f"Root delay : {delay} seconds\n"
        f"Root dispersion : {dispersion} seconds\n"
        f"Leap status : {leap}\n"
    )


NOW = datetime.datetime(2026, 11, 4, 5, 1,
                        tzinfo=datetime.timezone.utc)


class ClockAccuracyStatusContract(unittest.TestCase):
    def test_valid_recent_chrony_estimate_has_error_bound_and_source(self):
        value = host.parse_tracking_measurement(tracking(), at_utc=NOW)
        self.assertEqual(value["status"], "measured")
        self.assertEqual(value["offsetMs"], -50)
        self.assertEqual(value["uncertaintyMs"], 20)
        self.assertEqual(value["source"], "CHRONY_TRACKING")

    def test_unsynchronised_or_local_chrony_cannot_claim_accuracy(self):
        for payload, code in [
                (tracking(leap="Not synchronised"), "TRACKING_UNSYNCED"),
                (tracking(reference="7F7F0101 (local)"), "TRACKING_LOCAL"),
                (tracking(reference="00000000 ()"), "TRACKING_LOCAL"),
                (tracking(stratum="0"), "TRACKING_INVALID"),
                (tracking(system="nonsense"), "TRACKING_INVALID"),
                (tracking(dispersion="inf"), "TRACKING_INVALID"),
        ]:
            with self.subTest(payload=payload):
                value = host.parse_tracking_measurement(
                    payload, at_utc=NOW)
                self.assertEqual(value["status"], "unavailable")
                self.assertEqual(value["errorCode"], code)

    def test_expired_and_future_tracking_references_rejected(self):
        for timestamp in ("Wed Nov 04 04:00:00 2026",
                          "Wed Nov 04 05:03:00 2026"):
            with self.subTest(timestamp=timestamp):
                value = host.parse_tracking_measurement(
                    tracking(timestamp=timestamp), at_utc=NOW)
                self.assertEqual(value["errorCode"], "TRACKING_STALE")

    def test_tracking_large_uncertainty_is_not_confused_with_low_offset(self):
        value = host.parse_tracking_measurement(
            tracking(system="0.000100 seconds fast of NTP time",
                     delay="1.000000", dispersion="1.000000"),
            at_utc=NOW)
        self.assertEqual(value["status"], "measured")
        self.assertEqual(value["offsetMs"], 0)
        self.assertEqual(value["uncertaintyMs"], 1500)

    def test_timezone_offset_regex_accepts_real_iana_offsets(self):
        # Two backslashes in a JS regular expression match a literal \d,
        # not a digit. The host sends values such as UTC-05:00.
        correct = r"const match = /^UTC([+-])(\d{2}):(\d{2})$/.exec(text);"
        incorrect = r"const match = /^UTC([+-])(\\d{2}):(\\d{2})$/.exec(text);"
        self.assertIn(correct, SERVICE)
        self.assertNotIn(incorrect, SERVICE)
        self.assertIn("hostMinutes !== qmlMinutes", SERVICE)

    def test_header_is_not_selected_mode_placeholder(self):
        header = TIMEW.split("id: stateIndicator", 1)[1].split(
            "id: syncButton", 1)[0]
        self.assertIn("clockAccuracyState(localClock.date.getTime())", header)
        self.assertIn("clockAccuracyLabel(", header)
        self.assertIn("clockAccuracyDetail(", header)
        self.assertIn('width: 99', header)
        self.assertNotIn('"PLANNED"', header)
        self.assertNotIn("timew.selectedMode", header)
        self.assertIn("accuracyColor", header)
        self.assertIn("ANGEL // RESERVED", TIMEW)

    def test_health_status_uses_actual_evidence_with_unknown_fallback(self):
        self.assertIn('case "out-of-sync": return "OUT OF SYNC"', SERVICE)
        self.assertIn('case "dirty": return "DIRTY"', SERVICE)
        self.assertIn('case "in-sync": return "IN SYNC"', SERVICE)
        self.assertIn('case "uncertain": return "UNCERTAIN"', SERVICE)
        self.assertIn('default: return "UNCHECKED"', SERVICE)
        self.assertIn("referenceIsOutOfSync(nowEpochMs)", SERVICE)
        self.assertIn("referenceIsUncertain(nowEpochMs)", SERVICE)
        self.assertIn("displayDeviationActive", SERVICE)
        self.assertIn("dockZoneOffsetMismatch(nowEpochMs)", SERVICE)
        self.assertIn("hasFreshReference(nowEpochMs)", SERVICE)
        self.assertIn("referenceMaxAgeMs: 15 * 60 * 1000", SERVICE)
        self.assertNotIn(
            "ntpSynchronized", SERVICE.split("function clockAccuracyState", 1)[1]
            .split("function clockAccuracyLabel", 1)[0])
        self.assertIn("TimeSettings.dockTimeUnderlined", DOCK)

    def test_burst_and_one_shot_both_request_single_post_sync_check(self):
        self.assertIn('value.status === "completed"', SERVICE)
        self.assertIn('|| value.status === "requested"', SERVICE)
        self.assertIn("postResyncVerificationPending = false;", SERVICE)
        self.assertIn("function runPostResyncVerification()", SERVICE)
        self.assertIn("resyncProcess.running", SERVICE)
        self.assertIn("timeSettings.runPostResyncVerification();", SERVICE)
        self.assertIn("TimeHostControl.py\"), \"measure\"", SERVICE)
        self.assertNotIn("set-ntp", SERVICE)
        self.assertNotIn("set-local-rtc", SERVICE)

    def test_backend_measurements_are_read_only(self):
        host_code = HOST_PATH.read_text()
        self.assertIn('[CHRONYC, "tracking"]', host_code)
        self.assertIn('[chronyd, "-Q", "-t", "15"]', host_code)
        self.assertIn('"TRACKING_UNSYNCED"', host_code)
        self.assertIn('"TRACKING_STALE"', host_code)
        self.assertIn("parse_tracking_measurement", host_code)
        self.assertIn("root", host_code.lower())


if __name__ == "__main__":
    unittest.main()
