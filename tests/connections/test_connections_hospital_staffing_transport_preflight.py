#!/usr/bin/env python3
"""Connections Hospital staffing transport preflight, offline GitHub CI.

No native service, genuine signing, privileged operator, host policy, key,
production login1/Polkit, Hospital database or user machine is used.
Tests use real Linux socketpair kernel credential observations and pin the
Hospital #133 source parser, not a hand-written replacement.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import socket
import sys

if (os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("CI") != "true"
        or not os.environ.get("RUNNER_TEMP")
        or not Path(os.environ["RUNNER_TEMP"]).is_dir()
        or not sys.platform.startswith("linux")):
    raise SystemExit("CONNECTIONS_STAFFING_PREFLIGHT_HOLD // CI_ONLY")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"services/connections/hospital/staffing"))
sys.path.insert(0, str(ROOT/"hospital-source/bin"))
import StaffingTransportPreflight as pre
import px_hospital_staffing_transport as hospital
import px_hospital_staffing_grants as grants
import px_hospital_staffing_native_peer as hospital_kernel

assert pre.REQUEST_SCHEMA == hospital.SCHEMA
assert pre.MAX_FRAME == hospital.MAX_FRAME == hospital_kernel.MAX_PACKET == 16384
assert pre.MAX_GRANT_BYTES == hospital.MAX_GRANT_BYTES == grants.MAX_FRAME == 8192
assert pre.PREPARE_FIELDS == hospital.PREPARE_FIELDS
assert pre.COMMIT_FIELDS == hospital.COMMIT_FIELDS
assert pre.BODY_FIELDS == grants.BODY_FIELDS
assert pre.ALLOWED_ACTIONS == {grants.ATTACH, grants.SUCCEED}
assert pre.GRANT_SCHEMA == grants.SCHEMA
assert pre.AUDIENCE == grants.AUDIENCE


def denied(call, reason):
    try:
        call()
    except pre.PreflightHold as exc:
        assert reason in str(exc), (reason, str(exc))
        return
    raise AssertionError("INVALID_STAFFING_TRANSPORT_ACCEPTED: " + reason)


def b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def build(scope, action=grants.ATTACH):
    prepared = {
        "schema": pre.REQUEST_SCHEMA, "kind": "prepare",
        "action": action, "roomId": scope["roomId"], "intent": scope,
        "requestNonce": b64(b"P"*32),
    }
    writer = "ci-staffing-writer-01"
    body = {
        "schema": pre.GRANT_SCHEMA, "audience": pre.AUDIENCE,
        "operation": action, "scope": scope,
        "roomRevision": 2, "graphDigest": "a"*64,
        "operatorId": "uid:1001", "approvalId": "ci-approval-fixture-01",
        "seatId": "logind-seat0-ciFixture", "hostId": "b"*64,
        "nonce": b64(b"N"*32), "requestNonce": prepared["requestNonce"],
        "writerInstance": writer, "issuedAt": 1760000000,
        "expiresAt": 1760000025, "operatorUid": 1001,
        "polkitActionId": grants.POLKIT_ACTIONS[action],
        "policyGeneration": 3, "clientExecutableSha256": "c"*64,
        "issuerReleaseSha256": "d"*64, "reviewDigest": "e"*64,
    }
    # Deliberately synthetic signature. The composer may check its shape,
    # but cannot verify trust and must NEVER claim it is authorized.
    signature = b64(b"\x91"*64)
    envelope = pre.canonical({"body":body,"signature":signature})
    return pre.canonical(prepared), writer, envelope


scope = dict(roomId="room-ci",patientId="patient-ci",repository="org/repo",
             branch="feature/staffing",bedPath="/tmp/staffing-test",
             assignmentId="1",sessionId="session-ci",doctorId="doctor-ci",
             providerId="provider-ci",mode="create")
original, writer, envelope = build(scope)
assert hospital.parse_request(original)["kind"] == "prepare"
committed = pre.compose_commit(original, writer, envelope)
assert committed == hospital.canonical(hospital.parse_request(committed))
assert hospital.parse_request(committed)["kind"] == "commit"
assert len(committed) < 16384
assert pre.parse_original_prepare(original)["requestNonce"] == b64(b"P"*32)
assert b64(envelope) in committed.decode("ascii")
assert pre.signed_envelope_budget(envelope) == len(envelope)
assert pre.frame_budget(committed) == len(committed)
assert len(b64(b"\x00"*8192)) == 10923

# Budget checks are syntactic ONLY, not permission to accept bogus bytes.
assert pre.frame_budget(b"X"*16384) == 16384
denied(lambda:pre.frame_budget(b"X"*16385),
       "COMPLETE_FRAME_TOO_LARGE_OR_EMPTY")
assert pre.signed_envelope_budget(b"X"*8192) == 8192
denied(lambda:pre.signed_envelope_budget(b"X"*8193),
       "SIGNED_ENVELOPE_TOO_LARGE_OR_EMPTY")
denied(lambda:pre.signed_envelope_budget(b""),
       "SIGNED_ENVELOPE_TOO_LARGE_OR_EMPTY")

# Complete frame can overflow *despite* a <=8192-byte signed envelope.
# This fixture's long Bed is intentionally invalid as a real Hospital
# scope: it exercises the issuer's length gate before any native send.
found_overflow = False
for n in range(5500, 7901, 100):
    big = dict(scope, bedPath="/"+"x"*n)
    large_prepare, large_writer, large_envelope = build(big)
    if len(large_envelope) > pre.MAX_GRANT_BYTES:
        continue
    candidate = dict(json.loads(large_prepare),kind="commit",
                     writerInstance=large_writer,
                     signedEnvelope=b64(large_envelope))
    if len(pre.canonical(candidate)) > pre.MAX_FRAME:
        denied(lambda:pre.compose_commit(
            large_prepare,large_writer,large_envelope),
            "COMPLETE_FRAME_TOO_LARGE_OR_EMPTY")
        found_overflow = True
        break
assert found_overflow, "NEED_INDEPENDENT_WHOLE_FRAME_BUDGET_FIXTURE"

# Changed original PREPARE, writer instance, or grant intent cannot be
# silently reauthorized by the composition helper.
changed = dict(json.loads(original),requestNonce=b64(b"Q"*32))
denied(lambda:pre.compose_commit(
    pre.canonical(changed),writer,envelope),
    "GRANT_NOT_BOUND_TO_ORIGINAL_PREPARE")
denied(lambda:pre.compose_commit(
    original,"another-writer-001",envelope),
    "GRANT_NOT_BOUND_TO_ORIGINAL_PREPARE")
wrong = json.loads(envelope)
wrong["body"]["scope"]["sessionId"] = "different-session"
denied(lambda:pre.compose_commit(
    original,writer,pre.canonical(wrong)),
    "GRANT_NOT_BOUND_TO_ORIGINAL_PREPARE")
wrong = json.loads(envelope)
wrong["body"]["operation"] = grants.SUCCEED
denied(lambda:pre.compose_commit(
    original,writer,pre.canonical(wrong)),
    "GRANT_NOT_BOUND_TO_ORIGINAL_PREPARE")
wrong = json.loads(envelope)
wrong["body"]["polkitActionId"] = "org.postapollo.hospital.room-trash"
# This helper is not a native grant validator! Exact Polkit/action checks
# remain with Hospital's pinned signed grant verifier after signing.
candidate = pre.compose_commit(original,writer,pre.canonical(wrong))
assert hospital.parse_request(candidate)["kind"] == "commit"
# Actual writer verifier refuses the modified signed field, regardless of
# this untrusted syntactic preflight returning candidate bytes.
try:
    grants._body(wrong["body"], now=1760000001)
except grants.StaffingGrantHold as exc:
    assert "STAFFING_POLKIT_ACTION_MISMATCH" in str(exc)
else:
    raise AssertionError("ROOM_TRASH_CROSSED_STAFFING_GRANT_BOUNDARY")

bad = json.loads(envelope)
bad["body"]["schema"] = "post-apollo.hospital.room-lifecycle-grant.v1"
denied(lambda:pre.compose_commit(original,writer,pre.canonical(bad)),
       "GRANT_NOT_BOUND_TO_ORIGINAL_PREPARE")
bad = json.loads(envelope)
bad["signature"] = "!!!"
denied(lambda:pre.compose_commit(original,writer,pre.canonical(bad)),
       "INVALID_ED25519_SIGNATURE_SHAPE")
bad = json.loads(envelope)
bad["unauthorized"] = True
denied(lambda:pre.compose_commit(original,writer,pre.canonical(bad)),
       "EXACT_SIGNED_ENVELOPE_REQUIRED")
denied(lambda:pre.compose_commit(original,writer,envelope+b"\n"),
       "NONCANONICAL_OR_PARTIAL_JSON")
denied(lambda:pre.compose_commit(original,writer,b"{" + b"A"*8192),
       "SIGNED_ENVELOPE_TOO_LARGE_OR_EMPTY")

bad_prepare = dict(json.loads(original),kind="commit")
denied(lambda:pre.compose_commit(
    pre.canonical(bad_prepare),writer,envelope),
    "ORIGINAL_PREPARE_REQUIRED")
bad_prepare = dict(json.loads(original),action="TRASH")
denied(lambda:pre.compose_commit(
    pre.canonical(bad_prepare),writer,envelope),
    "UNKNOWN_ACTION_OR_SCOPE")
bad_prepare = dict(json.loads(original),extra=True)
denied(lambda:pre.compose_commit(
    pre.canonical(bad_prepare),writer,envelope),
    "ORIGINAL_PREPARE_REQUIRED")
denied(lambda:pre.compose_commit(
    original.replace(b'"kind":"prepare"',b'"kind": "prepare"'),
    writer,envelope),"NONCANONICAL_OR_PARTIAL_JSON")

# Real kernel packet identity: this is no enrolled release/seat, merely
# SO_PEERCRED + SCM_CREDENTIALS on disconnected disposable socketpairs.
def pair():
    a,b=socket.socketpair(socket.AF_UNIX,socket.SOCK_SEQPACKET)
    a.settimeout(2)
    b.settimeout(2)
    a.setsockopt(socket.SOL_SOCKET,socket.SO_PASSCRED,1)
    return a,b

a,b=pair()
with a,b:
    b.send(committed)
    got, identity = pre.observe_kernel_packet(a,expected_uid=os.getuid())
    assert got == committed
    assert identity[0] == os.getpid()
    assert identity[1] == os.getuid()

a,b=pair()
with a,b:
    b.send(committed)
    denied(lambda:pre.observe_kernel_packet(a,expected_uid=os.getuid()+1),
           "UNENROLLED_SOCKET_PEER_UID")

a,b=pair()
with a,b:
    b.send(b"X"*16384)
    got,_=pre.observe_kernel_packet(a,expected_uid=os.getuid())
    assert len(got)==16384
a,b=pair()
with a,b:
    b.send(b"X"*16385)
    denied(lambda:pre.observe_kernel_packet(a,expected_uid=os.getuid()),
           "OVERSIZED_OR_TRUNCATED_PACKET")

a,b=pair()
with a,b:
    a.setsockopt(socket.SOL_SOCKET,socket.SO_PASSCRED,0)
    b.send(committed)
    denied(lambda:pre.observe_kernel_packet(a,expected_uid=os.getuid()),
           "PASSCRED_MUST_PRECEDE_SEND")

a,b=socket.socketpair(socket.AF_UNIX,socket.SOCK_STREAM)
with a,b:
    b.send(committed)
    denied(lambda:pre.observe_kernel_packet(a,expected_uid=os.getuid()),
           "UNIX_SEQPACKET_REQUIRED")

# An inherited sender FD is not the original connected process. Linux
# SO_PEERCRED keeps the original PID, SCM_CREDENTIALS names the child.
a,b=pair()
child=os.fork()
if child == 0:
    try:
        a.close()
        b.send(committed)
        os._exit(0)
    except BaseException:
        os._exit(3)
try:
    b.close()
    with a:
        denied(lambda:pre.observe_kernel_packet(a,expected_uid=os.getuid()),
               "PACKET_SENDER_NOT_SOCKET_PEER")
finally:
    _,status=os.waitpid(child,0)
    assert os.WIFEXITED(status) and os.WEXITSTATUS(status)==0

denied(lambda:pre.run_native_issuer(
    operatorConfirmed=True, signedGrant=envelope),
    "STAFFING_NATIVE_ISSUER_NOT_INSTALLED")
assert "room-trash" not in pre.ALLOWED_ACTIONS
assert not hasattr(pre, "load_key")
assert not hasattr(pre, "sign_grant")

print("CONNECTIONS HOSPITAL STAFFING TRANSPORT PREFLIGHT // PASS // exact whole-COMMIT budget, decoded grant limit, original PREPARE, wrong action, Linux peer/packet and truncation refusal; NATIVE ISSUER OFF")
