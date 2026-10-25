"""Offline native-desktop and official-web fallbacks; no real launches or logins."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "services/messaging/DesktopServiceLauncher.py"
WEB = ROOT / "widgets/messanger/XBrowser.py"
GEOMETRY = ROOT / "widgets/messanger/DiscordGeometry.py"
SOCIAL = ROOT / "widgets/messanger/MessagingW.qml"
PANEL = ROOT / "widgets/messanger/ProviderAccessPanel.qml"
ROUTER = ROOT / "services/messaging/SocialMessageRouter.qml"

def load(path, module):
    spec = importlib.util.spec_from_file_location(module, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

desktop = load(LAUNCHER, "native_desktop_test")
browser = load(WEB, "social_web_fallback_test")
geometry = load(GEOMETRY, "social_web_geometry_test")

class ProviderAccessContracts(unittest.TestCase):
    def test_supported_desktop_commands_are_allowlisted(self):
        self.assertEqual(set(desktop.DESKTOP_APPS), {"signal", "viber", "wechat"})
        for provider in ("signal", "viber", "wechat"):
            with patch.object(desktop.shutil, "which", return_value=None):
                r = desktop.operation("probe", provider)
                self.assertFalse(r["desktopInstalled"])
                self.assertFalse(r["launched"])
                self.assertEqual(r["backendMode"], "UNSUPPORTED")
        for unsupported in ("line", "kakaotalk", "whatsapp", "messenger", "telegram", "missing"):
            with self.subTest(service=unsupported), self.assertRaises(ValueError):
                desktop.operation("open", unsupported)

    def test_probe_only_reads_installed_binary_no_login_or_spawn(self):
        with patch.object(desktop.shutil, "which", return_value="/usr/bin/signal-desktop"):
            with patch.object(desktop.subprocess, "Popen") as spawn:
                status = desktop.operation("probe", "signal")
        spawn.assert_not_called()
        self.assertEqual(status["desktopInstalled"], True)
        self.assertFalse(status["launched"])
        self.assertEqual(status["backendMode"], "UNSUPPORTED")

    def test_explicit_open_only_starts_exact_executable(self):
        with patch.object(desktop.shutil, "which", return_value="/usr/bin/viber"):
            with patch.object(desktop.subprocess, "Popen") as spawn:
                result = desktop.operation("open", "viber")
        spawn.assert_called_once()
        args, kwargs = spawn.call_args
        self.assertEqual(args[0], ["/usr/bin/viber"])
        self.assertIs(kwargs["stdin"], subprocess.DEVNULL)
        self.assertIs(kwargs["stdout"], subprocess.DEVNULL)
        self.assertIs(kwargs["stderr"], subprocess.DEVNULL)
        self.assertTrue(kwargs["start_new_session"])
        self.assertTrue(result["launched"])
        self.assertEqual(result["backendMode"], "UNSUPPORTED")
        self.assertNotIn("authenticated", result)

    def test_web_fallback_sites_keep_existing_profiles_distinct(self):
        self.assertEqual(set(browser.WEB_FALLBACK_SITES), {"whatsappweb", "messengerweb"})
        self.assertEqual(len(browser.SITES), 21)
        self.assertEqual(set(browser.ALL_SITES), set(geometry.BROWSER_SITES))
        self.assertEqual(browser.site_config("whatsappweb"),
            ("https://web.whatsapp.com/", "post-apollo-whatsappweb", "whatsappweb-browser"))
        self.assertEqual(browser.site_config("messengerweb"),
            ("https://www.facebook.com/messages/", "post-apollo-messengerweb", "messengerweb-browser"))
        self.assertEqual(geometry.sway_criteria("whatsappweb"),
            '[class="post-apollo-whatsappweb"]')
        self.assertEqual(geometry.sway_criteria("messengerweb"),
            '[class="post-apollo-messengerweb"]')

    def test_browser_launch_explicit_and_no_profile_collision(self):
        with patch.object(browser, "browser_prefix", return_value=["/usr/bin/chromium"]):
            with patch.dict(browser.os.environ, {"XDG_DATA_HOME": "/tmp/post-apollo-fallback-tests"}):
                a = browser.browser_command("whatsappweb")
                b = browser.browser_command("messengerweb")
        self.assertIn("--app=https://web.whatsapp.com/", a)
        self.assertIn("--app=https://www.facebook.com/messages/", b)
        self.assertIn("--class=post-apollo-whatsappweb", a)
        self.assertIn("--class=post-apollo-messengerweb", b)
        self.assertIn("--user-data-dir=/tmp/post-apollo-fallback-tests/post-apollo/whatsappweb-browser", a)
        self.assertIn("--user-data-dir=/tmp/post-apollo-fallback-tests/post-apollo/messengerweb-browser", b)
        self.assertNotEqual(a, b)

    def test_router_reads_real_inert_adapter_states_only(self):
        src = ROUTER.read_text()
        self.assertIn("SignalAdapter {", src)
        self.assertIn("MessengerAdapter {", src)
        self.assertIn("ViberAdapter {", src)
        self.assertIn("active: router.appIndex === 26", src)
        self.assertIn("active: router.appIndex === 15", src)
        self.assertIn("active: router.appIndex === 29", src)
        self.assertIn('appIndex === 26 ? signal.backendMode', src)
        self.assertIn('appIndex === 15 ? messenger.backendDetail', src)
        self.assertIn('appIndex === 29 ? viber.backendDetail', src)
        self.assertIn('selectedBackend: appIndex === 0 ? sessions', src)
        self.assertIn('appIndex === 2 ? telegram : null', src)
        self.assertIn('if (!nativeSelected || !selectedBackend || !sendEnabled', src)

    def test_panel_is_embedded_and_buttons_do_not_perform_login(self):
        panel = PANEL.read_text()
        social = SOCIAL.read_text()
        self.assertIn("ProviderAccessPanel {", social)
        self.assertIn("backendMode: messageRouter.accessBackendMode", social)
        self.assertIn("backendDetail: messageRouter.accessBackendDetail", social)
        self.assertIn("serviceIndex: messagingWindow.activeAppIndex", social)
        self.assertIn("messagingWindow.openProviderWeb(serviceId);", social)
        self.assertIn('panel.browserRequested(panel.serviceId)', panel)
        self.assertIn('Quickshell.shellPath("services/messaging/DesktopServiceLauncher.py")', panel)
        self.assertIn('"probe", serviceId', panel)
        self.assertIn('"open", serviceId', panel)
        self.assertIn("if (!visible || !desktopSupported", panel)
        self.assertIn("NATIVE PERSONAL-MESSAGE BACKEND // ", panel)
        self.assertIn("providerWebOpen = true;", social)
        self.assertIn("providerWebOpen = false;", social)
        # Contact and feed panels must disappear entirely during Discord;
        # the old source assertions unintentionally enforced opaque paint
        # above Vesktop even though only the app selector should remain.
        self.assertIn("visible: messagingWindow.menuOpen && !messagingWindow.discordSelected", social)
        self.assertIn("&& !providerAccessPanel.visible && !messagingWindow.providerDesktopManaged", social)
        self.assertIn("&& !telegramConnectPanel.visible && !providerAccessPanel.visible", social)
        self.assertNotIn("sendMessage(", panel)
        self.assertNotIn("password", panel.lower())

    def test_cli_probe_and_invalid_action_do_not_launch(self):
        result = subprocess.run([sys.executable, str(LAUNCHER), "probe", "viber"],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        obj = json.loads(result.stdout)
        self.assertEqual(obj["backendMode"], "UNSUPPORTED")
        self.assertFalse(obj["launched"])
        bad = subprocess.run([sys.executable, str(LAUNCHER), "open", "kakaotalk"],
                             capture_output=True, text=True, timeout=5)
        self.assertNotEqual(bad.returncode, 0)
        self.assertNotIn('"launched": true', bad.stdout.lower())

if __name__ == "__main__":
    unittest.main()
