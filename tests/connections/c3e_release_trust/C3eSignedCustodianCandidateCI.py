#!/usr/bin/env python3
"""DOC 1: synthetic signed custodian replies never become protected settlement.

All data, including the expected public key, is supplied by a disposable
GitHub CI test. Correct Ed25519 bytes prove possession of that TEST key only.
No real independent enrollment, immutable current head, protected challenge
or authenticated native host exists. No network, key issuance, SQLite write,
production service, grant, terminal receipt or automatic retry.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sys
from types import MappingProxyType

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

REQUEST_SCHEMA = "postapollo.connections.c3e-custodian-query-candidate-ci-v1"
RESPONSE_SCHEMA = "postapollo.connections.c3e-custodian-denial-candidate-ci-v1"
REPORT_SCHEMA = "postapollo.connections.c3e-custodian-signed-candidate-observation-ci-v1"
PURPOSE = "postapollo.connections.identity-custodian-ci-only"
ROLE = "UNENROLLED_HISTORY_TEST_SIGNER"
STATUS = "SIGNED_TEST_CANDIDATE_NOT_INDEPENDENT_CUSTODY"
HEX32 = re.compile(r"[0-9a-f]{32}\Z", re.ASCII)
HEX64 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
BASE64_64 = re.compile(r"[A-Za-z0-9_-]{86}\Z", re.ASCII)
QUERY_FIELDS = frozenset({
    "schema", "purpose", "requestId", "challengeHex",
    "epoch", "previousHeadSha256", "previousSequence",
})
RESPONSE_FIELDS = frozenset({
    *QUERY_FIELDS, "signerRole", "kind", "settlement", "challengeState",
    "observedHeadSha256", "observedSequence", "signatureB64url",
})
DENIED = MappingProxyType({
    "operatorEnrolledHistoryRootVerified": False,
    "independentCurrentHistoryVerified": False,
    "independentChallengeIssuedVerified": False,
    "independentChallengeSpentVerified": False,
    "authenticatedRemoteTransportVerified": False,
    "nativeGatewayHostReleaseSeatVerified": False,
    "protectedTerminalReceiptVerified": False,
    "identityC5ConsentVerified": False,
    "safeToRetry": False,
    "productionSignInAllowed": False,
})


class Refused(ValueError):
    """Malformed, forged, cross-purpose or prohibited settlement candidate."""


def _deny(code):
    raise Refused(code)


def _ci():
    if (sys.platform != "linux" or os.geteuid() != 0
            or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
        _deny("C3E_CUSTODIAN_CANDIDATE_DISPOSABLE_ROOT_CI_ONLY")


def _exact(doc, keys, code):
    if (type(doc) is not dict or len(doc) != len(keys)
            or any(type(key) is not str for key in doc)
            or set(doc) != keys):
        _deny(code)


def _hex(v, pattern):
    return type(v) is str and pattern.fullmatch(v) is not None


def _counter(value):
    return type(value) is int and 1 <= value <= 2**63-1


def _canonical(body):
    return json.dumps(body, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _query(request):
    _exact(request, QUERY_FIELDS, "C3E_CUSTODIAN_QUERY_FIELDS_REFUSED")
    if (type(request["schema"]) is not str
            or type(request["purpose"]) is not str
            or request["schema"] != REQUEST_SCHEMA
            or request["purpose"] != PURPOSE
            or not _hex(request["requestId"], HEX32)
            or not _hex(request["challengeHex"], HEX64)
            or not _hex(request["epoch"], HEX32)
            or not _hex(request["previousHeadSha256"], HEX64)
            or not _counter(request["previousSequence"])):
        _deny("C3E_CUSTODIAN_QUERY_DOMAIN_OR_COUNTER_REFUSED")


def _candidate(request, response):
    _exact(response, RESPONSE_FIELDS, "C3E_CUSTODIAN_RESPONSE_FIELDS_REFUSED")
    for key in QUERY_FIELDS - {"schema"}:
        if type(response[key]) is not type(request[key]) or response[key] != request[key]:
            _deny("C3E_CUSTODIAN_RESPONSE_REQUEST_BINDING_REFUSED")
    if (any(type(response[key]) is not str for key in
            ("schema", "signerRole", "kind", "settlement", "challengeState"))
            or response["schema"] != RESPONSE_SCHEMA
            or response["signerRole"] != ROLE
            or response["kind"] != "UNAVAILABLE"
            or response["settlement"] != "NONE"
            or response["challengeState"] != "UNKNOWN"
            or not _hex(response["observedHeadSha256"], HEX64)
            or not _counter(response["observedSequence"])):
        _deny("C3E_CUSTODIAN_RESPONSE_NOT_DENIAL_ONLY")
    signature = response["signatureB64url"]
    if type(signature) is not str or BASE64_64.fullmatch(signature) is None:
        _deny("C3E_CUSTODIAN_SIGNATURE_CANONICAL_BASE64URL_REQUIRED")
    malformed = False
    try:
        sig = base64.urlsafe_b64decode(signature + "==")
    except (ValueError, base64.binascii.Error):
        malformed = True
    if malformed:
        _deny("C3E_CUSTODIAN_SIGNATURE_MALFORMED")
    if len(sig) != 64 or base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=") != signature:
        _deny("C3E_CUSTODIAN_SIGNATURE_NONCANONICAL")
    return sig


def _relation(request, response):
    old, new = request["previousSequence"], response["observedSequence"]
    if new < old:
        return "SIGNED_TEST_RESPONSE_STALE_HEAD_HOLD"
    if new > old:
        return "SIGNED_TEST_RESPONSE_AHEAD_UNVERIFIED_HOLD"
    if response["observedHeadSha256"] != request["previousHeadSha256"]:
        return "SIGNED_TEST_RESPONSE_EQUAL_SEQUENCE_FORK_HOLD"
    return "SIGNED_TEST_RESPONSE_EQUAL_NOT_TRUSTED_HOLD"


def _verified(request, response, test_public_key):
    _query(request)
    signature = _candidate(request, response)
    if type(test_public_key) is not bytes or len(test_public_key) != 32:
        _deny("C3E_CUSTODIAN_EXACT_TEST_PUBLIC_KEY_REQUIRED")
    body = {k:v for k,v in response.items() if k != "signatureB64url"}
    signed = b"POSTAPOLLO_C3E_CUSTODIAN_CANDIDATE_CI_V1\x00" + _canonical(body)
    invalid_signature = False
    try:
        Ed25519PublicKey.from_public_bytes(test_public_key).verify(signature, signed)
    except (InvalidSignature, ValueError):
        invalid_signature = True
    if invalid_signature:
        _deny("C3E_CUSTODIAN_BAD_TEST_SIGNATURE")
    return body


def inspect_ci_only(*, request, response, test_public_key):
    """Cryptographic TEST signature correctness, NEVER a protected grant."""
    _ci()
    body = _verified(request, response, test_public_key)
    return {
        "schema": REPORT_SCHEMA,
        "status": STATUS,
        "relation": _relation(request, response),
        "testCandidateDigestSha256": hashlib.sha256(_canonical(body)).hexdigest(),
        "testPublicKeySha256": hashlib.sha256(test_public_key).hexdigest(),
        "cryptographicTestSignatureValid": True,
        "next": "HOLD_NO_INDEPENDENT_CUSTODIAN_OR_TERMINAL_SETTLEMENT",
        "winner": None,
        "safeActions": [],
        **DENIED,
    }


def compare_signed_candidates_ci_only(*, request, left, right, test_public_key):
    """Two valid local signatures do NOT prove unique globally current history."""
    _ci()
    l = _verified(request, left, test_public_key)
    r = _verified(request, right, test_public_key)
    if l["observedSequence"] != r["observedSequence"]:
        relation = "SIGNED_TEST_CANDIDATES_DIFFERENT_SEQUENCE_HOLD"
    elif l["observedHeadSha256"] != r["observedHeadSha256"]:
        relation = "SIGNED_TEST_CANDIDATES_SAME_SEQUENCE_FORK_HOLD"
    else:
        relation = "SIGNED_TEST_CANDIDATES_MATCH_STILL_NOT_QUORUM_HOLD"
    return {
        "schema": REPORT_SCHEMA,
        "status": STATUS,
        "relation": relation,
        "leftTestCandidateDigestSha256": hashlib.sha256(_canonical(l)).hexdigest(),
        "rightTestCandidateDigestSha256": hashlib.sha256(_canonical(r)).hexdigest(),
        "testPublicKeySha256": hashlib.sha256(test_public_key).hexdigest(),
        "cryptographicTestSignaturesValid": True,
        "next": "HOLD_NO_INDEPENDENT_CUSTODIAN_OR_TERMINAL_SETTLEMENT",
        "winner": None,
        "safeActions": [],
        **DENIED,
    }


def protected_admission(*_args, **_kwargs):
    _deny("C3E_CUSTODIAN_CANDIDATE_NO_OPERATOR_ENROLLED_ROOT_OR_SIGNIN")
