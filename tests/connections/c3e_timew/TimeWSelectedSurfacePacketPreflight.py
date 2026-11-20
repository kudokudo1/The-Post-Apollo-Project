#!/usr/bin/env python3
"""Connections C3e / TimeW Scope A: genuine kernel packet custody, no trust issuer.

CI-only. A packet sent by one Linux peer and a matching caller-provided
selected-surface claim are NOT proof of a Sway compositor-origin selection.
No installed policy, root signature, C5 consent, Sway commands or authority.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import socket
import struct
import sys

TIME = Path(__file__).resolve().parents[3] / "services/time"
if str(TIME) not in sys.path:
    sys.path.insert(0, str(TIME))

import MachineBraveProcessLease as Lease
import MachineV2SelectedSurfaceReview as ScopeA

SCHEMA = "postapollo.connections.c3e.timew-selected-surface-packet.ci-v1"
KIND = "fake-selected-surface-kernel-packet-observation"
VERSION = 1
MAX_PACKET = 4096
CREDENTIALS = struct.Struct("=3i")
FIELDS = frozenset((
    "schema", "kind", "version", "scopeASchema", "scopeAAudience",
    "challengeSha256", "selectionSha256", "selectionId",
    "compositorEpoch", "surfaceLifetimeId", "surfaceGeneration",
    "liveConId", "seatId", "sessionId", "issuedMs", "expiresMs",
))
DENIED = {
    "trustedSwayPXCompositorVerified": False,
    "installedCompositorReleaseEnrolled": False,
    "perSurfaceSelectionOriginAuthenticated": False,
    "compositorLifetimeAuthenticated": False,
    "activeSeatAndSessionAuthenticated": False,
    "selectionChallengeIndependentlyIssued": False,
    "selectionChallengeSpentOnce": False,
    "braveWindowIdentityVerified": False,
    "c5TimeWOperatorConsentVerified": False,
    "protectedGeometryGrantVerified": False,
    "canSignSelectedSurface": False,
    "canMoveWindow": False,
    "canRestoreBrave": False,
    "productionAuthority": False,
}


class ObservationHold(ValueError):
    pass


def _hold(reason):
    raise ObservationHold("C3E_TIMEW_SCOPE_A_KERNEL_HOLD // " + reason)


def _canonical(value):
    try:
        return json.dumps(
            value, sort_keys=True, ensure_ascii=True,
            separators=(",", ":"), allow_nan=False
        ).encode("ascii")
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise ObservationHold(
            "C3E_TIMEW_SCOPE_A_KERNEL_HOLD // NONCANONICAL_DATA"
        ) from exc


def _unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            _hold("DUPLICATE_PACKET_FIELD")
        out[key] = value
    return out


def _bad_constant(_value):
    _hold("NONFINITE_PACKET_NUMBER")


def _selection(selection, challenge, now_ms):
    """Validate structural TimeW Scope A fixture, not its origin or selection."""
    if type(selection) is not dict or set(selection) != ScopeA.REQUIRED:
        _hold("TIMEW_SCOPE_A_FIELDS_REQUIRED")
    if (selection["schema"] != ScopeA.SCHEMA
            or selection["audience"] != ScopeA.AUDIENCE
            or "browser_window_ref" in selection):
        _hold("WRONG_SCOPE_A_AUDIENCE")
    if type(challenge) is not bytes or len(challenge) != 32:
        _hold("CHALLENGE_FIXTURE_NOT_32_BYTES")
    digest = hashlib.sha256(challenge).hexdigest()
    if selection["challenge_sha256"] != digest:
        _hold("TIMEW_CHALLENGE_DIGEST_CHANGED")
    try:
        for key in ("selection_id", "compositor_epoch",
                    "surface_lifetime_id", "session_id", "checkpoint_id"):
            ScopeA._id(selection[key])
        ScopeA._id(selection["window_key"], version=None)
        for key in ("seat_id", "app_id", "output", "workspace"):
            ScopeA._text(selection[key])
        ScopeA._int(selection["surface_generation"])
        ScopeA._int(selection["live_con_id"])
        ScopeA._rect(selection["before_rect"])
        ScopeA._rect(selection["target_rect"])
        now = ScopeA._int(now_ms, positive=False)
        issued = ScopeA._int(selection["issued_ms"], positive=False)
        expires = ScopeA._int(selection["expires_ms"], positive=False)
    except (ScopeA.ScopeARefused, KeyError, TypeError) as exc:
        raise ObservationHold(
            "C3E_TIMEW_SCOPE_A_KERNEL_HOLD // INVALID_TIMEW_CLAIM"
        ) from exc
    if (selection["floating"] is not True
            or type(selection["fullscreen_mode"]) is not int
            or selection["fullscreen_mode"] != 0):
        _hold("SELECTED_SURFACE_NOT_FLOATING")
    if (not issued <= now < expires or not 0 < expires-issued
            <= ScopeA.MAX_FIXTURE_LEASE_MS):
        _hold("STALE_OR_UNBOUNDED_SELECTION_FIXTURE")
    return digest


def make_packet_ci_only(*, selection: dict, challenge: bytes, now_ms: int):
    """Build synthetic source bytes without signing or sending."""
    sha = _selection(selection, challenge, now_ms)
    packet = {
        "schema": SCHEMA, "kind": KIND, "version": VERSION,
        "scopeASchema": ScopeA.SCHEMA,
        "scopeAAudience": ScopeA.AUDIENCE,
        "challengeSha256": sha,
        "selectionSha256": hashlib.sha256(_canonical(selection)).hexdigest(),
        "selectionId": selection["selection_id"],
        "compositorEpoch": selection["compositor_epoch"],
        "surfaceLifetimeId": selection["surface_lifetime_id"],
        "surfaceGeneration": selection["surface_generation"],
        "liveConId": selection["live_con_id"],
        "seatId": selection["seat_id"],
        "sessionId": selection["session_id"],
        "issuedMs": selection["issued_ms"],
        "expiresMs": selection["expires_ms"],
    }
    raw = _canonical(packet)
    if not 0 < len(raw) <= MAX_PACKET:
        _hold("PACKET_BOUNDS")
    return raw


def inspect_kernel_sender_and_selection_ci_only(
        *, receiver: socket.socket, expected_uid: int,
        expected_selection: dict, expected_challenge: bytes, now_ms: int):
    """Inspect real kernel sender of ONE test-owned seqpacket; no service.

    All expected inputs come from a caller, not an independently enrolled
    root or the protected SwayPX compositor. No source can promote this
    observation into a signing decision or TimeW restore permission.
    """
    expected_raw = make_packet_ci_only(
        selection=expected_selection, challenge=expected_challenge,
        now_ms=now_ms)
    if (type(receiver) is not socket.socket
            or receiver.family != socket.AF_UNIX
            or (receiver.type & 15) != socket.SOCK_SEQPACKET
            or type(expected_uid) is not int or expected_uid < 0):
        _hold("CI_RECEIVER_OR_UID_INVALID")
    if (receiver.gettimeout() is None or not 0 < receiver.gettimeout() <= 1.5):
        _hold("BOUNDED_SOCKET_TIMEOUT_REQUIRED")
    try:
        if receiver.getsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED) != 1:
            _hold("PACKET_CREDENTIALS_NOT_ENABLED")
        raw_origin = receiver.getsockopt(
            socket.SOL_SOCKET, socket.SO_PEERCRED, CREDENTIALS.size)
        if len(raw_origin) != CREDENTIALS.size:
            _hold("ORIGINAL_PEER_CREDS_MISSING")
        pid, uid, gid = CREDENTIALS.unpack(raw_origin)
        if pid <= 1 or uid != expected_uid or gid < 0:
            _hold("ORIGINAL_PEER_DIFFERS_FROM_TEST_POLICY")
        peer = type("KernelPeer", (), {"pid": pid, "uid": uid, "gid": gid})()
        with Lease.capture_socket_peer(receiver, peer=peer) as custody:
            if not custody.valid():
                _hold("KERNEL_ORIGINAL_PEER_LIFETIME_CHANGED")
            packet, controls, flags, addr = receiver.recvmsg(
                MAX_PACKET+1, socket.CMSG_SPACE(CREDENTIALS.size))
            if (flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC)
                    or len(packet) == 0 or len(packet) > MAX_PACKET
                    or addr):
                _hold("PACKET_TRUNCATED_OVERSIZED_OR_BAD_ADDRESS")
            senders = []
            for level, kind, data in controls:
                if level == socket.SOL_SOCKET and kind == socket.SCM_CREDENTIALS:
                    if len(data) != CREDENTIALS.size:
                        _hold("SCM_CREDENTIALS_MALFORMED")
                    senders.append(CREDENTIALS.unpack(data))
            if len(senders) != 1 or senders[0] != (pid, uid, gid):
                _hold("INHERITED_SOCKET_SENDER_OR_MISSING_CREDS")
            if not custody.valid():
                _hold("KERNEL_ORIGINAL_PEER_LIFETIME_CHANGED")
            try:
                claim = json.loads(packet.decode("ascii", "strict"),
                                   object_pairs_hook=_unique,
                                   parse_constant=_bad_constant)
            except (ValueError, UnicodeError, RecursionError) as exc:
                raise ObservationHold(
                    "C3E_TIMEW_SCOPE_A_KERNEL_HOLD // INVALID_PACKET_JSON"
                ) from exc
            if type(claim) is not dict or set(claim) != FIELDS:
                _hold("UNRECOGNIZED_PACKET_FIELDS")
            if packet != _canonical(claim):
                _hold("NONCANONICAL_PACKET_JSON")
            if packet != expected_raw:
                _hold("PACKET_DIFFERS_FROM_EXPECTED_SCOPE_A")
            if not custody.valid():
                _hold("KERNEL_ORIGINAL_PEER_LIFETIME_CHANGED")
            return {
                "schema": SCHEMA,
                "status": "ACTUAL_KERNEL_PACKET_SENDER_OBSERVED_NOT_SWAY_ORIGIN",
                "actualLinuxPacketSenderMatchesOriginalPeerInCI": True,
                "sourceOnlyPeerPid": pid,
                "sourceOnlyPeerUid": uid,
                "sourceOnlyPeerStartTicks": custody.identity.start_ticks,
                "fixtureTimeWScopeASelectionDigestMatches": True,
                "fixturePacketSha256": hashlib.sha256(packet).hexdigest(),
                **DENIED,
            }
    except (OSError, AttributeError, struct.error, TimeoutError,
            Lease.LifecycleRefusal) as exc:
        raise ObservationHold(
            "C3E_TIMEW_SCOPE_A_KERNEL_HOLD // KERNEL_CUSTODY_UNAVAILABLE"
        ) from exc


def run_native_selected_surface_issuer(*_args, **_kwargs):
    _hold("REAL_SWAYPX_SELECTED_SURFACE_ISSUER_NOT_INSTALLED")
