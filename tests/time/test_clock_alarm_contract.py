"""Clock V1 alarm: audible local alarm with durable daily schedule."""
from pathlib import Path
import unittest
import wave

ROOT = Path(__file__).resolve().parents[2]
TIMEW = (ROOT / "widgets/TimeW.qml").read_text(encoding="utf-8")
PANE = (ROOT / "widgets/AlarmPane.qml").read_text(encoding="utf-8")
OWNER = (ROOT / "services/time/AlarmService.qml").read_text(encoding="utf-8")
POLICY = (ROOT / "services/time/AlarmPolicy.js").read_text(encoding="utf-8")
AUDIO = (ROOT / "services/time/AlarmAudio.qml").read_text(encoding="utf-8")
MODULE = (ROOT / "services/time/qmldir").read_text(encoding="utf-8")


class ClockAlarmContracts(unittest.TestCase):
    def test_one_owner_and_explicit_page_in_timew(self):
        self.assertIn('singleton AlarmService 1.0 AlarmService.qml', MODULE)
        self.assertIn('AlarmPane {', TIMEW)
        self.assertIn('id: alarmPlaceholderPane', TIMEW)
        self.assertIn('timew.toolsView === "alarm"', TIMEW)
        self.assertNotIn('ALARM CONTROLS // NOT IMPLEMENTED', TIMEW)
        self.assertNotIn('import QtMultimedia', TIMEW)
        self.assertNotIn('import QtMultimedia', OWNER)
        self.assertIn('import qs.services.time', PANE)
        self.assertIn('!alarmPlaceholderPane.editingActive', TIMEW)
        self.assertIn('readonly property bool editingActive:', PANE)

    def test_actual_time_is_not_visual_calibration(self):
        self.assertIn('AlarmPolicy.tick(document, nowMs)', OWNER)
        self.assertIn('onTriggered: {', OWNER)
        self.assertIn('alarmService.nowMs = Date.now()', OWNER)
        self.assertNotIn('displayOffsetMs', OWNER + POLICY)
        self.assertNotIn('TimeSettings.adjustedEpochMs', OWNER)
        self.assertIn('function todayAt(nowMs, hour, minute)', POLICY)

    def test_atomic_store_and_durable_no_double_fire(self):
        self.assertIn('"/time-alarm-v1.json"', OWNER)
        self.assertIn('atomicWrites: true', OWNER)
        self.assertIn('watchChanges: false', OWNER)
        self.assertIn('if (pendingDocument !== null)', OWNER)
        self.assertIn('queuedDocument = next;', OWNER)
        self.assertIn('lastFiredDay', POLICY)
        self.assertIn('volumePercent: 60', POLICY)
        self.assertIn('function withVolume(doc, value)', POLICY)
        self.assertIn('AlarmService.setVolumePercent(', PANE)
        self.assertIn('ringStartedAtMs', POLICY)
        self.assertIn('MAX_LATE_MS = 2 * 60 * 1000', POLICY)
        self.assertIn('MAX_RING_MS = 15 * 60 * 1000', POLICY)
        self.assertIn('!/[\\x00-\\x1f\\x7f]/.test(value)', POLICY)
        self.assertIn('INVALID ALARM FILE // NOT OVERWRITTEN', OWNER)

    def test_bounded_explicit_actions_and_emergency_silence(self):
        for action in ('arm(', 'disarm()', 'stopRinging()', 'snoozeRinging()',
                       'setSoundEnabled(', 'previewSound()'):
            self.assertIn('AlarmService.' + action, PANE)
        self.assertIn('stopAudio(); // emergency silence must never', OWNER)
        self.assertIn('SILENCED HERE // STORAGE FAILED', OWNER)
        self.assertIn('SNOOZED HERE // STORAGE FAILED', OWNER)
        self.assertNotIn('pkexec', OWNER + POLICY)
        self.assertNotIn('set-timezone', OWNER + POLICY)
        self.assertNotIn('resyncProcess', OWNER + POLICY)
        self.assertNotIn('Process {', OWNER)

    def test_sound_fails_independently_of_alarm_scheduler(self):
        self.assertIn('active: false', OWNER)
        self.assertIn('source: "AlarmAudio.qml"', OWNER)
        self.assertIn('if (status === Loader.Error)', OWNER)
        self.assertIn('AUDIO MODULE UNAVAILABLE', OWNER)
        self.assertIn('import QtMultimedia', AUDIO)
        self.assertIn('SoundEffect {', AUDIO)
        self.assertIn('loops: SoundEffect.Infinite', AUDIO)
        self.assertIn('Qt.resolvedUrl("../../assets/sounds/clock-alarm-chime.wav")', AUDIO)
        self.assertIn('soundPreviewTimeout', OWNER)
        self.assertIn('interval: 4000', OWNER)

    def test_alarm_sound_is_original_short_mono_pcm_wav(self):
        path = ROOT / "assets/sounds/clock-alarm-chime.wav"
        with wave.open(str(path), "rb") as wav:
            self.assertEqual(wav.getnchannels(), 1)
            self.assertEqual(wav.getsampwidth(), 2)
            self.assertEqual(wav.getframerate(), 48000)
            self.assertLessEqual(wav.getnframes(), 48000 * 2)


if __name__ == "__main__":
    unittest.main()
