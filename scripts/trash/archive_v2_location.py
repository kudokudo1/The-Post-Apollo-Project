#!/usr/bin/env python3
"""Private V2 archive placement shared by the read-only index and copy writer.

Quickshell's dataDir is a shared parent and often has mode 0755. SQLite must
instead live in a mode-0700 Trash++ subdirectory. This module refuses unsafe
links, owners and legacy storage; it never chmods or migrates existing files.
"""
import os
from pathlib import Path
import stat

DB_NAME = "trashpp-archive-v2.sqlite3"
PRIVATE_SUBDIR = "trashpp-private-archive-v2"
MAX_PATH = 4096


class ArchiveRootError(Exception):
    """Non-sensitive stable error code."""


def _stat(path):
    try:
        return path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ArchiveRootError("ARCHIVE_ROOT_UNAVAILABLE") from exc


def archive_directory(data_dir, *, create=False):
    """Resolve private store path; return None for an absent read-only store.

    'create' is only true after a user-confirmed, witness-checked capture.
    An existing legacy SQLite database in a private dataDir is retained as-is,
    never silently migrated or hidden by a newer empty private folder.
    """
    if (not isinstance(data_dir, (str, Path))
            or not Path(data_dir).is_absolute()
            or ".." in Path(data_dir).parts
            or "\x00" in str(data_dir)
            or len(str(data_dir)) > MAX_PATH
            or type(create) is not bool):
        raise ArchiveRootError("INVALID_ARCHIVE_ROOT")
    base = Path(data_dir)
    info = _stat(base)
    if (info is None or not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.geteuid()):
        raise ArchiveRootError("ARCHIVE_ROOT_UNSAFE")
    # A shared 0755 parent is safe for a protected child, but a directory
    # writable by another account could substitute the child pathname.
    if info.st_mode & 0o022:
        raise ArchiveRootError("ARCHIVE_PARENT_WRITABLE")
    private = base / PRIVATE_SUBDIR
    if len(str(private)) > MAX_PATH:
        raise ArchiveRootError("INVALID_ARCHIVE_ROOT")
    existing_db = _stat(base / DB_NAME)
    existing_private = _stat(private)
    if existing_db is not None:
        # A former private-root deployment must not disappear from the index.
        # If this root is shared, do not read its old DB or migrate it here.
        if info.st_mode & 0o077:
            raise ArchiveRootError("ARCHIVE_LEGACY_ROOT_UNSAFE")
        if existing_private is not None:
            raise ArchiveRootError("ARCHIVE_MULTIPLE_ROOTS")
        return base
    if existing_private is None:
        if not create:
            return None
        try:
            os.mkdir(private, 0o700)
        except FileExistsError:
            pass  # A concurrent capture may have created it.
        except OSError as exc:
            raise ArchiveRootError("ARCHIVE_PRIVATE_ROOT_CREATE_FAILED") from exc
        existing_private = _stat(private)
    if (existing_private is None
            or not stat.S_ISDIR(existing_private.st_mode)
            or existing_private.st_uid != os.geteuid()
            or existing_private.st_mode & 0o077):
        raise ArchiveRootError("ARCHIVE_PRIVATE_ROOT_UNSAFE")
    return private
