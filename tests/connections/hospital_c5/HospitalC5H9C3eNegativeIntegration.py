#!/usr/bin/env python3
"""DOC 4 Hospital C5-H9: combine original C3e diagnostics and exact C5 review.

Disposable GitHub Linux CI ONLY. A C3e observed Identity read-only packet,
a source-consistent PX Room review, and a matching *claimed* human gesture
cannot together provide Hospital source trust, consent, one-use custody,
signer access, PX COMMIT or production permission.

This module is NEVER imported by the Hospital issuer or runtime. It does not
modify the C3e, C4b, PX, native agent, SwayPX or signer owners' sources.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/connections/hospital"))
import HospitalNativeIssuerCore as C

def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("HOSPITAL_C5H9_PINNED_ORIGINAL_SOURCE_UNAVAILABLE")
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj

# Exact original, merged owner modules. Do not replace with fake protocols.
M = _load("hospital_c5h9_original_c3e_packet_nonadmission",
          ROOT / "tests/connections/c3e_release_trust/"
                 "C3eIdentityPacketOriginNonAdmissionCI.py")
R = _load("hospital_c5h9_original_hospital_exact_review",
          ROOT / "tests/connections/hospital_c5/"
                 "HospitalC5ExactConsentProbe.py")

SCHEMA = "postapollo.hospital.c5h9.c3e-source-comparison-ci.v1"
STATUS = "C3E_PACKET_AND_HOSPITAL_CLAIM_NOT_NATIVE_CONSENT_HOLD"
DENIED = {
    "identityPacketIsHospitalSourceProof": False,
    "protectedIssuerProducerEnrolled": False,
    "hospitalRoomSourceAuthenticated": False,
    "activeUnlockedSeatAuthenticated": False,
    "actualExactRoomDisplayVerified": False,
    "humanGestureAuthenticated": False,
    "independentlyCurrentHistoryVerified": False,
    "independentOneUseConsentSpent": False,
    "canPassC5H4HumanConsentGate": False,
    "signingKeyLoadingAllowed": False,
    "protectedPxRoomCommitAllowed": False,
    "safeToRetry": False,
    "productionHospitalAuthorized": False,
}
C3E_FIELDS = frozenset({
    "schema", "status", "packetSha256LocalComparisonOnly",
    "kernelSenderPidObservedOnly", "localReadOnlyOperation",
    "originalDiagnosticStatus", "next", *M.DENIED,
})
CLAIM_RESULT_FIELDS = frozenset({
    "schema", "status", "claimMatchesReview",
    "externalConsentProducerAuthenticated", "humanConsentVerified",
    "independentHistoryVerified", "signingAllowed",
    "nativeRoomMutationAllowed", "productionAuthorized", "safeActions",
})


def compare_ci_only(identity_packet_diagnostic, reference, untrusted_claim):
    """Read-only exact-shape comparison. A matching claim is still HOLD.

    The C3e report itself is supplied from a disposable test boundary. Even
    if every field matches, neither that report nor R's synthetic exact
    review is signed independently, enrolled or linked to the real renderer.
    """
    x = identity_packet_diagnostic
    if (type(x) is not dict or set(x) != C3E_FIELDS
            or x.get("schema") != M.SCHEMA
            or x.get("status") != M.STATUS
            or x.get("next") != "HOLD_NO_PROTECTED_IDENTITY_OR_AUTO_RETRY"
            or x.get("localReadOnlyOperation") != "CUSTODIAN_STATUS"
            or x.get("originalDiagnosticStatus") != M.P.S.STATUS_HOLD
            or type(x.get("packetSha256LocalComparisonOnly")) is not str
            or C.SHA.fullmatch(x["packetSha256LocalComparisonOnly"]) is None
            or type(x.get("kernelSenderPidObservedOnly")) is not int
            or x["kernelSenderPidObservedOnly"] <= 1
            or any(x.get(key) is not False for key in M.DENIED)):
        C.deny("C5H9_C3E_CANNOT_ASSERT_HOSPITAL_PROTECTED_TRUST")
    y = untrusted_claim
    if (type(y) is not dict or set(y) != CLAIM_RESULT_FIELDS
            or y.get("schema") !=
                "postapollo.hospital.c5h6.consent-probe-result.v2"
            or y.get("status") not in (
                "MATCHING_CLAIM_UNTRUSTED_HOLD",
                "CHANGED_OR_STALE_CLAIM_HOLD")
            or type(y.get("claimMatchesReview")) is not bool
            or y["safeActions"] != []
            or any(y.get(k) is not False for k in (
                "externalConsentProducerAuthenticated",
                "humanConsentVerified", "independentHistoryVerified",
                "signingAllowed", "nativeRoomMutationAllowed",
                "productionAuthorized"))):
        C.deny("C5H9_UNTRUSTED_DISPLAY_CANNOT_ASSERT_CONSENT")
    if (type(reference) is not dict
            or set(reference) != {"review", "reviewDigest"}
            or type(reference["review"]) is not dict
            or set(reference["review"]) != R.REVIEW_FIELDS
            or reference["review"].get("schema") != R.REVIEW_SCHEMA
            or type(reference["reviewDigest"]) is not str
            or C.SHA.fullmatch(reference["reviewDigest"]) is None):
        C.deny("C5H9_EXACT_REVIEW_REFERENCE_INVALID")
    # Reuse the original comparison digest, never invent an auth signature.
    import hashlib
    if (hashlib.sha256(
            R.DOMAIN + C.canonical(reference["review"])).hexdigest()
            != reference["reviewDigest"]):
        C.deny("C5H9_EXACT_REVIEW_REFERENCE_CHANGED")
    if ((y["status"] == "MATCHING_CLAIM_UNTRUSTED_HOLD")
            != y["claimMatchesReview"]):
        C.deny("C5H9_DISPLAY_STATUS_CONTRADICTS_CLAIM")
    return {
        "schema": SCHEMA, "status": STATUS,
        "c3eStatus": x["originalDiagnosticStatus"],
        "identityPacketObservedOnly": True,
        "untrustedDisplayClaimMatches": y["claimMatchesReview"],
        "reviewDigestLocalOnly": reference["reviewDigest"],
        "next": "HOLD_UNTIL_INDEPENDENT_H0_C0_AND_PROTECTED_PX_W0_T0",
        **DENIED, "safeActions": [],
    }


def authorize_hospital_room(*_args, **_kwargs):
    C.deny("C5H9_NO_ENROLLED_HUMAN_CONSENT_OR_INDEPENDENT_CUSTODIAN")
