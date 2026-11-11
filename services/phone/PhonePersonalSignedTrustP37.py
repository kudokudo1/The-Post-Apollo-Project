"""P37 PHONE-only, DENY-ONLY signed contact-save receipt consistency contract.

This verifies two actual Ed25519 signatures using separate externally supplied
public keys, but DOES NOT verify who enrolled those keys, who measured the
installed process, or whether a human approved anything. The verifier returns
NO permission-granting result. It cannot access the vault, keyring, PHONE UI,
BlueFerry, Identity Gateway, C5 or the operating system.

Current C3e, C4b and C5 workers own their actual trust and consent producers.
Synthetic receipts minted in tests are NOT eligible production credentials.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
from typing import Any

SCHEMA = "post-apollo.phone.personal-contact-save-request.p37-ci"
HOST_SCHEMA = "post-apollo.phone.personal-contact-host-receipt.p37-ci"
CONSENT_SCHEMA = "post-apollo.phone.personal-contact-consent-receipt.p37-ci"
HOST_ROLE = "post-apollo.phone.installed-host-witness.ci-only"
CONSENT_ROLE = "post-apollo.phone.separate-consent-reviewer.ci-only"
AUDIENCE = "post-apollo.phone.personal-contact-vault.ci-only"
PURPOSE = "personal.contact.metadata-write.ci-only"
HOST_DOMAIN = b"post-apollo.phone.p37.host-receipt-ci\x00"
CONSENT_DOMAIN = b"post-apollo.phone.p37.consent-receipt-ci\x00"

REQ_FIELDS = frozenset({
    "schema", "action", "profileId", "providerOwner", "sessionRef",
    "snapshotEpoch", "selectedCardHmac", "editHmac",
    "expectedRevision", "challengeSha256", "minimumReleaseEpoch",
    "minimumReleaseSequence", "requestNonce",
})
HOST_FIELDS = frozenset({
    "schema", "role", "audience", "purpose", "requestSha256",
    "challengeSha256", "releaseEpoch", "releaseSequence",
    "releaseSha256", "hostEvidenceSha256", "issuedAt", "expiresAt",
})
CONSENT_FIELDS = frozenset({
    "schema", "role", "audience", "purpose", "requestSha256",
    "challengeSha256", "hostSha256", "gestureEvidenceSha256",
    "issuedAt", "expiresAt",
})

PROFILE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
OWNER = re.compile(r"^:[0-9]+\.[0-9]+$")
REF = re.compile(r"^[A-Za-z0-9_-]{12,64}$")
HEX64 = re.compile(r"^[a-f0-9]{64}$")
HEX32 = re.compile(r"^[a-f0-9]{32}$")
ACTIONS = frozenset({"LINK", "FAVORITE", "NOTE", "UNLINK"})
MAX_FRAME = 4096
MAX_LIFETIME_SECONDS = 60
MAX_INTEGER = 2**53 - 1

# This is not a successful authorization response, even on valid signatures.
DENIED = {
    "status": "NO_PRODUCTION_AUTHORITY",
    "productionEnabled": False,
    "vaultWriteEnabled": False,
    "humanConsentVerified": False,
    "installedHostVerified": False,
}
MATCHED_FIXTURE = {**DENIED, "status": "SIGNED_FIXTURE_PAIR_MATCHED"}


class ReceiptRefused(Exception):
    """Content-free internal refusal; public API returns DENIED only."""


def _refuse() -> None:
    raise ReceiptRefused("P37_RECEIPT_REFUSED")


def _int(value: object, minimum: int = 0) -> bool:
    return type(value) is int and minimum <= value <= MAX_INTEGER


def _hex(value: object) -> bool:
    return type(value) is str and HEX64.fullmatch(value) is not None


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for k, v in pairs:
        if k in obj:
            _refuse()
        obj[k] = v
    return obj


def _signed_frame(raw: bytes, required_fields: frozenset[str]) -> dict[str, Any]:
    if type(raw) is not bytes or not 2 <= len(raw) <= MAX_FRAME:
        _refuse()
    try:
        obj = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_pairs,
                         parse_constant=lambda _value: _refuse())
        if type(obj) is not dict or frozenset(obj) != required_fields:
            _refuse()
        if raw != _canonical(obj):
            _refuse()
    except (ValueError, UnicodeError, TypeError, OverflowError):
        _refuse()
    return obj


def _valid_request(request: object) -> bool:
    if type(request) is not dict or frozenset(request) != REQ_FIELDS:
        return False
    return (
        request["schema"] == SCHEMA
        and type(request["action"]) is str and request["action"] in ACTIONS
        and type(request["profileId"]) is str
        and PROFILE.fullmatch(request["profileId"]) is not None
        and type(request["providerOwner"]) is str
        and OWNER.fullmatch(request["providerOwner"]) is not None
        and type(request["sessionRef"]) is str
        and REF.fullmatch(request["sessionRef"]) is not None
        and _int(request["snapshotEpoch"], 1)
        and _hex(request["selectedCardHmac"])
        and _hex(request["editHmac"])
        and _int(request["expectedRevision"])
        and _hex(request["challengeSha256"])
        and _int(request["minimumReleaseEpoch"], 1)
        and _int(request["minimumReleaseSequence"], 1)
        and type(request["requestNonce"]) is str
        and HEX32.fullmatch(request["requestNonce"]) is not None
        and len(_canonical(request)) <= MAX_FRAME
    )


def _valid_time(receipt: dict, now: int) -> bool:
    issued, expiry = receipt["issuedAt"], receipt["expiresAt"]
    return (_int(issued) and _int(expiry)
            and issued <= now < expiry
            and 0 < expiry - issued <= MAX_LIFETIME_SECONDS)


def _verify_signature(public_key: bytes, signature: bytes,
                      domain: bytes, raw: bytes) -> None:
    if type(public_key) is not bytes or len(public_key) != 32:
        _refuse()
    if type(signature) is not bytes or len(signature) != 64:
        _refuse()
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey,
        )
        from cryptography.exceptions import InvalidSignature
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            signature, domain + raw
        )
    except (ImportError, InvalidSignature, ValueError, TypeError):
        _refuse()


def compare_signed_fixture_receipts(
    *, expected_request: object, host_frame: bytes, host_signature: bytes,
    host_public_key: bytes, consent_frame: bytes, consent_signature: bytes,
    consent_public_key: bytes, now: int,
) -> dict[str, object]:
    """Compare two differently signed, fully bound receipts.

    All pins and expected request fields are caller-supplied CI inputs. A
    matching pair is ONLY consistency evidence and grants absolutely nothing.
    """
    try:
        if not _int(now) or not _valid_request(expected_request):
            _refuse()
        if (type(host_public_key) is not bytes
                or type(consent_public_key) is not bytes
                or len(host_public_key) != 32 or len(consent_public_key) != 32
                or hmac.compare_digest(host_public_key, consent_public_key)):
            _refuse()
        # Freeze the caller's expected request before any signature or scope
        # checks, preventing a mutable caller map from changing halfway.
        expected = _canonical(expected_request)
        request_digest = hashlib.sha256(expected).hexdigest()
        host = _signed_frame(host_frame, HOST_FIELDS)
        consent = _signed_frame(consent_frame, CONSENT_FIELDS)
        _verify_signature(host_public_key, host_signature, HOST_DOMAIN, host_frame)
        _verify_signature(consent_public_key, consent_signature,
                          CONSENT_DOMAIN, consent_frame)
        if (host["schema"] != HOST_SCHEMA
                or host["role"] != HOST_ROLE
                or host["audience"] != AUDIENCE or host["purpose"] != PURPOSE
                or consent["schema"] != CONSENT_SCHEMA
                or consent["role"] != CONSENT_ROLE
                or consent["audience"] != AUDIENCE
                or consent["purpose"] != PURPOSE
                or not _valid_time(host, now)
                or not _valid_time(consent, now)):
            _refuse()
        if (host["requestSha256"] != request_digest
                or consent["requestSha256"] != request_digest
                or host["challengeSha256"] != expected_request["challengeSha256"]
                or consent["challengeSha256"] != expected_request["challengeSha256"]
                or consent["hostSha256"] != hashlib.sha256(host_frame).hexdigest()
                or not _hex(host["releaseSha256"])
                or not _hex(host["hostEvidenceSha256"])
                or not _hex(consent["gestureEvidenceSha256"])
                or not _int(host["releaseEpoch"], 1)
                or not _int(host["releaseSequence"], 1)
                or host["releaseEpoch"] != expected_request["minimumReleaseEpoch"]
                or host["releaseSequence"]
                   < expected_request["minimumReleaseSequence"]
                or consent["issuedAt"] < host["issuedAt"]
                or consent["issuedAt"] >= host["expiresAt"]
                or consent["expiresAt"] > host["expiresAt"]):
            _refuse()
        return dict(MATCHED_FIXTURE)
    except (ReceiptRefused, ValueError, TypeError, KeyError, OverflowError):
        return dict(DENIED)


# No signer, key generation, issuer, challenge/replay ledger, file I/O, host
# integration, real human consent, production grant, or vault commit method.
