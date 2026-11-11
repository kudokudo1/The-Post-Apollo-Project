#!/usr/bin/env python3
"""C3e-X: CI-only Identity running-service evidence/receipt consistency receiver.

All process observations and expected pins are caller-supplied test data; a
matching signed UNAVAILABLE receipt is NOT independently authenticated host
origin. No socket, OS process, installed service, keys, credentials, user
consent, external nonce authority or production operation is created here.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ROOT = Path(__file__).resolve().parents[3]
RECEIPT_SOURCE = ROOT / "services/identity/signed_command_receipt_v0.py"
_spec = importlib.util.spec_from_file_location("c3ex_identity_receipts", RECEIPT_SOURCE)
if _spec is None or _spec.loader is None:
    raise RuntimeError("C3EX_REQUIRED_IDENTITY_RECEIPT_VERIFIER_MISSING")
Receipt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(Receipt)

SCHEMA = "postapollo.connections.c3ex-identity-runtime-denial.ci-v1"
ROLE = "postapollo.identity.native-command-gateway.deny-only-ci"
UNIT = "post-apollo-identity-silverblue-ci.service"
SELINUX = "system_u:system_r:postapollo_identity_ci_t:s0"
CGROUP = "/system.slice/" + UNIT
SOCKET = "/run/postapollo-identity-silverblue-ci-only/native/identity-command-v0.sock"
EXECUTABLE = "/run/postapollo-identity-silverblue-ci-only/ci-python3"
REQUEST_ID = "CI_NO_LOGIN_REQUEST_01234567"
ACTIONS = ("BEGIN", "STATUS", "CANCEL", "RECOVER")
HEX = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
SNAPSHOT = frozenset((
    "rpmSha256", "entrypointSha256", "exeSha256", "exePath", "unit",
    "pid", "startTicks", "uid", "gid", "cgroup", "selinux", "socketPath",
))
RECORD = frozenset((
    "action", "commandRequestId", "clientNonce", "before", "after", "peer",
))
NEGATIVE = {
    "externalIssuerCustodyVerified": False,
    "externalRollbackResistanceVerified": False,
    "signedGuestOriginAuthenticated": False,
    "evidenceCryptographicallyAttested": False,
    "installedGuestMeasured": False,
    "hostAuthenticated": False,
    "c5HumanConsentVerified": False,
    "canBeginSignIn": False,
    "canApprove": False,
    "credentialActionsEnabled": False,
    "productionAuthority": False,
}


class Refused(ValueError):
    """Malformed, mismatched or untrusted CI evidence; never an authorization."""


def _deny(code: str):
    raise Refused(code)


def _unique(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            _deny("DUPLICATE_EVIDENCE_FIELD")
        result[name] = value
    return result


def _canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False,
    ).encode("ascii")


def _decode(raw: bytes):
    if (type(raw) is not bytes or not 1 <= len(raw) <= 16384
            or not raw.endswith(b"\n") or raw.count(b"\n") != 1):
        _deny("BOUNDED_EVIDENCE_FRAME_REFUSED")
    try:
        document = json.loads(
            raw[:-1].decode("ascii"), object_pairs_hook=_unique,
            parse_constant=lambda _: _deny("NONFINITE_EVIDENCE_REFUSED"),
        )
        if type(document) is not dict or raw != _canonical(document) + b"\n":
            _deny("NONCANONICAL_EVIDENCE_REFUSED")
    except (UnicodeError, ValueError, RecursionError, TypeError, OverflowError) as exc:
        raise Refused("EVIDENCE_JSON_REFUSED") from exc
    if (set(document) != {"schema", "role", "records"}
            or document["schema"] != SCHEMA or document["role"] != ROLE
            or type(document["records"]) is not list
            or len(document["records"]) != 4):
        _deny("IDENTITY_EVIDENCE_SCHEMA_OR_ROLE_REFUSED")
    return document["records"]


def _validate_pins(expected):
    if type(expected) is not dict or set(expected) != SNAPSHOT:
        _deny("INDEPENDENT_TEST_PINS_REQUIRED")
    for key in ("rpmSha256", "entrypointSha256", "exeSha256"):
        if type(expected[key]) is not str or HEX.fullmatch(expected[key]) is None:
            _deny("INDEPENDENT_SHA256_PIN_REFUSED")
    for key in ("pid", "startTicks", "uid", "gid"):
        if type(expected[key]) is not int or not 0 < expected[key] < 2**63:
            _deny("INDEPENDENT_KERNEL_ID_PIN_REFUSED")
    if (expected["pid"] <= 1 or expected["uid"] == 0
            or expected["gid"] == 0
            or expected["unit"] != UNIT or expected["cgroup"] != CGROUP
            or expected["socketPath"] != SOCKET
            or expected["exePath"] != EXECUTABLE
            or expected["selinux"] != SELINUX):
        _deny("INDEPENDENT_IDENTITY_ROLE_OR_DOMAIN_REFUSED")


def inspect_running_denials(*, evidence_line: bytes, signed_receipts,
                            independently_pinned_receipt_key: Ed25519PublicKey,
                            independently_measured: dict):
    """Match four signed denial frames to an independently pinned CI snapshot.

    The caller MUST obtain expected measurements and public signer key from
    outside the guest. This CI test does not prove that obligation was met.
    Nothing accepted here may be promoted into a production host/consent bit.
    """
    _validate_pins(independently_measured)
    if not isinstance(independently_pinned_receipt_key, Ed25519PublicKey):
        _deny("INDEPENDENT_RECEIPT_KEY_REQUIRED")
    if type(signed_receipts) not in (tuple, list) or len(signed_receipts) != 4:
        _deny("EXACT_FOUR_SIGNED_RECEIPTS_REQUIRED")
    records = _decode(evidence_line)
    nonce_seen = set()
    host_instance = None
    for index, action in enumerate(ACTIONS):
        record = records[index]
        if type(record) is not dict or set(record) != RECORD:
            _deny("EVIDENCE_RECORD_FIELDS_REFUSED")
        expected_id = None if action == "BEGIN" else REQUEST_ID
        if (record["action"] != action
                or record["commandRequestId"] != expected_id):
            _deny("DENIAL_ORDER_OR_REQUEST_REFUSED")
        nonce = record["clientNonce"]
        if (type(nonce) is not str or nonce in nonce_seen
                or Receipt._NONCE.fullmatch(nonce) is None):
            _deny("FRESH_UNIQUE_CI_NONCE_REQUIRED")
        nonce_seen.add(nonce)
        # These snapshots must originate from the kernel/systemd via the
        # independently controlled future C4b witness, never a UART claim.
        for name in ("before", "after"):
            snap = record[name]
            if type(snap) is not dict or set(snap) != SNAPSHOT:
                _deny("KERNEL_SNAPSHOT_FIELDS_REFUSED")
            if (any(type(snap[key]) is not type(independently_measured[key])
                    for key in SNAPSHOT)
                    or snap != independently_measured):
                _deny("KERNEL_SNAPSHOT_DIFFERS_FROM_INDEPENDENT_PINS")
        peer = record["peer"]
        if (type(peer) is not dict or set(peer) != {"pid", "uid", "gid"}
                or any(type(peer[k]) is not int for k in peer)
                or peer != {k: independently_measured[k]
                            for k in ("pid", "uid", "gid")}):
            _deny("KERNEL_SOCKET_PEER_MISMATCH")
        frame = signed_receipts[index]
        if type(frame) is not bytes or not 1 <= len(frame) <= 1024:
            _deny("SIGNED_DENIAL_FRAME_REFUSED")
        try:
            receipt = Receipt.verify_receipt(
                frame, pinned_key=independently_pinned_receipt_key,
                action=action, command_request_id=expected_id,
                client_nonce=nonce,
            )
        except Receipt.ReceiptRejected as exc:
            raise Refused("IDENTITY_SIGNED_RECEIPT_REFUSED") from exc
        if (receipt["state"] != "UNAVAILABLE"
                or receipt["requestId"] is not None
                or receipt["sequence"] != index + 1):
            _deny("DENIAL_STATE_OR_SEQUENCE_REFUSED")
        if host_instance is None:
            host_instance = receipt["hostInstance"]
        elif host_instance != receipt["hostInstance"]:
            _deny("IDENTITY_SIGNER_INSTANCE_REPLACED")
    return {
        "schema": SCHEMA,
        "fourKernelSnapshotsAgreeWithCallerPinsInCI": True,
        "fourSignedDenialsConsistentInCI": True,
        "receiptSequenceBoundInCI": True,
        **NEGATIVE,
    }
