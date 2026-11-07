#!/usr/bin/env python3
"""P21 // Remembered Personal read-only preference for the existing Social PHONE.

This is NOT an app-authenticated OS permission, enterprise grant, identity
token, or protection from other processes under the same Linux UID. It is
a deliberately opt-in *Personal desktop preference*. A same-UID program can
access BlueFerry independently and could forge the preference. Never use it
for LLC/nonprofit phone account authorization or production credential isolation.

Permission record contains only profile UUID, operations, generation and
display-correlation fields. No message, contact, number, or credential is
stored. Each one-shot read checks the connected device and pinned BlueFerry
owner, then uses the existing bounded P18c host read port. No persistent
socket, terminal, daemon, background sync, send, or read-marking.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys
import tempfile
from typing import Callable, Any, Iterator

from BlueFerryHostReadPort import (
    UniqueOwnerBlueFerrySource, _owner_valid, read_for_trusted_host,
)
from PhoneDeviceObservation import PROFILE, observe as observe_device
from PhonePersonalReadPilot import _matching_device

SCHEMA = "post-apollo.phone.personal-remembered-read.v0"
STORE_SCHEMA = "post-apollo.phone.personal-read-preference.v0"
EXECUTION = "LOCAL_USER_PREFERENCE_NOT_AUTHORITY"
MAX_FILE = 4096
MAX_RESPONSE = 3 * 1024 * 1024
MAX_EPOCH = 2_147_483_647
OPERATIONS = ("contacts.read", "messages.read")
CHOICES = {
    "m": ("messages.read",),
    "c": ("contacts.read",),
    "b": OPERATIONS,
}
KEY = re.compile(r"^[A-Za-z0-9_-]{16,96}$")


def _reply(state: str, **extra: object) -> dict[str, object]:
    return {
        "schema": SCHEMA, "execution": EXECUTION, "state": state,
        "ownerKind": "PERSONAL", "organizationAccess": False,
        "sendingEnabled": False, **extra,
    }


def _path() -> Path:
    root = os.environ.get("XDG_STATE_HOME")
    base = (Path(root) if root and os.path.isabs(root)
            else Path.home() / ".local" / "state")
    return base / "post-apollo" / "social-phone-personal-read.json"


def _private_directory(path: Path, *, create: bool) -> bool:
    try:
        if create:
            path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        info = path.parent.lstat()
        # Post-Apollo already uses this shared state directory. Its normal
        # user-owned 0755 permissions are safe for an owner-only 0600
        # preference file and 0600 lock: other users can list filenames but
        # cannot read or write the record. Do not chmod the shared directory,
        # and still refuse group/other writable or symlinked directories.
        return (stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid()
                and info.st_mode & 0o022 == 0)
    except FileNotFoundError:
        return not create  # Missing store is an unapproved state.
    except OSError:
        return False


def _load(path: Path) -> dict[str, object] | None:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(path, flags)
    except FileNotFoundError:
        return {}
    except OSError:
        return None
    try:
        with os.fdopen(fd, "r", encoding="utf-8") as inp:
            info = os.fstat(inp.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or info.st_mode & 0o077 or info.st_size > MAX_FILE):
                return None
            raw = inp.read(MAX_FILE + 1)
        if len(raw.encode("utf-8")) > MAX_FILE:
            return None
        record = json.loads(raw)
        if type(record) is not dict or set(record) != {
            "schema", "profileId", "approved", "allowed",
            "contextKey", "epoch", "sequences",
        } or record["schema"] != STORE_SCHEMA:
            return None
        if (type(record["profileId"]) is not str
                or PROFILE.fullmatch(record["profileId"]) is None
                or type(record["approved"]) is not bool
                or type(record["allowed"]) is not list
                or len(record["allowed"]) > 2
                or record["allowed"] != sorted(set(record["allowed"]))
                or any(type(op) is not str or op not in OPERATIONS
                       for op in record["allowed"])
                or (record["approved"] and not record["allowed"])
                or (not record["approved"] and record["allowed"])
                or type(record["contextKey"]) is not str
                or KEY.fullmatch(record["contextKey"]) is None
                or type(record["epoch"]) is not int
                or not 1 <= record["epoch"] <= MAX_EPOCH
                or type(record["sequences"]) is not dict
                or set(record["sequences"]) != set(OPERATIONS)
                or any(type(value) is not int or not 0 <= value <= MAX_EPOCH
                       for value in record["sequences"].values())):
            return None
        return record
    except (OSError, UnicodeError, ValueError, TypeError):
        return None


def _write(path: Path, record: dict[str, object]) -> bool:
    payload = (json.dumps(record, sort_keys=True, separators=(",", ":"))
               + "\n").encode("utf-8")
    if len(payload) > MAX_FILE:
        return False
    fd: int | None = None
    temporary: str | None = None
    try:
        fd, temporary = tempfile.mkstemp(prefix=".phone-permission-", dir=path.parent)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as out:
            fd = None
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
        temporary = None
        return True
    except OSError:
        return False
    finally:
        if fd is not None:
            os.close(fd)
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass


@contextmanager
def _locked(path: Path) -> Iterator[None]:
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_CLOEXEC", 0)
    fd = os.open(str(path) + ".lock", flags, 0o600)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077):
            raise ValueError("unsafe local preference lock")
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def _device(observer: Callable[[], object]) -> str:
    try:
        result = observer()
        if (type(result) is dict
                and result.get("schema") == "post-apollo.phone.device-observation.v0"
                and result.get("execution") == "READ_ONLY_DEVICE_OBSERVATION"
                and result.get("state") == "BLUETOOTH_CONNECTED"
                and result.get("bluetoothLink") == "CONNECTED"
                and result.get("trustedPhoneLink") == "UNVERIFIED"
                and result.get("contentAccessEnabled") is False):
            profile = result.get("profileId")
            if type(profile) is str and PROFILE.fullmatch(profile):
                return profile
    except Exception:
        pass
    return ""


def _source_binding(source: Any, profile: str) -> str:
    try:
        owner = source.owner()
        if not _owner_valid(owner):
            return ""
        status = source.status(owner)
        if (type(status) is not dict
                or type(status.get("api_version")) is not int
                or status["api_version"] != 2
                or status.get("daemon") is not True
                or status.get("phone_profile_id") != profile
                or type(status.get("map")) is not bool
                or type(status.get("pbap")) is not bool):
            return ""
        return owner
    except Exception:
        return ""


def _approved_summary(record: dict[str, object]) -> dict[str, object]:
    return _reply(
        "APPROVED", contextKey=record["contextKey"],
        epoch=record["epoch"],
        messagesAllowed="messages.read" in record["allowed"],
        contactsAllowed="contacts.read" in record["allowed"],
    )


def action(
    argv: list[str], *,
    observer: Callable[[], object] = observe_device,
    source_factory: Callable[[], Any] = UniqueOwnerBlueFerrySource,
    location: Path | None = None,
) -> dict[str, object]:
    """Every read and write is explicitly called; import does nothing."""
    if (not isinstance(argv, list) or
            not (len(argv) == 1 and argv[0] in ("--status", "--revoke")
                 or len(argv) == 2 and (
                     argv[0] == "--approve" and argv[1] in CHOICES
                     or argv[0] == "--read" and argv[1] in OPERATIONS))):
        return _reply("REFUSED")
    cmd = argv[0]
    path = location if location is not None else _path()
    create = cmd == "--approve"
    if not _private_directory(path, create=create):
        return _reply("STORAGE_UNAVAILABLE")
    if cmd == "--status":
        record = _load(path)
        if record is None:
            return _reply("STORAGE_UNAVAILABLE")
        if not record or not record["approved"]:
            return _reply("APPROVAL_REQUIRED")
        profile = _device(observer)
        if not profile or profile != record["profileId"]:
            return _reply("DEVICE_UNAVAILABLE")
        return _approved_summary(record)

    if cmd != "--approve" and not path.exists():
        return _reply("REVOKED" if cmd == "--revoke" else "APPROVAL_REQUIRED")

    try:
        with _locked(path):
            record = _load(path)
            if record is None:
                return _reply("STORAGE_UNAVAILABLE")
            if cmd == "--revoke":
                if not record:
                    return _reply("REVOKED")
                if record["epoch"] >= MAX_EPOCH:
                    return _reply("STORAGE_UNAVAILABLE")
                revoked = {
                    **record, "approved": False, "allowed": [],
                    "contextKey": secrets.token_urlsafe(24),
                    "epoch": record["epoch"] + 1,
                    "sequences": {name: 0 for name in OPERATIONS},
                }
                return (_reply("REVOKED") if _write(path, revoked)
                        else _reply("STORAGE_UNAVAILABLE"))

            profile = _device(observer)
            if not profile:
                return _reply("DEVICE_UNAVAILABLE")

            if cmd == "--approve":
                # Only a real click in the visible PHONE permission prompt is
                # the supported UX. CLI arguments are NOT app authentication.
                source = source_factory()
                if not _source_binding(source, profile):
                    return _reply("PROVIDER_UNAVAILABLE")
                next_epoch = int(record.get("epoch", 0)) + 1
                if next_epoch > MAX_EPOCH:
                    return _reply("STORAGE_UNAVAILABLE")
                saved: dict[str, object] = {
                    "schema": STORE_SCHEMA, "profileId": profile,
                    "approved": True, "allowed": list(CHOICES[argv[1]]),
                    "contextKey": secrets.token_urlsafe(24),
                    "epoch": next_epoch,
                    "sequences": {name: 0 for name in OPERATIONS},
                }
                if not _write(path, saved):
                    return _reply("STORAGE_UNAVAILABLE")
                return _approved_summary(saved)

            operation = argv[1]
            if not record or not record["approved"] or profile != record["profileId"]:
                return _reply("APPROVAL_REQUIRED"
                              if not record or not record["approved"]
                              else "DEVICE_UNAVAILABLE")
            if operation not in record["allowed"]:
                return _reply("NOT_CONSENTED")
            if record["epoch"] >= MAX_EPOCH or record["sequences"][operation] >= MAX_EPOCH:
                return _reply("STORAGE_UNAVAILABLE")

            source = source_factory()
            owner = _source_binding(source, profile)
            if not owner:
                return _reply("PROVIDER_UNAVAILABLE")
            held: dict[str, dict[str, object]] = {}

            def guard(op: str, device_profile: str, observed_owner: str) -> bool:
                return (op == operation and device_profile == profile
                        and observed_owner == owner
                        and source.owner() == owner
                        and _matching_device(observer, profile))

            def release(
                op: str, device_profile: str, observed_owner: str,
                projection: dict[str, object],
            ) -> bool:
                if not guard(op, device_profile, observed_owner):
                    return False
                held["projection"] = projection
                return True

            result = read_for_trusted_host(
                operation=operation, profile_id=profile,
                source=source, host_guard=guard, host_release=release,
            )
            if result.get("state") != "HOST_HANDOFF_REPORTED" or not held:
                return _reply("READ_UNAVAILABLE")
            if not guard(operation, profile, owner):
                held.clear()
                return _reply("DEVICE_UNAVAILABLE")

            next_record: dict[str, object] = {
                **record, "epoch": record["epoch"] + 1,
                "sequences": {
                    **record["sequences"],
                    operation: record["sequences"][operation] + 1,
                },
            }
            response = _reply(
                "SNAPSHOT", operation=operation, profileId=profile,
                contextKey=record["contextKey"],
                epoch=next_record["epoch"],
                sequence=next_record["sequences"][operation],
                projection=held.pop("projection"),
            )
            if len(json.dumps(response, ensure_ascii=False).encode("utf-8")) > MAX_RESPONSE:
                return _reply("READ_UNAVAILABLE")
            if not _write(path, next_record):
                return _reply("STORAGE_UNAVAILABLE")
            return response
    except Exception:
        # Never put raw BlueFerry errors, profile IDs or private data on stdout.
        # Provider imports or transient D-Bus failures must fail closed too.
        return _reply("READ_UNAVAILABLE" if cmd == "--read"
                      else "PROVIDER_UNAVAILABLE" if cmd == "--approve"
                      else "STORAGE_UNAVAILABLE")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    result = action(args)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0 if result["state"] != "REFUSED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
