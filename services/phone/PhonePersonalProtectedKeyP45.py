"""PHONE P45 // Dormant, read-only protected Personal key retrieval adapter.

Host-private building block ONLY. The future installed, independently
authenticated PHONE host must decide whether it is allowed to call this,
select the opaque enrolled key id, and keep the 32-byte key out of QML.

This module NEVER provisions, unlocks, rotates, exports, clears or backs up
a key, never presents a prompt, and has no CLI/IPC/daemon entry point.
The underlying Secret Service implementation may itself prompt a locked user
collection, so real host preflight must verify lock state before invoking.
No production key authority or host identity is established by key lookup.
"""
from __future__ import annotations

import base64
import binascii
import re
import shutil
import subprocess

SERVICE = "post-apollo-phone-personal-protected-v1"
KEY_ID = re.compile(r"^[0-9a-f]{32}$", re.ASCII)
B64 = re.compile(rb"^[A-Za-z0-9_-]{43}$", re.ASCII)
EXECUTABLE = "/usr/bin/secret-tool"
KEY_BYTES = 32
MAX_CAPTURE = 128


class ProtectedKeyUnavailable(Exception):
    """Never echoes a key, selector, profile, path or keyring error."""


def _deny() -> None:
    raise ProtectedKeyUnavailable("PHONE_PERSONAL_KEY_UNAVAILABLE")


def read_existing_key_for_trusted_host(
    key_id: object, *, which=shutil.which, run=subprocess.run,
) -> bytes:
    """Look up an already provisioned opaque key by host-owned selector.

    This function is intentionally a *mechanism*, not an auth decision.
    The enrolled selector and authoritative Secret Service/OS process
    boundary must be owned by a future protected host. Never invoke from
    QML or an ordinary same-UID client; a random ID is not a capability.
    No fallback to creating a new key if one is missing or locked.
    """
    if type(key_id) is not str or KEY_ID.fullmatch(key_id) is None:
        _deny()
    try:
        # Do not run a PATH-shadowing executable from the untrusted user's
        # environment. The eventual host must pin executable provenance.
        if which("secret-tool") != EXECUTABLE:
            _deny()
        command = [
            EXECUTABLE, "lookup",
            "post-apollo-service", SERVICE,
            "key-id", key_id,
        ]
        result = run(
            command, input=b"", capture_output=True,
            timeout=4, check=False,
        )
        if (type(result.returncode) is not int
                or result.returncode != 0
                or type(result.stdout) is not bytes
                or not 43 <= len(result.stdout) <= MAX_CAPTURE):
            _deny()
        raw = result.stdout
        if raw.endswith(b"\n"):
            raw = raw[:-1]
        if B64.fullmatch(raw) is None:
            _deny()
        key = base64.urlsafe_b64decode(raw + b"=")
        if (len(key) != KEY_BYTES
                or base64.urlsafe_b64encode(key).rstrip(b"=") != raw
                or not any(key)):
            _deny()
        return key
    except ProtectedKeyUnavailable:
        raise
    except (OSError, subprocess.TimeoutExpired, TypeError, ValueError,
            AttributeError, binascii.Error, OverflowError):
        _deny()


# No main(), import-time host operation, mutation, key backup, or QML export.
