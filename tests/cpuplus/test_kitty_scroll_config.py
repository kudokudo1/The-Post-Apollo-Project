"""Isolated Kitty scroll configuration: user settings, symlinks and failures."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import stat
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "services/input/KittyScrollConfig.py"
spec = importlib.util.spec_from_file_location("KittyScrollConfig", SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class KittyScrollTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.config_dir = self.home / ".config" / "kitty"
        self.config_dir.mkdir(parents=True)
        self.kitty = self.config_dir / "kitty.conf"
        self.fragment = self.config_dir / "post-apollo-scroll.conf"
        self.backup = self.config_dir / "kitty.conf.post-apollo-before-scroll-v1.bak"
        self.original = ("font_size 15.0\n"
                         "cursor_shape block\n"
                         "background #111111\n")
        self.kitty.write_text(self.original)

    def test_status_and_staging_do_not_write_anything(self):
        self.assertEqual(helper.status(self.home, self.config_dir)["status"],
                         "needs_include")
        self.assertEqual(helper.status(self.home, self.config_dir)["status"],
                         "needs_include")
        self.assertEqual(self.kitty.read_text(), self.original)
        self.assertFalse(self.backup.exists())
        self.assertFalse(self.fragment.exists())

    def test_enroll_preserves_config_with_one_include_and_backup(self):
        out = helper.enroll("8.00", "2.00", self.home, self.config_dir)
        self.assertEqual(out["status"], "enrolled")
        self.assertEqual(self.backup.read_text(), self.original)
        self.assertTrue(self.kitty.read_text().startswith(self.original))
        self.assertEqual(self.kitty.read_text().count(
            helper.include_line(self.fragment)), 1)
        state = helper.status(self.home, self.config_dir)
        self.assertEqual(state["status"], "installed")
        self.assertEqual(state["wheel"], 8.0)
        self.assertEqual(state["touch"], 2.0)
        self.assertEqual(stat.S_IMODE(self.fragment.stat().st_mode), 0o600)
        self.assertFalse(state.get("runtime_verified", False))

    def test_apply_updates_only_owned_fragment(self):
        helper.enroll("5", "1", self.home, self.config_dir)
        original_config = self.kitty.read_text()
        original_backup = self.backup.read_text()
        out = helper.apply("12", "1.50", self.home, self.config_dir)
        self.assertEqual(out["status"], "saved")
        self.assertFalse(out["runtime_verified"])
        self.assertEqual(self.kitty.read_text(), original_config)
        self.assertEqual(self.backup.read_text(), original_backup)
        self.assertEqual(helper.status(self.home, self.config_dir)["wheel"],12.0)

    def test_unenrolled_apply_is_refused(self):
        with self.assertRaisesRegex(helper.KittyConfigError, "INCLUDE_MISSING"):
            helper.apply("9", "2", self.home, self.config_dir)
        self.assertFalse(self.fragment.exists())
        self.assertEqual(self.kitty.read_text(), self.original)

    def test_unowned_fragment_refused_without_altering_it(self):
        self.fragment.write_text("font_size 100\n")
        with self.assertRaisesRegex(helper.KittyConfigError,"UNOWNED_FRAGMENT"):
            helper.enroll("8", "2", self.home, self.config_dir)
        self.assertFalse(self.backup.exists())
        self.assertEqual(self.kitty.read_text(),self.original)
        self.assertEqual(self.fragment.read_text(),"font_size 100\n")

    def test_invalid_values_never_write(self):
        for wheel,touch in [("nan","1"),("-1","1"),("0","1"),
                            ("17","1"),("5","0.01"),("5","9"),
                            ("5;reload","1"),("5","inf"),
                            ("1.12345","2")]:
            with self.assertRaises(helper.KittyConfigError):
                helper.enroll(wheel,touch,self.home,self.config_dir)
            self.assertEqual(self.kitty.read_text(),self.original)
            self.assertFalse(self.backup.exists())
            self.assertFalse(self.fragment.exists())

    def test_duplicate_include_blocks_without_writes(self):
        line=helper.include_line(self.fragment)
        self.kitty.write_text(line+"\n"+line+"\n")
        with self.assertRaisesRegex(helper.KittyConfigError,
                                    "CONFLICTING_INCLUDE"):
            helper.enroll("5","1",self.home,self.config_dir)
        self.assertFalse(self.fragment.exists())

    def test_symlink_is_inspectable_but_not_overwritten(self):
        repo=self.home/"Projects"/"Kitty-Config"
        repo.mkdir(parents=True)
        target=repo/"kitty.conf"
        target.write_text(self.original)
        self.kitty.unlink()
        self.kitty.symlink_to(target)
        self.assertEqual(helper.status(self.home,self.config_dir)["status"],
                         "needs_include")
        with self.assertRaisesRegex(helper.KittyConfigError,
                                    "SYMLINK_CONFIG_MANUAL_INCLUDE"):
            helper.enroll("5","1",self.home,self.config_dir)
        self.assertTrue(self.kitty.is_symlink())
        self.assertEqual(target.read_text(),self.original)
        target.write_text(self.original+"\n"+helper.include_line(self.fragment)+"\n")
        self.assertEqual(helper.apply("8","2",self.home,self.config_dir)
                         ["status"],"saved")
        self.assertTrue(self.kitty.is_symlink())
        self.assertTrue(target.read_text().startswith(self.original))

    def test_outside_home_symlink_refused(self):
        outside=self.home.parent/(self.home.name+"-kitty-outside")
        self.addCleanup(outside.unlink,missing_ok=True)
        outside.write_text(self.original)
        self.kitty.unlink()
        self.kitty.symlink_to(outside)
        with self.assertRaisesRegex(helper.KittyConfigError,
                                    "UNSAFE_CONFIG_SYMLINK"):
            helper.status(self.home,self.config_dir)
        self.assertFalse(self.fragment.exists())

    def test_no_kitty_process_or_zellij_config_change(self):
        source=SOURCE.read_text()
        for forbidden in ("subprocess", "swaymsg", "kitty @", "SIGUSR1",
                          "zellij", "os.system", "shell=True", "pkexec"):
            self.assertNotIn(forbidden,source)
        self.assertEqual(helper.main(["invalid"]),2)


if __name__=="__main__":
    unittest.main()
