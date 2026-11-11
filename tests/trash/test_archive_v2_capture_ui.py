"""Trash++ V2f UI contract: only two source families get explicit snapshots."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
QML = (ROOT / "modules/Trash.qml").read_text(encoding="utf-8")
CLI = (ROOT / "scripts/trash/archive_v2_capture_cli.py").read_text(encoding="utf-8")
ADAPTER = (ROOT / "scripts/trash/owner_snapshot_adapter_v2.py").read_text(
    encoding="utf-8")


class SnapshotCaptureUiTests(unittest.TestCase):
    def test_source_copy_button_is_opt_in_and_owner_scoped(self):
        for marker in ('function snapshotSource(row)', 'function requestSnapshot(row)',
                       'function consumeSnapshot(raw)', 'id: snapshotCaptureProcess',
                       'id: saveSnapshotButton', 'label: "SAVE SNAPSHOT"',
                       '? "CONFIRM COPY" : "SAVE SNAPSHOT"',
                       'onLeftClicked: trashLauncher.requestSnapshot(modelData)',
                       'row.capabilities.saveCopy !== true',
                       'row.kind === "WEB SCRAPE"',
                       'row.kind === "EVENT HISTORY"',
                       'found.ownerId === "demo-scrape"',
                       'found.ownerId === "weather-events"',
                       'snapshotSource(row)'):
            self.assertIn(marker, QML)
        for forbidden in ('row.kind === "HUB NOTE" && found.ownerId',
                          'row.kind === "SAVED DOSSIER" && found.ownerId',
                          'row.kind === "HUB TASK" && found.ownerId',
                          'onLeftClicked: trashLauncher.captureSnapshot('):
            self.assertNotIn(forbidden, QML)
        self.assertIn('Quickshell.shellPath("scripts/trash/archive_v2_capture_cli.py")', QML)

    def test_snapshot_is_separate_from_legacy_and_burn(self):
        for marker in ('function saveDemoCopy(row)', 'function saveWeatherEventCopy(row)',
                       'function runResearch(action, args)', 'id: researchProcess',
                       'id: archiveV2Process', 'id: trashProcess',
                       'snapshotPendingAction = confirming ? "capture" : "preview"',
                       'snapshotStatus = "SAVED // INDEPENDENT READ-ONLY COPY"',
                       'snapshotStatus = "SOURCE CHECKED // CLICK CONFIRM COPY"',
                       'snapshotBusy || confirmMode !== ""',
                       'snapshotStatus !== "IDLE"'):
            self.assertIn(marker, QML)
        self.assertIn('if (!snapshotBusy || snapshotPendingAction !== "capture")', QML)
        self.assertIn('snapshotCaptureProcess.exec(args)', QML)
        self.assertIn('snapshotWitness = preview.sourceRevision', QML)
        self.assertIn('clearSnapshotArm();', QML)
        self.assertNotIn('onLeftClicked: trashLauncher.runResearch("burn",', QML)
        # New CLI has no source mutations or destructive verbs.
        self.assertIn('PREVIEW_OR_CAPTURE_ONLY', CLI)
        self.assertNotIn('def delete(', CLI)
        self.assertNotIn('def burn(', CLI)
        self.assertNotIn('def restore(', CLI)

    def test_preview_does_not_need_archive_writer(self):
        self.assertIn('class PilotSnapshotReader:', ADAPTER)
        self.assertIn('class PilotSnapshotAdapter(PilotSnapshotReader):', ADAPTER)
        self.assertIn('reader = PilotSnapshotReader(', CLI)
        self.assertIn('writer = PilotSnapshotAdapter(', CLI)
        self.assertIn('STALE_SOURCE_REFRESH_REQUIRED', CLI)
        self.assertIn('hmac.compare_digest(', CLI)
        self.assertIn('Path.home()', CLI)


if __name__ == "__main__":
    unittest.main()
