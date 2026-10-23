#!/usr/bin/env python3
"""Opt-in Proton native/Quickshell Unix availability transport. Offline only."""
from pathlib import Path
import importlib.util
import io
import json
import os
import socket
import stat
import struct
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[2]
HOST_FILE = ROOT / "integrations/proton/browser/proton_native_host.py"
QML = ROOT / "services/notifications/mail/ProtonRelayPilot.qml"
HOST_TEXT = HOST_FILE.read_text(encoding="utf8")
PILOT = QML.read_text(encoding="utf8")
assert "active: false" in PILOT
assert "SocketServer" in PILOT and "SplitParser" in PILOT
assert "Quickshell.env" in PILOT and "XDG_RUNTIME_DIR" in PILOT
assert "post-apollo-proton-relay.sock" in PILOT
assert "PROTON_RELAY_PROBE" in PILOT and "PROTON_RELAY_ACK" in PILOT
assert '"mailboxAccess":false' in PILOT
assert '"messageIdentityVerified":false' in PILOT
for forbidden in ("notify(", "invokeExternalAction(",
                  "getAttribute(", "getProperty(", "console.log(",
                  "content_scripts", "mailboxAccess:true"):
    assert forbidden not in PILOT, forbidden
assert "POST_APOLLO_PROTON_RELAY_ENABLE" in HOST_TEXT
assert "SO_PEERCRED" in HOST_TEXT
assert "os.lstat" in HOST_TEXT

spec = importlib.util.spec_from_file_location("proton_host_pilot", HOST_FILE)
assert spec and spec.loader
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)
CALLER = "chrome-extension://" + "a" * 32 + "/"
WRONG = "chrome-extension://" + "b" * 32 + "/"


def frame(value: dict) -> bytes:
    payload = json.dumps(value, separators=(",", ":")).encode("utf8")
    return struct.pack("=I", len(payload)) + payload


def check_native(caller, env, request=None):
    if request is None:
        request = {"protocol": 1, "kind": "RELAY_PING"}
    output = io.BytesIO()
    result = host.serve(caller, CALLER, io.BytesIO(frame(request)), output, env)
    return result, output.getvalue()


def socket_fixture(runtime: str, reply: dict | bytes):
    path = os.path.join(runtime, host.RELAY_SOCKET)
    ready = threading.Event()
    captured = []
    failures = []

    def listener():
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as srv:
                srv.bind(path)
                os.chmod(path, 0o600)
                srv.listen(1)
                ready.set()
                conn, _ = srv.accept()
                with conn:
                    conn.settimeout(1.0)
                    wire = bytearray()
                    while b"\n" not in wire and len(wire) < 513:
                        part = conn.recv(513 - len(wire))
                        if not part:
                            break
                        wire.extend(part)
                    captured.append(bytes(wire))
                    if isinstance(reply, dict):
                        out = json.dumps(reply, separators=(",", ":")).encode("utf8") + b"\n"
                    else:
                        out = reply
                    conn.sendall(out)
        except Exception as exc:
            failures.append(repr(exc))
            ready.set()

    thread = threading.Thread(target=listener, daemon=True)
    thread.start()
    assert ready.wait(2), "fixture socket did not start"
    assert not failures, failures
    return path, captured, failures, thread


# Old pinned PING is unchanged, even if relay is off.
ok, payload = check_native(CALLER, {}, {"protocol": 1, "kind": "PING"})
assert ok
assert json.loads(payload[4:]) == {
    "protocol": 1, "kind": "PONG",
    "origin": "https://mail.proton.me",
    "mailboxAccess": False,
    "messageIdentityVerified": False,
    "capabilities": [],
}
assert check_native(CALLER, {}) == (False, b"")
assert check_native(WRONG, {}) == (False, b"")
assert check_native(CALLER, {},
    {"protocol": 1, "kind": "RELAY_PING", "messageId": "private"}) == (False, b"")

with tempfile.TemporaryDirectory(prefix="pa-proton-relay-") as runtime:
    os.chmod(runtime, 0o700)
    env = {"XDG_RUNTIME_DIR": runtime, "POST_APOLLO_PROTON_RELAY_ENABLE": "1"}
    assert host.relay_path(env) is None  # No socket at all.
    assert check_native(CALLER, env) == (False, b"")

    valid = host.RELAY_RESPONSE.copy()
    path, captured, failures, thread = socket_fixture(runtime, valid)
    assert host.relay_path(env) == path
    assert check_native(CALLER, {**env, "POST_APOLLO_PROTON_RELAY_ENABLE": "0"}) == (False, b"")
    assert check_native(WRONG, env) == (False, b"")
    ok, wire = check_native(CALLER, env)
    thread.join(timeout=2)
    assert not failures, failures
    assert not thread.is_alive()
    assert captured == [host.RELAY_REQUEST]
    assert ok
    reply = json.loads(wire[4:])
    assert reply == {
        "protocol": 1, "kind": "RELAY_PONG",
        "desktopConnected": True,
        "mailboxAccess": False, "messageIdentityVerified": False, "capabilities": [],
    }
    os.unlink(path)

    # A malicious/surprising response cannot claim message authority.
    wrong_reply = {**valid, "mailboxAccess": True}
    path, captured, failures, thread = socket_fixture(runtime, wrong_reply)
    assert check_native(CALLER, env) == (False, b"")
    thread.join(timeout=2)
    assert not failures
    os.unlink(path)

    # The local socket and its directory must remain owner-only.
    path, captured, failures, thread = socket_fixture(runtime, valid)
    os.chmod(path, 0o666)
    assert host.relay_path(env) is None
    assert check_native(CALLER, env) == (False, b"")
    # Restore, connect and let the fixture terminate.
    os.chmod(path, 0o600)
    assert check_native(CALLER, env)[0]
    thread.join(timeout=2)
    assert not failures
    os.unlink(path)

    os.chmod(runtime, 0o755)
    assert host.relay_path(env) is None
    os.chmod(runtime, 0o700)

    # Never follow a symlink that happens to point to a local socket.
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        alt = os.path.join(runtime, "other.sock")
        s.bind(alt)
        os.chmod(alt, 0o600)
        os.symlink(alt, path)
        assert host.relay_path(env) is None
        os.unlink(path)

assert check_native(CALLER, {"POST_APOLLO_PROTON_RELAY_ENABLE":"1",
                             "XDG_RUNTIME_DIR":"/tmp"}) == (False, b"")
print("Proton opt-in native Unix relay probe: PASS")
