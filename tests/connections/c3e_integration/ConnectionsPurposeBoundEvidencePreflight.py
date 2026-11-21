#!/usr/bin/env python3
"""C3e cross-owner PURPOSE-SEPARATED Ed25519 evidence, CI-only.

This reads a caller-supplied signed fixture and independently supplied
CI-only expected bytes and keys. Real issuer key custody, compositor origin,
Hospital writer origin, antirollback and C5 consent are NOT established.
No signing, installed source, socket, key provisioning or native dispatcher.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests/connections/c3e_timew"))
sys.path.insert(0, str(ROOT / "services/connections/hospital/staffing"))

import TimeWSelectedSurfacePacketPreflight as TimeW
import StaffingRecoveryQueryPreflight as Hospital

SCHEMA = "postapollo.connections.c3e-cross-owner-purpose-proof.ci-v1"
TIMEW_PURPOSE = "timew-selected-live-surface-geometry-only"
HOSPITAL_PURPOSE = "hospital-staffing-read-only-original-commit-recover"
TIMEW_AUDIENCE = TimeW.ScopeA.AUDIENCE
HOSPITAL_AUDIENCE = "hospital-staffing-original-commit-read-only-recovery"
TIMEW_DOMAIN = b"postapollo.connections.c3e-timew-surface-proof.ci-v1\x00"
HOSPITAL_DOMAIN = b"postapollo.connections.c3e-hospital-recover-proof.ci-v1\x00"
RULES = {
    TIMEW_PURPOSE: (TIMEW_AUDIENCE, TIMEW_DOMAIN),
    HOSPITAL_PURPOSE: (HOSPITAL_AUDIENCE, HOSPITAL_DOMAIN),
}
FIELDS = frozenset((
    "schema", "purpose", "audience", "sourceSha256",
    "challengeSha256", "signerKeySha256", "hostId",
    "releaseEpoch", "releaseSequence", "issuedMs", "expiresMs",
))
DIGEST = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
HOST = re.compile(r"[a-z0-9][a-z0-9-]{2,63}\Z", re.ASCII)
MAX_RECORD = 4096
MAX_MS = 9007199254740991
MAX_LEASE_MS = 5000  # CI-only, not a production selection/consent lease.
DENIED = {
    "independentlyEnrolledIssuerRootVerified": False,
    "independentlyInstalledReleaseProven": False,
    "realCompositorSelectedSurfaceAuthenticated": False,
    "realHospitalWriterResultAuthenticated": False,
    "activeUnlockedSeatVerified": False,
    "independentExternalChallengeIssuerVerified": False,
    "challengeReplayOrSpendProtected": False,
    "durableOutcomeJournalVerified": False,
    "protectedOneUseOperatorConsentVerified": False,
    "nativeTimeWGeometryAllowed": False,
    "nativeHospitalRECOVERAllowed": False,
    "sameGrantCOMMITRetryAllowed": False,
    "canSignSelectedSurface": False,
    "canMoveWindow": False,
    "canAttachSession": False,
    "canSucceedDoctor": False,
    "productionAuthority": False,
}


class ScopedEvidenceHold(ValueError):
    pass


def _hold(reason):
    raise ScopedEvidenceHold("C3E_SCOPED_EVIDENCE_HOLD // " + reason)


def _canonical(obj):
    try:
        return json.dumps(obj, sort_keys=True, ensure_ascii=True,
                          allow_nan=False, separators=(",", ":")).encode("ascii")
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise ScopedEvidenceHold("C3E_SCOPED_EVIDENCE_HOLD // INVALID_CANONICAL_DATA") from exc


def _unique(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            _hold("DUPLICATE_SIGNED_PROOF_FIELD")
        d[k] = v
    return d


def _nonfinite(_):
    _hold("NONFINITE_SIGNED_PROOF")


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _hex(v):
    if type(v) is not str or DIGEST.fullmatch(v) is None:
        _hold("INVALID_PINNED_FINGERPRINT")
    return v


def _integer(v, *, positive=False):
    if type(v) is not int or v < (1 if positive else 0) or v > MAX_MS:
        _hold("INVALID_PROOF_INTEGER")
    return v


def _issuer_key(public, separately_pinned_sha256,
                separately_pinned_other_purpose_sha256, revoked):
    if not isinstance(public, Ed25519PublicKey):
        _hold("PUBLIC_SIGNER_KEY_REQUIRED")
    if type(revoked) is not tuple or len(revoked) > 64:
        _hold("INVALID_REVOCATION_ROSTER")
    if any(type(x) is not str or DIGEST.fullmatch(x) is None for x in revoked):
        _hold("INVALID_REVOCATION_ROSTER")
    if tuple(sorted(set(revoked))) != revoked:
        _hold("INVALID_REVOCATION_ROSTER")
    sha = _hash(public.public_bytes(Encoding.Raw, PublicFormat.Raw))
    if (sha != _hex(separately_pinned_sha256)
            or sha == _hex(separately_pinned_other_purpose_sha256)):
        _hold("SIGNER_SUBSTITUTION_OR_ROLE_KEY_ALIAS")
    if sha in revoked:
        _hold("REVOKED_SIGNER")
    return sha


def _inspect_ci_only(*, purpose, expected_source_raw, expected_challenge,
                     signed_proof_raw, signature,
                     independently_pinned_signer_key,
                     separately_expected_signer_sha256,
                     separately_expected_other_role_key_sha256,
                     revoked_signer_sha256,
                     expected_host_id, minimum_release_epoch,
                     minimum_release_sequence, now_ms):
    if purpose not in RULES:
        _hold("PURPOSE_NOT_ENROLLED_FOR_THIS_TEST")
    if (type(expected_source_raw) is not bytes
            or not 1 <= len(expected_source_raw) <= 16384
            or type(expected_challenge) is not bytes
            or len(expected_challenge) != 32):
        _hold("EXACT_EXPECTED_SOURCE_AND_CHALLENGE_REQUIRED")
    if (type(signed_proof_raw) is not bytes
            or not 2 <= len(signed_proof_raw) <= MAX_RECORD
            or type(signature) is not bytes or len(signature) != 64):
        _hold("SIGNED_PROOF_FRAME_BOUNDS")
    if (type(expected_host_id) is not str or HOST.fullmatch(expected_host_id) is None):
        _hold("EXPECTED_HOST_ID_REQUIRED")
    floor = (_integer(minimum_release_epoch, positive=True),
             _integer(minimum_release_sequence, positive=True))
    now = _integer(now_ms)
    sha = _issuer_key(
        independently_pinned_signer_key, separately_expected_signer_sha256,
        separately_expected_other_role_key_sha256, revoked_signer_sha256)
    try:
        obj = json.loads(signed_proof_raw.decode("ascii", "strict"),
                         object_pairs_hook=_unique, parse_constant=_nonfinite)
    except (ValueError, UnicodeError, RecursionError, OverflowError) as exc:
        raise ScopedEvidenceHold(
            "C3E_SCOPED_EVIDENCE_HOLD // SIGNED_PROOF_JSON_INVALID"
        ) from exc
    if type(obj) is not dict or set(obj) != FIELDS or _canonical(obj) != signed_proof_raw:
        _hold("PROOF_FIELDS_OR_CANONICAL_BYTES_CHANGED")
    audience, domain = RULES[purpose]
    if (obj["schema"] != SCHEMA or obj["purpose"] != purpose
            or obj["audience"] != audience or obj["hostId"] != expected_host_id
            or obj["sourceSha256"] != _hash(expected_source_raw)
            or obj["challengeSha256"] != _hash(expected_challenge)
            or obj["signerKeySha256"] != sha):
        _hold("CROSS_DOMAIN_OR_ORIGINAL_SOURCE_CHANGED")
    candidate_floor = (_integer(obj["releaseEpoch"], positive=True),
                       _integer(obj["releaseSequence"], positive=True))
    if candidate_floor < floor:
        _hold("RELEASE_FLOOR_DOWNGRADE")
    issued = _integer(obj["issuedMs"])
    expires = _integer(obj["expiresMs"])
    if not issued <= now < expires or not 0 < expires-issued <= MAX_LEASE_MS:
        _hold("EXPIRED_OR_UNBOUNDED_FIXTURE")
    try:
        independently_pinned_signer_key.verify(signature, domain + signed_proof_raw)
    except (InvalidSignature, ValueError) as exc:
        raise ScopedEvidenceHold(
            "C3E_SCOPED_EVIDENCE_HOLD // WRONG_SIGNATURE_OR_PURPOSE_DOMAIN"
        ) from exc
    return {
        "schema": SCHEMA,
        "status": "PURPOSE_SEPARATED_ED25519_FORMAT_VERIFIED_WITH_CALLER_CI_PINS",
        "fixtureProofPurpose": purpose,
        "ciSignerFingerprint": sha,
        "callerPinnedFixtureSignatureVerified": True,
        "testOnlyExpectedSourceDigestMatched": True,
        "testOnlyExpectedChallengeDigestMatched": True,
        "testOnlyExternalRevocationAndFloorInputsConsistent": True,
        "originalMutationOutcome": "UNKNOWN",
        **DENIED,
    }


def inspect_timew_scope_a_ci_only(*, selection, challenge, now_ms, **pins):
    """Validate TimeW's existing Scope A packet then CI proof; no Sway claim."""
    try:
        source = TimeW.make_packet_ci_only(selection=selection,
                                           challenge=challenge, now_ms=now_ms)
    except (TimeW.ObservationHold, TypeError, ValueError) as exc:
        raise ScopedEvidenceHold("C3E_SCOPED_EVIDENCE_HOLD // TIMEW_FIXTURE_REFUSED") from exc
    return _inspect_ci_only(
        purpose=TIMEW_PURPOSE, expected_source_raw=source,
        expected_challenge=challenge, now_ms=now_ms, **pins)


def inspect_hospital_recover_ci_only(
        *, original_prepare_raw, prepared_raw, commit_raw, candidate_query_raw,
        expected_query_id, expected_challenge, now_ms, **pins):
    """Accept only existing Hospital CI query shape, never a writer result."""
    try:
        result = Hospital.inspect_candidate_query_ci_only(
            original_prepare_raw=original_prepare_raw,
            prepared_raw=prepared_raw, commit_raw=commit_raw,
            candidate_query_raw=candidate_query_raw,
            expected_query_id=expected_query_id,
            expected_challenge=expected_challenge, now_ms=now_ms)
    except (Hospital.RecoveryQueryHold, ValueError, TypeError) as exc:
        raise ScopedEvidenceHold("C3E_SCOPED_EVIDENCE_HOLD // HOSPITAL_QUERY_REFUSED") from exc
    if (result["originalCommitOutcome"] != "UNKNOWN"
            or any(result.get(k) is not False for k in Hospital.DENIED)):
        _hold("HOSPITAL_UNKNOWN_OR_DENIAL_BOUNDARY_CHANGED")
    return _inspect_ci_only(
        purpose=HOSPITAL_PURPOSE, expected_source_raw=candidate_query_raw,
        expected_challenge=expected_challenge, now_ms=now_ms, **pins)


def run_native_purpose_proof_verifier(*_args, **_kwargs):
    _hold("INDEPENDENT_ISSUER_AND_C5_NATIVE_ORIGIN_NOT_INSTALLED")
