"""PHONE's one contextual calling setup action, no terminal or auto install."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PHONE = ROOT / "widgets" / "messanger" / "PhonePane.qml"
HELPER = ROOT / "services" / "phone" / "PhoneCallingSetupHandoff.py"


class CallingSetupUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ui = PHONE.read_text()
        cls.helper = HELPER.read_text()

    def test_small_calling_setup_control_stays_inside_existing_device_menu(self):
        self.assertIn('id: phoneAudioSettings', self.ui)
        self.assertIn('id: installCallingSupport', self.ui)
        self.assertIn('label: phonePane.callSetupStatus === "GUI_OPEN_REQUESTED"', self.ui)
        self.assertIn('|| phonePane.callSetupStatus === "FOLLOWUP_REQUIRED"', self.ui)
        self.assertIn('? "CHECK AGAIN"', self.ui)
        self.assertIn('? "RETRY SETUP" : "SET UP CALLING"', self.ui)
        self.assertIn('onTriggered: phonePane.callingSupportSetup()', self.ui)
        self.assertIn('callPrerequisiteReport.state === "PACKAGE_NOT_INSTALLED"', self.ui)
        self.assertIn('id: connectPhoneAction', self.ui)
        self.assertEqual(self.ui.count('id: connectPhoneAction'), 1)
        self.assertIn('    ContactList {', self.ui)
        self.assertIn('    ChatFeed {', self.ui)
        self.assertIn('sendEnabled: false', self.ui)
        self.assertNotIn('FloatingWindow {', self.ui)
        self.assertNotIn('PanelWindow {', self.ui)

    def test_click_uses_safe_gui_launcher_not_terminal_installer(self):
        start = self.ui.index('function callingSupportSetup()')
        end = self.ui.index('function callingSupportSetupText()', start)
        action = self.ui[start:end]
        self.assertIn('setupState !== "CHECKED"', action)
        self.assertIn('callPrerequisiteReport.package !== "NOT_INSTALLED"', action)
        self.assertIn('callPrerequisiteReport.serviceLoad !== "not-found"', action)
        self.assertIn('callPrerequisiteReport.state !== "PACKAGE_NOT_INSTALLED"', action)
        self.assertIn('callSetupProcess.running = true;', action)
        self.assertIn('PhoneCallingSetupHandoff.py', action)
        self.assertIn('"--open-ofono"', action)
        self.assertIn('callSetupStatus === "GUI_OPEN_REQUESTED"', action)
        self.assertIn('diagnoseCallPrerequisites();', action)
        self.assertIn('refreshPhoneAudioControls();', action)
        self.assertNotIn('dnf install', action)
        self.assertNotIn('systemctl start', action)

    def test_an_installer_request_is_never_reported_as_installed(self):
        self.assertIn('id: callSetupProcess', self.ui)
        self.assertIn('r.schema !== "post-apollo.phone.calling-setup-handoff.v0"', self.ui)
        self.assertIn('r.execution !== "USER_INITIATED_GUI_HANDOFF"', self.ui)
        self.assertIn('r.package !== "ofono"', self.ui)
        self.assertIn('r.packageInstalled !== false', self.ui)
        self.assertIn('r.hfpVerified !== false', self.ui)
        self.assertIn('r.trustedPhoneLink !== "UNVERIFIED"', self.ui)
        self.assertIn('r.contentAccessEnabled !== false', self.ui)
        self.assertIn('r.installerOpened !== (r.status === "GUI_OPEN_REQUESTED")', self.ui)
        self.assertIn('No package was installed by Social.', self.ui)
        self.assertIn('oFono is still reported missing.', self.ui)
        self.assertIn('CHECK AGAIN updates the existing service and call statuses', self.ui)

    def test_fedora_native_approval_and_missing_installer_explained(self):
        self.assertIn("Fedora's software manager handles package review and approval.", self.ui)
        self.assertIn('No supported graphical package installer was found.', self.ui)
        self.assertIn('No installation was confirmed.', self.ui)
        self.assertIn('Only oFono.', self.ui)
        self.assertIn('GUI_UNAVAILABLE', self.ui)
        self.assertIn('GUI_LAUNCH_FAILED', self.ui)
        self.assertIn('UNSUPPORTED_HOST', self.ui)

    def test_no_silent_setup_from_opening_phone_or_changing_tabs(self):
        start = self.ui.index('onVisibleChanged: {')
        end = self.ui.index('\n    }', start)
        visibility = self.ui[start:end]
        self.assertNotIn('callingSupportSetup()', visibility)
        self.assertNotIn('callSetupProcess.running = true;', visibility)
        self.assertIn('callSetupStatus = "IDLE";', visibility)
        self.assertIn('visible: phonePane.setupState === "CHECKED" && !phonePane.stageWanted', self.ui)
        self.assertIn('WeatherStage.StationChassisCutout {', self.ui)
        self.assertIn('conversations: []', self.ui)
        self.assertIn('messages: []', self.ui)

    def test_no_installation_or_device_defaults_ever_enter_our_code(self):
        for forbidden in ("pkexec", "sudo ", "dnf install", "subprocess.run(",
                          "bluetoothctl pair", "systemctl start", "shell=True",
                          "sendMessage(", "getContacts("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.helper)


if __name__ == "__main__":
    unittest.main()
