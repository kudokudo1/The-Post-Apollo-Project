#!/usr/bin/env python3
"""C3e TimeW: observe kernel identity of an original Sway IPC socket peer.

Never confuses SO_PEERCRED / SO_PEERPIDFD with proof of which task authored
a STREAM reply, an installed compositor, or a Brave Wayland surface. CI only.
A native entrypoint is deliberately unimplemented and unconditionally denies.
"""
from __future__ import annotations

from pathlib import Path
import socket
import struct
import sys

TIME = Path(__file__).resolve().parents[3] / "services/time"
if str(TIME) not in sys.path:
    sys.path.insert(0, str(TIME))

import MachineBraveProcessLease as Lease
import TimeWSwayIpcTreeReadPreflight as Tree

CREDENTIALS = struct.Struct("=3i")
DENIED = {
    "independentlyEnrolledSwayIpcPeer": False,
    "protectedSwaySocketPathAuthenticated": False,
    "installedSwayPxSignedReleaseVerified": False,
    "activeUnlockedSeatAndCompositorSessionVerified": False,
    "actualSwayIpcReplySenderProven": False,
    "braveWindowToWaylandSurfaceBound": False,
    "braveWindowReferenceAuthenticated": False,
    "timewPairingIssuerAvailable": False,
    "c5OperatorConsentVerified": False,
    "canMoveWindow": False,
    "canRestoreBrave": False,
    "productionAuthority": False,
}


class PeerRefused(ValueError):
    pass


def _hold(message):
    raise PeerRefused("C3E_TIMEW_SWAY_PEER_HOLD // " + message)


def inspect_original_sway_socket_peer_ci_only(
    *, connection: socket.socket, expected_uid: int,
    expected_start_ticks: int,
):
    """Read actual kernel socket-origin evidence on a test-owned stream.

    The expected UID and process birth time are CALLER-PROVIDED CI fixtures.
    They have no installed root/protected enrollment. No direct Sway socket
    path or process is opened. A fork may inherit a connected STREAM socket;
    Linux SO_PEERCRED alone cannot prove the eventual reply author.
    """
    if (type(connection) is not socket.socket or type(expected_uid) is not int
            or expected_uid < 0 or type(expected_start_ticks) is not int
            or expected_start_ticks <= 0):
        _hold("UNTRUSTED_TEST_POLICY")
    if (connection.family != socket.AF_UNIX
            or connection.type & 15 != socket.SOCK_STREAM):
        _hold("UNEXPECTED_SOCKET_TYPE")
    try:
        raw = connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED,
                                    CREDENTIALS.size)
        if len(raw) != CREDENTIALS.size:
            _hold("INCOMPLETE_KERNEL_CREDENTIALS")
        pid, uid, gid = CREDENTIALS.unpack(raw)
        if pid <= 1 or uid != expected_uid or gid < 0:
            _hold("KERNEL_PEER_DIFFERS_FROM_TEST_EXPECTATION")
        peer = type("ObservedPeer", (), {"pid":pid, "uid":uid, "gid":gid})()
        with Lease.capture_socket_peer(connection, peer=peer) as lease:
            if (not lease.valid()
                    or lease.identity.start_ticks != expected_start_ticks):
                _hold("ORIGINAL_PROCESS_IDENTITY_CHANGED")
            # GET_TREE is read-only. Its server origin is NOT authenticated
            # by these caller-supplied checks, and SOCK_STREAM may be shared.
            observation = Tree.inspect_fake_sway_ipc_ci_only(
                connection=connection)
            if not lease.valid():
                _hold("ORIGINAL_PROCESS_LIFETIME_ENDED")
            return {
                "schema": "postapollo.connections.c3e-timew-sway-peer-observation.ci-v1",
                "status": "ORIGINAL_KERNEL_SOCKET_PEER_OBSERVED_NOT_COMPOSITOR_TRUST",
                "actualOriginalUnixStreamPeerPidfdSeenInCi": True,
                "actualKernelPeerUidMatchesTestFixture": True,
                "testOnlySwayTreeWireObserved": observation["ciFakeCompositorTreeParsed"],
                "testOnlyBraveLeafCount": observation["braveLeafCountInCi"],
                "testOnlyAmbiguousSamePidBrave": observation["braveLeavesSharePidInCi"],
                "sourceOnlyOriginalPeerPid": pid,
                "sourceOnlyOriginalPeerStartTicks": lease.identity.start_ticks,
                **Tree.DENIED,
                **DENIED,
            }
    except (OSError, AttributeError, struct.error, Lease.LifecycleRefusal,
            Tree.Refused, TimeoutError) as exc:
        raise PeerRefused(
            "C3E_TIMEW_SWAY_PEER_HOLD // KERNEL_OR_READONLY_TREE_UNAVAILABLE"
        ) from exc


def run_native_sway_ipc_attested_window_issuer(*_args, **_kwargs):
    _hold("REAL_COMPOSITOR_OR_BRAVE_WINDOW_TRUST_NOT_IMPLEMENTED")
