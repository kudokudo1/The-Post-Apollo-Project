#!/usr/bin/env python3
"""Local, private Social identity contact details and account *labels*.

This is deliberately NOT an authentication store. No credentials, cookies,
session files, API keys, bearer tokens or provider login states belong here.

Quickshell sends explicit edits over stdin, never command-line arguments.
The file is owner-only (0700 directory, 0600 file), written atomically.
Unsupported/corrupt/unsafe files are refused rather than overwritten.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from typing import Any

# Reuse the existing Social provider catalog, rather than creating a second
# source of truth or relying on unstable numeric selector indices.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "messaging"))
from SocialAccountCatalog import ITEM_BY_ID  # noqa: E402

SCHEMA = "post-apollo.social-identity-account-details.v1"
FILE_NAME = "identity-account-details-v1.json"
MAX_BYTES = 65536
MAX_REQUEST_BYTES = 4096
MAX_IDENTITIES = 12
IDENTITY_ID = re.compile(r"^identity-[1-9][0-9]{0,8}$")
CONTROL = re.compile(r"[\x00-\x1f\x7f]")
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}$")
PHONE = re.compile(r"^\+?[0-9() .-]{5,24}$")


class StoreError(Exception):
    """Public error codes only. Never include local document contents."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def root_path() -> Path:
    base = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local/share"))
    return base / "post-apollo" / "social"


def storage_path() -> Path:
    return root_path() / FILE_NAME


def new_document() -> dict[str, Any]:
    return {"schema": SCHEMA, "revision": 0, "identities": {}}


def require_identity(value: Any) -> str:
    if not isinstance(value, str) or not IDENTITY_ID.fullmatch(value):
        raise StoreError("INVALID_IDENTITY")
    return value


def require_string(value: Any, limit: int) -> str:
    if not isinstance(value, str) or len(value) > limit or CONTROL.search(value):
        raise StoreError("INVALID_FIELD")
    return value.strip()


def validate_contact(email: Any, phone: Any) -> tuple[str, str]:
    e = require_string(email, 254)
    p = require_string(phone, 24)
    if e and (not EMAIL.fullmatch(e) or e.count("@") != 1):
        raise StoreError("INVALID_EMAIL")
    if p and not PHONE.fullmatch(p):
        raise StoreError("INVALID_PHONE")
    return e, p


def validate_document(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        raise StoreError("UNSUPPORTED_VERSION")
    if set(document) != {"schema", "revision", "identities"}:
        raise StoreError("INVALID_DOCUMENT")
    revision = document["revision"]
    if type(revision) is not int or revision < 0 or revision >= 1_000_000_000:
        raise StoreError("INVALID_DOCUMENT")
    identities = document["identities"]
    if not isinstance(identities, dict) or len(identities) > MAX_IDENTITIES:
        raise StoreError("INVALID_DOCUMENT")
    clean: dict[str, Any] = {}
    for identity_id, values in identities.items():
        require_identity(identity_id)
        if not isinstance(values, dict) or set(values) != {"email", "phone", "accounts"}:
            raise StoreError("INVALID_DOCUMENT")
        email, phone = validate_contact(values["email"], values["phone"])
        accounts = values["accounts"]
        if not isinstance(accounts, dict) or len(accounts) > len(ITEM_BY_ID):
            raise StoreError("INVALID_DOCUMENT")
        labels: dict[str, str] = {}
        for service_id, label in accounts.items():
            if service_id not in ITEM_BY_ID:
                raise StoreError("INVALID_SERVICE")
            text = require_string(label, 48)
            if not text:
                raise StoreError("INVALID_FIELD")
            labels[service_id] = text
        clean[identity_id] = {"email": email, "phone": phone, "accounts": labels}
    return {"schema": SCHEMA, "revision": revision, "identities": clean}


def _assert_secure_dir(path: Path, create: bool) -> bool:
    if not path.exists() and not path.is_symlink():
        if not create:
            return False
        path.mkdir(parents=True, mode=0o700)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise StoreError("UNSAFE_DIRECTORY")
    return True


def _assert_secure_file(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise StoreError("UNSAFE_FILE")
    return True


def load() -> dict[str, Any]:
    root = root_path()
    if not _assert_secure_dir(root, create=False):
        return new_document()
    path = storage_path()
    if not _assert_secure_file(path):
        return new_document()
    # O_NOFOLLOW protects against swapping a symlink at open time.
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as inp:
        if os.fstat(inp.fileno()).st_mode & 0o077:
            raise StoreError("UNSAFE_FILE")
        raw = inp.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise StoreError("FILE_TOO_LARGE")
    try:
        parsed = json.loads(raw)
    except (ValueError, UnicodeError):
        raise StoreError("INVALID_JSON") from None
    return validate_document(parsed)


def apply(document: dict[str, Any], command: Any) -> dict[str, Any]:
    doc = validate_document(document)
    if not isinstance(command, dict):
        raise StoreError("INVALID_REQUEST")
    op = command.get("action")
    fields = ({"action", "identityId", "expectedRevision", "email", "phone"}
              if op == "save_contact" else
              {"action", "identityId", "expectedRevision", "serviceId", "label"}
              if op == "set_account_label" else set())
    if not fields or set(command) != fields:
        raise StoreError("INVALID_REQUEST")
    identity_id = require_identity(command["identityId"])
    revision = command["expectedRevision"]
    if type(revision) is not int or revision != doc["revision"]:
        raise StoreError("REVISION_CONFLICT")
    record = doc["identities"].get(identity_id)
    if record is None:
        if len(doc["identities"]) >= MAX_IDENTITIES:
            raise StoreError("IDENTITY_CAPACITY")
        record = {"email": "", "phone": "", "accounts": {}}
        doc["identities"][identity_id] = record
    if op == "save_contact":
        record["email"], record["phone"] = validate_contact(
            command["email"], command["phone"])
    else:
        service = command["serviceId"]
        if not isinstance(service, str) or service not in ITEM_BY_ID:
            raise StoreError("INVALID_SERVICE")
        label = require_string(command["label"], 48)
        if label:
            record["accounts"][service] = label
        else:
            record["accounts"].pop(service, None)
    if record == {"email": "", "phone": "", "accounts": {}}:
        doc["identities"].pop(identity_id, None)
    doc["revision"] += 1
    return validate_document(doc)


def save(document: dict[str, Any]) -> None:
    doc = validate_document(document)
    root = root_path()
    _assert_secure_dir(root, create=True)
    target = storage_path()
    _assert_secure_file(target)
    encoded = (json.dumps(doc, ensure_ascii=True, separators=(",", ":")) + "\n").encode("utf-8")
    if len(encoded) > MAX_BYTES:
        raise StoreError("FILE_TOO_LARGE")
    fd, temporary = tempfile.mkstemp(prefix=".account-details-", dir=root)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as out:
            fd = -1
            out.write(encoded)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, target)
        # Directory sync makes the atomic name durable after a power loss.
        dir_fd = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if fd >= 0:
            os.close(fd)
        if os.path.exists(temporary):
            os.unlink(temporary)


def run(action: str) -> dict[str, Any]:
    if action == "read":
        return {"ok": True, "document": load()}
    if action != "update":
        raise StoreError("INVALID_REQUEST")
    raw = sys.stdin.buffer.readline(MAX_REQUEST_BYTES + 1)
    if not raw or len(raw) > MAX_REQUEST_BYTES or not raw.endswith(b"\n"):
        raise StoreError("INVALID_REQUEST")
    try:
        command = json.loads(raw)
    except (ValueError, UnicodeError):
        raise StoreError("INVALID_REQUEST") from None
    current = load()
    changed = apply(current, command)
    save(changed)
    return {"ok": True, "document": changed}


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(description="Private Social account-setup metadata")
    cli.add_argument("action", choices=("read", "update"))
    args = cli.parse_args(argv)
    try:
        result = run(args.action)
        status = 0
    except (StoreError, OSError) as exc:
        code = exc.code if isinstance(exc, StoreError) else "STORAGE_UNAVAILABLE"
        result = {"ok": False, "error": code}
        status = 2
    # Never print the request, account secrets, tokens or traceback.
    print(json.dumps(result, separators=(",", ":")))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
