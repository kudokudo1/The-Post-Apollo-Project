#!/usr/bin/env python3
"""Opt-in, single-user PERSONAL iPhone read-only pilot (not organization auth).

The host is started ONLY after a typed confirmation in a separate terminal.
It uses owner-only runtime Unix IPC and Linux peer UID; this does NOT isolate
other applications with the same UID, authenticate an Identity Center user,
prove any organization/line binding, or meet the proposed production threat
model. This experimental pilot must not be activated as a trusted service.

No persistent grants, body/contacts DB, background polling, calls or sending.
An operator-approved, short-lived host reads from an already-running BlueFerry
daemon and serves only matching paired+connected Personal iPhone projections.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import stat
import struct
import subprocess
import sys
import time
from typing import Any, Callable

from BlueFerryHostReadPort import UniqueOwnerBlueFerrySource, read_for_trusted_host
from PhoneDeviceObservation import observe as observe_device

SCHEMA = "post-apollo.phone.personal-local-pilot.v0"
REQUEST_SCHEMA = "post-apollo.phone.personal-local-pilot-request.v0"
EXECUTION = "EXPLICIT_PERSONAL_LOCAL_PILOT"
SOCKET_FILE = "phone-personal-read-v0.sock"
RUNTIME_SUBDIR = "post-apollo-phone"
CONFIRM_TEXT = "ALLOW PERSONAL IPHONE READ"
TTL_SECONDS = 600
MAX_RESPONSE_BYTES = 3 * 1024 * 1024
OPERATIONS = {"messages.read", "contacts.read"}


def _reply(state: str, **extra: object) -> dict[str, object]:
    return {
        "schema": SCHEMA, "execution": EXECUTION, "state": state,
        "ownerKind": "PERSONAL", "organizationAccess": False,
        "sendingEnabled": False, **extra,
    }


def _directory(create: bool) -> Path:
    xdg = os.environ.get("XDG_RUNTIME_DIR", "")
    if not xdg or not os.path.isabs(xdg):
        raise ValueError("private XDG runtime directory unavailable")
    base = Path(xdg)
    info = base.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o077):
        raise ValueError("insecure XDG runtime directory")
    directory = base / RUNTIME_SUBDIR
    if create:
        try:
            directory.mkdir(mode=0o700)
        except FileExistsError:
            pass
    info = directory.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o077):
        raise ValueError("insecure phone runtime directory")
    return directory


def _socket_path(create: bool = False) -> Path:
    path = _directory(create=create) / SOCKET_FILE
    if len(os.fsencode(path)) > 98:
        raise ValueError("socket path too long")
    return path


def _peer_valid(conn: socket.socket) -> bool:
    if not hasattr(socket, "SO_PEERCRED"):
        return False
    try:
        raw = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
        _pid, uid, _gid = struct.unpack("3i", raw)
        return uid == os.getuid()
    except (OSError, ValueError, struct.error):
        return False


def _matching_device(observer: Callable[[], object], profile: str) -> bool:
    try:
        obj = observer()
        return (
            type(obj) is dict
            and obj.get("schema") == "post-apollo.phone.device-observation.v0"
            and obj.get("execution") == "READ_ONLY_DEVICE_OBSERVATION"
            and obj.get("state") == "BLUETOOTH_CONNECTED"
            and obj.get("bluetoothLink") == "CONNECTED"
            and obj.get("profileId") == profile
            and obj.get("trustedPhoneLink") == "UNVERIFIED"
            and obj.get("contentAccessEnabled") is False
        )
    except Exception:
        return False


class PersonalReadSession:
    """Single-threaded, bounded host session after explicit terminal consent.

    Construction is NOT a trusted grant mechanism. Production must replace
    the OS UID trust model with authenticated Identity Center/Account Broker
    principal, provider permission, device/line and revoke-wipe authority.
    """

    def __init__(
        self, *, profile: str, owner: str, allowed: frozenset[str],
        source: Any, observer: Callable[[], object],
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        from BlueFerrySocialProjection import PROFILE
        if (type(profile) is not str or not PROFILE.fullmatch(profile)
                or type(owner) is not str or not owner.startswith(":")
                or type(allowed) is not frozenset
                or not allowed or not allowed.issubset(OPERATIONS)
                or not callable(observer) or not callable(clock)):
            raise ValueError("invalid Personal host session")
        self.profile, self.owner = profile, owner
        self.allowed = allowed
        self.source, self.observer, self.clock = source, observer, clock
        self.expiry = clock() + TTL_SECONDS
        self.epoch = int(time.time())
        self.context = secrets.token_urlsafe(24)
        self.sequence = {"messages.read": 0, "contacts.read": 0}
        self.revoked = False

    def active(self) -> bool:
        try:
            return (
                not self.revoked and self.clock() < self.expiry
                and self.source.owner() == self.owner
                and _matching_device(self.observer, self.profile)
            )
        except Exception:
            return False

    def process(self, request: object) -> dict[str, object]:
        if (type(request) is not dict
                or set(request) != {"schema", "operation"}
                or request.get("schema") != REQUEST_SCHEMA
                or type(request.get("operation")) is not str):
            return _reply("REFUSED")
        operation = request["operation"]
        if operation == "revoke":
            self.revoked = True
            return _reply("REVOKED")
        if operation == "status":
            if self.active():
                return _reply("PERSONAL_LOCAL_PILOT_ACTIVE",
                              contextKey=self.context, epoch=self.epoch)
            return _reply("NOT_ACTIVE")
        if operation not in OPERATIONS:
            return _reply("REFUSED")
        if operation not in self.allowed:
            return _reply("NOT_CONSENTED")
        try:
            if not self.active():
                self.revoked = True
                return _reply("NOT_ACTIVE")
            held: dict[str, dict[str, object]] = {}

            def guard(op: str, profile: str, owner: str) -> bool:
                return (op == operation and profile == self.profile
                        and owner == self.owner and self.active())

            def release(op: str, profile: str, owner: str,
                        projection: dict[str, object]) -> bool:
                # The single-threaded socket host cannot process revoke
                # concurrently with this read. Recheck physical identity.
                if not guard(op, profile, owner):
                    return False
                held["projection"] = projection
                return True

            result = read_for_trusted_host(
                operation=operation, profile_id=self.profile,
                source=self.source, host_guard=guard, host_release=release,
            )
            if (result.get("state") != "HOST_HANDOFF_REPORTED"
                    or "projection" not in held or not self.active()):
                held.clear()
                return _reply("READ_UNAVAILABLE")
            self.sequence[operation] += 1
            return _reply(
                "SNAPSHOT", operation=operation, profileId=self.profile,
                contextKey=self.context, epoch=self.epoch,
                sequence=self.sequence[operation],
                projection=held.pop("projection"),
            )
        except Exception:
            return _reply("READ_UNAVAILABLE")


def _handle(conn: socket.socket, session: PersonalReadSession) -> None:
    try:
        conn.settimeout(12.0)
        if not _peer_valid(conn):
            return
        data = bytearray()
        while len(data) <= 256:
            chunk = conn.recv(257 - len(data))
            if not chunk:
                break
            data.extend(chunk)
            if b"\n" in data:
                break
        if len(data) > 256 or not data.endswith(b"\n") or data.count(b"\n") != 1:
            result = _reply("REFUSED")
        else:
            try:
                request = json.loads(data.decode("utf-8").strip())
            except (ValueError, UnicodeError):
                request = None
            result = session.process(request)
        payload = json.dumps(result, ensure_ascii=False, allow_nan=False,
                             separators=(",", ":")).encode("utf-8")
        if len(payload) > MAX_RESPONSE_BYTES:
            payload = json.dumps(_reply("READ_UNAVAILABLE")).encode("utf-8")
        conn.sendall(payload + b"\n")
    except (OSError, UnicodeError, ValueError):
        pass


def _run_server(session: PersonalReadSession) -> None:
    path = _socket_path(create=True)
    if os.path.lexists(path):
        raise FileExistsError("Existing phone pilot socket; refusing takeover")
    previous_umask = os.umask(0o077)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    inode = None
    try:
        server.bind(str(path))
        os.chmod(path, 0o600)
        inode = path.lstat().st_ino
        server.listen(4)
        server.settimeout(0.5)
        while not session.revoked and session.clock() < session.expiry:
            try:
                conn, _ = server.accept()
            except socket.timeout:
                continue
            with conn:
                _handle(conn, session)
        session.revoked = True
    finally:
        os.umask(previous_umask)
        server.close()
        if inode is not None:
            try:
                info = path.lstat()
                if stat.S_ISSOCK(info.st_mode) and info.st_ino == inode:
                    path.unlink()
            except OSError:
                pass


def _consent_and_serve() -> int:
    if not sys.stdin.isatty():
        return 2
    print("POST-APOLLO // PERSONAL IPHONE READ-ONLY PILOT\n")
    print("This permits local apps running as your Linux user to read the")
    print("selected iPhone's BlueFerry cached threads and contact cards for")
    print("up to 10 minutes. No texts are sent, marked read or saved by")
    print("Post-Apollo. Do not use this for LLC/nonprofit identities.")
    print("Other same-UID desktop applications are NOT isolated by this pilot.\n")
    print("Type exactly: " + CONFIRM_TEXT)
    try:
        if input("> ").strip() != CONFIRM_TEXT:
            print("Consent declined.")
            return 2
        observed = observe_device()
        if (type(observed) is not dict or
                observed.get("state") != "BLUETOOTH_CONNECTED" or
                observed.get("trustedPhoneLink") != "UNVERIFIED" or
                observed.get("contentAccessEnabled") is not False):
            print("No exact paired and connected BlueFerry iPhone.")
            return 2
        profile = observed.get("profileId")
        source = UniqueOwnerBlueFerrySource()
        owner = source.owner()
        from BlueFerryHostReadPort import _owner_valid
        if not _owner_valid(owner) or not _matching_device(observe_device, profile):
            print("Phone provider or profile could not be verified.")
            return 2
        # Separate explicit scope choice: only requested read operations
        # become available for this short Personal consent session.
        print("\nChoose read access: [m]essages, [c]ontacts, [b]oth, or [n]either")
        choice = input("> ").strip().lower()
        choices = {
            "m": frozenset({"messages.read"}),
            "c": frozenset({"contacts.read"}),
            "b": frozenset({"messages.read", "contacts.read"}),
        }
        if choice not in choices:
            print("No phone data permission granted.")
            return 2
        session = PersonalReadSession(
            profile=profile, owner=owner, allowed=choices[choice],
            source=source, observer=observe_device,
        )
        print("\nPersonal pilot active for at most 10 minutes.")
        print("Use Social PHONE → MESSAGES / CONTACTS → LOAD PERSONAL.")
        print("Press Ctrl+C in this terminal to stop the host.")
        _run_server(session)
        return 0
    except (KeyboardInterrupt, EOFError):
        print("\nPersonal phone pilot stopped.")
        return 0
    except Exception:
        print("Phone read pilot could not start. No access was granted.")
        return 2


def _client(operation: str) -> int:
    if operation not in OPERATIONS | {"status", "revoke"}:
        print(json.dumps(_reply("REFUSED")))
        return 2
    try:
        path = _socket_path()
        info = path.lstat()
        if (not stat.S_ISSOCK(info.st_mode)
                or info.st_uid != os.getuid() or info.st_mode & 0o077):
            raise ValueError("untrusted socket")
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
            conn.settimeout(12)
            conn.connect(str(path))
            if not _peer_valid(conn):
                raise ValueError("untrusted peer")
            request = json.dumps({
                "schema": REQUEST_SCHEMA, "operation": operation,
            }).encode("utf-8") + b"\n"
            conn.sendall(request)
            received = bytearray()
            while len(received) <= MAX_RESPONSE_BYTES:
                part = conn.recv(min(65536, MAX_RESPONSE_BYTES + 1 - len(received)))
                if not part:
                    break
                received.extend(part)
                if b"\n" in part:
                    break
            if (len(received) > MAX_RESPONSE_BYTES
                    or not received.endswith(b"\n")
                    or received.count(b"\n") != 1):
                raise ValueError("unexpected host response")
            result = json.loads(received.decode("utf-8"))
            if (type(result) is not dict or result.get("schema") != SCHEMA
                    or result.get("execution") != EXECUTION
                    or result.get("ownerKind") != "PERSONAL"
                    or result.get("organizationAccess") is not False
                    or result.get("sendingEnabled") is not False):
                raise ValueError("unexpected host schema")
            print(json.dumps(result, ensure_ascii=False, allow_nan=False))
            return 0
    except Exception:
        print(json.dumps(_reply("NOT_ACTIVE")))
        return 2


def _open_consent() -> int:
    # Only the user's explicit PHONE button runs this. The terminal performs
    # a second, visible typed opt-in; launching a terminal is not consent.
    foot = shutil.which("foot")
    if not foot:
        print(json.dumps(_reply("TERMINAL_UNAVAILABLE")))
        return 2
    try:
        subprocess.Popen(
            [foot, "--title=Post-Apollo-Personal-Phone", sys.executable,
             str(Path(__file__).resolve()), "--serve"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True,
            close_fds=True,
        )
        print(json.dumps(_reply("CONSENT_TERMINAL_REQUESTED")))
        return 0
    except OSError:
        print(json.dumps(_reply("TERMINAL_UNAVAILABLE")))
        return 2


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args == ["--serve"]:
        return _consent_and_serve()
    if args == ["--open-consent"]:
        return _open_consent()
    if len(args) == 2 and args[0] == "--client":
        return _client(args[1])
    print(json.dumps(_reply("EXPLICIT_ACTION_REQUIRED")))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
