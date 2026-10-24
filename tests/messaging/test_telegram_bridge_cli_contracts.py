"""Subprocess-level Telegram bridge smoke with a fake Telethon module.

The CLI, stdin envelope, output JSON, authorization gates and protected session
path are exercised without network access or any real account/API credentials.
"""
from __future__ import annotations

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
BRIDGE = ROOT / "services/messaging/bridges/telegram/bridge.py"

# A tiny *fake* dependency, placed in an isolated PYTHONPATH. Never import the
# actual Telethon library in these tests; no Telegram network connection occurs.
FAKE_TELETHON = r'''
import os
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

class TelegramClient:
    def __init__(self, session, api_id, api_hash, receive_updates=False):
        assert api_id == 123456
        assert api_hash == "fake-for-tests-only"
        assert receive_updates is False
        self.session = Path(session)
        self.session.write_text("FAKE SESSION -- NOT VALID TELEGRAM CREDENTIALS")
        stamp = datetime(2026, 10, 24, 18, tzinfo=timezone.utc)
        self.dialog = SimpleNamespace(
            id=-100123, name="Offline Group", is_group=True,
            is_channel=False, entity="group",
            unread_count=3, message=SimpleNamespace(message="latest", date=stamp)
        )
    async def connect(self):
        return None
    async def disconnect(self):
        return None
    async def is_user_authorized(self):
        return os.environ.get("FAKE_TELEGRAM_UNAUTHORIZED", "") != "1"
    async def get_dialogs(self, *, limit):
        assert limit is None
        return [self.dialog]
    async def get_messages(self, entity, *, limit):
        assert entity == "group"
        assert 1 <= limit <= 100
        return [
            SimpleNamespace(
                id=2, message="new", out=True,
                date=datetime(2026, 10, 24, 18, 0, 5, tzinfo=timezone.utc)
            ),
            SimpleNamespace(
                id=1, message="old", out=False,
                date=datetime(2026, 10, 24, 18, tzinfo=timezone.utc)
            ),
        ]
    async def send_message(self, entity, body, *, parse_mode):
        assert entity == "group"
        assert parse_mode is None
        assert isinstance(body, str)
        if os.environ.get("FAKE_TELEGRAM_FAIL_SEND") == "1":
            raise RuntimeError("FAKE provider failure")
        return SimpleNamespace(id=42)
'''


class TelegramCLISmoke(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="social-tg-cli-")
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        (root / "telethon.py").write_text(textwrap.dedent(FAKE_TELETHON))
        self.data_root = root / "xdg"
        self.env = os.environ.copy()
        self.env["PYTHONPATH"] = str(root)
        self.env["XDG_DATA_HOME"] = str(self.data_root)
        self.env["POST_APOLLO_TELEGRAM_API_ID"] = "123456"
        self.env["POST_APOLLO_TELEGRAM_API_HASH"] = "fake-for-tests-only"
        self.env.pop("FAKE_TELEGRAM_UNAUTHORIZED", None)
        self.env.pop("FAKE_TELEGRAM_FAIL_SEND", None)

    def run_bridge(self, *args, payload=None, env=None):
        return subprocess.run(
            [sys.executable, str(BRIDGE), *args],
            input=payload,
            text=True,
            capture_output=True,
            env=env or self.env,
            timeout=8,
            check=False,
        )

    def test_ready_health_is_noninteractive_and_session_is_private(self):
        result = self.run_bridge("health")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["mode"], "READY")
        session = self.data_root / "post-apollo" / "telegram" / "personal.session"
        self.assertTrue(session.exists())
        self.assertEqual(stat.S_IMODE(session.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(session.parent.stat().st_mode), 0o700)
        self.assertNotIn("fake-for-tests-only", result.stdout + result.stderr)

    def test_list_uses_normalized_personal_conversations(self):
        result = self.run_bridge("list")
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = json.loads(result.stdout)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "-100123")
        self.assertEqual(rows[0]["serviceId"], "telegram")
        self.assertEqual(rows[0]["type"], "group")
        self.assertEqual(rows[0]["unreadCount"], 3)

    def test_message_history_is_oldest_first(self):
        result = self.run_bridge("messages", "-100123", "--limit", "100")
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = json.loads(result.stdout)
        self.assertEqual([r["id"] for r in rows], ["1", "2"])
        self.assertEqual([r["direction"] for r in rows], ["incoming", "outgoing"])
        self.assertEqual(rows[0]["conversationId"], "-100123")
        self.assertLess(rows[0]["sent_at"], rows[1]["sent_at"])

    def test_send_reads_body_from_stdin_not_argv(self):
        body = "plain **not markdown** with spaces"
        result = self.run_bridge("send", "-100123", payload=json.dumps({"text": body}) + "\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"sent": True, "messageId": "42"})
        self.assertNotIn(body, result.stdout + result.stderr)

    def test_send_rejection_does_not_emit_confirmation(self):
        for bad in ('not-json\n', '{"wrong": 1}\n', '{"text": "   "}\n'):
            with self.subTest(payload=bad):
                result = self.run_bridge("send", "-100123", payload=bad)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(result.stdout.strip())
        result = self.run_bridge("send", "-1", payload='{"text":"hello"}\n')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(result.stdout.strip())

    def test_failed_provider_does_not_return_success(self):
        env = dict(self.env, FAKE_TELEGRAM_FAIL_SEND="1")
        result = self.run_bridge("send", "-100123", payload='{"text":"test"}\n', env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(result.stdout.strip())
        self.assertNotIn("FAKE provider failure", result.stderr)

    def test_missing_credentials_and_unlinked_account_gate(self):
        env = dict(self.env)
        env.pop("POST_APOLLO_TELEGRAM_API_ID", None)
        result = self.run_bridge("health", env=env)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["mode"], "AUTH_REQUIRED")
        env = dict(self.env, FAKE_TELEGRAM_UNAUTHORIZED="1")
        result = self.run_bridge("health", env=env)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["mode"], "AUTH_REQUIRED")
        result = self.run_bridge("list", env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(result.stdout.strip())

    def test_no_automatic_login(self):
        # subprocess.run uses pipes, not an interactive TTY. Login must refuse.
        result = self.run_bridge("login")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("interactive terminal", result.stderr)
        self.assertFalse(result.stdout.strip())


if __name__ == "__main__":
    unittest.main()
