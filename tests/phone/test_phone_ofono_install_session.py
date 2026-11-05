"""oFono's embedded PackageKit session never runs without an interactive opt-in."""
from pathlib import Path
import importlib.util
from unittest import mock
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
FILE = ROOT / "services/phone/PhoneOfonoInstallSession.py"
spec = importlib.util.spec_from_file_location("phone_ofono_install_session", FILE)
session = importlib.util.module_from_spec(spec)
spec.loader.exec_module(session)


class OfonoSessionTests(unittest.TestCase):
    def test_no_tty_prevents_transaction(self):
        run = mock.Mock()
        hold = mock.Mock()
        result = session.run_session(
            interactive=lambda: False, runner=run, hold=hold)
        self.assertEqual(result, 3)
        run.assert_not_called()
        hold.assert_not_called()

    def test_only_exact_packagekit_executable_and_package(self):
        run = mock.Mock(return_value=mock.Mock(returncode=0))
        hold = mock.Mock(return_value="")
        result = session.run_session(
            interactive=lambda: True, find=lambda x: "/usr/bin/pkcon",
            runner=run, hold=hold)
        self.assertEqual(result, 0)
        run.assert_called_once_with(
            ["/usr/bin/pkcon", "install", "ofono"], check=False)
        hold.assert_called_once()
        args = run.call_args.args[0]
        self.assertNotIn("--noninteractive", args)
        self.assertNotIn("-y", args)
        self.assertNotIn("--allow-untrusted", args)

    def test_missing_or_untrusted_pkcon_fails_without_execution(self):
        for path in (None, "", "/tmp/not-pkcon", "pkcon", 17):
            with self.subTest(path=path):
                run = mock.Mock()
                result = session.run_session(
                    interactive=lambda: True, find=lambda _: path,
                    runner=run, hold=mock.Mock())
                self.assertEqual(result, 3)
                run.assert_not_called()

    def test_transaction_failure_not_misreported_as_installed(self):
        run = mock.Mock(return_value=mock.Mock(returncode=7))
        with mock.patch("builtins.print") as output:
            result = session.run_session(
                interactive=lambda: True, find=lambda _: "/usr/bin/pkcon",
                runner=run, hold=lambda _: "")
        self.assertEqual(result, 2)
        self.assertTrue(any("did not confirm" in str(x.args[0])
                            for x in output.call_args_list))

    def test_runtime_error_sanitized_does_not_leak_packagekit_error(self):
        run = mock.Mock(side_effect=OSError("PRIVATE PHONE IDENTIFIER"))
        with mock.patch("builtins.print") as output:
            result = session.run_session(
                interactive=lambda: True, find=lambda _: "/usr/bin/pkcon",
                runner=run, hold=lambda _: "")
        self.assertEqual(result, 2)
        self.assertNotIn("PRIVATE", " ".join(str(x) for x in output.call_args_list))

    def test_exact_user_flag_and_no_background_install(self):
        with mock.patch.object(session, "run_session") as go:
            for args in ([], ["--open"], ["--interactive-ofono", "yes"],
                         ["--install", "ofono"]):
                with self.subTest(args=args):
                    self.assertEqual(session.main(args), 2)
            go.assert_not_called()

    def test_no_direct_system_service_or_bluetooth_changes(self):
        content = FILE.read_text()
        for forbidden in ("sudo ", "pkexec", "dnf install", "systemctl start",
                          "systemctl restart", "bluetoothctl", "shell=True",
                          "os.system(", "sendMessage(", "getContacts("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, content)


if __name__ == "__main__":
    unittest.main()
