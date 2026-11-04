"""Camera M2 source contract: explicit folder, full collection, zoom/pan,
image-only Trash and retained independent Camera/Social ownership."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
VIEW = (ROOT / "components/CameraImageViewer.qml").read_text()
QMLDIR = (ROOT / "components/qmldir").read_text()
PANEL = (ROOT / "widgets/CameraW.qml").read_text()
BACKEND = (ROOT / "scripts/camera/camera_cli.py").read_text()
SHELL = (ROOT / "shell.qml").read_text()


class CameraM2ViewerContracts(unittest.TestCase):
    def test_viewer_is_registered_and_supports_wheel_and_drag(self):
        self.assertEqual(QMLDIR.count(
            "CameraImageViewer 1.0 CameraImageViewer.qml"), 1)
        self.assertIn("CameraImageViewer {", PANEL)
        self.assertIn("import QtQuick", VIEW)
        self.assertIn("Flickable {", VIEW)
        self.assertNotIn("WheelHandler {", VIEW)
        self.assertIn("MouseArea {", VIEW)
        self.assertIn("onWheel: function(wheel)", VIEW)
        self.assertIn("wheel.accepted = true", VIEW)
        self.assertIn("onPressed: function(mouse)", VIEW)
        self.assertIn("onPositionChanged: function(mouse)", VIEW)
        self.assertIn("interactive: false", VIEW)
        self.assertIn("Qt.ClosedHandCursor", VIEW)
        self.assertIn("Qt.OpenHandCursor", VIEW)
        self.assertIn("contentWidth:", VIEW)
        self.assertIn("contentHeight:", VIEW)
        self.assertIn("function changeZoom(multiplier, pointerX, pointerY)", VIEW)
        self.assertIn("viewport.contentX =", VIEW)
        self.assertIn("viewport.contentY =", VIEW)
        self.assertIn("function reset()", VIEW)
        self.assertIn("onSourceChanged: reset()", VIEW)
        self.assertIn("maxZoom: 8.0", VIEW)
        self.assertIn("minZoom: 1.0", VIEW)
        self.assertNotIn("onPaint:", VIEW)
        self.assertNotIn("FileView {", VIEW)
        self.assertNotIn("Process {", VIEW)
        self.assertIn("cache: false", VIEW)
        self.assertIn("asynchronous: true", VIEW)

    def test_gallery_uses_server_side_pagination_instead_of_150_cap(self):
        self.assertIn("property int galleryPageIndex: 0", PANEL)
        self.assertIn("property bool galleryHasMore: false", PANEL)
        self.assertIn("property string galleryCustomFolder:", PANEL)
        self.assertIn("galleryFiles.concat(payload.files || [])", PANEL)
        self.assertIn('"--page", String(nextPage)', PANEL)
        self.assertIn('"--query", galleryRequestedQuery', PANEL)
        self.assertIn('"--folder", galleryCustomFolder', PANEL)
        self.assertIn('["--shots-only"]', PANEL)
        self.assertIn("onTextChanged:", PANEL)
        self.assertIn("gallerySearchDebounce.restart()", PANEL)
        self.assertIn("source: camera.fileUrl(modelData.path)", PANEL)
        self.assertIn("model: camera.filteredFiles", PANEL)
        self.assertIn('label: "LOAD 120 MORE"', PANEL)
        self.assertIn("MAX_SCAN_FILES = 60000", BACKEND)
        self.assertIn("MAX_SCAN_DEPTH = 4", BACKEND)
        self.assertNotIn("MAX_GALLERY = 150", BACKEND)
        self.assertIn("def safe_user_folder(raw):", BACKEND)
        self.assertIn("if entry.name.startswith", BACKEND)
        self.assertIn("extra_folder", BACKEND)

    def test_selected_trash_is_two_phase_and_never_unlink_original(self):
        self.assertIn("function previewSelectedTrash()", PANEL)
        self.assertIn("function confirmSelectedTrash()", PANEL)
        self.assertIn('["preview-selected", selectedPath]', PANEL)
        self.assertIn('["trash-selected", plan.planId, "MOVE_TO_TRASH"]', PANEL)
        self.assertIn('label: "MOVE SELECTED TO TRASH"', PANEL)
        self.assertIn('label: "CONFIRM TRASH"', PANEL)
        self.assertIn('label: "CANCEL"', PANEL)
        self.assertIn("selectedTrashPreview = null", PANEL)
        self.assertIn("def preview_selected_trash(raw_path):", BACKEND)
        self.assertIn("def trash_selected(token, confirmation):", BACKEND)
        self.assertIn('"version": 2', BACKEND)
        self.assertIn('if confirmation != "MOVE_TO_TRASH"', BACKEND)
        self.assertIn("fingerprint != record.get", BACKEND)
        self.assertIn('subprocess.run([gio, "trash", str(target)]', BACKEND)
        self.assertNotIn("target.unlink()", BACKEND)
        self.assertNotIn("shutil.rmtree", BACKEND)
        self.assertNotIn("shell=True", BACKEND)
        self.assertIn('id: messagingWindow', SHELL)
        self.assertIn('id: cameraWindow', SHELL)


if __name__ == "__main__":
    unittest.main()
