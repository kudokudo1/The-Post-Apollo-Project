#!/usr/bin/env python3
"""BG1-B2B16: native, independently pinned V2 file sync observation.

The native supervisor can verify the actual saved V2 file's exact bytes
without exposing alarm contents. It cannot prove the old Quickshell process
has stopped/refrained from future writes or grant release/ownership/ringing.
Neither the source path nor expected digest may come from the socket request.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat

SOURCE_NAME = "time-alarms-v2.json"
DISPOSABLE_PARENT = "bg1-clock-final-v2-fixture"
MAX_FILE = 2 * 1024 * 1024
HEX = re.compile(r"^[0-9a-f]{64}$")
NO_RIGHTS = {
    "fileSyncObserved": False, "parentDirectorySyncObserved": False,
    "writerStopped": False, "releaseAcknowledged": False,
    "oldWriterRestartPrevented": False, "ownsRealAlarmFile": False,
    "canTransferOwnership": False, "canRing": False, "canNotify": False,
}


class Refused(ValueError):
    """Stable refusal without exposing the alarm source, contents or path."""


def _unique_pairs(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise Refused("DUPLICATE_V2_DOCUMENT_FIELD")
        data[key] = value
    return data


def _check_v2(raw):
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_FILE:
        raise Refused("FINAL_V2_BYTES_INVALID")
    try:
        data = json.loads(raw.decode("utf-8", "strict"),
                          object_pairs_hook=_unique_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(
                              Refused("NONFINITE_V2_NUMBER")))
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise Refused("FINAL_V2_JSON_UNREADABLE") from exc
    if (type(data) is not dict or type(data.get("version")) is not int
            or data["version"] != 2
            or type(data.get("nextId")) is not int or data["nextId"] < 1
            or type(data.get("alarms")) is not list
            or len(data["alarms"]) > 100):
        raise Refused("FINAL_V2_STRUCTURE_REFUSED")
    # Structural evidence only. The QML AlarmManagerPolicy.js owns the
    # full application-level alarm validation; no false claim here.
    seen = set()
    for row in data["alarms"]:
        if (type(row) is not dict or type(row.get("id")) is not int
                or row["id"] < 1 or row["id"] >= data["nextId"]
                or row["id"] in seen):
            raise Refused("FINAL_V2_ALARM_ID_REFUSED")
        seen.add(row["id"])
    return True


def _stat_guard(st, *, uid, directory):
    if (not (stat.S_ISDIR(st.st_mode) if directory
             else stat.S_ISREG(st.st_mode))
            or st.st_uid not in ({0, uid} if directory else {uid})
            or st.st_mode & 0o022
            or (not directory and st.st_nlink != 1)):
        raise Refused("UNSAFE_FINAL_V2_SOURCE")


def _snapshot(st):
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns,
            st.st_ctime_ns, st.st_mode, st.st_uid, st.st_nlink)


def _open_parent(parent, *, uid, synthetic):
    """Open every component with O_NOFOLLOW from /, no linked ancestor."""
    parts = parent.parts
    fd = None
    try:
        fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY |
                     os.O_CLOEXEC)
        _stat_guard(os.fstat(fd), uid=uid, directory=True)
        path = Path("/")
        for part in parts[1:]:
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY |
                          os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd)
            fd = new
            path = path/part
            st = os.fstat(fd)
            if (synthetic and path == Path("/tmp")
                    and st.st_uid == 0
                    and (st.st_mode & stat.S_ISVTX)):
                continue
            _stat_guard(st, uid=uid, directory=True)
        return fd
    except (OSError, Refused) as exc:
        if fd is not None:
            os.close(fd)
        raise Refused("UNSAFE_FINAL_V2_DIRECTORY_CHAIN") from exc


class ClockFinalV2SourceWitness:
    """Pinned read-only source witness. NO file path in the socket frame."""

    def __init__(self, *, source_path, pinned_sha256, expected_uid,
                 synthetic_only=False):
        if (type(synthetic_only) is not bool
                or type(pinned_sha256) is not str or not HEX.fullmatch(pinned_sha256)
                or type(expected_uid) is not int or expected_uid < 0
                or not isinstance(source_path, (str, Path))):
            raise Refused("INDEPENDENT_FINAL_V2_PIN_REQUIRED")
        self.source = Path(source_path)
        if (not self.source.is_absolute()
                or str(self.source) != os.path.normpath(str(self.source))
                or self.source.name != SOURCE_NAME):
            raise Refused("FINAL_V2_PATH_NOT_APPROVED")
        if synthetic_only:
            parent = self.source.parent
            if (parent.name != DISPOSABLE_PARENT
                    or parent.parent == parent
                    or os.getuid() != expected_uid):
                raise Refused("DISPOSABLE_FINAL_V2_SOURCE_REQUIRED")
            for item in (parent.parent, parent):
                try:
                    st = os.lstat(item)
                    if (not stat.S_ISDIR(st.st_mode)
                            or st.st_uid != expected_uid
                            or stat.S_IMODE(st.st_mode) != 0o700):
                        raise Refused("UNSAFE_DISPOSABLE_FINAL_V2_DIRECTORY")
                except OSError as exc:
                    raise Refused("DISPOSABLE_FINAL_V2_DIRECTORY_MISSING") from exc
        self.synthetic = synthetic_only
        self.expected_uid = expected_uid
        self.pinned_sha256 = pinned_sha256

    def observe(self):
        """fsync actual file and parent, remeasure bytes and inode/path.

        NOTE: This is only a *point-in-time* synchronized file observation.
        Concurrent writers or reboots can change the path immediately after.
        """
        directory_fd = _open_parent(self.source.parent, uid=self.expected_uid,
                                    synthetic=self.synthetic)
        file_fd = None
        try:
            file_fd = os.open(SOURCE_NAME, os.O_RDONLY | os.O_NOFOLLOW |
                              os.O_CLOEXEC | getattr(os,"O_NONBLOCK",0),
                              dir_fd=directory_fd)
            before = os.fstat(file_fd)
            _stat_guard(before, uid=self.expected_uid, directory=False)
            if not 1 <= before.st_size <= MAX_FILE:
                raise Refused("FINAL_V2_SIZE_REFUSED")
            raw = bytearray()
            while len(raw) <= MAX_FILE:
                chunk = os.read(file_fd, min(65536, MAX_FILE+1-len(raw)))
                if not chunk:
                    break
                raw.extend(chunk)
            if len(raw) != before.st_size:
                raise Refused("FINAL_V2_LENGTH_CHANGED")
            raw = bytes(raw)
            _check_v2(raw)
            if hashlib.sha256(raw).hexdigest() != self.pinned_sha256:
                raise Refused("FINAL_V2_DIGEST_MISMATCH")
            # A file's onSaved callback alone is not a durability witness.
            # This actual Linux sync rejects on EIO/EROFS/etc; it does not
            # yield exclusive ownership of the source path.
            os.fsync(file_fd)
            os.fsync(directory_fd)
            post_sync = os.fstat(file_fd)
            os.lseek(file_fd, 0, os.SEEK_SET)
            again = bytearray()
            while len(again) <= MAX_FILE:
                chunk = os.read(file_fd, min(65536, MAX_FILE+1-len(again)))
                if not chunk:
                    break
                again.extend(chunk)
            by_path = os.stat(SOURCE_NAME, dir_fd=directory_fd,
                              follow_symlinks=False)
            if (_snapshot(before) != _snapshot(post_sync)
                    or _snapshot(before) != _snapshot(by_path)
                    or bytes(again) != raw):
                raise Refused("FINAL_V2_CHANGED_DURING_SYNC")
            # A held dirfd still points to the OLD directory after an
            # attacker renames its absolute path. Reopen the approved
            # full path to prove the source directory itself was not
            # swapped during our sync snapshot.
            renewed_fd = None
            try:
                renewed_fd = _open_parent(
                    self.source.parent, uid=self.expected_uid,
                    synthetic=self.synthetic)
                old_parent = os.fstat(directory_fd)
                new_parent = os.fstat(renewed_fd)
                if ((old_parent.st_dev, old_parent.st_ino) !=
                        (new_parent.st_dev, new_parent.st_ino)):
                    raise Refused("FINAL_V2_DIRECTORY_REPLACED")
            finally:
                if renewed_fd is not None:
                    os.close(renewed_fd)
            return {
                "finalV2RevisionObserved": True,
                "sourceDigestMatched": True,
                "fileSyncObserved": True,
                "parentDirectorySyncObserved": True,
                "fixtureOnly": self.synthetic,
                "sourceExclusive": False,
                "finalRevisionDurablyLocked": False,
                **{key: value for key, value in NO_RIGHTS.items()
                   if key not in ("fileSyncObserved",
                                  "parentDirectorySyncObserved")},
            }
        except OSError as exc:
            raise Refused("FINAL_V2_SYNC_OR_READ_REFUSED") from exc
        finally:
            if file_fd is not None:
                os.close(file_fd)
            os.close(directory_fd)
