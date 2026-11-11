#!/usr/bin/env python3
"""Private same-user STOP channel for opt-in experimental autoscroll sessions.

No TCP, keyboard hooks, service registration or automated activation.
The AF_UNIX endpoint is created only by an explicit experimental backend run.
An authorized same-UID client can send one literal STOP command. Existing
sockets are NEVER unlinked or replaced during server startup.
"""
from __future__ import annotations

import os
from pathlib import Path
import select
import socket
import stat
import struct

SOCKET_NAME = "autoscroll-stop-v1.sock"
STOP_COMMAND = b"STOP\n"
ACK = b"STOPPED\n"


class StopChannelError(Exception):
    pass


def parent_path():
    base = os.environ.get("XDG_RUNTIME_DIR")
    if not base:
        raise StopChannelError("RUNTIME_DIR_UNAVAILABLE")
    root = Path(base)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise StopChannelError("RUNTIME_DIR_UNSAFE")
    info = root.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise StopChannelError("RUNTIME_DIR_UNSAFE")
    return root / "post-apollo"


def private_directory():
    root = parent_path()
    try:
        root.mkdir(mode=0o700, exist_ok=True)
    except OSError as exc:
        raise StopChannelError("SOCKET_DIRECTORY_FAILED") from exc
    info = root.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o077):
        raise StopChannelError("SOCKET_DIRECTORY_UNSAFE")
    return root


def socket_path(create=False):
    return (private_directory() if create else parent_path()) / SOCKET_NAME


def inspect_socket(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if (not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o177):
        raise StopChannelError("SOCKET_UNSAFE")
    return info


class StopServer:
    def __init__(self):
        self.path = None
        self.sock = None
        self.inode = None

    def __enter__(self):
        self.path = socket_path(create=True)
        if self.path.exists() or self.path.is_symlink():
            raise StopChannelError("STOP_ENDPOINT_ALREADY_EXISTS")
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock = sock
        try:
            old_umask = os.umask(0o177)
            try:
                sock.bind(str(self.path))
            finally:
                os.umask(old_umask)
            os.chmod(self.path, 0o600)
            self.inode = os.lstat(self.path).st_ino
            sock.listen(3)
            sock.setblocking(False)
            return self
        except Exception:
            self.close()
            raise

    def healthy(self):
        if self.sock is None or self.path is None or self.inode is None:
            return False
        try:
            info = self.path.lstat()
            return (info.st_ino == self.inode
                    and stat.S_ISSOCK(info.st_mode)
                    and info.st_uid == os.getuid()
                    and not (info.st_mode & 0o177))
        except OSError:
            return False

    def poll(self):
        if self.sock is None:
            return False
        try:
            readable, _, _ = select.select([self.sock], [], [], 0)
            if not readable:
                return False
            connection, _ = self.sock.accept()
            with connection:
                connection.settimeout(0.1)
                if not hasattr(socket, "SO_PEERCRED"):
                    return False
                credentials = connection.getsockopt(
                    socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
                pid, uid, gid = struct.unpack("3i", credentials)
                if uid != os.getuid() or pid <= 0:
                    return False
                payload = connection.recv(16)
                if payload != STOP_COMMAND:
                    return False
                connection.sendall(ACK)
                return True
        except (OSError, ValueError, struct.error):
            return False

    def close(self):
        if self.sock is not None:
            self.sock.close()
            self.sock = None
        if self.path is not None and self.inode is not None:
            try:
                info = self.path.lstat()
                if (info.st_ino == self.inode
                        and stat.S_ISSOCK(info.st_mode)
                        and info.st_uid == os.getuid()):
                    self.path.unlink()
            except FileNotFoundError:
                pass
            self.inode = None

    def __exit__(self, exc_type, exc, tb):
        self.close()


def send_stop():
    path = socket_path()
    if inspect_socket(path) is None:
        raise StopChannelError("NO_ACTIVE_SESSION")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
        conn.settimeout(0.3)
        try:
            conn.connect(str(path))
            conn.sendall(STOP_COMMAND)
            response = conn.recv(32)
        except OSError as exc:
            raise StopChannelError("STOP_DELIVERY_FAILED") from exc
        if response != ACK:
            raise StopChannelError("STOP_NOT_ACKNOWLEDGED")
    return {"status": "stop_acknowledged", "runtime_stopped": False}
