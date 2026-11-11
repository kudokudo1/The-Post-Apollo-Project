"""Opt-in Remember mode: isolated Sway fragment sync, no compositor writes."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HELPER_PATH = ROOT / "services/input/SwayKeyboardStartup.py"
spec = importlib.util.spec_from_file_location("KeyboardStartup", HELPER_PATH)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class RememberStartupPolicy(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.config_home = self.home / ".config"
        self.sway = self.config_home / "sway"
        self.sway.mkdir(parents=True)
        self.repo = self.home / "Projects" / "Post-Apollo-Sway-Config"
        self.repo.mkdir(parents=True)
        self.source = self.repo / "config"
        self.original = "set $mod Mod4\n" + helper.APPROVED_INCLUDE + "\n"
        self.source.write_text(self.original, encoding="utf-8")
        self.active_config = self.sway / "config"
        self.active_config.symlink_to(self.source)
        self.fragment = self.sway / "post-apollo-keyboard-locks.conf"

    def test_remember_num_arm_then_transition(self):
        installed = helper.apply_policy(
            "remember", "off", "on", "unknown", self.config_home)
        self.assertTrue(installed["remember_num"])
        self.assertFalse(installed["remember_caps"])
        self.assertEqual(installed["num"], "on")
        self.assertEqual(helper.inspect(self.config_home)["num"], "on")
        updated = helper.sync_remember("num", "off", "on", self.config_home)
        self.assertEqual(updated["num"], "off")
        self.assertEqual(updated["caps"], "off")
        self.assertTrue(updated["remember_num"])
        self.assertEqual(helper.inspect(self.config_home)["num"], "off")
        self.assertTrue(self.active_config.is_symlink())
        self.assertEqual(self.source.read_text(), self.original)

    def test_both_locks_remembered_and_independent(self):
        helper.apply_policy("remember", "remember", "off", "on",
                            self.config_home)
        helper.sync_remember("num", "on", "off", self.config_home)
        helper.sync_remember("caps", "off", "on", self.config_home)
        state = helper.inspect(self.config_home)
        self.assertEqual((state["num"], state["caps"]), ("on", "off"))
        self.assertTrue(state["remember_num"])
        self.assertTrue(state["remember_caps"])

    def test_absent_observation_never_arms(self):
        for x, y, saved_num, saved_caps in [
            ("remember", "off", "unknown", "off"),
            ("off", "remember", "on", "unknown"),
            ("remember", "remember", "on", "")
        ]:
            with self.assertRaises(helper.LockConfigError):
                helper.apply_policy(x, y, saved_num, saved_caps,
                                    self.config_home)
            self.assertFalse(self.fragment.exists())
        self.assertEqual(self.source.read_text(), self.original)

    def test_unarmed_sync_refused_without_writes(self):
        helper.apply("on", "off", self.config_home)
        previous = self.fragment.read_text()
        with self.assertRaisesRegex(helper.LockConfigError,
                                    "REMEMBER_NOT_AUTHORIZED"):
            helper.sync_remember("num", "off", "on", self.config_home)
        self.assertEqual(self.fragment.read_text(), previous)

    def test_static_lock_stays_unarmed(self):
        helper.apply_policy("remember", "off", "on", "off", self.config_home)
        previous = self.fragment.read_text()
        with self.assertRaisesRegex(helper.LockConfigError,
                                    "REMEMBER_NOT_AUTHORIZED"):
            helper.sync_remember("caps", "on", "off", self.config_home)
        self.assertEqual(self.fragment.read_text(), previous)

    def test_compare_and_swap_stale_denied(self):
        helper.apply_policy("remember", "remember", "on", "off",
                            self.config_home)
        helper.sync_remember("num", "off", "on", self.config_home)
        previous = self.fragment.read_text()
        with self.assertRaisesRegex(helper.LockConfigError, "STALE_FRAGMENT"):
            helper.sync_remember("num", "on", "on", self.config_home)
        self.assertEqual(self.fragment.read_text(), previous)

    def test_explicit_policy_change_disarms_remember(self):
        helper.apply_policy("remember", "remember", "on", "off",
                            self.config_home)
        helper.apply_policy("on", "off", "unknown", "unknown",
                            self.config_home)
        self.assertNotIn("remember_num", helper.inspect(self.config_home))
        with self.assertRaisesRegex(helper.LockConfigError,
                                    "REMEMBER_NOT_AUTHORIZED"):
            helper.sync_remember("num", "off", "on", self.config_home)

    def test_modified_marker_is_unowned(self):
        helper.apply_policy("remember", "off", "on", "off", self.config_home)
        modified = self.fragment.read_text().replace(
            "# Remember Num Lock: 1", "# Remember Num Lock: yes")
        self.fragment.write_text(modified)
        with self.assertRaisesRegex(helper.LockConfigError,
                                    "MODIFIED_FRAGMENT"):
            helper.sync_remember("num", "off", "on", self.config_home)
        self.assertEqual(self.fragment.read_text(), modified)

    def test_missing_include_blocks_automatic_follow(self):
        helper.apply_policy("remember", "off", "on", "off", self.config_home)
        self.source.write_text("set $mod Mod4\n")
        previous = self.fragment.read_text()
        with self.assertRaisesRegex(helper.LockConfigError,
                                    "REMEMBER_NOT_AUTHORIZED"):
            helper.sync_remember("num", "off", "on", self.config_home)
        self.assertEqual(self.fragment.read_text(), previous)

    def test_no_compositor_reload_or_config_overwrite(self):
        s = HELPER_PATH.read_text()
        self.assertNotIn("subprocess", s)
        self.assertNotIn("swaymsg", s)
        self.assertNotIn("atomic_write(config,", s)
        self.assertNotIn("os.system", s)
        self.assertIn("atomic_write(fragment,", s)


if __name__ == "__main__":
    unittest.main()
