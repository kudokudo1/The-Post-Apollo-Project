#!/usr/bin/env python3
"""Uninstalled Proton Brave native host: bounded, read-only native protocol."""
from pathlib import Path
import importlib.util
import io
import json
import struct

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "integrations/proton/browser"
HOST = PILOT / "proton_native_host.py"
MANIFEST = json.loads((PILOT / "manifest.json").read_text(encoding="utf-8"))
REG = json.loads((PILOT / "native-host.example.json").read_text(encoding="utf-8"))
BACKGROUND = (PILOT / "background.js").read_text(encoding="utf-8")
assert MANIFEST["manifest_version"] == 3
assert sorted(MANIFEST["permissions"]) == ["activeTab", "nativeMessaging", "scripting"]
assert "content_scripts" not in MANIFEST
assert "host_permissions" not in MANIFEST
assert "webRequest" not in MANIFEST["permissions"]
assert "https://mail.proton.me" in BACKGROUND
assert "chrome.action.onClicked" in BACKGROUND
assert "chrome.runtime.sendNativeMessage" in BACKGROUND
assert "mailboxAccess !== false" in BACKGROUND
assert REG["allowed_origins"] == ["chrome-extension://REPLACE_WITH_ACTUAL_EXTENSION_ID/"]
assert REG["path"].startswith("/ABSOLUTE/")
assert REG["type"] == "stdio"

spec = importlib.util.spec_from_file_location("proton_mail_native_host", HOST)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

origin = "chrome-extension://" + "a" * 32 + "/"
not_allowed = "chrome-extension://" + "b" * 32 + "/"
assert mod.trusted_origin(origin, origin)
assert not mod.trusted_origin(not_allowed, origin)
assert not mod.trusted_origin(origin, "")
assert not mod.trusted_origin("https://mail.proton.me", "https://mail.proton.me")
assert not mod.trusted_origin(origin, "chrome-extension://*/")


def encode_frame(data: dict) -> bytes:
    wire = json.dumps(data).encode("utf-8")
    return struct.pack("=I", len(wire)) + wire


out = io.BytesIO()
assert mod.serve(origin, origin, io.BytesIO(
    encode_frame({"protocol": 1, "kind": "PING"})
), out)
wire = out.getvalue()
assert len(wire) >= 4
reported_size = struct.unpack("=I", wire[:4])[0]
assert reported_size == len(wire) - 4
# The native host's inbound parser deliberately rejects objects with more
# than three fields; the five-field PONG must be decoded as outbound data.
message = json.loads(wire[4:].decode("utf-8"))
assert message == {
    "protocol": 1,
    "kind": "PONG",
    "origin": "https://mail.proton.me",
    "mailboxAccess": False,
    "messageIdentityVerified": False,
    "capabilities": [],
}
assert mod.serve(not_allowed, origin, io.BytesIO(
    encode_frame({"protocol": 1, "kind": "PING"})
), io.BytesIO()) is False
assert mod.serve(origin, origin, io.BytesIO(
    encode_frame({"protocol": 1, "kind": "archive"})
), io.BytesIO()) is False
assert mod.serve(origin, origin, io.BytesIO(
    encode_frame({"protocol": 1, "kind": "PING", "password": "unsafe"})
), io.BytesIO()) is False
assert mod.read_frame(io.BytesIO(struct.pack("=I", mod.MAX_FRAME+1))) is None
assert mod.read_frame(io.BytesIO(b"\x01\x00")) is None
assert mod.read_frame(io.BytesIO(b"\x04\x00\x00\x00bad!")) is None
assert "imaplib" not in HOST.read_text(encoding="utf-8")
assert "subprocess" not in HOST.read_text(encoding="utf-8")
assert "os.system" not in HOST.read_text(encoding="utf-8")
print("Proton read-only native companion handshake: PASS")
