"""Offline integration source contracts for Session + Telegram native Social routing.

These checks inspect source and mock provider data. They do not claim to
exercise a running Quickshell UI or live Telegram account.
"""
from pathlib import Path
from datetime import datetime, timezone
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[2]
router = (ROOT / "services/messaging/SocialMessageRouter.qml").read_text()
session = (ROOT / "services/messaging/SessionAdapter.qml").read_text()
telegram = (ROOT / "services/messaging/adapters/TelegramAdapter.qml").read_text()
social = (ROOT / "widgets/messanger/MessagingW.qml").read_text()
feed = (ROOT / "components/ConversationFeed.qml").read_text()
selector = (ROOT / "widgets/messanger/AppSelector.qml").read_text()
bridge_file = ROOT / "services/messaging/bridges/telegram/bridge.py"

class NativeIntegrationContracts(unittest.TestCase):
    def test_exact_native_indices_and_browser_isolation(self):
        self.assertIn('appIndex === 0 ? sessions', router)
        self.assertIn('appIndex === 2 ? telegram : null', router)
        self.assertIn('active: router.appIndex === 0', router)
        self.assertIn('active: router.appIndex === 2', router)
        self.assertIn('nativeChatSelected: activeAppIndex === 0 || activeAppIndex === 2', social)
        self.assertIn('import "adapters"', router)
        for label in ('"SESSIONS"', '"TELEGRAM"', '"DISCORD"', '"WHATSAPP"',
                      '"MESSENGER"', '"SIGNAL"', '"WECHAT"', '"LINE"', '"VIBER"',
                      '"KAKAOTALK"'):
            self.assertIn("name: " + label, selector)
        self.assertIn('readonly property bool externalSelected: discordSelected || xSelected', social)
        self.assertIn('if ((index >= 3 && index <= 13) || (index >= 16 && index <= 25))', social)

    def test_shared_ui_binds_to_router_without_direct_provider_commands(self):
        self.assertIn('SocialMessageRouter {', social)
        self.assertIn('appIndex: messagingWindow.activeAppIndex', social)
        self.assertIn('conversations: messageRouter.conversations', social)
        self.assertIn('messageRouter.loadMessages(selectedConversation.id)', social)
        self.assertIn('messageRouter.sendMessage(conversationId, text)', social)
        self.assertIn('messageRouter.sendSuccessSerial', social)
        self.assertIn('scopeId: messagingWindow.nativeChatSelected && conversation', social)
        self.assertIn('sendEnabled: messageRouter.sendEnabled', social)
        self.assertNotIn('sessionAdapter.sendMessage(', social)
        self.assertNotIn('TelegramAdapter {', social)
        self.assertIn('String(messageRouter.selectedConversationId) === String(contactList.selectedConversation.id)', social)

    def test_refuse_unsupported_and_unready_transports(self):
        self.assertIn('if (!nativeSelected || !selectedBackend || !sendEnabled || !conversationId', router)
        self.assertIn('String(conversationId) !== selectedConversationId', router)
        self.assertIn('telegram.backendMode === "READY"', router)
        self.assertIn('telegram.capabilities.sendText === true', router)
        self.assertIn('selectedBackend ? selectedBackend.conversations : []', router)
        self.assertIn('selectedBackend ? selectedBackend.messages : []', router)
        self.assertIn('active: router.appIndex === 2', router)
        self.assertIn('active: router.appIndex === 0', router)
        self.assertIn('TELEGRAM //', router)
        for unsupported in ('services/messaging/adapters/SignalAdapter.qml',
                            'services/messaging/adapters/MessengerAdapter.qml',
                            'services/messaging/adapters/ViberAdapter.qml'):
            src = (ROOT / unsupported).read_text()
            self.assertIn('backendMode: "UNSUPPORTED"', src)
            self.assertNotIn('Process {', src)

    def test_sessions_poll_only_when_selected(self):
        self.assertIn('property bool active: true', session)
        self.assertIn('running: adapter.active', session)
        self.assertIn('running: adapter.active && adapter.selectedConversationId !== ""', session)
        self.assertIn('if (!active || conversationProcess.running)', session)
        self.assertIn('if (!active || !selectedConversationId', session)
        self.assertIn('if (!active || !conversationId', session)
        self.assertIn('messageRequestConversationId = selectedConversationId', session)
        self.assertIn('String(adapter.messageRequestConversationId)', session)
        self.assertIn('String(adapter.selectedConversationId)', session)
        self.assertIn('messages = [];', session)

    def test_drafts_and_acknowledgements_are_scoped(self):
        for item in (
            'property bool sendEnabled: true',
            'property string scopeId: ""',
            'readonly property string effectiveScope:',
            'property var draftByScope: ({})',
            'property var pendingByScope: ({})',
            'draftByScope[previousScope] = messageInput.text;',
            'onEffectiveScopeChanged:',
            'const pending = pendingByScope[effectiveScope];',
            'if (!pending || sendSuccessSerial <= pending.serial)',
            'if (messageInput.text.trim() === pending.text)',
            'delete pendingByScope[effectiveScope];',
            'if (!conversation || !sendEnabled || sending || !effectiveScope)',
            'pendingByScope[effectiveScope] = { serial: sendSuccessSerial, text: text };',
            'onSendSuccessSerialChanged: finishConfirmedSend()',
            'enabled: !chatFeed.sending && chatFeed.sendEnabled',
            'property bool canSend: chatFeed.sendEnabled && !chatFeed.sending',
        ):
            self.assertIn(item, feed)

    def test_normalized_telegram_provider_fixture(self):
        spec = importlib.util.spec_from_file_location("telegram_integration_fixture", bridge_file)
        bridge = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bridge)
        moment = datetime(2026, 10, 24, 18, 0, tzinfo=timezone.utc)
        from types import SimpleNamespace
        obj = SimpleNamespace(id=91, message="hello", out=False, date=moment)
        row = bridge.normalize_message(obj, "27")
        self.assertEqual(row["sent_at"], int(moment.timestamp()))
        self.assertEqual(row["direction"], "incoming")
        self.assertEqual(row["conversationId"], "27")

if __name__ == "__main__":
    unittest.main()
