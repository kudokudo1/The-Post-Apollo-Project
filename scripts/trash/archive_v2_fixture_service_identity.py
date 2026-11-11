#!/usr/bin/env python3
"""V2q deny-only fixture service-file, socket and UID/GID evidence.

The broker supplies an independently pinned TEST_FIXTURE_ONLY policy. No
request may choose files or a trust root. This observes only synthetic files
under an explicit private 0700 test directory, creates no service or socket,
and never grants ArchiveStore or production access.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import stat

HEX = re.compile(r"^[0-9a-f]{64}$")
BASENAME = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9_.-]{0,79}$")
OWNERS = frozenset(("demo-scrape", "weather-events"))
POLICY_KEYS = frozenset((
    "origin", "ownerId", "expectedUid", "expectedGid",
    "unitName", "scriptName", "socketName",
    "unitSha256", "scriptSha256",
))
MAX_FILE_BYTES = 1024 * 1024


class ServiceFixtureError(Exception):
    """Bounded error code, never arbitrary paths, bytes or identifiers."""


def _need(ok, code):
    if not ok:
        raise ServiceFixtureError(code)


def _root_fd(root):
    try:
        fd = os.open(str(root), os.O_RDONLY | os.O_DIRECTORY
                     | getattr(os, "O_NOFOLLOW", 0) | os.O_CLOEXEC)
    except OSError as exc:
        raise ServiceFixtureError("SERVICE_ROOT_UNSAFE") from exc
    st = os.fstat(fd)
    if not (stat.S_ISDIR(st.st_mode) and st.st_uid == os.geteuid()
            and (st.st_mode & 0o077) == 0):
        os.close(fd)
        raise ServiceFixtureError("SERVICE_ROOT_UNSAFE")
    return fd, st


def _file(fd_root, name, uid, gid, expected):
    try:
        fd = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                     | os.O_CLOEXEC | getattr(os, "O_NONBLOCK", 0),
                     dir_fd=fd_root)
    except OSError as exc:
        raise ServiceFixtureError("SERVICE_FILE_UNSAFE") from exc
    try:
        st = os.fstat(fd)
        _need(stat.S_ISREG(st.st_mode)
              and st.st_uid == uid and st.st_gid == gid
              and st.st_nlink == 1 and (st.st_mode & 0o077) == 0
              and 0 < st.st_size <= MAX_FILE_BYTES,
              "SERVICE_FILE_UNSAFE")
        h = hashlib.sha256()
        size = 0
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            size += len(chunk)
            _need(size <= MAX_FILE_BYTES, "SERVICE_FILE_LIMIT")
            h.update(chunk)
        final = os.fstat(fd)
        listed = os.stat(name, dir_fd=fd_root, follow_symlinks=False)
        _need((st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns)
              == (final.st_dev, final.st_ino, final.st_size,
                  final.st_mtime_ns)
              and (st.st_dev, st.st_ino) == (listed.st_dev, listed.st_ino)
              and stat.S_ISREG(listed.st_mode),
              "SERVICE_FILE_CHANGED")
        _need(h.hexdigest() == expected, "SERVICE_FILE_DIGEST_MISMATCH")
        return {"digest": h.hexdigest(), "dev": st.st_dev,
                "ino": st.st_ino, "mode": stat.S_IMODE(st.st_mode)}
    except OSError as exc:
        raise ServiceFixtureError("SERVICE_FILE_UNSAFE") from exc
    finally:
        os.close(fd)


def _socket(fd_root, name, uid, gid):
    try:
        st = os.stat(name, dir_fd=fd_root, follow_symlinks=False)
    except OSError as exc:
        raise ServiceFixtureError("SERVICE_SOCKET_UNSAFE") from exc
    _need(stat.S_ISSOCK(st.st_mode)
          and st.st_uid == uid and st.st_gid == gid
          and (st.st_mode & 0o077) == 0,
          "SERVICE_SOCKET_UNSAFE")
    return {"dev": st.st_dev, "ino": st.st_ino,
            "mode": stat.S_IMODE(st.st_mode)}


class PinnedFixtureServiceFiles:
    """Pin synthetic file inodes + bytes and recheck before test commit."""

    def __init__(self, root, policy):
        _need(type(policy) is dict and set(policy) == POLICY_KEYS
              and policy.get("origin") == "TEST_FIXTURE_ONLY",
              "SERVICE_TRUST_NOT_PROVISIONED")
        _need(type(policy["ownerId"]) is str
              and policy["ownerId"] in OWNERS
              and type(policy["expectedUid"]) is int
              and type(policy["expectedGid"]) is int
              and policy["expectedUid"] == os.geteuid()
              and policy["expectedGid"] == os.getegid()
              and all(type(policy[k]) is str and BASENAME.fullmatch(policy[k])
                      and policy[k] not in (".", "..")
                      for k in ("unitName", "scriptName", "socketName"))
              and len({policy["unitName"],policy["scriptName"],
                       policy["socketName"]}) == 3
              and all(type(policy[k]) is str and HEX.fullmatch(policy[k])
                      for k in ("unitSha256", "scriptSha256")),
              "SERVICE_POLICY_INVALID")
        _need(isinstance(root, (str, Path))
              and Path(root).is_absolute()
              and ".." not in Path(root).parts,
              "SERVICE_ROOT_UNSAFE")
        self.root = Path(root)
        self.policy = dict(policy)
        self._baseline = self._read()
        self._witness = self._fingerprint(self._baseline)

    def _read(self):
        fd, root_st = _root_fd(self.root)
        try:
            p = self.policy
            unit = _file(fd, p["unitName"], p["expectedUid"],
                         p["expectedGid"], p["unitSha256"])
            script = _file(fd, p["scriptName"], p["expectedUid"],
                           p["expectedGid"], p["scriptSha256"])
            sock = _socket(fd, p["socketName"], p["expectedUid"],
                           p["expectedGid"])
            after = os.fstat(fd)
            _need((root_st.st_dev,root_st.st_ino)
                  == (after.st_dev,after.st_ino),
                  "SERVICE_ROOT_CHANGED")
            listed_root = self.root.lstat()
            _need((root_st.st_dev,root_st.st_ino)
                  == (listed_root.st_dev,listed_root.st_ino)
                  and stat.S_ISDIR(listed_root.st_mode),
                  "SERVICE_ROOT_CHANGED")
            return {"ownerId":p["ownerId"], "uid":p["expectedUid"],
                    "gid":p["expectedGid"],
                    "root":[root_st.st_dev,root_st.st_ino],
                    "unit":unit, "script":script, "socket":sock}
        except OSError as exc:
            raise ServiceFixtureError("SERVICE_FILES_UNAVAILABLE") from exc
        finally:
            os.close(fd)

    @staticmethod
    def _fingerprint(fields):
        raw = json.dumps(fields,sort_keys=True,ensure_ascii=True,
                         separators=(",",":")).encode("ascii")
        return hashlib.sha256(raw).hexdigest()

    def check_connection(self, connected_socket):
        """Bind the pinned socket pathname to this accepted Unix socket."""
        _need(isinstance(connected_socket, socket.socket)
              and connected_socket.family == socket.AF_UNIX
              and connected_socket.type & socket.SOCK_STREAM
                    == socket.SOCK_STREAM,
              "SERVICE_SOCKET_CONNECTION_INVALID")
        try:
            address = connected_socket.getsockname()
        except OSError as exc:
            raise ServiceFixtureError("SERVICE_SOCKET_CONNECTION_INVALID") from exc
        _need(type(address) is str
              and address == str(self.root / self.policy["socketName"]),
              "SERVICE_SOCKET_CONNECTION_MISMATCH")
        return self.require_unchanged()

    def require_unchanged(self):
        now = self._read()
        _need(now == self._baseline, "SERVICE_FIXTURE_CHANGED")
        return {"state":"TEST_SERVICE_FILES_MATCHED_DENY_ONLY",
                "ownerId":self.policy["ownerId"],
                "serviceWitnessSha256":self._witness,
                "fixtureFilesMatched":True,
                "sourceServiceVerified":False,
                "sourceProcessVerified":False,
                "captureAllowed":False,
                "productionAllowed":False}
