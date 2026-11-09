#!/usr/bin/env python3
"""MACHINE Brave native-messaging connectivity probe, no OS/window authority.

One request, one bounded framed response. No Sway IPC, browser reads, storage,
network, subprocesses, restore operations or persistent credentials.

A Chromium-supplied extension origin is NOT a trustworthy authentication
proof against other local processes. This host deliberately has no privileged
capabilities, including no ability to identify a native window.
"""
from __future__ import annotations

import json
import re
import struct
import sys
import uuid

HOST_NAME = "org.postapollo.machine_brave_probe"
KIND = "machine-brave-native-transport-probe-v1"
MAX_INPUT = 4096
MAX_OUTPUT = 4096
ORIGIN_PATTERN = re.compile(r"chrome-extension://[a-p]{32}/\Z")


class ProbeError(ValueError):
    pass


def _canonical_uuid(value):
    if not isinstance(value, str):
        raise ProbeError("INVALID CHALLENGE")
    try:
        result = str(uuid.UUID(value))
    except (ValueError, AttributeError) as exc:
        raise ProbeError("INVALID CHALLENGE") from exc
    if value != result:
        raise ProbeError("INVALID CHALLENGE")
    return value


def handle(request, *, origin):
    """Accept a transport-only challenge and grant zero other capabilities."""
    if not isinstance(origin, str) or not ORIGIN_PATTERN.fullmatch(origin):
        raise ProbeError("INVALID CALLER FORMAT")
    if (not isinstance(request, dict)
            or set(request) != {"kind", "challenge"}
            or request["kind"] != "machine-brave-native-transport-request-v1"):
        raise ProbeError("UNSUPPORTED REQUEST")
    challenge = _canonical_uuid(request["challenge"])
    return {
        "kind": KIND,
        "status": "transport_observed",
        "challenge": challenge,
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


def _read_exact(stream, count):
    remaining = count
    parts = []
    while remaining:
        piece = stream.read(remaining)
        if not piece:
            raise ProbeError("TRUNCATED FRAME")
        parts.append(piece)
        remaining -= len(piece)
    return b"".join(parts)


def read_request(stream):
    header = _read_exact(stream, 4)
    (length,) = struct.unpack("=I", header)
    if not 1 <= length <= MAX_INPUT:
        raise ProbeError("FRAME LIMIT")
    data = _read_exact(stream, length)
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ProbeError("INVALID JSON") from exc
    return value


def write_response(stream, value):
    encoded = json.dumps(value, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    if not 1 <= len(encoded) <= MAX_OUTPUT:
        raise ProbeError("RESPONSE LIMIT")
    stream.write(struct.pack("=I", len(encoded)))
    stream.write(encoded)
    stream.flush()


def main(argv=None, stdin=None, stdout=None):
    arguments = sys.argv[1:] if argv is None else argv
    in_pipe = sys.stdin.buffer if stdin is None else stdin
    out_pipe = sys.stdout.buffer if stdout is None else stdout
    if len(arguments) != 1 or not ORIGIN_PATTERN.fullmatch(arguments[0]):
        # No unframed stderr/stdout; malformed caller ends connection.
        return 1
    try:
        request = read_request(in_pipe)
        reply = handle(request, origin=arguments[0])
    except (ProbeError, OSError, TypeError):
        reply = {"kind": KIND, "status": "request_rejected",
                 "read_only": True, "restore_allowed": False,
                 "safe_actions": []}
    try:
        write_response(out_pipe, reply)
    except (ProbeError, OSError):
        return 1
    return 0 if reply.get("status") == "transport_observed" else 1


if __name__ == "__main__":
    sys.exit(main())
