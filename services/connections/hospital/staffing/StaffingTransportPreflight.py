#!/usr/bin/env python3
"""Connections / Hospital staffing transport preflight, source-only.

An intentionally uninstalled, unprivileged byte-composition and Linux
peer-observation helper for the proposed staffing issuer. No service, socket
listener, signer, private key, Polkit, login1, Hospital DB or native command
dispatcher is supplied. A matching candidate packet has NO authorization.

The protected writer/Hospital remain the owners of full grant verification,
PREPARE state, durable nonce consumption and Session/Doctor atomic writes.
"""
from __future__ import annotations

import base64
import json
import re
import socket
import struct

REQUEST_SCHEMA = "postapollo.hospital.native-staffing-request.v1"
GRANT_SCHEMA = "post-apollo.hospital.staffing-grant.v1"
AUDIENCE = "px-hospital-native-staffing-v1"
PREPARE = "prepare"
COMMIT = "commit"
ALLOWED_ACTIONS = frozenset(("SESSION_ATTACH", "DOCTOR_SUCCEED"))
MAX_FRAME = 16384
MAX_GRANT_BYTES = 8192
PREPARE_FIELDS = frozenset((
    "schema", "kind", "action", "roomId", "intent", "requestNonce",
))
COMMIT_FIELDS = PREPARE_FIELDS | {"writerInstance", "signedEnvelope"}
BODY_FIELDS = frozenset((
    "schema", "audience", "operation", "scope", "roomRevision",
    "graphDigest", "operatorId", "approvalId", "seatId", "hostId",
    "nonce", "requestNonce", "writerInstance", "issuedAt", "expiresAt",
    "operatorUid", "polkitActionId", "policyGeneration",
    "clientExecutableSha256", "issuerReleaseSha256", "reviewDigest",
))
WRITER = re.compile(r"[A-Za-z0-9_-]{12,128}\Z", re.ASCII)
NONCE = re.compile(r"[A-Za-z0-9_-]{43}\Z", re.ASCII)
SIGNATURE = re.compile(r"[A-Za-z0-9_-]{86}\Z", re.ASCII)
CREDENTIAL_SIZE = struct.calcsize("3i")


class PreflightHold(RuntimeError):
    pass


def hold(reason):
    raise PreflightHold("HOSPITAL_STAFFING_PREFLIGHT_HOLD // " + reason)


def canonical(obj):
    try:
        return json.dumps(
            obj, sort_keys=True, ensure_ascii=True,
            allow_nan=False, separators=(",", ":"),
        ).encode("ascii")
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise PreflightHold(
            "HOSPITAL_STAFFING_PREFLIGHT_HOLD // INVALID_FRAME_CONTENT"
        ) from exc


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            hold("DUPLICATE_JSON_FIELD")
        result[key] = value
    return result


def _nonfinite(_value):
    hold("NONFINITE_JSON_VALUE")


def _exact_json(raw, maximum):
    if type(raw) is not bytes or not 2 <= len(raw) <= maximum:
        hold("FRAME_BOUNDS_EXCEEDED")
    try:
        obj = json.loads(raw.decode("ascii", "strict"),
                         object_pairs_hook=_unique,
                         parse_constant=_nonfinite)
        if type(obj) is not dict or canonical(obj) != raw:
            hold("NONCANONICAL_OR_PARTIAL_JSON")
    except (ValueError, UnicodeError, RecursionError, OverflowError) as exc:
        raise PreflightHold(
            "HOSPITAL_STAFFING_PREFLIGHT_HOLD // INVALID_JSON"
        ) from exc
    return obj


def _decode_b64(value, size):
    if type(value) is not str or not value or "=" in value:
        hold("INVALID_UNPADDED_BASE64URL")
    try:
        data = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, TypeError) as exc:
        raise PreflightHold(
            "HOSPITAL_STAFFING_PREFLIGHT_HOLD // INVALID_UNPADDED_BASE64URL"
        ) from exc
    if (len(data) != size
            or base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")
            != value):
        hold("NONCANONICAL_BASE64URL")
    return data


def frame_budget(raw):
    """Size-only decision, NOT acceptance of a syntactically valid request."""
    if type(raw) is not bytes or not 2 <= len(raw) <= MAX_FRAME:
        hold("COMPLETE_FRAME_TOO_LARGE_OR_EMPTY")
    return len(raw)


def signed_envelope_budget(raw):
    """Budget separately from whole-frame size. No signature verification."""
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_GRANT_BYTES:
        hold("SIGNED_ENVELOPE_TOO_LARGE_OR_EMPTY")
    return len(raw)


def parse_original_prepare(raw):
    """Parse precisely the original PREPARE, not a caller-modified COMMIT."""
    request = _exact_json(raw, MAX_FRAME)
    if set(request) != PREPARE_FIELDS or request.get("kind") != PREPARE:
        hold("ORIGINAL_PREPARE_REQUIRED")
    if (request.get("schema") != REQUEST_SCHEMA
            or request.get("action") not in ALLOWED_ACTIONS
            or type(request.get("roomId")) is not str
            or type(request.get("intent")) is not dict
            or request["intent"].get("roomId") != request["roomId"]):
        hold("UNKNOWN_ACTION_OR_SCOPE")
    nonce = request.get("requestNonce")
    if type(nonce) is not str or NONCE.fullmatch(nonce) is None:
        hold("PREPARE_NONCE_INVALID")
    _decode_b64(nonce, 32)
    return request


def compose_commit(original_prepare_raw, writer_instance, signed_envelope_raw):
    """Create canonical candidate bytes, never sign, deliver or authorize.

    This checks the signed envelope's syntax/claimed binding only. It
    **cannot** prove that its Ed25519 signature is valid, that a real
    operator authorized it or that an installed writer accepted it.
    """
    prepared = parse_original_prepare(original_prepare_raw)
    if (type(writer_instance) is not str
            or WRITER.fullmatch(writer_instance) is None):
        hold("INVALID_PROTECTED_WRITER_INSTANCE")
    signed_envelope_budget(signed_envelope_raw)
    envelope = _exact_json(signed_envelope_raw, MAX_GRANT_BYTES)
    if set(envelope) != {"body", "signature"} or type(envelope["body"]) is not dict:
        hold("EXACT_SIGNED_ENVELOPE_REQUIRED")
    body = envelope["body"]
    if set(body) != BODY_FIELDS:
        hold("WRONG_STAFFING_GRANT_FIELDS")
    if (body.get("schema") != GRANT_SCHEMA
            or body.get("audience") != AUDIENCE
            or body.get("operation") != prepared["action"]
            or body.get("scope") != prepared["intent"]
            or body.get("requestNonce") != prepared["requestNonce"]
            or body.get("writerInstance") != writer_instance):
        hold("GRANT_NOT_BOUND_TO_ORIGINAL_PREPARE")
    signature = envelope["signature"]
    if type(signature) is not str or SIGNATURE.fullmatch(signature) is None:
        hold("INVALID_ED25519_SIGNATURE_SHAPE")
    _decode_b64(signature, 64)
    frame = dict(prepared, kind=COMMIT, writerInstance=writer_instance,
                 signedEnvelope=base64.urlsafe_b64encode(
                     signed_envelope_raw).rstrip(b"=").decode("ascii"))
    encoded = canonical(frame)
    frame_budget(encoded)  # COMPLETE canonical serialized packet, not grant.
    return encoded


def observe_kernel_packet(sock, *, expected_uid):
    """Read-only actual Linux packet identity probe, not permission.

    Takes an *already-connected* Unix seqpacket socket. The caller must
    arm SO_PASSCRED before the sender queues the frame (READY handshake
    ownership is not implemented here). expected_uid is a CI/test input,
    **not** an enrolled signer identity. No production API uses this.
    """
    if (not isinstance(sock, socket.socket)
            or sock.family != socket.AF_UNIX
            or (sock.type & 0xF) != socket.SOCK_SEQPACKET):
        hold("UNIX_SEQPACKET_REQUIRED")
    if type(expected_uid) is not int or expected_uid < 0:
        hold("EXPECTED_UID_NOT_VALIDATED")
    if not all(hasattr(socket, attr) for attr in
               ("SO_PEERCRED", "SO_PASSCRED", "SCM_CREDENTIALS",
                "MSG_TRUNC", "MSG_CTRUNC")):
        hold("LINUX_PACKET_CREDENTIALS_UNAVAILABLE")
    try:
        sock.getpeername()
        raw_peer = sock.getsockopt(
            socket.SOL_SOCKET, socket.SO_PEERCRED, CREDENTIAL_SIZE)
        if len(raw_peer) != CREDENTIAL_SIZE:
            hold("TRUNCATED_SOCKET_PEER")
        peer = struct.unpack("3i", raw_peer)
        if (peer[0] <= 1 or peer[1] != expected_uid
                or peer[2] < 0):
            hold("UNENROLLED_SOCKET_PEER_UID")
        if sock.getsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED) != 1:
            hold("PASSCRED_MUST_PRECEDE_SEND")
        payload, anc, flags, _ = sock.recvmsg(
            MAX_FRAME + 1, socket.CMSG_SPACE(CREDENTIAL_SIZE))
        if (not payload or len(payload) > MAX_FRAME
                or flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC)):
            hold("OVERSIZED_OR_TRUNCATED_PACKET")
        credentials = [
            struct.unpack("3i", value)
            for level, kind, value in anc
            if level == socket.SOL_SOCKET
            and kind == socket.SCM_CREDENTIALS
            and len(value) == CREDENTIAL_SIZE
        ]
        if len(credentials) != 1 or credentials[0] != peer:
            hold("PACKET_SENDER_NOT_SOCKET_PEER")
        if sock.getsockopt(
                socket.SOL_SOCKET, socket.SO_PEERCRED, CREDENTIAL_SIZE
        ) != raw_peer:
            hold("SOCKET_PEER_CHANGED")
        return payload, peer
    except OSError as exc:
        raise PreflightHold(
            "HOSPITAL_STAFFING_PREFLIGHT_HOLD // KERNEL_PACKET_UNAVAILABLE"
        ) from exc


def run_native_issuer(*_args, **_kwargs):
    """There is deliberately no installed native issuer in this package."""
    hold("STAFFING_NATIVE_ISSUER_NOT_INSTALLED")
