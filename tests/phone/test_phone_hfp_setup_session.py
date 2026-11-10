"""Guided HFP setup: no implicit service, audio, pairing or permission changes."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase, mock
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
import PhoneHfpSetupSession as hfp


class Host:
    def __init__(self, *, service="active", bus=True, wp=True):
        self.service = service
        self.bus = bus
        self.wp = wp
        self.commands = []

    def __call__(self, argv, **kwargs):
        self.commands.append(tuple(argv))
        if argv == ["wireplumber", "--version"]:
            return self.reply(0, "wireplumber\nCompiled with libwireplumber 0.5.19\n")
        if argv[:3] == ["systemctl", "show", "ofono.service"]:
            return self.reply(0, f"LoadState=loaded\nActiveState={self.service}\n")
        if argv == ["systemctl", "--user", "is-active", "wireplumber.service"]:
            return self.reply(0 if self.wp else 3, "active" if self.wp else "inactive")
        if argv[0:3] == ["busctl", "--system", "call"]:
            return self.reply(0 if self.bus else 1, "")
        if argv == ["/usr/bin/sudo", "/usr/bin/systemctl", "start", "ofono.service"]:
            self.service = "active"
            return self.reply(0, "")
        if argv == ["systemctl", "--user", "restart", "wireplumber.service"]:
            return self.reply(0, "")
        raise AssertionError(f"Unexpected external command: {argv!r}")

    @staticmethod
    def reply(code, output):
        return SimpleNamespace(returncode=code, stdout=output)

    @property
    def writes(self):
        return [c for c in self.commands
                if (c[:2] == ("/usr/bin/sudo", "/usr/bin/systemctl")
                    or c[:3] == ("systemctl", "--user", "restart"))]


class GuidedHfpTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.target = self.home / ".config/wireplumber/wireplumber.conf.d" / hfp.CONFIG_NAME

    def run_setup(self, host=None, answers=(), **kwargs):
        host = host or Host()
        prompt = mock.Mock(side_effect=list(answers))
        with mock.patch("builtins.print"):
            result = hfp.run_session(
                interactive=lambda: True, runner=host, approve=prompt,
                home=self.home, system_roots=(), sudo="/usr/bin/sudo",
                review=lambda: None, **kwargs)
        return result, host, prompt

    def test_requires_exact_cli_and_real_tty(self):
        self.assertEqual(hfp.main([]), 2)
        with mock.patch("builtins.print"):
            self.assertEqual(hfp.run_session(interactive=lambda: False), 3)
        self.assertFalse(self.target.exists())

    def test_does_not_change_anything_without_confirmation(self):
        host = Host(service="inactive")
        code, host, prompt = self.run_setup(host, answers=["CANCEL"])
        self.assertEqual(code, 1)
        self.assertFalse(self.target.exists())
        self.assertEqual(host.writes, [])
        self.assertEqual(prompt.call_count, 1)

    def test_no_automatic_dbus_privilege_widening(self):
        code, host, prompt = self.run_setup(Host(bus=False))
        self.assertEqual(code, 2)
        self.assertEqual(host.writes, [])
        self.assertFalse(self.target.exists())
        prompt.assert_not_called()

    def test_fails_closed_when_wireplumber_is_down(self):
        host = Host(wp=False)
        code, host, prompt = self.run_setup(host)
        self.assertEqual(code, 2)
        self.assertEqual(host.writes, [])
        prompt.assert_not_called()

    def test_native_hfp_configuration_is_never_overwritten(self):
        self.target.parent.mkdir(parents=True)
        old = 'monitor.bluez.properties = { bluez5.hfphsp-backend = "native" }\n'
        self.target.write_text(old)
        code, host, prompt = self.run_setup()
        self.assertEqual(code, 2)
        self.assertEqual(self.target.read_text(), old)
        self.assertEqual(host.writes, [])
        prompt.assert_not_called()

    def test_unrelated_system_override_is_not_silently_replaced(self):
        system_dir = self.home / "system"
        system_dir.mkdir()
        (system_dir / "88-hfp.conf").write_text(
            'monitor.bluez.properties = { bluez5.hfphsp-backend = "native" }\n')
        host = Host()
        with mock.patch("builtins.print"):
            outcome = hfp.run_session(
                interactive=lambda: True, runner=host,
                approve=mock.Mock(side_effect=AssertionError("no consent")),
                home=self.home, system_roots=(system_dir,), review=lambda: None)
        self.assertEqual(outcome, 2)
        self.assertFalse(self.target.exists())
        self.assertEqual(host.writes, [])

    def test_if_already_configured_nothing_gets_restarted(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_text(hfp.CONFIG_TEXT)
        code, host, prompt = self.run_setup()
        self.assertEqual(code, 0)
        self.assertEqual(host.writes, [])
        prompt.assert_not_called()

    def test_restart_refusal_rolls_back_newly_created_file(self):
        code, host, prompt = self.run_setup(
            answers=[hfp.ACK_CONFIG, "NO RESTART"])
        self.assertEqual(code, 1)
        self.assertFalse(self.target.exists())
        self.assertEqual(host.writes, [])
        self.assertEqual(prompt.call_count, 2)

    def test_configure_restarts_only_after_both_confirmations(self):
        code, host, prompt = self.run_setup(
            answers=[hfp.ACK_CONFIG, hfp.ACK_RESTART])
        self.assertEqual(code, 0)
        self.assertEqual(self.target.read_text(), hfp.CONFIG_TEXT)
        self.assertEqual(host.writes, [
            ("systemctl", "--user", "restart", "wireplumber.service")
        ])
        self.assertEqual(prompt.call_count, 2)

    def test_inactive_service_requires_distinct_third_confirmation(self):
        code, host, prompt = self.run_setup(
            Host(service="inactive"),
            answers=[hfp.ACK_START, hfp.ACK_CONFIG, hfp.ACK_RESTART])
        self.assertEqual(code, 0)
        self.assertEqual(host.service, "active")
        self.assertEqual(host.writes, [
            ("/usr/bin/sudo", "/usr/bin/systemctl", "start", "ofono.service"),
            ("systemctl", "--user", "restart", "wireplumber.service")
        ])
        self.assertEqual(prompt.call_count, 3)

    def test_symlink_is_not_followed_or_removed(self):
        other = self.home / "outside.conf"
        other.write_text("KEEP\n")
        self.target.parent.mkdir(parents=True)
        self.target.symlink_to(other)
        code, host, prompt = self.run_setup()
        self.assertEqual(code, 2)
        self.assertEqual(other.read_text(), "KEEP\n")
        self.assertTrue(self.target.is_symlink())
        self.assertEqual(host.writes, [])
        prompt.assert_not_called()

    def test_version_guard_prevents_legacy_wireplumber_changes(self):
        host = Host()
        base = host.__call__

        def old_version(argv, **kwargs):
            if argv == ["wireplumber", "--version"]:
                return Host.reply(0, "Compiled with libwireplumber 0.4.19")
            return base(argv, **kwargs)

        with mock.patch("builtins.print"):
            result = hfp.run_session(
                interactive=lambda: True, runner=old_version, home=self.home,
                system_roots=(), approve=mock.Mock(
                    side_effect=AssertionError("unexpected prompt")))
        self.assertEqual(result, 2)
        self.assertFalse(self.target.exists())
        self.assertEqual(host.writes, [])


if __name__ == "__main__":
    import unittest
    unittest.main()
