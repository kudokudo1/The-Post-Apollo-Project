"""User-authorized oFono setup opens a graphical installer, not a root shell."""
import importlib.util
from pathlib import Path
from unittest import mock
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
FILE = ROOT / "services/phone/PhoneCallingSetupHandoff.py"
sys.path.insert(0, str(ROOT / "services" / "phone"))
spec = importlib.util.spec_from_file_location("phone_call_setup_gui", FILE)
gui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gui)


def evidence(**updates):
    value = {
        "schema": "post-apollo.phone.calls-prerequisites.v0",
        "execution": "READ_ONLY_CALL_DIAGNOSIS",
        "state": "PACKAGE_NOT_INSTALLED", "package": "NOT_INSTALLED",
        "serviceLoad": "not-found", "serviceActive": "inactive",
        "systemBus": "UNKNOWN", "hfpVerified": False,
        "trustedPhoneLink": "UNVERIFIED", "contentAccessEnabled": False,
    }
    value.update(updates)
    return value


class CallingSetupGuiTests(unittest.TestCase):
    def locked(self, result):
        self.assertEqual(result["schema"], gui.SCHEMA)
        self.assertEqual(result["execution"], "USER_INITIATED_GUI_HANDOFF")
        self.assertEqual(result["package"], "ofono")
        self.assertFalse(result["packageInstalled"])
        self.assertFalse(result["hfpVerified"])
        self.assertEqual(result["trustedPhoneLink"], "UNVERIFIED")
        self.assertIs(result["contentAccessEnabled"], False)
        self.assertEqual(result["installerOpened"],
                         result["status"] == "GUI_OPEN_REQUESTED")
        self.assertEqual(set(result), {
            "schema", "execution", "status", "package",
            "installerOpened", "packageInstalled", "hfpVerified",
            "trustedPhoneLink", "contentAccessEnabled",
        })
        self.assertNotIn("PRIVATE", str(result))

    def test_one_explicit_click_opens_fedora_software_package_details(self):
        found = mock.Mock(return_value="/usr/bin/gnome-software")
        launcher = mock.Mock()
        result = gui.open_support(
            prerequisite=lambda: evidence(), is_fedora=lambda: True,
            find=found, launcher=launcher)
        self.locked(result)
        self.assertEqual(result["status"], "GUI_OPEN_REQUESTED")
        found.assert_called_once_with("gnome-software")
        launcher.assert_called_once_with(
            ["/usr/bin/gnome-software", "--details-pkg=ofono"],
            stdin=gui.subprocess.DEVNULL,
            stdout=gui.subprocess.DEVNULL,
            stderr=gui.subprocess.DEVNULL,
            start_new_session=True, close_fds=True)
        self.assertFalse(result["packageInstalled"])

    def test_fallback_to_gnome_packagekit_gui_without_auto_install(self):
        found = mock.Mock(side_effect=lambda name:
                          "/usr/bin/gpk-install-package-name"
                          if name == "gpk-install-package-name" else None)
        launcher = mock.Mock()
        result = gui.open_support(
            prerequisite=lambda: evidence(), is_fedora=lambda: True,
            find=found, launcher=launcher)
        self.locked(result)
        self.assertEqual(result["status"], "GUI_OPEN_REQUESTED")
        self.assertEqual([x.args[0] for x in found.call_args_list],
                         ["gnome-software", "gpk-install-package-name"])
        self.assertEqual(launcher.call_args.args[0],
                         ["/usr/bin/gpk-install-package-name", "ofono"])

    def test_no_supported_gui_gives_clean_explanation_not_terminal_fallback(self):
        launch = mock.Mock()
        result = gui.open_support(
            prerequisite=lambda: evidence(), is_fedora=lambda: True,
            find=lambda name: None, launcher=launch)
        self.locked(result)
        self.assertEqual(result["status"], "GUI_UNAVAILABLE")
        launch.assert_not_called()

    def test_untrusted_resolved_program_not_launched(self):
        launch = mock.Mock()
        for resolved in ("gnome-software", "/tmp/evil", "", None, 2, True):
            with self.subTest(resolved=resolved):
                result = gui.open_support(
                    prerequisite=lambda: evidence(), is_fedora=lambda: True,
                    find=lambda name: resolved, launcher=launch)
                self.locked(result)
                self.assertEqual(result["status"], "GUI_UNAVAILABLE")
        launch.assert_not_called()

    def test_primary_gui_failure_falls_back_to_secondary_gui(self):
        def find(name):
            return "/usr/bin/" + name
        def launch(args, **kwargs):
            if args[0] == "/usr/bin/gnome-software":
                raise OSError("PRIVATE INSTALLER ERROR")
        result = gui.open_support(
            prerequisite=lambda: evidence(), is_fedora=lambda: True,
            find=find, launcher=launch)
        self.locked(result)
        self.assertEqual(result["status"], "GUI_OPEN_REQUESTED")

    def test_all_gui_launches_fail_without_leaking_error(self):
        result = gui.open_support(
            prerequisite=lambda: evidence(), is_fedora=lambda: True,
            find=lambda name: "/usr/bin/" + name,
            launcher=lambda *args, **kwargs: (_ for _ in ()).throw(
                RuntimeError("PRIVATE TOKEN")))
        self.locked(result)
        self.assertEqual(result["status"], "GUI_LAUNCH_FAILED")

    def test_no_gui_opened_when_service_present_or_diagnosis_unreliable(self):
        cases = [
            evidence(state="SERVICE_STOPPED", package="INSTALLED",
                     serviceLoad="loaded"),
            evidence(state="SERVICE_UNIT_MISSING", package="UNKNOWN"),
            evidence(state="SERVICE_FAILED"),
            evidence(state="AUDIO_PATH_UNVERIFIED"),
            evidence(package="UNKNOWN"),
            evidence(serviceLoad="loaded"),
        ]
        for view in cases:
            with self.subTest(view=view):
                launch = mock.Mock()
                result = gui.open_support(
                    prerequisite=lambda: view, is_fedora=lambda: True,
                    find=lambda x: "/usr/bin/gnome-software",
                    launcher=launch)
                self.locked(result)
                self.assertEqual(result["status"], "NOT_APPLICABLE")
                launch.assert_not_called()

    def test_tampered_diagnostic_refuses_install(self):
        cases = [
            {}, None, [], evidence(trustedPhoneLink="VERIFIED"),
            evidence(contentAccessEnabled=True), evidence(hfpVerified=True),
            evidence(schema="fake"), evidence(execution="USER_ACTION"),
        ]
        for view in cases:
            with self.subTest(view=view):
                result = gui.open_support(
                    prerequisite=lambda: view, is_fedora=lambda: True)
                self.locked(result)
                self.assertEqual(result["status"], "DIAGNOSIS_UNAVAILABLE")

    def test_only_fedora_is_supported_for_package_name(self):
        launch = mock.Mock()
        result = gui.open_support(
            prerequisite=lambda: evidence(), is_fedora=lambda: False,
            launcher=launch)
        self.locked(result)
        self.assertEqual(result["status"], "UNSUPPORTED_HOST")
        launch.assert_not_called()

    def test_os_release_parses_quoted_or_unquoted_id(self):
        for value in ("ID=fedora\n", "NAME=Fedora\nID=\"fedora\"\n"):
            with self.subTest(value=value):
                with mock.patch.object(gui, "Path") as path:
                    path.return_value.read_text.return_value = value
                    self.assertTrue(gui._fedora())
        with mock.patch.object(gui, "Path") as path:
            path.return_value.read_text.return_value = "ID=ubuntu\n"
            self.assertFalse(gui._fedora())

    def test_explicit_flag_required_no_auto_launch(self):
        with mock.patch.object(gui, "open_support") as open_, mock.patch("builtins.print"):
            for flags in ([], ["--open"], ["ofono"],
                          ["--open-ofono", "install"], ["--set", "ofono"]):
                with self.subTest(flags=flags):
                    self.assertEqual(gui.main(flags), 2)
            open_.assert_not_called()

    def test_gui_unavailable_is_normal_report_not_python_crash(self):
        with mock.patch.object(gui, "open_support", return_value=gui._result(
            "GUI_UNAVAILABLE")) as open_, mock.patch("builtins.print") as printed:
            self.assertEqual(gui.main(["--open-ofono"]), 0)
            open_.assert_called_once_with()
            self.assertIn("GUI_UNAVAILABLE", printed.call_args.args[0])

    def test_source_never_directly_installs_or_modifies_service(self):
        script = FILE.read_text()
        for forbidden in ("pkexec", "sudo ", "dnf install", "pkcon install",
                          "systemctl start", "systemctl enable", "systemctl restart",
                          "bluetoothctl", "shell=True", "sendMessage(",
                          "getContacts(", "subprocess.run(", "os.system("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, script)


if __name__ == "__main__":
    unittest.main()
