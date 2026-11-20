"""TimeW Scope A: selected LIVE compositor surface geometry, DENY-ONLY review.

This is a pure structural fixture-review boundary for an explicitly selected,
already-existing floating surface in ONE CURRENT session. It is NOT a trusted
compositor/seat witness and never authorizes a Sway command. Neither an app_id,
a browser UUID, a title, a process ID nor a transient con_id independently
establishes the correct window. No Brave pairing or C5 consent is inferred.

Every observation is caller supplied. Even a fully consistent record returns
restore_allowed=False. Only a separately installed, independently enrolled
SwayPX/C3e source and protected C5 one-use consent could later provide trust.
"""
from __future__ import annotations

import re
import uuid

from MachineV2FloatingPilot import APPROVAL_KIND, RehearsalRefused, prepare
from MachineV2GeometryJournal import _rect as journal_rect

SCHEMA = "post-apollo.timew.selected-live-surface.review.v1"
AUDIENCE = "timew-selected-live-surface-geometry-only"
KIND = "timew-v2-selected-live-surface-deny-only-review-v1"
MAX_FIXTURE_LEASE_MS = 5000  # CI cap, NOT a production authorization duration
MAX_SURFACES = 512
MAX_MS = 9007199254740991
MAX_TEXT = 128
HASH = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
REQUIRED = frozenset((
    "schema", "audience", "challenge_sha256", "selection_id",
    "compositor_epoch", "surface_lifetime_id", "surface_generation",
    "live_con_id", "app_id", "output", "workspace", "floating",
    "fullscreen_mode", "before_rect", "target_rect", "checkpoint_id",
    "window_key", "seat_id", "session_id", "issued_ms", "expires_ms",
))
OBS_FIELDS = frozenset((
    "live_con_id", "compositor_epoch", "surface_lifetime_id",
    "surface_generation", "app_id", "output", "workspace", "rect",
    "floating", "fullscreen_mode",
))


class ScopeARefused(ValueError):
    pass


def refuse():
    raise ScopeARefused("TIMEW SCOPE A SELECTED SURFACE REVIEW REFUSED")


def _id(value, *, version=4):
    if not isinstance(value, str):
        refuse()
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        refuse()
    if str(parsed) != value or (version and parsed.version != version):
        refuse()
    return value


def _text(value):
    if (not isinstance(value, str) or not 1 <= len(value) <= MAX_TEXT
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        refuse()
    return value


def _int(value, *, positive=True):
    if type(value) is not int or value < (1 if positive else 0) or value > MAX_MS:
        refuse()
    return value


def _rect(value):
    try:
        return journal_rect(value)
    except (ValueError, TypeError, KeyError):
        refuse()


def _state(record):
    if not isinstance(record, dict) or set(record) != OBS_FIELDS:
        refuse()
    con_id = _int(record["live_con_id"])
    epoch = _id(record["compositor_epoch"])
    lifetime = _id(record["surface_lifetime_id"])
    generation = _int(record["surface_generation"])
    app = _text(record["app_id"])
    output = _text(record["output"])
    workspace = _text(record["workspace"])
    # The *selected* surface must be floating/non-fullscreen. Unrelated
    # current surfaces may be tiled or fullscreen without blocking selection.
    # Still validate all records strictly to catch ambiguous/lost lifetimes.
    if (type(record["floating"]) is not bool
            or type(record["fullscreen_mode"]) is not int
            or not 0 <= record["fullscreen_mode"] <= 2):
        refuse()
    return {
        "live_con_id": con_id, "compositor_epoch": epoch,
        "surface_lifetime_id": lifetime, "surface_generation": generation,
        "app_id": app, "output": output, "workspace": workspace,
        "rect": _rect(record["rect"]), "floating": record["floating"],
        "fullscreen_mode": record["fullscreen_mode"],
    }


def review_selected_fixture(*, request, selection, observed_surfaces, now_ms,
                            expected_session_id, expected_seat_id,
                            expected_challenge_sha256, read_runner,
                            legacy_reader, geometry_reader):
    """Inspect an explicit manual selection against twice-read saved/live V2.

    This prototype cannot authenticate the selection or surface lifetime.
    Thus it never returns signed permission, and it exposes no command
    runner, key source, installed service, operator-approved flag or CLI.
    """
    now = _int(now_ms, positive=False)
    session = _id(expected_session_id)
    seat = _text(expected_seat_id)
    if not isinstance(expected_challenge_sha256, str) or not HASH.fullmatch(expected_challenge_sha256):
        refuse()
    if not isinstance(selection, dict) or set(selection) != REQUIRED:
        refuse()
    if selection["schema"] != SCHEMA or selection["audience"] != AUDIENCE:
        refuse()
    _id(selection["selection_id"])
    _id(selection["compositor_epoch"])
    _id(selection["surface_lifetime_id"])
    _int(selection["surface_generation"])
    _int(selection["live_con_id"])
    _id(selection["session_id"])
    _id(selection["checkpoint_id"])
    _id(selection["window_key"], version=None)  # saved keys may be UUIDv4 or UUIDv5
    _text(selection["app_id"])
    _text(selection["output"])
    _text(selection["workspace"])
    _text(selection["seat_id"])
    if (selection["floating"] is not True
            or type(selection["fullscreen_mode"]) is not int
            or selection["fullscreen_mode"] != 0):
        refuse()
    if (not isinstance(selection["challenge_sha256"], str)
            or not HASH.fullmatch(selection["challenge_sha256"])
            or selection["challenge_sha256"] != expected_challenge_sha256):
        refuse()
    first, last = _int(selection["issued_ms"], positive=False), _int(selection["expires_ms"], positive=False)
    if last <= first or last - first > MAX_FIXTURE_LEASE_MS or not first <= now < last:
        refuse()
    if selection["seat_id"] != seat or selection["session_id"] != session:
        refuse()
    before = _rect(selection["before_rect"])
    after = _rect(selection["target_rect"])

    if (not isinstance(request, dict)
            or set(request) != {"checkpoint_id", "window_key", "live_con_id"}):
        refuse()
    if (request["checkpoint_id"] != selection["checkpoint_id"]
            or request["window_key"] != selection["window_key"]
            or type(request["live_con_id"]) is not int
            or request["live_con_id"] != selection["live_con_id"]):
        refuse()

    if (not isinstance(observed_surfaces, list)
            or not 1 <= len(observed_surfaces) <= MAX_SURFACES):
        refuse()
    seen_con_ids, seen_lifetimes = set(), set()
    selected = []
    for raw in observed_surfaces:
        entry = _state(raw)
        key = (entry["compositor_epoch"], entry["surface_lifetime_id"],
               entry["surface_generation"])
        if entry["live_con_id"] in seen_con_ids or key in seen_lifetimes:
            refuse()
        seen_con_ids.add(entry["live_con_id"])
        seen_lifetimes.add(key)
        if entry["live_con_id"] == selection["live_con_id"]:
            selected.append(entry)
    if len(selected) != 1:
        refuse()
    actual = selected[0]
    if actual["floating"] is not True or actual["fullscreen_mode"] != 0:
        refuse()
    for field in ("compositor_epoch", "surface_lifetime_id", "surface_generation",
                  "live_con_id", "app_id", "output", "workspace"):
        if actual[field] != selection[field]:
            refuse()
    if actual["rect"] != before:
        refuse()

    # Important: the existing pilot checks actual saved geometry, screen,
    # floating state, current output/workspace and fresh double Sway reading,
    # but its manual approval flags remain CI-only placeholders, not C5 grants.
    candidate_request = {
        "checkpoint_id": request["checkpoint_id"],
        "checkpoint_window_key": request["window_key"],
        "live_con_id": request["live_con_id"],
        "operator_selected": True,
        "execution_approved": True,
        "approval_kind": APPROVAL_KIND,
    }
    try:
        proposed = prepare(candidate_request, read_runner=read_runner,
                           legacy_reader=legacy_reader,
                           geometry_reader=geometry_reader)
    except (RehearsalRefused, ValueError, TypeError, KeyError, OSError):
        refuse()
    target, live = proposed["target"], proposed["current"]
    if (target["window_key"] != selection["window_key"]
            or live["app_id"] != actual["app_id"]
            or live["output"] != actual["output"]
            or live["workspace"] != actual["workspace"]
            or live["rect"] != actual["rect"]
            or target["rect"] != after
            or target["app_id"] != actual["app_id"]
            or target["output"] != actual["output"]
            or target["workspace"] != actual["workspace"]):
        refuse()

    return {
        "kind": KIND,
        "scope": "selected_live_surface_geometry_only",
        "status": "fixture_consistent_only",
        "checkpoint_id": request["checkpoint_id"],
        "window_key": request["window_key"],
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
        "requires_protected_swaypx_witness": True,
        "requires_independent_c3e_enrollment": True,
        "requires_protected_c5_consent": True,
        "manual_recheck_before_each_command": True,
        "safe_actions": [],
    }
