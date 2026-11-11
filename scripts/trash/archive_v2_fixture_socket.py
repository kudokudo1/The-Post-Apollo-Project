#!/usr/bin/env python3
"""V2o single-request Unix socket broker PROTOCOL fixture, deny-only.

A caller supplies an ALREADY ACCEPTED AF_UNIX SOCK_STREAM socket, explicit
test-only trust and peer policies, and an isolated V2m/V2n test ledger. This
module never binds/listens, holds keys, imports ArchiveStore, reads source
paths, authorizes capture, or starts as a runtime service. Actual source
owner service UID/script integrity, protected time and permission grants
are NOT established by this fixture.
"""
import base64
import binascii
import json
import re
import socket
import struct

from scripts.trash.archive_v2_broker_handoff import (
    BrokerHandoffError, admit_peer_bound_fixture,
)
from scripts.trash.archive_v2_peer_evidence import inspect_fixture_peer
from scripts.trash.archive_v2_peer_lifecycle import (
    PeerLeaseError, pin_fixture_peer,
)
from scripts.trash.archive_v2_fixture_service_identity import (
    PinnedFixtureServiceFiles, ServiceFixtureError,
)
from scripts.trash.archive_v2_service_grant import (
    ServiceGrantError, verify_fixture_service_grant,
)
from scripts.trash.archive_v2_service_release_history import (
    ServiceReleaseError, TestServiceReleaseHistory,
)
from scripts.trash.archive_v2_origin_checkpoint import (
    FixtureOriginError, measure_fixture_origin,
    verify_fixture_checkpoint,
)
from scripts.trash.archive_v2_owner_trust import OwnerTrustError
from scripts.trash.archive_v2_peer_evidence import BrokerPeerError
from scripts.trash.archive_v2_signed_capture import SignedCaptureError
from scripts.trash.archive_v2_trust_history import (
    TestOwnerTrustHistory, TrustHistoryError,
)
from scripts.trash.archive_v2_atomic_admission import AtomicAdmissionError

WIRE_SCHEMA = "post-apollo.trashpp.fixture-broker.v2o"
MAX_WIRE_BYTES = 262144
MAX_PAYLOAD_BYTES = 131072
SOCKET_TIMEOUT_SECONDS = 2
FIELDS = frozenset(("schema", "ownerId", "resourceId", "sourceRevision",
                    "sourceCapturedAtMs", "payloadB64",
                    "signedManifest", "signedClaim"))
HASH = re.compile(r"^[0-9a-f]{64}$")
IDENTITY = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
SAFE_CODE = re.compile(r"^[A-Z0-9_]{1,80}$")


class FixtureWireError(Exception):
    """Bounded safe rejection without request data, paths or key bytes."""


def _require(condition, code):
    if not condition:
        raise FixtureWireError(code)


def _one_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise FixtureWireError("BROKER_DUPLICATE_FIELD")
        obj[key] = value
    return obj


def _exact_receive(sock, length):
    result = bytearray()
    while len(result) < length:
        try:
            chunk = sock.recv(length - len(result))
        except socket.timeout as exc:
            raise FixtureWireError("BROKER_FRAME_TIMEOUT") from exc
        except OSError as exc:
            raise FixtureWireError("BROKER_FRAME_READ_FAILED") from exc
        _require(len(chunk) > 0, "BROKER_FRAME_TRUNCATED")
        result.extend(chunk)
    return bytes(result)


def decode_fixture_request(raw):
    """Require canonical ASCII JSON and exact fields, never arbitrary paths."""
    _require(type(raw) is bytes and 0 < len(raw) <= MAX_WIRE_BYTES,
             "BROKER_FRAME_LIMIT")
    try:
        packet = json.loads(raw.decode("ascii"), object_pairs_hook=_one_object)
    except (UnicodeError, ValueError, RecursionError, TypeError) as exc:
        raise FixtureWireError("BROKER_JSON_INVALID") from exc
    _require(type(packet) is dict and set(packet) == FIELDS
             and packet["schema"] == WIRE_SCHEMA,
             "BROKER_REQUEST_SCHEMA_INVALID")
    # A signed source claim still gets validated by Ed25519 later. Strict
    # canonical wire encoding prevents multiple representations and excess
    # field smuggling at the IPC boundary.
    _require(json.dumps(packet, sort_keys=True, ensure_ascii=True,
                        allow_nan=False, separators=(",", ":")).encode("ascii")
             == raw, "BROKER_WIRE_NONCANONICAL")
    _require(type(packet["ownerId"]) is str
             and packet["ownerId"] in ("demo-scrape", "weather-events")
             and type(packet["resourceId"]) is str
             and IDENTITY.fullmatch(packet["resourceId"])
             and type(packet["sourceRevision"]) is str
             and HASH.fullmatch(packet["sourceRevision"])
             and type(packet["sourceCapturedAtMs"]) is int
             and 1 <= packet["sourceCapturedAtMs"] <= 9999999999999
             and type(packet["signedManifest"]) is dict
             and type(packet["signedClaim"]) is dict,
             "BROKER_REQUEST_FIELDS_INVALID")
    encoded = packet["payloadB64"]
    _require(type(encoded) is str and len(encoded) <= 4*((MAX_PAYLOAD_BYTES+2)//3),
             "BROKER_PAYLOAD_LIMIT")
    try:
        payload = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise FixtureWireError("BROKER_PAYLOAD_INVALID") from exc
    _require(0 < len(payload) <= MAX_PAYLOAD_BYTES,
             "BROKER_PAYLOAD_LIMIT")
    _require(base64.b64encode(payload).decode("ascii") == encoded,
             "BROKER_PAYLOAD_INVALID")
    return packet, payload


def read_fixture_frame(connection):
    _require(isinstance(connection, socket.socket)
             and connection.family == socket.AF_UNIX
             and connection.type & socket.SOCK_STREAM == socket.SOCK_STREAM,
             "BROKER_SOCKET_UNSUPPORTED")
    header = _exact_receive(connection, 4)
    length = struct.unpack("!I", header)[0]
    _require(0 < length <= MAX_WIRE_BYTES, "BROKER_FRAME_LIMIT")
    return decode_fixture_request(_exact_receive(connection, length))


def encode_fixture_frame(packet):
    """Test-client helper; does not sign anything or open a socket."""
    _require(type(packet) is dict, "BROKER_REQUEST_SCHEMA_INVALID")
    try:
        raw = json.dumps(packet, sort_keys=True, ensure_ascii=True,
                         allow_nan=False, separators=(",", ":")).encode("ascii")
    except (ValueError, TypeError, RecursionError) as exc:
        raise FixtureWireError("BROKER_JSON_INVALID") from exc
    # Shared decoder ensures the helper can't secretly add caller metadata.
    decode_fixture_request(raw)
    return struct.pack("!I",len(raw)) + raw


def _safe_reply(result):
    return {"ok": True, "state":"TEST_IPC_COPY_RECORDED_DENY_ONLY",
            "receiptId":result["snapshotId"],
            "peerWitnessSha256":result["peerWitnessSha256"],
            "requestBindingSha256":result["requestBindingSha256"],
            "syntheticCopyRecorded":True,
            "sourceProcessVerified":False,
            "humanConsentVerified":False,
            "archiveCopyAuthorized":False,
            "peerLifetimeCheckedBeforeCommit":True,
            "serviceWitnessSha256":result["serviceWitnessSha256"],
            "serviceGrantSha256":result["serviceGrantSha256"],
            "serviceReleaseSha256":result["serviceReleaseSha256"],
            "originWitnessSha256":result["originWitnessSha256"],
            "checkpointSha256":result["checkpointSha256"],
            "cgroupObservedBeforeCommit":bool(result["originWitnessSha256"]),
            "externalCheckpointChecked":bool(result["checkpointSha256"]),
            "systemdUnitVerified":False,
            "releaseFloorChecked":bool(result["serviceReleaseSha256"]),
            "signedServiceGrantChecked":bool(result["serviceGrantSha256"]),
            "serviceFilesMatchedBeforeCommit":
                bool(result["serviceWitnessSha256"]),
            "captureAllowed":False,
            "restoreAllowed":False,
            "burnAllowed":False,
            "productionAllowed":False}


def handle_fixture_connection(connection, *, peer_policy, pinned_test_root,
                              ledger, now_ms, service_files=None,
                              signed_service_grant=None,
                              signed_service_release=None,
                              service_release_history=None,
                              origin_policy=None,
                              signed_checkpoint=None, checkpoint_root=None):
    """Handle ONE framed request and reply; no loop, listener or live keys.

    A successful result admits a TEST ledger copy only. All failures produce
    fixed error codes and do not disclose private payload or source paths.
    The caller owns connection lifecycle and separately provides test time.
    """
    _require(type(ledger) is TestOwnerTrustHistory,
             "BROKER_TEST_LEDGER_REQUIRED")
    _require(isinstance(connection, socket.socket),
             "BROKER_SOCKET_UNSUPPORTED")
    previous_timeout = connection.gettimeout()
    try:
        connection.settimeout(SOCKET_TIMEOUT_SECONDS)
        try:
            packet, payload = read_fixture_frame(connection)
            _require(type(peer_policy) is dict
                     and packet["ownerId"] == peer_policy.get("ownerId"),
                     "BROKER_OWNER_PEER_MISMATCH")
            # Pin the original connected process with a kernel pidfd.
            # Fail-closed if pidfd is unsupported or the peer exits before
            # the nonce+synthetic copy transaction commits.
            witness = inspect_fixture_peer(connection, peer_policy)
            if origin_policy is not None:
                origin_evidence = measure_fixture_origin(
                    connection, witness, origin_policy)
                origin_digest = origin_evidence["originWitnessSha256"]
            else:
                origin_digest = ""
            _require((signed_checkpoint is None and checkpoint_root is None)
                     or (signed_checkpoint is not None
                         and checkpoint_root is not None
                         and signed_service_release is not None
                         and type(service_release_history)
                             is TestServiceReleaseHistory),
                     "CHECKPOINT_COMPONENTS_REQUIRED")
            _require(signed_service_grant is None or service_files is not None,
                     "SERVICE_GRANT_FILES_REQUIRED")
            if service_files is not None:
                _require(type(service_files) is PinnedFixtureServiceFiles,
                         "BROKER_SERVICE_FIXTURE_REQUIRED")
                service_evidence = service_files.check_connection(connection)
                _require(service_evidence["ownerId"] == packet["ownerId"],
                         "BROKER_SERVICE_OWNER_MISMATCH")
                service_digest = service_evidence["serviceWitnessSha256"]
            else:
                service_digest = ""
            _require((signed_service_release is None and
                      service_release_history is None)
                     or (signed_service_release is not None
                         and signed_service_grant is not None
                         and type(service_release_history)
                             is TestServiceReleaseHistory),
                     "RELEASE_FLOOR_REQUIRED")
            if signed_service_grant is not None:
                grant_evidence = verify_fixture_service_grant(
                    signed_service_grant, pinned_test_root, service_files,
                    packet["signedManifest"], now_ms=now_ms)
                _require(grant_evidence["ownerId"] == packet["ownerId"]
                         and grant_evidence["serviceWitnessSha256"]
                             == service_digest,
                         "SERVICE_GRANT_BINDING_MISMATCH")
                grant_digest = grant_evidence["serviceGrantSha256"]
            else:
                grant_digest = ""
            if signed_service_release is not None:
                release_evidence = service_release_history.require_current(
                    signed_service_release, pinned_test_root,
                    owner_id=packet["ownerId"],
                    grant_sha256=grant_digest, now_ms=now_ms)
                release_digest = release_evidence["releaseSha256"]
            else:
                release_digest = ""
            if signed_checkpoint is not None:
                checkpoint_evidence = verify_fixture_checkpoint(
                    signed_checkpoint, checkpoint_root,
                    history=service_release_history,
                    signed_release=signed_service_release,
                    release_root=pinned_test_root,
                    owner_id=packet["ownerId"],
                    grant_sha256=grant_digest, now_ms=now_ms)
                checkpoint_digest = checkpoint_evidence["checkpointSha256"]
            else:
                checkpoint_digest = ""
            with pin_fixture_peer(connection, witness) as lifetime:
                lifetime.require_alive()
                def before_fixture_commit():
                    lifetime.require_alive()
                    if service_files is not None:
                        latest = service_files.check_connection(connection)
                        _require(latest["serviceWitnessSha256"] == service_digest,
                                 "BROKER_SERVICE_WITNESS_CHANGED")
                    if signed_service_grant is not None:
                        checked_grant = verify_fixture_service_grant(
                            signed_service_grant, pinned_test_root,
                            service_files, packet["signedManifest"], now_ms=now_ms)
                        _require(checked_grant["serviceGrantSha256"] == grant_digest,
                                 "BROKER_GRANT_CHANGED")
                    if origin_policy is not None:
                        latest_origin = measure_fixture_origin(
                            connection, witness, origin_policy)
                        _require(latest_origin["originWitnessSha256"] == origin_digest,
                                 "BROKER_ORIGIN_CHANGED")
                    if signed_service_release is not None:
                        checked_release = service_release_history.require_current(
                            signed_service_release, pinned_test_root,
                            owner_id=packet["ownerId"],
                            grant_sha256=grant_digest, now_ms=now_ms)
                        _require(checked_release["releaseSha256"] == release_digest,
                                 "BROKER_RELEASE_CHANGED")
                    if signed_checkpoint is not None:
                        latest_checkpoint = verify_fixture_checkpoint(
                            signed_checkpoint, checkpoint_root,
                            history=service_release_history,
                            signed_release=signed_service_release,
                            release_root=pinned_test_root,
                            owner_id=packet["ownerId"],
                            grant_sha256=grant_digest, now_ms=now_ms)
                        _require(latest_checkpoint["checkpointSha256"] ==
                                 checkpoint_digest, "BROKER_CHECKPOINT_CHANGED")
                admitted = admit_peer_bound_fixture(
                    connection, peer_policy,
                    packet["signedManifest"], pinned_test_root,
                    packet["signedClaim"], ledger=ledger,
                    owner_id=packet["ownerId"],
                    resource_id=packet["resourceId"],
                    source_revision=packet["sourceRevision"],
                    source_captured_ms=packet["sourceCapturedAtMs"],
                    payload=payload, now_ms=now_ms,
                    commit_guard=before_fixture_commit,
                    expected_peer_witness_sha256=witness["peerWitnessSha256"],
                    service_witness_sha256=service_digest,
                    service_grant_sha256=grant_digest,
                    service_release_sha256=release_digest,
                    origin_witness_sha256=origin_digest,
                    checkpoint_sha256=checkpoint_digest)
            _require(admitted["captureAllowed"] is False
                     and admitted["productionAllowed"] is False
                     and admitted["sourceProcessVerified"] is False,
                     "BROKER_UNEXPECTED_PRIVILEGE")
            result = _safe_reply(admitted)
        except (FixtureWireError, BrokerHandoffError, BrokerPeerError,
                PeerLeaseError, ServiceFixtureError, ServiceGrantError,
                ServiceReleaseError, FixtureOriginError, SignedCaptureError,
                OwnerTrustError,
                TrustHistoryError, AtomicAdmissionError) as exc:
            code = str(exc)
            result = {"ok":False, "error":code if SAFE_CODE.fullmatch(code)
                      else "BROKER_REQUEST_REFUSED"}
        except Exception:
            result = {"ok":False, "error":"BROKER_REQUEST_REFUSED"}
        # No payload bytes or caller-supplied text are returned.
        raw = json.dumps(result, sort_keys=True, ensure_ascii=True,
                         separators=(",", ":")).encode("ascii")
        _require(len(raw) < 4096, "BROKER_REPLY_LIMIT")
        try:
            connection.sendall(struct.pack("!I",len(raw)) + raw)
        except OSError:
            # Lost reply after commit is resolved by V2m read-only witness.
            pass
        return result
    finally:
        connection.settimeout(previous_timeout)
