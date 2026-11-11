#!/usr/bin/env python3
"""MACHINE // sealed Brave snapshot file vault, disconnected source-only V1.

Accepts an opaque externally AES-256-GCM-sealed envelope, never a URL or key.
The host is NOT a registered Brave native host and cannot restore anything.
All CLI mutations require an explicit call; repository tests use isolated
XDG_DATA_HOME paths. Filesystem permissions are NOT encryption.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

RECORD_KIND = "machine-brave-sealed-vault-record-v1"
ENVELOPE_KIND = "machine-brave-sealed-session-v1"
REQUEST_KIND = "machine-brave-sealed-vault-put-v1"
AAD = ENVELOPE_KIND
MAX_REQUEST = 196608
MAX_RECORD = 196608
MAX_CIPHERTEXT = 131072
MAX_RECORDS = 32
ID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z")
DIGEST_RE = re.compile(r"[0-9a-f]{64}\Z")
B64_RE = re.compile(r"[A-Za-z0-9_-]+\Z")

class VaultError(ValueError):
    pass

def reject():
    raise VaultError("SEALED VAULT REFUSED")

def strict_object_pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            reject()
        result[key] = value
    return result

def strict_json(data):
    try:
        value = json.loads(data, object_pairs_hook=strict_object_pairs)
    except (ValueError, UnicodeError, TypeError) as exc:
        raise VaultError("SEALED VAULT REFUSED") from exc
    return value

def exact_keys(value, names):
    if type(value) is not dict or set(value) != set(names):
        reject()

def decode_b64(value, lower, upper):
    if not isinstance(value, str) or not B64_RE.fullmatch(value):
        reject()
    try:
        raw = base64.b64decode(value + "=" * (-len(value) % 4),
                               altchars=b"-_", validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise VaultError("SEALED VAULT REFUSED") from exc
    if not lower <= len(raw) <= upper or (
        base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=") != value
    ):
        reject()
    return raw

def validate_envelope(source):
    """Structural envelope check only. No AES-GCM authentication without key."""
    exact_keys(source, ("kind", "version", "algorithm", "kdf",
                        "iterations", "salt", "nonce", "aad", "ciphertext"))
    if (source["kind"] != ENVELOPE_KIND or
        type(source["version"]) is not int or source["version"] != 1 or
        source["algorithm"] != "AES-256-GCM" or
        source["kdf"] != "PBKDF2-HMAC-SHA256" or
        type(source["iterations"]) is not int or
        not 600000 <= source["iterations"] <= 2000000 or
        source["aad"] != AAD):
        reject()
    decode_b64(source["salt"], 16, 16)
    decode_b64(source["nonce"], 12, 12)
    decode_b64(source["ciphertext"], 16, MAX_CIPHERTEXT)
    return dict(source)

def _home():
    data = os.environ.get("XDG_DATA_HOME")
    base = Path(data) if data is not None else Path.home() / ".local" / "share"
    if not base.is_absolute() or base.is_symlink():
        reject()
    info = base.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid():
        reject()
    return base

def _private_directory(path, create):
    if path.is_symlink():
        reject()
    try:
        if create:
            path.mkdir(mode=0o700)
    except FileExistsError:
        pass
    except OSError as exc:
        raise VaultError("SEALED VAULT REFUSED") from exc
    try:
        info = path.lstat()
    except OSError as exc:
        raise VaultError("SEALED VAULT REFUSED") from exc
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or
        stat.S_IMODE(info.st_mode) & 0o077):
        reject()

def vault_root(*, create):
    base = _home()
    path = base
    for component in ("post-apollo", "machine", "brave-sealed-vault"):
        path = path / component
        if not create and not path.exists() and not path.is_symlink():
            return None
        _private_directory(path, create)
    return path

def _dir_fd(path):
    return os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) |
                   getattr(os, "O_NOFOLLOW", 0))

def _safe_open_file(rootfd, name):
    fd = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
                 dir_fd=rootfd)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or
            info.st_uid != os.geteuid() or info.st_nlink != 1 or
            stat.S_IMODE(info.st_mode) != 0o600 or
            not 0 < info.st_size <= MAX_RECORD):
            reject()
        raw = b""
        while len(raw) <= MAX_RECORD:
            block = os.read(fd, min(16384, MAX_RECORD + 1 - len(raw)))
            if not block:
                break
            raw += block
        if len(raw) > MAX_RECORD:
            reject()
        return raw
    finally:
        os.close(fd)

def _record(raw, expected_id):
    value = strict_json(raw)
    exact_keys(value, ("kind", "record_id", "created_at_utc", "envelope"))
    if value["kind"] != RECORD_KIND or value["record_id"] != expected_id:
        reject()
    try:
        stamp = dt.datetime.fromisoformat(value["created_at_utc"])
    except (ValueError, TypeError, AttributeError):
        reject()
    if stamp.utcoffset() != dt.timedelta(0):
        reject()
    validate_envelope(value["envelope"])
    return value

def _id(value):
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        reject()
    return value

def _files(root):
    names = []
    orphan = False
    with os.scandir(root) as entries:
        for item in entries:
            if item.name.startswith(".tmp-"):
                # A crash before the atomic link can leave an orphan.
                # Report it, never silently delete it or treat as a snapshot.
                orphan = True
                continue
            if not item.name.endswith(".json"):
                reject()
            key = item.name[:-5]
            _id(key)
            if item.is_symlink() or not item.is_file(follow_symlinks=False):
                reject()
            names.append(key)
            if len(names) > MAX_RECORDS:
                reject()
    return sorted(names), orphan

def _digest(raw):
    return hashlib.sha256(raw).hexdigest()

def listing():
    root = vault_root(create=False)
    if root is None:
        return {"status": "listed", "records": [], "orphan_temp_present": False,
                "restore_allowed": False, "safe_actions": []}
    names, orphan = _files(root)
    records = []
    dfd = _dir_fd(root)
    try:
        for name in names:
            raw = _safe_open_file(dfd, name + ".json")
            record = _record(raw, name)
            records.append({
                "record_id": name, "created_at_utc": record["created_at_utc"],
                "sealed_bytes": len(raw), "sha256": _digest(raw)
            })
    finally:
        os.close(dfd)
    return {"status": "listed", "records": records,
            "orphan_temp_present": orphan,
            "ciphertext_authentication_verified": False,
            "restore_allowed": False, "safe_actions": []}

def read(record_id):
    record_id = _id(record_id)
    root = vault_root(create=False)
    if root is None:
        reject()
    dfd = _dir_fd(root)
    try:
        raw = _safe_open_file(dfd, record_id + ".json")
    finally:
        os.close(dfd)
    record = _record(raw, record_id)
    return {"status": "sealed_record_read", "record": record,
            "sha256": _digest(raw),
            "ciphertext_authentication_verified": False,
            "restore_allowed": False, "safe_actions": []}

def put(request):
    exact_keys(request, ("kind", "operator_save_requested", "envelope"))
    if request["kind"] != REQUEST_KIND or request["operator_save_requested"] is not True:
        reject()
    envelope = validate_envelope(request["envelope"])
    # Payload validation precedes any directory creation.
    root = vault_root(create=True)
    names, orphan = _files(root)
    if len(names) >= MAX_RECORDS or orphan:
        reject()
    key = str(uuid.uuid4())
    record = {"kind": RECORD_KIND, "record_id": key,
              "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "envelope": envelope}
    raw = (json.dumps(record, sort_keys=True,
                     separators=(",", ":"), ensure_ascii=True) + "\n").encode()
    if len(raw) > MAX_RECORD:
        reject()
    temp = ".tmp-" + str(uuid.uuid4())
    dest = key + ".json"
    dfd = _dir_fd(root)
    created = False
    linked = False
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(temp, flags, 0o600, dir_fd=dfd)
        created = True
        try:
            with os.fdopen(fd, "wb") as writer:
                writer.write(raw)
                writer.flush()
                os.fsync(writer.fileno())
        except BaseException:
            raise
        # Link is atomic and refuses replacement if target already exists.
        os.link(temp, dest, src_dir_fd=dfd, dst_dir_fd=dfd,
                follow_symlinks=False)
        linked = True
        os.unlink(temp, dir_fd=dfd)
        created = False
        os.fsync(dfd)
    except BaseException:
        if linked:
            os.unlink(dest, dir_fd=dfd)
        if created:
            os.unlink(temp, dir_fd=dfd)
        os.fsync(dfd)
        raise
    finally:
        os.close(dfd)
    return {"status": "sealed_record_saved", "record_id": key,
            "sha256": _digest(raw), "ciphertext_authentication_verified": False,
            "restore_allowed": False, "safe_actions": []}

def delete(record_id, expected_sha256):
    record_id = _id(record_id)
    if not isinstance(expected_sha256, str) or not DIGEST_RE.fullmatch(expected_sha256):
        reject()
    root = vault_root(create=False)
    if root is None:
        reject()
    dfd = _dir_fd(root)
    try:
        raw = _safe_open_file(dfd, record_id + ".json")
        _record(raw, record_id)
        if _digest(raw) != expected_sha256:
            reject()
        # Optimistic stale-digest guard; not a same-UID adversary lock.
        os.unlink(record_id + ".json", dir_fd=dfd)
        os.fsync(dfd)
    finally:
        os.close(dfd)
    return {"status": "sealed_record_deleted", "record_id": record_id,
            "restore_allowed": False, "safe_actions": []}

def _stdin_request():
    data = sys.stdin.buffer.readline(MAX_REQUEST + 1)
    if (not data or len(data) > MAX_REQUEST or not data.endswith(b"\n")
            or sys.stdin.buffer.read(1)):
        reject()
    return strict_json(data)

def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if args == ["list"]:
            result = listing()
        elif args == ["put"]:
            result = put(_stdin_request())
        elif len(args) == 2 and args[0] == "read":
            result = read(args[1])
        elif len(args) == 3 and args[0] == "delete":
            result = delete(args[1], args[2])
        else:
            reject()
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except (VaultError, ValueError, TypeError, OSError, OverflowError):
        # Never print request, ciphertext, passwords or environment paths.
        print('{"status":"refused","restore_allowed":false,"safe_actions":[]}')
        return 1

if __name__ == "__main__":
    sys.exit(main())
