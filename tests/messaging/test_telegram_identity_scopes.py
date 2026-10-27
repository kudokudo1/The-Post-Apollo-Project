"""Private universal/identity-specific Telegram API keys and isolated sessions.

All tests use synthetic credentials, fake Telethon and temporary XDG homes.
They never contact Telegram, open the real application, or read user sessions.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / "services/messaging/bridges/telegram/bridge.py"
LOGIN = ROOT / "services/messaging/bridges/telegram/login_ui.py"
ADAPTER = (ROOT / "services/messaging/adapters/TelegramAdapter.qml").read_text()
ROUTER = (ROOT / "services/messaging/SocialMessageRouter.qml").read_text()
IDENTITIES = (ROOT / "services/social/SocialIdentityStore.qml").read_text()
spec = importlib.util.spec_from_file_location("scoped_telegram_bridge", BRIDGE)
assert spec and spec.loader
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)

UNIVERSAL_HASH = "a" * 32
OVERRIDE_HASH = "b" * 32

FAKE_TELETHON = r'''
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from .errors import SessionPasswordNeededError

class TelegramClient:
    def __init__(self, session, api_id, api_hash, receive_updates=False):
        self.file = Path(session)
        scope = self.file.parent.name
        if scope == "identity-2":
            assert api_id == 234567 and api_hash == "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        else:
            assert api_id == 123456 and api_hash == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        self.file.write_text("FAKE SESSION ONLY -- NO TELEGRAM DATA")
        self.authorized = not sys.argv[0].endswith("login_ui.py")
    async def connect(self): return None
    async def disconnect(self): return None
    async def is_user_authorized(self): return self.authorized
    async def send_code_request(self, phone):
        assert phone == "+15551234567"
        return SimpleNamespace(phone_code_hash="offline-code-hash")
    async def sign_in(self, *, phone=None, code=None, phone_code_hash=None, password=None):
        assert phone == "+15551234567" and code == "12345"
        assert phone_code_hash == "offline-code-hash"
        self.authorized = True
'''
FAKE_ERRORS = "class SessionPasswordNeededError(Exception): pass\n"


class TelegramIdentityConfigTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory(prefix="apollo-telegram-scopes-")
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        pkg = self.root / "telethon"
        pkg.mkdir()
        (pkg / "__init__.py").write_text(textwrap.dedent(FAKE_TELETHON))
        (pkg / "errors.py").write_text(FAKE_ERRORS)
        self.data = self.root / "data"
        self.config = self.root / "config"
        self.env = {
            **os.environ,
            "PYTHONPATH": str(self.root),
            "XDG_DATA_HOME": str(self.data),
            "XDG_CONFIG_HOME": str(self.config),
            "POST_APOLLO_TELEGRAM_API_ID": "123456",
            "POST_APOLLO_TELEGRAM_API_HASH": UNIVERSAL_HASH,
        }
        self.patch_env = patch.dict(os.environ, self.env)
        self.patch_env.start()
        self.addCleanup(self.patch_env.stop)

    def cli(self, executable, *args, value="", env=None):
        return subprocess.run(
            [sys.executable, str(executable), *args],
            input=value, text=True, capture_output=True,
            env=self.env if env is None else env,
            timeout=10, check=False,
        )

    def configure(self, identity=None, api_id="123456", api_hash=UNIVERSAL_HASH):
        cmd = ["configure"]
        if identity is not None:
            cmd.extend(["--identity", identity])
        payload = json.dumps({"action":"configure", "apiId":api_id,
                              "apiHash":api_hash}) + "\n"
        return self.cli(LOGIN, *cmd, value=payload)

    def test_paths_and_validator_preserve_legacy_without_creation(self):
        self.assertEqual(bridge._session_path(),
                         self.data/"post-apollo/telegram/personal.session")
        self.assertEqual(bridge._app_config_path(),
                         self.config/"post-apollo/telegram/client.json")
        for identity in ("identity-1", "identity-2", "identity-999999999"):
            self.assertEqual(bridge._session_path(identity),
                             self.data/"post-apollo/telegram/identities"/identity/"personal.session")
            self.assertEqual(bridge._app_config_path(identity),
                             self.config/"post-apollo/telegram/identities"/identity/"client.json")
        self.assertFalse(self.data.exists())
        self.assertFalse(self.config.exists())

    def test_invalid_ids_do_not_read_credentials_or_create_files(self):
        invalid = ("", "../identity-1", "identity-0", "identity-01",
                   "identity-1000000000", "identity-2/", "identity-2\n",
                   "identity-2] focus", True, 5, [], {})
        for candidate in invalid:
            with self.subTest(value=candidate):
                with self.assertRaises(bridge.BridgeError):
                    bridge._session_path(candidate)
                with self.assertRaises(bridge.BridgeError):
                    bridge._app_config_path(candidate)
                with self.assertRaises(bridge.BridgeError):
                    bridge._credentials(candidate)
        for args in (
            ("health", "--identity", "../identity-2"),
            ("list", "--identity", "identity-0"),
            ("send", "-10023", "--identity", "identity-1/../identity-2"),
        ):
            outcome = self.cli(BRIDGE, *args)
            self.assertNotEqual(outcome.returncode, 0) if args[0] != "health" else self.assertEqual(outcome.returncode, 0)
            self.assertFalse(self.data.exists())
        for mode in ("phone", "qr", "configure"):
            res = self.cli(LOGIN, mode, "--identity", "../identity-2")
            self.assertEqual(res.returncode, 2)
            self.assertFalse(self.config.exists())
        self.assertFalse(self.data.exists())

    def test_universal_keys_saved_privately_and_scoped_credentials_fall_back(self):
        env = dict(self.env)
        env.pop("POST_APOLLO_TELEGRAM_API_ID")
        env.pop("POST_APOLLO_TELEGRAM_API_HASH")
        saved = self.cli(LOGIN, "configure",
                         value=json.dumps({"action":"configure",
                             "apiId":"123456","apiHash":UNIVERSAL_HASH})+"\n",
                         env=env)
        self.assertEqual(saved.returncode, 0, saved.stderr)
        self.assertEqual([json.loads(x)["state"] for x in saved.stdout.splitlines()],
                         ["APP_SAVED"])
        global_file = self.config/"post-apollo/telegram/client.json"
        self.assertEqual(stat.S_IMODE(global_file.stat().st_mode),0o600)
        self.assertEqual(stat.S_IMODE(global_file.parent.stat().st_mode),0o700)
        self.assertEqual(bridge._credentials("identity-1"),(123456,UNIVERSAL_HASH))
        self.assertEqual(bridge._credentials("identity-3"),(123456,UNIVERSAL_HASH))
        self.assertFalse((self.config/"post-apollo/telegram/identities").exists())
        self.assertNotIn(UNIVERSAL_HASH,saved.stdout+saved.stderr)

    def test_explicit_override_precedence_and_isolation(self):
        global_cfg=self.configure()
        self.assertEqual(global_cfg.returncode,0,global_cfg.stderr)
        override=self.configure("identity-2","234567",OVERRIDE_HASH)
        self.assertEqual(override.returncode,0,override.stderr)
        root = self.config/"post-apollo/telegram"
        self.assertEqual(json.loads((root/"client.json").read_text())["apiHash"], UNIVERSAL_HASH)
        scoped=root/"identities/identity-2/client.json"
        self.assertEqual(json.loads(scoped.read_text())["apiHash"], OVERRIDE_HASH)
        for folder in (root/"identities", scoped.parent):
            self.assertEqual(stat.S_IMODE(folder.stat().st_mode),0o700)
        self.assertEqual(stat.S_IMODE(scoped.stat().st_mode),0o600)
        self.assertEqual(bridge._credentials("identity-2"),(234567,OVERRIDE_HASH))
        self.assertEqual(bridge._credentials("identity-1"),(123456,UNIVERSAL_HASH))
        self.assertEqual(bridge._credentials(),(123456,UNIVERSAL_HASH))
        self.assertNotIn(OVERRIDE_HASH, override.stdout+override.stderr)

    def test_explicit_scoped_health_never_uses_legacy_session(self):
        self.assertEqual(self.configure("identity-2","234567",OVERRIDE_HASH).returncode,0)
        for args in (("health",), ("health","--identity","identity-1"),
                     ("health","--identity","identity-2")):
            outcome = self.cli(BRIDGE,*args)
            self.assertEqual(outcome.returncode,0,outcome.stderr)
            self.assertEqual(json.loads(outcome.stdout)["mode"],"READY")
            self.assertNotIn(OVERRIDE_HASH,outcome.stdout+outcome.stderr)
        legacy=self.data/"post-apollo/telegram/personal.session"
        first=self.data/"post-apollo/telegram/identities/identity-1/personal.session"
        second=self.data/"post-apollo/telegram/identities/identity-2/personal.session"
        self.assertEqual(len({legacy.resolve(),first.resolve(),second.resolve()}),3)
        for target in (legacy,first,second):
            self.assertTrue(target.exists())
            self.assertEqual(stat.S_IMODE(target.stat().st_mode),0o600)
        self.assertEqual(first.parent.stat().st_mode & 0o077,0)
        self.assertEqual(second.parent.stat().st_mode & 0o077,0)
        self.assertEqual(legacy.read_text(),"FAKE SESSION ONLY -- NO TELEGRAM DATA")

    def test_explicit_phone_pairing_only_touches_scoped_session(self):
        result=self.cli(LOGIN,"phone","--identity","identity-1",
                        value='{"action":"phone","value":"+15551234567"}\n'
                        '{"action":"code","value":"12345"}\n')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual([json.loads(line)["state"]
                          for line in result.stdout.splitlines()],
                         ["PHONE_REQUIRED","CODE_REQUIRED","READY"])
        scoped=self.data/"post-apollo/telegram/identities/identity-1/personal.session"
        self.assertTrue(scoped.exists())
        self.assertEqual(stat.S_IMODE(scoped.stat().st_mode),0o600)
        self.assertFalse((self.data/"post-apollo/telegram/personal.session").exists())
        self.assertNotIn("+15551234567",result.stdout+result.stderr)

    def test_unsafe_config_and_session_do_not_fall_back_or_get_repaired(self):
        self.assertEqual(self.configure("identity-2","234567",OVERRIDE_HASH).returncode,0)
        file=self.config/"post-apollo/telegram/identities/identity-2/client.json"
        file.chmod(0o644)
        with self.assertRaises(bridge.BridgeError):
            bridge._credentials("identity-2")
        self.assertEqual(bridge._credentials("identity-1"),(123456,UNIVERSAL_HASH))
        before=file.read_bytes()
        failed=self.configure("identity-2","234567",OVERRIDE_HASH)
        self.assertEqual(failed.returncode,2)
        self.assertEqual(file.read_bytes(),before)
        file.chmod(0o600)
        profile=self.data/"post-apollo/telegram/identities/identity-1"
        profile.mkdir(parents=True, mode=0o700)
        path=profile/"personal.session"
        path.symlink_to(self.root/"elsewhere")
        with self.assertRaises(bridge.BridgeError):
            bridge._telegram_client(identity_id="identity-1")
        self.assertFalse((self.root/"elsewhere").exists())

    def test_symlinked_identity_directory_blocks_override_without_external_write(self):
        root=self.config/"post-apollo/telegram"
        root.mkdir(parents=True,mode=0o700)
        outside=self.root/"outside"
        outside.mkdir(mode=0o700)
        (root/"identities").symlink_to(outside,target_is_directory=True)
        failed=self.configure("identity-3")
        self.assertEqual(failed.returncode,2)
        self.assertEqual(list(outside.iterdir()),[])
        self.assertFalse((root/"client.json").exists())

    def test_invalid_override_refused_instead_of_global_fallback(self):
        self.assertEqual(self.configure("identity-2","234567",OVERRIDE_HASH).returncode,0)
        file=self.config/"post-apollo/telegram/identities/identity-2/client.json"
        file.write_text('{"apiId":"not-numeric","apiHash":"bad"}')
        file.chmod(0o600)
        with self.assertRaises(bridge.BridgeError):
            bridge._credentials("identity-2")
        self.assertEqual(bridge._credentials("identity-1"),(123456,UNIVERSAL_HASH))

    def test_existing_native_ui_and_router_stay_shared_until_separate_review(self):
        self.assertIn('property string loginMode:',ADAPTER)
        self.assertIn('var commandArgs = [pythonPath, loginBridgePath, loginMode];',ADAPTER)
        self.assertIn('if (loginMode === "configure" && requestedAppKeyIdentityId !== "")',ADAPTER)
        self.assertIn('commandArgs.push("--identity", requestedAppKeyIdentityId)',ADAPTER)
        self.assertIn('loginProcess.command = commandArgs;',ADAPTER)
        self.assertIn('healthProcess.command = command(["health"])',ADAPTER)
        self.assertIn('active: router.appIndex === 2',ROUTER)
        self.assertIn('social-identities-v1.json',IDENTITIES)
        # The app-key editor may use --identity for CONFIGURE/STATUS,
        # while existing health, list, message and send operations must
        # continue using the original shared native Telegram session.
        self.assertIn('if (loginMode === "configure" && requestedAppKeyIdentityId !== "")',ADAPTER)
        self.assertIn('commandArgs.push("--identity", requestedAppKeyIdentityId)',ADAPTER)
        self.assertIn('healthProcess.command = command(["health"])',ADAPTER)
        self.assertIn('listProcess.command = command(["list"])',ADAPTER)
        self.assertIn('messageProcess.command = command(["messages"',ADAPTER)
        self.assertIn('sendProcess.command = command(["send"',ADAPTER)
        self.assertNotIn("--identity",ROUTER)
        self.assertIn('return base / "personal.session"',BRIDGE.read_text())
        self.assertIn('return base / "client.json"',BRIDGE.read_text())


if __name__ == "__main__":
    unittest.main()
