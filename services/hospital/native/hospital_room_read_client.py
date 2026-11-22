#!/usr/bin/python3 -I
"""Hospital Room metadata only: protected PX source reader.

This source is NOT a desktop database client. Production installation is
independently reviewed at /usr/libexec/post-apollo/hospital/hospital-room-read.
The root-owned public *routing* policy pins the owner UID and socket. PX
writer checks the peer's desktop UID itself. No option, environment variable,
or fallback may choose a DB, socket, writer, key or alternate CLI.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import socket
import stat
import struct
import sys

CLIENT = Path("/usr/libexec/post-apollo/hospital/hospital-room-read")
CONFIG = Path("/etc/post-apollo/hospital/room-read-client.json")
SCHEMA = "postapollo.hospital.protected-read-client.v1"
REQUEST_SCHEMA = "post-apollo.hospital.protected-room-writer.v1"
SOCKET_NAME = "hospital-room-writer-v1.sock"
CONFIG_FIELDS = {"schema", "clientUid", "writerUid", "socketPath"}
DOCTOR_FIELDS = {"id", "name", "role", "status", "createdAt", "updatedAt"}
DOCTOR_STATUSES = {"ACTIVE", "INACTIVE", "RELEASED"}
MAX_DOCTORS = 250
ROOM_RE = re.compile(r"[A-Za-z0-9._:/-]{1,160}\Z", re.ASCII)
SHA_RE = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
MAX_RESPONSE = 1_048_576

class BackendHold(ValueError):
    pass

def refuse(code):
    raise BackendHold(code)

def unique_pairs(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            refuse("DUPLICATE_JSON_FIELD")
        data[key] = value
    return data

def nonfinite(_value):
    refuse("NONFINITE_JSON_NUMBER")

def decode(raw: bytes):
    if not isinstance(raw, bytes) or len(raw) > MAX_RESPONSE:
        refuse("RESPONSE_BOUNDS")
    try:
        return json.loads(raw.decode("utf-8", "strict"),
                          object_pairs_hook=unique_pairs,
                          parse_constant=nonfinite)
    except (UnicodeError, TypeError, ValueError) as exc:
        raise BackendHold("INVALID_JSON") from exc

def _trusted_root_path(path: Path):
    if not path.is_absolute():
        refuse("UNPINNED_FILE")
    for parent in path.parents:
        info = parent.lstat()
        if (not stat.S_ISDIR(info.st_mode)
                or info.st_uid != 0
                or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)):
            refuse("UNTRUSTED_ROOT_ANCESTOR")

def _installed_client():
    # The executable and all ancestors must be root-owned. The shebang
    # invokes python3 -I to disable PYTHONPATH/user-site injection.
    if sys.platform != "linux" or os.getuid() != os.geteuid() or os.geteuid() == 0:
        refuse("INVALID_CLIENT_IDENTITY")
    _trusted_root_path(CLIENT)
    info = CLIENT.lstat()
    actual = Path(__file__).stat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0
            or info.st_nlink != 1
            or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            or info.st_mode & stat.S_IXUSR == 0
            or (info.st_dev, info.st_ino) != (actual.st_dev, actual.st_ino)):
        refuse("CLIENT_EXECUTABLE_NOT_PINNED")

def _config():
    _trusted_root_path(CONFIG)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(str(CONFIG), flags)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != 0
                or before.st_nlink != 1
                or before.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
                or not 1 <= before.st_size <= 4096):
            refuse("UNTRUSTED_READ_POLICY")
        content = os.read(fd, 4097)
        after = os.fstat(fd)
        if (len(content) != before.st_size or
            (before.st_dev, before.st_ino, before.st_size,
             before.st_mtime_ns, before.st_ctime_ns) !=
            (after.st_dev, after.st_ino, after.st_size,
             after.st_mtime_ns, after.st_ctime_ns)):
            refuse("READ_POLICY_CHANGED")
    finally:
        os.close(fd)
    cfg = decode(content)
    if type(cfg) is not dict or set(cfg) != CONFIG_FIELDS or cfg["schema"] != SCHEMA:
        refuse("INVALID_READ_POLICY_FIELDS")
    owner, client = cfg["writerUid"], cfg["clientUid"]
    if (type(owner) is not int or owner <= 0 or type(client) is not int
            or client <= 0 or owner == client or client != os.geteuid()):
        refuse("WRITER_AND_DESKTOP_UID_NOT_PINNED")
    value = cfg["socketPath"]
    if type(value) is not str or not 1 <= len(value) < 100 or "\x00" in value:
        refuse("SOCKET_PATH_INVALID")
    target = Path(value)
    if (not target.is_absolute() or ".." in target.parts
            or target.name != SOCKET_NAME):
        refuse("UNTRUSTED_SOCKET_DESTINATION")
    return target, owner

def _socket_path(target: Path, writer_uid: int):
    for parent in target.parents:
        info = parent.lstat()
        if (not stat.S_ISDIR(info.st_mode)
                or info.st_uid not in (0, writer_uid)
                or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)):
            refuse("SOCKET_PARENT_NOT_PROTECTED")
    info = target.lstat()
    if (not stat.S_ISSOCK(info.st_mode) or info.st_uid != writer_uid
            or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)):
        refuse("SOCKET_NOT_PROTECTED")

def _peer(s: socket.socket, writer_uid: int):
    if not hasattr(socket, "SO_PEERCRED"):
        refuse("LINUX_PEER_IDENTITY_REQUIRED")
    raw = s.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
    if len(raw) != 12:
        refuse("KERNEL_PEER_TRUNCATED")
    pid, uid, gid = struct.unpack("3i", raw)
    if pid <= 1 or uid != writer_uid or gid < 0:
        refuse("PROTECTED_WRITER_UID_MISMATCH")
    return pid, uid, gid

def valid_room(room_id):
    return type(room_id) is str and ROOM_RE.fullmatch(room_id) is not None

def _bounded_read(s: socket.socket):
    result = bytearray()
    while len(result) <= MAX_RESPONSE:
        part = s.recv(min(16384, MAX_RESPONSE + 1 - len(result)))
        if not part:
            break
        result.extend(part)
    if (not result or len(result) > MAX_RESPONSE
            or result[-1:] != b"\n" or result.count(b"\n") != 1):
        refuse("MALFORMED_WRITER_RESPONSE")
    return bytes(result[:-1])

def _exchange(s: socket.socket, operation: str, room_id: str | None,
              writer_uid: int):
    # Only review/bin operations exist. No SQL, Trash, Restore or Burn.
    if operation == "review" and valid_room(room_id):
        request = {"schema": REQUEST_SCHEMA, "operation": "review", "roomId": room_id}
    elif operation == "bin" and room_id is None:
        request = {"schema": REQUEST_SCHEMA, "operation": "bin"}
    elif operation == "doctor-directory" and room_id is None:
        # Fixed metadata-only list. No caller-supplied filter, argv or SQL.
        request = {"schema": REQUEST_SCHEMA, "operation": "doctor-directory"}
    else:
        refuse("READ_ONLY_OPERATION_REQUIRED")
    initial_peer = _peer(s, writer_uid)
    payload = json.dumps(request, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False).encode("ascii") + b"\n"
    if len(payload) >= 4096:
        refuse("REQUEST_TOO_LARGE")
    s.sendall(payload)
    s.shutdown(socket.SHUT_WR)
    raw = _bounded_read(s)
    if _peer(s, writer_uid) != initial_peer:
        refuse("WRITER_PROCESS_CHANGED")
    decoded = decode(raw)
    if type(decoded) is not dict or set(decoded) != {"ok", "data"} or decoded["ok"] is not True:
        refuse("WRITER_REFUSED")
    body = decoded["data"]
    if operation == "review":
        if (type(body) is not dict
                or body.get("roomId") != room_id
                or body.get("state") not in ("ACTIVE", "TRASHED")
                or type(body.get("revision")) is not int or body["revision"] < 0
                or type(body.get("digest")) is not str
                or SHA_RE.fullmatch(body["digest"]) is None
                or type(body.get("blockers")) is not list
                or type(body.get("canTrash")) is not bool
                or type(body.get("canRestore")) is not bool
                or body.get("canBurn") is not False
                or body.get("operatorAuthenticated") is not False):
            refuse("INVALID_PROTECTED_ROOM_REVIEW")
    elif operation == "bin":
        if type(body) is not list or len(body) > 2500:
            refuse("INVALID_PROTECTED_BIN")
        for row in body:
            if (type(row) is not dict
                    or not valid_room(row.get("roomId"))
                    or row.get("state") != "TRASHED"
                    or row.get("kind") != "HOSPITAL ROOM"
                    or row.get("burnAllowed") is not False
                    or type(row.get("revision")) is not int
                    or row["revision"] <= 0):
                refuse("INVALID_PROTECTED_ROOM_ENTRY")
    else:
        # Doctor names are metadata, not authority. Reject unexpected
        # fields, duplicate identities, unbounded strings or partial lists.
        if type(body) is not list or len(body) > MAX_DOCTORS:
            refuse("INVALID_PROTECTED_DOCTOR_DIRECTORY")
        ids = set()
        for row in body:
            if (type(row) is not dict or set(row) != DOCTOR_FIELDS
                    or type(row["id"]) is not str
                    or not 1 <= len(row["id"]) <= 160
                    or "\x00" in row["id"]
                    or row["id"] in ids
                    or type(row["name"]) is not str
                    or not 1 <= len(row["name"]) <= 1024
                    or "\x00" in row["name"]
                    or type(row["role"]) is not str
                    or not 1 <= len(row["role"]) <= 128
                    or "\x00" in row["role"]
                    or type(row["status"]) is not str
                    or row["status"] not in DOCTOR_STATUSES
                    or any(
                        type(row[key]) is not str
                        or len(row[key]) > 96 or "\x00" in row[key]
                        for key in ("createdAt", "updatedAt")
                    )):
                refuse("INVALID_PROTECTED_DOCTOR_ENTRY")
            ids.add(row["id"])
    return body

def main(argv):
    if len(argv) == 2 and argv[0] == "review" and valid_room(argv[1]):
        op, room_id = "review", argv[1]
    elif len(argv) == 1 and argv[0] == "bin":
        op, room_id = "bin", None
    elif len(argv) == 1 and argv[0] == "doctor-directory":
        op, room_id = "doctor-directory", None
    else:
        refuse("READ_ONLY_ARGUMENTS_REQUIRED")
    _installed_client()
    socket_path, writer_uid = _config()
    _socket_path(socket_path, writer_uid)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(4)
        s.connect(str(socket_path))
        current_peer = _peer(s, writer_uid)
        result = _exchange(s, op, room_id, writer_uid)
        if _peer(s, writer_uid) != current_peer:
            refuse("WRITER_REPLACED")
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (BackendHold, OSError, socket.error, TimeoutError):
        # Never leak private writer paths, source records or user transcripts.
        print("HOSPITAL BACKEND NOT READY", file=sys.stderr)
        raise SystemExit(2)
