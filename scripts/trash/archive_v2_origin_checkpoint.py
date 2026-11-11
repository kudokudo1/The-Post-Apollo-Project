#!/usr/bin/env python3
"""V2t Linux cgroup origin witness and independent signed checkpoint fixtures.

Deny-only test contracts: Linux SO_PEERCRED and /proc cgroup are observations,
NOT systemd unit authentication. The externally pinned checkpoint uses only
ephemeral CI keys and is NOT a production authority-controlled monotonic
anchor. No real source/service is accessed or granted ArchiveStore rights.
"""
import base64
import binascii
import hashlib
import json
import os
import re
import socket
import struct

from scripts.trash.archive_v2_peer_evidence import (
    _boot_identity, _start_ticks,
)
from scripts.trash.archive_v2_service_release_history import (
    TestServiceReleaseHistory,
)
from scripts.trash.archive_v2_signed_capture import (
    ALLOWED_OWNERS, AUDIENCE, PURPOSE, Ed25519PublicKey,
    InvalidSignature, KEY_ID, SHA,
)

SCHEMA = "post-apollo.trashpp.fixture-release-checkpoint.v2t"
CHECKPOINT_FIELDS = frozenset((
    "schema", "audience", "purpose", "policyOrigin", "rootKeyId",
    "ownerId", "sequence", "releaseSha256", "grantSha256",
    "issuedAtMs", "validFromMs", "validUntilMs",
))
ORIGIN_POLICY_FIELDS = frozenset((
    "origin", "ownerId", "expectedUid", "expectedGid",
    "expectedCgroupV2",
))
CGROUP_SAFE = re.compile(r"^/[A-Za-z0-9_.:@+\\/-]{0,2047}$")
MAX_GROUP_BYTES = 8192


class FixtureOriginError(Exception):
    """Safe fixed refusal code; no kernel path or command-line details."""


def _need(ok, code):
    if not ok:
        raise FixtureOriginError(code)


def _ms(value):
    return type(value) is int and 1 <= value <= 9999999999999


def _read_cgroup_v2(pid):
    """Read only the kernel's cgroup v2 membership for the peer PID."""
    try:
        with open(f"/proc/{pid}/cgroup", "rb") as source:
            raw = source.read(MAX_GROUP_BYTES + 1)
    except OSError as exc:
        raise FixtureOriginError("ORIGIN_CGROUP_UNAVAILABLE") from exc
    _need(0 < len(raw) <= MAX_GROUP_BYTES, "ORIGIN_CGROUP_LIMIT")
    try:
        lines = raw.decode("ascii").splitlines()
    except UnicodeError as exc:
        raise FixtureOriginError("ORIGIN_CGROUP_INVALID") from exc
    _need(len(lines) == 1 and lines[0].startswith("0::"),
          "ORIGIN_CGROUP_UNSUPPORTED")
    path = lines[0][3:]
    _need(type(path) is str and CGROUP_SAFE.fullmatch(path)
          and all(segment not in (".", "..") for segment in path.split("/"))
          and "//" not in path and (path == "/" or not path.endswith("/")),
          "ORIGIN_CGROUP_INVALID")
    return path


def measure_fixture_origin(connection, witness, policy):
    """Bind the socket peer to its observed cgroup (not service authority).

    Expected policy is supplied by the test broker, never by client JSON.
    The witness was independently measured with SO_PEERCRED and is pinned
    again by the V2p pidfd lease at the eventual synthetic commit.
    """
    _need(type(policy) is dict and set(policy) == ORIGIN_POLICY_FIELDS
          and policy.get("origin") == "TEST_FIXTURE_ONLY",
          "ORIGIN_TRUST_NOT_PROVISIONED")
    _need(type(witness) is dict
          and witness.get("state") == "TEST_KERNEL_PEER_MATCHED_DENY_ONLY"
          and witness.get("captureAllowed") is False
          and witness.get("sourceProcessVerified") is False
          and type(witness.get("peerWitnessSha256")) is str
          and SHA.fullmatch(witness["peerWitnessSha256"]),
          "ORIGIN_PEER_WITNESS_INVALID")
    _need(type(policy["ownerId"]) is str
          and policy["ownerId"] in ALLOWED_OWNERS
          and type(policy["expectedUid"]) is int
          and type(policy["expectedGid"]) is int
          and 0 <= policy["expectedUid"] <= 2**32 - 1
          and 0 <= policy["expectedGid"] <= 2**32 - 1
          and type(policy["expectedCgroupV2"]) is str
          and CGROUP_SAFE.fullmatch(policy["expectedCgroupV2"])
          and all(x not in (".", "..")
                  for x in policy["expectedCgroupV2"].split("/"))
          and "//" not in policy["expectedCgroupV2"]
          and (policy["expectedCgroupV2"] == "/"
               or not policy["expectedCgroupV2"].endswith("/")),
          "ORIGIN_POLICY_INVALID")
    _need(isinstance(connection, socket.socket)
          and connection.family == socket.AF_UNIX
          and (connection.type & socket.SOCK_STREAM) == socket.SOCK_STREAM,
          "ORIGIN_SOCKET_INVALID")
    try:
        creds = struct.unpack("3i", connection.getsockopt(
            socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")))
    except (OSError, struct.error) as exc:
        raise FixtureOriginError("ORIGIN_PEER_UNAVAILABLE") from exc
    _need(creds == (witness.get("pid"), witness.get("uid"),
                    witness.get("gid")),
          "ORIGIN_PEER_CHANGED")
    _need(policy["ownerId"] == witness.get("ownerId")
          and creds[1:] == (policy["expectedUid"], policy["expectedGid"]),
          "ORIGIN_POLICY_MISMATCH")
    try:
        before = _start_ticks(creds[0])
        boot = _boot_identity()
        path = _read_cgroup_v2(creds[0])
        after = _start_ticks(creds[0])
    except FixtureOriginError:
        raise
    except Exception as exc:
        raise FixtureOriginError("ORIGIN_PEER_UNAVAILABLE") from exc
    _need(before == after
          and before == witness.get("startTicks")
          and boot == witness.get("bootId"),
          "ORIGIN_PEER_CHANGED")
    _need(path == policy["expectedCgroupV2"],
          "ORIGIN_CGROUP_MISMATCH")
    data = {
        "ownerId":policy["ownerId"],
        "peerWitnessSha256":witness["peerWitnessSha256"],
        "cgroupSha256":hashlib.sha256(path.encode("ascii")).hexdigest(),
        "bootId":boot,"startTicks":before,"uid":creds[1],"gid":creds[2],
    }
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=True,
                           separators=(",", ":")).encode("ascii")
    return {
        "state":"TEST_CGROUP_OBSERVED_DENY_ONLY",
        "ownerId":policy["ownerId"],
        "originWitnessSha256":hashlib.sha256(canonical).hexdigest(),
        "peerWitnessSha256":witness["peerWitnessSha256"],
        "sourceServiceVerified":False,
        "systemdUnitVerified":False,
        "captureAllowed":False,"productionAllowed":False,
    }


def canonical_checkpoint(checkpoint):
    _need(type(checkpoint) is dict
          and set(checkpoint) == CHECKPOINT_FIELDS,
          "CHECKPOINT_SCHEMA_INVALID")
    _need(checkpoint["schema"] == SCHEMA
          and checkpoint["audience"] == AUDIENCE
          and checkpoint["purpose"] == PURPOSE
          and checkpoint["policyOrigin"] == "TEST_FIXTURE_ONLY",
          "CHECKPOINT_SCOPE_INVALID")
    _need(type(checkpoint["rootKeyId"]) is str
          and KEY_ID.fullmatch(checkpoint["rootKeyId"])
          and type(checkpoint["ownerId"]) is str
          and checkpoint["ownerId"] in ALLOWED_OWNERS
          and type(checkpoint["sequence"]) is int
          and 1 <= checkpoint["sequence"] <= 1000000000
          and type(checkpoint["releaseSha256"]) is str
          and SHA.fullmatch(checkpoint["releaseSha256"])
          and type(checkpoint["grantSha256"]) is str
          and SHA.fullmatch(checkpoint["grantSha256"]),
          "CHECKPOINT_FIELDS_INVALID")
    _need(all(_ms(checkpoint[k]) for k in (
          "issuedAtMs","validFromMs","validUntilMs"))
          and checkpoint["validFromMs"] <= checkpoint["issuedAtMs"]
          < checkpoint["validUntilMs"]
          and checkpoint["validUntilMs"] - checkpoint["validFromMs"]
              <= 24 * 60 * 60 * 1000,
          "CHECKPOINT_TIME_INVALID")
    raw = json.dumps(checkpoint, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True, allow_nan=False).encode("ascii")
    _need(len(raw) <= 2048, "CHECKPOINT_LIMIT")
    return raw


def verify_fixture_checkpoint(signed, pinned_checkpoint_root, *,
                              history, signed_release, release_root,
                              owner_id, grant_sha256, now_ms):
    """Check independently signed expected release against V2s current head.

    The test fixture supplies its checkpoint out-of-band, never from the
    client socket. This is not a protected monotonic external service.
    """
    _need(type(signed) is dict and set(signed) == {"checkpoint","signatureB64"},
          "CHECKPOINT_ENVELOPE_INVALID")
    _need(type(pinned_checkpoint_root) is dict
          and set(pinned_checkpoint_root)
              == {"rootKeyId", "publicKeyBytes", "origin"}
          and pinned_checkpoint_root["origin"] == "EXTERNALLY_PINNED_TEST_ROOT",
          "CHECKPOINT_TRUST_UNPROVISIONED")
    _need(type(history) is TestServiceReleaseHistory,
          "CHECKPOINT_HISTORY_REQUIRED")
    cp = signed["checkpoint"]
    raw = canonical_checkpoint(cp)
    _need(type(pinned_checkpoint_root["rootKeyId"]) is str
          and pinned_checkpoint_root["rootKeyId"] == cp["rootKeyId"]
          and type(pinned_checkpoint_root["publicKeyBytes"]) is bytes
          and len(pinned_checkpoint_root["publicKeyBytes"]) == 32,
          "CHECKPOINT_ROOT_MISMATCH")
    _need(_ms(now_ms) and cp["validFromMs"] <= now_ms < cp["validUntilMs"]
          and cp["issuedAtMs"] <= now_ms + 30000,
          "CHECKPOINT_EXPIRED")
    encoded = signed["signatureB64"]
    _need(type(encoded) is str and len(encoded) == 88,
          "CHECKPOINT_SIGNATURE_INVALID")
    try:
        sig = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise FixtureOriginError("CHECKPOINT_SIGNATURE_INVALID") from exc
    _need(len(sig) == 64
          and base64.b64encode(sig).decode("ascii") == encoded,
          "CHECKPOINT_SIGNATURE_INVALID")
    _need(Ed25519PublicKey is not None,
          "CHECKPOINT_CRYPTO_UNAVAILABLE")
    try:
        Ed25519PublicKey.from_public_bytes(
            pinned_checkpoint_root["publicKeyBytes"]).verify(sig,raw)
    except (InvalidSignature, ValueError) as exc:
        raise FixtureOriginError("CHECKPOINT_SIGNATURE_REFUSED") from exc
    _need(owner_id == cp["ownerId"] and grant_sha256 == cp["grantSha256"],
          "CHECKPOINT_BINDING_MISMATCH")
    current = history.require_current(
        signed_release, release_root,
        owner_id=owner_id, grant_sha256=grant_sha256, now_ms=now_ms)
    _need(current["sequence"] == cp["sequence"]
          and current["releaseSha256"] == cp["releaseSha256"],
          "CHECKPOINT_STALE_OR_CHANGED")
    return {
        "state":"TEST_EXTERNAL_CHECKPOINT_MATCHED_DENY_ONLY",
        "ownerId":owner_id,
        "checkpointSha256":hashlib.sha256(raw).hexdigest(),
        "releaseSha256":current["releaseSha256"],
        "checkpointSignatureVerified":True,
        "independentAnchorVerified":False,
        "sourceServiceVerified":False,
        "captureAllowed":False,"productionAllowed":False,
    }
