"""PHONE P46 // In-memory AES-256-GCM encrypted master recovery envelope.

A protected installed host may eventually export a *sealed* master key to a
separately authorized recovery destination. Never store the recovery secret
with the vault, or send either key to QML. This module has no file writes,
keyring actions, CLI/IPC or human-consent authority.

An externally authenticated release/recovery floor is REQUIRED to make
restoration rollback-resistant; caller-supplied minimum_epoch here is just a
format sanity check and is forgeable. A matching envelope never authorizes
restoring it to a real collection or erasing the existing master.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
from typing import Any

import PhonePersonalContactIdentity as Identity

SCHEMA = "post-apollo.phone.personal-master-recovery.p46.v1"
ALGORITHM = "AES-256-GCM"
KDF_DOMAIN = b"post-apollo.phone.p46.recovery-v1\x00"
AAD_DOMAIN = b"post-apollo.phone.p46.aad-v1\x00"
MAX_ENVELOPE = 2048
MAX_EPOCH = 2**53 - 1
FIELDS = frozenset(("schema", "algorithm", "epoch", "salt", "nonce", "sealed"))
BASE64 = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"


class RecoveryRefused(Exception):
    """Never includes raw key, profile, envelope or provider diagnostics."""


def _deny() -> None:
    raise RecoveryRefused("PHONE_RECOVERY_ENVELOPE_REFUSED")


def _key(value: object) -> bool:
    return type(value) is bytes and len(value) == 32 and value != bytes(32)


def _profile(value: object) -> bool:
    return type(value) is str and Identity.PROFILE.fullmatch(value) is not None


def _epoch(value: object) -> bool:
    return type(value) is int and 1 <= value <= MAX_EPOCH


def _url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _unurl(value: object, exact: int) -> bytes:
    if (type(value) is not str
            or not 1 <= len(value) <= 512
            or any(ord(c) not in BASE64 for c in value)):
        _deny()
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        if len(raw) != exact or _url(raw) != value:
            _deny()
        return raw
    except (binascii.Error, ValueError, UnicodeError):
        _deny()


def _derive(recovery_key: bytes, salt: bytes) -> bytes:
    return hmac.new(recovery_key, KDF_DOMAIN + salt, hashlib.sha256).digest()


def _aad(profile: str, epoch: int) -> bytes:
    return AAD_DOMAIN + profile.encode("ascii") + b":" + str(epoch).encode("ascii")


def _pairs(rows: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in rows:
        if key in result:
            _deny()
        result[key] = value
    return result


def seal_master_for_recovery(
    *, master_key: object, recovery_key: object,
    profile: object, epoch: object,
    random_bytes=secrets.token_bytes,
) -> bytes:
    """Seal only in memory. Recovery key must be distinct and held off-host."""
    try:
        if (not _key(master_key) or not _key(recovery_key)
                or hmac.compare_digest(master_key, recovery_key)
                or not _profile(profile) or not _epoch(epoch)
                or not callable(random_bytes)):
            _deny()
        salt = random_bytes(16)
        nonce = random_bytes(12)
        if (type(salt) is not bytes or len(salt) != 16
                or type(nonce) is not bytes or len(nonce) != 12
                or not any(salt) or not any(nonce)):
            _deny()
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        ciphertext = AESGCM(_derive(recovery_key, salt)).encrypt(
            nonce, master_key, _aad(profile, epoch))
        envelope = {
            "schema": SCHEMA, "algorithm": ALGORITHM,
            "epoch": epoch, "salt": _url(salt), "nonce": _url(nonce),
            "sealed": _url(ciphertext),
        }
        raw = json.dumps(envelope, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False).encode("ascii")
        if len(raw) > MAX_ENVELOPE:
            _deny()
        return raw
    except RecoveryRefused:
        raise
    except Exception:
        _deny()


def unseal_master_for_recovery(
    *, envelope: object, recovery_key: object,
    profile: object, minimum_epoch: object,
) -> bytes:
    """In-memory recovery only; never import/restore/activate a real key."""
    try:
        if (type(envelope) is not bytes
                or not 2 <= len(envelope) <= MAX_ENVELOPE
                or not _key(recovery_key) or not _profile(profile)
                or not _epoch(minimum_epoch)):
            _deny()
        obj = json.loads(envelope.decode("ascii"), object_pairs_hook=_pairs,
                         parse_constant=lambda _: _deny())
        if (type(obj) is not dict or set(obj) != FIELDS
                or obj.get("schema") != SCHEMA
                or obj.get("algorithm") != ALGORITHM
                or not _epoch(obj.get("epoch"))
                or obj["epoch"] < minimum_epoch):
            _deny()
        canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=True, allow_nan=False).encode("ascii")
        if envelope != canonical:
            _deny()
        salt = _unurl(obj["salt"], 16)
        nonce = _unurl(obj["nonce"], 12)
        ciphertext = _unurl(obj["sealed"], 48)
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        material = AESGCM(_derive(recovery_key, salt)).decrypt(
            nonce, ciphertext, _aad(profile, obj["epoch"]))
        if not _key(material) or hmac.compare_digest(material, recovery_key):
            _deny()
        return material
    except RecoveryRefused:
        raise
    except Exception:
        _deny()


# No file IO, backup transport, public API, keyring import, rotation, erase,
# signed floor, C5 consent verification or production recovery authorization.
