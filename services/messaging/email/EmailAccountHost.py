#!/usr/bin/env python3
"""Thunderbird native-messaging host: bounded read-only account inventory.

Extension -> host only. No credentials, message bodies, or mail operations.
Writes an atomic, user-private snapshot for a future QML adapter.
This script does not register itself as a native host.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import struct
import sys
import tempfile

MAX_FRAME_BYTES = 1024 * 1024
MAX_ACCOUNTS = 64
MAX_IDENTITIES = 32
MAX_FOLDERS = 256


def state_path() -> Path:
    root = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
    return root / "post-apollo" / "social-email" / "accounts.json"


def normalize(payload: object) -> dict:
    if not isinstance(payload, dict) or payload.get("type") != "accounts.snapshot":
        raise ValueError("unsupported message")
    accounts = payload.get("accounts")
    if not isinstance(accounts, list) or len(accounts) > MAX_ACCOUNTS:
        raise ValueError("invalid account list")
    normalized = []
    for account in accounts:
        if not isinstance(account, dict):
            raise ValueError("invalid account")
        identities = account.get("identities", [])
        folders = account.get("folders", [])
        if not isinstance(identities, list) or len(identities) > MAX_IDENTITIES:
            raise ValueError("invalid identities")
        if not isinstance(folders, list) or len(folders) > MAX_FOLDERS:
            raise ValueError("invalid folders")
        normalized.append({
            "id": str(account.get("id") or "")[:128],
            "name": str(account.get("name") or "")[:256],
            "type": str(account.get("type") or "")[:64],
            "identities": [
                {"email": str(x.get("email") or "")[:320]}
                for x in identities if isinstance(x, dict)
            ],
            "folders": [
                {"id": str(x.get("id") or "")[:256],
                 "name": str(x.get("name") or "")[:256],
                 "type": str(x.get("type") or "")[:64]}
                for x in folders if isinstance(x, dict)
            ],
        })
    return {"schema": 1, "source": "thunderbird", "accounts": normalized}


def write_snapshot(payload: dict, destination: Path) -> None:
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(destination.parent, 0o700)
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    fd, temp = tempfile.mkstemp(prefix=".accounts-", dir=str(destination.parent))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, destination)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def read_frame() -> object | None:
    length_bytes = sys.stdin.buffer.read(4)
    if not length_bytes:
        return None
    if len(length_bytes) != 4:
        raise ValueError("truncated frame header")
    (length,) = struct.unpack("=I", length_bytes)
    if length > MAX_FRAME_BYTES:
        raise ValueError("frame too large")
    body = sys.stdin.buffer.read(length)
    if len(body) != length:
        raise ValueError("truncated frame")
    return json.loads(body)


def reply(message: dict) -> None:
    body = json.dumps(message, separators=(",", ":")).encode()
    sys.stdout.buffer.write(struct.pack("=I", len(body)) + body)
    sys.stdout.buffer.flush()


def main() -> int:
    while True:
        try:
            message = read_frame()
            if message is None:
                return 0
            write_snapshot(normalize(message), state_path())
            reply({"ok": True, "schema": 1})
        except (ValueError, OSError, TypeError, json.JSONDecodeError) as exc:
            reply({"ok": False, "error": str(exc)[:180]})
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
