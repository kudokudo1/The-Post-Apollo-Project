"""PHONE installer handoff opens exact staged PackageKit terminal, not Software app-details."""
import importlib.util
from pathlib import Path
from unittest import mock
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
FILE = ROOT / "services/phone/PhoneCallingSetupHandoff.py"
sys.path.insert(0, str(ROOT / "services" / "phone"))
spec = importlib.util.spec_from_file_location("phone_call_setup_staged", FILE)
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


def programs(**overrides):
    v = {"foot": "/usr/bin/foot", "pkcon": "/usr/bin/pkcon",
         "python3": "/usr/bin/python3"}
    v.update(overrides)
    return v.get


class CallingSetupGuiTests(unittest.TestCase):
    def locked(self, result):
        self.assertEqual(result["schema"], gui.SCHEMA)
        self.assertEqual(result["execution"], "USER_INITIATED_INSTALLER_HANDOFF")
        self.assertEqual(result["package"], "ofono")
        self.assertFalse(result["packageInstalled"])
        self.assertFalse(result["hfpVerified"])
        self.assertEqual(result["trustedPhoneLink"], "UNVERIFIED")
        self.assertIs(result["contentAccessEnabled"], False)
        self.assertIs(result["installerOpened"], result["status"] == "GUI_OPEN_REQUESTED")
        self.assertIs(result["stageCandidate"], result["status"] in (
            "STAGED_TERMINAL_REQUESTED", "STAGED_TERMINAL_EXISTING"))
        self.assertEqual(set(result), {
            "schema", "execution", "status", "package",
            "installerOpened", "stageCandidate", "packageInstalled",
            "hfpVerified", "trustedPhoneLink", "contentAccessEnabled",
        })
        self.assertNotIn("PRIVATE", str(result))

    def test_exact_missing_ofono_click_opens_staged_interactive_packagekit(self):
        launcher = mock.Mock()
        result = gui.open_support(
            prerequisite=lambda: evidence(), is_fedora=lambda: True,
            find=programs(), launcher=launcher, already_open=lambda: False)
        self.locked(result)
        self.assertEqual(result["status"], "STAGED_TERMINAL_REQUESTED")
        launcher.assert_called_once_with(
            ["/usr/bin/foot", "--app-id", gui.INSTALL_APP_ID, "-e",
             "/usr/bin/python3", str(FILE.with_name("PhoneOfonoInstallSession.py")),
             "--interactive-ofono"],
            stdin=gui.subprocess.DEVNULL,
            stdout=gui.subprocess.DEVNULL,
            stderr=gui.subprocess.DEVNULL,
            start_new_session=True, close_fds=True)

    def test_same_existing_exact_staged_actor_never_duplicate_installer(self):
        launcher = mock.Mock()
        result = gui.open_support(
            prerequisite=lambda: evidence(), is_fedora=lambda: True,
            already_open=lambda: True, launcher=launcher)
        self.locked(result)
        self.assertEqual(result["status"], "STAGED_TERMINAL_EXISTING")
        launcher.assert_not_called()

    def test_sway_stage_inspection_exception_refuses_untracked_duplicate(self):
        launcher = mock.Mock()
        result = gui.open_support(
            prerequisite=lambda: evidence(), is_fedora=lambda: True,
            already_open=mock.Mock(side_effect=ValueError("PRIVATE ACTOR")),
            launcher=launcher)
        self.locked(result)
        self.assertEqual(result["status"], "STAGE_UNAVAILABLE")
        launcher.assert_not_called()

    def test_when_staged_foot_is_unavailable_try_packagekit_gui_not_gnome_software(self):
        launcher = mock.Mock()
        p = programs(foot=None, **{"gpk-install-package-name": "/usr/bin/gpk-install-package-name",
                                    "gnome-software": "/usr/bin/gnome-software"})
        result = gui.open_support(
            prerequisite=lambda: evidence(), is_fedora=lambda: True,
            find=p, launcher=launcher, already_open=lambda: False)
        self.locked(result)
        self.assertEqual(result["status"], "GUI_OPEN_REQUESTED")
        self.assertFalse(result["stageCandidate"])
        self.assertEqual(launcher.call_args.args[0],
                         ["/usr/bin/gpk-install-package-name", "ofono"])
        self.assertNotIn("gnome-software", str(launcher.call_args.args[0]))

    def test_no_supported_client_no_hidden_terminal_fallback(self):
        launcher = mock.Mock()
        result = gui.open_support(
            prerequisite=lambda: evidence(), is_fedora=lambda: True,
            find=lambda _: None, launcher=launcher, already_open=lambda: False)
        self.locked(result)
        self.assertEqual(result["status"], "GUI_UNAVAILABLE")
        launcher.assert_not_called()

    def test_untrusted_resolved_program_is_not_launched(self):
        launcher = mock.Mock()
        for wrong in ("foot", "/tmp/untrusted", "", None, 2, True):
            with self.subTest(path=wrong):
                result = gui.open_support(
                    prerequisite=lambda: evidence(), is_fedora=lambda: True,
                    find=lambda name: wrong,
                    launcher=launcher, already_open=lambda: False)
                self.locked(result)
                self.assertEqual(result["status"], "GUI_UNAVAILABLE")
        launcher.assert_not_called()

    def test_stage_launch_failure_tries_packagekit_gui(self):
        def find(name):
            return "/usr/bin/" + name
        launched = []
        def launch(args, **kwargs):
            launched.append(args)
            if args[0] == "/usr/bin/foot":
                raise OSError("PRIVATE")
        result = gui.open_support(
            prerequisite=lambda: evidence(), is_fedora=lambda: True,
            find=find, launcher=launch, already_open=lambda: False)
        self.locked(result)
        self.assertEqual(result["status"], "GUI_OPEN_REQUESTED")
        self.assertEqual(launched[-1], ["/usr/bin/gpk-install-package-name", "ofono"])

    def test_all_launches_fail_without_leaking_error(self):
        result = gui.open_support(
            prerequisite=lambda: evidence(), is_fedora=lambda: True,
            find=lambda name: "/usr/bin/" + name,
            launcher=mock.Mock(side_effect=RuntimeError("PRIVATE")),
            already_open=lambda: False)
        self.locked(result)
        self.assertEqual(result["status"], "GUI_LAUNCH_FAILED")

    def test_not_missing_or_forged_grant_blocks_any_launch(self):
        cases = [
            evidence(state="SERVICE_STOPPED", package="INSTALLED", serviceLoad="loaded"),
            evidence(state="SERVICE_UNIT_MISSING", package="UNKNOWN"),
            evidence(state="SERVICE_FAILED"), evidence(package="UNKNOWN"),
            evidence(serviceLoad="loaded"), {}, None, [],
            evidence(trustedPhoneLink="VERIFIED"),
            evidence(contentAccessEnabled=True), evidence(hfpVerified=True),
            evidence(schema="fake"), evidence(execution="USER_ACTION"),
        ]
        for view in cases:
            with self.subTest(view=view):
                launcher = mock.Mock()
                result = gui.open_support(
                    prerequisite=lambda view=view: view, is_fedora=lambda: True,
                    find=programs(), launcher=launcher, already_open=lambda: False)
                self.locked(result)
                self.assertIn(result["status"], ("NOT_APPLICABLE", "DIAGNOSIS_UNAVAILABLE"))
                launcher.assert_not_called()

    def test_only_fedora_is_supported(self):
        launcher = mock.Mock()
        result = gui.open_support(
            prerequisite=lambda: evidence(), is_fedora=lambda: False,
            launcher=launcher)
        self.locked(result)
        self.assertEqual(result["status"], "UNSUPPORTED_HOST")
        launcher.assert_not_called()

    def test_os_release_parses_quoted_or_unquoted_id(self):
        for value in ("ID=fedora\n", 'NAME=Fedora\nID="fedora"\n'):
            with self.subTest(value=value):
                with mock.patch.object(gui, "Path") as path:
                    path.return_value.read_text.return_value = value
                    self.assertTrue(gui._fedora())
        with mock.patch.object(gui, "Path") as path:
            path.return_value.read_text.return_value = "ID=ubuntu\n"
            self.assertFalse(gui._fedora())

    def test_explicit_flag_required_no_auto_launch(self):
        with mock.patch.object(gui, "open_support") as opener, mock.patch("builtins.print"):
            for args in ([], ["--open"], ["ofono"], ["--open-ofono", "auto"]):
                self.assertEqual(gui.main(args), 2)
            opener.assert_not_called()

    def test_report_unavailable_does_not_crash(self):
        with mock.patch.object(gui, "open_support", return_value=gui._result(
            "GUI_UNAVAILABLE")), mock.patch("builtins.print") as printed:
            self.assertEqual(gui.main(["--open-ofono"]), 0)
            self.assertIn("GUI_UNAVAILABLE", printed.call_args.args[0])

    def test_no_direct_install_or_phone_mutation_in_handoff(self):
        source = FILE.read_text()
        for forbidden in ("sudo ", "dnf install", "systemctl start",
                          "systemctl enable", "systemctl restart",
                          "bluetoothctl", "shell=True", "sendMessage(",
                          "getContacts(", "subprocess.run(", "os.system("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
