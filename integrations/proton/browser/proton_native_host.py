#!/usr/bin/env python3
"""Strict read-only, opt-in Chromium/Firefox native messaging PING host.

No credentials, page content, session material or mailbox state pass through
this process. Nothing is installed by this repository.
"""
from __future__ import annotations

import json
import os
import re
import struct
import sys

MAX_FRAME = 4096
HOST_NAME = "org.postapollo.proton_mail"
EXTENSION_ORIGIN = re.compile(r"^chrome-extension://[a-p]{32}/$")
FIREFOX_EXTENSION_ID = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,79}@[A-Za-z0-9][A-Za-z0-9.-]{0,99}$"
)


def trusted_origin(caller: str, configured: str) -> bool:
    """Chromium extension origin must be an exact, pinned extension ID."""
    return bool(EXTENSION_ORIGIN.fullmatch(configured) and caller == configured)


def trusted_firefox_id(caller: str, configured: str) -> bool:
    """Firefox native messaging passes the add-on ID, not a chrome origin."""
    return bool(FIREFOX_EXTENSION_ID.fullmatch(configured) and caller == configured)


def trusted_extension(caller: str, configured: str) -> bool:
    return trusted_origin(caller, configured) or trusted_firefox_id(caller, configured)


def resolve_caller(args: list[str], environment: dict) -> tuple[str, str] | None:
    """Interpret browser-specific command lines without trusting a claim in JSON.

    Chromium Linux: argv[1] = chrome-extension://<extension-id>/
    Firefox: argv[1] = native-host manifest path, argv[2] = add-on ID.
    The manifest allowlist and these pinned identities must BOTH match.
    """
    if len(args) == 1:
        caller = args[0]
        configured = environment.get("POST_APOLLO_PROTON_EXTENSION_ORIGIN", "")
        if trusted_origin(caller, configured):
            return caller, configured
    elif len(args) == 2:
        manifest_path, caller = args
        configured = environment.get("POST_APOLLO_PROTON_FIREFOX_EXTENSION_ID", "")
        if (os.path.isabs(manifest_path)
                and os.path.basename(manifest_path) == HOST_NAME + ".json"
                and trusted_firefox_id(caller, configured)):
            return caller, configured
    return None


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
    if not trusted_extension(caller, configured):
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
    identity = resolve_caller(sys.argv[1:], os.environ)
    if identity is None:
        return 1
    caller, configured = identity
    return 0 if serve(caller, configured, sys.stdin.buffer, sys.stdout.buffer) else 1


if __name__ == "__main__":
    raise SystemExit(main())
