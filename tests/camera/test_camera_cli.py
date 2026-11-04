"""Camera M1 offline tests: no real Wayland, screenshots, Trash or user files."""
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch, Mock
import os

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "scripts/camera/camera_cli.py"
spec = importlib.util.spec_from_file_location("post_apollo_camera", SRC)
camera = importlib.util.module_from_spec(spec)
spec.loader.exec_module(camera)


class CameraOfflineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.home = self.base / "home"
        self.home.mkdir()
        (self.home / "Desktop").mkdir()
        self.home_patch = patch.object(camera, "home", return_value=self.home)
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)
        self.env_patch = patch.dict(os.environ, {"XDG_STATE_HOME": str(self.base / "state")})
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def add_file(self, name, content=b"image", directory=None):
        target = (directory or self.home / "Desktop") / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return target

    def test_gallery_is_read_only_and_includes_desktop_and_camera_images(self):
        desktop_image = self.add_file("20261104_101010_grim.png")
        normal_image = self.add_file("family picture.jpg")
        self.add_file("notes.txt")
        camera_image = self.add_file("post-apollo_focused_test.png",
                                     directory=camera.pictures())
        result = camera.gallery()
        self.assertTrue(result["ok"])
        self.assertEqual(result["total"], 3)
        self.assertEqual(len(result["files"]), 3)
        self.assertEqual(set(r["path"] for r in result["files"]),
                         {str(desktop_image), str(normal_image), str(camera_image)})
        self.assertTrue(desktop_image.exists())
        self.assertTrue(normal_image.exists())
        self.assertTrue(camera_image.exists())

    def test_preview_only_matches_screenshot_named_desktop_images(self):
        screenshot = self.add_file("Screenshot_2026-11-04.png")
        old_grim = self.add_file("20261104_02h22m_grim.png")
        family = self.add_file("family.jpg")
        other = self.add_file("notes.txt")
        result = camera.preview_desktop_trash()
        self.assertTrue(result["ok"])
        self.assertEqual(result["count"], 2)
        self.assertIn("Screenshot_2026-11-04.png", result["sample"])
        self.assertIn("20261104_02h22m_grim.png", result["sample"])
        self.assertTrue(result["planId"])
        self.assertEqual(len(result["planId"]), 32)
        self.assertTrue(screenshot.exists())
        self.assertTrue(old_grim.exists())
        self.assertTrue(family.exists())
        self.assertTrue(other.exists())
        plan = camera.plan_dir() / (result["planId"] + ".json")
        self.assertTrue(plan.is_file())
        self.assertEqual(plan.stat().st_mode & 0o777, 0o600)

    def test_trash_requires_explicit_confirmation_and_uses_gio_only(self):
        photo = self.add_file("Screenshot_test.png")
        family = self.add_file("family.jpg")
        preview = camera.preview_desktop_trash()
        token = preview["planId"]
        with patch.object(camera.shutil, "which", return_value="/usr/bin/gio"):
            with patch.object(camera.subprocess, "run") as run:
                run.return_value.returncode = 0
                self.assertEqual(camera.trash_plan(token, "anything")["error"],
                                 "CONFIRMATION_REQUIRED")
                run.assert_not_called()
                done = camera.trash_plan(token, "MOVE_TO_TRASH")
        self.assertTrue(done["ok"])
        self.assertEqual(done["moved"], 1)
        self.assertTrue(done["recoverable"])
        self.assertEqual(run.call_args.args[0], ["/usr/bin/gio", "trash", str(photo)])
        self.assertTrue(family.exists(), "unmatched family picture must not be touched")
        self.assertFalse((camera.plan_dir() / (token+".json")).exists())
        self.assertFalse(camera.trash_plan(token, "MOVE_TO_TRASH")["ok"],
                         "consumed plan cannot be reused")

    def test_changed_or_removed_image_is_not_trashed(self):
        changed = self.add_file("Screenshot_changed.png")
        removed = self.add_file("Screenshot_missing.png")
        preview = camera.preview_desktop_trash()
        changed.write_bytes(b"a newly changed image")
        removed.unlink()
        with patch.object(camera.shutil, "which", return_value="/usr/bin/gio"):
            with patch.object(camera.subprocess, "run") as run:
                receipt = camera.trash_plan(preview["planId"], "MOVE_TO_TRASH")
        self.assertEqual(receipt["moved"], 0)
        self.assertEqual(receipt["skipped"], 1)
        self.assertEqual(receipt["failed"], 1)
        run.assert_not_called()

    def test_symlinks_are_not_indexed_or_trashed(self):
        outside = self.add_file("keep.png", directory=self.base)
        (self.home / "Desktop" / "Screenshot_fake.png").symlink_to(outside)
        self.assertEqual(camera.gallery()["total"], 0)
        self.assertEqual(camera.preview_desktop_trash()["count"], 0)
        self.assertTrue(outside.exists())

    def test_expired_plan_fails_closed(self):
        self.add_file("Screenshot_old.png")
        receipt = camera.preview_desktop_trash()
        plan_path = camera.plan_dir() / (receipt["planId"] + ".json")
        plan = json.loads(plan_path.read_text())
        plan["createdAt"] = time.time() - camera.PLAN_TTL - 5
        plan_path.write_text(json.dumps(plan))
        with patch.object(camera.shutil, "which", return_value="/usr/bin/gio"):
            with patch.object(camera.subprocess, "run") as run:
                result = camera.trash_plan(receipt["planId"], "MOVE_TO_TRASH")
        self.assertEqual(result["error"], "PLAN_EXPIRED_OR_INVALID")
        run.assert_not_called()

    def test_captures_fail_closed_when_tools_missing(self):
        with patch.object(camera.shutil, "which", return_value=None):
            for mode in ("region", "focused", "all"):
                self.assertEqual(camera.capture(mode)["error"], "GRIM_NOT_INSTALLED")
        self.assertEqual(camera.capture("unknown")["error"], "INVALID_MODE")

    def test_region_capture_validates_cancel_and_uses_shell_free_argv(self):
        def exists(command):
            return "/fake/" + command
        with patch.object(camera.shutil, "which", side_effect=exists):
            with patch.object(camera.subprocess, "run") as runner:
                runner.return_value = Mock(stdout="", returncode=1)
                result = camera.capture("region")
                self.assertEqual(result["error"], "REGION_CANCELLED")
                self.assertEqual(runner.call_args.args[0], ["/fake/slurp"])
                runner.return_value = Mock(stdout="100,100 200x300", returncode=0)
                def simulate(*args, **kwargs):
                    argv = args[0]
                    if argv[0].endswith("slurp"):
                        return Mock(stdout="100,100 200x300", returncode=0)
                    Path(argv[-1]).write_bytes(b"PNG mocked")
                    return Mock(returncode=0)
                runner.side_effect = simulate
                done = camera.capture("region")
                self.assertTrue(done["ok"])
                self.assertEqual(done["mode"], "region")
                self.assertTrue(Path(done["path"]).is_file())
                self.assertEqual(runner.call_args.args[0][1:3],
                                 ["-g", "100,100 200x300"])
                self.assertTrue(done["path"].startswith(str(camera.pictures())))

    def test_focused_capture_selects_sway_focused_output(self):
        with patch.object(camera, "outputs", return_value=[
            {"name": "DP-3", "focused": True},
            {"name": "HDMI-A-1", "focused": False}
        ]):
            with patch.object(camera.shutil, "which", return_value="/fake/grim"):
                with patch.object(camera.subprocess, "run") as run:
                    def fake(argv, **kwargs):
                        self.assertEqual(argv[1:3], ["-o", "DP-3"])
                        Path(argv[-1]).write_bytes(b"PNG")
                        return Mock(returncode=0)
                    run.side_effect = fake
                    self.assertTrue(camera.capture("focused")["ok"])


if __name__ == "__main__":
    unittest.main()
