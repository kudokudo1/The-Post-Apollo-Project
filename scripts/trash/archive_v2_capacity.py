#!/usr/bin/env python3
"""Trash++ V2h disk-footprint accounting; no SQLite writes or cleanup verbs.

The Archive has a fixed budget for its main SQLite file and DELETE-mode
rollback journal. Budget checks charge the greater of logical and allocated
bytes. The SQLite main-file page limit is enforced separately by the writer.
"""
import os
from pathlib import Path
import stat

DB_NAME = "trashpp-archive-v2.sqlite3"
DEFAULT_DISK_QUOTA = 768 * 1024 * 1024
MIN_DISK_QUOTA = 64 * 1024
MAX_DISK_QUOTA = 2 ** 40


class CapacityError(Exception):
    """Stable refusal code, never source data or user paths."""


def capacity(root, disk_quota=DEFAULT_DISK_QUOTA):
    if (not isinstance(root, (str, Path)) or not Path(root).is_absolute()
            or type(disk_quota) is not int
            or not MIN_DISK_QUOTA <= disk_quota <= MAX_DISK_QUOTA):
        raise CapacityError("INVALID_ARCHIVE_CAPACITY")
    path = Path(root)
    try:
        owner = path.lstat()
    except OSError as exc:
        raise CapacityError("ARCHIVE_ROOT_UNAVAILABLE") from exc
    if (not stat.S_ISDIR(owner.st_mode) or owner.st_uid != os.geteuid()
            or owner.st_mode & 0o077):
        raise CapacityError("ARCHIVE_ROOT_UNSAFE")
    logical = allocated = 0
    sizes = {}
    for suffix in ("", "-journal"):
        target = path / (DB_NAME + suffix)
        try:
            entry = target.lstat()
        except FileNotFoundError:
            sizes[suffix] = 0
            continue
        except OSError as exc:
            raise CapacityError("ARCHIVE_CAPACITY_UNAVAILABLE") from exc
        if (not stat.S_ISREG(entry.st_mode) or entry.st_uid != os.geteuid()
                or entry.st_nlink != 1
                or (suffix == "" and entry.st_mode & 0o077)):
            raise CapacityError("ARCHIVE_FILE_UNSAFE")
        sizes[suffix] = entry.st_size
        logical += entry.st_size
        allocated += entry.st_blocks * 512
    # Refuse SQLite journaling-mode drift rather than underreporting unknown
    # WAL or shared-memory files. This is the same policy as ArchiveStore.
    for suffix in ("-wal", "-shm"):
        try:
            (path / (DB_NAME + suffix)).lstat()
        except FileNotFoundError:
            continue
        raise CapacityError("ARCHIVE_UNEXPECTED_SIDECAR")
    try:
        fs = os.statvfs(path)
    except OSError as exc:
        raise CapacityError("ARCHIVE_CAPACITY_UNAVAILABLE") from exc
    charged = max(logical, allocated)
    return {
        "databaseBytes": sizes[""],
        "journalBytes": sizes["-journal"],
        "logicalBytes": logical,
        "allocatedBytes": allocated,
        "chargedBytes": charged,
        "diskQuotaBytes": disk_quota,
        "remainingBytes": max(0, disk_quota - charged),
        "filesystemAvailableBytes": fs.f_bavail * fs.f_frsize,
        "capacityState": "FULL" if charged >= disk_quota else "READY",
    }
