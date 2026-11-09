"""MACHINE // Pure, fail-closed review of a proposed Brave/Sway focus sequence.

This is a diagnostic research contract, NOT a pairing certificate. The
existing native-messaging probe does not call this module. An A/B/A focus
pattern can arise accidentally or be forged and cannot prove browser-to-OS
identity, exclusion of private windows, or a restart-stable session ID.

Inputs are hypothetical observations to be provided by a separately reviewed,
operator-triggered coordinator in a future milestone. No focus, capture, Sway
IPC, browser API, storage or restore operation occurs here.
"""
from __future__ import annotations

import uuid

from MachineBraveFocusWitness import BRAVE_APP_IDS

KIND = "machine-brave-focus-sequence-input-v1"
REVIEW_KIND = "machine-brave-focus-sequence-review-v1"
STEPS = ("A1", "B1", "A2")
MAX_ID = 2**31 - 1
MAX_TIME = 2**53 - 1
MAX_STEP_DELAY_MS = 2000
MAX_CYCLE_MS = 8000


class FocusSequenceError(ValueError):
    pass


def _exact(record, required):
    if not isinstance(record, dict) or set(record) != set(required):
        raise FocusSequenceError("INVALID EVIDENCE STRUCTURE")


def _positive_id(value):
    if type(value) is not int or not 0 < value <= MAX_ID:
        raise FocusSequenceError("INVALID TEMPORARY WINDOW REFERENCE")


def _timestamp(value):
    if type(value) is not int or not 0 <= value <= MAX_TIME:
        raise FocusSequenceError("INVALID OBSERVATION TIME")


def _uuid(value):
    if not isinstance(value, str):
        raise FocusSequenceError("INVALID CHALLENGE")
    try:
        parsed = str(uuid.UUID(value))
    except (ValueError, AttributeError) as exc:
        raise FocusSequenceError("INVALID CHALLENGE") from exc
    if value != parsed:
        raise FocusSequenceError("NONCANONICAL CHALLENGE")


def review_focus_sequence(evidence):
    """Return a privacy-preserving consistency result with ZERO action authority.

    A true pattern is a reason to investigate a bridge, *not* an OS/window
    identity certificate. The host's native container IDs stay in memory
    and are never included in the result.
    """
    _exact(evidence, (
        "kind", "challenge", "gesture", "browser_private_windows_excluded",
        "host_private_exclusion_verified", "transport_origin_authenticated",
        "samples",
    ))
    if (evidence["kind"] != KIND
            or evidence["gesture"] != "operator_initiated_diagnostic_only"
            or evidence["browser_private_windows_excluded"] is not True
            or evidence["host_private_exclusion_verified"] is not False
            or evidence["transport_origin_authenticated"] is not False):
        raise FocusSequenceError("UNSUPPORTED IDENTITY OR PERMISSION CLAIM")
    _uuid(evidence["challenge"])
    samples = evidence["samples"]
    if not isinstance(samples, list) or len(samples) != len(STEPS):
        raise FocusSequenceError("INVALID SEQUENCE LENGTH")

    browser_ids, host_ids = [], []
    previous_host_time = -1
    first_request_time = None
    for expected_step, sample in zip(STEPS, samples):
        _exact(sample, (
            "step", "temporary_browser_window_id", "focused_host_container_id",
            "host_app_id", "host_stable_two_reads",
            "requested_at_ms", "observed_at_ms",
        ))
        if sample["step"] != expected_step:
            raise FocusSequenceError("OUT OF ORDER OBSERVATION")
        browser_id = sample["temporary_browser_window_id"]
        host_id = sample["focused_host_container_id"]
        _positive_id(browser_id)
        _positive_id(host_id)
        if (not isinstance(sample["host_app_id"], str)
                or sample["host_app_id"] not in BRAVE_APP_IDS
                or sample["host_stable_two_reads"] is not True):
            raise FocusSequenceError("UNSTABLE OR NON-BRAVE OBSERVATION")
        requested = sample["requested_at_ms"]
        observed = sample["observed_at_ms"]
        _timestamp(requested)
        _timestamp(observed)
        if (requested <= previous_host_time
                or observed < requested
                or observed - requested > MAX_STEP_DELAY_MS):
            raise FocusSequenceError("STALE OR OVERLAPPING OBSERVATION")
        if first_request_time is None:
            first_request_time = requested
        if observed - first_request_time > MAX_CYCLE_MS:
            raise FocusSequenceError("EXPIRED FOCUS CYCLE")
        previous_host_time = observed
        browser_ids.append(browser_id)
        host_ids.append(host_id)

    pattern = (
        browser_ids[0] == browser_ids[2] != browser_ids[1]
        and host_ids[0] == host_ids[2] != host_ids[1]
    )
    return {
        "kind": REVIEW_KIND,
        "status": ("consistent_unverified_focus_pattern" if pattern
                   else "unbound_focus_pattern"),
        "sample_count": len(STEPS),
        "observation_only": True,
        "browser_to_sway_identity_verified": False,
        "extension_origin_authenticated": False,
        "host_private_window_exclusion_verified": False,
        "restart_session_identity_verified": False,
        "session_capture_allowed": False,
        "restore_allowed": False,
        "action_allowed": False,
        "safe_actions": [],
    }
