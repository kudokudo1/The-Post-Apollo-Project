"""P35 // Dormant encrypted Personal contact metadata vault.

A key is supplied IN MEMORY by a separately authorized trusted host. This
module does not create, retrieve, unlock, export, back up, or persist keys,
does not expose CLI/DBus/QML actions, and cannot decide user consent. Caller
MUST independently verify current contacts.read permission, live device
profile and explicit edit intent. No production host is wired to this code.

The only on-disk contact data is AES-256-GCM ciphertext and random nonce,
under a new 0700 directory and 0600 files. Notes/favorites/identity match
proofs are NEVER serialized to plaintext. Filename and encryption keys are
domain-separated from the P34 HMAC matching key.
"""
from __future__ import annotations

import base64
from contextlib import contextmanager
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import stat
from typing import Iterator

import PhonePersonalContactIdentity as Identity

SCHEMA = "post-apollo.phone.personal-contact-sealed.v1"
VERSION = 1
MAX_FILE = Identity.MAX_DOCUMENT * 2 + 4096
MAX_CIPHERTEXT = Identity.MAX_DOCUMENT + 4096
ROOT_NAME = "contact-vault-v1"
LOCK_NAME = ".vault.lock"
FILE_PREFIX = "contact-"
B64 = re.compile(r"^[A-Za-z0-9_-]+$")


class VaultRefused(Exception):
    """Fixed, content-free error; never exposes notes, paths or keys."""


def _refuse() -> None:
    raise VaultRefused("PERSONAL_CONTACT_VAULT_REFUSED")


def _require_key(master_key: bytes) -> None:
    if type(master_key) is not bytes or len(master_key) != 32:
        _refuse()


def _require_profile(profile: str) -> None:
    if type(profile) is not str or not Identity.PROFILE.fullmatch(profile):
        _refuse()


def _derive(master_key: bytes, purpose: bytes) -> bytes:
    _require_key(master_key)
    return hmac.new(master_key, b"post-apollo:phone:personal:v1:" + purpose,
                    hashlib.sha256).digest()


def contact_matching_key(master_key: bytes) -> bytes:
    """Feed this distinct subkey to the existing P34 matching policy.

    Not a contact ID or a grant. The authorized host must not release it to UI.
    """
    return _derive(master_key, b"match")


def _filename(master_key: bytes, profile: str) -> str:
    _require_profile(profile)
    digest = hmac.new(_derive(master_key, b"filename"),
                      profile.encode("ascii"), hashlib.sha256).hexdigest()
    return FILE_PREFIX + digest + ".sealed"


def _aad(profile: str) -> bytes:
    _require_profile(profile)
    # Identity context is authenticated but is not stored as plaintext.
    return (SCHEMA + ":" + str(VERSION) + ":" + profile).encode("ascii")


def _urlsafe(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unbase64(value: object, size_min: int, size_max: int) -> bytes:
    if type(value) is not str or not B64.fullmatch(value):
        _refuse()
    try:
        data = base64.b64decode(value + "=" * (-len(value) % 4),
                                altchars=b"-_", validate=True)
    except (ValueError, base64.binascii.Error):
        _refuse()
    if not size_min <= len(data) <= size_max or _urlsafe(data) != value:
        _refuse()
    return data


def _strict_pairs(items: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for k, v in items:
        if k in result:
            _refuse()
        result[k] = v
    return result


def _parse(raw: bytes) -> dict[str, object]:
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_FILE:
        _refuse()
    try:
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_pairs)
    except (ValueError, TypeError, UnicodeError):
        _refuse()
    if (type(document) is not dict or set(document) !=
            {"schema", "version", "algorithm", "nonce", "ciphertext"}
            or document["schema"] != SCHEMA
            or type(document["version"]) is not int or document["version"] != VERSION
            or document["algorithm"] != "AES-256-GCM"):
        _refuse()
    return document


def _cryptography():
    # Optional dependency is required for an explicit caller to use the vault.
    # Missing dependency fails closed. Never replace AES-GCM with XOR/plaintext.
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.exceptions import InvalidTag
    except ImportError:
        _refuse()
    return AESGCM, InvalidTag


def seal(master_key: bytes, profile: str, document: object) -> bytes:
    """Encrypt an exact P34 document. No filesystem effects."""
    _require_key(master_key)
    _require_profile(profile)
    if not Identity.valid_document(document):
        _refuse()
    if any(entry["profileId"] != profile for entry in document["entries"]):
        _refuse()
    plaintext = json.dumps(document, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":")).encode("utf-8")
    if len(plaintext) > Identity.MAX_DOCUMENT:
        _refuse()
    AESGCM, _ = _cryptography()
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(_derive(master_key, b"aes-gcm")).encrypt(
        nonce, plaintext, _aad(profile))
    envelope = {
        "schema": SCHEMA, "version": VERSION, "algorithm": "AES-256-GCM",
        "nonce": _urlsafe(nonce), "ciphertext": _urlsafe(ciphertext)
    }
    sealed = (json.dumps(envelope, sort_keys=True, separators=(",", ":"))
              + "\n").encode("ascii")
    if len(sealed) > MAX_FILE:
        _refuse()
    return sealed


def unseal(master_key: bytes, profile: str, sealed: bytes) -> dict[str, object]:
    """Authenticate first. Never fall back to a plaintext JSON document."""
    _require_key(master_key)
    _require_profile(profile)
    envelope = _parse(sealed)
    nonce = _unbase64(envelope["nonce"], 12, 12)
    ciphertext = _unbase64(envelope["ciphertext"], 16, MAX_CIPHERTEXT)
    AESGCM, InvalidTag = _cryptography()
    try:
        plaintext = AESGCM(_derive(master_key, b"aes-gcm")).decrypt(
            nonce, ciphertext, _aad(profile))
        if len(plaintext) > Identity.MAX_DOCUMENT:
            _refuse()
        document = json.loads(plaintext.decode("utf-8"),
                              object_pairs_hook=_strict_pairs)
    except (InvalidTag, ValueError, UnicodeError, TypeError):
        _refuse()
    if (not Identity.valid_document(document)
            or any(row["profileId"] != profile for row in document["entries"])):
        _refuse()
    return document


def _root(path: Path, *, create: bool) -> Path | None:
    """A caller-selected, private directory, never an implicit HOME path."""
    if not isinstance(path, Path) or not path.is_absolute() or path.name != ROOT_NAME:
        _refuse()
    parent = path.parent
    try:
        if parent.is_symlink():
            _refuse()
        info = parent.stat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) & 0o022):
            _refuse()
        if not create and not path.exists() and not path.is_symlink():
            return None
        if create:
            try:
                path.mkdir(mode=0o700)
            except FileExistsError:
                pass
        actual = path.lstat()
    except OSError:
        _refuse()
    if (not stat.S_ISDIR(actual.st_mode) or actual.st_uid != os.geteuid()
            or stat.S_IMODE(actual.st_mode) != 0o700):
        _refuse()
    return path


def _dirfd(root: Path) -> int:
    try:
        fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY |
                     getattr(os, "O_NOFOLLOW", 0))
        info = os.fstat(fd)
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o700):
            os.close(fd)
            _refuse()
        return fd
    except OSError:
        _refuse()


def _read_file(dfd: int, name: str) -> bytes | None:
    try:
        fd = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
                     dir_fd=dfd)
    except FileNotFoundError:
        return None
    except OSError:
        _refuse()
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600
                or not 0 < info.st_size <= MAX_FILE):
            _refuse()
        chunks = []
        remaining = MAX_FILE + 1
        while remaining:
            data = os.read(fd, min(16384, remaining))
            if not data:
                break
            remaining -= len(data)
            chunks.append(data)
        raw = b"".join(chunks)
        if not raw or len(raw) > MAX_FILE:
            _refuse()
        return raw
    except OSError:
        _refuse()
    finally:
        os.close(fd)


def _require_single_profile_file(dfd: int, expected: str) -> None:
    """One encrypted phone profile per trusted-host-selected directory.

    A wrong/lost key has a different opaque filename. Never silently report
    EMPTY and create a second vault alongside previously sealed user notes.
    Unexpected files or leftover temp writes demand explicit manual recovery.
    """
    try:
        names = os.listdir(dfd)
    except OSError:
        _refuse()
    for name in names:
        if name != expected and name != LOCK_NAME:
            _refuse()


@contextmanager
def _write_lock(dfd: int) -> Iterator[None]:
    """Cooperating same-UID writers serialize CAS under a private inode."""
    try:
        fd = os.open(LOCK_NAME, os.O_RDWR | os.O_CREAT |
                     getattr(os, "O_NOFOLLOW", 0), 0o600, dir_fd=dfd)
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600):
            os.close(fd)
            _refuse()
        fcntl.flock(fd, fcntl.LOCK_EX)
    except OSError:
        _refuse()
    try:
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def read(master_key: bytes, profile: str, root: Path) -> dict[str, object]:
    """Read after a *separate trusted-host consent check*. No directory write."""
    _require_key(master_key)
    _require_profile(profile)
    safe_root = _root(root, create=False)
    if safe_root is None:
        return Identity.empty_document()
    dfd = _dirfd(safe_root)
    try:
        name = _filename(master_key, profile)
        _require_single_profile_file(dfd, name)
        raw = _read_file(dfd, name)
    finally:
        os.close(dfd)
    return (Identity.empty_document() if raw is None
            else unseal(master_key, profile, raw))


def _publish(dfd: int, name: str, payload: bytes) -> None:
    temporary = ".tmp-" + secrets.token_hex(16)
    written = False
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                     getattr(os, "O_NOFOLLOW", 0), 0o600, dir_fd=dfd)
        written = True
        with os.fdopen(fd, "wb") as out:
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())
        # We have already checked the previous file under the write lock.
        # No pre-existing file is ever edited in place or written in cleartext.
        os.replace(temporary, name, src_dir_fd=dfd, dst_dir_fd=dfd)
        written = False
        os.fsync(dfd)
    except OSError:
        _refuse()
    finally:
        if written:
            try:
                os.unlink(temporary, dir_fd=dfd)
            except OSError:
                pass


def commit(master_key: bytes, profile: str, root: Path,
           document: object, *, expected_revision: int) -> dict[str, object]:
    """Explicit durable write of a previously user-approved P34 update.

    The caller MUST check current consent/device, approve the edit, and retain
    the master key in a trusted Secret Service or other approved provider.
    No public host/CLI is provided. CAS conflicts fail closed; no last-wins.
    """
    _require_key(master_key)
    _require_profile(profile)
    if (type(expected_revision) is not int or expected_revision < 0
            or not Identity.valid_document(document)
            or document["revision"] != expected_revision + 1
            or any(row["profileId"] != profile for row in document["entries"])):
        _refuse()
    payload = seal(master_key, profile, document)
    safe_root = _root(root, create=True)
    if safe_root is None:
        _refuse()
    dfd = _dirfd(safe_root)
    try:
        with _write_lock(dfd):
            name = _filename(master_key, profile)
            _require_single_profile_file(dfd, name)
            current_raw = _read_file(dfd, name)
            current = (Identity.empty_document() if current_raw is None
                       else unseal(master_key, profile, current_raw))
            if current["revision"] != expected_revision:
                _refuse()
            _publish(dfd, name, payload)
    finally:
        os.close(dfd)
    return {"ok": True, "status": "SEALED", "revision": document["revision"]}


def erase(master_key: bytes, profile: str, root: Path, *,
          expected_revision: int, user_confirmed: bool) -> dict[str, object]:
    """Explicit whole-profile local deletion. Never modifies iPhone contacts."""
    _require_key(master_key)
    _require_profile(profile)
    if user_confirmed is not True or type(expected_revision) is not int:
        _refuse()
    safe_root = _root(root, create=False)
    if safe_root is None:
        _refuse()
    dfd = _dirfd(safe_root)
    try:
        with _write_lock(dfd):
            name = _filename(master_key, profile)
            _require_single_profile_file(dfd, name)
            raw = _read_file(dfd, name)
            if raw is None or unseal(master_key, profile, raw)["revision"] != expected_revision:
                _refuse()
            os.unlink(name, dir_fd=dfd)
            os.fsync(dfd)
    except OSError:
        _refuse()
    finally:
        os.close(dfd)
    return {"ok": True, "status": "ERASED"}


# No main(), keyring unlock, environment-key fallback, or command-line bridge.
