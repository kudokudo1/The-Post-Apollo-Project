"""oFono's embedded PackageKit session never runs without an interactive opt-in."""
from pathlib import Path
import importlib.util
from unittest import mock
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
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

    def test_no_supported_package_backend_fails_without_execution(self):
        for paths in ({}, {"pkcon": "pkcon"},
                      {"pkexec": "/usr/bin/pkexec"},
                      {"dnf5": "/usr/bin/dnf5"},
                      {"pkexec": "/tmp/pkexec", "dnf5": "/usr/bin/dnf5"},
                      {"pkexec": "/usr/bin/pkexec", "dnf5": "/tmp/dnf5"}):
            with self.subTest(paths=paths):
                run = mock.Mock()
                result = session.run_session(
                    interactive=lambda: True,
                    find=paths.get,
                    runner=run, hold=mock.Mock())
                self.assertEqual(result, 3)
                run.assert_not_called()

    def test_dnf5_fallback_with_polkit_requires_independent_authorization(self):
        run = mock.Mock(return_value=mock.Mock(returncode=0))
        found = {"pkexec": "/usr/bin/pkexec", "dnf5": "/usr/bin/dnf5"}
        result = session.run_session(
            interactive=lambda: True, find=found.get,
            runner=run, hold=lambda text: "")
        self.assertEqual(result, 0)
        run.assert_called_once_with(
            ["/usr/bin/pkexec", "/usr/bin/dnf5",
             "--setopt=assumeyes=False", "--setopt=defaultyes=False",
             "install", "ofono"], check=False)
        command = run.call_args.args[0]
        self.assertNotIn("--assumeyes", command)
        self.assertNotIn("-y", command)
        self.assertNotIn("--allow-erasing", command)
        self.assertNotIn("bash", command)

    def test_verified_dnf_alias_uses_same_interactive_transaction(self):
        run = mock.Mock(return_value=mock.Mock(returncode=0))
        paths = {"pkexec": "/usr/bin/pkexec", "dnf": "/usr/bin/dnf"}
        # The shared command-discovery tests prove that this alias is
        # allowed only when its canonical target really is dnf5.
        with mock.patch.object(session, "trusted_dnf5", return_value="/usr/bin/dnf"):
            result = session.run_session(
                interactive=lambda: True, find=paths.get,
                runner=run, hold=lambda _: "")
        self.assertEqual(result, 0)
        run.assert_called_once_with(
            ["/usr/bin/pkexec", "/usr/bin/dnf",
             "--setopt=assumeyes=False", "--setopt=defaultyes=False",
             "install", "ofono"], check=False)

    def test_packagekit_is_preferred_when_both_backends_exist(self):
        paths = {"pkcon": "/usr/bin/pkcon", "pkexec": "/usr/bin/pkexec",
                 "dnf5": "/usr/bin/dnf5"}
        run = mock.Mock(return_value=mock.Mock(returncode=0))
        result = session.run_session(
            interactive=lambda: True, find=paths.get,
            runner=run, hold=lambda text: "")
        self.assertEqual(result, 0)
        run.assert_called_once_with(
            ["/usr/bin/pkcon", "install", "ofono"], check=False)

    def test_failed_packagekit_does_not_automatically_try_root_dnf5(self):
        paths = {"pkcon": "/usr/bin/pkcon", "pkexec": "/usr/bin/pkexec",
                 "dnf5": "/usr/bin/dnf5"}
        run = mock.Mock(return_value=mock.Mock(returncode=126))
        result = session.run_session(
            interactive=lambda: True, find=paths.get,
            runner=run, hold=lambda text: "")
        self.assertEqual(result, 2)
        run.assert_called_once_with(
            ["/usr/bin/pkcon", "install", "ofono"], check=False)

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
        self.assertIn('"--setopt=assumeyes=False"', content)
        self.assertIn('"--setopt=defaultyes=False"', content)
        for forbidden in ("sudo ", "dnf install", "systemctl start",
                          "systemctl restart", "bluetoothctl", "shell=True",
                          "os.system(", "sendMessage(", "getContacts(",
                          "input_password(", "getMessages("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, content)


if __name__ == "__main__":
    unittest.main()
