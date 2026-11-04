"""Explicit native setup handoff. No phone/device/permission automation."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest import mock

FILE = (Path(__file__).resolve().parents[2] / "services" / "phone"
        / "PhoneNativeSetupLaunch.py")
SPEC = importlib.util.spec_from_file_location("phone_native_setup_launch", FILE)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class NativeSetupLaunchTests(unittest.TestCase):
    def assert_locked(self, response):
        self.assertEqual(response["schema"], module.SCHEMA)
        self.assertEqual(response["execution"], "USER_INITIATED_NATIVE_SETUP")
        self.assertEqual(response["trustedPhoneLink"], "UNVERIFIED")
        self.assertIs(response["routeEligible"], False)
        self.assertIs(response["contentAccessEnabled"], False)
        self.assertEqual(set(response), {
            "schema", "execution", "target", "status",
            "trustedPhoneLink", "routeEligible", "contentAccessEnabled",
        })

    def test_iphone_uses_existing_client_only_after_explicit_choice(self):
        find = mock.Mock(side_effect=lambda name: "/usr/bin/" + name
                         if name == "blueferry-gtk" else None)
        launcher = mock.Mock()
        result = module.open_setup("iphone", find_executable=find, launcher=launcher)
        self.assert_locked(result)
        self.assertEqual(result["status"], "OPEN_REQUESTED")
        self.assertEqual(result["target"], "iphone")
        self.assertEqual([call.args[0] for call in find.call_args_list],
                         ["blueferry-quickshell", "blueferry-gtk"])
        args, kwargs = launcher.call_args
        self.assertEqual(args[0], ["/usr/bin/blueferry-gtk"])
        self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(kwargs["stdout"], subprocess.DEVNULL)
        self.assertEqual(kwargs["stderr"], subprocess.DEVNULL)
        self.assertTrue(kwargs["start_new_session"])
        self.assertTrue(kwargs["close_fds"])
        self.assertNotIn("shell", kwargs)

    def test_iphone_falls_back_to_qt_client_not_cli_pairing(self):
        names = []
        def find(name):
            names.append(name)
            return "/usr/bin/blueferry-qt" if name == "blueferry-qt" else None
        launcher = mock.Mock()
        response = module.open_setup(
            "iphone", find_executable=find, launcher=launcher)
        self.assert_locked(response)
        self.assertEqual(response["status"], "OPEN_REQUESTED")
        self.assertEqual(names, ["blueferry-quickshell", "blueferry-gtk", "blueferry-qt"])
        self.assertEqual(launcher.call_args.args[0], ["/usr/bin/blueferry-qt"])

    def test_android_launches_kde_connect_native_gui(self):
        find = mock.Mock(return_value="/usr/bin/kdeconnect-app")
        launcher = mock.Mock()
        result = module.open_setup("android", find_executable=find, launcher=launcher)
        self.assert_locked(result)
        self.assertEqual(result["status"], "OPEN_REQUESTED")
        find.assert_called_once_with("kdeconnect-app")
        self.assertEqual(launcher.call_args.args[0], ["/usr/bin/kdeconnect-app"])

    def test_fallback_to_qt_when_gtk_cannot_launch(self):
        def find(name):
            return "/usr/bin/" + name if name in ("blueferry-gtk", "blueferry-qt") else None
        def launch(args, **kwargs):
            if args == ["/usr/bin/blueferry-gtk"]:
                raise OSError("PRIVATE_DESKTOP_LOG")
        response = module.open_setup(
            "iphone", find_executable=find, launcher=launch)
        self.assert_locked(response)
        self.assertEqual(response["status"], "OPEN_REQUESTED")
        self.assertNotIn("PRIVATE", str(response))

    def test_missing_desktop_client_never_runs_background_service(self):
        launcher = mock.Mock()
        result = module.open_setup(
            "iphone", find_executable=lambda _: None, launcher=launcher)
        self.assert_locked(result)
        self.assertEqual(result["status"], "CLIENT_UNAVAILABLE")
        launcher.assert_not_called()

    def test_nonabsolute_or_invalid_resolved_program_cannot_launch(self):
        launcher = mock.Mock()
        for value in ("blueferry-qt", "", None, [], True):
            with self.subTest(value=value):
                result = module.open_setup(
                    "android", find_executable=lambda _: value, launcher=launcher)
                self.assert_locked(result)
                self.assertEqual(result["status"], "CLIENT_UNAVAILABLE")
        launcher.assert_not_called()

    def test_untrusted_platform_cannot_choose_process(self):
        launcher, find = mock.Mock(), mock.Mock()
        for target in ("", "windows", "android; rm -rf /", None, 1, True):
            with self.subTest(target=target):
                response = module.open_setup(
                    target, find_executable=find, launcher=launcher)
                self.assert_locked(response)
                self.assertEqual(response["status"], "CLIENT_UNAVAILABLE")
        launcher.assert_not_called()
        find.assert_not_called()

    def test_program_errors_are_not_reflected_to_ui(self):
        def broken(**kwargs):
            raise ValueError("PRIVATE PHONE ACCESS TOKEN")
        result = module.open_setup(
            "android", find_executable=lambda _: "/usr/bin/kdeconnect-app",
            launcher=lambda *a, **k: broken(**k))
        self.assert_locked(result)
        self.assertEqual(result["status"], "LAUNCH_FAILED")
        self.assertNotIn("PRIVATE", str(result))
        self.assertNotIn("/usr/bin", str(result))

    def test_missing_flags_never_launches_program(self):
        for args in ([], ["--open"], ["iphone"], ["--open", "windows"],
                     ["--open", "iphone", "--pair"]):
            with self.subTest(args=args), mock.patch.object(module, "open_setup") as open_, mock.patch("builtins.print"):
                self.assertEqual(module.main(args), 2)
                open_.assert_not_called()

    def test_exact_flag_launches_one_target(self):
        with mock.patch.object(module, "open_setup",
                               return_value=module._result("android", "OPEN_REQUESTED")) as open_, mock.patch("builtins.print"):
            self.assertEqual(module.main(["--open", "android"]), 0)
            open_.assert_called_once_with("android")

    def test_backend_only_install_can_open_official_pairing_wizard(self):
        programs = {
            "blueferry": "/usr/bin/blueferry",
            "foot": "/usr/bin/foot",
        }
        launcher = mock.Mock()
        result = module.open_setup(
            "iphone",
            find_executable=programs.get,
            launcher=launcher,
        )
        self.assert_locked(result)
        self.assertEqual(result["status"], "OPEN_REQUESTED")
        self.assertEqual(
            launcher.call_args.args[0],
            ["/usr/bin/foot", "-e", "/usr/bin/blueferry", "pair-setup"],
        )
        self.assertNotIn("shell", launcher.call_args.kwargs)
        self.assertTrue(launcher.call_args.kwargs["start_new_session"])

    def test_no_terminal_or_cli_means_no_pairing(self):
        programs = {"blueferry": "/usr/bin/blueferry"}
        launcher = mock.Mock()
        result = module.open_setup(
            "iphone", find_executable=programs.get, launcher=launcher)
        self.assert_locked(result)
        self.assertEqual(result["status"], "CLIENT_UNAVAILABLE")
        launcher.assert_not_called()

    def test_native_gui_takes_precedence_over_pairing_wizard(self):
        programs = {
            "blueferry-quickshell": "/usr/bin/blueferry-quickshell",
            "blueferry": "/usr/bin/blueferry",
            "foot": "/usr/bin/foot",
        }
        launcher = mock.Mock()
        result = module.open_setup(
            "iphone", find_executable=programs.get, launcher=launcher)
        self.assert_locked(result)
        self.assertEqual(result["status"], "OPEN_REQUESTED")
        self.assertEqual(launcher.call_args.args[0],
                         ["/usr/bin/blueferry-quickshell"])
        self.assertEqual(launcher.call_count, 1)

    def test_android_never_uses_iphone_wizard(self):
        programs = {
            "blueferry": "/usr/bin/blueferry",
            "foot": "/usr/bin/foot",
        }
        launcher = mock.Mock()
        result = module.open_setup(
            "android", find_executable=programs.get, launcher=launcher)
        self.assert_locked(result)
        self.assertEqual(result["status"], "CLIENT_UNAVAILABLE")
        launcher.assert_not_called()

    def test_source_has_no_privileged_pairing_or_message_calls(self):
        src = FILE.read_text()
        for forbidden in ("systemctl start", "bluetoothctl pair",
                          "requestPairing(", "getMessages(", "sendMessage(",
                          "sudo ", "pkexec", "shell=True"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, src)
        self.assertIn('[terminal_path, *flags, wizard, "pair-setup"]', src)


if __name__ == "__main__":
    unittest.main()
