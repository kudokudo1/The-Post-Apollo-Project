"""PHONE P46 // Host-private first-use key provisioning mechanism.

NEVER a production authorization service. This module has no CLI, IPC,
QML binding, import side effect or user-triggerable entry point. An eventual
independently authenticated installed host must hold signer/session/seat
authority, prove the Secret Service collection unlocked, reserve the key ID
in an external rollback-resistant ledger and authorize first-use enrollment.

The mechanism accepts protected host callbacks for readiness/reservation.
Those callbacks are FORGEABLE when injected by an ordinary Python caller,
so a successful return does NOT grant production key custody. Only use
after authenticated host ownership is independently demonstrated.

No implicit unlock, automatic overwrite retry, key export, rotation or
deletion. Secret Service may independently display an unlock prompt;
the real host must prevent that before this mechanism is invoked.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
import hmac
import secrets
import shutil
import subprocess
from typing import Callable

import PhonePersonalProtectedKeyP45 as Existing

LABEL = "Post Apollo PHONE Personal (protected host only)"
OUTCOME = {
    "status": "STORED_AND_READ_BACK_NOT_HOST_ATTESTED",
    "productionEnabled": False,
    "installedHostVerified": False,
    "keyDurablyAttested": False,
    "personalSaveAuthorized": False,
}
MAX_INPUT = 64
TIMEOUT_SECONDS = 5


class KeyProvisionRefused(Exception):
    """No key, private selector, provider response or raw error is included."""


def _deny() -> None:
    raise KeyProvisionRefused("PHONE_KEY_PROVISION_REFUSED")


@dataclass(frozen=True, slots=True, repr=False)
class PreparedKey:
    """Short-lived host-private material. Never serialize, log or send to UI."""

    key_id: str
    material: bytes = field(repr=False)

    def __repr__(self) -> str:
        return "<PreparedKey HOST_PRIVATE_NO_PRODUCTION_AUTHORITY>"


def prepare_new_key(*, random_bytes=secrets.token_bytes) -> PreparedKey:
    """Use OS CSPRNG to prepare separate 128-bit ID and 256-bit master.

    This never writes a key. Only the verified host may actually enroll it.
    Random-source dependency injection exists exclusively for disposable CI.
    """
    try:
        if not callable(random_bytes):
            _deny()
        identifier = random_bytes(16)
        key = random_bytes(32)
        if (type(identifier) is not bytes or len(identifier) != 16
                or type(key) is not bytes or len(key) != 32
                or identifier == bytes(16)
                or key == bytes(32)):
            _deny()
        return PreparedKey(identifier.hex(), key)
    except KeyProvisionRefused:
        raise
    except Exception:
        _deny()


def store_prepared_for_protected_host(
    prepared: object, *, preflight_unlocked: Callable[[], bool],
    reserve_unused_id: Callable[[str], bool],
    which=shutil.which, run=subprocess.run,
) -> dict[str, object]:
    """Write via fixed Secret Service command and verify same bytes by lookup.

    Reservation MUST be atomic/external and never use this Python process
    as the global authority. Failure after store is potentially AMBIGUOUS:
    do not auto-retry, clear, or regenerate a master on failure.
    """
    if (type(prepared) is not PreparedKey
            or not Existing.KEY_ID.fullmatch(prepared.key_id)
            or type(prepared.material) is not bytes
            or len(prepared.material) != Existing.KEY_BYTES
            or prepared.material == bytes(32)
            or not callable(preflight_unlocked)
            or not callable(reserve_unused_id)):
        _deny()
    try:
        # Do not invoke the keyring until all caller-side readiness has been
        # checked. True from a callback is NOT genuine identity/consent.
        if (preflight_unlocked() is not True
                or which("secret-tool") != Existing.EXECUTABLE
                or reserve_unused_id(prepared.key_id) is not True
                or preflight_unlocked() is not True):
            _deny()
        encoded = base64.urlsafe_b64encode(prepared.material).rstrip(b"=")
        if len(encoded) != 43:
            _deny()
        argv = [
            Existing.EXECUTABLE, "store", "--label=" + LABEL,
            "post-apollo-service", Existing.SERVICE,
            "key-id", prepared.key_id,
        ]
        # Key passes ONLY on stdin, never command arguments or an env var.
        result = run(argv, input=encoded,
                     capture_output=True, timeout=TIMEOUT_SECONDS, check=False)
        if (type(result.returncode) is not int or result.returncode != 0
                or type(result.stdout) is not bytes
                or result.stdout != b""
                or preflight_unlocked() is not True):
            _deny()
        confirmed = Existing.read_existing_key_for_trusted_host(
            prepared.key_id, which=which, run=run)
        if not hmac.compare_digest(confirmed, prepared.material):
            _deny()
        if preflight_unlocked() is not True:
            _deny()
        return dict(OUTCOME)
    except KeyProvisionRefused:
        raise
    except Exception:
        # Includes ambiguous provider failures. Never expose stderr, content,
        # key ID, note, profile, process path or allow implicit retry.
        _deny()


# No real host enrollment, ledger, C3e/C5, keyring unlock, keyring clear,
# backup persistence, production service binding or same-UID security claim.
