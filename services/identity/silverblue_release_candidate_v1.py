"""Identity-side reader for C4b #1785 synthetic release envelope (CI only).

This checks an *externally supplied* signed release and independent source/RPM
pins. It never performs OS installed-host attestation, issues login permission,
constructs a native command client, or authenticates operator consent.
C4b owns the RPM/host lifecycle, C3e owns independent security review and C5
owns one-use human authorization. Production admission is not implemented.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from collections.abc import Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

SCHEMA = "postapollo.identity.c4b.silverblue.synthetic-release.ci-v1"
ROLE = "postapollo.identity.native-command-gateway.deny-only-ci"
DOMAIN = b"postapollo.identity.c4b.silverblue.synthetic-release.ci-v1\x00"
PACKAGE = "post-apollo-identity-silverblue-ci"
UNIT = "post-apollo-identity-silverblue-ci.service"
UNIT_PATH = "/usr/lib/systemd/system/" + UNIT
PREFIX = "/usr/libexec/post-apollo/identity/"
FILES = frozenset(PREFIX + name for name in (
    "identity-gateway-ci", "desktop_command_gateway_v0.py",
    "desktop_host_lifecycle_v0.py", "desktop_context_projection_v0.py",
    "desktop_session_host_v0.py", "native_loopback_callback_v0.py",
    "private_context_ipc_v0.py", "signed_command_receipt_v0.py",
)) | {UNIT_PATH}
KEYS = frozenset(("schema", "role", "package", "epoch", "sequence",
                  "rpmSha256", "receiptKeySha256", "unit", "files"))
HEX = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)


class CandidateRefused(ValueError):
    """A release envelope or its independently supplied pins did not agree."""


@dataclass(frozen=True, slots=True)
class SilverblueReleaseCandidateV1:
    """Metadata-only CI candidate. Every authority value is deliberately false."""
    epoch: int
    sequence: int
    package_sha256: str
    receipt_key_sha256: str
    installed_guest_measured: bool = False
    host_authenticated: bool = False
    production_authority: bool = False
    can_begin_sign_in: bool = False
    credential_actions_enabled: bool = False


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CandidateRefused("Duplicate signed field")
        result[key] = value
    return result


def _canonical(document):
    return json.dumps(document, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def assess_synthetic_release(
    *, signed_release: bytes, signature: bytes,
    independently_pinned_root: Ed25519PublicKey,
    independently_pinned_receipt_key: bytes,
    independently_measured_rpm_sha256: str,
    independently_measured_files: Mapping[str, str],
    minimum_epoch: int, minimum_sequence: int,
) -> SilverblueReleaseCandidateV1:
    """Check #1785 envelope syntax and independent *test* pins; never admit host.

    The independent inputs MUST NOT be sourced from the gateway, its socket,
    QML or the candidate envelope itself. Even a valid result does not prove
    a Silverblue installed process, OSTree rollback, SELinux, seat or consent.
    """
    if (type(signed_release) is not bytes
            or not 1 <= len(signed_release) <= 4096
            or type(signature) is not bytes or len(signature) != 64
            or not isinstance(independently_pinned_root, Ed25519PublicKey)
            or type(independently_pinned_receipt_key) is not bytes
            or len(independently_pinned_receipt_key) != 32
            or type(minimum_epoch) is not int or minimum_epoch < 1
            or type(minimum_sequence) is not int or minimum_sequence < 1
            or type(independently_measured_rpm_sha256) is not str
            or HEX.fullmatch(independently_measured_rpm_sha256) is None
            or not isinstance(independently_measured_files, Mapping)
            or set(independently_measured_files) != FILES
            or any(type(v) is not str or HEX.fullmatch(v) is None
                   for v in independently_measured_files.values())):
        raise CandidateRefused("Independent test pins missing or malformed")

    try:
        document = json.loads(signed_release.decode("utf-8"),
                              object_pairs_hook=_unique)
        if (type(document) is not dict or set(document) != KEYS
                or _canonical(document) != signed_release):
            raise CandidateRefused("Noncanonical or partial C4b envelope")
    except (ValueError, UnicodeError, TypeError, OverflowError,
            RecursionError) as exc:
        raise CandidateRefused("Malformed signed C4b envelope") from exc

    if (document["schema"] != SCHEMA or document["role"] != ROLE
            or document["package"] != PACKAGE or document["unit"] != UNIT
            or type(document["epoch"]) is not int
            or document["epoch"] < minimum_epoch
            or type(document["sequence"]) is not int
            or document["sequence"] < minimum_sequence
            or type(document["rpmSha256"]) is not str
            or HEX.fullmatch(document["rpmSha256"]) is None
            or type(document["receiptKeySha256"]) is not str
            or HEX.fullmatch(document["receiptKeySha256"]) is None
            or type(document["files"]) is not dict
            or set(document["files"]) != FILES
            or any(type(v) is not str or HEX.fullmatch(v) is None
                   for v in document["files"].values())):
        raise CandidateRefused("Unexpected Identity release role, file roster or floor")

    try:
        independently_pinned_root.verify(signature, DOMAIN + signed_release)
    except (InvalidSignature, ValueError) as exc:
        raise CandidateRefused("Independent release-root signature refused") from exc

    if (document["rpmSha256"] != independently_measured_rpm_sha256
            or document["receiptKeySha256"] !=
            hashlib.sha256(independently_pinned_receipt_key).hexdigest()
            or document["files"] != dict(independently_measured_files)):
        raise CandidateRefused("Release/package/module/receipt pins disagree")

    return SilverblueReleaseCandidateV1(
        epoch=document["epoch"], sequence=document["sequence"],
        package_sha256=document["rpmSha256"],
        receipt_key_sha256=document["receiptKeySha256"],
    )
