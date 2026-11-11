"""Isolated keyboard startup tests: source-controlled Sway symlinks stay intact."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import stat
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HELPER_PATH = ROOT / "services/input/SwayKeyboardStartup.py"
spec = importlib.util.spec_from_file_location("SwayKeyboardStartup", HELPER_PATH)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class SwayLockStartup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.config_home = self.home / ".config"
        self.sway = self.config_home / "sway"
        self.sway.mkdir(parents=True)
        self.main = self.sway / "config"
        self.fragment = self.sway / "post-apollo-keyboard-locks.conf"
        self.original = (
            "set $mod Mod4\n"
            "exec_always sh -c 'pkill -x quickshell; quickshell &'\n"
            + helper.APPROVED_INCLUDE + "\n"
        )
        self.source_dir = self.home / "Projects/Post-Apollo-Sway-Config"
        self.source_dir.mkdir(parents=True)
        self.source = self.source_dir / "config"
        self.source.write_text(self.original, encoding="utf-8")
        self.main.symlink_to(self.source)

    def assert_source_unchanged(self):
        self.assertTrue(self.main.is_symlink())
        self.assertEqual(self.main.resolve(), self.source.resolve())
        self.assertEqual(self.source.read_text(encoding="utf-8"), self.original)

    def test_symlinked_source_config_can_install_separate_fragment(self):
        self.assertEqual(helper.inspect(self.config_home)["status"], "not_installed")
        result = helper.apply("on", "off", self.config_home)
        self.assertEqual(result, {
            "status": "installed", "num": "on", "caps": "off",
            "activation": "NEXT_SWAY_START", "runtime_changed": False
        })
        self.assert_source_unchanged()
        self.assertEqual(helper.inspect(self.config_home), {
            "status": "installed", "num": "on", "caps": "off"})
        fragment = self.fragment.read_text(encoding="utf-8")
        self.assertIn("input type:keyboard xkb_numlock enabled\n", fragment)
        self.assertIn("input type:keyboard xkb_capslock disabled\n", fragment)
        self.assertEqual(stat.S_IMODE(self.fragment.stat().st_mode), 0o600)

    def test_idempotence_and_system_mode(self):
        helper.apply("on", "off", self.config_home)
        first = self.fragment.read_text()
        helper.apply("on", "off", self.config_home)
        self.assertEqual(self.fragment.read_text(), first)
        helper.apply("system", "on", self.config_home)
        self.assertNotIn("xkb_numlock", self.fragment.read_text())
        self.assertEqual(helper.inspect(self.config_home), {
            "status": "installed", "num": "system", "caps": "on"})
        self.assert_source_unchanged()

    def test_regular_config_is_read_only_too(self):
        self.main.unlink()
        self.main.write_text(self.original, encoding="utf-8")
        helper.apply("on", "off", self.config_home)
        self.assertEqual(self.main.read_text(), self.original)
        self.assertFalse(self.main.is_symlink())

    def test_missing_include_blocks_writes_until_sway_repo_is_updated(self):
        self.original = "set $mod Mod4\n"
        self.source.write_text(self.original)
        result = helper.inspect(self.config_home)
        self.assertEqual(result["status"], "not_installed")
        self.assertEqual(result["reason"], "CONFIG_INCLUDE_MISSING")
        with self.assertRaisesRegex(helper.LockConfigError, "CONFIG_INCLUDE_MISSING"):
            helper.apply("on", "off", self.config_home)
        self.assertFalse(self.fragment.exists())
        self.assert_source_unchanged()

    def test_duplicate_include_and_legacy_conflict(self):
        self.original += helper.APPROVED_INCLUDE + "\n"
        self.source.write_text(self.original)
        with self.assertRaisesRegex(helper.LockConfigError, "CONFLICTING_INCLUDE"):
            helper.apply("on", "off", self.config_home)
        self.assertFalse(self.fragment.exists())
        self.assert_source_unchanged()

    def test_symlink_outside_home_is_rejected(self):
        self.main.unlink()
        outside = self.home.parent / (self.home.name + "-foreign-config")
        self.addCleanup(outside.unlink, missing_ok=True)
        outside.write_text(self.original)
        self.main.symlink_to(outside)
        with self.assertRaisesRegex(helper.LockConfigError, "UNSAFE_SYMLINK_TARGET"):
            helper.apply("on", "off", self.config_home)
        self.assertFalse(self.fragment.exists())
        self.assertEqual(outside.read_text(), self.original)

    def test_unowned_or_symlink_fragment_is_refused(self):
        self.fragment.write_text("input type:keyboard xkb_numlock disabled\n")
        with self.assertRaisesRegex(helper.LockConfigError, "UNOWNED_FRAGMENT"):
            helper.apply("on", "on", self.config_home)
        self.fragment.unlink()
        self.fragment.symlink_to(self.source)
        with self.assertRaisesRegex(helper.LockConfigError, "UNSAFE_CONFIG_FILE"):
            helper.apply("on", "on", self.config_home)
        self.assert_source_unchanged()

    def test_invalid_modes_never_write(self):
        for mode in ("toggle", "../bad", "", "remember"):
            with self.assertRaises(helper.LockConfigError):
                helper.apply(mode, "on", self.config_home)
            self.assertFalse(self.fragment.exists())
        self.assert_source_unchanged()

    def test_missing_main_config_refuses(self):
        self.main.unlink()
        with self.assertRaises(helper.LockConfigError):
            helper.apply("on", "off", self.config_home)
        self.assertFalse(self.fragment.exists())
        self.assertEqual(self.source.read_text(), self.original)

    def test_legacy_managed_include_is_read_without_migration_write(self):
        self.original = helper.include_block(self.fragment)
        self.source.write_text(self.original)
        helper.apply("off", "system", self.config_home)
        self.assertEqual(helper.inspect(self.config_home), {
            "status": "installed", "num": "off", "caps": "system"})
        self.assert_source_unchanged()

    def test_no_config_or_compositor_write_path(self):
        code = HELPER_PATH.read_text()
        for forbidden in ("subprocess", "swaymsg", "os.system", "shell=True",
                          "atomic_write(config,", "atomic_write(target,"):
            self.assertNotIn(forbidden, code)
        self.assertIn("atomic_write(fragment,", code)
        self.assertIn("read_config_without_writes", code)
        self.assertEqual(helper.main(["invalid"]), 2)


if __name__ == "__main__":
    unittest.main()
