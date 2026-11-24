#!/usr/bin/env python3
"""DOC 1: Forest installed candidate public HOLD is NOT enrolled C3e authority.

This CI-only decoder cannot read a private DB, sign or spend a challenge,
authenticate the installed process, or grant Forest title/list permission.
All real native observations are owned by the disposable B5c test harness.
There is deliberately no positive custodian/consent/terminal outcome path.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

SCHEMA = "postapollo.connections.c3e-forest-installed-candidate-hold.ci-v1"
SOURCE_SCHEMA = "post-apollo.forest.b5b-ci-only"
STATUS = "INSTALLED_FOREST_TEST_HOST_PUBLIC_HOLD_NOT_CUSTODIAN"
MAX_FRAME = 1024
SHA256_HEX = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
PUBLIC_FIELDS = frozenset({
    "schema", "status", "sourceAuthenticated", "recipientAuthenticated",
    "permissionGranted", "productionAuthority", "privateBytesSubmitted",
    "revocationFencedAck", "safeActions",
})
AUTHORITY_FALSE = {
    "installedForestHostOperatorApproved": False,
    "independentForestEnrollmentRootVerified": False,
    "currentForestHistoryAndRevocationVerified": False,
    "originalProcessSeatRecipientAuthenticated": False,
    "privateForestDatabaseCustodyVerified": False,
    "protectedOneUseChallengeSpent": False,
    "forestListSessionsAllowed": False,
    "forestPrivateTitleDisclosureAllowed": False,
    "forestProvisionalEgressAllowed": False,
    "protectedTerminalOutcomeVerified": False,
    "productionSignInAllowed": False,
    "safeToRetry": False,
}


class Refused(ValueError):
    """Malformed/nonpublic data or a forged native authority claim."""


class UnknownHold(RuntimeError):
    """No terminal reply from an untrusted installed test candidate."""


def _deny(code):
    raise Refused(code)


def _ci_only():
    if (sys.platform != "linux" or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
        _deny("C3E_FOREST_INSTALLED_CANDIDATE_GITHUB_HOSTED_CI_ONLY")


def _unique_pairs(pairs):
    doc = {}
    for key, value in pairs:
        if key in doc:
            _deny("C3E_FOREST_INSTALLED_DUPLICATE_JSON_KEY_REFUSED")
        doc[key] = value
    return doc


def _constant(_value):
    _deny("C3E_FOREST_INSTALLED_NONFINITE_JSON_REFUSED")


def inspect_public_hold_ci_only(packet: bytes, *,
                                controller_expected_source_sha256: str):
    """Validate exact public bytes and return immutable false authority.

    The SHA is provided by the CI controller, not protected enrollment. Even
    correct package/file correspondence does NOT authenticate Forest custody.
    """
    _ci_only()
    if (type(controller_expected_source_sha256) is not str
            or SHA256_HEX.fullmatch(controller_expected_source_sha256) is None):
        _deny("C3E_FOREST_INSTALLED_CONTROLLER_TEST_DIGEST_REQUIRED")
    if type(packet) is not bytes:
        _deny("C3E_FOREST_INSTALLED_PACKET_BYTES_REQUIRED")
    if not packet:
        raise UnknownHold("C3E_FOREST_INSTALLED_NO_ACK_UNKNOWN_HOLD_NO_RETRY")
    if len(packet) > MAX_FRAME:
        _deny("C3E_FOREST_INSTALLED_OVERSIZE_PACKET_REFUSED")
    try:
        reply = json.loads(packet.decode("utf-8"),
                           object_pairs_hook=_unique_pairs,
                           parse_constant=_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise Refused("C3E_FOREST_INSTALLED_INVALID_UTF8_JSON_REFUSED") from exc
    if type(reply) is not dict or set(reply) != PUBLIC_FIELDS:
        _deny("C3E_FOREST_INSTALLED_UNEXPECTED_FIELDS_OR_PRIVATE_BYTES")
    if (reply["schema"] != SOURCE_SCHEMA or reply["status"] != "UNKNOWN_HOLD"
            or type(reply["privateBytesSubmitted"]) is not int
            or reply["privateBytesSubmitted"] != 0
            or type(reply["safeActions"]) is not list
            or reply["safeActions"] != []
            or any(reply[k] is not False for k in (
                "sourceAuthenticated", "recipientAuthenticated",
                "permissionGranted", "productionAuthority",
                "revocationFencedAck",
            ))):
        _deny("C3E_FOREST_INSTALLED_ANY_AUTHORITY_CLAIM_REFUSED")

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "publicPacketSha256": hashlib.sha256(packet).hexdigest(),
        "controllerTestSourceSha256": controller_expected_source_sha256,
        "packageDigestIsOperatorEnrollment": False,
        "originalStatus": "UNKNOWN_HOLD",
        "next": "HOLD_NO_INDEPENDENT_FOREST_CUSTODIAN_OR_PRIVATE_DATA",
        "safeActions": [],
        "winner": None,
        **AUTHORITY_FALSE,
    }


def protected_forest_admission(*_args, **_kwargs):
    _deny("C3E_FOREST_INSTALLED_TEST_HOST_NOT_PROTECTED_OR_ENROLLED")
