"""Experimental token-free signed receipt envelope for Identity Center commands.

This module provides REAL Ed25519 signing and strict verification for the
existing native BEGIN / STATUS / CANCEL / RECOVER gateway. It is not an
installed-host attestation, an operator consent provider, a credential store,
a signed release, or an authority source for QML.

Production HOLD: a separately approved C3e/C4b owner must provision and pin
the host signing identity independently, verify the installed gateway process
and client provenance, and C5 must validate each human command intent. CI uses
throwaway in-memory test keys only. Never fetch trust keys from the socket.
"""
from __future__ import annotations

import base64
import json
import re
import secrets
from collections.abc import Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey,
)

REQUEST_SCHEMA = "post-apollo.identity.signed-command-request.experimental-v0"
RECEIPT_SCHEMA = "post-apollo.identity.signed-command-receipt.experimental-v0"
LEGACY_RECEIPT_SCHEMA = "post-apollo.identity.command-receipt.experimental-v0"
_DOMAIN = b"post-apollo.identity.signed-command-receipt.experimental-v0\x00"
_ID = re.compile(r"[A-Za-z0-9_-]{16,96}\Z", re.ASCII)
_NONCE = re.compile(r"[A-Za-z0-9_-]{43}\Z", re.ASCII)
_SIGNATURE = re.compile(r"[A-Za-z0-9_-]{86}\Z", re.ASCII)
_ACTIONS = frozenset(("BEGIN", "STATUS", "CANCEL", "RECOVER"))
_STATES = frozenset(("REQUESTED", "PENDING", "AUTHENTICATED", "CANCELLED",
                     "FAILED", "HOST_LOST", "UNAVAILABLE"))
_ALLOWED = {
    "BEGIN": frozenset(("REQUESTED", "UNAVAILABLE")),
    "STATUS": frozenset(("PENDING", "AUTHENTICATED", "CANCELLED", "FAILED",
                        "HOST_LOST", "UNAVAILABLE")),
    "CANCEL": frozenset(("CANCELLED", "UNAVAILABLE")),
    "RECOVER": frozenset(("REQUESTED", "UNAVAILABLE")),
}
_BODY_KEYS = frozenset(("schema", "hostInstance", "sequence", "action",
                        "commandRequestId", "clientNonce", "state", "requestId"))


class ReceiptRejected(ValueError):
    """Untrusted or unverified receipt: no state/action may be inferred."""


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    d: dict[str, object] = {}
    for k, v in pairs:
        if k in d:
            raise ReceiptRejected("Duplicate field")
        d[k] = v
    return d


def _canonical(body: Mapping[str, object]) -> bytes:
    return json.dumps(body, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _line(raw: bytes, maximum: int) -> dict[str, object]:
    if (type(raw) is not bytes or not 0 < len(raw) <= maximum
            or not raw.endswith(b"\n") or raw.count(b"\n") != 1):
        raise ReceiptRejected("Invalid command/receipt frame")
    try:
        value = json.loads(raw[:-1].decode("utf-8", errors="strict"),
                           object_pairs_hook=_unique_pairs,
                           parse_constant=lambda _:
                           (_ for _ in ()).throw(ReceiptRejected("Constant")))
    except (UnicodeError, ValueError, RecursionError, TypeError) as e:
        raise ReceiptRejected("Malformed command/receipt") from e
    if type(value) is not dict:
        raise ReceiptRejected("Non-object command/receipt")
    return value


def _rid(value: object) -> bool:
    return type(value) is str and _ID.fullmatch(value) is not None


def _nonce(value: object) -> bool:
    return type(value) is str and _NONCE.fullmatch(value) is not None


def _command(action: object, rid: object) -> bool:
    return (type(action) is str and action in _ACTIONS
            and ((action == "BEGIN" and rid is None)
                 or (action != "BEGIN" and _rid(rid))))


def build_request(action: str, request_id: str | None, client_nonce: str) -> bytes:
    if not _command(action, request_id) or not _nonce(client_nonce):
        raise ReceiptRejected("Invalid signed command")
    return _canonical({
        "schema": REQUEST_SCHEMA,
        "action": action,
        "requestId": request_id,
        "clientNonce": client_nonce,
    }) + b"\n"


def parse_request(raw: bytes) -> tuple[str, str | None, str] | None:
    try:
        obj = _line(raw, 1024)
        if (set(obj) != {"schema", "action", "requestId", "clientNonce"}
                or obj["schema"] != REQUEST_SCHEMA
                or not _command(obj["action"], obj["requestId"])
                or not _nonce(obj["clientNonce"])):
            return None
        return obj["action"], obj["requestId"], obj["clientNonce"]
    except ReceiptRejected:
        return None


def _validate_body(body: object) -> bool:
    if type(body) is not dict or set(body) != _BODY_KEYS:
        return False
    return (
        body["schema"] == RECEIPT_SCHEMA
        and _rid(body["hostInstance"])
        and type(body["sequence"]) is int
        and 1 <= body["sequence"] <= 2**53 - 1
        and _command(body["action"], body["commandRequestId"])
        and _nonce(body["clientNonce"])
        and type(body["state"]) is str
        and body["state"] in _ALLOWED[body["action"]]
        and ((body["state"] == "UNAVAILABLE" and body["requestId"] is None)
             or (body["state"] != "UNAVAILABLE" and _rid(body["requestId"])))
        and (body["state"] == "UNAVAILABLE"
             or (body["action"] in ("STATUS", "CANCEL")
                 and body["requestId"] == body["commandRequestId"])
             or (body["action"] == "BEGIN"
                 and body["commandRequestId"] is None)
             or (body["action"] == "RECOVER"
                 and body["requestId"] != body["commandRequestId"]))
    )


def _legacy_result(receipt: bytes) -> tuple[str, str | None]:
    obj = _line(receipt, 256)
    if (set(obj) != {"schema", "state", "requestId"}
            or obj["schema"] != LEGACY_RECEIPT_SCHEMA
            or type(obj["state"]) is not str
            or obj["state"] not in _STATES
            or not ((obj["state"] == "UNAVAILABLE" and obj["requestId"] is None)
                    or (obj["state"] != "UNAVAILABLE" and _rid(obj["requestId"])))):
        raise ReceiptRejected("Invalid host receipt")
    return obj["state"], obj["requestId"]


class ReceiptIssuer:
    """Sign using ONLY an independently provisioned private Ed25519 key.

    The caller must serialize concurrent seal() invocations; gateway does so
    under its command lock. Never instantiate with an untrusted client key.
    """

    def __init__(self, key: Ed25519PrivateKey) -> None:
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError("Host-owned Ed25519 private key required")
        self._key = key
        self._instance = secrets.token_urlsafe(32)
        self._sequence = 0

    def seal(self, action: str, command_request_id: str | None,
             client_nonce: str, host_receipt: bytes) -> bytes:
        if not _command(action, command_request_id) or not _nonce(client_nonce):
            raise ReceiptRejected("Bad command binding")
        state, request_id = _legacy_result(host_receipt)
        body = {
            "schema": RECEIPT_SCHEMA,
            "hostInstance": self._instance,
            "sequence": self._sequence + 1,
            "action": action,
            "commandRequestId": command_request_id,
            "clientNonce": client_nonce,
            "state": state,
            "requestId": request_id,
        }
        if not _validate_body(body):
            raise ReceiptRejected("Host returned inconsistent action/receipt")
        signing_bytes = _DOMAIN + _canonical(body)
        signature = self._key.sign(signing_bytes)
        if len(signature) != 64:
            raise ReceiptRejected("Invalid host signer")
        frame = _canonical({
            "body": body,
            "signature": base64.urlsafe_b64encode(signature).decode("ascii").rstrip("="),
        }) + b"\n"
        if len(frame) > 1024:
            raise ReceiptRejected("Host signed receipt too large")
        self._sequence += 1
        return frame


def verify_receipt(frame: bytes, *, pinned_key: Ed25519PublicKey,
                   action: str, command_request_id: str | None,
                   client_nonce: str) -> dict[str, object]:
    """Verify with caller-provisioned pinned public key. No TOFU or fallback.

    A VALID signature is still not independent installed-host attestation,
    consent, or user identity. The client's separately approved process/seat
    guard must independently verify the executing native host.
    """
    if not isinstance(pinned_key, Ed25519PublicKey):
        raise ReceiptRejected("Missing independently pinned host public key")
    if not _command(action, command_request_id) or not _nonce(client_nonce):
        raise ReceiptRejected("Invalid expected command binding")
    envelope = _line(frame, 1024)
    if set(envelope) != {"body", "signature"}:
        raise ReceiptRejected("Invalid signed envelope")
    body, signature = envelope["body"], envelope["signature"]
    if not _validate_body(body) or not (type(signature) is str
                                        and _SIGNATURE.fullmatch(signature)):
        raise ReceiptRejected("Invalid signed fields")
    if (body["action"] != action
            or body["commandRequestId"] != command_request_id
            or body["clientNonce"] != client_nonce):
        raise ReceiptRejected("Wrong command, request or challenge")
    try:
        sig = base64.urlsafe_b64decode(signature + "==")
        if (len(sig) != 64 or
                base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=") != signature):
            raise ReceiptRejected("Noncanonical signature encoding")
        pinned_key.verify(sig, _DOMAIN + _canonical(body))
    except (InvalidSignature, UnicodeError, ValueError) as e:
        raise ReceiptRejected("Untrusted host receipt signature") from e
    return body.copy()
