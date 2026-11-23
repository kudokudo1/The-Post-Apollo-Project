"""TimeW Scope A: synthetic SwayPX lineage comparison, permanently DENY-ONLY.

This is a test-only reference for negotiating a future receipt contract.
It is NOT a canonical packet, native adapter, signed source, receipt parser,
protected operation ledger, or an imported production TimeW service.

SwayPX #178's process-local boot/lifetime/transaction counters are diagnostic,
and its transaction sequence is not tied to actual transaction_commit.
All fields here are caller-controlled. A match is NEVER authority.
"""

from __future__ import annotations

import math
import struct

KIND = "timew-scope-a-untrusted-lineage-shadow"
SHADOW_REVISION = 1  # Test reference revision, NOT a wire version.
MAX_U64 = (1 << 64) - 1
FIELDS = frozenset((
    "boot_a", "boot_b", "lifetime_sequence", "transaction_sequence",
    "seat_epoch", "session_epoch", "output_epoch", "workspace_epoch",
    "output_scale_bits", "output_transform",
))
POSITIVE_FIELDS = (
    "lifetime_sequence", "transaction_sequence", "seat_epoch",
    "session_epoch", "output_epoch", "workspace_epoch",
)
UINT_FIELDS = FIELDS - {"output_transform"}


def _valid(snapshot):
    if type(snapshot) is not dict or set(snapshot) != FIELDS:
        return False
    if any(type(snapshot[key]) is not int or not 0 <= snapshot[key] <= MAX_U64
           for key in UINT_FIELDS):
        return False
    if snapshot["boot_a"] == 0 and snapshot["boot_b"] == 0:
        return False
    if any(snapshot[key] == 0 for key in POSITIVE_FIELDS):
        return False
    if (type(snapshot["output_transform"]) is not int
            or not 0 <= snapshot["output_transform"] <= 7):
        return False
    try:
        scale = struct.unpack("=d", struct.pack(
            "=Q", snapshot["output_scale_bits"]))[0]
    except (TypeError, ValueError, OverflowError, struct.error):
        return False
    return math.isfinite(scale) and scale > 0.0


def _hold(status):
    return {
        "kind": KIND,
        "shadow_revision": SHADOW_REVISION,
        "status": status,
        "read_only": True,
        "source_authenticated": False,
        "operator_selection_authenticated": False,
        "active_seat_authenticated": False,
        "transaction_commit_bound": False,
        "configure_ack_verified": False,
        "final_frame_settled": False,
        "native_receipt_verified": False,
        "protected_c5_spent_verified": False,
        "restore_allowed": False,
        "resize_allowed": False,
        "move_allowed": False,
        "retry_allowed": False,
        "undo_allowed": False,
        "safe_actions": [],
    }


def inspect_untrusted_lineage(
    *, original, observed, timeout_seen, revocation_seen, process_exit_seen,
    surface_alive_reported, seat_unlocked_reported, output_valid_reported,
):
    """Compare two *caller-created* diagnostic snapshots, NEVER issue action.

    Diagnostic boot and monotonic counters are in-process correlation only;
    their comparison does not prove genuine native source, physical selection,
    actual transaction generation, ACK, presentation, consent, or history.
    """
    if original is None or observed is None:
        return _hold("MISSING_LINEAGE_UNKNOWN_HOLD")
    if not _valid(original) or not _valid(observed):
        return _hold("INVALID_LINEAGE_UNKNOWN_HOLD")
    flags = (timeout_seen, revocation_seen, process_exit_seen,
             surface_alive_reported, seat_unlocked_reported,
             output_valid_reported)
    if any(type(flag) is not bool for flag in flags):
        return _hold("INVALID_OBSERVATION_FLAG_HOLD")
    if timeout_seen or revocation_seen or process_exit_seen:
        return _hold("AMBIGUOUS_OR_REVOKED_HOLD")
    if not (surface_alive_reported and seat_unlocked_reported
            and output_valid_reported):
        return _hold("OBSERVATION_CONTINUITY_LOST_HOLD")
    if original != observed:
        return _hold("LINEAGE_DRIFT_UNKNOWN_HOLD")
    return _hold("MATCHED_DIAGNOSTIC_UNTRUSTED_HOLD")
