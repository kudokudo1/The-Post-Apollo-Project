"""Offline, no-credential Telegram bridge/provider contract tests."""
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace as Object
from unittest import IsolatedAsyncioTestCase
import unittest

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / 'services/messaging/bridges/telegram/bridge.py'
QML = ROOT / 'services/messaging/adapters/TelegramAdapter.qml'
spec = importlib.util.spec_from_file_location('telegram_bridge', BRIDGE)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)

class FakeClient:
    def __init__(self):
        ts = datetime(2026, 10, 24, 13, tzinfo=timezone.utc)
        self.dialog = Object(id=-100481, name='Family', is_group=True, is_channel=False, entity='peer',
                             unread_count=2, message=Object(message='last', date=ts))
        self.sent = []
    async def get_dialogs(self, *, limit):
        assert limit is None
        return [self.dialog]
    async def get_messages(self, entity, *, limit):
        assert entity == 'peer' and limit == 100
        return [Object(id=2, message='second', out=True, date=datetime(2026,10,24,13,0,5,tzinfo=timezone.utc)),
                Object(id=1, message='first', out=False, date=datetime(2026,10,24,13,tzinfo=timezone.utc))]
    async def send_message(self, entity, body, *, parse_mode):
        assert parse_mode is None
        self.sent.append((entity, body))
        return Object(id=3)

class TelegramContract(IsolatedAsyncioTestCase):
    async def test_conversations(self):
        row=(await bridge.list_conversations(FakeClient()))[0]
        self.assertEqual(row['id'], '-100481')
        self.assertEqual(row['serviceId'], 'telegram')
        self.assertEqual(row['unreadCount'], 2)
        self.assertEqual(row['displayNameInProfile'], 'Family')
        self.assertEqual(row['type'], 'group')
    async def test_history(self):
        rows=await bridge.list_messages(FakeClient(), '-100481')
        self.assertEqual([r['id'] for r in rows], ['1','2'])
        self.assertEqual([r['direction'] for r in rows], ['incoming','outgoing'])
        self.assertEqual(rows[0]['conversationId'], '-100481')
        self.assertEqual(rows[1]['body'], 'second')
        self.assertIsInstance(rows[0]['sent_at'], int)
    async def test_send_ack(self):
        client=FakeClient()
        result=await bridge.send_text(client, '-100481', 'hello **not markup**')
        self.assertEqual(result, {'sent': True, 'messageId': '3'})
        self.assertEqual(client.sent, [('peer', 'hello **not markup**')])
    async def test_invalid_send_and_conversation(self):
        client=FakeClient()
        with self.assertRaises(bridge.BridgeError):
            await bridge.send_text(client,'-100481','   ')
        with self.assertRaises(bridge.BridgeError):
            await bridge.send_text(client,'-100481','a' * 4097)
        with self.assertRaises(bridge.BridgeError):
            await bridge.send_text(client,'-1','hello')
        self.assertEqual(client.sent, [])

class QmlContract(unittest.TestCase):
    def test_qml_surface(self):
        src=QML.read_text()
        for needle in ('readonly property string serviceId: "telegram"', 'property bool active: false',
            'property var conversations: []', 'property var messages: []', 'property bool loading: false',
            'property bool messagesLoading: false', 'property bool sending: false',
            'property string backendMode:', 'property string backendDetail:',
            'property string error:', 'property string messagesError:', 'property string sendError:',
            'property int sendSuccessSerial: 0', 'readonly property var capabilities:',
            'function refresh()', 'function loadMessages(conversationId)', 'function refreshMessages()',
            'function sendMessage(conversationId, text)', 'sendSuccessSerial += 1',
            'if (!adapter.active', 'adapter.activationSerial', 'requestedConversationId === adapter.selectedConversationId',
            'stdinEnabled: true', 'onStarted:', 'write(JSON.stringify({ text: adapter.pendingSendText }) + "\\n");'):
            self.assertIn(needle,src)
        self.assertNotIn('Component.onCompleted: adapter.refresh()',src)
        self.assertNotIn('sendProcess.command = command(["send", String(conversationId), body])',src)
        self.assertIn('adapter.active && adapter.backendMode === "READY"',src)
    def test_health_offline_without_credentials(self):
        env=os.environ.copy()
        env.pop('POST_APOLLO_TELEGRAM_API_ID',None)
        env.pop('POST_APOLLO_TELEGRAM_API_HASH',None)
        result=subprocess.run([sys.executable,str(BRIDGE),'health'],env=env,capture_output=True,text=True,timeout=8)
        self.assertEqual(result.returncode,0,result.stderr)
        j=json.loads(result.stdout)
        self.assertEqual(j['mode'],'AUTH_REQUIRED')
        self.assertNotIn('token',result.stdout.lower())
    def test_whatsapp_is_blocked(self):
        path=ROOT / 'services/messaging/bridges/whatsapp/FEASIBILITY.md'
        # Different PR; only present in the WhatsApp worktree.
        if path.exists():
            self.assertIn('BLOCKED / RESEARCH',path.read_text())

if __name__=='__main__':
    unittest.main()
