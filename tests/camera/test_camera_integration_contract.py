"""Static contract for Camera M1, complementing offline executable CLI tests."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
DOCK = (ROOT / "modules/Screenshot.qml").read_text()
PANEL = (ROOT / "widgets/CameraW.qml").read_text()
SHELL = (ROOT / "shell.qml").read_text()
BACKEND = (ROOT / "scripts/camera/camera_cli.py").read_text()
FILES = (ROOT / "services/files/FileService.qml").read_text()
MEDIA = (ROOT / "widgets/MediaDeckW.qml").read_text()


class CameraWidgetContracts(unittest.TestCase):
    def test_existing_empty_dock_slot_reused_and_window_separate(self):
        self.assertIn("DockButton {", DOCK)
        self.assertIn("signal toggleRequested()", DOCK)
        self.assertIn("onLeftClicked: toggleRequested()", DOCK)
        self.assertIn('text: "CAM"', DOCK)
        self.assertIn("id: cameraHost", SHELL)
        self.assertIn("Screenshot {", SHELL)
        self.assertIn("id: cameraDock", SHELL)
        self.assertIn("onToggleRequested: cameraWindow.toggle()", SHELL)
        self.assertIn("CameraW {", SHELL)
        self.assertIn("screen: shellRoot.screen", SHELL)
        self.assertIn("id: sharedMediaDock", SHELL)
        self.assertIn("id: messagingWindow", SHELL)
        self.assertIn("PanelWindow {", PANEL)
        self.assertIn("WlrLayershell.layer: WlrLayer.Overlay", PANEL)
        self.assertIn("exclusiveZone: 0", PANEL)

    def test_capture_modes_and_hidden_panel_before_shutter(self):
        self.assertIn('label: "REGION"', PANEL)
        self.assertIn('label: "ONE SCREEN"', PANEL)
        self.assertIn('label: "BOTH"', PANEL)
        self.assertIn('camera.prepareCapture("region")', PANEL)
        self.assertIn('camera.prepareCapture("focused")', PANEL)
        self.assertIn('camera.prepareCapture("all")', PANEL)
        self.assertIn("menuOpen = false;", PANEL)
        self.assertIn("shutterDelay.restart()", PANEL)
        self.assertIn('["capture", camera.captureMode]', PANEL)
        self.assertIn('Quickshell.shellPath("scripts/camera/camera_cli.py")', PANEL)
        self.assertIn('running: false', PANEL)
        self.assertIn("onStreamFinished: camera.consume(this.text)", PANEL)
        self.assertIn('if mode not in ("region", "focused", "all"):', BACKEND)
        self.assertIn('args.extend(["-o", focused])', BACKEND)
        self.assertIn('args.extend(["-g", geometry])', BACKEND)
        self.assertIn("subprocess.run(args + [str(target)]", BACKEND)
        self.assertIn('"Post-Apollo"', BACKEND)
        self.assertNotIn("shell=True", BACKEND)

    def test_gallery_is_local_file_based_and_scrollable(self):
        self.assertIn('label: "GALLERY"', PANEL)
        self.assertIn("model: camera.filteredFiles", PANEL)
        self.assertIn('id: photoList', PANEL)
        self.assertIn("ListView {", PANEL)
        self.assertIn("NeonScrollBar {", PANEL)
        self.assertIn("handleStyle: \"star\"", PANEL)
        self.assertIn("camera.fileUrl(modelData.path)", PANEL)
        self.assertIn("source: camera.selectedPath", PANEL)
        self.assertIn("Image.PreserveAspectFit", PANEL)
        self.assertIn("Qt.formatDateTime(", PANEL)
        self.assertIn('photoList', PANEL)
        self.assertIn('MAX_GALLERY = 150', BACKEND)
        self.assertIn('"roots": [str(pictures()), str(screenshots_root()), str(desktop())]', BACKEND)
        self.assertIn('property var galleryFiles: []', PANEL)

    def test_batch_trash_needs_preview_and_separate_confirmation(self):
        self.assertIn("function previewCleanup()", PANEL)
        self.assertIn('run("preview", ["preview-trash"])', PANEL)
        self.assertIn("function confirmCleanup()", PANEL)
        self.assertIn('run("trash", ["trash", id, "MOVE_TO_TRASH"])', PANEL)
        self.assertIn('label: "PREVIEW MATCHES"', PANEL)
        self.assertIn('label: camera.trashPreview', PANEL)
        self.assertIn("destructive: true", PANEL)
        self.assertIn("accentColor: Colors.red", PANEL)
        self.assertIn("camera.trashPreview.sample.join", PANEL)
        self.assertIn('PLAN_TTL = 600', BACKEND)
        self.assertIn('MAX_TRASH = 20000', BACKEND)
        self.assertIn('if confirmed != "MOVE_TO_TRASH"', BACKEND)
        self.assertIn('if target.parent != desktop()', BACKEND)
        self.assertIn('signature != record.get("signature")', BACKEND)
        self.assertIn('subprocess.run([gio, "trash", str(target)]', BACKEND)
        self.assertNotIn('subprocess.run(["rm"', BACKEND)
        self.assertIn('"recoverable": True', BACKEND)

    def test_camera_does_not_own_files_media_or_social(self):
        self.assertIn("property string currentDir", FILES)
        self.assertIn("HeadlessMediaController {", MEDIA)
        self.assertNotIn("FileView {", PANEL)
        self.assertNotIn("MediaDeckW {", PANEL)
        self.assertNotIn("MessagingW {", PANEL)
        self.assertNotIn("FileService {", PANEL)
        self.assertNotIn("Timer {", DOCK)
        # The only timer is a one-shot shutter delay, not an automatic capture.
        self.assertIn("repeat: false", PANEL)
        self.assertNotIn("Component.onCompleted: camera.prepareCapture", PANEL)
        self.assertNotIn("onMenuOpenChanged: camera.previewCleanup", PANEL)


if __name__ == "__main__":
    unittest.main()
