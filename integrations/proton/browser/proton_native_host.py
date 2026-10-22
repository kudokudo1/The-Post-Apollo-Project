#!/usr/bin/env python3
"""Strictly read-only, opt-in Chromium native messaging PING host.

No credentials, Proton page content, session material or mailbox state pass
through this process. It has no mutation commands. The host manifest and
approved extension ID are intentionally NOT installed by this repository.
"""
from __future__ import annotations

import json
import os
import re
import struct
import sys

MAX_FRAME = 4096
EXTENSION_ORIGIN = re.compile(r"^chrome-extension://[a-p]{32}/$")


def trusted_origin(caller: str, configured: str) -> bool:
    return bool(EXTENSION_ORIGIN.fullmatch(configured) and caller == configured)


def read_frame(stream) -> dict | None:
    prefix = stream.read(4)
    if len(prefix) != 4:
        return None
    size = struct.unpack("=I", prefix)[0]
    if size < 2 or size > MAX_FRAME:
        return None
    payload = stream.read(size)
    if len(payload) != size:
        return None
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeError, ValueError):
        return None
    if not isinstance(data, dict) or len(data) > 3:
        return None
    return data


def write_frame(stream, data: dict) -> None:
    encoded = json.dumps(data, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_FRAME:
        raise ValueError("response too large")
    stream.write(struct.pack("=I", len(encoded)) + encoded)
    stream.flush()


def serve(caller: str, configured: str, incoming, outgoing) -> bool:
    if not trusted_origin(caller, configured):
        return False
    payload = read_frame(incoming)
    if payload != {"protocol": 1, "kind": "PING"}:
        return False
    write_frame(outgoing, {
        "protocol": 1,
        "kind": "PONG",
        "origin": "https://mail.proton.me",
        "mailboxAccess": False,
        "messageIdentityVerified": False,
        "capabilities": []
    })
    return True


def main() -> int:
    caller = sys.argv[1] if len(sys.argv) > 1 else ""
    configured = os.environ.get("POST_APOLLO_PROTON_EXTENSION_ORIGIN", "")
    if not trusted_origin(caller, configured):
        return 1
    return 0 if serve(caller, configured, sys.stdin.buffer, sys.stdout.buffer) else 1


if __name__ == "__main__":
    raise SystemExit(main())
