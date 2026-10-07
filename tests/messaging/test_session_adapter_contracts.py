import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "services" / "messaging" / "SessionAdapter.qml"
BRIDGE = ROOT / "services" / "messaging" / "SessionBridge.py"


assert ADAPTER.is_file(), ADAPTER
assert BRIDGE.is_file(), BRIDGE

adapter = ADAPTER.read_text()
bridge = BRIDGE.read_text()

# The bridge itself must remain valid Python without importing optional
# SQLCipher dependencies at module load time.
compile(bridge, str(BRIDGE), "exec")

assert "/var/home/mapple" not in adapter
assert 'Quickshell.shellPath("services/messaging/SessionBridge.py")' in adapter
assert 'property string backendMode: "PROBING"' in adapter
assert "function bridgeCommand(args)" in adapter
assert "function compactProcessError(value, context)" in adapter
assert "property string conversationStderr:" in adapter
assert "property string messageStderr:" in adapter
assert "property string sendStderr:" in adapter
assert 'bridgeCommand(["--json", "list"])' in adapter
assert '"messages",' in adapter
assert 'bridgeCommand(["--json", "health"])' in adapter
assert '"SESSION LIST"' in adapter
assert '"SESSION MESSAGES"' in adapter
assert '"SESSION SEND"' in adapter

assert "def _cli_candidates()" in bridge
assert 'os.environ.get("SESSION_CLI"' in bridge
assert "DEFAULT_READ_TIMEOUT" in bridge
assert "subprocess.TimeoutExpired" in bridge
assert "def _direct_list()" in bridge
assert "def _direct_messages(" in bridge
assert "PRAGMA table_info" in bridge
assert "sqlcipher3" in bridge
assert "pysqlcipher3" in bridge
assert 'os.environ.get("SESSION_DATA_DIR"' in bridge
assert '"DATABASE_FALLBACK"' in bridge
assert "session-cli read failed:" in bridge
assert 'row["direction"] = direction' in bridge
assert "Writes still go through session-cli/CDP" in bridge
assert "def _cdp_send_direct(" in bridge
assert "suppress_origin=True" in bridge
assert 'parser.add_argument("--cdp-direct"' in bridge

# Prove the CDP fallback suppresses Origin and preserves Session's existing
# sendMessage renderer contract without touching a live Session instance.
spec = importlib.util.spec_from_file_location("session_bridge_contract", BRIDGE)
session_bridge = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(session_bridge)

capture = {}


class FakeSocket:
    def __init__(self):
        self.closed = False
        self.sent = None

    def send(self, payload):
        self.sent = json.loads(payload)

    def recv(self):
        return json.dumps(
            {
                "id": 1,
                "result": {
                    "result": {
                        "value": True,
                    }
                },
            }
        )

    def close(self):
        self.closed = True


fake_socket = FakeSocket()


def fake_create_connection(url, **kwargs):
    capture["url"] = url
    capture["kwargs"] = kwargs
    return fake_socket


previous_websocket = sys.modules.get("websocket")
sys.modules["websocket"] = types.SimpleNamespace(
    create_connection=fake_create_connection
)
previous_url_lookup = session_bridge._cdp_websocket_url
session_bridge._cdp_websocket_url = lambda: "ws://localhost:9222/devtools/page/test"

try:
    send_result = session_bridge._cdp_send_direct("05-test", 'hello "world"')
finally:
    session_bridge._cdp_websocket_url = previous_url_lookup
    if previous_websocket is None:
        sys.modules.pop("websocket", None)
    else:
        sys.modules["websocket"] = previous_websocket

assert send_result == "sent"
assert capture["kwargs"]["suppress_origin"] is True
assert capture["kwargs"]["timeout"] >= 1.0
assert fake_socket.closed is True
assert fake_socket.sent["method"] == "Runtime.evaluate"
params = fake_socket.sent["params"]
assert params["returnByValue"] is True
assert params["awaitPromise"] is True
assert 'window.getConversationController().get("05-test")' in params["expression"]
assert 'body: "hello \\"world\\""' in params["expression"]

# Exercise the normal bridge path with a fake session-cli. This proves the
# QML-facing JSON contract survives the wrapper and that message direction /
# timestamp compatibility fields are normalized.
with tempfile.TemporaryDirectory() as temp_dir:
    fake_cli = Path(temp_dir) / "session-cli"
    fake_cli.write_text(
        """#!/usr/bin/env python3
import json
import sys

if "list" in sys.argv:
    print(json.dumps([
        {
            "id": "05-test",
            "type": "private",
            "active_at": 10,
            "displayNameInProfile": "TEST"
        }
    ]))
    raise SystemExit(0)

if "messages" in sys.argv:
    print(json.dumps([
        {
            "id": "message-1",
            "conversationId": "05-test",
            "type": "outgoing",
            "timestamp": 1234,
            "body": "hello"
        }
    ]))
    raise SystemExit(0)

if "send" in sys.argv:
    print("sent")
    raise SystemExit(0)

raise SystemExit(2)
"""
    )
    fake_cli.chmod(0o755)

    env = os.environ.copy()
    env["SESSION_CLI"] = str(fake_cli)

    list_result = subprocess.run(
        [sys.executable, str(BRIDGE), "--json", "list"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert list_result.returncode == 0, list_result.stderr
    conversations = json.loads(list_result.stdout)
    assert conversations[0]["id"] == "05-test"
    assert conversations[0]["unreadCount"] == 0

    messages_result = subprocess.run(
        [
            sys.executable,
            str(BRIDGE),
            "--json",
            "messages",
            "--limit",
            "100",
            "05-test",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert messages_result.returncode == 0, messages_result.stderr
    messages = json.loads(messages_result.stdout)
    assert messages[0]["direction"] == "outgoing"
    assert messages[0]["sent_at"] == 1234

    health_result = subprocess.run(
        [sys.executable, str(BRIDGE), "--json", "health"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert health_result.returncode == 0, health_result.stderr
    health = json.loads(health_result.stdout)
    assert health["mode"] == "SESSION_CLI"

print("Session adapter compatibility contracts: PASS")
