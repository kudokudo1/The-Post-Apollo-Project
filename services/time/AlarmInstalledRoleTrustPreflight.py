#!/usr/bin/env python3
"""BG1-B2B9: read-only pinned installed Clock role-origin preflight.

The independently pinned release-root fingerprint MUST come from a trusted
installer/supervisor, never an untrusted caller, socket, or signed policy.
A matching signature and program are still OBSERVATION ONLY. This module
cannot pause Quickshell, authorize writing alarms, or permit ringing.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import re
import stat
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def _load_role():
    path = Path(__file__).resolve().with_name("AlarmSignedRoleOrigin.py")
    spec = importlib.util.spec_from_file_location("clock_b2b9_role_origin", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Clock signed-role component unavailable")
    component = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = component
    spec.loader.exec_module(component)
    return component


Role = _load_role()
TRUST_DIR = Path("/usr/share/post-apollo/clock/trust-v1")
ROOT_NAME = "clock-root-ed25519-v1.pub"
FIXTURE_NAME = "bg1-installed-role-fixture"
MAX_ROOT = 32
MAX_SIG = 64
HEX = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)


class Refused(ValueError):
    """Fixed refusal code; no paths, alarm titles or private details."""


def _directory_protected(path, *, disposable):
    if not path.is_absolute() or path != Path(os.path.normpath(str(path))):
        raise Refused("TRUST_DIRECTORY_INVALID")
    if disposable:
        if path.name != FIXTURE_NAME:
            raise Refused("DISPOSABLE_TRUST_DIRECTORY_REQUIRED")
        for directory in (path.parent, path):
            try:
                st = os.lstat(directory)
            except OSError as exc:
                raise Refused("FIXTURE_TRUST_DIRECTORY_UNAVAILABLE") from exc
            if (not stat.S_ISDIR(st.st_mode)
                    or st.st_uid != os.getuid()
                    or stat.S_IMODE(st.st_mode) != 0o700):
                raise Refused("UNSAFE_DISPOSABLE_TRUST_DIRECTORY")
        return
    if path != TRUST_DIR:
        raise Refused("INSTALLED_CLOCK_TRUST_PATH_REQUIRED")
    # Validate root-owned, non-writable ancestors rather than trusting a
    # caller-specified user directory or following intermediate symlinks.
    ancestor = Path("/")
    for part in path.parts[1:]:
        ancestor = ancestor / part
        try:
            st = os.lstat(ancestor)
        except OSError as exc:
            raise Refused("INSTALLED_TRUST_DIRECTORY_UNAVAILABLE") from exc
        if (not stat.S_ISDIR(st.st_mode) or st.st_uid != 0
                or st.st_mode & 0o022):
            raise Refused("UNSAFE_INSTALLED_TRUST_ANCESTOR")


def _read_secure(path, *, max_bytes, disposable):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC |
                     getattr(os, "O_NONBLOCK", 0))
    except OSError as exc:
        raise Refused("TRUST_FILE_UNAVAILABLE_OR_LINKED") from exc
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or before.st_uid != (os.getuid() if disposable else 0)
                or before.st_mode & 0o022
                or not 1 <= before.st_size <= max_bytes):
            raise Refused("UNSAFE_CLOCK_TRUST_FILE")
        raw = os.read(fd, max_bytes + 1)
        after = os.fstat(fd)
        if (len(raw) != before.st_size or
                (before.st_dev, before.st_ino, before.st_size,
                 before.st_mtime_ns, before.st_ctime_ns) !=
                (after.st_dev, after.st_ino, after.st_size,
                 after.st_mtime_ns, after.st_ctime_ns)):
            raise Refused("TRUST_FILE_CHANGED_DURING_READ")
        return raw
    except OSError as exc:
        raise Refused("CLOCK_TRUST_READ_FAILED") from exc
    finally:
        os.close(fd)


class ClockInstalledRoleTrustPreflight:
    """Loader for independently pinned, root-protected signed Clock origins.

    This is *not* a credential issuer. It returns a deny-only B2B2 role
    observation from a real kernel AF_UNIX peer. The installed Clock root
    and policy files must already be provisioned by an approved owner.
    """

    def __init__(self, *, trust_directory, pinned_root_sha256,
                 expected_role, minimum_epoch, minimum_sequence,
                 disposable_test_mode=False):
        if (type(disposable_test_mode) is not bool
                or type(pinned_root_sha256) is not str
                or not HEX.fullmatch(pinned_root_sha256)
                or type(expected_role) is not str
                or expected_role not in Role.ROLES
                or type(minimum_epoch) is not int
                or type(minimum_sequence) is not int
                or not 1 <= minimum_epoch <= 2147483647
                or not 1 <= minimum_sequence <= 2147483647
                or not isinstance(trust_directory, (str, Path))):
            raise Refused("INDEPENDENT_CLOCK_TRUST_PIN_REQUIRED")
        self.trust = Path(trust_directory)
        self.pinned_root = pinned_root_sha256
        self.role = expected_role
        self.floor = (minimum_epoch, minimum_sequence)
        self.disposable = disposable_test_mode
        _directory_protected(self.trust, disposable=self.disposable)

    def _load_bundle(self):
        _directory_protected(self.trust, disposable=self.disposable)
        raw_root = _read_secure(self.trust / ROOT_NAME,
                                max_bytes=MAX_ROOT, disposable=self.disposable)
        if (len(raw_root) != 32 or
                hashlib.sha256(raw_root).hexdigest() != self.pinned_root):
            raise Refused("UNTRUSTED_CLOCK_RELEASE_ROOT")
        try:
            root = Ed25519PublicKey.from_public_bytes(raw_root)
        except ValueError as exc:
            raise Refused("UNTRUSTED_CLOCK_RELEASE_ROOT") from exc
        base = "clock-" + self.role + "-origin-v1"
        policy = _read_secure(self.trust / (base + ".json"),
                              max_bytes=Role.MAX_POLICY,
                              disposable=self.disposable)
        signature = _read_secure(self.trust / (base + ".sig"),
                                 max_bytes=MAX_SIG, disposable=self.disposable)
        if len(signature) != 64:
            raise Refused("WRONG_CLOCK_ROLE_SIGNATURE_SIZE")
        try:
            parsed = Role._policy(policy)
        except (Role.Refused, ValueError) as exc:
            raise Refused("INVALID_INSTALLED_CLOCK_ROLE_POLICY") from exc
        if parsed["role"] != self.role:
            raise Refused("WRONG_INSTALLED_CLOCK_ROLE")
        if ((parsed["releaseEpoch"], parsed["releaseSequence"]) <
                self.floor):
            raise Refused("CLOCK_RELEASE_FLOOR_ROLLBACK")
        try:
            root.verify(signature, Role.DOMAIN + policy)
        except Exception as exc:
            raise Refused("UNTRUSTED_CLOCK_SIGNED_ROLE") from exc
        # Enforce the existing installed executable prefix even before a
        # peer connects. Test-only artifacts are limited to fixture dirs.
        if not self.disposable:
            if not parsed["entrypointPath"].startswith(Role.PROTECTED_PREFIX):
                raise Refused("UNAPPROVED_CLOCK_ENTRYPOINT")
        else:
            if Path(parsed["entrypointPath"]).parent != self.trust.parent:
                raise Refused("UNAPPROVED_DISPOSABLE_ENTRYPOINT")
        return (root, policy, signature)

    def inspect(self, connection, peer_witness, *, expected_pid,
                expected_start_ticks):
        if (type(expected_pid) is not int or expected_pid <= 1
                or type(expected_start_ticks) is not int
                or expected_start_ticks <= 0):
            raise Refused("INDEPENDENT_PROCESS_PIN_REQUIRED")
        root, policy, signature = self._load_bundle()
        try:
            probe = Role.SignedClockRoleProbe(
                signed_policy=policy,
                policy_signature=signature,
                pinned_release_root=root,
                expected_role=self.role,
                minimum_epoch=self.floor[0],
                minimum_sequence=self.floor[1],
                expected_pid=expected_pid,
                expected_start_ticks=expected_start_ticks,
                disposable_test_mode=self.disposable)
            observed = probe.inspect(connection, peer_witness)
        except (Role.Refused, OSError, ValueError) as exc:
            raise Refused("INSTALLED_CLOCK_PROCESS_NOT_VERIFIED") from exc
        # Reject package/release changes during a running verification.
        _, after_policy, after_signature = self._load_bundle()
        if after_policy != policy or after_signature != signature:
            raise Refused("CLOCK_ROLE_POLICY_CHANGED_DURING_PROBE")
        if (observed.signature_verified is not True
                or observed.process_verified is not True
                or observed.role_authenticated is not False
                or observed.can_write_alarm_file is not False
                or observed.can_ring is not False
                or observed.can_notify is not False):
            raise Refused("CLOCK_ORIGIN_WOULD_ESCALATE_AUTHORITY")
        return {
            "originObserved": True,
            "role": observed.role,
            "releaseEpoch": observed.release_epoch,
            "releaseSequence": observed.release_sequence,
            "observedPid": observed.observed_pid,
            "rootFingerprintMatched": True,
            "signedRoleMatched": True,
            "processMatched": True,
            "fixtureOnly": self.disposable,
            "roleAuthenticated": False,
            "writerStopped": False,
            "releaseAcknowledged": False,
            "ownsRealAlarmFile": False,
            "canTransferOwnership": False,
            "canRing": False,
            "canNotify": False,
        }
