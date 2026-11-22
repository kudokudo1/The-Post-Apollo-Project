"""TimeW Scope A proposed native outcome matrix, CI-only and deny-only.

Combines REAL TimeW local journal views with SIMULATED C5 spend and SwayPX
post-resize observations. It neither verifies a native signer nor installs
C5, starts Sway, dispatches commands, changes a journal or authorizes Restore.
No result from this module can authorize geometry movement or retry.
"""
from __future__ import annotations

import os
import uuid

from MachineV2GeometryJournal import _rect, _summary

KIND = "timew-scope-a-outcome-uncertainty-ci-rehearsal-v1"
C5_CLAIMS = frozenset(("absent", "refused", "unknown", "spent"))
RECEIPT_CLAIMS = frozenset(("not_seen", "claimed_ok", "lost", "ambiguous"))
SURFACE_FIELDS = frozenset((
    "compositor_epoch", "surface_lifetime_id", "surface_generation",
    "live_con_id", "seat_id", "session_id", "output", "workspace",
))
JOURNAL_PHASES = frozenset((
    "prepared", "dispatching", "uncertain_requires_review",
    "verified_fixture_placement",
))

class FixtureHold(ValueError):
    pass


def hold():
    raise FixtureHold("TIMEW_SCOPE_A_NATIVE_OUTCOME_FIXTURE_HOLD")


def _id(value):
    if type(value) is not str:
        hold()
    try:
        if str(uuid.UUID(value)) != value:
            hold()
    except (TypeError, AttributeError, ValueError):
        hold()
    return value


def _surface(value):
    if type(value) is not dict or set(value) != SURFACE_FIELDS:
        hold()
    _id(value["compositor_epoch"])
    _id(value["surface_lifetime_id"])
    _id(value["session_id"])
    for name in ("surface_generation", "live_con_id"):
        v = value[name]
        if type(v) is not int or not 0 < v <= 9007199254740991:
            hold()
    for name in ("seat_id", "output", "workspace"):
        t = value[name]
        if (type(t) is not str or not 1 <= len(t) <= 128
                or any(ord(ch) < 32 or ord(ch) == 127 for ch in t)):
            hold()
    return dict(value)


def _trunc2(amount):
    """C signed integer / 2 truncates toward zero, unlike Python -odd // 2."""
    return amount // 2 if amount >= 0 else -((-amount) // 2)


def centered_pending_hint(before, *, width, height):
    """Source-linked arithmetic HINT for SwayPX floating resize_set.

    Derived from SwayPX sway/commands/resize.c pending.x/y -= grow/2.
    Actual width/height may clamp, arrange, or commit differently. A hint
    is never a substitute for the compositor's protected live observation.
    """
    box = _rect(before)
    if (type(width) is not int or type(height) is not int
            or not 1 <= width <= 100000 or not 1 <= height <= 100000):
        hold()
    dw, dh = width - box["width"], height - box["height"]
    return _rect({
        "x": box["x"] - _trunc2(dw),
        "y": box["y"] - _trunc2(dh),
        "width": width, "height": height,
    })


def inspect_ci_only(*, journal_view, c5_spend_claim, resize_receipt_claim,
                    move_receipt_claim, post_resize, final_observed,
                    selected_identity, observed_identity,
                    source_claim_active):
    """Reconcile supplied evidence only to a permanent NO-AUTHORITY result.

    All C5/source/receipt inputs are UNTRUSTED TEST CLAIMS. The journal view
    is local durable storage, not the independently protected C5 spend ledger.
    Even a fully consistent example is a diagnostic, never a production PASS.
    """
    if os.environ.get("CI") != "true" or os.environ.get("GITHUB_ACTIONS") != "true":
        hold()
    if (c5_spend_claim not in C5_CLAIMS
            or resize_receipt_claim not in RECEIPT_CLAIMS
            or move_receipt_claim not in RECEIPT_CLAIMS
            or type(source_claim_active) is not bool
            or type(journal_view) is not dict
            or type(journal_view.get("summary")) is not dict):
        hold()
    if journal_view.get("phase") not in JOURNAL_PHASES:
        hold()
    if any(journal_view.get(k) is not False for k in (
            "production_restore_allowed", "automatic_retry_allowed",
            "automatic_undo_allowed", "persistent_identity_verified")):
        hold()
    try:
        summary = _summary(journal_view["summary"])
        identity = _surface(selected_identity)
        observed = None if observed_identity is None else _surface(observed_identity)
        middle = None if post_resize is None else _rect(post_resize)
        final = None if final_observed is None else _rect(final_observed)
    except (ValueError, TypeError, KeyError, AttributeError):
        hold()
    if identity["live_con_id"] != summary["live_con_id"]:
        hold()

    # SwayPX's centered resize arithmetic is a HINT ONLY. A native resize
    # can be clamped or alter geometry in other ways. TimeW must consume an
    # independently authenticated observed rectangle for the move pre-state.
    hint = centered_pending_hint(
        summary["before_rect"], width=summary["target_rect"]["width"],
        height=summary["target_rect"]["height"])
    hint_matches = middle == hint if middle is not None else False
    same_surface = observed == identity if observed is not None else False

    # No local row or synthetic "no C5 spend" can establish absence of a
    # side effect. Unknown/lost/contradictory outcomes must be non-retryable.
    diagnosis = "UNKNOWN_HOLD"
    if (journal_view["phase"] == "prepared"
            and c5_spend_claim in ("absent", "refused")
            and resize_receipt_claim == "not_seen"
            and move_receipt_claim == "not_seen"):
        diagnosis = "UNTRUSTED_PRE_ACTION_HOLD"
    elif (journal_view["phase"] == "dispatching"
            and c5_spend_claim == "spent"
            and resize_receipt_claim == "claimed_ok"
            and move_receipt_claim == "claimed_ok"
            and source_claim_active is True
            and same_surface
            and middle is not None
            and middle["width"] == summary["target_rect"]["width"]
            and middle["height"] == summary["target_rect"]["height"]
            and final == summary["target_rect"]):
        # Claims alone NEVER prove source provenance, actual native receipt,
        # consent, absence of replay or reliable command completion.
        diagnosis = "COMPLETE_UNTRUSTED_FIXTURE_ONLY"

    return {
        "kind": KIND,
        "status": diagnosis,
        "read_only": True,
        "c5_status_is_caller_supplied": True,
        "sway_observations_are_caller_supplied": True,
        "local_journal_is_not_protected_c5_spend": True,
        "centered_resize_hint_matches_observation": hint_matches,
        "same_surface_claims_match": same_surface,
        "protected_source_verified": False,
        "protected_c5_spend_verified": False,
        "native_receipts_verified": False,
        "restore_allowed": False,
        "production_authorized": False,
        "automatic_retry_allowed": False,
        "automatic_undo_allowed": False,
        "native_geometry_dispatch_allowed": False,
        "manual_review_required": True,
        "safe_actions": [],
    }


def run_native_restore(*_args, **_kwargs):
    hold()
