#!/usr/bin/env python3
"""C4b: read-only owner-held *fixture* inputs for the signed enrollment gate.

A guest's signed denial cannot establish which signing key, release or host
the controller independently expects. This CI contract requires the controller
harness to choose a private directory outside the guest and to populate it
before reading guest UART. Never treat this directory's Unix owner/mode, or
keys minted in one GitHub runner, as proof of operator authority or
production root custody. All credential/sign-in/production flags stay FALSE.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

import controller_pinned_enrollment_gate_ci as E

SCHEMA = "postapollo.identity.c4b.controller-policy-intake.ci-v1"
AUDIENCE = "protected-connections-c3e-ci-only"
SCOPE = "signed-denial-diagnostic-only"
POLICY_FIELDS = frozenset({
    "schema", "audience", "scope", "hostId", "releaseSha256",
    "rootPublicSha256", "minimumReleaseEpoch", "minimumReleaseSequence",
    "revokedEnrollmentIds",
})
FILES = {
    "root": ("controller-root-public.ed25519", 32),
    "policy": ("controller-policy.json", 4096),
    "enrollment": ("gateway-enrollment.json", E.MAX_ENROLLMENT),
    "signature": ("gateway-enrollment.ed25519", 64),
}
EXACT = {"root", "signature"}
NEGATIVE = {
    "operatorControlledRootEnrollmentVerified": False,
    "independentlyAuthenticatedHostEvidenceVerified": False,
    "protectedRevocationLedgerVerified": False,
    "rollbackResistantSourceVerified": False,
    "operatorC5ConsentVerified": False,
    "hostAuthenticated": False,
    "canBeginSignIn": False,
    "credentialActionsEnabled": False,
    "productionAuthority": False,
}

class Refused(ValueError):
    """A controller-only local CI fixture is unsafe or unverifiable."""

def _deny(reason):
    raise Refused(reason)

def _pairs_unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _deny("C4B_POLICY_DUPLICATE_FIELD_REFUSED")
        result[key] = value
    return result

def _parse_policy(raw):
    if type(raw) is not bytes or len(raw) < 2 or len(raw) > FILES["policy"][1]:
        _deny("C4B_POLICY_SIZE_REFUSED")
    try:
        document = json.loads(
            raw.decode("ascii"), object_pairs_hook=_pairs_unique,
            parse_constant=lambda _: _deny("C4B_POLICY_NONFINITE_FIELD_REFUSED"),
        )
    except (UnicodeError, ValueError, RecursionError, OverflowError, TypeError) as exc:
        raise Refused("C4B_POLICY_JSON_REFUSED") from exc
    if type(document) is not dict or set(document) != POLICY_FIELDS:
        _deny("C4B_POLICY_EXACT_FIELDS_REQUIRED")
    try:
        canonical = json.dumps(
            document, sort_keys=True, ensure_ascii=True, allow_nan=False,
            separators=(",", ":"),
        ).encode("ascii")
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise Refused("C4B_POLICY_CANONICAL_ENCODING_REFUSED") from exc
    if raw != canonical:
        _deny("C4B_POLICY_NONCANONICAL_RECORD_REFUSED")
    if (document["schema"] != SCHEMA or document["audience"] != AUDIENCE
            or document["scope"] != SCOPE
            or type(document["hostId"]) is not str
            or E.HOST.fullmatch(document["hostId"]) is None
            or any(type(document[key]) is not str
                   or E.HEX.fullmatch(document[key]) is None
                   for key in ("rootPublicSha256", "releaseSha256"))
            or any(type(document[key]) is not int
                   or not 0 < document[key] < 2**53
                   for key in ("minimumReleaseEpoch", "minimumReleaseSequence"))
            or type(document["revokedEnrollmentIds"]) is not list):
        _deny("C4B_POLICY_SCOPE_OR_PIN_FORMAT_REFUSED")
    revoked = document["revokedEnrollmentIds"]
    if (len(revoked) > 1024
            or any(type(x) is not str or E.IDENT.fullmatch(x) is None
                   for x in revoked)
            or revoked != sorted(set(revoked))):
        _deny("C4B_POLICY_REVOCATION_LIST_REFUSED")
    return document

def _safe_directory(path: Path):
    # Path is caller-selected by an external controller. This is deliberately
    # not a guest-supplied path; Unix permissions alone are NOT an external
    # protected enrollment authority.
    if (not isinstance(path, Path) or not path.is_absolute()
            or ".." in path.parts or str(path) in ("/", "/tmp", "/var/tmp")):
        _deny("C4B_POLICY_DIRECTORY_SCOPE_REFUSED")
    fd = None
    try:
        # A symlink at the final component is refused. Resolve equality also
        # catches pre-existing symlinks in parent components in this CI
        # snapshot, though not an adversarial parent-path race.
        if path != path.resolve(strict=True):
            _deny("C4B_POLICY_DIRECTORY_SYMLINK_REFUSED")
        fd = os.open(str(path), os.O_RDONLY | os.O_DIRECTORY |
                     os.O_NOFOLLOW | os.O_CLOEXEC)
        st = os.fstat(fd)
        if (not stat.S_ISDIR(st.st_mode) or st.st_uid != os.geteuid()
                or stat.S_IMODE(st.st_mode) != 0o700):
            _deny("C4B_POLICY_DIRECTORY_OWNERSHIP_OR_MODE_REFUSED")
        return fd
    except OSError as exc:
        raise Refused("C4B_POLICY_DIRECTORY_UNAVAILABLE") from exc
    except Exception:
        if fd is not None:
            os.close(fd)
        raise

def _read_regular(parent_fd: int, name: str, ceiling: int, exact: bool) -> bytes:
    if type(name) is not str or name not in (v[0] for v in FILES.values()):
        _deny("C4B_POLICY_FILENAME_NOT_ALLOWLISTED")
    fd = None
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                     dir_fd=parent_fd)
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.geteuid()
                or stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1
                or not 0 < st.st_size <= ceiling
                or (exact and st.st_size != ceiling)):
            _deny("C4B_POLICY_FILE_UNSAFE")
        data = os.read(fd, ceiling + 1)
        after = os.fstat(fd)
        if (len(data) != st.st_size
                or (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns,
                    st.st_ctime_ns, st.st_mode, st.st_nlink)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns,
                    after.st_ctime_ns, after.st_mode, after.st_nlink)):
            _deny("C4B_POLICY_FILE_CHANGED_DURING_READ")
        return data
    except OSError as exc:
        raise Refused("C4B_POLICY_FILE_OPEN_REFUSED") from exc
    finally:
        if fd is not None:
            os.close(fd)

def inspect_controller_owned_ci_only(
    *, controller_dir: Path, serial: bytes, controller_challenge: str,
):
    """Check controller-owned fixture pins BEFORE reading any guest proof.

    This performs no file writes and no key generation. The controller must
    independently establish the authority, origin and currentness of its
    own files; this helper cannot certify those properties.
    """
    directory = _safe_directory(controller_dir)
    try:
        # Each file is opened below a single pinned directory descriptor.
        # A symlinked, world-readable, hardlinked or replaced file is refused.
        raw = {
            key: _read_regular(directory, name, ceiling, key in EXACT)
            for key, (name, ceiling) in FILES.items()
        }
    finally:
        os.close(directory)
    document = _parse_policy(raw["policy"])
    if not hmac.compare_digest(
        hashlib.sha256(raw["root"]).hexdigest(), document["rootPublicSha256"],
    ):
        _deny("C4B_POLICY_CONTROLLER_ROOT_HASH_MISMATCH")
    try:
        root = Ed25519PublicKey.from_public_bytes(raw["root"])
    except ValueError as exc:
        raise Refused("C4B_POLICY_INVALID_CONTROLLER_ROOT") from exc
    try:
        result = E.inspect_enrolled_controller_challenge_ci_only(
            serial=serial, controller_challenge=controller_challenge,
            signed_enrollment=raw["enrollment"],
            enrollment_signature=raw["signature"],
            independently_pinned_controller_root=root,
            independently_pinned_release_sha256=document["releaseSha256"],
            independently_pinned_host_id=document["hostId"],
            minimum_release_epoch=document["minimumReleaseEpoch"],
            minimum_release_sequence=document["minimumReleaseSequence"],
            revoked_enrollment_ids=tuple(document["revokedEnrollmentIds"]),
        )
    except E.Refused as exc:
        raise Refused("C4B_POLICY_ENROLLMENT_OR_SIGNED_DENIAL_REFUSED") from exc
    if (result.get("ciControllerRootSignatureAndSourcePinsMatch") is not True
            or result.get("receiptSignerMatchesControllerSignedEnrollmentInCI") is not True
            or result.get("signedDenialMatchesFreshControllerNonceInCI") is not True
            or any(result.get(flag) is not False for flag in E.NEGATIVE)):
        _deny("C4B_POLICY_PARENT_AUTHORITY_PROMOTION_REFUSED")
    return {
        "schema": SCHEMA,
        "localControllerFixturePinsConsumedInCI": True,
        "enrolledReceiptKeyMatchesSignedFreshDenialInCI": True,
        "policySha256": hashlib.sha256(raw["policy"]).hexdigest(),
        "enrollmentSha256": hashlib.sha256(raw["enrollment"]).hexdigest(),
        "receiptKeySha256": result["receiptKeySha256"],
        "hostId": result["hostId"],
        # These values came from the verified C4b controller-signed
        # enrollment, not unverified guest-provided version fields.
        "releaseEpoch": result["releaseEpoch"],
        "releaseSequence": result["releaseSequence"],
        "releaseSha256": result["releaseSha256"],
        "controllerRootSha256": hashlib.sha256(raw["root"]).hexdigest(),
        **E.NEGATIVE, **NEGATIVE,
    }
