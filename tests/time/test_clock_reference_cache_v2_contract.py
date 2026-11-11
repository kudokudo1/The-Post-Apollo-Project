"""Clock V2: persisted evidence does not weaken resync permission boundaries."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SERVICE = (ROOT / "services/time/TimeSettings.qml").read_text()
REFERENCE = (ROOT / "services/time/TimeReferencePolicy.js").read_text()
AUTO = (ROOT / "services/time/TimeAutoCheckPolicy.js").read_text()
COMPACT = (ROOT / "widgets/TimeSettingsCompact.qml").read_text()
PANE = (ROOT / "widgets/TimeSettingsPane.qml").read_text()


class ClockReferenceV2Contracts(unittest.TestCase):
    def test_reference_separate_from_schedule_and_calibration(self):
        self.assertIn('"/time-reference-v1.json"', SERVICE)
        self.assertIn('"/time-auto-check-v1.json"', SERVICE)
        self.assertIn('"/time-settings-v1.json"', SERVICE)
        self.assertIn('import "TimeReferencePolicy.js" as Reference', SERVICE)
        self.assertIn('id: referenceBootFile', SERVICE)
        self.assertIn('path: "/proc/sys/kernel/random/boot_id"', SERVICE)
        self.assertIn('id: referenceFile', SERVICE)
        self.assertIn('atomicWrites: true', SERVICE)
        self.assertIn('timeSettings.restoreReferenceAfterLoad()', SERVICE)
        self.assertIn('referenceRestoreHandled', SERVICE)
        self.assertIn('referenceBootReadDone', SERVICE)
        self.assertIn('referenceStoreReadDone', SERVICE)

    def test_failure_keeps_last_measurement(self):
        failure = SERVICE.split('function noteReferenceFailure(message) {', 1)[1].split(
            'function recordReferenceMeasurement', 1)[0]
        self.assertIn('referenceCheckedAtMs > 0 ? "measured"', failure)
        self.assertIn('Reference.withFailure(', failure)
        self.assertNotIn('referenceCheckedAtMs = 0', failure)
        self.assertNotIn('referenceOffsetMs = 0', failure)
        self.assertIn('sample: validSample(doc.sample) ? doc.sample : null', REFERENCE)

    def test_reload_waits_for_measurement_restore(self):
        startup = SERVICE.split('function maybeBeginStartupAutoChecks() {', 1)[1].split(
            'function invalidateReferenceForResync()', 1)[0]
        self.assertIn('!referenceRestoreHandled', startup)
        self.assertIn('maybeAutoCheckTime("reload")', startup)
        self.assertIn('autoCheckOpenPendingWhileLoading', startup)
        self.assertIn('hasMeasurement: estimate.available', SERVICE)
        self.assertIn('lastFailureAtMs: referenceFailureAtMs', SERVICE)
        self.assertIn('if (!evidence.hasMeasurement)', AUTO)

    def test_automatic_checks_never_resync(self):
        automatic = SERVICE.split('function maybeAutoCheckTime(trigger) {', 1)[1].split(
            'function completeAutoReferenceIfReady()', 1)[0]
        self.assertIn('checkTimeAccuracy()', automatic)
        self.assertNotIn('resyncProcess.exec(', automatic)
        self.assertNotIn('requestResync(', automatic)
        self.assertNotIn('pkexec', automatic)
        self.assertIn('Reference.estimate(', SERVICE)
        self.assertIn('interval: 1000', SERVICE)
        self.assertIn('referenceNowMs = Date.now()', SERVICE)

    def test_visual_controls_and_explicit_correction_remain(self):
        for ui in (COMPACT, PANE):
            self.assertIn('label: "-1H", delta: -3600000', ui)
            self.assertIn('label: "+1H", delta: 3600000', ui)
            self.assertIn('TimeSettings.adjustDisplayMs(modelData.delta)', ui)
        self.assertIn('TimeSettings.referenceLiveDetail', COMPACT)
        self.assertIn('TimeSettings.referenceLiveDetail', PANE)
        self.assertIn('TimeSettings.prepareResync()', COMPACT)
        self.assertIn('TimeSettings.requestResync()', COMPACT)
        self.assertIn('TimeSettings.cancelResync()', COMPACT)


if __name__ == "__main__":
    unittest.main()
