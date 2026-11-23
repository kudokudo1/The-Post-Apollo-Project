"""DOC 5 TimeW C5 EXACT-VALUE REVIEW SHADOW (CI fixture, NEVER CONSENT).

Reuse TimeW's merged in-memory binary64 value model without changing it.
This test-only comparison does not define a wire format, source signature,
native selection, trusted display, human click, issued grant or SPENT record.
Even a perfect lexical and value match is always a non-authorizing HOLD.
"""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path
import sys

from TimeWC5SpendFenceReference import (
    ACTION, AUDIENCE, FIELDS, MAX_MS, ReferenceRefused, _claim, _uuid4,
)

VALUE_PATH = (Path(__file__).resolve().parents[3] / "services" / "time"
              / "MachineV2ExactLogicalGeometry.py")
_spec = importlib.util.spec_from_file_location(
    "doc5_timew_value_only", VALUE_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError("MISSING_TIMEW_VALUE_REFERENCE")
_value = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _value
_spec.loader.exec_module(_value)

SHADOW_SCHEMA = "postapollo.connections.c5.timew.review-shadow-fixture.v1"
STEPS = ("resize", "observe-after-resize", "move", "verify-final")
SHADOW_EXTRA = frozenset((
    "schema", "checkpoint_id", "window_key", "boot_epoch",
    "surface_generation", "output_id", "workspace_id",
    "output_scale_hex", "output_transform", "before_value",
    "target_value", "operation_steps",
))
ORIGINAL_FIELDS = FIELDS | SHADOW_EXTRA
REVIEW_FIELDS = ORIGINAL_FIELDS | {"review_lines"}


def hold(reason):
    return {
        "diagnostic": reason,
        "production_authorized": False,
        "native_action_allowed": False,
        "human_consent_verified": False,
        "trusted_display_verified": False,
        "selected_surface_authenticated": False,
        "external_custody_verified": False,
        "spent_grant_verified": False,
        "native_terminal_receipt_verified": False,
        "retry_allowed": False,
        "undo_allowed": False,
        "safe_actions": [],
    }


def _label(value):
    return (type(value) is str and 1 <= len(value) <= 128
            and all(33 <= ord(c) <= 126 for c in value))


def _scale(value):
    if type(value) is not str or len(value) > 48:
        return False
    try:
        number = float.fromhex(value)
    except (TypeError, ValueError, OverflowError):
        return False
    return (math.isfinite(number) and 0.1 <= number <= 8.0
            and number.hex() == value)


def _validate_original(original):
    if not isinstance(original, dict) or set(original) != ORIGINAL_FIELDS:
        return False
    try:
        _claim({k: original[k] for k in FIELDS})
        for field in ("checkpoint_id", "window_key", "boot_epoch"):
            _uuid4(original[field])
        if (original["schema"] != SHADOW_SCHEMA
                or type(original["surface_generation"]) is not int
                or not 1 <= original["surface_generation"] <= MAX_MS
                or not _label(original["output_id"])
                or not _label(original["workspace_id"])
                or not _scale(original["output_scale_hex"])
                or type(original["output_transform"]) is not int
                or not 0 <= original["output_transform"] <= 7
                or type(original["operation_steps"]) is not tuple
                or original["operation_steps"] != STEPS):
            return False
        before = original["before_value"]
        target = original["target_value"]
        _value.read_value(before)
        _value.read_value(target)
        # Pure value phase distinction. Neither label proves authentic CURRENT
        # or that a target is a compositor-queued instruction or settled frame.
        return (before.phase == _value.PHASE_CURRENT
                and target.phase == _value.PHASE_PENDING)
    except (ReferenceRefused, _value.ExactGeometryRefused,
            TypeError, ValueError, KeyError, AttributeError):
        return False


def _geometry_line(label, rect):
    coords = _value.read_value(rect)
    # Two untrusted display representations: readable decimal *and* bit-exact
    # hexadecimal float. Python round-trip text is NOT a signed native wire.
    pairs = ("x", "y", "width", "height")
    fields = ", ".join(
        f"{name}={repr(number)} [{number.hex()}]"
        for name, number in zip(pairs, coords)
    )
    return f"{label}: version={rect.version}, phase={rect.phase}; {fields}"


def review_lines(original):
    """Deterministic test-only complete transcript; not a real trusted UI."""
    if not _validate_original(original):
        raise ValueError("INVALID_SHADOW_ORIGINAL")
    return (
        f"purpose: {original['audience']} / {original['action']}",
        f"grant/operation: {original['grant_id']} / {original['operation_id']}",
        f"selection/source/intent: {original['selection_sha256']} / "
        f"{original['source_sha256']} / {original['intent_sha256']}",
        f"session/seat/issuer: {original['session_id']} / "
        f"{original['seat_id']} / {original['issuer_epoch']}",
        f"checkpoint/window: {original['checkpoint_id']} / "
        f"{original['window_key']}",
        f"native lifetime: boot={original['boot_epoch']}, "
        f"surface_generation={original['surface_generation']}",
        f"workspace/output: {original['workspace_id']} / "
        f"{original['output_id']}; scale={original['output_scale_hex']}; "
        f"transform={original['output_transform']}",
        _geometry_line("observed-before value (untrusted CURRENT)", original["before_value"]),
        _geometry_line("saved-target value (untrusted PENDING)", original["target_value"]),
        f"one-grant operation: {' -> '.join(original['operation_steps'])}",
        f"issue/expiry ms: {original['issued_ms']} / {original['expires_ms']}",
    )


def assess_review_shadow(*, original, presented, now_ms, seat_unlocked,
                         surface_alive):
    """Compare fixture review to one original, never issue consent/permission."""
    if not _validate_original(original):
        return hold("INVALID_ORIGINAL_HOLD")
    if type(now_ms) is not int or not 0 <= now_ms <= MAX_MS:
        return hold("INVALID_CLOCK_HOLD")
    if not original["issued_ms"] <= now_ms < original["expires_ms"]:
        return hold("EXPIRED_OR_NOT_YET_VALID_HOLD")
    if seat_unlocked is not True or surface_alive is not True:
        return hold("NO_ACTIVE_SELECTED_SURFACE_OR_UNLOCKED_SEAT_HOLD")
    if not isinstance(presented, dict) or set(presented) != REVIEW_FIELDS:
        return hold("INCOMPLETE_OR_EXTRA_REVIEW_FIELDS_HOLD")
    exposed = {k: presented[k] for k in ORIGINAL_FIELDS}
    if not _validate_original(exposed):
        return hold("INVALID_PRESENTED_REVIEW_HOLD")
    if any(exposed[k] != original[k] for k in ORIGINAL_FIELDS):
        return hold("REVIEW_OR_INTENT_MISMATCH_HOLD")
    if type(presented["review_lines"]) is not tuple:
        return hold("DISPLAY_NOT_EXACT_HOLD")
    if presented["review_lines"] != review_lines(original):
        return hold("DISPLAY_NOT_EXACT_HOLD")
    # This is a SHADOW test. An arbitrary caller may control both sides, the
    # pretend seat flags and even the displayed text. Always deny native action.
    return hold("MATCHED_BUT_UNTRUSTED_SHADOW_HOLD")
