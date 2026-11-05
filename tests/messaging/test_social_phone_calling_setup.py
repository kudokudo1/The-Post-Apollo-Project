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

    def test_click_uses_safe_installer_launcher_not_direct_host_install(self):
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

    def test_check_again_survives_install_and_never_becomes_second_setup_button(self):
        # The previous P9 view hid the sole action when the package became
        # installed, leaving the next service/HFP stage without a recheck.
        start = self.ui.index('id: installCallingSupport')
        end = self.ui.index('onTriggered: phonePane.callingSupportSetup()', start)
        control = self.ui[start:end]
        self.assertIn('callPrerequisiteReport.state === "PACKAGE_NOT_INSTALLED"',
                      control)
        self.assertIn('|| phonePane.callSetupStatus === "FOLLOWUP_REQUIRED"',
                      control)
        self.assertIn('? "CHECK AGAIN"', control)
        self.assertIn('? "RETRY SETUP" : "SET UP CALLING"', control)
        self.assertEqual(self.ui.count('id: installCallingSupport'), 1)
        self.assertEqual(self.ui.count('id: connectPhoneAction'), 1)

        begin = self.ui.index('function callingSupportSetup()')
        finish = self.ui.index('function callingSupportSetupText()', begin)
        action = self.ui[begin:finish]
        self.assertIn('callSetupStatus === "GUI_OPEN_REQUESTED"', action)
        self.assertIn('|| callSetupStatus === "FOLLOWUP_REQUIRED"', action)
        self.assertIn('callSetupStatus = "RECHECKING";', action)
        self.assertIn('diagnoseCallPrerequisites();', action)
        self.assertIn('refreshPhoneAudioControls();', action)
        self.assertIn('callPrerequisiteReport.state !== "PACKAGE_NOT_INSTALLED"',
                      action)
        self.assertIn('callSetupProcess.running = true;', action)

    def test_post_install_status_distinguishes_hfp_states_without_claiming_audio(self):
        start = self.ui.index('function callProgressText()')
        finish = self.ui.index('function diagnoseCallPrerequisites()', start)
        progress = self.ui[start:finish]
        self.assertIn('callSetupStatus !== "FOLLOWUP_REQUIRED"', progress)
        for state in ('SERVICE_STOPPED', 'SERVICE_FAILED', 'SERVICE_MASKED',
                      'SERVICE_UNIT_MISSING', 'DBUS_NAME_MISSING',
                      'AUDIO_PATH_UNVERIFIED', 'SERVICE_STARTING'):
            with self.subTest(service=state):
                self.assertIn('"' + state + '"', progress)
        for state in ('READY', 'BLUEZ_CONFLICT', 'SEARCHING', 'CONNECTING'):
            with self.subTest(calls=state):
                self.assertIn('"' + state + '"', progress)
        self.assertIn('BlueFerry reports hands-free call control READY.', progress)
        self.assertIn('still need a real non-emergency test call.', progress)
        self.assertIn('BlueFerry reports a BlueZ HFP conflict.', progress)
        self.assertIn('WirePlumber', progress)
        self.assertIn('phoneAudioStatus.callsEnabled !== true', progress)
        self.assertIn('phoneAudioStatus.result !== "OBSERVED"', progress)
        self.assertIn('visible: phonePane.callProgressText().length > 0',
                      self.ui)
        self.assertIn('text: phonePane.callProgressText()', self.ui)
        for forbidden in ('systemctl start', 'systemctl restart',
                          'bluetoothctl remove', 'sendMessage(',
                          'setCallsEnabled(', 'dnf install'):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, progress)

    def test_package_only_copy_ends_after_install(self):
        # Fedora package-manager instructions should not persist when the
        # same control is now being used to recheck an installed service.
        start = self.ui.index('visible: installCallingSupport.visible')
        text_block = self.ui[start:start + 270]
        self.assertIn(
            '&& phonePane.callPrerequisiteReport.state === "PACKAGE_NOT_INSTALLED"',
            text_block)
        self.assertIn('No installation was confirmed by Social.', self.ui)
        self.assertIn('Package check completed.', self.ui)

    def test_an_installer_request_is_never_reported_as_installed(self):
        self.assertIn('id: callSetupProcess', self.ui)
        self.assertIn('r.schema !== "post-apollo.phone.calling-setup-handoff.v0"', self.ui)
        self.assertIn('r.execution !== "USER_INITIATED_INSTALLER_HANDOFF"', self.ui)
        self.assertIn('r.package !== "ofono"', self.ui)
        self.assertIn('r.packageInstalled !== false', self.ui)
        self.assertIn('r.hfpVerified !== false', self.ui)
        self.assertIn('r.trustedPhoneLink !== "UNVERIFIED"', self.ui)
        self.assertIn('r.contentAccessEnabled !== false', self.ui)
        self.assertIn('r.installerOpened !== (r.status === "GUI_OPEN_REQUESTED")', self.ui)
        self.assertIn('r.stageCandidate !== (', self.ui)
        self.assertIn('r.status === "STAGED_TERMINAL_REQUESTED"', self.ui)
        self.assertIn('r.status === "STAGED_TERMINAL_EXISTING"', self.ui)
        self.assertIn('No installation was confirmed by Social.', self.ui)
        self.assertIn('oFono is still reported missing.', self.ui)
        self.assertIn('CHECK AGAIN updates the existing service and call statuses', self.ui)

    def test_fedora_native_approval_and_missing_installer_explained(self):
        self.assertIn("Review and confirm the Fedora package transaction inside PHONE", self.ui)
        self.assertIn('Neither PackageKit (pkcon) nor Polkit with DNF5 is available.', self.ui)
        self.assertIn('The embedded installer requires foot and Python.', self.ui)
        self.assertIn('No external window was opened or installation confirmed.', self.ui)
        self.assertIn('Only oFono.', self.ui)
        self.assertIn('GUI_UNAVAILABLE', self.ui)
        self.assertIn('GUI_LAUNCH_FAILED', self.ui)
        self.assertIn('UNSUPPORTED_HOST', self.ui)

    def test_fallback_uses_the_same_phone_stage_and_native_approval(self):
        self.assertIn('"TERMINAL_UNAVAILABLE"', self.ui)
        self.assertIn('"PACKAGE_MANAGER_UNAVAILABLE"', self.ui)
        self.assertIn('Polkit with DNF5', self.ui)
        self.assertIn("Fedora's interactive installer runs in the PHONE terminal", self.ui)
        self.assertIn('Review its transaction and confirm or decline;', self.ui)
        self.assertIn('r.packageInstalled !== false', self.ui)
        self.assertIn('r.hfpVerified !== false', self.ui)
        self.assertNotIn('dnf5 install', self.ui)
        self.assertIn('onTriggered: phonePane.callingSupportSetup()', self.ui)

    def test_staged_packagekit_terminal_reuses_verified_phone_cutout(self):
        self.assertIn('property string stagePurpose: "PHONE"', self.ui)
        self.assertIn('phonePane.stagePurpose = "OFONO";', self.ui)
        self.assertIn('phonePane.stageWanted = true;', self.ui)
        self.assertIn('stagePurpose === "OFONO" ? "--sync-installer" : "--sync"', self.ui)
        self.assertIn('WeatherStage.StationChassisCutout {', self.ui)
        self.assertIn('result.verifiedHole === true', self.ui)
        self.assertIn('visible: phonePane.stageHoleActive', self.ui)
        self.assertIn('"OFONO INSTALL // TERMINAL BELOW"', self.ui)
        self.assertIn('phonePane.callSetupStatus = "RECHECKING";', self.ui)
        self.assertIn('phonePane.diagnoseCallPrerequisites();', self.ui)
        self.assertIn('phonePane.refreshPhoneAudioControls();', self.ui)
        self.assertIn('? "RETURN TO PHONE" : "CLOSE SETUP"', self.ui)

    def test_leaving_phone_never_kills_an_active_package_transaction(self):
        start = self.ui.index('function closeStagedSetup()')
        end = self.ui.index('function syncStagedSetup()', start)
        cleanup = self.ui[start:end]
        self.assertIn('var installer = stagePurpose === "OFONO";', cleanup)
        self.assertIn('if (installer) {', cleanup)
        self.assertIn('return;', cleanup)
        self.assertLess(cleanup.index('if (installer) {'),
                        cleanup.index('if (!stageCloseProcess.running)'))
        self.assertNotIn('systemctl', cleanup)
        self.assertIn('if (selectedSection !== "DEVICE") closeStagedSetup();', self.ui)
        self.assertIn('if (!visible) closeStagedSetup();', self.ui)

    def test_setup_does_not_open_external_window_if_panel_bay_is_too_small(self):
        start = self.ui.index('function callingSupportSetup()')
        end = self.ui.index('function callingSupportSetupText()', start)
        body = self.ui[start:end]
        self.assertIn('if (!stageHoleValid) {', body)
        self.assertIn('callSetupStatus = "STAGE_BAY_TOO_SMALL";', body)
        self.assertLess(body.index('if (!stageHoleValid) {'),
                        body.index('callSetupProcess.running = true;'))
        self.assertIn('Enlarge the Social panel and try SET UP CALLING again.', self.ui)
        self.assertIn('No external window was opened.', self.ui)

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
        self.assertIn('pkexec = installed_program("pkexec")', self.helper)
        self.assertIn('dnf5 = installed_program("dnf5")', self.helper)
        self.assertIn('backend_ready = bool(pkcon or (pkexec and dnf5))', self.helper)
        for forbidden in ("sudo ", "dnf install", "subprocess.run(",
                          "bluetoothctl pair", "systemctl start", "shell=True",
                          "sendMessage(", "getContacts("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.helper)


if __name__ == "__main__":
    unittest.main()
