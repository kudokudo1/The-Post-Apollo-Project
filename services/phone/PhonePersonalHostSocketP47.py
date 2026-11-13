"""P47 PHONE Personal // Real Linux Unix-socket STATUS boundary, never a save host.

This is executable Linux socket transport source for a future installed host,
not an installed, independently attested Identity/C3e/C5 service. It ONLY
answers a constant, non-sensitive status probe. It never imports/reads P35
vault, keyring, C5, BlueFerry, a note or a contact identity and has no
mutation operation. Kernel SO_PEERCRED is observed on accepted connections,
but same-UID, PID or cgroup alone CANNOT authenticate a trusted installation.

A caller-created 0700 private, non-symlink directory is required explicitly;
there is no default HOME or runtime socket, automatic launch or CLI entry
point. No production grant can be enabled with a constructor argument.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import stat
import struct
from threading import Event

SCHEMA = "post-apollo.phone.personal-host-status.p47.v1"
SOCKET_NAME = "phone-personal-status-p47.sock"
MAX_REQUEST = 512
UNIX_PATH_MAX = 107
ACCEPT_TIMEOUT = 0.1
PEER_TIMEOUT = 0.5
REQUEST = {
    "schema": SCHEMA,
    "operation": "STATUS",
}
STATUS = {
    "schema": SCHEMA,
    "status": "HOST_UNTRUSTED_STATUS_ONLY",
    "linuxPeerCredentialsObserved": True,
    "installedIdentityVerified": False,
    "independentChallengeVerified": False,
    "c5OneUseConsentVerified": False,
    "keyReadAuthorized": False,
    "productionEnabled": False,
    "personalSaveAuthorized": False,
    "readbackTrusted": False,
    "retryAuthorized": False,
}
DENIED = {
    **STATUS,
    "status": "DENIED",
    "linuxPeerCredentialsObserved": False,
}


class HostBoundaryRefused(Exception):
    """No path, process, request body, note or raw error in public refusal."""


def _deny() -> None:
    raise HostBoundaryRefused("PHONE_HOST_BOUNDARY_REFUSED")


def _canonical(value: dict[str, object]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii") + b"\n"


REQUEST_FRAME = _canonical(REQUEST)
STATUS_FRAME = _canonical(STATUS)
DENIED_FRAME = _canonical(DENIED)


def _private_directory(directory: object) -> Path:
    try:
        if type(directory) is not Path or not directory.is_absolute():
            _deny()
        info = directory.lstat()
        if (not stat.S_ISDIR(info.st_mode)
                or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o700
                or directory.resolve(strict=True) != directory):
            _deny()
        sockpath = directory / SOCKET_NAME
        if len(os.fsencode(str(sockpath))) > UNIX_PATH_MAX:
            _deny()
        # Never unlink a stale path or overwrite another service.
        if os.path.lexists(sockpath):
            _deny()
        return directory
    except HostBoundaryRefused:
        raise
    except (OSError, ValueError, TypeError, RuntimeError):
        _deny()


def _kernel_same_uid_peer(conn: socket.socket) -> bool:
    """Actual Linux kernel SO_PEERCRED at connect, NOT installed-app trust."""
    try:
        raw = conn.getsockopt(
            socket.SOL_SOCKET, socket.SO_PEERCRED,
            struct.calcsize("3i")
        )
        if type(raw) is not bytes or len(raw) != struct.calcsize("3i"):
            return False
        pid, uid, _gid = struct.unpack("3i", raw)
        return pid > 0 and uid == os.geteuid()
    except (AttributeError, OSError, ValueError, TypeError, struct.error):
        return False


def _read_exact_status(conn: socket.socket) -> bool:
    """Only the exact one-line STATUS request, no personal data or JSON extras.

    A slow, oversized, partial, malformed, multiline or private-operation
    request gets a fixed DENIED answer. There is only one response per socket.
    """
    buf = bytearray()
    try:
        conn.settimeout(PEER_TIMEOUT)
        while len(buf) <= MAX_REQUEST:
            chunk = conn.recv(MAX_REQUEST + 1 - len(buf))
            if not chunk:
                return False
            buf.extend(chunk)
            if len(buf) > MAX_REQUEST:
                return False
            if b"\n" in chunk:
                return bytes(buf) == REQUEST_FRAME
        return False
    except (OSError, TimeoutError, ValueError):
        return False


def _respond(conn: socket.socket) -> None:
    try:
        if _kernel_same_uid_peer(conn) and _read_exact_status(conn):
            conn.sendall(STATUS_FRAME)
        else:
            conn.sendall(DENIED_FRAME)
    except (OSError, TimeoutError, ValueError):
        # No user-supplied data, operating-system credentials, paths or errors
        # are ever emitted on stdout/stderr or to a public log.
        return


def serve_status_only(
    socket_directory: object, *, stop: Event, started: Event | None = None,
) -> None:
    """Serve constant STATUS on a real Linux AF_UNIX socket until stopped.

    Caller explicitly creates a 0700 directory; the server creates ONLY a
    0600 socket. There is no live key access, trust permit, production save
    call, or readiness upgrade. The accepted peer is inspected using Linux
    SO_PEERCRED. A future service needs its own independently authenticated
    installed/seat/signer evidence and genuine C5 one-use consent.
    """
    if type(stop) is not Event or (started is not None
                                  and type(started) is not Event):
        _deny()
    directory = _private_directory(socket_directory)
    path = directory / SOCKET_NAME
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    own_inode: tuple[int, int] | None = None
    try:
        server.settimeout(ACCEPT_TIMEOUT)
        try:
            server.bind(str(path))
            os.chmod(path, 0o600, follow_symlinks=False)
            current = path.lstat()
            if (not stat.S_ISSOCK(current.st_mode)
                    or current.st_uid != os.geteuid()
                    or stat.S_IMODE(current.st_mode) != 0o600):
                _deny()
            own_inode = (current.st_dev, current.st_ino)
            server.listen(4)
        except (OSError, ValueError, TypeError):
            _deny()
        if started is not None:
            started.set()
        while not stop.is_set():
            try:
                conn, _ = server.accept()
            except socket.timeout:
                continue
            except OSError:
                _deny()
            with conn:
                _respond(conn)
    finally:
        server.close()
        # Never blindly remove a socket that another process replaced.
        try:
            current = path.lstat()
            if (own_inode is not None
                    and stat.S_ISSOCK(current.st_mode)
                    and (current.st_dev, current.st_ino) == own_inode):
                path.unlink()
        except OSError:
            pass


# No __main__, live service registration, QML wiring, keyring, P35 mutation,
# trust signer, C5 issuer, production upgrade switch or saved response.
