#!/usr/bin/env python3
"""V2w read-only, separately owned release-floor file contract. DENY-ONLY.

The operator/source owner must independently provide the absolute directory,
expected filesystem UID and pinned Ed25519 public key. Neither values nor
the authority document are taken from a client's capture request.

This code cannot establish that an authority is organizationally legitimate,
that a host has protected key custody, trusted time or monotonic storage.
No file is created/modified; this reader does not grant ArchiveStore access.
"""
import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from scripts.trash.archive_v2_service_release_history import (
    TestServiceReleaseHistory,
)
from scripts.trash.archive_v2_signed_capture import (
    ALLOWED_OWNERS, AUDIENCE, PURPOSE, Ed25519PublicKey,
    InvalidSignature, KEY_ID, SHA,
)

FILE_NAME = "trashpp-v2w-authority-floor.json"
SCHEMA = "post-apollo.trashpp.readonly-authority-floor.v2w"
FIELDS = frozenset((
    "schema", "audience", "purpose", "policyOrigin", "rootKeyId",
    "ownerId", "epoch", "sequence", "releaseSha256", "grantSha256",
    "issuedAtMs", "validFromMs", "validUntilMs", "revoked",
))
ENVELOPE = frozenset(("floor", "signatureB64"))
PIN_FIELDS = frozenset(("rootKeyId", "publicKeyBytes", "origin"))
MAX_BYTES = 4096
MAX_VALID_MS = 24 * 60 * 60 * 1000


class ExternalFloorRefused(Exception):
    """Stable denial code; never a file path, signature or authority bytes."""


def _require(value, code):
    if not value:
        raise ExternalFloorRefused(code)


def _ms(value):
    return type(value) is int and 1 <= value <= 9999999999999


def _object_unique(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "EXTERNAL_FLOOR_DUPLICATE_FIELD")
        result[key] = value
    return result


def canonical_floor(floor):
    _require(type(floor) is dict and set(floor) == FIELDS,
             "EXTERNAL_FLOOR_SCHEMA_INVALID")
    _require(floor["schema"] == SCHEMA
             and floor["audience"] == AUDIENCE
             and floor["purpose"] == PURPOSE
             and floor["policyOrigin"] in (
                 "TEST_FIXTURE_ONLY", "EXTERNAL_OWNER_AUTHORITY"),
             "EXTERNAL_FLOOR_SCOPE_INVALID")
    _require(type(floor["rootKeyId"]) is str
             and KEY_ID.fullmatch(floor["rootKeyId"])
             and type(floor["ownerId"]) is str
             and floor["ownerId"] in ALLOWED_OWNERS
             and type(floor["epoch"]) is int
             and 1 <= floor["epoch"] <= 1000000000
             and type(floor["sequence"]) is int
             and 1 <= floor["sequence"] <= 1000000000
             and type(floor["releaseSha256"]) is str
             and SHA.fullmatch(floor["releaseSha256"])
             and type(floor["grantSha256"]) is str
             and SHA.fullmatch(floor["grantSha256"])
             and type(floor["revoked"]) is bool,
             "EXTERNAL_FLOOR_FIELDS_INVALID")
    _require(all(_ms(floor[k]) for k in (
             "issuedAtMs", "validFromMs", "validUntilMs"))
             and floor["validFromMs"] <= floor["issuedAtMs"]
                 < floor["validUntilMs"]
             and floor["validUntilMs"] - floor["validFromMs"] <= MAX_VALID_MS,
             "EXTERNAL_FLOOR_TIME_INVALID")
    raw = json.dumps(floor, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True, allow_nan=False).encode("ascii")
    _require(len(raw) < MAX_BYTES - 160,
             "EXTERNAL_FLOOR_LIMIT")
    return raw


def _read_owner_file(root, expected_uid):
    """Directory-fd rooted, symlink-free, read-only scan with inode rechecks."""
    _require(isinstance(root, (str, Path)) and type(expected_uid) is int
             and 0 <= expected_uid <= 2**32 - 1,
             "EXTERNAL_FLOOR_ROOT_POLICY_INVALID")
    path = Path(root)
    _require(path.is_absolute() and ".." not in path.parts
             and len(str(path)) <= 4096,
             "EXTERNAL_FLOOR_ROOT_POLICY_INVALID")
    descriptors = []
    try:
        directory = os.open("/", os.O_RDONLY | os.O_DIRECTORY
                            | os.O_CLOEXEC)
        descriptors.append(directory)
        for part in path.parts[1:]:
            _require(part not in (".", "..", "") and "/" not in part,
                     "EXTERNAL_FLOOR_ROOT_UNSAFE")
            directory = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
                | getattr(os, "O_NOFOLLOW", 0), dir_fd=directory)
            descriptors.append(directory)
        root_info = os.fstat(directory)
        _require(stat.S_ISDIR(root_info.st_mode)
                 and root_info.st_uid == expected_uid
                 and (root_info.st_mode & 0o022) == 0,
                 "EXTERNAL_FLOOR_ROOT_UNSAFE")
        fd = os.open(FILE_NAME, os.O_RDONLY | os.O_CLOEXEC
                     | getattr(os, "O_NOFOLLOW", 0)
                     | getattr(os, "O_NONBLOCK", 0), dir_fd=directory)
        descriptors.append(fd)
        before = os.fstat(fd)
        _require(stat.S_ISREG(before.st_mode)
                 and before.st_uid == expected_uid
                 and before.st_nlink == 1
                 and (before.st_mode & 0o022) == 0
                 and 0 < before.st_size <= MAX_BYTES,
                 "EXTERNAL_FLOOR_FILE_UNSAFE")
        data = bytearray()
        while len(data) <= MAX_BYTES:
            part = os.read(fd, min(4096, MAX_BYTES + 1 - len(data)))
            if not part:
                break
            data.extend(part)
        _require(0 < len(data) <= MAX_BYTES,
                 "EXTERNAL_FLOOR_FILE_LIMIT")
        after = os.fstat(fd)
        listed = os.stat(FILE_NAME, dir_fd=directory,
                         follow_symlinks=False)
        root_after = os.fstat(directory)
        _require(
            (before.st_dev, before.st_ino, before.st_mtime_ns,
             before.st_ctime_ns, before.st_size, before.st_mode)
            == (after.st_dev, after.st_ino, after.st_mtime_ns,
                after.st_ctime_ns, after.st_size, after.st_mode)
            and (before.st_dev, before.st_ino)
                == (listed.st_dev, listed.st_ino)
            and stat.S_ISREG(listed.st_mode)
            and (root_info.st_dev, root_info.st_ino)
                == (root_after.st_dev, root_after.st_ino),
            "EXTERNAL_FLOOR_FILE_CHANGED")
        return bytes(data), (
            root_info.st_dev, root_info.st_ino,
            before.st_dev, before.st_ino,
        )
    except ExternalFloorRefused:
        raise
    except (OSError, UnicodeError) as exc:
        raise ExternalFloorRefused("EXTERNAL_FLOOR_UNAVAILABLE") from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


class ReadOnlyExternalFloor:
    """Pins an independently configured authority file for one test capture.

    The fixture permits a same-UID test owner, but never promotes it to a
    production authority. A real off-UID protected directory can be
    *observed* only after an operator/source-owner provisions it.
    """

    def __init__(self, root, expected_uid, pinned_key, *,
                 test_fixture_only=False):
        _require(type(test_fixture_only) is bool
                 and type(pinned_key) is dict
                 and set(pinned_key) == PIN_FIELDS
                 and pinned_key["origin"] in (
                     "EXTERNALLY_PINNED_TEST_ROOT",
                     "EXTERNALLY_PINNED_SOURCE_ROOT")
                 and type(pinned_key["rootKeyId"]) is str
                 and KEY_ID.fullmatch(pinned_key["rootKeyId"])
                 and type(pinned_key["publicKeyBytes"]) is bytes
                 and len(pinned_key["publicKeyBytes"]) == 32,
                 "EXTERNAL_FLOOR_KEY_UNPROVISIONED")
        if test_fixture_only:
            _require(pinned_key["origin"] == "EXTERNALLY_PINNED_TEST_ROOT"
                     and expected_uid == os.geteuid(),
                     "EXTERNAL_FLOOR_FIXTURE_INVALID")
        else:
            _require(pinned_key["origin"] == "EXTERNALLY_PINNED_SOURCE_ROOT"
                     and expected_uid != os.geteuid(),
                     "EXTERNAL_FLOOR_OWNER_NOT_INDEPENDENT")
        self._root = root
        self._expected_uid = expected_uid
        self._pinned = pinned_key.copy()
        self._fixture = test_fixture_only
        self._raw, self._inode = _read_owner_file(root, expected_uid)
        self._fields, self._hash = self._verify(self._raw)

    def _verify(self, raw):
        try:
            envelope = json.loads(
                raw.decode("ascii"), object_pairs_hook=_object_unique)
        except ExternalFloorRefused:
            raise
        except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
            raise ExternalFloorRefused("EXTERNAL_FLOOR_JSON_INVALID") from exc
        _require(type(envelope) is dict and set(envelope) == ENVELOPE,
                 "EXTERNAL_FLOOR_ENVELOPE_INVALID")
        floor = envelope["floor"]
        canonical = canonical_floor(floor)
        try:
            wire = json.dumps(envelope, sort_keys=True,
                              ensure_ascii=True, allow_nan=False,
                              separators=(",", ":")).encode("ascii")
        except (ValueError, TypeError) as exc:
            raise ExternalFloorRefused("EXTERNAL_FLOOR_JSON_INVALID") from exc
        _require(raw == wire, "EXTERNAL_FLOOR_NONCANONICAL")
        _require(floor["rootKeyId"] == self._pinned["rootKeyId"],
                 "EXTERNAL_FLOOR_KEY_MISMATCH")
        _require(floor["policyOrigin"] == (
                 "TEST_FIXTURE_ONLY" if self._fixture
                 else "EXTERNAL_OWNER_AUTHORITY"),
                 "EXTERNAL_FLOOR_SCOPE_INVALID")
        encoded = envelope["signatureB64"]
        _require(type(encoded) is str and len(encoded) == 88,
                 "EXTERNAL_FLOOR_SIGNATURE_INVALID")
        try:
            signature = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ExternalFloorRefused(
                "EXTERNAL_FLOOR_SIGNATURE_INVALID") from exc
        _require(len(signature) == 64
                 and base64.b64encode(signature).decode("ascii")
                     == encoded,
                 "EXTERNAL_FLOOR_SIGNATURE_INVALID")
        _require(Ed25519PublicKey is not None,
                 "EXTERNAL_FLOOR_CRYPTO_UNAVAILABLE")
        try:
            Ed25519PublicKey.from_public_bytes(
                self._pinned["publicKeyBytes"]).verify(signature, canonical)
        except (InvalidSignature, ValueError) as exc:
            raise ExternalFloorRefused(
                "EXTERNAL_FLOOR_SIGNATURE_REFUSED") from exc
        return floor, hashlib.sha256(canonical).hexdigest()

    def require_current(self, *, history, signed_release, release_root,
                        owner_id, grant_sha256, now_ms):
        """Fail if observed external file changed or local signed head differs.

        This remains a *read-only observation*; no protected monotonic writer
        or authenticated time service exists inside this module.
        """
        _require(type(history) is TestServiceReleaseHistory,
                 "EXTERNAL_FLOOR_HISTORY_REQUIRED")
        _require(type(release_root) is dict
                 and type(release_root.get("publicKeyBytes")) is bytes
                 and self._pinned["publicKeyBytes"]
                     != release_root["publicKeyBytes"],
                 "EXTERNAL_FLOOR_ROOT_NOT_DISTINCT")
        raw, inode = _read_owner_file(
            self._root, self._expected_uid)
        _require(inode == self._inode and raw == self._raw,
                 "EXTERNAL_FLOOR_CHANGED")
        floor, digest = self._verify(raw)
        _require(digest == self._hash,
                 "EXTERNAL_FLOOR_CHANGED")
        _require(_ms(now_ms) and floor["validFromMs"] <= now_ms
                 < floor["validUntilMs"]
                 and floor["issuedAtMs"] <= now_ms + 30000,
                 "EXTERNAL_FLOOR_EXPIRED")
        _require(type(owner_id) is str and owner_id in ALLOWED_OWNERS
                 and floor["ownerId"] == owner_id
                 and floor["grantSha256"] == grant_sha256,
                 "EXTERNAL_FLOOR_BINDING_MISMATCH")
        _require(floor["revoked"] is False,
                 "EXTERNAL_FLOOR_REVOKED")
        try:
            release = history.require_current(
                signed_release, release_root, owner_id=owner_id,
                grant_sha256=grant_sha256, now_ms=now_ms)
        except Exception:
            # The caller should not infer an external approval when the
            # local test history is corrupt, revoked, stale, or missing.
            raise ExternalFloorRefused("EXTERNAL_FLOOR_RELEASE_REFUSED")
        _require(floor["sequence"] == release["sequence"]
                 and floor["releaseSha256"] == release["releaseSha256"],
                 "EXTERNAL_FLOOR_STALE_OR_CHANGED")
        return {
            "state":"TEST_EXTERNAL_FLOOR_MATCHED_DENY_ONLY"
                    if self._fixture
                    else "OFF_UID_FLOOR_OBSERVED_DENY_ONLY",
            "ownerId":owner_id,
            "epoch":floor["epoch"],"sequence":floor["sequence"],
            "externalFloorSha256":digest,
            "releaseSha256":release["releaseSha256"],
            "signatureVerified":True,
            "offUidFileObserved":not self._fixture,
            "externallyProtectedMonotonicAuthorityVerified":False,
            "trustedClockVerified":False,
            "sourceAuthorityVerified":False,
            "captureAllowed":False,
            "productionAllowed":False,
            "restoreAllowed":False,
            "burnAllowed":False,
        }
