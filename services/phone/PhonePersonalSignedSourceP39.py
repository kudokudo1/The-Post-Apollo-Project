"""P39 PHONE deny-only verification of actual C4b/C3e-Y signed CI source frames.

Unlike P38's untrusted summary-field intake, this validates *signed bytes*
for the exact source release and signed host statement, and binds those bytes
to the signed P37 contact-save fixture. All keys, measured files and claimed
kernel snapshot remain *caller supplied* synthetic CI inputs. This module
does not verify the four individual C3e-X denial signatures, independently
attest any installed process, consume an externally issued challenge or
accept real C5 consent. Even perfect matching NEVER authorizes a vault write.

Production PHONE MUST NOT invoke this module as an authentication service.
There is no D-Bus, CLI, keyring, provider, vault or live host integration.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import PhonePersonalSignedTrustP37 as P37

C4B_SCHEMA = "postapollo.identity.c4b.silverblue.synthetic-release.ci-v1"
C4B_ROLE = "postapollo.identity.native-command-gateway.deny-only-ci"
C4B_DOMAIN = (C4B_SCHEMA + "\x00").encode("ascii")
C4B_PACKAGE = "post-apollo-identity-silverblue-ci"
C4B_UNIT = "post-apollo-identity-silverblue-ci.service"
PREFIX = "/usr/libexec/post-apollo/identity/"
C4B_FILES = frozenset(
    PREFIX + name for name in (
        "identity-gateway-ci",
        "desktop_command_gateway_v0.py",
        "desktop_host_lifecycle_v0.py",
        "desktop_context_projection_v0.py",
        "desktop_session_host_v0.py",
        "native_loopback_callback_v0.py",
        "private_context_ipc_v0.py",
        "signed_command_receipt_v0.py",
    )
) | {"/usr/lib/systemd/system/" + C4B_UNIT}
C4B_FIELDS = frozenset({
    "schema", "role", "package", "unit", "epoch", "sequence",
    "rpmSha256", "receiptKeySha256", "files",
})

C3EY_SCHEMA = "postapollo.connections.c3ey-signed-full-identity-evidence.ci-v1"
C3EY_ROLE = C4B_ROLE
C3EY_PURPOSE = "postapollo.identity.c3ey-deny-only-full-record.ci"
C3EY_AUDIENCE = "postapollo.connections.c3ey-disposable-root-issuer.ci"
C3EY_DOMAIN = (C3EY_SCHEMA + "\x00").encode("ascii")
C3EY_FIELDS = frozenset({
    "schema", "role", "purpose", "audience", "releaseEpoch",
    "releaseSequence", "challengeSha256", "evidenceSha256",
    "receiptSha256", "snapshotSha256", "receiptKeySha256",
})
C3EX_SCHEMA = "postapollo.connections.c3ex-identity-runtime-denial.ci-v1"
C3EX_FIELDS = frozenset({"schema", "role", "records"})
SNAPSHOT_FIELDS = frozenset({
    "rpmSha256", "entrypointSha256", "exeSha256", "exePath",
    "unit", "pid", "startTicks", "uid", "gid", "cgroup",
    "selinux", "socketPath",
})

HEX = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
REFUSED = {
    "status": "NO_AUTHENTICATED_INSTALLED_HOST_OR_C5",
    "productionEnabled": False,
    "installedHostVerified": False,
    "humanConsentVerified": False,
    "vaultWriteEnabled": False,
    "keyReleaseEnabled": False,
    "externalChallengeConsumed": False,
}
MATCHED = {
    **REFUSED,
    "status": "SIGNED_CI_SOURCE_BYTES_BOUND_NOT_AUTHENTICATED",
}


class SourceRefused(Exception):
    """Internal, content-free; never reveal names, keys, digests or notes."""


def _deny() -> None:
    raise SourceRefused("P39_CI_SOURCE_REFUSED")


def _int(v: object) -> bool:
    return type(v) is int and 0 < v < 2**53 - 1


def _hex(v: object) -> bool:
    return type(v) is str and HEX.fullmatch(v) is not None


def _canonical(obj: object) -> bytes:
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _no_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            _deny()
        out[key] = value
    return out


def _frame(raw: object, fields: frozenset[str], *,
           line: bool = False, max_bytes: int = 4096) -> dict[str, Any]:
    if type(raw) is not bytes or not 2 <= len(raw) <= max_bytes:
        _deny()
    try:
        if line and (not raw.endswith(b"\n") or raw.count(b"\n") != 1):
            _deny()
        doc = json.loads(
            (raw[:-1] if line else raw).decode("ascii"),
            object_pairs_hook=_no_duplicate,
            parse_constant=lambda _: _deny()
        )
        if (type(doc) is not dict or set(doc) != fields
                or raw != _canonical(doc) + (b"\n" if line else b"")):
            _deny()
        return doc
    except (UnicodeError, ValueError, TypeError, RecursionError,
            OverflowError):
        _deny()


def _verify(public: bytes, signature: bytes, domain: bytes, raw: bytes) -> None:
    if type(public) is not bytes or len(public) != 32 \
            or type(signature) is not bytes or len(signature) != 64:
        _deny()
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        Ed25519PublicKey.from_public_bytes(public).verify(signature, domain + raw)
    except (ImportError, InvalidSignature, ValueError, TypeError):
        _deny()


def _release(raw: bytes, signature: bytes, release_root: bytes,
             receipt_key: bytes, measured_files: object, rpm: object,
             expected: dict) -> dict[str, Any]:
    doc = _frame(raw, C4B_FIELDS)
    if (doc["schema"] != C4B_SCHEMA or doc["role"] != C4B_ROLE
            or doc["package"] != C4B_PACKAGE or doc["unit"] != C4B_UNIT
            or not _int(doc["epoch"]) or not _int(doc["sequence"])
            or doc["epoch"] != expected["minimumReleaseEpoch"]
            or doc["sequence"] < expected["minimumReleaseSequence"]
            or not _hex(doc["rpmSha256"])
            or not _hex(doc["receiptKeySha256"])
            or type(receipt_key) is not bytes or len(receipt_key) != 32
            or not _hex(rpm) or rpm != doc["rpmSha256"]
            or doc["receiptKeySha256"] != hashlib.sha256(receipt_key).hexdigest()
            or type(measured_files) is not dict
            or set(measured_files) != C4B_FILES
            or any(not _hex(v) for v in measured_files.values())
            or type(doc["files"]) is not dict
            or set(doc["files"]) != C4B_FILES
            or doc["files"] != measured_files):
        _deny()
    _verify(release_root, signature, C4B_DOMAIN, raw)
    return doc


def _statement(raw: bytes, signature: bytes, witness_key: bytes,
               receipt_key: bytes, evidence_line: bytes,
               denial_frames: object, measured: object,
               expected: dict, release: dict) -> dict[str, Any]:
    statement = _frame(raw, C3EY_FIELDS)
    if (type(denial_frames) not in (tuple, list)
            or len(denial_frames) != 4
            or any(type(frame) is not bytes or not 1 <= len(frame) <= 1024
                   for frame in denial_frames)
            or type(measured) is not dict or set(measured) != SNAPSHOT_FIELDS
            or not all(_int(measured[k]) for k in ("pid", "startTicks", "uid", "gid"))
            or not all(_hex(measured[k]) for k in (
                "rpmSha256", "entrypointSha256", "exeSha256"))
            or any(type(measured[k]) is not str for k in (
                "exePath", "unit", "cgroup", "selinux", "socketPath"))
            or measured["rpmSha256"] != release["rpmSha256"]
            or measured["entrypointSha256"] != release["files"][PREFIX + "identity-gateway-ci"]
            or measured["unit"] != C4B_UNIT):
        _deny()
    evidence = _frame(evidence_line, C3EX_FIELDS,
                      line=True, max_bytes=16384)
    if (evidence["schema"] != C3EX_SCHEMA
            or evidence["role"] != C3EY_ROLE
            or type(evidence["records"]) is not list
            or len(evidence["records"]) != 4):
        _deny()
    if (statement["schema"] != C3EY_SCHEMA
            or statement["role"] != C3EY_ROLE
            or statement["purpose"] != C3EY_PURPOSE
            or statement["audience"] != C3EY_AUDIENCE
            or statement["releaseEpoch"] != release["epoch"]
            or statement["releaseSequence"] != release["sequence"]
            or statement["challengeSha256"] != expected["challengeSha256"]
            or statement["receiptKeySha256"] != hashlib.sha256(receipt_key).hexdigest()
            or statement["evidenceSha256"] != hashlib.sha256(evidence_line).hexdigest()
            or statement["snapshotSha256"] != hashlib.sha256(_canonical(measured)).hexdigest()
            or type(statement["receiptSha256"]) is not list
            or statement["receiptSha256"] != [
                hashlib.sha256(frame).hexdigest() for frame in denial_frames
            ]):
        _deny()
    _verify(witness_key, signature, C3EY_DOMAIN, raw)
    return statement


def compare_signed_ci_source(
    *, expected_request: object, p37_host_frame: bytes,
    p37_host_signature: bytes, p37_host_public_key: bytes,
    p37_consent_frame: bytes, p37_consent_signature: bytes,
    p37_consent_public_key: bytes, now: int,
    signed_release: bytes, release_signature: bytes, release_root_key: bytes,
    receipt_public_key: bytes, independently_measured_files: object,
    independently_measured_rpm: object,
    signed_statement: bytes, witness_signature: bytes, witness_public_key: bytes,
    evidence_line: bytes, denial_frames: object,
    independently_measured_snapshot: object, genuine_c5_receipt: object = None,
) -> dict[str, object]:
    """Validate actual CI signed source bytes, NEVER production authority.

    All five public keys, measured files/snapshot and P37 request are supplied
    by the CI caller. C3e-X signed denial frame signatures are NOT verified
    here, nor is an external challenge consumed. No C5 issuer is enrolled.
    """
    try:
        if genuine_c5_receipt is not None or type(expected_request) is not dict:
            _deny()
        keys = (
            p37_host_public_key, p37_consent_public_key,
            release_root_key, witness_public_key, receipt_public_key
        )
        if any(type(k) is not bytes or len(k) != 32 for k in keys) \
                or len(set(keys)) != 5:
            _deny()
        result = P37.compare_signed_fixture_receipts(
            expected_request=expected_request,
            host_frame=p37_host_frame, host_signature=p37_host_signature,
            host_public_key=p37_host_public_key,
            consent_frame=p37_consent_frame,
            consent_signature=p37_consent_signature,
            consent_public_key=p37_consent_public_key, now=now,
        )
        if result != P37.MATCHED_FIXTURE:
            _deny()
        host = P37._signed_frame(p37_host_frame, P37.HOST_FIELDS)
        release = _release(
            signed_release, release_signature, release_root_key,
            receipt_public_key, independently_measured_files,
            independently_measured_rpm, expected_request
        )
        _statement(
            signed_statement, witness_signature, witness_public_key,
            receipt_public_key, evidence_line, denial_frames,
            independently_measured_snapshot, expected_request, release
        )
        if (host["releaseSha256"] != release["rpmSha256"]
                or host["hostEvidenceSha256"] !=
                hashlib.sha256(signed_statement).hexdigest()
                or host["releaseSequence"] != release["sequence"]
                or host["releaseEpoch"] != release["epoch"]):
            _deny()
        return dict(MATCHED)
    except (SourceRefused, P37.ReceiptRefused, KeyError, ValueError,
            TypeError, AttributeError, UnicodeError, OverflowError,
            RecursionError):
        return dict(REFUSED)


# No grant, key release, vault write, C5 issuer, actual host/process
# observation, C3e-X denial signature checks or real challenge consumption.
