from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "components" / "ConversationFeed.qml"
QMLDIR = ROOT / "components" / "qmldir"
WRAPPER = ROOT / "widgets" / "messanger" / "ChatFeed.qml"
ADAPTER = ROOT / "services" / "hospital" / "HospitalRoomConversationAdapter.qml"
ROOM_CHAT = ROOT / "widgets" / "HospitalRoomChatView.qml"
PROVIDERS = ROOT / "services" / "hospital" / "HospitalProviderService.qml"
DOCTORS = ROOT / "services" / "hospital" / "HospitalDoctorService.qml"

assert SHARED.is_file(), SHARED

qmldir = QMLDIR.read_text()
assert "ConversationFeed 1.0 ConversationFeed.qml" in qmldir

wrapper = WRAPPER.read_text()
assert "import qs.components" in wrapper
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
assert '"agent",\n            "session-create"' in adapter
assert '"agent",\n            "turn"' in adapter
assert '"--prompt-json-stdin"' in adapter
assert "stdinEnabled: true" in adapter
assert "turnProcess.write(" in adapter
assert "function compatibleSession(rows)" in adapter
assert '"hospital",\n            "sessions"' in adapter
assert "function discoverSession(roomIdValue, continueAfter)" in adapter
assert "function createSessionForPendingTurn()" in adapter
assert "function runPendingTurn()" in adapter
assert "Quickshell.execDetached" not in adapter
assert '"kitty"' not in adapter
assert "codex" not in adapter.lower()
assert "hermes" not in adapter.lower()

print("hospital live doctor adapter contract: PASS")


assert ROOM_CHAT.is_file(), ROOM_CHAT
room_chat = ROOM_CHAT.read_text()
assert "ConversationFeed {" in room_chat
assert "HospitalRoomConversationAdapter {" in room_chat
assert "messageTextFormat: Text.MarkdownText" in room_chat
assert 'emptyConversationLabel: "SELECT A ROOM"' in room_chat
assert "adapter.sendMessage(conversationId, text)" in room_chat

print("hospital room chat view contract: PASS")


adapter = ADAPTER.read_text()
assert "function bindRoom(roomValue)" in adapter
assert '"room-bind"' in adapter
assert "property bool bindingRoom:" in adapter
assert "property var queuedRoomBinding:" in adapter
assert "signal roomBound(var room)" in adapter

room_chat = ROOM_CHAT.read_text()
for field in (
    'property string repository: ""',
    'property string patientId: ""',
    'property string team: ""',
    'property string branch: ""',
    'property string bedPath: ""',
    'property string assignmentId: ""',
):
    assert field in room_chat, field
assert "function roomBinding()" in room_chat
assert "adapter.bindRoom(root.roomBinding())" in room_chat

print("hospital room binding contract: PASS")


room_chat = ROOM_CHAT.read_text()
assert 'property string providerId: ""' in room_chat
assert 'property string doctorId: ""' in room_chat
assert "readonly property string activeSessionId: adapter.activeSessionId" in room_chat
assert "providerId: root.providerId" in room_chat
assert "doctorId: root.doctorId" in room_chat
assert "workingDirectory: root.bedPath" in room_chat
assert 'return root.providerId ? "READY TO CONNECT" : "ROOM CHAT";' in room_chat

print("hospital live doctor chat view contract: PASS")


assert PROVIDERS.is_file(), PROVIDERS
providers = PROVIDERS.read_text()
assert '"agent",\n            "providers"' in providers
assert "property var providers:" in providers
assert "function providerById(value)" in providers
assert "readonly property int readyCount:" in providers
assert "codex" not in providers.lower()
assert "hermes" not in providers.lower()
assert "Quickshell.execDetached" not in providers

assert DOCTORS.is_file(), DOCTORS
doctors = DOCTORS.read_text()
assert '"hospital",\n            "doctors"' in doctors
assert '"doctor-put"' in doctors
assert "function doctorById(value)" in doctors
assert "function saveDoctor(idValue, nameValue, roleValue, statusValue)" in doctors
assert "function releaseDoctor(idValue)" in doctors
assert "provider" not in doctors.lower()

print("hospital staffing services contracts: PASS")


adapter = ADAPTER.read_text()
assert 'const roomProviderId = String(room.providerId || "").trim();' in adapter
assert '"--provider-id"' in adapter
assert "args.push(roomProviderId);" in adapter

room_chat = ROOM_CHAT.read_text()
assert "readonly property string storedProviderId:" in room_chat
assert "readonly property string effectiveProviderId:" in room_chat
assert "String(root.providerId || root.storedProviderId || "").trim()" in room_chat
assert "providerId: root.effectiveProviderId" in room_chat
assert "onProviderIdChanged: scheduleRoomBinding()" in room_chat

print("hospital Room provider persistence contracts: PASS")
