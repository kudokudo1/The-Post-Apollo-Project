#!/usr/bin/env python3
"""C3e/TimeW Linux socket sender custody, never Brave window authority.

A connected Unix packet socket lets the Linux kernel identify the process
that sent a packet. That process is a native bridge endpoint, NOT necessarily
the Brave window or Wayland surface described by an unrelated pairing. A
real SO_PEERPIDFD lease and SCM_CREDENTIALS check are useful negative evidence,
but cannot supply independent signer enrollment or browser-surface binding.
CI-only. No signer, socket listener, Sway command, or production handler.
"""
from __future__ import annotations

import hashlib
import json
import socket
import struct

import TimeWBraveSwayIdentityPreflight as Window
import MachineBraveProcessLease as Lease

SCHEMA = "postapollo.connections.c3e-timew-linux-peer-observation.ci-v1"
KIND = "observe-packet-sender-only"
STATUS = "KERNEL_NATIVE_PEER_OBSERVED_BUT_BRAVE_SURFACE_UNPROVEN"
MAX_PACKET = 1024
FIELDS = frozenset(("schema", "kind", "challengeSha256", "pairSha256"))
DENIED = {
    "rootEnrolledNativePeerVerified": False,
    "installedNativeBridgeReleaseVerified": False,
    "braveBrowserProcessProven": False,
    "nativePeerIsBraveWindowProven": False,
    "browserWindowReferenceAuthenticated": False,
    "independentlyAuthenticatedSwaySocket": False,
    "braveWaylandSurfaceBindingVerified": False,
    "activeSeatOrConsentVerified": False,
    "timewOneUseGrantIssued": False,
    "canSignNativePairing": False,
    "canMoveWindow": False,
    "canRestoreBrave": False,
    "productionAuthority": False,
}


class PeerRefused(ValueError):
    pass


def _deny(reason):
    raise PeerRefused("C3E_TIMEW_PEER_HOLD // " + reason)


def _unique_pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate field")
        obj[key] = value
    return obj


def make_packet_ci_only(*, challenge: bytes, pair_payload_sha256: str) -> bytes:
    """Candidate fixture frame, no authentication or signing."""
    if type(challenge) is not bytes or len(challenge) != 32:
        _deny("EXTERNAL_CHALLENGE_REQUIRED")
    if (type(pair_payload_sha256) is not str
            or Window.HEX.fullmatch(pair_payload_sha256) is None):
        _deny("SIGNED_PAIR_DIGEST_REQUIRED")
    return json.dumps({
        "schema": SCHEMA, "kind": KIND,
        "challengeSha256": hashlib.sha256(challenge).hexdigest(),
        "pairSha256": pair_payload_sha256,
    },sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("ascii")


def inspect_kernel_peer_ci_only(*, receiver: socket.socket,
                                independently_expected_uid: int,
                                independently_issued_challenge: bytes,
                                pairing_inputs: dict):
    """Observe one genuine Linux peer+packet, then a synthetic TimeW pair.

    Both 'independently' named values are CALLER-SUPPLIED CI inputs. The
    kernel facts authenticate only the observed socket endpoint, not the
    source of those expectations, not the Brave renderer and not Sway.
    """
    if (type(receiver) is not socket.socket
            or type(independently_expected_uid) is not int
            or independently_expected_uid < 0):
        _deny("UNTRUSTED_PEER_POLICY")
    if (type(independently_issued_challenge) is not bytes
            or len(independently_issued_challenge) != 32):
        _deny("EXTERNAL_CHALLENGE_REQUIRED")
    if type(pairing_inputs) is not dict:
        _deny("PAIR_INPUTS_REQUIRED")
    try:
        if receiver.family != socket.AF_UNIX or receiver.type & 15 != socket.SOCK_SEQPACKET:
            _deny("UNEXPECTED_SOCKET_TYPE")
        raw = receiver.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12)
        pid,uid,gid = struct.unpack("3i",raw)
        if pid <= 1 or uid != independently_expected_uid or gid < 0:
            _deny("KERNEL_PEER_NOT_ENROLLED_IN_CI")
        peer = type("Peer", (), {"pid":pid,"uid":uid,"gid":gid})()
        with Lease.capture_socket_peer(receiver,peer=peer) as custody:
            if not custody.valid():
                _deny("PEER_LEASE_INVALID")
            packet, control, flags, address = receiver.recvmsg(
                MAX_PACKET + 1, socket.CMSG_SPACE(struct.calcsize("3i")))
            if (flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC)
                    or not 0 < len(packet) <= MAX_PACKET or address):
                _deny("PACKET_TRUNCATED_OVERSIZED_OR_WRONG_ORIGIN")
            credentials = []
            for level, kind, cdata in control:
                if level == socket.SOL_SOCKET and kind == socket.SCM_CREDENTIALS:
                    if len(cdata) != 12:
                        _deny("INVALID_PACKET_CREDENTIALS")
                    credentials.append(struct.unpack("3i",cdata))
            if len(credentials) != 1 or credentials[0] != (pid,uid,gid):
                _deny("INHERITED_FD_OR_MISSING_PACKET_CREDENTIALS")
            if not custody.valid():
                _deny("PEER_LEASE_CHANGED_DURING_PACKET")
            try:
                obj = json.loads(packet.decode("ascii"),object_pairs_hook=_unique_pairs)
            except (ValueError,UnicodeError,TypeError) as exc:
                raise PeerRefused("C3E_TIMEW_PEER_HOLD // NONCANONICAL_PACKET") from exc
            if type(obj) is not dict or set(obj) != FIELDS:
                _deny("UNEXPECTED_PACKET_FIELDS")
            candidate = make_packet_ci_only(
                challenge=independently_issued_challenge,
                pair_payload_sha256=obj["pairSha256"])
            if packet != candidate:
                _deny("CHANGED_OR_NONCANONICAL_PACKET")
            if not custody.valid():
                _deny("PEER_LEASE_EXPIRED")
            try:
                result = Window.inspect_live_pairing_ci_only(**pairing_inputs)
            except (Window.Refused,TypeError) as exc:
                raise PeerRefused("C3E_TIMEW_PEER_HOLD // SYNTHETIC_PAIR_REFUSED") from exc
            if result["pairPayloadSha256"] != obj["pairSha256"]:
                _deny("PACKET_BOUND_TO_DIFFERENT_SIGNED_PAIR")
            if not custody.valid():
                _deny("PEER_LEASE_EXPIRED")
            return {
                "schema": SCHEMA,
                "status": STATUS,
                "actualKernelPeerCredentialsAndPidfdObservedInCI": True,
                "actualPacketSenderMatchesSocketPeerInCI": True,
                "testOnlyPairHashMatchesChallengePacket": True,
                "sourceOnlyPid": pid,
                "sourceOnlyUid": uid,
                "sourceOnlyStartTicks": custody.identity.start_ticks,
                "pairPayloadSha256": result["pairPayloadSha256"],
                **Window.DENIED,
                **DENIED,
            }
    except (OSError,AttributeError,struct.error,Lease.LifecycleRefusal,TimeoutError) as exc:
        raise PeerRefused("C3E_TIMEW_PEER_HOLD // KERNEL_CUSTODY_UNAVAILABLE") from exc


def run_native_browser_window_issuer(*_args,**_kwargs):
    _deny("NATIVE_WAYLAND_BRAVE_PAIRING_NOT_IMPLEMENTED")
