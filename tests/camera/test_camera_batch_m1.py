"""Camera Batch M1: synthetic local files, mocked GIO; no real deletion."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/camera/camera_cli.py"
QML = ROOT / "widgets/CameraW.qml"
spec = importlib.util.spec_from_file_location("camera_batch_m1", SCRIPT)
camera = importlib.util.module_from_spec(spec)
spec.loader.exec_module(camera)


class CameraBatchM1Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.planroot = self.home / ".state" / "camera-plans"
        self.photos = self.home / "Pictures" / "Screenshots"
        self.photos.mkdir(parents=True)
        self.videos = self.home / "Videos" / "Post-Apollo"
        self.videos.mkdir(parents=True)
        self.a = self.photos / "First.png"
        self.b = self.photos / "Second.jpg"
        self.v = self.videos / "screen_record.mp4"
        self.a.write_bytes(b"first")
        self.b.write_bytes(b"second")
        self.v.write_bytes(b"video")
        for name, value in (("home", self.home),
                            ("plan_dir", self.planroot)):
            patcher = patch.object(camera, name, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def preview(self, paths=None):
        if paths is None:
            paths = [str(self.a), str(self.b)]
        return camera.preview_batch_trash(json.dumps(paths))

    def mock_trash(self):
        gio = patch.object(camera.shutil, "which", return_value="/usr/bin/gio")
        proc = patch.object(camera.subprocess, "run",
                            return_value=Mock(returncode=0))
        gio.start()
        run = proc.start()
        self.addCleanup(gio.stop)
        self.addCleanup(proc.stop)
        return run

    def test_gallery_image_and_video_selection_is_only_previewed(self):
        result = self.preview([str(self.a), str(self.v)])
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["bytes"], 10)
        self.assertEqual(result["expiresSeconds"], camera.PLAN_TTL)
        self.assertEqual(result["sample"], ["First.png", "screen_record.mp4"])
        self.assertTrue(self.a.exists())
        self.assertTrue(self.v.exists())
        planfile = self.planroot / (result["planId"] + ".json")
        self.assertEqual(planfile.stat().st_mode & 0o777, 0o600)
        plan = json.loads(planfile.read_text())
        self.assertEqual(plan["version"], 3)
        self.assertEqual(len(plan["records"]), 2)

    def test_reject_empty_invalid_duplicate_and_overlimit(self):
        for raw in ('[]', '{}', 'not json', '["/a","/a"]'):
            self.assertFalse(camera.preview_batch_trash(raw)["ok"], raw)
        self.assertEqual(self.preview([str(self.a)] * 2)["error"],
                         "INVALID_OR_DUPLICATE_PATH")
        self.assertEqual(camera.preview_batch_trash(
            json.dumps([f"/tmp/{n}.png" for n in range(501)]))["error"],
            "INVALID_SELECTION_SIZE")
        self.assertEqual(camera.preview_batch_trash("x" * 100001)["error"],
                         "SELECTION_TOO_LARGE")

    def test_not_in_gallery_and_symlink_are_not_admitted(self):
        other = self.home / "Documents"
        other.mkdir()
        not_scanned = other / "notes.png"
        not_scanned.write_bytes(b"secret")
        self.assertEqual(self.preview([str(not_scanned)])["error"],
                         "NOT_IN_GALLERY")
        link = self.photos / "linked.png"
        link.symlink_to(self.a)
        self.assertEqual(self.preview([str(link)])["error"], "NOT_IN_GALLERY")
        self.assertTrue(not_scanned.exists())
        self.assertTrue(self.a.exists())

    def test_correct_confirmation_mocked_trash_and_replay_rejection(self):
        plan = self.preview()
        self.assertTrue(plan["ok"], plan)
        run = self.mock_trash()
        self.assertEqual(camera.trash_batch(plan["planId"], "WRONG")["error"],
                         "CONFIRMATION_REQUIRED")
        receipt = camera.trash_batch(plan["planId"], "MOVE_TO_TRASH")
        self.assertEqual((receipt["moved"], receipt["skipped"], receipt["failed"]),
                         (2, 0, 0))
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].args[0],
                         ["/usr/bin/gio", "trash", str(self.a)])
        self.assertFalse((self.planroot / (plan["planId"] + ".json")).exists())
        self.assertEqual(camera.trash_batch(plan["planId"], "MOVE_TO_TRASH")["error"],
                         "PLAN_NOT_FOUND")
        self.assertEqual(run.call_count, 2)

    def test_modified_file_skipped_without_blocking_unchanged_selection(self):
        plan = self.preview()
        self.b.write_bytes(b"this file changed after preview")
        run = self.mock_trash()
        receipt = camera.trash_batch(plan["planId"], "MOVE_TO_TRASH")
        self.assertEqual((receipt["moved"], receipt["skipped"], receipt["failed"]),
                         (1, 1, 0))
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][-1], str(self.a))
        self.assertTrue(self.b.exists())

    def test_expired_plan_cannot_move_anything(self):
        plan = self.preview()
        file = self.planroot / (plan["planId"] + ".json")
        data = json.loads(file.read_text())
        data["createdAt"] = time.time() - camera.PLAN_TTL - 3
        file.write_text(json.dumps(data))
        run = self.mock_trash()
        receipt = camera.trash_batch(plan["planId"], "MOVE_TO_TRASH")
        self.assertEqual(receipt["error"], "PLAN_EXPIRED_OR_INVALID")
        self.assertEqual(run.call_count, 0)

    def test_batch_always_review_first_and_never_direct_file_delete_in_qml(self):
        qml = QML.read_text()
        for snippet in ('property var batchPaths: []',
                        'function batchToggle(record)',
                        'function batchSelectLoaded(nameNeedle)',
                        'function previewBatchTrash()',
                        'function confirmBatchTrash()',
                        '"preview-batch"',
                        '"trash-batch"',
                        'galleryFiles.length',
                        'label: "SELECT LOADED"',
                        'label: "CONFIRM TRASH"'):
            self.assertIn(snippet, qml)
        self.assertIn('batchReviewKey !== JSON.stringify(batchPaths)', qml)
        self.assertIn('batchPreview = null;', qml)
        self.assertNotIn('rm -rf', qml)


if __name__ == "__main__":
    unittest.main()
