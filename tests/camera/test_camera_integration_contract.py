"""Static contract for Camera M1, complementing offline executable CLI tests."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
DOCK = (ROOT / "modules/Screenshot.qml").read_text()
PANEL = (ROOT / "widgets/CameraW.qml").read_text()
CLEANUP = (ROOT / "widgets/CameraCleanupView.qml").read_text()
TRASH = (ROOT / "modules/Trash.qml").read_text()
SHELL = (ROOT / "shell.qml").read_text()
BACKEND = (ROOT / "scripts/camera/camera_cli.py").read_text()
FILES = (ROOT / "services/files/FileService.qml").read_text()
MEDIA = (ROOT / "widgets/MediaDeckW.qml").read_text()


class CameraWidgetContracts(unittest.TestCase):
    def test_existing_empty_dock_slot_reused_and_window_separate(self):
        self.assertIn("DockButton {", DOCK)
        self.assertIn("signal toggleRequested()", DOCK)
        self.assertIn("onLeftClicked: toggleRequested()", DOCK)
        self.assertIn("CameraGlyph {", DOCK)
        self.assertNotIn('text: "CAM"', DOCK)
        self.assertIn("id: cameraHost", SHELL)
        self.assertIn("Screenshot {", SHELL)
        self.assertIn("id: cameraDock", SHELL)
        self.assertIn("cameraWindow.toggle();", SHELL)
        self.assertIn("CameraW {", SHELL)
        self.assertIn("screen: shellRoot.screen", SHELL)
        self.assertIn("id: sharedMediaDock", SHELL)
        self.assertIn("id: messagingWindow", SHELL)
        self.assertIn("PanelWindow {", PANEL)
        self.assertIn("WlrLayershell.layer: WlrLayer.Overlay", PANEL)
        self.assertIn("exclusiveZone: 0", PANEL)

    def test_left_top_tray_order_launcher_workspaces_tray_music_camera(self):
        # This tests the real declaration order in the LEFT Row, not a
        # screenshot-only mock or just the presence of five module names.
        left = SHELL.split("id: leftModules", 1)[1].split(
            "// Hospital", 1)[0]
        ordered = [
            "Applauncher {",
            "Workspaces {}",
            "Tray {}",
            "Mediaplayer {",
            "id: cameraHost",
        ]
        offsets = [left.index(marker) for marker in ordered]
        self.assertEqual(offsets, sorted(offsets))
        self.assertEqual(left.count("Tray {}"), 1)
        self.assertEqual(left.count("Mediaplayer {"), 1)
        self.assertEqual(left.count("Screenshot {"), 1)
        # Preserve the existing left-row spacing and 25px launcher gap.
        self.assertIn("spacing: 8", left)
        self.assertIn("id: appControlWorkspaceGap", left)
        self.assertIn("width: 9", left)
        # Moving dock declarations never transfers their functional owners.
        self.assertIn("id: sharedMediaDock", left)
        self.assertIn("cameraWindow.toggle();", left)

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

    def test_region_button_directly_launches_native_wayland_selector(self):
        self.assertIn('camera.prepareCapture("region")', PANEL)
        self.assertIn('property bool nativeRegionSelecting: false', PANEL)
        self.assertIn('nativeRegionSelecting = true;', PANEL)
        self.assertIn('visible: !camera.nativeRegionSelecting', PANEL)
        self.assertNotIn('regionGuideOpen', PANEL)
        self.assertNotIn('beginRegionSelection', PANEL)
        self.assertNotIn('label: "BEGIN SELECTING"', PANEL)
        setup = PANEL.split('function prepareCapture(mode)', 1)[1].split(
            'function webcamPhoto()', 1)[0]
        self.assertIn('captureMode = mode;', setup)
        self.assertIn('if (mode === "region") {', setup)
        self.assertIn('menuOpen = false;', setup)
        self.assertIn('shutterDelay.restart();', setup)
        self.assertIn('REGION // DRAG TO SELECT', setup)
        # The Camera layer returns on success, cancel, or an unavailable backend.
        self.assertIn('if (action === "capture")\n            nativeRegionSelecting = false;', PANEL)
        self.assertIn('camera.nativeRegionSelecting = false;', PANEL)
        self.assertIn('label: "ONE SCREEN"', PANEL)
        self.assertIn('label: "BOTH"', PANEL)
        # Display guidance belongs to the actual native slurp selection overlay.
        self.assertIn('stdin=subprocess.DEVNULL', BACKEND)
        self.assertIn('slurp, "-d"', BACKEND)
        self.assertIn('"C74EC7FF"', BACKEND)

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
        self.assertIn("GALLERY_PAGE_SIZE = 120", BACKEND)
        self.assertIn("def gallery(page=0, query=", BACKEND)
        self.assertIn("def scan_gallery(extra_folder=", BACKEND)
        self.assertIn('property var galleryFiles: []', PANEL)
        self.assertIn("galleryPageIndex", PANEL)
        self.assertIn("galleryHasMore", PANEL)
        self.assertIn('label: "LOAD 120 MORE"', PANEL)
        self.assertIn('label: "SCREENSHOTS"', PANEL)
        self.assertIn("CameraImageViewer {", PANEL)
        self.assertIn("function previewSelectedTrash()", PANEL)
        self.assertIn("function confirmSelectedTrash()", PANEL)
        self.assertIn('run("previewSelected", ["preview-selected", selectedPath])', PANEL)
        self.assertIn('run("trashSelected", ["trash-selected", plan.planId, "MOVE_TO_TRASH"])', PANEL)
        self.assertIn('label: "CONFIRM TRASH"', PANEL)
        self.assertIn("galleryFolderInput", PANEL)

    def test_batch_trash_needs_preview_and_separate_confirmation(self):
        self.assertIn("function previewCleanup()", PANEL)
        self.assertIn('run("preview", ["preview-trash"])', PANEL)
        self.assertIn("function confirmCleanup()", PANEL)
        self.assertIn('run("trash", ["trash", id, "MOVE_TO_TRASH"])', PANEL)
        self.assertIn('label: "PREVIEW MATCHES"', CLEANUP)
        self.assertIn('label: camera.trashPreview', CLEANUP)
        self.assertIn("destructive: true", PANEL)
        self.assertIn("accentColor: Colors.red", PANEL)
        self.assertIn("camera.trashPreview.sample.join", CLEANUP)
        self.assertIn('PLAN_TTL = 600', BACKEND)
        self.assertIn('MAX_TRASH = 20000', BACKEND)
        self.assertIn('if confirmed != "MOVE_TO_TRASH"', BACKEND)
        self.assertIn('if target.parent != desktop()', BACKEND)
        self.assertIn('signature != record.get("signature")', BACKEND)
        self.assertIn('subprocess.run([gio, "trash", str(target)]', BACKEND)
        self.assertNotIn('subprocess.run(["rm"', BACKEND)
        self.assertIn('"recoverable": True', BACKEND)

    def test_cleanup_menus_are_physically_in_trash_not_in_camera(self):
        self.assertNotIn('id: cleanupPage', PANEL)
        self.assertNotIn('{id: "cleanup", label: "CLEANUP"}', PANEL)
        self.assertIn('id: cleanupPage', CLEANUP)
        self.assertIn('id: cleanupHuntView', CLEANUP)
        self.assertIn('id: cleanupSwipeView', CLEANUP)
        self.assertIn('id: cleanupQueueView', CLEANUP)
        self.assertIn('id: cleanupDesktopView', CLEANUP)
        self.assertIn('CameraCleanupView {', TRASH)
        self.assertIn('cameraCleanupController: cameraWindow', SHELL)
        self.assertIn('hostedCleanupActive: trashWindow.menuOpen', SHELL)
        self.assertIn('hostedCleanupSurface: trashWindow.cleanupContentView', SHELL)
        self.assertIn('property var batchPaths: []', PANEL)
        self.assertNotIn('property var batchPaths: []', CLEANUP)

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
