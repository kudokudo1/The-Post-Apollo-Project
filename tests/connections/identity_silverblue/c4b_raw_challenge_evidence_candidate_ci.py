#!/usr/bin/env python3
"""DOC 2: raw challenge → exact installed-gateway denial nonce compatibility.

This is a disposable CI adapter of the ORIGINAL C4b signed-denial verifier.
It does not claim who issued the raw challenge, whether it was spent, or
whether release/process/seat/host custody is independently authenticated.
No service, enrollment, signer, SQLite, remote transport, credential or
production admission is created.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_controller_challenge_ci as C4B

SCHEMA = "postapollo.identity.c4b-raw-challenge-evidence-candidate.ci-v1"
STATUS = "C4B_RAW_CHALLENGE_SIGNED_DENIAL_DIAGNOSTIC_NOT_TRUSTED_HOST"
DIGEST = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
DENIED = {
    **C4B.NEGATIVE,
    "independentChallengeIssuerVerified": False,
    "independentlyCurrentHistoryVerified": False,
    "independentReceiptKeyEnrollmentVerified": False,
    "authenticatedBootAndUnlockedSeatVerified": False,
    "protectedTerminalOutcomeVerified": False,
    "actualHostOriginAuthenticated": False,
}

class Refused(ValueError):
    """Invalid nonce, receipt or attempted evidence-authority promotion."""

def _deny(reason):
    raise Refused(reason)

def encode_raw_challenge_ci_only(raw_challenge: bytes) -> str:
    """Make the original 43-character C4b nonce from exactly 32 raw bytes.

    This encoding is NOT custodian challenge issuance, anti-replay state,
    evidence of challenge ownership, or a future on-the-wire protocol.
    """
    if type(raw_challenge) is not bytes or len(raw_challenge) != 32:
        _deny("C4B_RAW_CHALLENGE_EXACT_32_BYTES_REQUIRED")
    value = base64.urlsafe_b64encode(raw_challenge).rstrip(b"=").decode("ascii")
    if len(value) != 43:
        _deny("C4B_RAW_CHALLENGE_NONCE_ENCODING_REFUSED")
    return value

def inspect_raw_challenge_denial_ci_only(*, raw_challenge: bytes, serial: bytes):
    """Verify the original signed BEGIN/UNAVAILABLE denial, remain HOLD."""
    nonce = encode_raw_challenge_ci_only(raw_challenge)
    try:
        proof = C4B.inspect_ci_only(serial=serial, controller_challenge=nonce)
    except C4B.Refused as exc:
        raise Refused("C4B_RAW_CHALLENGE_ORIGINAL_DENIAL_REFUSED") from exc
    keys = {
        "schema", "freshControllerNonceInActualSignedBeginDenialInCI",
        "publicKeyVerifiedOnlyForThisCIReceipt", "controllerChallengeSha256",
        "receiptFrameSha256", "runtimePublicKeySha256", *C4B.NEGATIVE,
    }
    if type(proof) is not dict or set(proof) != keys:
        _deny("C4B_RAW_CHALLENGE_PROOF_FIELDS_REFUSED")
    if (proof["schema"] != C4B.SCHEMA
            or proof["freshControllerNonceInActualSignedBeginDenialInCI"] is not True
            or proof["publicKeyVerifiedOnlyForThisCIReceipt"] is not True
            or any(proof[key] is not False for key in C4B.NEGATIVE)):
        _deny("C4B_RAW_CHALLENGE_PROOF_AUTHORITY_REFUSED")
    for key in ("controllerChallengeSha256", "receiptFrameSha256",
                "runtimePublicKeySha256"):
        if type(proof[key]) is not str or DIGEST.fullmatch(proof[key]) is None:
            _deny("C4B_RAW_CHALLENGE_PROOF_DIGEST_REFUSED")
    encoded_digest = hashlib.sha256(nonce.encode("ascii")).hexdigest()
    if not hmac.compare_digest(proof["controllerChallengeSha256"], encoded_digest):
        _deny("C4B_RAW_CHALLENGE_PROOF_NONCE_DIGEST_MISMATCH")
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "rawChallengeSha256": hashlib.sha256(raw_challenge).hexdigest(),
        "encodedCommandNonceSha256": encoded_digest,
        "receiptFrameSha256": proof["receiptFrameSha256"],
        "runtimePublicKeySha256": proof["runtimePublicKeySha256"],
        "ciOnlyOriginalSignedDenialVerified": True,
        **DENIED,
    }
