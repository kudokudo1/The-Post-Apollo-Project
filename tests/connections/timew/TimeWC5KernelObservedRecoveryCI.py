"""DOC 5 / TimeW C5 paired actual Linux packet OBSERVATION, NEVER admission.

Disposable hosted-root CI only. Reuses the merged TimeW SOCK_SEQPACKET,
SCM_CREDENTIALS + SO_PEERPIDFD kernel packet observer without changing it.
The two packets are compared to CALLER-SUPPLIED fixture data using a PRIVATE
CI JSON representation; neither those bytes nor their SHA authenticate a
protected custodian, real selected XDG source, human, or receipt.

This is not a production wire, service, listener, credential store, signature
verifier, network endpoint, grant, C5 spend, or native command. No socket is
opened or message sent here; all socket pairs and senders belong to tests.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys

from TimeWC5DualRecoveryReturnReference import (
    Comparison, compare_untrusted_recovery_returns,
)

ROOT = Path(__file__).resolve().parents[3]
_SOURCE = ROOT / "services/connections/ConnectionsTimeWNativePacketObservation.py"
_spec = importlib.util.spec_from_file_location("doc5_original_timew_kernel_observer", _SOURCE)
if _spec is None or _spec.loader is None:
    raise RuntimeError("ORIGINAL_KERNEL_OBSERVER_REQUIRED")
K = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(K)

C5_ROLE = "LOCAL_CI_C5_HISTORY_RETURN_UNTRUSTED"
NATIVE_ROLE = "LOCAL_CI_NATIVE_OUTCOME_RETURN_UNTRUSTED"
MAX_EXPECTED = K.MAX_PAYLOAD
AUTHORITY_FIELDS = (
    "production_authorized", "external_custody_verified",
    "current_head_verified", "protected_spent_verified",
    "operator_intent_verified", "native_source_verified",
    "configure_ack_verified", "selected_frame_settled",
    "terminal_receipt_verified", "native_action_allowed",
    "second_spend_allowed", "move_allowed", "retry_allowed", "undo_allowed",
)
OBS_KEYS = frozenset((
    "kind", "status", "packetSha256Untrusted", "packetLength",
    "kernelPeerPidObserved", "kernelPeerUidObserved",
    "kernelPeerGidObserved", "exactPeerPidfdAliveAtRead",
    "rawPacketUntrusted", "safeActions", *K.NO_AUTHORITY,
))


@dataclass(frozen=True, slots=True)
class KernelRecoveryObservation:
    status: str
    comparison_diagnostic: str | None = None
    c5_sender_pid_observed: int | None = None
    native_sender_pid_observed: int | None = None
    different_local_pid_observed: bool = False
    source_authenticated: bool = False
    enrolled_custodian_verified: bool = False
    independent_current_history_verified: bool = False
    original_human_consent_verified: bool = False
    protected_spent_verified: bool = False
    native_selected_xdg_verified: bool = False
    native_terminal_receipt_verified: bool = False
    production_authorized: bool = False
    native_action_allowed: bool = False
    retry_allowed: bool = False
    undo_allowed: bool = False
    safe_actions: tuple = ()


def _hold(code):
    return KernelRecoveryObservation(code)


def _ci_guard():
    # This is operational isolation, NOT a cryptographic attestation.
    return (sys.platform == "linux" and os.geteuid() == 0
            and os.environ.get("GITHUB_ACTIONS") == "true"
            and os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted")


def _snapshot_response(response):
    """Own a bounded flat copy; no mutable child or custom JSON objects."""
    if type(response) is not dict or len(response) > 64:
        raise ValueError("INVALID_C5_NATIVE_TEST_RESPONSE")
    copied = response.copy()
    if len(copied) > 64:
        raise ValueError("INVALID_C5_NATIVE_TEST_RESPONSE")
    for key, value in copied.items():
        if type(key) is not str or not 1 <= len(key) <= 128:
            raise ValueError("INVALID_C5_NATIVE_TEST_RESPONSE_KEY")
        if value is None or type(value) is bool:
            continue
        if type(value) is str and len(value) <= MAX_EXPECTED:
            continue
        if type(value) is int and value.bit_length() <= 64:
            continue
        if (type(value) is tuple and len(value) == 4
                and all(type(n) is int and n.bit_length() <= 64
                        for n in value)):
            continue
        raise ValueError("INVALID_C5_NATIVE_TEST_RESPONSE_VALUE")
    return copied


def _receiver_identity(receiver):
    # Different Python socket objects (or dup() FDs) can name the same
    # kernel socket. Compare live Linux socket inode identities, not objects.
    info = os.fstat(receiver.fileno())
    return info.st_dev, info.st_ino


def fixture_packet_ci_only(role, response):
    """Private deterministic CI bytes only: not a standardized C5/SwayPX wire."""
    if type(role) is not str or role not in (C5_ROLE, NATIVE_ROLE):
        raise ValueError("INVALID_C5_NATIVE_TEST_ROLE")
    response = _snapshot_response(response)
    try:
        packet = json.dumps(
            {"role": role, "diagnosticReturn": response},
            sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("INVALID_C5_NATIVE_TEST_JSON") from exc
    if not 0 < len(packet) <= MAX_EXPECTED:
        raise ValueError("C5_NATIVE_TEST_PACKET_BOUNDS")
    return packet


def _kernel_packet(receiver, expected):
    # The existing observer enforces exact SOCK_SEQPACKET, SO_PASSCRED,
    # pidfd original process still alive, per-message SCM_CREDENTIALS and
    # unexpected SCM_RIGHTS disposal. It never returns the raw packet.
    observed = K.inspect_one_untrusted_packet(receiver)
    if (type(observed) is not dict or set(observed) != OBS_KEYS
            or observed["kind"] != K.OBSERVATION_KIND
            or observed["status"] !=
            "KERNEL_PACKET_PEER_OBSERVED_BUT_SWAYPX_UNENROLLED"
            or observed["exactPeerPidfdAliveAtRead"] is not True
            or observed["rawPacketUntrusted"] is not True
            or observed["safeActions"] != []
            or any(observed[k] is not False for k in K.NO_AUTHORITY)
            or type(observed["packetLength"]) is not int
            or observed["packetLength"] != len(expected)
            or type(observed["packetSha256Untrusted"]) is not str
            or observed["packetSha256Untrusted"] !=
            hashlib.sha256(expected).hexdigest()
            or any(type(observed[k]) is not int or observed[k] < 0
                   for k in ("kernelPeerPidObserved",
                             "kernelPeerUidObserved",
                             "kernelPeerGidObserved"))):
        raise ValueError("UNTRUSTED_PACKET_OR_KERNEL_REPORT_MISMATCH")
    return observed["kernelPeerPidObserved"]


def inspect_dual_packet_returns_ci_only(*, c5_receiver, native_receiver,
                                       expected_c5_return,
                                       expected_native_return,
                                       original_recovery_plan,
                                       last_seen=None):
    """Read exactly two real kernel packets, match local fixture, HOLD.

    Hash comparison uses caller-supplied expected fixture contents; it is not
    signer enrollment or actual authenticated data origin. Even two different
    Linux PIDs are not independent protected hosts or custodian identities.
    """
    if not _ci_guard():
        return _hold("HOSTED_ROOT_ONLY_NO_PRODUCTION_ACCESS_HOLD")
    if (type(c5_receiver) is not socket.socket
            or type(native_receiver) is not socket.socket
            or c5_receiver is native_receiver
            or c5_receiver.fileno() < 0 or native_receiver.fileno() < 0):
        return _hold("TWO_DISTINCT_CONNECTED_RECEIVERS_REQUIRED_HOLD")
    try:
        if _receiver_identity(c5_receiver) == _receiver_identity(native_receiver):
            return _hold("TWO_DISTINCT_CONNECTED_RECEIVERS_REQUIRED_HOLD")
    except OSError:
        return _hold("TWO_DISTINCT_CONNECTED_RECEIVERS_REQUIRED_HOLD")
    try:
        # These private flat snapshots are the SAME values used for both
        # packet digest matching and the subsequent comparison. In particular,
        # a caller mutating its original dict during recvmsg cannot substitute
        # data after its bytes have been matched.
        c5_snapshot = _snapshot_response(expected_c5_return)
        native_snapshot = _snapshot_response(expected_native_return)
        c5_expected = fixture_packet_ci_only(C5_ROLE, c5_snapshot)
        native_expected = fixture_packet_ci_only(NATIVE_ROLE, native_snapshot)
    except ValueError:
        return _hold("MALFORMED_EXPECTED_LOCAL_FIXTURE_HOLD")
    try:
        c5_pid = _kernel_packet(c5_receiver, c5_expected)
    except (K.ObservationHold, ValueError, OSError):
        return _hold("C5_KERNEL_PACKET_UNKNOWN_HOLD")
    try:
        native_pid = _kernel_packet(native_receiver, native_expected)
    except (K.ObservationHold, ValueError, OSError):
        return _hold("NATIVE_KERNEL_PACKET_UNKNOWN_HOLD")
    try:
        comparison = compare_untrusted_recovery_returns(
            plan=original_recovery_plan,
            c5_return=c5_snapshot,
            native_return=native_snapshot,
            last_seen=last_seen,
        )
    except (TypeError, ValueError):
        return _hold("COMPARATOR_REFUSED_UNKNOWN_HOLD")
    if (type(comparison) is not Comparison
            or type(comparison.diagnostic) is not str
            or comparison.safe_actions != ()
            or any(getattr(comparison, k) is not False
                   for k in AUTHORITY_FIELDS)):
        return _hold("COMPARATOR_AUTHORITY_PROMOTION_REFUSED_HOLD")

    return KernelRecoveryObservation(
        status="KERNEL_OBSERVED_UNENROLLED_TWO_RETURNS_UNKNOWN_HOLD",
        comparison_diagnostic=comparison.diagnostic,
        c5_sender_pid_observed=c5_pid,
        native_sender_pid_observed=native_pid,
        different_local_pid_observed=c5_pid != native_pid,
    )
