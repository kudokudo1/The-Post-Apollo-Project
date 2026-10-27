"""Credential-free account setup tests for the Telegram in-menu pairing subprocess."""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "services/messaging/bridges/telegram/login_ui.py"
ADAPTER = ROOT / "services/messaging/adapters/TelegramAdapter.qml"
PANEL = ROOT / "widgets/messanger/TelegramConnectPanel.qml"
SOCIAL = ROOT / "widgets/messanger/MessagingW.qml"
ROUTER = ROOT / "services/messaging/SocialMessageRouter.qml"

FAKE_TELETHON = r'''
import os
from pathlib import Path
from types import SimpleNamespace
from . import errors

class Login:
    url = "tg://login?token=fake-qr-token"
    async def wait(self):
        if os.environ.get("FAKE_QR_2FA") == "1":
            raise errors.SessionPasswordNeededError()
        self.client.authorized = True
    async def recreate(self):
        return None
    def __init__(self, client):
        self.client = client

class TelegramClient:
    def __init__(self, session, api_id, api_hash, receive_updates=False):
        assert api_id == 123456
        assert api_hash == "1234567890abcdef1234567890abcdef"
        self.authorized = False
        self.receive_updates = receive_updates
        self.session = Path(session)
        self.session.write_text("FAKE SESSION")
    async def connect(self):
        return None
    async def disconnect(self):
        return None
    async def is_user_authorized(self):
        return self.authorized
    async def qr_login(self):
        assert self.receive_updates is True, "QR requires Telegram update delivery"
        return Login(self)
    async def send_code_request(self, phone):
        assert phone == "+15551234567"
        return SimpleNamespace(phone_code_hash="fake-code-hash")
    async def sign_in(self, *, phone=None, code=None, phone_code_hash=None, password=None):
        if password is not None:
            if password != "secure-example-only":
                raise ValueError("bad password")
            self.authorized = True
            return
        if code != "12345":
            raise ValueError("bad code")
        if os.environ.get("FAKE_PHONE_2FA") == "1":
            raise errors.SessionPasswordNeededError()
        assert phone == "+15551234567"
        assert phone_code_hash == "fake-code-hash"
        self.authorized = True
'''
FAKE_ERRORS = "class SessionPasswordNeededError(Exception): pass\n"
FAKE_QR = r'''
class QRCode:
    def __init__(self, border):
        assert border == 4
        self.url = None
    def add_data(self, url):
        assert url.startswith("tg://login?token=")
        self.url = url
    def make(self, fit):
        assert fit is True
    def get_matrix(self):
        assert self.url
        # Fake 29x29 QR grid including a white quiet border.
        return [
            [False] * 29 if row < 4 or row >= 25 else
            [False] * 4 + [((row + col) % 3) == 0 for col in range(21)] + [False] * 4
            for row in range(29)
        ]
'''


class TelegramMenuLoginContracts(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="post-apollo-telegram-menu-")
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        pkg = root / "telethon"
        pkg.mkdir()
        (pkg / "__init__.py").write_text(textwrap.dedent(FAKE_TELETHON))
        (pkg / "errors.py").write_text(FAKE_ERRORS)
        (root / "qrcode.py").write_text(textwrap.dedent(FAKE_QR))
        self.root = root
        self.env = os.environ.copy()
        self.env["PYTHONPATH"] = str(root)
        self.env["XDG_DATA_HOME"] = str(root / "data")
        self.env["XDG_CONFIG_HOME"] = str(root / "config")
        self.env["POST_APOLLO_TELEGRAM_API_ID"] = "123456"
        self.env["POST_APOLLO_TELEGRAM_API_HASH"] = "1234567890abcdef1234567890abcdef"

    def run_bridge(self, mode, input="", env=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT), mode],
            input=input, capture_output=True, text=True,
            env=env or self.env, timeout=10, check=False,
        )

    def events(self, result):
        return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]

    def test_qr_is_generated_only_after_explicit_command(self):
        result = self.run_bridge("qr")
        self.assertEqual(result.returncode, 0, result.stderr)
        events = self.events(result)
        self.assertEqual([e["state"] for e in events], ["QR_READY", "READY"])
        rows = events[0]["modules"]
        self.assertEqual(len(rows), 29)
        self.assertTrue(all(len(row) == 29 for row in rows))
        self.assertTrue(all(set(row) <= {"0", "1"} for row in rows))
        self.assertEqual(rows[0], "0" * 29)
        self.assertEqual(rows[-1], "0" * 29)
        self.assertNotIn("image", events[0])
        self.assertNotIn("fake-qr-token", result.stdout + result.stderr)
        self.assertNotIn("1234567890abcdef", result.stdout + result.stderr)

    def test_qr_two_step_password_in_same_process(self):
        env = dict(self.env, FAKE_QR_2FA="1")
        result = self.run_bridge(
            "qr", '{"action":"password","value":"secure-example-only"}\n', env=env
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([e["state"] for e in self.events(result)],
                         ["QR_READY", "PASSWORD_REQUIRED", "READY"])
        self.assertNotIn("secure-example-only", result.stdout + result.stderr)

    def test_phone_and_code_flow(self):
        input_data = ('{"action":"phone","value":"+15551234567"}\n'
                      '{"action":"code","value":"12345"}\n')
        result = self.run_bridge("phone", input_data)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([e["state"] for e in self.events(result)],
                         ["PHONE_REQUIRED", "CODE_REQUIRED", "READY"])
        self.assertNotIn("+15551234567", result.stdout + result.stderr)
        self.assertNotIn("12345", result.stdout + result.stderr)

    def test_phone_2fa_flow(self):
        env = dict(self.env, FAKE_PHONE_2FA="1")
        input_data = ('{"action":"phone","value":"+15551234567"}\n'
                      '{"action":"code","value":"12345"}\n'
                      '{"action":"password","value":"secure-example-only"}\n')
        result = self.run_bridge("phone", input_data, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([e["state"] for e in self.events(result)],
                         ["PHONE_REQUIRED", "CODE_REQUIRED", "PASSWORD_REQUIRED", "READY"])

    def test_invalid_code_does_not_fake_ready(self):
        input_data = ('{"action":"phone","value":"+15551234567"}\n'
                      '{"action":"code","value":"00000"}\n'
                      '{"action":"code","value":"00000"}\n'
                      '{"action":"code","value":"00000"}\n')
        result = self.run_bridge("phone", input_data)
        self.assertNotEqual(result.returncode, 0)
        states = [e["state"] for e in self.events(result)]
        self.assertEqual(states.count("INVALID_CODE"), 3)
        self.assertNotIn("READY", states)

    def test_app_keys_only_stored_with_explicit_config_request(self):
        env = dict(self.env)
        env.pop("POST_APOLLO_TELEGRAM_API_ID")
        env.pop("POST_APOLLO_TELEGRAM_API_HASH")
        blocked = self.run_bridge("qr", env=env)
        self.assertEqual([e["state"] for e in self.events(blocked)], ["APP_REQUIRED"])
        cfg = self.root / "config/post-apollo/telegram/client.json"
        self.assertFalse(cfg.exists())
        keys = '{"action":"configure","apiId":"123456","apiHash":"1234567890abcdef1234567890abcdef"}\n'
        saved = self.run_bridge("configure", keys, env=env)
        self.assertEqual(saved.returncode, 0, saved.stderr)
        self.assertEqual([e["state"] for e in self.events(saved)], ["APP_SAVED"])
        self.assertEqual(stat.S_IMODE(cfg.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(cfg.parent.stat().st_mode), 0o700)
        self.assertNotIn("1234567890abcdef", saved.stdout + saved.stderr)
        # The existing bridge reads the same private configuration.
        recheck = self.run_bridge("qr", env=env)
        self.assertEqual([e["state"] for e in self.events(recheck)], ["QR_READY", "READY"])

    def test_invalid_credentials_rejected_without_storage(self):
        result = self.run_bridge(
            "configure",
            '{"action":"configure","apiId":"123456","apiHash":"not-a-real-hash"}\n'
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.events(result)[-1]["state"], "ERROR")
        cfg = self.root / "config/post-apollo/telegram/client.json"
        self.assertFalse(cfg.exists())

    def test_source_connects_setup_panel_without_terminal(self):
        adapter = ADAPTER.read_text()
        panel = PANEL.read_text()
        social = SOCIAL.read_text()
        router = ROUTER.read_text()
        for value in (
            'readonly property string loginBridgePath:',
            'function startLogin(mode)',
            'function cancelLogin()',
            'function submitPhone(value)',
            'function submitCode(value)',
            'function submitPassword(value)',
            'function saveApplicationKeys(apiId, apiHash, identityId)',
            'stdinEnabled: true',
            'stdout: SplitParser',
            'onRead: function(line)',
            'onActiveChanged:',
        ):
            self.assertIn(value, adapter)
        self.assertIn('TelegramConnectPanel {', social)
        self.assertIn('adapter: messageRouter.telegramBackend', social)
        self.assertIn('messageRouter.telegramNeedsSetup', social)
        self.assertIn('readonly property bool telegramNeedsSetup:', router)
        self.assertIn('echoMode: TextInput.Password', panel)
        self.assertIn('CONNECT WITH QR', panel)
        self.assertIn('Canvas {', panel)
        self.assertIn('const rows = panel.qrMatrixRows || [];', panel)
        self.assertIn('qrCanvas.requestPaint()', panel)
        self.assertIn('property var qrModules: []', adapter)
        self.assertNotIn('data:image/png', panel)
        self.assertNotIn('qrSource', panel)
        self.assertNotIn('base64', (ROOT / "services/messaging/bridges/telegram/login_ui.py").read_text())
        self.assertIn('USE PHONE NUMBER', panel)
        self.assertIn('SAVE APP KEYS', panel)
        self.assertNotIn('console.log', adapter)
        self.assertNotIn('console.log', panel)
        self.assertNotIn('apiHashInput.text)', adapter)


if __name__ == "__main__":
    unittest.main()
