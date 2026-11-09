#!/usr/bin/env python3
"""Native Messaging probe: exact framed subprocess and no secret/restore actions."""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/time"))
from MachineBraveNativeProbe import (
    handle, ProbeError, KIND, HOST_NAME, MAX_INPUT)

HOST = ROOT / "services/time/MachineBraveNativeProbe.py"
ORIGIN = "chrome-extension://" + "a" * 32 + "/"
CHALLENGE = str(uuid.UUID(int=2048))
REQUEST = {
    "kind": "machine-brave-native-transport-request-v1",
    "challenge": CHALLENGE,
}


def framed(value):
    data = json.dumps(value, separators=(",", ":")).encode("utf-8")
    return struct.pack("=I", len(data)) + data


def invoke(payload, *, origin=ORIGIN, extra_args=()):
    with tempfile.TemporaryDirectory(prefix="machine-native-probe-") as temp:
        env = dict(os.environ, XDG_DATA_HOME=temp)
        for item in ("SWAYSOCK", "I3SOCK", "WAYLAND_DISPLAY"):
            env.pop(item, None)
        proc = subprocess.run(
            ["python3", "-B", "-I", str(HOST), origin] + list(extra_args),
            input=payload, capture_output=True, timeout=6, env=env)
        assert not (Path(temp) / "post-apollo" / "machine" / "machine.db").exists()
        assert not proc.stderr, proc.stderr
        if not proc.stdout:
            return proc.returncode, None
        assert len(proc.stdout) >= 4
        (length,) = struct.unpack("=I", proc.stdout[:4])
        assert 1 <= length <= 4096
        assert length == len(proc.stdout) - 4
        return proc.returncode, json.loads(proc.stdout[4:].decode("utf-8"))


def refused(request):
    try:
        handle(request, origin=ORIGIN)
    except ProbeError:
        return
    raise AssertionError("unsafe native host probe request was accepted")


result = handle(REQUEST, origin=ORIGIN)
assert result == {
    "kind": KIND,
    "status": "transport_observed",
    "challenge": CHALLENGE,
    "read_only": True,
    "extension_origin_argument_observed": True,
    "extension_origin_authenticated": False,
    "browser_window_identity_verified": False,
    "sway_window_identity_verified": False,
    "browser_session_identity_verified": False,
    "incognito_exclusion_verified_by_host": False,
    "tab_content_captured": False,
    "session_capture_allowed": False,
    "restore_allowed": False,
    "safe_actions": [],
}
assert HOST_NAME == "org.postapollo.machine_brave_probe"
assert "challenge" in result and "restorable" not in json.dumps(result)
assert result["safe_actions"] == []

code, reply = invoke(framed(REQUEST))
assert code == 0 and reply == result

# Never accept a browser-supplied capability flag, window identity or
# tab content, even when included alongside an otherwise valid request.
for private_key, private_val in (
    ("url", "https://private.example"),
    ("title", "My finances"),
    ("tabs", [{"id": 1}]),
    ("window_id", 3456),
    ("sway_con_id", 1234),
    ("restore", True),
    ("permission", True),
    ("source_authenticated", True),
    ("profile", "/private/profile"),
):
    malicious = dict(REQUEST, **{private_key: private_val})
    refused(malicious)
    code, reply = invoke(framed(malicious))
    assert code == 1
    assert reply == {"kind": KIND, "status": "request_rejected",
                     "read_only": True, "restore_allowed": False,
                     "safe_actions": []}
    assert str(private_val) not in json.dumps(reply)

for request in (
    {}, [], None, 1, "hi",
    {"kind": "restore", "challenge": CHALLENGE},
    {"kind": REQUEST["kind"], "challenge": True},
    {"kind": REQUEST["kind"], "challenge": "not-uuid"},
    {"kind": REQUEST["kind"], "challenge": CHALLENGE.upper()},
    {"kind": REQUEST["kind"], "challenge": CHALLENGE, "other": 0},
):
    refused(request)

for origin in (
    "", "http://example/", "chrome-extension://bad/",
    "chrome-extension://" + "z" * 32 + "/",
    "chrome-extension://" + "a" * 32 + "/etc",
    "chrome-extension://" + "a" * 32,
):
    try:
        handle(REQUEST, origin=origin)
    except ProbeError:
        pass
    else:
        raise AssertionError("malformed extension origin accepted")
    code, reply = invoke(framed(REQUEST), origin=origin)
    assert code == 1 and reply is None

# Chromium could provide an origin with a valid format even from an
# entirely different extension: never convert that to authenticated=True.
other_origin = "chrome-extension://" + "b" * 32 + "/"
code, reply = invoke(framed(REQUEST), origin=other_origin)
assert code == 0
assert reply["extension_origin_authenticated"] is False
assert reply["browser_window_identity_verified"] is False

# Length caps, malformed bytes, invalid UTF-8, truncated messages and an
# empty frame must be rejected with no tracebacks or unframed stdout.
for raw in (
    b"", b"\x00", struct.pack("=I", 0),
    struct.pack("=I", MAX_INPUT + 1),
    struct.pack("=I", 9) + b"{}",
    struct.pack("=I", 4) + b"NOPE",
    struct.pack("=I", 2) + b"\xff\xfe",
    framed({"kind": "reopen_tabs", "challenge": CHALLENGE}),
):
    code, reply = invoke(raw)
    assert code == 1, (raw[:12], code)
    if reply is not None:
        assert reply["status"] == "request_rejected"
        assert reply["restore_allowed"] is False

code, reply = invoke(framed(REQUEST), extra_args=("another-arg",))
assert code == 1 and reply is None
print("MACHINE BRAVE // isolated native frame probe, origin non-auth, no actions PASS")
