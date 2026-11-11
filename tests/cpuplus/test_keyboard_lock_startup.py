"""Isolated Sway startup adapter tests: no real user config or compositor."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
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
        self.root = Path(self.tmp.name)
        self.sway = self.root / "sway"
        self.sway.mkdir()
        self.main = self.sway / "config"
        self.fragment = self.sway / "post-apollo-keyboard-locks.conf"
        self.original = "set $mod Mod4\nbindsym $mod+Return exec foot\n"
        self.main.write_text(self.original, encoding="utf-8")

    def test_explicit_install_persists_independent_locks(self):
        self.assertEqual(helper.inspect(self.root), {"status": "not_installed"})
        result = helper.apply("on", "off", self.root)
        self.assertEqual(result["status"], "installed")
        self.assertEqual(result["activation"], "NEXT_SWAY_START")
        self.assertFalse(result["runtime_changed"])
        self.assertEqual(helper.inspect(self.root), {
            "status": "installed", "num": "on", "caps": "off"})
        fragment = self.fragment.read_text(encoding="utf-8")
        self.assertIn("input type:keyboard xkb_numlock enabled\n", fragment)
        self.assertIn("input type:keyboard xkb_capslock disabled\n", fragment)
        self.assertTrue(self.main.read_text(encoding="utf-8").startswith(self.original))
        self.assertEqual(self.main.read_text().count(helper.START), 1)

    def test_idempotent_apply_and_reversible_modes(self):
        helper.apply("on", "off", self.root)
        once = self.main.read_text()
        helper.apply("on", "off", self.root)
        self.assertEqual(self.main.read_text(), once)
        helper.apply("system", "on", self.root)
        self.assertEqual(helper.inspect(self.root), {
            "status": "installed", "num": "system", "caps": "on"})
        self.assertNotIn("xkb_numlock", self.fragment.read_text())

    def test_invalid_modes_do_not_touch_config(self):
        for mode in ("toggle", "../bad", "", "remember"):
            with self.assertRaises(helper.LockConfigError):
                helper.apply(mode, "on", self.root)
            self.assertEqual(self.main.read_text(), self.original)
            self.assertFalse(self.fragment.exists())

    def test_missing_main_config_refuses_to_create_new_sway_setup(self):
        self.main.unlink()
        with self.assertRaises(helper.LockConfigError):
            helper.apply("on", "off", self.root)
        self.assertFalse(self.fragment.exists())

    def test_unowned_fragment_refused_without_touching_main(self):
        self.fragment.write_text("input type:keyboard xkb_numlock disabled\n")
        with self.assertRaises(helper.LockConfigError):
            helper.apply("on", "on", self.root)
        self.assertEqual(self.main.read_text(), self.original)

    def test_symlink_and_multiple_include_markers_refused(self):
        self.main.unlink()
        other = self.root / "actual"
        other.write_text(self.original)
        self.main.symlink_to(other)
        with self.assertRaises(helper.LockConfigError):
            helper.apply("on", "off", self.root)
        self.assertEqual(other.read_text(), self.original)
        self.main.unlink()
        self.main.write_text(self.original + helper.START + helper.START)
        with self.assertRaises(helper.LockConfigError):
            helper.apply("on", "off", self.root)
        self.assertEqual(self.main.read_text(), self.original + helper.START * 2)

    def test_no_compositor_action_on_apply(self):
        self.assertNotIn("subprocess", HELPER_PATH.read_text())
        self.assertNotIn("swaymsg", HELPER_PATH.read_text())
        self.assertNotIn("os.system", HELPER_PATH.read_text())
        self.assertNotIn("shell=True", HELPER_PATH.read_text())

    def test_cli_status_is_read_only(self):
        self.assertEqual(helper.main(["invalid"]), 2)
        self.assertEqual(helper.inspect(self.root)["status"], "not_installed")
        self.assertEqual(self.main.read_text(), self.original)


if __name__ == "__main__":
    unittest.main()
