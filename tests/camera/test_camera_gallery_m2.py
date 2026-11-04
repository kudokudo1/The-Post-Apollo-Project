"""Camera M2 tests: legacy screenshots, paging and selected-file safe Trash.

Every file and plan lives in a disposable TemporaryDirectory. No Quickshell,
Sway, GIO or real user's pictures are touched by these tests.
"""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "camera_m2", ROOT / "scripts/camera/camera_cli.py")
camera = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(camera)


class GalleryM2Tests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.base = Path(self.scratch.name)
        self.user_home = self.base / "person"
        self.user_home.mkdir()
        self.patch_home = patch.object(camera, "home", return_value=self.user_home)
        self.patch_home.start()
        self.addCleanup(self.patch_home.stop)
        self.patch_env = patch.dict(
            os.environ, {"XDG_STATE_HOME": str(self.base / "state")})
        self.patch_env.start()
        self.addCleanup(self.patch_env.stop)

    def image(self, relative, contents=b"test image"):
        path = self.user_home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)
        return path

    def test_five_thousand_old_desktop_screenshots_are_pageable(self):
        # Before M2, the first 150 were all the UI could ever see.
        desktop = self.user_home / "Desktop"
        desktop.mkdir()
        for i in range(5000):
            (desktop / f"Screenshot_legacy_{i:05d}.png").write_bytes(b"x")
        first = camera.gallery()
        self.assertTrue(first["ok"])
        self.assertEqual(first["total"], 5000)
        self.assertEqual(first["shown"], camera.GALLERY_PAGE_SIZE)
        self.assertTrue(first["hasMore"])
        self.assertEqual(first["page"], 0)
        assert camera.GALLERY_PAGE_SIZE < 5000
        last_page = (5000 - 1) // camera.GALLERY_PAGE_SIZE
        last = camera.gallery(last_page)
        self.assertTrue(last["ok"])
        self.assertEqual(last["page"], last_page)
        self.assertFalse(last["hasMore"])
        self.assertGreater(last["shown"], 0)
        self.assertEqual(sum(
            len(camera.gallery(page)["files"])
            for page in range(last_page + 1)), 5000)
        self.assertEqual(len(list(desktop.iterdir())), 5000,
                         "gallery indexing must never move old screenshots")

    def test_legacy_locations_nested_pictures_downloads_and_search(self):
        old = self.image("Pictures/old/screens/2019-02 Screenshot.png")
        older = self.image("Downloads/captures/Screenshot-2018.jpg")
        unrelated = self.image("Pictures/holiday-photo.jpg")
        item = self.image("Desktop/Screenshot-today.webp")
        page = camera.gallery(0)
        self.assertEqual(page["total"], 4)
        self.assertEqual(set(x["path"] for x in page["files"]),
                         {str(old), str(older), str(unrelated), str(item)})
        shots = camera.gallery(0, shots_only=True)
        self.assertEqual(set(x["path"] for x in shots["files"]),
                         {str(old), str(older), str(item)})
        found = camera.gallery(0, "2019-02")
        self.assertEqual(found["total"], 1)
        self.assertEqual(found["files"][0]["path"], str(old))
        self.assertFalse(found["truncated"])

    def test_optional_user_folder_is_read_only_and_rejects_private_paths(self):
        custom = self.image("Archives/old screenshots/capture from 2017.png")
        other = self.image("Archives/old screenshots/summer.jpg")
        extra = str(custom.parent)
        result = camera.gallery(0, extra_folder=extra)
        self.assertEqual(result["total"], 2)
        self.assertEqual(set(x["path"] for x in result["files"]),
                         {str(custom), str(other)})
        self.assertTrue(custom.exists())
        for forbidden in [
            str(self.user_home),
            str(self.base),
            str(self.user_home / ".ssh"),
            str(self.user_home / "Pictures" / ".." / ".config"),
            "../../outside",
        ]:
            bad = camera.gallery(0, extra_folder=forbidden)
            self.assertEqual(bad["error"], "FOLDER_NOT_PERMITTED")

    def test_symlinks_and_hidden_folders_not_scanned(self):
        photo = self.image("External/secret.png")
        desktop = self.user_home / "Desktop"
        desktop.mkdir()
        (desktop / "shortcut.png").symlink_to(photo)
        (desktop / "shortcut-folder").symlink_to(photo.parent)
        hidden = self.image("Pictures/.hidden/secret.jpg")
        visible = self.image("Pictures/screenshot.png")
        result = camera.gallery(0)
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["files"][0]["path"], str(visible))
        self.assertTrue(hidden.exists())
        self.assertTrue(photo.exists())

    def test_selected_delete_requires_preview_and_second_confirmation(self):
        target = self.image("Pictures/old/Screenshot-to-trash.png")
        preview = camera.preview_selected_trash(str(target))
        self.assertTrue(preview["ok"])
        self.assertEqual(preview["name"], target.name)
        self.assertTrue(target.exists())
        plan_path = camera.plan_dir() / (preview["planId"] + ".json")
        self.assertTrue(plan_path.exists())
        self.assertEqual(plan_path.stat().st_mode & 0o777, 0o600)
        with patch.object(camera.shutil, "which", return_value="/usr/bin/gio"):
            with patch.object(camera.subprocess, "run") as run:
                run.return_value = Mock(returncode=0)
                self.assertEqual(
                    camera.trash_selected(preview["planId"], "CANCEL")["error"],
                    "CONFIRMATION_REQUIRED")
                run.assert_not_called()
                done = camera.trash_selected(
                    preview["planId"], "MOVE_TO_TRASH")
        self.assertTrue(done["ok"])
        self.assertTrue(done["recoverable"])
        self.assertEqual(run.call_args.args[0],
                         ["/usr/bin/gio", "trash", str(target)])
        self.assertFalse(plan_path.exists(), "used confirmation cannot be replayed")

    def test_changed_file_or_symlink_after_preview_is_rejected(self):
        picture = self.image("Desktop/Screenshot-changed.png", b"original")
        preview = camera.preview_selected_trash(str(picture))
        picture.write_bytes(b"new contents")
        with patch.object(camera.shutil, "which", return_value="/usr/bin/gio"):
            with patch.object(camera.subprocess, "run") as run:
                receipt = camera.trash_selected(
                    preview["planId"], "MOVE_TO_TRASH")
        self.assertEqual(receipt["error"], "FILE_CHANGED")
        run.assert_not_called()
        link_target = self.image("Pictures/another.png")
        picture.unlink()
        picture.symlink_to(link_target)
        with patch.object(camera.shutil, "which", return_value="/usr/bin/gio"):
            with patch.object(camera.subprocess, "run") as run:
                receipt = camera.trash_selected(
                    preview["planId"], "MOVE_TO_TRASH")
        self.assertEqual(receipt["error"], "FILE_CHANGED")
        run.assert_not_called()
        self.assertTrue(link_target.exists())

    def test_reject_external_private_and_nonimage_delete_requests(self):
        outside = self.base / "outside.png"
        outside.write_bytes(b"keep")
        hidden = self.image(".config/private.png")
        note = self.image("Pictures/notes.txt")
        for target in [outside, hidden, note]:
            preview = camera.preview_selected_trash(str(target))
            self.assertFalse(preview["ok"])
            self.assertTrue(target.exists())
        direct = camera.trash_selected("not-token", "MOVE_TO_TRASH")
        self.assertEqual(direct["error"], "CONFIRMATION_REQUIRED")

    def test_selected_plan_expires_and_failed_gio_reports_error(self):
        picture = self.image("Downloads/Screenshot-expired.jpg")
        preview = camera.preview_selected_trash(str(picture))
        plan_file = camera.plan_dir() / (preview["planId"] + ".json")
        plan = json.loads(plan_file.read_text())
        plan["createdAt"] = time.time() - camera.PLAN_TTL - 2
        plan_file.write_text(json.dumps(plan))
        with patch.object(camera.shutil, "which", return_value="/usr/bin/gio"):
            with patch.object(camera.subprocess, "run") as run:
                result = camera.trash_selected(
                    preview["planId"], "MOVE_TO_TRASH")
        self.assertEqual(result["error"], "PLAN_EXPIRED_OR_INVALID")
        run.assert_not_called()
        preview = camera.preview_selected_trash(str(picture))
        with patch.object(camera.shutil, "which", return_value="/usr/bin/gio"):
            with patch.object(camera.subprocess, "run") as run:
                run.return_value = Mock(returncode=1)
                result = camera.trash_selected(
                    preview["planId"], "MOVE_TO_TRASH")
        self.assertEqual(result["error"], "TRASH_FAILED")
        self.assertTrue(picture.exists())

    def test_old_desktop_bulk_cleanup_remains_independent(self):
        old = self.image("Desktop/Screenshot-legacy.png")
        innocent = self.image("Desktop/family.jpg")
        preview = camera.preview_desktop_trash()
        self.assertEqual(preview["count"], 1)
        self.assertTrue(old.exists())
        self.assertTrue(innocent.exists())


if __name__ == "__main__":
    unittest.main()
