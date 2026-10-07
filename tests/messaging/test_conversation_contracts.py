from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "components" / "ConversationFeed.qml"
WRAPPER = ROOT / "widgets" / "messanger" / "ChatFeed.qml"

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
