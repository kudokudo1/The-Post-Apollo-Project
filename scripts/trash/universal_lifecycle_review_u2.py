#!/usr/bin/env python3
"""Trash++ U2 // in-memory, DENY-ONLY cross-owner lifecycle risk review.

Strictly classifies untrusted *metadata* about a proposed Trash, Restore or
Burn. This has NO source adapters, filesystem/database calls, identity broker,
signer, owner execution path, permission grant, UI callback or CLI.

Even a perfect-looking caller-provided record is not a cryptographic witness
and cannot authorize mutation. Existing GIO and managed-copy operations remain
owned by their original, separately reviewed implementations.
"""
from __future__ import annotations

import re
from types import MappingProxyType

SCHEMA = "post-apollo.trashpp.universal-lifecycle-review.u2"
ACTIONS = frozenset(("trash", "restore", "burn"))
SCOPES = frozenset(("gio-file", "managed-copy", "source-owned",
                    "protected-archive"))
STATES = frozenset(("active", "trashed", "unknown"))
REVISION_STATES = frozenset(("unverified", "reported_stable"))
RETENTION_STATES = frozenset(("unknown", "eligible", "hold", "mandatory"))
DEPENDENCY_STATES = frozenset(("unknown", "none_reported", "linked"))
RECOVERY_STATES = frozenset(("unknown", "copy_reported", "restore_test_reported"))
WRITER_STATES = frozenset(("unknown", "stable_reported", "concurrent"))
DESTINATION_STATES = frozenset(("unknown", "empty_reported", "occupied"))
CONFIRMATION_STATES = frozenset(("none", "first_click", "second_click_reported"))
OWNER_GRANT_STATES = frozenset(("absent", "reported"))

FIELDS = frozenset((
    "schema", "operation", "ownerId", "resourceId", "expectedRevision",
    "resourceScope", "resourceState", "revisionWitnessState",
    "retentionState", "dependencyState", "recoveryState", "writerState",
    "destinationState", "confirmationState", "ownerGrantState",
))
OWNER = re.compile(r"^[A-Za-z0-9._:-]{1,96}$")
RESOURCE = re.compile(r"^[A-Za-z0-9._:|-]{1,200}$")
SHA = re.compile(r"^[0-9a-f]{64}$")

# Review-time conservative categories only. These are NOT live registered
# owners, identity claims or grants. The actual source owners remain separate.
# Unknown owner IDs are refused; no caller may register an owner here.
OWNER_REVIEW_PROFILES = MappingProxyType({
    "filesystem-gio": ("gio-file", "ordinary"),
    "trashpp-managed-copy": ("managed-copy", "disposable"),
    "demo-scrape": ("source-owned", "evidence"),
    "weather-events": ("source-owned", "evidence"),
    "weather-dossiers": ("source-owned", "evidence"),
    "apollo-hub-notes": ("source-owned", "personal"),
    "apollo-hub-todo": ("source-owned", "personal"),
    "hospital": ("source-owned", "regulated"),
    "time-machine": ("source-owned", "evidence"),
    "company": ("source-owned", "business"),
    "social": ("source-owned", "personal"),
    "finance": ("source-owned", "regulated"),
    "identity": ("source-owned", "security"),
})
HIGH_RISK = frozenset(("regulated", "security", "evidence", "business",
                       "personal"))


class LifecycleReviewRefused(ValueError):
    """Fixed, non-sensitive error code. Never interpolate caller values."""


def _require(ok, reason):
    if not ok:
        raise LifecycleReviewRefused(reason)


def _enum(value, allowed):
    return type(value) is str and value in allowed


def review(request):
    """Return owner-review blockers, never an executable or allowed action.

    All status fields are UNTRUSTED caller reports, even when named
    'reported_stable' or 'restore_test_reported'. A trusted owner adapter
    will eventually need independent evidence, authorization and atomic
    commit-time revalidation; those capabilities are not in U2.
    """
    _require(type(request) is dict and set(request) == FIELDS,
             "U2_REQUEST_SCHEMA_REFUSED")
    _require(request["schema"] == SCHEMA and
             _enum(request["operation"], ACTIONS),
             "U2_OPERATION_REFUSED")
    _require(type(request["ownerId"]) is str and
             OWNER.fullmatch(request["ownerId"]) is not None and
             type(request["resourceId"]) is str and
             RESOURCE.fullmatch(request["resourceId"]) is not None and
             type(request["expectedRevision"]) is str and
             SHA.fullmatch(request["expectedRevision"]) is not None,
             "U2_IDENTITY_OR_REVISION_REFUSED")

    for name, options in (
        ("resourceScope", SCOPES), ("resourceState", STATES),
        ("revisionWitnessState", REVISION_STATES),
        ("retentionState", RETENTION_STATES),
        ("dependencyState", DEPENDENCY_STATES),
        ("recoveryState", RECOVERY_STATES),
        ("writerState", WRITER_STATES),
        ("destinationState", DESTINATION_STATES),
        ("confirmationState", CONFIRMATION_STATES),
        ("ownerGrantState", OWNER_GRANT_STATES),
    ):
        _require(_enum(request[name], options), "U2_UNTRUSTED_STATUS_REFUSED")

    operation = request["operation"]
    profile = OWNER_REVIEW_PROFILES.get(request["ownerId"])
    category = profile[1] if profile is not None else "unregistered"
    reasons = {
        "owner_execution_not_connected",
        "owner_identity_not_authenticated",
        "revision_witness_not_authenticated",
        "permission_and_consent_not_authenticated",
    }

    if profile is None:
        reasons.add("owner_review_profile_missing")
    elif request["resourceScope"] != profile[0]:
        reasons.add("owner_scope_mismatch")

    if request["resourceScope"] == "source-owned":
        reasons.add("source_owned_writer_not_delegated")
    elif request["resourceScope"] == "protected-archive":
        reasons.add("protected_archive_is_read_only")
    if category in HIGH_RISK:
        reasons.add("protected_information_owner_review_required")

    if request["revisionWitnessState"] != "reported_stable":
        reasons.add("revision_not_reported_stable")
    if request["ownerGrantState"] != "reported":
        reasons.add("owner_grant_not_reported")

    if request["retentionState"] != "eligible":
        reasons.add("retention_unknown_or_protected")
    if request["dependencyState"] != "none_reported":
        reasons.add("dependencies_unresolved")
    if request["writerState"] != "stable_reported":
        reasons.add("writer_state_unresolved")

    if operation == "trash":
        if request["resourceState"] != "active":
            reasons.add("resource_not_confirmed_active")
        if request["recoveryState"] != "restore_test_reported":
            reasons.add("recoverable_restore_not_demonstrated")
    elif operation == "restore":
        if request["resourceState"] != "trashed":
            reasons.add("resource_not_confirmed_trashed")
        if request["recoveryState"] != "restore_test_reported":
            reasons.add("restoration_not_demonstrated")
        if request["destinationState"] != "empty_reported":
            reasons.add("restore_destination_conflict_unresolved")
    else:
        # Burn is not an alternative to a first Trash when U2 is reviewing a
        # managed lifecycle. Do not bypass the recovery/retention period.
        if request["resourceState"] != "trashed":
            reasons.add("resource_not_confirmed_in_trash")
        if request["confirmationState"] != "second_click_reported":
            reasons.add("two_step_burn_unverified")
        reasons.add("owner_signed_burn_receipt_not_available")
        reasons.add("permanent_deletion_authority_unavailable")

    # The result contains no caller-provided identity, resource ID, revision,
    # path, bytes, description, payload or private record metadata.
    return {
        "schema": SCHEMA,
        "state": "DENY_ONLY_OWNER_REVIEW",
        "operation": operation,
        "reviewProfile": category,
        "profileRecognized": profile is not None,
        "holdReasons": sorted(reasons),
        "readOnly": True,
        "sourceBytesRead": False,
        "ownerAuthorityVerified": False,
        "sourceRevisionVerified": False,
        "retentionVerified": False,
        "dependenciesVerified": False,
        "restoreVerified": False,
        "humanConsentVerified": False,
        "captureAllowed": False,
        "trashAllowed": False,
        "restoreAllowed": False,
        "burnAllowed": False,
        "productionAllowed": False,
        "deleteOriginalAllowed": False,
        "safeActions": [],
        "requiresIndependentOwnerReview": True,
    }


if __name__ == "__main__":
    raise SystemExit(1)  # No CLI, daemon, live inputs or mutation operation.
