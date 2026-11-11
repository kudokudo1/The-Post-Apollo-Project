#!/usr/bin/env python3
"""MACHINE // protected destination read-only inspection, NEVER admission.

Only a separately running non-root service UID may inspect its own already
existing private archive directory, supplied out of band by a trusted
supervisor. No client paths, native host, listener, installer, source
migration, file creation, positive trust decision, or production CLI.

These are sampled filesystem observations, not trusted path custody, a
C3e live client identity, LSM/SELinux policy, independent backup, one-use
C5 human consent, or an operator-approved migration.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import MachineBraveSealedVault as vault

KIND = "machine-protected-destination-readiness-observation-v1"


class ReadinessRefusal(ValueError):
    pass


def refuse():
    raise ReadinessRefusal("MACHINE PROTECTED DESTINATION READINESS REFUSED")


def _directory_stat(info):
    if (not stat.S_ISDIR(info.st_mode)
            or os.geteuid() == 0
            or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) != 0o700):
        refuse()


def _inspect_once(fd):
    """One read-only pass of a pinned service-owned directory descriptor."""
    names = []
    try:
        with os.scandir(fd) as iterator:
            for entry in iterator:
                # No orphan, hidden/unexpected, temporary or symlink entries.
                if not entry.name.endswith(".json"):
                    refuse()
                identifier = vault._id(entry.name[:-5])
                if entry.is_symlink() or not entry.is_file(follow_symlinks=False):
                    refuse()
                names.append(identifier)
                if len(names) > vault.MAX_RECORDS:
                    refuse()
    except OSError:
        refuse()
    rows = []
    for identifier in sorted(names):
        # Descriptor-relative no-follow open, owner==effective service UID,
        # mode 0600, link count 1, bounded bytes and exact sealed schema.
        raw = vault._safe_open_file(fd, identifier + ".json")
        entry = vault._record(raw, identifier)
        rows.append({
            "record_id": identifier,
            "created_at_utc": entry["created_at_utc"],
            "sealed_bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        })
    return rows


def inspect_pinned_fd(fd):
    """Read-only observation of a trusted supervisor's existing directory FD.

    The provided descriptor must already be safely opened from a supervisor
    trusted path. The service UID cannot be root. The returned flags are
    ALWAYS negative; even a perfect POSIX snapshot grants nothing.
    """
    if type(fd) is not int or fd < 3:
        refuse()
    try:
        before = os.fstat(fd)
        _directory_stat(before)
        rows = _inspect_once(fd)
        if rows != _inspect_once(fd):
            refuse()
        after = os.fstat(fd)
        _directory_stat(after)
        if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            refuse()
    except (OSError, ValueError, TypeError, vault.VaultError):
        refuse()

    observation = {
        "kind": KIND,
        "record_count": len(rows),
        "total_sealed_bytes": sum(item["sealed_bytes"] for item in rows),
        "records": rows,
    }
    canonical = json.dumps(observation, sort_keys=True,
                           separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return {
        "status": "ci_only_protected_destination_observed",
        "observation": observation,
        "observation_sha256": hashlib.sha256(canonical).hexdigest(),
        "read_only": True,
        "path_ancestry_authenticated": False,
        "kernel_cross_uid_isolation_verified": False,
        "selinux_policy_verified": False,
        "backup_verified": False,
        "client_authenticated": False,
        "operator_consent_verified": False,
        "migration_authorized": False,
        "restore_allowed": False,
        "safe_actions": [],
    }


def inspect_trusted_path_for_fixture(target: Path):
    """CI fixture entrypoint, NOT an untrusted caller path/production command.

    Pin the actual directory inode before and after the read. It still does
    not authenticate writable ancestor paths or an installed service unit.
    """
    if (not isinstance(target, Path) or not target.is_absolute()
            or ".." in target.parts or os.geteuid() == 0):
        refuse()
    fd = -1
    try:
        expected = target.lstat()
        if not stat.S_ISDIR(expected.st_mode):
            refuse()
        fd = os.open(target, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
                     | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0))
        pinned = os.fstat(fd)
        if (expected.st_dev, expected.st_ino) != (pinned.st_dev, pinned.st_ino):
            refuse()
        result = inspect_pinned_fd(fd)
        last = target.lstat()
        if (pinned.st_dev, pinned.st_ino) != (last.st_dev, last.st_ino):
            refuse()
        return result
    except (OSError, ValueError, TypeError):
        refuse()
    finally:
        if fd >= 0:
            os.close(fd)


if __name__ == "__main__":
    # Not a callable runtime/desktop interface.
    raise SystemExit(1)
