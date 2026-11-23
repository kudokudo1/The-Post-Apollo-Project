"""TimeW Scope A: read-only review of UNTRUSTED fractional observation values.

This consumes only Python in-process ExactLogicalRect values from the isolated
TimeW value model. There is no cross-process wire, checkpoint persistence,
signed SwayPX receipt, operator selection, C3e/C4b provenance, C5 spend,
native command, or production call site here.

Provisional READY/TIMEOUT labels are supplied by a caller and have no trust.
Even bit-exact matching values always HOLD. The current compositor can copy
CURRENT after a transaction timeout, and scene arrangement is not settlement.
"""

from __future__ import annotations

from MachineV2ExactLogicalGeometry import (
    ExactGeometryRefused, ExactLogicalRect, PHASE_PENDING, PHASE_CURRENT,
    read_value,
)

REVIEW_REVISION = 1  # Local code revision, NOT a packet or database schema.
KIND = "timew-fractional-observation-untrusted-review-v1"
STAGES = frozenset(("READY_REPORTED", "TIMEOUT_FORCED", "UNKNOWN"))


class FractionalObservationRefused(ValueError):
    pass


def _refuse():
    raise FractionalObservationRefused("TIMEW FRACTIONAL OBSERVATION REFUSED")


def _bits(value, expected_phase):
    if type(value) is not ExactLogicalRect:
        _refuse()
    try:
        read_value(value)
    except ExactGeometryRefused:
        _refuse()
    if value.phase != expected_phase:
        _refuse()
    return (value.x_bits, value.y_bits, value.width_bits, value.height_bits)


def _stage(value):
    # These are caller-supplied diagnostic labels, not native receipts.
    if type(value) is not str or value not in STAGES:
        _refuse()
    return value


def review_untrusted_candidate(
    *, before_current, target_pending, post_resize_current, final_current,
    resize_stage, move_stage,
):
    """Compare provisional exact VALUES without granting an executable action.

    In particular, post_resize_current is a NEW observation, not an assumed
    preservation of before_current x/y after the resize. No source or settling
    proof exists, so even exact values and READY labels remain untrusted.
    Missing/unknown observations or timeout are UNKNOWN_HOLD.
    """
    before = _bits(before_current, PHASE_CURRENT)
    target = _bits(target_pending, PHASE_PENDING)
    after_resize = (
        None if post_resize_current is None
        else _bits(post_resize_current, PHASE_CURRENT)
    )
    final = (
        None if final_current is None
        else _bits(final_current, PHASE_CURRENT)
    )
    resize = _stage(resize_stage)
    move = _stage(move_stage)

    if (after_resize is None or final is None
            or resize != "READY_REPORTED" or move != "READY_REPORTED"):
        status = "UNKNOWN_HOLD"
    elif after_resize[2:] != target[2:] or final != target:
        status = "GEOMETRY_MISMATCH_HOLD"
    else:
        # Matching bits still cannot authenticate an actual window, receipt,
        # configure ACK, final frame, human consent or authorization.
        status = "MATCHED_VALUES_UNTRUSTED_HOLD"

    return {
        "kind": KIND,
        "review_revision": REVIEW_REVISION,
        "status": status,
        "read_only": True,
        "restore_allowed": False,
        "native_action_allowed": False,
        "selected_surface_authenticated": False,
        "compositor_source_authenticated": False,
        "configure_ack_verified": False,
        "final_frame_settled": False,
        "c5_consent_spent_verified": False,
        "no_automatic_retry": True,
        "no_automatic_undo": True,
        "safe_actions": [],
    }
