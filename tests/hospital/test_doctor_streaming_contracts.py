from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "services" / "hospital" / "HospitalRoomConversationAdapter.qml"
CHAT = ROOT / "widgets" / "HospitalRoomChatView.qml"

assert ADAPTER.is_file(), ADAPTER
assert CHAT.is_file(), CHAT

adapter = ADAPTER.read_text()
for needle in (
    'property var liveStreamEvents: []',
    'property string liveStreamText: ""',
    'property string liveStreamError: ""',
    'property bool liveStreamLoading: false',
    'property string liveStreamSessionId: ""',
    'function clearLiveStream()',
    'function rebuildLiveStream(rows)',
    'function refreshLiveStream()',
    'eventType !== "provider.stream"',
    'streamName !== "stdout"',
    '"hospital",',
    '"events",',
    '"160",',
    'id: liveStreamProcess',
    'id: liveStreamTimer',
    'interval: 350',
    'adapter.sending',
    'adapter.activeSessionId.length > 0',
    'Qt.callLater(adapter.refreshLiveStream)',
):
    assert needle in adapter, needle

assert adapter.index('id: liveStreamProcess') < adapter.index('id: turnProcess')
assert 'clearLiveStream();\n        sending = true;' in adapter

chat = CHAT.read_text()
for needle in (
    'readonly property var displayMessages:',
    'adapter.sending && adapter.liveStreamText',
    '"live-doctor-stream-"',
    'direction: "incoming"',
    'messageType: "provider_stream"',
    'transient: true',
    'body: "LIVE // " + adapter.liveStreamText',
    'return adapter.liveStreamText ? "STREAMING" : "SENDING";',
    'messages: root.roomId ? root.displayMessages : []',
):
    assert needle in chat, needle

assert 'messages: root.roomId ? adapter.messages : []' not in chat

print("hospital Doctor streaming contracts: PASS")
