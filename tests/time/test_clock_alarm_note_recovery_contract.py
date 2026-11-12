"""Clock NOTE recovery: exact ownership boundary and guarded UI contracts."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PANE = (ROOT / "widgets/AlarmManagerPane.qml").read_text(encoding="utf-8")
POLICY = (ROOT / "services/time/AlarmNoteDraftPolicy.js").read_text(encoding="utf-8")
SERVICE = (ROOT / "services/time/AlarmNoteRecoveryService.qml").read_text(encoding="utf-8")
MANAGER = (ROOT / "services/time/AlarmManagerService.qml").read_text(encoding="utf-8")
MODULE = (ROOT / "services/time/qmldir").read_text(encoding="utf-8")


class ClockAlarmNoteRecovery(unittest.TestCase):
    def test_note_recovery_is_a_sidecar_not_a_second_alarm_writer(self):
        self.assertIn("singleton AlarmNoteRecoveryService 1.0 AlarmNoteRecoveryService.qml", MODULE)
        self.assertIn('"/alarm-note-draft-v1.json"', SERVICE)
        self.assertIn("AlarmManagerService.storagePath", SERVICE)
        self.assertEqual(SERVICE.count("FileView {"), 2)
        self.assertIn('id: draftFile', SERVICE)
        self.assertIn('atomicWrites: true', SERVICE)
        self.assertIn('id: alarmReadFile', SERVICE)
        self.assertIn('alarmReadFile.reload()', SERVICE)
        self.assertNotIn('alarmReadFile.setText(', SERVICE)
        self.assertNotIn('alarmFile.setText(', SERVICE)
        self.assertIn("AlarmManagerService.saveAlarm(id, pendingPatch)", SERVICE)
        self.assertIn("AlarmManagerService.saveAlarmNote(pendingId, pendingDraft.after)", SERVICE)
        self.assertNotIn("AlarmNoteRecoveryService", MANAGER)
        for forbidden in ("Process {", "Window {", "pushRich(", "playSound("):
            self.assertNotIn(forbidden, SERVICE)

    def test_draft_ack_precedes_canonical_write_and_save_receipt(self):
        stage = SERVICE.split('function saveWithPatch(id, edit) {',1)[1].split(
            'function saveNote(id, note) {',1)[0]
        self.assertIn('pendingSource = JSON.stringify(AlarmManagerService.document)', stage)
        self.assertIn('phase = "draft"', stage)
        self.assertIn("draftFile.setText(JSON.stringify(prepared.document)", stage)
        self.assertNotIn('AlarmManagerService.saveAlarm(', stage)
        self.assertIn('if (recovery.phase === "draft" && recovery.draftState === "writing")', SERVICE)
        self.assertIn('recovery.beginCanonicalWrite()', SERVICE)
        self.assertIn('pendingSource !== JSON.stringify(AlarmManagerService.document)', SERVICE)
        self.assertIn('Draft.disposition(pendingDraft, AlarmManagerService.document)', SERVICE)
        self.assertIn('phase = "journal"', SERVICE)
        self.assertIn('function observeCanonicalWrite()', SERVICE)
        self.assertIn('AlarmManagerService.storageState === "ready"', SERVICE)
        self.assertIn('noteSaved(id)', SERVICE)
        self.assertIn('beginClear()', SERVICE)
        self.assertIn('function abortPending(reason)', SERVICE)
        self.assertIn('noteSaveFailed(id, reason)', SERVICE)
        self.assertIn('interval: 12000', SERVICE)
        self.assertIn('WRITE STALLED // NO RETRY', SERVICE)

    def test_recovery_requires_manual_fresh_disk_check_and_current_source(self):
        self.assertIn('function checkDisk()', SERVICE)
        self.assertIn('if (!recovery.checkPending) return;', SERVICE)
        self.assertIn('diskChecked = true', SERVICE)
        self.assertIn('function retryVerified()', SERVICE)
        self.assertIn('function clearVerified()', SERVICE)
        self.assertIn('diskChecked && disposition === "recoverable"', SERVICE)
        self.assertIn('diskChecked && disposition === "already-saved"', SERVICE)
        self.assertIn('JSON.stringify(AlarmManagerService.document)', SERVICE)
        self.assertIn('=== JSON.stringify(diskDocument)', SERVICE)
        self.assertIn('function disposition(d, doc)', POLICY)
        self.assertIn('return "conflict"', POLICY)
        self.assertIn('"identity-conflict"', POLICY)
        self.assertIn('return "already-saved"', POLICY)
        self.assertIn('return "recoverable"', POLICY)

    def test_original_alarm_ui_routes_note_edits_to_sidecar(self):
        self.assertIn('AlarmNoteRecoveryService.saveNote(id, alarmNote.text)', PANE)
        self.assertIn('AlarmNoteRecoveryService.saveWithPatch(selectedId, patch)', PANE)
        self.assertIn('function onNoteSaved(alarmId)', PANE)
        self.assertIn('function onNoteSaveFailed(alarmId, reason)', PANE)
        self.assertIn('pane.settleNoteWrite(true, "")', PANE)
        self.assertIn('pane.settleNoteWrite(false, reason)', PANE)
        self.assertIn('function settleNoteWrite(success, reason)', PANE)
        self.assertIn('id: noteRecoveryEditor', PANE)
        self.assertIn('label: "CHECK DISK"', PANE)
        self.assertIn('AlarmNoteRecoveryService.checkDisk()', PANE)
        self.assertIn('AlarmNoteRecoveryService.retryVerified()', PANE)
        self.assertIn('AlarmNoteRecoveryService.clearVerified()', PANE)
        self.assertIn('AlarmNoteRecoveryService.noteDraft.after', PANE)
        self.assertIn('readOnly: true', PANE)
        self.assertIn('id: editOptions', PANE)
        self.assertIn('height: 99', PANE)
        self.assertIn('id: listFrame', PANE)
        self.assertNotIn('onStorageStateChanged() {\\n            pane.settleNoteWrite()', PANE)


if __name__ == "__main__":
    unittest.main()
