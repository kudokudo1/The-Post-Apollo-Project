"""TimeW Scope A: structural *continuity* rehearsal across two geometry steps.

A selected SwayPX surface must retain its lifecycle, session and geometry
through before-resize, after-resize, after-move observations. All observations
and clocks are INJECTED UNTRUSTED TEST FIXTURES. This module does not connect
to any compositor, accept signed production evidence, issue grants, or execute
commands. Success is CONSISTENCY ONLY, never admission.
"""
from __future__ import annotations

from MachineV2SelectedSurfaceReview import (
    AUDIENCE, HASH, MAX_FIXTURE_LEASE_MS, MAX_SURFACES, OBS_FIELDS, REQUIRED,
    SCHEMA, _id, _int, _rect, _state, _text, refuse,
)

KIND = "timew-v2-selected-surface-intercommand-continuity-deny-only-v1"
PHASES = ("before_resize", "after_resize", "after_move")
SAMPLE_FIELDS = frozenset(("phase", "now_ms", "observed_surfaces"))
IMMUTABLE = (
    "live_con_id", "compositor_epoch", "surface_lifetime_id",
    "surface_generation", "app_id", "output", "workspace",
    "floating", "fullscreen_mode",
)
# A TimeW geometry pilot deliberately permits no unrelated desktop
# topology/rectangle changes between the two non-atomic commands.
# A real protected owner may later approve a different policy.
NO_AUTHORITY = {
    "kind": KIND,
    "status": "fixture_continuity_only",
    "read_only": True,
    "restore_allowed": False,
    "production_authorized": False,
    "source_origin_verified": False,
    "compositor_surface_lifetime_verified": False,
    "active_seat_verified": False,
    "c5_operator_consent_verified": False,
    "one_use_grant_spent": False,
    "brave_window_identity_verified": False,
    "persistent_brave_identity_verified": False,
    "browser_tabs_restorable": False,
    "no_automatic_retry": True,
    "requires_native_recheck_before_each_command": True,
    "safe_actions": [],
}


def _inventory(value, *, target):
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_SURFACES:
        refuse()
    con_ids, generations, records = set(), set(), {}
    for record in value:
        if not isinstance(record, dict) or set(record) != OBS_FIELDS:
            refuse()
        clean = _state(record)
        lifetime = (clean["compositor_epoch"], clean["surface_lifetime_id"],
                    clean["surface_generation"])
        if clean["live_con_id"] in con_ids or lifetime in generations:
            refuse()
        # All records in this fixture are claimed to originate from one
        # compositor epoch; cannot combine two separate desktop snapshots.
        if clean["compositor_epoch"] != target["compositor_epoch"]:
            refuse()
        con_ids.add(clean["live_con_id"])
        generations.add(lifetime)
        records[clean["live_con_id"]] = clean
    return records


def inspect_fixture(*, selection, samples, expected_session_id,
                    expected_seat_id, expected_challenge_sha256):
    """Pure three-stage structural check. Every result remains deny-only.

    A later *protected compositor service*, not TimeW, must originate and
    validate fresh per-command observations, revocations and kernel/seat
    facts. C5 protected consent/spend is a separate prerequisite.
    """
    if not isinstance(selection, dict) or set(selection) != REQUIRED:
        refuse()
    if selection["schema"] != SCHEMA or selection["audience"] != AUDIENCE:
        refuse()
    for name in ("selection_id", "compositor_epoch", "surface_lifetime_id",
                 "checkpoint_id", "session_id"):
        _id(selection[name])
    _id(selection["window_key"], version=None)
    for name in ("app_id", "output", "workspace", "seat_id"):
        _text(selection[name])
    for name in ("surface_generation", "live_con_id"):
        _int(selection[name])
    if (selection["floating"] is not True
            or type(selection["fullscreen_mode"]) is not int
            or selection["fullscreen_mode"] != 0):
        refuse()
    if (not isinstance(expected_challenge_sha256, str)
            or not HASH.fullmatch(expected_challenge_sha256)
            or selection["challenge_sha256"] != expected_challenge_sha256
            or selection["session_id"] != _id(expected_session_id)
            or selection["seat_id"] != _text(expected_seat_id)):
        refuse()
    first, last = (_int(selection["issued_ms"], positive=False),
                   _int(selection["expires_ms"], positive=False))
    if last <= first or last-first > MAX_FIXTURE_LEASE_MS:
        refuse()
    before, target = _rect(selection["before_rect"]), _rect(selection["target_rect"])
    resized = dict(before, width=target["width"], height=target["height"])
    expected_rects = (before, resized, target)

    if not isinstance(samples, list) or len(samples) != len(PHASES):
        refuse()
    first_other = None
    prev_time = None
    for phase, expected in zip(samples, PHASES):
        if not isinstance(phase, dict) or set(phase) != SAMPLE_FIELDS or phase["phase"] != expected:
            refuse()
        instant = _int(phase["now_ms"], positive=False)
        if (not first <= instant < last
                or (prev_time is not None and instant < prev_time)):
            refuse()
        prev_time = instant
        entries = _inventory(phase["observed_surfaces"], target=selection)
        selected = entries.get(selection["live_con_id"])
        if selected is None or selected["floating"] is not True or selected["fullscreen_mode"] != 0:
            refuse()
        for name in IMMUTABLE:
            if selected[name] != selection[name]:
                refuse()
        expected_rect = expected_rects[PHASES.index(expected)]
        if selected["rect"] != expected_rect:
            refuse()
        # Other windows can be tiled/fullscreen, but they must not disappear,
        # reorder identity, change state or move in the middle of this
        # strictly bounded *fixture*. Any change is UNKNOWN, not success.
        other = {con: item for con, item in entries.items()
                 if con != selection["live_con_id"]}
        if first_other is None:
            first_other = other
        elif other != first_other:
            refuse()

    # Do not leak a shared mutable action list even to untrusted callers.
    return dict(NO_AUTHORITY, safe_actions=[])
