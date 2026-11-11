"""Isolated config.kdl fixtures for explicitly authorized Zellij scroll options."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "services/input/ZellijScrollConfig.py"
spec = importlib.util.spec_from_file_location("ZellijScrollConfig", SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class ZellijScrollConfigTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.home = Path(temp.name)
        self.config_dir = self.home / ".config" / "zellij"
        self.config_dir.mkdir(parents=True)
        self.config = self.config_dir / "config.kdl"
        self.backup = self.config_dir / "config.kdl.post-apollo-scroll-v1.bak"
        self.original = (
            '// mouse_mode false\n'
            'theme "default"\n'
            'keybinds {\n'
            '    scroll {\n'
            '        bind "j" { ScrollDown; }\n'
            '    }\n'
            '}\n'
        )
        self.config.write_text(self.original)

    def observe(self):
        return helper.status(self.home, self.config)

    def install(self, mouse="true", resize="true", sync="true",
                buffer="10000", expected=None):
        old = self.observe()
        return helper.apply(
            expected if expected is not None else old["revision"],
            mouse, resize, sync, buffer, self.home, self.config
        )

    def test_status_only_reads_and_never_creates_backup(self):
        for _ in range(3):
            out = self.observe()
            self.assertEqual(out["status"], "available")
            self.assertFalse(out["runtime_verified"])
            self.assertEqual(out["scope"], "zellij_config_only")
        self.assertEqual(self.config.read_text(), self.original)
        self.assertFalse(self.backup.exists())

    def test_enroll_backup_then_update_only_managed_lines(self):
        first = self.install("true", "false", "true", "10000")
        self.assertEqual(first["status"], "saved")
        self.assertFalse(first["runtime_verified"])
        self.assertEqual(self.backup.read_text(), self.original)
        content = self.config.read_text()
        self.assertTrue(content.startswith(self.original))
        self.assertEqual(content.count(helper.START), 1)
        self.assertEqual(content.count(helper.END), 1)
        out = self.observe()
        self.assertEqual(out["status"], "managed")
        self.assertEqual(out["mouse"], "true")
        self.assertEqual(out["resize"], "false")
        self.assertEqual(out["buffer"], 10000)
        self.assertEqual(out["revision"], first["revision"])
        second = self.install("false", "false", "false", "20000")
        self.assertEqual(second["buffer"], 20000)
        self.assertTrue(self.config.read_text().startswith(self.original))
        self.assertEqual(self.backup.read_text(), self.original)
        self.assertEqual(self.config.read_text().count(helper.START), 1)

    def test_repeated_same_settings_no_duplicate_block(self):
        self.install()
        original_fragment = self.config.read_text()
        same = self.install()
        self.assertEqual(same["status"], "saved")
        self.assertEqual(self.config.read_text(), original_fragment)

    def test_stale_revision_refused_without_write(self):
        old = self.observe()["revision"]
        self.config.write_text(self.original + "// edited concurrently\n")
        with self.assertRaisesRegex(helper.ZellijScrollError, "STALE_CONFIG"):
            self.install(expected=old)
        self.assertFalse(self.backup.exists())
        self.assertEqual(self.config.read_text(),
                         self.original + "// edited concurrently\n")

    def test_existing_option_conflict_refuses_without_write(self):
        for line in ('mouse_mode false\n', 'scroll_buffer_size 20000\n',
                     'mouse_scroll_resize false\n', 'scroll_mode_sync false\n'):
            self.config.write_text(self.original + line)
            with self.assertRaisesRegex(helper.ZellijScrollError,
                                        "EXTERNAL_SCROLL_OPTIONS"):
                self.observe()
            with self.assertRaises(helper.ZellijScrollError):
                helper.apply("0" * 64, "true", "true", "true", "10000",
                             self.home, self.config)
            self.assertFalse(self.backup.exists())
        self.config.write_text(self.original)

    def test_unowned_or_duplicate_markers_are_refused(self):
        self.install()
        text = self.config.read_text()
        edited = text.replace("mouse_scroll_resize true",
                              "mouse_scroll_resize maybe")
        self.config.write_text(edited)
        with self.assertRaisesRegex(helper.ZellijScrollError, "ALTERED_BLOCK"):
            self.observe()
        self.config.write_text(text + helper.START + "\n")
        with self.assertRaisesRegex(helper.ZellijScrollError, "DUPLICATE_MARKER"):
            self.observe()

    def test_symlinked_config_is_never_replaced(self):
        repo = self.home / "Projects" / "ZellijConfig"
        repo.mkdir(parents=True)
        target = repo / "config.kdl"
        target.write_text(self.original)
        self.config.unlink()
        self.config.symlink_to(target)
        with self.assertRaisesRegex(helper.ZellijScrollError, "UNSAFE_CONFIG"):
            self.observe()
        self.assertTrue(self.config.is_symlink())
        self.assertEqual(target.read_text(), self.original)
        self.assertFalse(self.backup.exists())

    def test_missing_config_is_never_created_automatically(self):
        self.config.unlink()
        with self.assertRaisesRegex(helper.ZellijScrollError, "CONFIG_MISSING"):
            self.observe()
        self.assertFalse(self.config.exists())
        self.assertFalse(self.backup.exists())

    def test_backup_collision_refuses_before_first_write(self):
        self.backup.write_text("keep me\n")
        with self.assertRaisesRegex(helper.ZellijScrollError,
                                    "BACKUP_ALREADY_EXISTS"):
            self.install()
        self.assertEqual(self.config.read_text(), self.original)
        self.assertEqual(self.backup.read_text(), "keep me\n")

    def test_reject_unknown_values_and_fake_scroll_speed(self):
        for values in (
            ("yes", "true", "true", "10000"),
            ("true", "on", "true", "10000"),
            ("true", "true", "1", "10000"),
            ("true", "true", "true", "0"),
            ("true", "true", "true", "500000"),
            ("true", "true", "true", "10000;reload"),
        ):
            with self.assertRaises(helper.ZellijScrollError):
                self.install(*values)
        self.assertEqual(self.config.read_text(), self.original)
        self.assertFalse(self.backup.exists())
        text = SOURCE.read_text()
        self.assertNotIn("wheel_scroll_multiplier", text)
        self.assertNotIn("mouse_scroll_speed", text)
        for forbidden in ("subprocess", "pkexec", "swaymsg", "os.system"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
