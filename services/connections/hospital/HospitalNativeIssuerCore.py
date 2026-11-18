#!/usr/bin/env python3
"""Native Hospital Room signer core, intended ONLY for a separately approved service.

No key provisioning, installer, command-line grant issuance, CI environment
override, PX database access or QML authority exists here. The installed
native service MUST derive its inputs from kernel peer credentials, real
logind, interactive per-operation polkit and a separate protected PX writer.
A signed response never returns to the unprivileged caller: the writer alone
receives it and performs the source transaction.

Real signing code is implemented; it fails closed without separate operator
key-custody, authenticated human consent, protected source/writer and approved
native installation. Cryptographic consistency is NOT a deployment approval.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

PX_DOMAIN = b"post-apollo.hospital.room-lifecycle-grant.v1\x00"
PX_SCHEMA = "post-apollo.hospital.room-lifecycle-grant.v1"
PX_AUDIENCE = "px-hospital-room-lifecycle-v12"
REQUEST_SCHEMA = "postapollo.connections.hospital.native-request.v1"
PREPARED_SCHEMA = "postapollo.hospital.protected-writer-prepared.v1"
RECEIPT_SCHEMA = "postapollo.hospital.protected-writer-receipt.v1"
RUNTIME_POLICY_SCHEMA = "postapollo.connections.hospital-native-issuer-policy.v1"
POLICY_PATH = "/etc/post-apollo/hospital/issuer-runtime-policy.json"
KEY_PATH = "/etc/post-apollo/hospital/issuer.key"
PUBLIC_PATH = "/etc/post-apollo/hospital/room-lifecycle-issuer.pub"
WRITER_SOCKET = "/run/post-apollo/hospital/px-writer.sock"
REQUEST_FIELDS = frozenset({"schema", "action", "roomId"})
POLICY_FIELDS = frozenset({
    "schema", "operatorUid", "clientExecutableSha256",
    "pxWriterUid", "pxWriterExecutableSha256",
    "hostId", "minimumPolicyGeneration", "expiresAt",
})
PREPARED_FIELDS = frozenset({
    "schema", "requestNonce", "action", "roomId", "patientId",
    "repository", "expectedRevision", "expectedDigest", "state",
    "blockers", "canTrash", "canRestore",
    "retentionApproved", "legalHold", "policyGeneration",
    "writerInstance", "expiresAt",
})
RECEIPT_FIELDS = frozenset({
    "schema", "requestNonce", "roomId", "action", "revisionAfter",
    "grantDigest", "state", "originalPreserved", "burnAllowed",
})
ROOM = re.compile(r"[A-Za-z0-9._:/-]{1,160}\Z", re.ASCII)
NAME = re.compile(r"[A-Za-z0-9_.:@/-]{1,96}\Z", re.ASCII)
ID = re.compile(r"[A-Za-z0-9_-]{12,128}\Z", re.ASCII)
SHA = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
HEX_ID = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)

class Refused(ValueError):
    pass

def deny(code):
    raise Refused("HOSPITAL_NATIVE_HOLD // " + code)

def _unique(pairs):
    value = {}
    for k, v in pairs:
        if k in value:
            deny("DUPLICATE_FIELD")
        value[k] = v
    return value

def canonical(value):
    try:
        return json.dumps(value, ensure_ascii=True, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("ascii")
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError) as exc:
        raise Refused("HOSPITAL_NATIVE_HOLD // JSON_ENCODING_REFUSED") from exc

def parse_exact(raw, fields, ceiling=8192):
    if type(raw) is not bytes or not 2 <= len(raw) <= ceiling:
        deny("FRAME_BOUNDS_REFUSED")
    try:
        obj = json.loads(raw.decode("ascii"), object_pairs_hook=_unique,
                         parse_constant=lambda _: deny("NONFINITE_REFUSED"))
        if type(obj) is not dict or set(obj) != fields or canonical(obj) != raw:
            deny("NONCANONICAL_OR_PARTIAL_FRAME_REFUSED")
        return obj
    except (UnicodeError, ValueError, OverflowError, TypeError, RecursionError) as exc:
        raise Refused("HOSPITAL_NATIVE_HOLD // FRAME_REFUSED") from exc

def b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

def validate_request(raw):
    obj = parse_exact(raw, REQUEST_FIELDS, 512)
    if (obj["schema"] != REQUEST_SCHEMA
            or type(obj["action"]) is not str
            or obj["action"] not in ("TRASH", "RESTORE")
            or type(obj["roomId"]) is not str
            or ROOM.fullmatch(obj["roomId"]) is None):
        deny("UNKNOWN_ROOM_OR_OPERATION")
    return obj

def _owner_only_bytes(path: str, length: int, ceiling: int):
    """Read fixed root-owned single-link file; reject symlinks and weak parents.

    Real privileged deployment must additionally pin its release and SELinux
    policy; these local POSIX checks are not proof of external key custody.
    """
    if type(path) is not str or not path.startswith("/etc/post-apollo/hospital/"):
        deny("OWNER_FILE_PATH_UNEXPECTED")
    p = Path(path)
    for ancestor in (p.parent, p.parent.parent, p.parent.parent.parent):
        try:
            st = ancestor.lstat()
        except OSError as exc:
            raise Refused("HOSPITAL_NATIVE_HOLD // PROTECTED_PARENT_MISSING") from exc
        if (not stat.S_ISDIR(st.st_mode) or st.st_uid != 0
                or stat.S_IMODE(st.st_mode) & 0o022):
            deny("WEAK_OWNER_DIRECTORY_OR_SYMLINK")
    fd = None
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != 0
                or st.st_nlink != 1
                or stat.S_IMODE(st.st_mode) != 0o600
                or st.st_size < length or st.st_size > ceiling):
            deny("UNPROTECTED_OWNER_FILE")
        raw = os.read(fd, ceiling + 1)
        after = os.fstat(fd)
        if (len(raw) != st.st_size
                or (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
                != (after.st_dev, after.st_ino, after.st_size,
                    after.st_mtime_ns, after.st_ctime_ns)):
            deny("OWNER_FILE_CHANGED")
        return raw
    except OSError as exc:
        raise Refused("HOSPITAL_NATIVE_HOLD // OWNER_FILE_UNAVAILABLE") from exc
    finally:
        if fd is not None:
            os.close(fd)

def read_policy():
    doc = parse_exact(_owner_only_bytes(POLICY_PATH, 10, 4096), POLICY_FIELDS, 4096)
    if doc["schema"] != RUNTIME_POLICY_SCHEMA:
        deny("POLICY_SCHEMA_REFUSED")
    for key in ("operatorUid", "pxWriterUid", "minimumPolicyGeneration"):
        if (type(doc[key]) is not int or not 0 < doc[key] < 2**31):
            deny("POLICY_UID_OR_FLOOR_REFUSED")
    for key in ("clientExecutableSha256", "pxWriterExecutableSha256", "hostId"):
        if type(doc[key]) is not str or SHA.fullmatch(doc[key]) is None:
            deny("POLICY_DIGEST_OR_HOST_REFUSED")
    if (type(doc["expiresAt"]) is not int
            or doc["expiresAt"] < int(time.time())
            or doc["expiresAt"] >= 2**63):
        deny("ISSUER_POLICY_EXPIRED")
    return doc

def load_installed_key():
    if os.geteuid() != 0:
        deny("NOT_PRIVILEGED_NATIVE_ISSUER")
    raw = _owner_only_bytes(KEY_PATH, 32, 32)
    if len(raw) != 32:
        deny("PRIVATE_KEY_LENGTH_REFUSED")
    pub = _owner_only_bytes(PUBLIC_PATH, 32, 32)
    if len(pub) != 32:
        deny("PUBLIC_KEY_LENGTH_REFUSED")
    try:
        key = Ed25519PrivateKey.from_private_bytes(raw)
        expected = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    except (TypeError, ValueError) as exc:
        raise Refused("HOSPITAL_NATIVE_HOLD // INSTALLED_KEY_INVALID") from exc
    if not __import__("hmac").compare_digest(expected, pub):
        deny("ISSUER_PUBLIC_ROOT_NOT_PINNED_TO_PRIVATE_KEY")
    return key

def validate_prepared(raw, request, nonce, policy, now):
    doc = parse_exact(raw, PREPARED_FIELDS)
    if (doc["schema"] != PREPARED_SCHEMA
            or doc["requestNonce"] != nonce
            or doc["action"] != request["action"]
            or doc["roomId"] != request["roomId"]
            or type(doc["patientId"]) is not str
            or NAME.fullmatch(doc["patientId"]) is None
            or type(doc["repository"]) is not str
            or not 1 <= len(doc["repository"]) <= 256
            or any(not 33 <= ord(ch) <= 126 for ch in doc["repository"])
            or type(doc["expectedRevision"]) is not int
            or not 0 <= doc["expectedRevision"] < 1_000_000_000
            or type(doc["expectedDigest"]) is not str
            or SHA.fullmatch(doc["expectedDigest"]) is None
            or doc["blockers"] != []
            or doc["retentionApproved"] is not True
            or doc["legalHold"] is not False
            or type(doc["policyGeneration"]) is not int
            or doc["policyGeneration"] < policy["minimumPolicyGeneration"]
            or type(doc["writerInstance"]) is not str
            or ID.fullmatch(doc["writerInstance"]) is None
            or type(doc["expiresAt"]) is not int
            or not now < doc["expiresAt"] <= now + 60):
        deny("UNTRUSTED_OR_STALE_PROTECTED_PX_REVIEW")
    if request["action"] == "TRASH":
        if doc["state"] != "ACTIVE" or doc["canTrash"] is not True or doc["canRestore"] is not False:
            deny("PX_TRASH_BLOCKED")
    else:
        if doc["state"] != "TRASHED" or doc["canRestore"] is not True or doc["canTrash"] is not False:
            deny("PX_RESTORE_BLOCKED")
    return doc

def host_fingerprint():
    """Match PX's installed_host_binding() domain construction exactly."""
    raw = _owner_only_bytes("/etc/post-apollo/hospital/issuer-runtime-policy.json", 10, 4096)
    # Re-reading policy only ensures configuration remains available; host
    # binding itself is derived from root-owned /etc/machine-id below.
    if not raw:
        deny("POLICY_UNAVAILABLE")
    path = "/etc/machine-id"
    fd = None
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_size > 128:
            deny("UNTRUSTED_MACHINE_ID")
        data = os.read(fd, 129).strip()
    except OSError as exc:
        raise Refused("HOSPITAL_NATIVE_HOLD // MACHINE_ID_UNAVAILABLE") from exc
    finally:
        if fd is not None:
            os.close(fd)
    if not re.fullmatch(rb"[0-9a-f]{32}", data):
        deny("MACHINE_ID_INVALID")
    return hashlib.sha256(PX_DOMAIN + bytes.fromhex(data.decode("ascii"))).hexdigest()

def sign_px_grant(*, request, prepared, operator_uid, seat_id, host_id, private_key,
                  nonce_bytes=None, approval_bytes=None, now=None):
    """Sign only after native process/seat/polkit and protected PX review gates.

    The privileged service never exposes this function through an IPC command
    or accepts a caller-provided key. Synthetic inputs are available to unit
    tests of wire compatibility; a test result is not a grant.
    """
    if type(operator_uid) is not int or operator_uid <= 0:
        deny("OPERATOR_UID_UNVERIFIED")
    if type(seat_id) is not str or ID.fullmatch(seat_id) is None:
        deny("NATIVE_SEAT_UNVERIFIED")
    if type(host_id) is not str or HEX_ID.fullmatch(host_id) is None:
        deny("HOST_UNVERIFIED")
    if not isinstance(private_key, Ed25519PrivateKey):
        deny("ISSUER_KEY_UNAVAILABLE")
    now = int(time.time()) if now is None else now
    if type(now) is not int:
        deny("TIME_REFUSED")
    if prepared["expiresAt"] <= now:
        deny("STALE_PX_REVIEW")
    nonce = os.urandom(32) if nonce_bytes is None else nonce_bytes
    approval = os.urandom(18) if approval_bytes is None else approval_bytes
    if type(nonce) is not bytes or len(nonce) != 32 or type(approval) is not bytes or len(approval) != 18:
        deny("ISSUER_RANDOMNESS_REFUSED")
    body = {
        "schema": PX_SCHEMA, "audience": PX_AUDIENCE,
        "action": request["action"], "roomId": prepared["roomId"],
        "patientId": prepared["patientId"], "repository": prepared["repository"],
        "expectedRevision": prepared["expectedRevision"],
        "expectedDigest": prepared["expectedDigest"],
        "operatorId": "uid:" + str(operator_uid),
        "approvalId": b64(approval),
        "seatId": seat_id,
        "hostId": host_id,
        "retentionApproved": True,
        "nonce": b64(nonce),
        "issuedAt": now,
        "expiresAt": min(now + 30, prepared["expiresAt"]),
    }
    signature = private_key.sign(PX_DOMAIN + canonical(body))
    encoded = canonical({"body": body, "signature": b64(signature)})
    if len(encoded) > 4096:
        deny("PX_SIGNED_FRAME_TOO_LARGE")
    return encoded

def validate_commit_receipt(raw, *, request, prepared, nonce, signed_grant):
    value = parse_exact(raw, RECEIPT_FIELDS)
    body = parse_exact(signed_grant, frozenset({"body", "signature"}))["body"]
    expected = {
        "schema": RECEIPT_SCHEMA, "requestNonce": nonce,
        "roomId": request["roomId"], "action": request["action"],
        "revisionAfter": prepared["expectedRevision"] + 1,
        "grantDigest": hashlib.sha256(
            PX_DOMAIN + canonical(body)).hexdigest(),
        "state": "TRASHED" if request["action"] == "TRASH" else "ACTIVE",
        "originalPreserved": True, "burnAllowed": False,
    }
    if value != expected:
        deny("PROTECTED_WRITER_RECEIPT_MISMATCH")
    return {
        "schema": "postapollo.connections.hospital-native-issuer-response.v1",
        "status": "COMMITTED",
        "action": request["action"], "roomId": request["roomId"],
        "revision": value["revisionAfter"],
        "originalPreserved": True, "burnAllowed": False,
    }
