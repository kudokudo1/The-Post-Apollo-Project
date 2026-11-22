"""TimeW Scope A / C3e signed source + geometry continuity; CI-ONLY FUSION.

No protected compositor origin, independently installed issuer, C5 consent,
one-use spend, live Sway dispatch, Brave identity or production permission.
All signers, clocks, Sway responses and selected-surface records are supplied
by untrusted CI fixtures. NEVER call this as an authorization decision.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests/connections/c3e_integration"))
sys.path.insert(0, str(ROOT / "services/time"))

import ConnectionsPurposeBoundEvidencePreflight as C3e
import MachineV2SelectedSurfaceReview as Selected
import MachineV2SurfaceContinuityReview as Continuity

KIND = "timew-v2-scope-a-signed-source-continuity-ci-only-v1"
DENIED = {
    "read_only": True,
    "restore_allowed": False,
    "production_authorized": False,
    "native_timew_geometry_allowed": False,
    "trusted_swaypx_compositor_verified": False,
    "compositor_surface_lifetime_verified": False,
    "independently_enrolled_issuer_verified": False,
    "active_unlocked_seat_verified": False,
    "c5_operator_consent_verified": False,
    "protected_one_use_spend_verified": False,
    "brave_window_identity_verified": False,
    "browser_tabs_restorable": False,
    "no_automatic_retry": True,
    "manual_review_required_for_unknown": True,
}


class FusionHold(ValueError):
    pass


def hold():
    raise FusionHold("TIMEW_SCOPE_A_SOURCE_CONTINUITY_FUSION_HOLD")


def inspect_ci_only(*, request, selection, observed_surfaces, samples,
                    challenge, signed_proof_raw, signature,
                    independently_pinned_signer_key,
                    separately_expected_signer_sha256,
                    separately_expected_other_role_key_sha256,
                    revoked_signer_sha256,
                    expected_host_id, minimum_release_epoch,
                    minimum_release_sequence,
                    expected_session_id, expected_seat_id,
                    now_ms, read_runner, legacy_reader, geometry_reader):
    """Join three existing tests without promoting any format proof to trust.

    Exact same selection and challenge flow through C3e format verification,
    TimeW saved/current selected surface review, and TimeW after-command
    continuity. The actual protected source and grant are deliberately absent.
    """
    if os.environ.get("CI") != "true" or os.environ.get("GITHUB_ACTIONS") != "true":
        hold()
    if (type(challenge) is not bytes or len(challenge) != 32
            or type(selection) is not dict
            or type(request) is not dict
            or type(samples) is not list
            or type(observed_surfaces) is not list):
        hold()
    digest = hashlib.sha256(challenge).hexdigest()
    if (selection.get("challenge_sha256") != digest
            or selection.get("session_id") != expected_session_id
            or selection.get("seat_id") != expected_seat_id
            or request.get("checkpoint_id") != selection.get("checkpoint_id")
            or request.get("window_key") != selection.get("window_key")
            or request.get("live_con_id") != selection.get("live_con_id")):
        hold()
    try:
        source = C3e.inspect_timew_scope_a_ci_only(
            selection=selection,
            challenge=challenge,
            signed_proof_raw=signed_proof_raw,
            signature=signature,
            independently_pinned_signer_key=independently_pinned_signer_key,
            separately_expected_signer_sha256=separately_expected_signer_sha256,
            separately_expected_other_role_key_sha256=separately_expected_other_role_key_sha256,
            revoked_signer_sha256=revoked_signer_sha256,
            expected_host_id=expected_host_id,
            minimum_release_epoch=minimum_release_epoch,
            minimum_release_sequence=minimum_release_sequence,
            now_ms=now_ms,
        )
        selected = Selected.review_selected_fixture(
            request=request, selection=selection,
            observed_surfaces=observed_surfaces, now_ms=now_ms,
            expected_session_id=expected_session_id,
            expected_seat_id=expected_seat_id,
            expected_challenge_sha256=digest,
            read_runner=read_runner,
            legacy_reader=legacy_reader, geometry_reader=geometry_reader,
        )
        continuous = Continuity.inspect_fixture(
            selection=selection, samples=samples,
            expected_session_id=expected_session_id,
            expected_seat_id=expected_seat_id,
            expected_challenge_sha256=digest,
        )
    except (C3e.ScopedEvidenceHold, Selected.ScopeARefused,
            Selected.RehearsalRefused, TypeError, KeyError, ValueError,
            OSError, RecursionError):
        hold()

    # The C3e test confirms only a correctly formed signature with
    # separately caller-provided CI keys and pins. It cannot supply native
    # compositor identity, independently protected challenge, or C5 consent.
    if (source.get("fixtureProofPurpose") != C3e.TIMEW_PURPOSE
            or source.get("callerPinnedFixtureSignatureVerified") is not True
            or source.get("testOnlyExpectedSourceDigestMatched") is not True
            or source.get("testOnlyExpectedChallengeDigestMatched") is not True
            or source.get("originalMutationOutcome") != "UNKNOWN"
            or any(source.get(key) is not False for key in C3e.DENIED)):
        hold()
    if (selected.get("status") != "fixture_consistent_only"
            or selected.get("checkpoint_id") != selection["checkpoint_id"]
            or selected.get("window_key") != selection["window_key"]
            or any(selected.get(key) is not False for key in (
                "restore_allowed", "production_authorized",
                "source_origin_verified", "active_seat_verified",
                "c5_operator_consent_verified", "one_use_grant_spent"))
            or selected.get("safe_actions") != []):
        hold()
    if (continuous.get("status") != "fixture_continuity_only"
            or any(continuous.get(key) is not False for key in (
                "restore_allowed", "production_authorized",
                "source_origin_verified", "active_seat_verified",
                "c5_operator_consent_verified", "one_use_grant_spent"))
            or continuous.get("safe_actions") != []):
        hold()
    return {
        "kind": KIND,
        "status": "SIGNED_TEST_SOURCE_AND_GEOMETRY_CONSISTENT_NO_AUTHORITY",
        "proof_scope": "timew-selected-live-surface-geometry-only",
        "source_is_ci_only": True,
        "all_evidence_is_caller_supplied": True,
        "replayed_consistent_fixture_still_untrusted": True,
        "requires_protected_swaypx_selection": True,
        "requires_independent_c3e_c4b_enrollment": True,
        "requires_protected_c5_one_use_consent": True,
        **DENIED,
        "safe_actions": [],
    }


def run_native_timew_scope_a(*_args, **_kwargs):
    hold()
