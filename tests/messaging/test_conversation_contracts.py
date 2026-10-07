from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "components" / "ConversationFeed.qml"
WRAPPER = ROOT / "widgets" / "messanger" / "ChatFeed.qml"
ADAPTER = ROOT / "services" / "hospital" / "HospitalRoomConversationAdapter.qml"
ROOM_CHAT = ROOT / "widgets" / "HospitalRoomChatView.qml"

assert SHARED.is_file(), SHARED

wrapper = WRAPPER.read_text()
assert 'import "../../components"' in wrapper
assert "ConversationFeed {" in wrapper
assert "SessionAdapter" not in wrapper
assert len(wrapper.splitlines()) < 20

shared = SHARED.read_text()
assert "session-cli" not in shared
assert "SessionAdapter" not in shared
assert "HospitalRoom" not in shared
assert "HospitalSession" not in shared

assert "property int messageTextFormat: Text.PlainText" in shared
assert 'property string emptyConversationLabel: "SELECT A CONTACT"' in shared
assert 'property string composerPlaceholder: "MESSAGE..."' in shared
assert 'property string sendLabel: "SEND"' in shared
assert 'property string sendingLabel: "SENDING"' in shared
assert "textFormat: chatFeed.messageTextFormat" in shared

print("conversation surface contracts: PASS")


assert ADAPTER.is_file(), ADAPTER
adapter = ADAPTER.read_text()
for field in (
    "property var conversations:",
    "property string selectedConversationId:",
    "property var messages:",
    "property bool messagesLoading:",
    "property bool sending:",
    "property int sendSuccessSerial:",
):
    assert field in adapter, field

assert "function loadMessages(conversationId)" in adapter
assert "function refreshMessages()" in adapter
assert "function sendMessage(conversationId, textValue)" in adapter
assert '"hospital",\n            "rooms"' in adapter
assert '"hospital",\n            "messages"' in adapter
assert '"message-append"' in adapter
assert "codex" not in adapter.lower()
assert "hermes" not in adapter.lower()

print("hospital conversation adapter contract: PASS")


assert ROOM_CHAT.is_file(), ROOM_CHAT
room_chat = ROOM_CHAT.read_text()
assert "ConversationFeed {" in room_chat
assert "HospitalRoomConversationAdapter {" in room_chat
assert "messageTextFormat: Text.MarkdownText" in room_chat
assert 'emptyConversationLabel: "SELECT A ROOM"' in room_chat
assert "adapter.sendMessage(conversationId, text)" in room_chat

print("hospital room chat view contract: PASS")
