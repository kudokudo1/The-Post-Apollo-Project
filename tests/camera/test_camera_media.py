"""Camera M2 offline regression: no hardware, screen recording, or Trash activity."""
import importlib.util
from pathlib import Path
from unittest.mock import patch, Mock
import os
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("camera_m2", ROOT / "scripts/camera/camera_cli.py")
camera = importlib.util.module_from_spec(spec)
spec.loader.exec_module(camera)


class CameraMediaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / "home"
        self.home.mkdir()
        self.patch_home = patch.object(camera, "home", return_value=self.home)
        self.patch_home.start()
        self.addCleanup(self.patch_home.stop)
        self.patch_state = patch.dict(os.environ, {"XDG_STATE_HOME": str(Path(self.tmp.name) / "state")})
        self.patch_state.start()
        self.addCleanup(self.patch_state.stop)

    def add(self, root, filename):
        root.mkdir(parents=True, exist_ok=True)
        path = root / filename
        path.write_bytes(b"fixture")
        return path

    def test_media_filters_and_large_library_are_file_backed(self):
        self.add(camera.pictures(), "Screenshot_A.png")
        self.add(camera.webcam_root(), "webcam_photo.jpg")
        self.add(camera.video_root(), "webcam_2026.mp4")
        self.add(camera.video_root(), "screen_2026.mp4")
        self.add(self.home / "Desktop", "ordinary.jpg")
        counts = {name: camera.gallery(media_filter=name)["total"] for name in
                  ("all", "screenshots", "webcam", "videos", "screen-recordings")}
        self.assertEqual(counts, {"all": 5, "screenshots": 1, "webcam": 2,
                                  "videos": 2, "screen-recordings": 1})
        self.assertEqual(camera.gallery(media_filter="wrong")["error"], "INVALID_FILTER")

    def test_batch_desktop_trash_never_includes_videos(self):
        self.add(self.home / "Desktop", "Screenshot_video.mp4")
        self.add(self.home / "Desktop", "Screenshot_image.png")
        preview = camera.preview_desktop_trash()
        self.assertEqual(preview["count"], 1)
        self.assertEqual(preview["sample"], ["Screenshot_image.png"])

    def test_webcam_fails_closed_without_ffmpeg_or_device(self):
        with patch.object(camera.shutil, "which", return_value=None):
            self.assertEqual(camera.webcam_photo_capture()["error"], "FFMPEG_MISSING")
        with patch.object(camera.shutil, "which", return_value="/usr/bin/ffmpeg"):
            with patch.object(camera, "video_devices", return_value=[]):
                self.assertEqual(camera.webcam_photo_capture()["error"], "NO_WEBCAM_DEVICE")
        self.assertIsNone(camera.camera_device("/tmp/untrusted-camera"))

    def test_webcam_photo_argv_not_shell_and_output_on_disk(self):
        with patch.object(camera.shutil, "which", return_value="/usr/bin/ffmpeg"):
            with patch.object(camera, "camera_device", return_value="/dev/video4"):
                def fake_run(argv, **kwargs):
                    self.assertEqual(argv[0], "/usr/bin/ffmpeg")
                    self.assertEqual(argv[argv.index("-i") + 1], "/dev/video4")
                    self.assertNotIn("shell", kwargs)
                    Path(argv[-1]).write_bytes(b"JPEG")
                    return Mock(returncode=0)
                with patch.object(camera.subprocess, "run", side_effect=fake_run):
                    result = camera.webcam_photo_capture("/dev/video4")
        self.assertTrue(result["ok"])
        self.assertTrue(Path(result["path"]).is_file())

    def test_record_start_is_opt_in_and_no_unrelated_process_kill(self):
        with patch.object(camera.shutil, "which", return_value=None):
            self.assertEqual(camera.record_start_action("screen")["error"], "WF_RECORDER_MISSING")
        with patch.object(camera, "_read_recording", return_value={"pid": 99999, "ticks": "12"}):
            with patch.object(camera, "_pid_start_ticks", return_value="12"):
                with patch.object(camera.subprocess, "Popen") as popen:
                    self.assertEqual(camera.record_start_action("screen")["error"], "ALREADY_RECORDING")
                    popen.assert_not_called()
        with patch.object(camera, "_read_recording", return_value=None):
            with patch.object(camera.os, "kill") as kill:
                self.assertEqual(camera.record_stop_action()["error"], "NOT_RECORDING")
                kill.assert_not_called()


if __name__ == "__main__":
    unittest.main()
