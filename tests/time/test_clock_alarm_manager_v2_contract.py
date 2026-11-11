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

    def test_pinned_management_controls_and_tabbed_optional_sound(self):
        self.assertIn('Item {\n    id: pane\n    clip: true', PANE)
        self.assertIn('id: pinnedControls', PANE)
        self.assertIn('id: managerCommands', PANE)
        self.assertIn('id: alarmSearch', PANE)
        self.assertIn('id: newAlarm', PANE)
        self.assertIn('id: duplicateAlarm', PANE)
        self.assertIn('id: emergencyStop', PANE)
        self.assertIn('visible: AlarmManagerService.ringingCount > 0', PANE)
        self.assertIn('id: entryFields', PANE)
        self.assertIn('id: editorActions', PANE)
        self.assertIn('id: editTabs', PANE)
        self.assertIn('id: editOptions', PANE)
        self.assertIn('height: 99', PANE)
        self.assertIn('property string settingsTab: "schedule"', PANE)
        self.assertIn('pane.settingsTab === "sound"', PANE)
        self.assertIn('pane.settingsTab === "pause"', PANE)
        self.assertIn('pane.settingsTab === "schedule"', PANE)
        self.assertIn('id: soundChoices', PANE)
        self.assertIn('id: soundOptions', PANE)
        self.assertIn('id: volumeRow', PANE)
        self.assertIn('"TEST SOUND"', PANE)
        self.assertIn('"SAVE + ARM"', PANE)
        self.assertIn('CONFIRM DELETE // PRESS RED X AGAIN', PANE)
        self.assertIn('"STOP ALL"', PANE)
        self.assertIn('"SNOOZE // 5M"', PANE)
        self.assertIn('"ONE TIME"', PANE)
        self.assertIn('"REPEAT / WEEKLY"', PANE)
        self.assertIn('draftDays', PANE)
        self.assertIn('toggleDay(index)', PANE)
        self.assertIn('AlarmManagerService.createAlarm()', PANE)
        self.assertIn('AlarmManagerService.removeAlarm(id)', PANE)
        self.assertIn('AlarmManagerService.saveAlarm(selectedId, patch)', PANE)

    def test_only_lower_saved_items_scroll_inside_bounded_timew(self):
        self.assertIn('id: listFrame', PANE)
        self.assertIn('y: pinnedControls.y + pinnedControls.implicitHeight + 5', PANE)
        self.assertIn('height: Math.max(0, pane.height - y)', PANE)
        self.assertIn('ListView {', PANE)
        self.assertIn('id: alarmList', PANE)
        self.assertIn('id: listRail', PANE)
        self.assertIn('NeonScrollBar {', PANE)
        self.assertIn('accountForContentOrigin: true', PANE)
        self.assertIn('geometryMode: "viewport"', PANE)
        self.assertIn('containGlow: true', PANE)
        self.assertIn('interactive: contentHeight > height', PANE)
        self.assertNotIn('id: alarmViewport', PANE)
        self.assertNotIn('id: editorScroll', PANE)
        self.assertNotIn('id: panRow', PANE)
        self.assertIn('505 - toolsSubModeStrip.height', TIMEW)
        self.assertIn('- parent.spacing - 24', TIMEW)

    def test_previous_and_next_are_pinned_in_timew_bottom_footer(self):
        footer = TIMEW.split('id: alarmFooterNavigation', 1)[1].split(
            '                    GohuText {\n                        // The floating result sheet',
            1)[0]
        self.assertIn('visible: timew.selectedMode === "tools"', footer)
        self.assertIn('timew.toolsView === "alarm"', footer)
        self.assertIn('label: "◀ PREVIOUS"', footer)
        self.assertIn('label: "NEXT ▶"', footer)
        self.assertIn('alarmPlaceholderPane.stepSelection(-1)', footer)
        self.assertIn('alarmPlaceholderPane.stepSelection(1)', footer)
        self.assertIn('alarmPlaceholderPane.selectionLabel', footer)
        self.assertIn('alarmPlaceholderPane.canStepSelection', footer)
        self.assertIn('readonly property bool canStepSelection:', PANE)
        self.assertIn('function stepSelection(delta)', PANE)
        self.assertIn('&& timew.toolsView === "alarm")', TIMEW)
        self.assertNotIn('TOOLS // ALARMS // SAVED + SCHEDULED', TIMEW)

    def test_new_alarm_selects_only_local_today_and_legacy_stays_daily(self):
        self.assertIn('weekdays: [new Date(instant).getDay()]', POLICY)
        self.assertIn('var instant = timestamp(nowMs)', POLICY)
        self.assertIn('function create(doc, nowMs)', POLICY)
        self.assertIn('Policy.create(document, Date.now())', OWNER)
        self.assertIn('a.weekdays = [0, 1, 2, 3, 4, 5, 6]', POLICY)
        self.assertIn('property var draftDays: [new Date().getDay()]', PANE)
        self.assertIn('draftDays = a.weekdays.slice()', PANE)
        self.assertIn('pane.draftDays.indexOf(index) >= 0', PANE)
        self.assertIn('if (pane.draftDays.length === 0)', PANE)
        self.assertIn('pane.draftDays = [new Date().getDay()]', PANE)

    def test_entry_actions_are_ordered_and_confirmed(self):
        # The row is fully inside the existing clipped/scrolling list.
        row = PANE.split('delegate: Row {', 1)[1].split(
            '        NeonScrollBar {', 1)[0]
        self.assertLess(row.index('id: favoriteAlarm'), row.index('id: toggleAlarm'))
        self.assertLess(row.index('id: toggleAlarm'), row.index('id: selectAlarm'))
        self.assertLess(row.index('id: selectAlarm'), row.index('id: noteAlarm'))
        self.assertLess(row.index('id: noteAlarm'), row.index('id: deleteAlarm'))
        self.assertIn('onLeftClicked: AlarmManagerService.toggleFavorite(', row)
        self.assertIn('onLeftClicked: pane.openNote(entry.rowAlarm.id)', row)
        self.assertIn('onLeftClicked: pane.removeById(entry.rowAlarm.id)', row)
        self.assertIn('pane.deleteConfirmId === entry.rowAlarm.id', row)
        self.assertIn('CONFIRM DELETE // PRESS RED X AGAIN', PANE)
        self.assertIn('id: listRail', PANE)
        self.assertIn('id: alarmList', PANE)
        self.assertNotIn('pane.removeSelected()', PANE)

    def test_note_editor_uses_explicit_save_and_preserves_failed_draft(self):
        self.assertIn('property bool noteDirty: false', PANE)
        self.assertIn('property int noteSavePendingId: 0', PANE)
        self.assertIn('function canLeaveNote(id)', PANE)
        self.assertIn('SAVE OR DISCARD NOTE BEFORE CHANGING ALARM', PANE)
        self.assertIn('function saveNote()', PANE)
        self.assertIn('function discardNote()', PANE)
        self.assertIn('function settleNoteWrite()', PANE)
        self.assertIn('NOTE NOT SAVED // KEEP DRAFT VISIBLE', PANE)
        self.assertIn('onStorageStateChanged()', PANE)
        self.assertIn('id: alarmNote', PANE)
        self.assertIn('maximumLength: Policy.MAX_NOTE_LENGTH', PANE)
        self.assertIn('readOnly: pane.noteSavePendingId !== 0', PANE)
        self.assertIn('onAccepted: pane.saveNote()', PANE)
        self.assertIn('label: "SAVE NOTE"', PANE)
        self.assertIn('label: "DISCARD DRAFT"', PANE)
        self.assertIn('Policy.validNote(value)', OWNER)
        self.assertIn('function saveAlarmNote(id, value)', OWNER)
        self.assertIn('function toggleFavorite(id)', OWNER)
        self.assertIn('note: alarmNote.text.trim()', PANE)

    def test_legacy_v2_persistence_compatibility_and_unique_names(self):
        self.assertIn('MAX_NOTE_LENGTH = 256', POLICY)
        self.assertIn('function validNote(value)', POLICY)
        self.assertIn('a.favorite === undefined', POLICY)
        self.assertIn('a.note === undefined', POLICY)
        self.assertIn('cloneDocument(v)', POLICY)
        self.assertIn('favorite: false, note: ""', POLICY)
        self.assertIn('name: "New Alarm " + id', POLICY)
        self.assertIn('var suffix = next.nextId;', POLICY)
        self.assertIn('"New Alarm " + suffix', POLICY)
        self.assertIn('"favorite", "note"', POLICY)

    def test_tone_and_time_fields_follow_requested_color_grammar(self):
        self.assertIn('label: "TONE"', PANE)
        tabs = PANE.split('id: editTabs', 1)[1].split(
            'id: editOptions', 1)[0]
        self.assertIn('idleForegroundColor: Colors.cyan', tabs)
        self.assertIn('idleBorderColor: Colors.magenta', tabs)
        self.assertIn('idleSoftGlowColor: Colors.magenta', tabs)
        self.assertIn('selectedForegroundColor: Colors.cyan', tabs)
        self.assertIn('selectedBorderColor: Colors.magenta', tabs)
        for field in ('alarmHour', 'alarmMinute'):
            region = PANE.split('id: ' + field, 1)[1].split(
                'background: Rectangle', 1)[0]
            self.assertIn('color: Colors.white', region)
            self.assertIn('layer.enabled: true', region)
            self.assertIn('shadowColor: Colors.white', region)
        for title in ('HOUR', 'MIN'):
            region = PANE.split('text: "' + title + '"', 1)[1].split(
                '}', 2)[0]
            self.assertIn('color: Colors.white', region)
            self.assertIn('shadowColor: Colors.white', region)
        save = PANE.split('id: editorActions', 1)[1].split(
            'id: ringActions', 1)[0]
        self.assertIn('accentColor: Colors.green', save)
        self.assertNotIn('onLeftClicked: pane.removeSelected()', save)

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
