"""Clock Alarm V2 source, migration, UI and sound-file contracts."""
from pathlib import Path
import unittest
import wave

ROOT = Path(__file__).resolve().parents[2]
TIMEW = (ROOT / "widgets/TimeW.qml").read_text(encoding="utf-8")
MODULE = (ROOT / "services/time/qmldir").read_text(encoding="utf-8")
POLICY = (ROOT / "services/time/AlarmManagerPolicy.js").read_text(encoding="utf-8")
OWNER = (ROOT / "services/time/AlarmManagerService.qml").read_text(encoding="utf-8")
PANE = (ROOT / "widgets/AlarmManagerPane.qml").read_text(encoding="utf-8")
AUDIO = (ROOT / "services/time/AlarmAudioV2.qml").read_text(encoding="utf-8")


class AlarmManagerV2Contracts(unittest.TestCase):
    def test_only_manager_view_is_mounted(self):
        self.assertIn("AlarmManagerPane {", TIMEW)
        self.assertNotIn("                    AlarmPane {", TIMEW)
        self.assertIn("singleton AlarmManagerService 1.0 AlarmManagerService.qml", MODULE)
        self.assertIn('!alarmPlaceholderPane.editingActive', TIMEW)
        self.assertIn("readonly property bool editingActive:", PANE)
        self.assertNotIn("import QtMultimedia", TIMEW + OWNER)
        self.assertNotIn("TimeSettings.adjustedEpochMs", OWNER + POLICY)
        self.assertNotIn("pkexec", OWNER + POLICY)
        self.assertNotIn("Process {", OWNER)

    def test_v2_store_is_atomic_and_does_not_overwrite_old_file(self):
        self.assertIn('"/time-alarms-v2.json"', OWNER)
        self.assertIn('"/time-alarm-v1.json"', OWNER)
        self.assertIn("Policy.migrateLegacy(legacyFile.text(), Date.now())", OWNER)
        self.assertIn("legacyFile", OWNER)
        self.assertIn("V1 FILE PRESERVED", OWNER)
        self.assertIn("atomicWrites: true", OWNER)
        self.assertIn("pendingDocument", OWNER)
        self.assertIn("queuedDocument", OWNER)
        self.assertIn("V2 FILE INVALID // NOT OVERWRITTEN", OWNER)
        self.assertIn("V2 ALARMS UNREADABLE // NOT OVERWRITTEN", OWNER)

    def test_independent_alarm_management(self):
        self.assertIn("MAX_ALARMS = 100", POLICY)
        for token in ['mode: "weekly"', 'mode === "once"', "weekdays",
                      "pausedUntilDate", "keepSaved", "completed", "soundId",
                      "soundEnabled", "volumePercent", "lastFiredDay"]:
            self.assertIn(token, POLICY)
        for fn in ["createAlarm()", "saveAlarm(id, edit)", "enableAlarm(id, enabled)",
                   "pauseAlarm(id, resumeDate)", "removeAlarm(id)",
                   "stopAlarm(id)", "stopAll()", "snoozeAlarm(id)",
                   "previewSound(soundId, volumePercent)"]:
            self.assertIn("function " + fn, OWNER)
        self.assertIn("Policy.tick(document, nowMs)", OWNER)
        self.assertIn("manager.nowMs = Date.now()", OWNER)
        self.assertIn("interval: 1000", OWNER)

    def test_compact_scrollable_list_and_editor(self):
        for token in ["ListView {", "id: alarmList", "id: editorScroll",
                      "id: editorRail", "id: listRail", "NeonScrollBar {",
                      "id: alarmSearch", "stepSelection(delta)",
                      '"ONE TIME"', '"REPEAT / WEEKLY"', '"SAVE + ARM"',
                      '"STOP ALL"', '"CONFIRM DELETE"', '"SNOOZE // 5M"',
                      '"YYYY-MM-DD"', "draftDays", "toggleDay(index)"]:
            self.assertIn(token, PANE)
        self.assertIn("AlarmManagerService.createAlarm()", PANE)
        self.assertIn("AlarmManagerService.removeAlarm(id)", PANE)
        self.assertIn("AlarmManagerService.saveAlarm(selectedId, patch)", PANE)

    def test_compact_alarm_page_is_clipped_and_full_editor_remains_reachable(self):
        # The root is a bounded Item, not a free-growing Column whose
        # implicit height can place the save/delete row outside TimeW.
        self.assertIn('Item {\n    id: pane\n    clip: true', PANE)
        self.assertIn('id: alarmBodyFrame', PANE)
        self.assertIn('height: Math.max(0, pane.height - y)', PANE)
        self.assertIn('id: alarmViewport', PANE)
        self.assertIn('contentHeight: alarmFlow.implicitHeight', PANE)
        self.assertIn('anchors.fill: parent', PANE)
        self.assertIn('anchors.rightMargin: alarmPageRail.crossExtent + 5', PANE)
        self.assertIn('id: alarmFlow', PANE)
        self.assertIn('id: alarmPageRail', PANE)
        self.assertIn('containGlow: true', PANE)
        self.assertIn('height: editorContent.implicitHeight', PANE)
        self.assertNotIn('height: 264', PANE)
        self.assertIn('interactive: false', PANE)
        self.assertIn('y: headerRow.y + headerRow.height + 8', PANE)
        self.assertIn('y: alarmSearch.y + alarmSearch.height + 8', PANE)
        bounded = TIMEW.split('AlarmManagerPane {', 1)[1].split(
            '                    }', 1)[0]
        self.assertIn('505 - toolsSubModeStrip.height', bounded)
        self.assertIn('parent.spacing', bounded)
        self.assertIn('TOOLS // ALARMS // SAVED + SCHEDULED', TIMEW)

    def test_audio_remains_optional_and_ids_allowlisted(self):
        self.assertIn('active: false', OWNER)
        self.assertIn('source: "AlarmAudioV2.qml"', OWNER)
        self.assertIn('if (status === Loader.Error)', OWNER)
        self.assertIn('SOUND_IDS = ["chime", "soft", "urgent"]', POLICY)
        self.assertIn("import QtMultimedia", AUDIO)
        self.assertIn("SoundEffect {", AUDIO)
        self.assertIn("SoundEffect.Infinite", AUDIO)
        for name in ("chime", "soft", "urgent"):
            self.assertIn(f"clock-alarm-{name}.wav", AUDIO)
            with wave.open(str(ROOT / "assets/sounds" / f"clock-alarm-{name}.wav"), "rb") as wav:
                self.assertEqual(wav.getnchannels(), 1)
                self.assertEqual(wav.getsampwidth(), 2)
                self.assertIn(wav.getframerate(), (24000, 48000))
                self.assertLess(wav.getnframes(), wav.getframerate() * 3)

    def test_emergency_silence_even_on_write_failure(self):
        self.assertIn("function stopAll()", OWNER)
        self.assertIn("function stopAlarm(id)", OWNER)
        self.assertIn('SILENCED LOCALLY // SAVE FAILED', OWNER)
        self.assertIn('saveDocument(next)', OWNER)
        self.assertIn("Policy.stop(next, id)", OWNER)


if __name__ == "__main__":
    unittest.main()
