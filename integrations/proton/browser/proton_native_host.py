#!/usr/bin/env python3
"""Strict read-only, opt-in Chromium/Firefox native messaging PING host.

No credentials, page content, session material or mailbox state pass through
this process. Nothing is installed by this repository.
"""
from __future__ import annotations

import json
import os
import re
import socket
import stat
import struct
import sys

MAX_FRAME = 4096
RELAY_SOCKET = "post-apollo-proton-relay.sock"
RELAY_REQUEST = b'{"protocol":1,"kind":"PROTON_RELAY_PROBE"}\n'
RELAY_RESPONSE = {
    "protocol": 1,
    "kind": "PROTON_RELAY_ACK",
    "mailboxAccess": False,
    "messageIdentityVerified": False,
    "capabilities": [],
}

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


def relay_path(environment: dict) -> str | None:
    """Use ONLY the owner's private XDG runtime dir, never an arbitrary path."""
    runtime = environment.get("XDG_RUNTIME_DIR", "")
    if (not isinstance(runtime, str) or not os.path.isabs(runtime)
            or os.path.realpath(runtime) != runtime):
        return None
    try:
        folder = os.stat(runtime, follow_symlinks=False)
        if (not stat.S_ISDIR(folder.st_mode) or folder.st_uid != os.getuid()
                or stat.S_IMODE(folder.st_mode) & 0o077):
            return None
        path = os.path.join(runtime, RELAY_SOCKET)
        # Linux sockaddr_un.sun_path is 108 bytes including a terminator.
        if len(os.fsencode(path)) > 103:
            return None
        endpoint = os.lstat(path)
        if (not stat.S_ISSOCK(endpoint.st_mode)
                or endpoint.st_uid != os.getuid()
                or stat.S_IMODE(endpoint.st_mode) & 0o077):
            return None
    except (OSError, ValueError, TypeError):
        return None
    return path


def relay_probe(environment: dict) -> bool:
    """Optional SAME-UID local availability probe; no mail/event IDs or writes.

    This is NOT a message-authentication protocol. Browser caller identity
    must already pass resolve_caller and the relay must be enabled separately.
    """
    if environment.get("POST_APOLLO_PROTON_RELAY_ENABLE") != "1":
        return False
    path = relay_path(environment)
    if path is None:
        return False
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
            peer.settimeout(0.5)
            peer.connect(path)
            # Peer credentials protect against a socket owned by another UID.
            # Same-UID process impersonation is still out of scope here.
            if not hasattr(socket, "SO_PEERCRED"):
                return False
            creds = peer.getsockopt(
                socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
            _pid, uid, _gid = struct.unpack("3i", creds)
            if uid != os.getuid():
                return False
            peer.sendall(RELAY_REQUEST)
            wire = bytearray()
            while len(wire) <= 512 and b"\n" not in wire:
                fragment = peer.recv(513 - len(wire))
                if not fragment:
                    break
                wire.extend(fragment)
            if len(wire) > 512 or wire.count(b"\n") != 1 or not wire.endswith(b"\n"):
                return False
            response = json.loads(wire[:-1].decode("utf-8"))
            return response == RELAY_RESPONSE and isinstance(response, dict)
    except (OSError, UnicodeError, ValueError, TypeError):
        return False


def serve(caller: str, configured: str, incoming, outgoing,
          environment: dict | None = None) -> bool:
    if not trusted_extension(caller, configured):
        return False
    payload = read_frame(incoming)
    if payload == {"protocol": 1, "kind": "PING"}:
        write_frame(outgoing, {
            "protocol": 1,
            "kind": "PONG",
            "origin": "https://mail.proton.me",
            "mailboxAccess": False,
            "messageIdentityVerified": False,
            "capabilities": []
        })
        return True
    if payload == {"protocol": 1, "kind": "RELAY_PING"}:
        if not relay_probe(environment if environment is not None else {}):
            return False
        write_frame(outgoing, {
            "protocol": 1, "kind": "RELAY_PONG",
            "desktopConnected": True,
            "mailboxAccess": False,
            "messageIdentityVerified": False,
            "capabilities": []
        })
        return True
    return False


def main() -> int:
    identity = resolve_caller(sys.argv[1:], os.environ)
    if identity is None:
        return 1
    caller, configured = identity
    return 0 if serve(caller, configured, sys.stdin.buffer,
                      sys.stdout.buffer, os.environ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
