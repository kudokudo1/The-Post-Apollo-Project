"""P38: deny-only PHONE adapter for ACTUAL C3e-Z/C4b CI result shapes.

Only P37 verifies cryptographic signatures here; the C3e-Z/C4b *results*
are mere caller-provided summaries. Neither is a separately authenticated
running-host witness, and there is no PHONE-specific genuine C5 consent
receipt or protected production key. This adapter NEVER returns approval,
does not consume a real challenge, and cannot reach the Personal vault.

Do not expose as QML, D-Bus, IPC, CLI, Secret Service or a grant API.
"""
from __future__ import annotations

import json
import re
from typing import Any

import PhonePersonalSignedTrustP37 as P37

# Exact formats currently present on main (Nov 11, 2026). Any change of
# upstream source schema requires a reviewed PHONE adapter version update.
C4B_FIELDS = frozenset({
    "epoch", "sequence", "package_sha256", "receipt_key_sha256",
    "installed_guest_measured", "host_authenticated",
    "production_authority", "can_begin_sign_in", "credential_actions_enabled",
})
C4B_FALSE = frozenset({
    "installed_guest_measured", "host_authenticated", "production_authority",
    "can_begin_sign_in", "credential_actions_enabled",
})
C3EZ_SCHEMA = "postapollo.connections.c3ez-release-bound-host-denial.ci-v1"
C3EZ_TRUE = frozenset({
    "releaseSourceAndRuntimePinsMatchedInCI",
    "releaseReceiptSignerMatchedInCI",
    "fullRecordChallengeConsumedInRootLocalCI",
})
C3EZ_FALSE = frozenset({
    "independentlyEnrolledReleaseRoot", "independentlyEnrolledWitnessKey",
    "independentlyEnrolledReceiptKey", "installedHostEvidenceAuthenticated",
    "externalChallengeCustodyVerified", "externalRollbackResistanceVerified",
    "c5HumanConsentVerified", "hostAuthenticated", "canBeginSignIn",
    "credentialActionsEnabled", "productionAuthority",
    "externalIssuerCustodyVerified", "signedGuestOriginAuthenticated",
    "evidenceCryptographicallyAttested", "installedGuestMeasured",
    "canApprove",
})
C3EZ_FIELDS = frozenset({"schema"}) | C3EZ_TRUE | C3EZ_FALSE
HEX64 = re.compile(r"^[0-9a-f]{64}$", re.ASCII)

# No success, grant, key unlock or saved note state exists in this module.
REFUSED = {
    "status": "EXTERNAL_TRUST_CONTRACT_UNAVAILABLE",
    "productionEnabled": False,
    "vaultWriteEnabled": False,
    "humanConsentVerified": False,
    "installedHostVerified": False,
    "keyReleaseEnabled": False,
}
CI_COMPATIBLE = {
    **REFUSED,
    "status": "CI_FORMATS_RECOGNIZED_NOT_AUTHENTICATED",
}


def _valid_c4b(candidate: object, request: dict, host: dict) -> bool:
    # Caller passes dataclasses.asdict(SilverblueReleaseCandidateV1).
    # This is NOT permission to convert raw untrusted JSON to authority.
    return (
        type(candidate) is dict and set(candidate) == C4B_FIELDS
        and all(candidate[k] is False for k in C4B_FALSE)
        and type(candidate["epoch"]) is int
        and type(candidate["sequence"]) is int
        and candidate["epoch"] == request["minimumReleaseEpoch"]
        and candidate["sequence"] == host["releaseSequence"]
        and candidate["sequence"] >= request["minimumReleaseSequence"]
        and type(candidate["package_sha256"]) is str
        and HEX64.fullmatch(candidate["package_sha256"]) is not None
        and candidate["package_sha256"] == host["releaseSha256"]
        and type(candidate["receipt_key_sha256"]) is str
        and HEX64.fullmatch(candidate["receipt_key_sha256"]) is not None
    )


def _valid_c3ez(result: object) -> bool:
    # The C3e-Z result is not the signed evidence itself. We inspect a
    # CLOSED whitelist of *deny-only CI diagnostics*, NEVER a trust grant.
    return (
        type(result) is dict and set(result) == C3EZ_FIELDS
        and result["schema"] == C3EZ_SCHEMA
        and all(result[k] is True for k in C3EZ_TRUE)
        and all(result[k] is False for k in C3EZ_FALSE)
    )


def compare_fixture_handoff(
    *, expected_request: object, host_frame: bytes, host_signature: bytes,
    host_public_key: bytes, consent_frame: bytes, consent_signature: bytes,
    consent_public_key: bytes, now: int, c4b_candidate: object,
    c3ez_result: object, genuine_c5_receipt: object = None,
) -> dict[str, object]:
    """ONLY recognize known, non-authorizing current upstream CI outputs.

    The alleged C4b/C3e-Z outputs are *caller-supplied*, not independently
    authenticated native source evidence. C5 has no accepted production
    receipt, so ANY purported real C5 receipt currently fails closed.
    """
    try:
        # No C5 PHONE consent issuer or key lifecycle currently exists.
        if genuine_c5_receipt is not None:
            return dict(REFUSED)
        checked = P37.compare_signed_fixture_receipts(
            expected_request=expected_request,
            host_frame=host_frame, host_signature=host_signature,
            host_public_key=host_public_key, consent_frame=consent_frame,
            consent_signature=consent_signature,
            consent_public_key=consent_public_key, now=now,
        )
        if checked != P37.MATCHED_FIXTURE:
            return dict(REFUSED)
        # P37's exact canonical decoder already enforces bounded frames.
        # Do not use the signed "claim" as independent host observation.
        host = P37._signed_frame(host_frame, P37.HOST_FIELDS)
        if (not _valid_c4b(c4b_candidate, expected_request, host)
                or not _valid_c3ez(c3ez_result)):
            return dict(REFUSED)
        return dict(CI_COMPATIBLE)
    except (TypeError, ValueError, KeyError, AttributeError,
            P37.ReceiptRefused, OverflowError):
        return dict(REFUSED)


# No C3e-Z challenge consumption, imported C5 reviewer, key lookup, local
# persistence, re-authentication, host process inspection or vault write.
