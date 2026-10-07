import json
import os
import subprocess
import sys
import tempfile
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
