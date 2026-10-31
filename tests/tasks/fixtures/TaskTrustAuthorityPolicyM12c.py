"""M12c proposed trust-authority governance model (pure, synthetic only).

No disk, network, cryptography, GitHub mutation, credential storage, launch
or production writer access. All attestations are untrusted *test arguments*.
"SYNTHETIC_REVIEW_ELIGIBLE" never means a signature or authority is verified.
"""
from __future__ import annotations

import re

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Z][A-Z0-9_-]{5,63}\Z")


def _exact(value, names):
    return type(value) is dict and set(value) == set(names)


def _token(value):
    return type(value) is str and _ID.fullmatch(value) is not None


def _fingerprint(value):
    return type(value) is str and _SHA.fullmatch(value) is not None


def _refuse(reason):
    return {"status": "REFUSED", "reason": reason,
            "syntheticOnly": True, "productionAuthorized": False,
            "trustStoreChanged": False, "activationApproved": False}


def _candidate(kind, details):
    return {"status": "SYNTHETIC_REVIEW_ELIGIBLE", "reason": kind,
            "review": details, "syntheticOnly": True,
            "productionAuthorized": False, "trustStoreChanged": False,
            "activationApproved": False}


ROLES = ("custodian", "signer", "reviewer", "operator")
ANCHOR_FIELDS = ("rootProvenance", "trustedKeyId", "trustedKeyFingerprint",
                 "generationFloor", "revokedKeyIds", "roles")
RELEASE_FIELDS = ("keyId", "keyFingerprint", "generation", "artifactDigest",
                  "declaredSigner", "releaseSuppliedTrustRoot")
EVIDENCE_FIELDS = ("signatureVerifiedAgainstExternalRoot",
                   "artifactBytesVerifiedAgainstSignedManifest",
                   "generationFloorReadFromIndependentStore",
                   "identityAndApprovalEvidenceExternal",
                   "approvedByReviewer", "operatorReleaseReview")
ROTATION_FIELDS = ("oldKeyId", "newKeyId", "newFingerprint", "newGenerationFloor",
                   "releaseSuppliedTrustRoot")
ROTATION_EVIDENCE_FIELDS = ("oldRootEndorsementVerified",
                            "newRootPossessionVerified",
                            "independentCustodianApproval",
                            "independentReviewerApproval",
                            "operatorTrustRootReview",
                            "generationFloorPersistedExternally")


def _anchor_error(anchor):
    if not _exact(anchor, ANCHOR_FIELDS):
        return "INDEPENDENT_ANCHOR_REQUIRED"
    if (anchor["rootProvenance"] != "OPERATOR_CONTROLLED_OUTSIDE_RELEASE"
            or not _token(anchor["trustedKeyId"])
            or not _fingerprint(anchor["trustedKeyFingerprint"])
            or type(anchor["generationFloor"]) is not int
            or anchor["generationFloor"] < 0
            or type(anchor["revokedKeyIds"]) is not list
            or not all(_token(x) for x in anchor["revokedKeyIds"])
            or len(set(anchor["revokedKeyIds"])) != len(anchor["revokedKeyIds"])
            or not _exact(anchor["roles"], ROLES)
            or not all(_token(anchor["roles"][role]) for role in ROLES)):
        return "INVALID_ANCHOR_POLICY"
    if len(set(anchor["roles"].values())) != len(ROLES):
        return "SEPARATION_OF_DUTIES_REQUIRED"
    if anchor["trustedKeyId"] in anchor["revokedKeyIds"]:
        return "TRUSTED_KEY_REVOKED"
    return None


def assess_release(anchor, release, evidence):
    """Check governance consistency, never authorize release or write."""
    invalid = _anchor_error(anchor)
    if invalid:
        return _refuse(invalid)
    if not _exact(release, RELEASE_FIELDS):
        return _refuse("INVALID_RELEASE_DESCRIPTOR")
    if not (_token(release["keyId"])
            and _fingerprint(release["keyFingerprint"])
            and type(release["generation"]) is int
            and 0 < release["generation"] <= 1_000_000_000
            and _fingerprint(release["artifactDigest"])
            and _token(release["declaredSigner"])
            and release["releaseSuppliedTrustRoot"] is False):
        return _refuse("INVALID_RELEASE_DESCRIPTOR")
    if (release["keyId"] in anchor["revokedKeyIds"]
            or release["keyId"] != anchor["trustedKeyId"]
            or release["keyFingerprint"] != anchor["trustedKeyFingerprint"]):
        return _refuse("UNTRUSTED_OR_REVOKED_SIGNER_KEY")
    if release["generation"] <= anchor["generationFloor"]:
        return _refuse("RELEASE_ROLLBACK_OR_REPLAY")
    if release["declaredSigner"] != anchor["roles"]["signer"]:
        return _refuse("UNAUTHORIZED_SIGNER")
    if not _exact(evidence, EVIDENCE_FIELDS):
        return _refuse("EXTERNAL_RELEASE_EVIDENCE_REQUIRED")
    if not all(evidence[k] is True for k in EVIDENCE_FIELDS):
        return _refuse("EXTERNAL_RELEASE_EVIDENCE_INCOMPLETE")
    return _candidate("EXTERNAL_RELEASE_EVIDENCE_REVIEWED", {
        "keyId": release["keyId"], "generation": release["generation"],
        "artifactDigest": release["artifactDigest"],
        "actualSignatureVerificationPerformedHere": False,
        "operatorActivationDecisionStillRequired": True
    })


def assess_rotation(anchor, proposal, evidence):
    """Review synthetic rotation plan without adding/revoking real keys.

    Root rotation requires a separate operator approval and transition proof.
    Booleans here *do not prove* cross-signatures or independent identities.
    """
    invalid = _anchor_error(anchor)
    if invalid:
        return _refuse(invalid)
    if not _exact(proposal, ROTATION_FIELDS):
        return _refuse("INVALID_ROTATION_PROPOSAL")
    if not (_token(proposal["oldKeyId"]) and _token(proposal["newKeyId"])
            and proposal["oldKeyId"] == anchor["trustedKeyId"]
            and proposal["newKeyId"] != proposal["oldKeyId"]
            and proposal["newKeyId"] not in anchor["revokedKeyIds"]
            and _fingerprint(proposal["newFingerprint"])
            and proposal["newFingerprint"] != anchor["trustedKeyFingerprint"]
            and type(proposal["newGenerationFloor"]) is int
            and proposal["newGenerationFloor"] >= anchor["generationFloor"]
            and proposal["releaseSuppliedTrustRoot"] is False):
        return _refuse("INVALID_ROTATION_PROPOSAL")
    if not _exact(evidence, ROTATION_EVIDENCE_FIELDS):
        return _refuse("ROTATION_EVIDENCE_REQUIRED")
    if not all(evidence[k] is True for k in ROTATION_EVIDENCE_FIELDS):
        return _refuse("ROTATION_EVIDENCE_INCOMPLETE")
    return _candidate("ROTATION_PENDING_EXTERNAL_APPROVAL", {
        "oldKeyId": proposal["oldKeyId"],
        "proposedKeyId": proposal["newKeyId"],
        "proposedGenerationFloor": proposal["newGenerationFloor"],
        "actualTrustRootInstalledHere": False,
        "separateOperatorActivationStillRequired": True,
    })
