"""Clock resync native authorization bridge structural and security contracts.

This checks the one-shot command wiring without changing host time, and keeps
the short-lived Polkit login surface scoped to a confirmed TimeSettings flow.
Live compositor + compiled Quickshell Polkit are checked separately.
"""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SERVICE = (ROOT / "services/time/TimeSettings.qml").read_text()
AUTH = (ROOT / "widgets/TimeResyncAuthW.qml").read_text()
SHELL = (ROOT / "shell.qml").read_text()
TIMEW = (ROOT / "widgets/TimeW.qml").read_text()
PANE = (ROOT / "widgets/TimeSettingsPane.qml").read_text()
HOST = (ROOT / "services/time/TimeHostControl.py").read_text()


class NativePolkitClockResyncContracts(unittest.TestCase):
    def test_confirmation_waits_for_agent_registration(self):
        prepare = SERVICE.split("function requestResync() {", 1)[1].split(
            "function launchResyncAfterAgentReady(nativeRegistered)", 1)[0]
        self.assertIn("resyncConfirmRequired = false", prepare)
        self.assertIn("resyncAuthPending = true", prepare)
        self.assertIn('resyncStatus = "auth-preparing"', prepare)
        self.assertNotIn("resyncProcess.exec", prepare)
        launch = SERVICE.split("function launchResyncAfterAgentReady() {", 1)[1].split(
            "Timer {", 1)[0]
        self.assertIn("resyncAuthPending = false", launch)
        self.assertIn("resyncProcess.exec([", launch)
        self.assertIn('"resync"', launch)
        self.assertIn("authRegistrationFallback.stop()", launch)

    def test_lazy_authentication_lifetime_and_status(self):
        self.assertIn("import qs.services.time", SHELL)
        self.assertIn("LazyLoader {", SHELL)
        self.assertIn("TimeSettings.resyncAuthPending", SHELL)
        self.assertIn('TimeSettings.resyncStatus === "working"', SHELL)
        self.assertIn("TimeResyncAuthW.qml", SHELL)
        self.assertIn('authRegistrationFallback.restart()', SERVICE)
        self.assertIn("launchResyncAfterAgentReady(true)", AUTH)
        self.assertIn("launchResyncAfterAgentReady(false)", SERVICE)
        self.assertIn("NATIVE POLKIT AGENT REGISTERED", SERVICE)
        self.assertIn("TimeSettings.resyncAuthPath", PANE)
        self.assertIn("onIsRegisteredChanged", AUTH)

    def test_native_polkit_ui_never_collects_password_in_python(self):
        self.assertIn("import Quickshell.Services.Polkit", AUTH)
        self.assertIn("PolkitAgent {", AUTH)
        self.assertIn("flow.submit(responseField.text)", AUTH)
        self.assertIn("TextInput.Password", AUTH)
        self.assertIn('responseField.text = ""', AUTH)
        self.assertIn("flow.cancelAuthenticationRequest()", AUTH)
        self.assertIn("authAgent.flow.actionId", AUTH)
        self.assertNotIn("sudo -S", AUTH + SERVICE + HOST)
        self.assertNotIn("password=", HOST)
        self.assertNotIn("console.log", AUTH)
        self.assertNotIn("console.warn", AUTH)
        self.assertNotIn("FileView {", AUTH)

    def test_system_clock_changes_only_on_explicit_confirm_and_pkexec(self):
        self.assertIn("TimeSettings.requestResync()", PANE)
        self.assertIn('label: "CONFIRM RESYNC"', PANE)
        self.assertIn("TimeSettings.prepareResync()", TIMEW)
        self.assertIn("TimeSettings.prepareResync()", PANE)
        self.assertIn("resyncAuthPending", PANE)
        self.assertIn('id: syncButton', TIMEW)
        self.assertIn('label: "⟳"', TIMEW)
        self.assertIn("[PKEXEC] + command", HOST)
        self.assertIn('[chronyd, "-q", "-t", "15"]', HOST)
        self.assertNotIn("set-ntp", SERVICE)
        self.assertNotIn("set-local-rtc", HOST)
        self.assertNotIn("set-timezone", HOST)


if __name__ == "__main__":
    unittest.main()
