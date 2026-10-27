"""Telegram application-key management entirely in the existing Social UI.

Synthetic settings and config-status tests only: no real API credentials,
Telegram network, profile migration, browser, window manager or live session.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "services/messaging/bridges/telegram/login_ui.py"
ADAPTER = (ROOT / "services/messaging/adapters/TelegramAdapter.qml").read_text()
PANEL = (ROOT / "widgets/messanger/TelegramConnectPanel.qml").read_text()
HOST = (ROOT / "widgets/messanger/MessagingW.qml").read_text()
SELECTOR = (ROOT / "widgets/messanger/AppSelector.qml").read_text()
BRIDGE = (ROOT / "services/messaging/bridges/telegram/bridge.py").read_text()

UNIVERSAL_HASH = "0" * 32
OVERRIDE_HASH = "f" * 32


class TelegramWidgetApplicationKeys(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="apollo-tg-inwidget-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.env = os.environ.copy()
        self.env["XDG_CONFIG_HOME"] = str(self.root / "config")
        self.env["XDG_DATA_HOME"] = str(self.root / "data")
        self.env.pop("POST_APOLLO_TELEGRAM_API_ID", None)
        self.env.pop("POST_APOLLO_TELEGRAM_API_HASH", None)

    def run_login(self, *args, stdin=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            input=stdin, text=True, capture_output=True,
            env=self.env, timeout=8, check=False,
        )

    def status(self, identity=None):
        args = ["status"]
        if identity is not None:
            args += ["--identity", identity]
        result = self.run_login(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(UNIVERSAL_HASH, result.stdout + result.stderr)
        self.assertNotIn(OVERRIDE_HASH, result.stdout + result.stderr)
        data = json.loads(result.stdout.strip())
        self.assertEqual(data["state"], "APP_KEY_STATUS")
        self.assertEqual(data["scope"], identity or "universal")
        self.assertEqual(set(data), {"state", "detail", "scope",
                                     "configuration", "source"})
        return data

    def configure(self, api_id="123456", api_hash=UNIVERSAL_HASH, identity=None):
        args = ["configure"]
        if identity is not None:
            args += ["--identity", identity]
        secret = json.dumps({"action":"configure","apiId":api_id,
                             "apiHash":api_hash}) + "\n"
        result = self.run_login(*args, stdin=secret)
        self.assertNotIn(api_hash, result.stdout + result.stderr)
        self.assertNotIn(secret, result.stdout + result.stderr)
        return result

    def test_no_config_returns_unavailable_without_creating_files(self):
        data = self.status()
        self.assertEqual((data["configuration"], data["source"]),
                         ("UNAVAILABLE", "UNAVAILABLE"))
        self.assertEqual(self.status("identity-2")["configuration"],
                         "UNAVAILABLE")
        self.assertFalse((self.root / "config").exists())
        self.assertFalse((self.root / "data").exists())

    def test_universal_save_and_identity_inheritance(self):
        saved = self.configure()
        self.assertEqual(saved.returncode, 0, saved.stderr)
        self.assertEqual(json.loads(saved.stdout)["state"], "APP_SAVED")
        universal = self.root/"config/post-apollo/telegram/client.json"
        self.assertTrue(universal.exists())
        self.assertEqual(stat.S_IMODE(universal.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(universal.parent.stat().st_mode), 0o700)
        self.assertEqual(self.status()["source"], "UNIVERSAL")
        identity = self.status("identity-1")
        self.assertEqual(identity["configuration"], "CONFIGURED")
        self.assertEqual(identity["source"], "UNIVERSAL")
        self.assertFalse((universal.parent/"identities").exists())
        self.assertFalse((self.root/"data").exists())

    def test_optional_identity_override_not_exposed_or_shared(self):
        self.assertEqual(self.configure().returncode, 0)
        result = self.configure("234567", OVERRIDE_HASH, "identity-2")
        self.assertEqual(result.returncode, 0, result.stderr)
        overridden = self.status("identity-2")
        self.assertEqual(overridden["source"], "IDENTITY_OVERRIDE")
        self.assertEqual(overridden["configuration"], "CONFIGURED")
        self.assertEqual(self.status("identity-1")["source"], "UNIVERSAL")
        self.assertEqual(self.status()["source"], "UNIVERSAL")
        root = self.root/"config/post-apollo/telegram"
        self.assertEqual(json.loads((root/"client.json").read_text())["apiHash"],
                         UNIVERSAL_HASH)
        key_file = root/"identities/identity-2/client.json"
        self.assertEqual(stat.S_IMODE(key_file.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(key_file.parent.stat().st_mode), 0o700)
        self.assertEqual(json.loads(key_file.read_text())["apiHash"], OVERRIDE_HASH)
        self.assertFalse((self.root/"data").exists())

    def test_unsafe_override_never_claims_universal_ready(self):
        self.assertEqual(self.configure().returncode, 0)
        self.assertEqual(self.configure("234567", OVERRIDE_HASH, "identity-2").returncode, 0)
        file = self.root/"config/post-apollo/telegram/identities/identity-2/client.json"
        file.chmod(0o644)
        self.assertEqual(self.status("identity-2")["configuration"], "UNAVAILABLE")
        self.assertEqual(self.status("identity-2")["source"], "UNAVAILABLE")
        self.assertEqual(self.status("identity-1")["source"], "UNIVERSAL")
        self.assertFalse((self.root/"data").exists())

    def test_invalid_scopes_cannot_create_or_reveal_keys(self):
        for value in ("../identity-1", "identity-0", "identity-1/../identity-2"):
            with self.subTest(identity=value):
                for mode in ("status","configure"):
                    r = self.run_login(mode,"--identity",value)
                    self.assertEqual(r.returncode, 2)
                    self.assertNotIn(UNIVERSAL_HASH, r.stdout+r.stderr)
        self.assertFalse((self.root/"config").exists())

    def test_configure_does_not_start_telegram_login(self):
        output=self.configure()
        self.assertEqual(output.returncode,0,output.stderr)
        self.assertEqual([x["state"] for x in map(json.loads,
            output.stdout.splitlines())],["APP_SAVED"])
        self.assertFalse((self.root/"data").exists())

    def test_in_widget_scope_controls_and_no_external_navigation(self):
        for mark in (
            'signal sharedTelegramApplicationKeysRequested(string keyScope)',
            'label: "CONFIGURE UNIVERSAL API KEYS"',
            'label: "OPTIONAL IDENTITY API KEYS"',
            'sharedTelegramApplicationKeysRequested("universal")',
            'sharedTelegramApplicationKeysRequested("identity")',
            'appSelector.identitySnapshot.writable',
        ):
            self.assertIn(mark, SELECTOR, mark)
        for mark in (
            "function openTelegramAppKeyEditor(keyScope)",
            "function closeTelegramAppKeyEditor()",
            "function invalidateTelegramKeyEditorScope()",
            'if (keyScope !== "universal" && keyScope !== "identity")',
            'appSelector.accountSelectedServiceId !== "telegram"',
            "onSharedTelegramApplicationKeysRequested:",
            "editApplicationKeys: messagingWindow.telegramAppKeyEditorOpen",
            "keyIdentityId: messagingWindow.telegramAppKeyEditorIdentityId",
            "onCloseKeyEditorRequested:",
            "messageRouter.telegramBackend.runningAppKeyIdentityId === \"\"",
            'messageRouter.telegramBackend.loginState === "APP_SAVED"',
        ):
            self.assertIn(mark, HOST, mark)
        self.assertEqual(HOST.count("FloatingWindow {"), 1)
        self.assertNotIn("Qt.openUrlExternally", PANEL)
        self.assertNotIn("QtWebEngine", PANEL)
        self.assertNotIn("subprocess.Popen", PANEL)
        self.assertIn('readonly property bool identityKeyEditor:', PANEL)
        self.assertIn('onVisibleChanged:', PANEL)
        self.assertIn('onKeyIdentityIdChanged: clearUnsubmittedAppKeys()', PANEL)
        self.assertIn('title: "BACK TO TELEGRAM"', PANEL)
        self.assertIn('title: "SAVE APP KEYS"', PANEL)
        self.assertIn('echoMode: TextInput.Password', PANEL)
        self.assertIn('title: "CHECK API CONFIGURATION"', PANEL)
        self.assertIn('panel.adapter.inspectApplicationKeys(', PANEL)
        self.assertIn('panel.adapter.saveApplicationKeys(', PANEL)
        self.assertNotIn('console.log', PANEL)

    def test_adapter_never_switches_shared_messages_or_logs_credentials(self):
        for mark in (
            'function inspectApplicationKeys(identityId)',
            'function saveApplicationKeys(apiId, apiHash, identityId)',
            'commandArgs.push("--identity", requestedAppKeyIdentityId)',
            'runningAppKeyIdentityId',
            'id: appKeyStatusProcess',
            'result.state !== "APP_KEY_STATUS"',
            'result.scope !== (adapter.appKeyConfigurationScope || "universal")',
            'appKeyConfigurationStatus = "UNAVAILABLE"',
            'adapter.runningAppKeyIdentityId === ""',
            'loginProcess.write', # QML syntax checks actual Process.write below
        ):
            if mark == 'loginProcess.write':
                self.assertIn('write(JSON.stringify({', ADAPTER)
            else:
                self.assertIn(mark, ADAPTER, mark)
        self.assertIn('if (adapter.backendMode === "READY")', ADAPTER)
        self.assertIn('adapter.loginDetail = "Universal application keys saved. "', ADAPTER)
        self.assertIn('adapter.requestedLoginMode = "qr";', ADAPTER)
        self.assertIn('Qt.callLater(function() { adapter.probe(); });', ADAPTER)
        self.assertIn('healthProcess.command = command(["health"])', ADAPTER)
        self.assertIn('listProcess.command = command(["list"])', ADAPTER)
        self.assertIn('messageProcess.command = command(["messages"', ADAPTER)
        self.assertIn('sendProcess.command = command(["send"', ADAPTER)
        self.assertNotIn('console.log', ADAPTER)
        self.assertNotIn('console.error', ADAPTER)
        self.assertIn('return base / "personal.session"', BRIDGE)
        self.assertIn('return base / "client.json"', BRIDGE)


if __name__ == "__main__":
    unittest.main()
