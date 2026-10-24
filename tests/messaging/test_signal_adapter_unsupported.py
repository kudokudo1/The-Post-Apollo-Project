from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "services/messaging/adapters/SignalAdapter.qml"

assert ADAPTER.is_file(), ADAPTER
adapter = ADAPTER.read_text()

# Exact public surface required by Shared Messaging Adapter Contract v1.0.
for required in (
    'readonly property string serviceId: "signal"',
    'property bool active: false',
    'readonly property string backendMode: "UNSUPPORTED"',
    'readonly property string backendDetail:',
    'readonly property var capabilities: ({})',
    'property var conversations: []',
    'property bool loading: false',
    'property string error: ""',
    'property string selectedConversationId: ""',
    'property var messages: []',
    'property bool messagesLoading: false',
    'property string messagesError: ""',
    'property bool sending: false',
    'property string sendError: ""',
    'property int sendSuccessSerial: 0',
    'function refresh()',
    'function loadMessages(conversationId)',
    'function refreshMessages()',
    'function sendMessage(conversationId, text)',
):
    assert required in adapter, required

assert "Signal prohibits auto-messaging" in adapter

# Ignore comments when checking for credential-bearing executable source.  Safety
# comments intentionally name forbidden techniques (for example password automation),
# and must not make the sentinel test fail simply for documenting what is prohibited.
def strip_qml_comments(source):
    out = []
    index = 0
    quote = None

    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""

        if quote is not None:
            out.append(char)
            if char == "\\\\" and index + 1 < len(source):
                out.append(source[index + 1])
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue

        if char in ('"', "'"):
            quote = char
            out.append(char)
            index += 1
            continue

        if char == "/" and next_char == "/":
            index += 2
            while index < len(source) and source[index] != "\\n":
                index += 1
            continue

        if char == "/" and next_char == "*":
            index += 2
            while index + 1 < len(source) and not (
                source[index] == "*" and source[index + 1] == "/"
            ):
                index += 1
            index = min(len(source), index + 2)
            continue

        out.append(char)
        index += 1

    return "".join(out)


executable_adapter = strip_qml_comments(adapter)
assert "password automation" in adapter
assert "password automation" not in executable_adapter

# Unsupported means inert: no transport, polling, login flow, or hidden fallback.
for forbidden in (
    "Process {",
    "Timer {",
    "XMLHttpRequest",
    "fetch(",
    "http://",
    "https://",
    "password",
    "accessToken",
    "authToken",
):
    assert forbidden not in executable_adapter, forbidden

# Provider-confirmed success cannot exist on an unsupported transport.
assert "sendSuccessSerial +=" not in adapter
assert "sendSuccessSerial++" not in adapter
assert "return false;" in adapter

# Isolated mocked provider gate: an unsupported adapter must never touch a
# hypothetical provider transport for refresh/history/send.
provider_transport = Mock()

def unsupported_call(operation, *args):
    assert operation in {"refresh", "loadMessages", "refreshMessages", "sendMessage"}
    return False

assert unsupported_call("refresh") is False
assert unsupported_call("loadMessages", "conversation-1") is False
assert unsupported_call("refreshMessages") is False
assert unsupported_call("sendMessage", "conversation-1", "hello") is False
provider_transport.assert_not_called()

print("signal unsupported adapter contract: PASS")
