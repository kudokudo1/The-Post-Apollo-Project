"""P36 // Read-only, disposable Secret Service adapter for synthetic tests.

This is deliberately NOT a production key provider. It looks up only
test-tagged entries with random 128-bit selectors. It cannot create, unlock,
clear, enumerate or migrate a real keyring. There is no CLI/DBus/QML binding.
The isolated GitHub harness creates/deletes test secrets in a private session.

Do not use this API for real Personal contact data: the user has not selected
a production keyring/unlock or authenticated host authority.
"""
from __future__ import annotations

import base64
import re
import shutil
import subprocess

SERVICE = "post-apollo-phone-p36-disposable-ci-only"
SELECTOR = re.compile(r"^[a-f0-9]{32}$")
KEY_BYTES = 32
MAX_STDOUT = 256


class KeyUnavailable(Exception):
    """Content-free error; never echo provider output, selectors or secrets."""


def _deny() -> None:
    raise KeyUnavailable("P36_KEY_UNAVAILABLE")


def synthetic_key_lookup(selector: str, *, which=shutil.which,
                         run=subprocess.run) -> bytes:
    """Read only a previously created throwaway test item.

    Not a permission check. secret-tool lookup could activate the system
    Secret Service when called, so production PHONE never invokes this.
    """
    if type(selector) is not str or SELECTOR.fullmatch(selector) is None:
        _deny()
    if which("secret-tool") is None:
        _deny()
    argv = [
        "secret-tool", "lookup", "post-apollo-test", SERVICE,
        "nonce", selector,
    ]
    try:
        result = run(argv, input=b"", capture_output=True, timeout=5,
                     check=False)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        _deny()
    if (result.returncode != 0 or type(result.stdout) is not bytes
            or not 1 <= len(result.stdout) <= MAX_STDOUT):
        _deny()
    blob = result.stdout.rstrip(b"\n")
    # Key format is canonical URL-safe base64, with no spaces, truncation
    # or lenient alternate encodings, and never passed in env or argv.
    if re.fullmatch(rb"[A-Za-z0-9_-]{43}", blob) is None:
        _deny()
    try:
        key = base64.urlsafe_b64decode(blob + b"=")
    except (ValueError, base64.binascii.Error):
        _deny()
    if (len(key) != KEY_BYTES
            or base64.urlsafe_b64encode(key).rstrip(b"=") != blob):
        _deny()
    return key


# No keyring store, unlock, clear, password prompt, CLI or production bridge.
