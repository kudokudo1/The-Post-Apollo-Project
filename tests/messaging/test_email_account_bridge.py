"""Offline contracts for the Social Email account inventory bridge."""
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
HOST = ROOT / "services/messaging/email/EmailAccountHost.py"
EXTENSION = ROOT / "services/messaging/email/extension"
compile(HOST.read_text(), str(HOST), "exec")

spec = importlib.util.spec_from_file_location("email_account_host", HOST)
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)
manifest = json.loads((EXTENSION / "manifest.json").read_text())
js = (EXTENSION / "background.js").read_text()

assert set(manifest["permissions"]) == {"accountsRead", "nativeMessaging"}
assert "messagesRead" not in manifest["permissions"]
assert "compose" not in manifest["permissions"]
assert "messenger.accounts.list()" in js
assert "sendNativeMessage" in js
assert "messenger.messages" not in js
assert "sendMessage(" not in js

source = {
    "type": "accounts.snapshot",
    "accounts": [{
        "id": "account1", "name": "Personal", "type": "imap",
        "identities": [{"email": "a@example.com", "unused": "secret"}],
        "folders": [{"id": "folder1", "name": "Inbox", "type": "inbox",
                     "messages": ["do not persist"]}],
        "password": "do not persist", "token": "do not persist",
    }],
}
normalized = host.normalize(source)
serialized = json.dumps(normalized)
assert normalized["schema"] == 1
assert normalized["accounts"][0]["identities"][0]["email"] == "a@example.com"
assert all(word not in serialized for word in ("secret", "token", "password", "do not persist"))
for bad in (
    {"type": "send", "accounts": []},
    {"type": "accounts.snapshot", "accounts": "not a list"},
    {"type": "accounts.snapshot", "accounts": [{}] * 65},
):
    try:
        host.normalize(bad)
        raise AssertionError("invalid command accepted")
    except ValueError:
        pass

with tempfile.TemporaryDirectory() as temporary:
    destination = Path(temporary) / "social-email" / "accounts.json"
    host.write_snapshot(normalized, destination)
    assert json.loads(destination.read_text()) == normalized
    assert os.stat(destination).st_mode & 0o777 == 0o600
    assert os.stat(destination.parent).st_mode & 0o777 == 0o700

frame = json.dumps(source).encode()
input_buffer = io.BytesIO(struct.pack("=I", len(frame)) + frame)
class FakeInput:
    buffer = input_buffer
with patch.object(host.sys, "stdin", FakeInput()):
    assert host.read_frame() == source

oversize = io.BytesIO(struct.pack("=I", host.MAX_FRAME_BYTES + 1))
class LargeInput:
    buffer = oversize
with patch.object(host.sys, "stdin", LargeInput()):
    try:
        host.read_frame()
        raise AssertionError("oversize frame accepted")
    except ValueError:
        pass

print("Social Email read-only account bridge contracts: PASS")
