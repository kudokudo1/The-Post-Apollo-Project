"""P50 PHONE // Strict Ed25519 release/source preflight for the CI-only status host.

This verifies *cryptographic consistency* of canonical release bytes and
measured on-disk P47/P48/P49/P50 Python modules + inert P49 systemd unit.
All public keys and floors are supplied by the caller, NOT independently
enrolled. Even a valid signature and matching live files confer NO installed
host identity, C3e challenge, C5 human consent, keyring authority or SAVE.

The production release root, signed RPM/OSTree provenance, SELinux/logind
seat, external rollback floor and supervised systemd MainPID have not been
supplied by their owning services. This module never guesses them.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any

SCHEMA = "post-apollo.phone.personal-status-release.p50.ci.v1"
ROLE = "post-apollo.phone.personal-status-host.ci-only"
AUDIENCE = "post-apollo.phone.source-consistency-review.ci-only"
PURPOSE = "personal.status-only.ci-no-private-access"
DOMAIN = b"post-apollo.phone.p50.status-release-ci\x00"
SOURCE_NAMES = (
    "PhonePersonalStatusHostP49.py",
    "PhonePersonalHostSocketP47.py",
    "PhonePersonalPeerEvidenceP48.py",
    "PhonePersonalInstalledReleaseP50.py",
)
UNIT_FILE = "systemd/post-apollo-phone-personal-status-ci.service"
NAMES = frozenset((*SOURCE_NAMES, UNIT_FILE))
FIELDS = frozenset((
    "schema", "role", "audience", "purpose", "releaseEpoch",
    "releaseSequence", "unit", "files",
))
HEX64 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
UNIT_NAME = "post-apollo-phone-personal-status-ci.service"
MAX_FRAME = 4096
MAX_MODULE = 128 * 1024
MAX_UNIT = 16 * 1024
MAX_I = 2**53 - 1

RESULT = {
    "status": "SIGNED_CI_SOURCE_MATCH_NOT_HOST_ATTESTED",
    "productionEnabled": False,
    "installedHostVerified": False,
    "c3eChallengeConsumed": False,
    "c5HumanConsentVerified": False,
    "keyReleaseAuthorized": False,
    "personalSaveAuthorized": False,
    "retryAuthorized": False,
}


class OriginRefused(Exception):
    """No release, keys, process data, contact or provider error escapes."""


def _deny() -> None:
    raise OriginRefused("PHONE_STATUS_ORIGIN_REFUSED")


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            _deny()
        out[key] = value
    return out


def canonical(obj: dict[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii")


def _int(value: object) -> bool:
    return type(value) is int and 1 <= value <= MAX_I


def _hash_regular(path: Path, size_limit: int) -> str:
    """No symlinks, writable/shareable inodes, or missing file admitted.

    This is a POSIX source-integrity check, NOT trusted package provenance.
    A same-UID attacker can replace code and sign with their own caller key.
    """
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                 | getattr(os, "O_CLOEXEC", 0))
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or info.st_uid not in (0, os.geteuid())
                or stat.S_IMODE(info.st_mode) & 0o022
                or not 0 < info.st_size <= size_limit):
            _deny()
        digest = hashlib.sha256()
        total = 0
        while total <= size_limit:
            part = os.read(fd, min(65536, size_limit + 1 - total))
            if not part:
                break
            digest.update(part)
            total += len(part)
        if total != info.st_size or total > size_limit:
            _deny()
        return digest.hexdigest()
    finally:
        os.close(fd)


def _measured(bundle: Path) -> dict[str, str]:
    if (not isinstance(bundle, Path) or not bundle.is_absolute()
            or bundle.resolve(strict=True) != bundle
            or bundle.is_symlink()):
        _deny()
    basedir = bundle.lstat()
    if (not stat.S_ISDIR(basedir.st_mode)
            or stat.S_IMODE(basedir.st_mode) & 0o022
            or basedir.st_uid not in (0, os.geteuid())):
        _deny()
    unit_folder = bundle / "systemd"
    mode = unit_folder.lstat()
    if (not stat.S_ISDIR(mode.st_mode) or unit_folder.is_symlink()
            or stat.S_IMODE(mode.st_mode) & 0o022
            or mode.st_uid not in (0, os.geteuid())):
        _deny()
    return {
        name: _hash_regular(bundle / name, MAX_UNIT if name == UNIT_FILE
                            else MAX_MODULE)
        for name in sorted(NAMES)
    }


def verify_candidate(
    *, manifest: object, signature: object, root_public: object,
    bundle: object, minimum_epoch: object, minimum_sequence: object,
) -> dict[str, object]:
    """Check detached signed bytes and measured files. NEVER grant authority.

    The signer and floor must later be independently enrolled/held by a
    genuinely authenticated owner. Supplying one's own Ed25519 public key
    and matching manifest is NOT proof of that provenance.
    """
    try:
        if (type(manifest) is not bytes or not 2 <= len(manifest) <= MAX_FRAME
                or type(signature) is not bytes or len(signature) != 64
                or type(root_public) is not bytes or len(root_public) != 32
                or not _int(minimum_epoch) or not _int(minimum_sequence)):
            _deny()
        doc = json.loads(
            manifest.decode("ascii"), object_pairs_hook=_no_duplicates,
            parse_constant=lambda _: _deny(),
        )
        if (type(doc) is not dict or set(doc) != FIELDS
                or canonical(doc) != manifest
                or doc["schema"] != SCHEMA
                or doc["role"] != ROLE
                or doc["audience"] != AUDIENCE
                or doc["purpose"] != PURPOSE
                or doc["unit"] != UNIT_NAME
                or not _int(doc["releaseEpoch"])
                or not _int(doc["releaseSequence"])
                or doc["releaseEpoch"] < minimum_epoch
                or doc["releaseSequence"] < minimum_sequence
                or type(doc["files"]) is not dict
                or set(doc["files"]) != NAMES
                or any(type(v) is not str or HEX64.fullmatch(v) is None
                       for v in doc["files"].values())):
            _deny()
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey,
        )
        Ed25519PublicKey.from_public_bytes(root_public).verify(
            signature, DOMAIN + manifest
        )
        if _measured(bundle) != doc["files"]:
            _deny()
        # Caller-supplied signing root and on-disk files can both be forged.
        # Do not return any "hostAuthenticated" or equivalent success flag.
        return dict(RESULT)
    except OriginRefused:
        raise
    except Exception:
        _deny()


def _read_small_regular(path: Path, maximum: int) -> bytes:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                 | getattr(os, "O_CLOEXEC", 0))
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_uid not in (0, os.geteuid())
                or stat.S_IMODE(info.st_mode) & 0o022
                or not 0 < info.st_size <= maximum):
            _deny()
        data = os.read(fd, maximum + 1)
        if len(data) != info.st_size:
            _deny()
        return data
    finally:
        os.close(fd)


def verify_candidate_from_paths(
    *, bundle: object, manifest_path: object,
    signature_path: object, root_path: object,
    minimum_epoch: object = 1, minimum_sequence: object = 1,
) -> dict[str, object]:
    """Explicit host-private test preflight. Paths are untrusted caller input."""
    try:
        paths = (manifest_path, signature_path, root_path)
        if any(not isinstance(p, Path) or not p.is_absolute() for p in paths):
            _deny()
        return verify_candidate(
            manifest=_read_small_regular(manifest_path, MAX_FRAME),
            signature=_read_small_regular(signature_path, 64),
            root_public=_read_small_regular(root_path, 32),
            bundle=bundle,
            minimum_epoch=minimum_epoch,
            minimum_sequence=minimum_sequence,
        )
    except OriginRefused:
        raise
    except Exception:
        _deny()


# No C4b Identity signer admission, independently enrolled release root,
# C3e issuer, C5 human gesture, host package authority, key or SAVE action.
