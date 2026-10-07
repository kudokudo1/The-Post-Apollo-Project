from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "components" / "ConversationFeed.qml"
WRAPPER = ROOT / "widgets" / "messanger" / "ChatFeed.qml"


def test_shared_conversation_surface_exists():
    assert SHARED.is_file()


def test_social_chat_is_compatibility_wrapper():
    text = WRAPPER.read_text()
    assert 'import "../../components"' in text
    assert "ConversationFeed {" in text
    assert "SessionAdapter" not in text
    assert len(text.splitlines()) < 20


def test_shared_surface_is_transport_agnostic():
    text = SHARED.read_text()
    assert "session-cli" not in text
    assert "SessionAdapter" not in text
    assert "Hospital" not in text


def test_shared_surface_exposes_host_rendering_hooks():
    text = SHARED.read_text()
    assert "property int messageTextFormat: Text.PlainText" in text
    assert 'property string emptyConversationLabel: "SELECT A CONTACT"' in text
    assert 'property string composerPlaceholder: "MESSAGE..."' in text
    assert 'property string sendLabel: "SEND"' in text
    assert 'property string sendingLabel: "SENDING"' in text
    assert "textFormat: chatFeed.messageTextFormat" in text
