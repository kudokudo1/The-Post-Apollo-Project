#!/usr/bin/env python3
"""Clock BG1-B2B12: protected signed session-enrollment READ-ONLY observer.

This verifies a controller-signed, exact-boot/exact-process enrollment using
the B2B9 independently pinned installed Clock role root. It NEVER authorizes
pause, ownership transfer, FileView writes, scheduling, ringing or notification.
No production enrollment key/pin/floor is installed by this module.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import uuid

from cryptography.exceptions import InvalidSignature


def _load_origin():
    path=Path(__file__).resolve().with_name("AlarmInstalledRoleTrustPreflight.py")
    spec=importlib.util.spec_from_file_location("clock_b2b12_origin",path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Clock installed verifier missing")
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module


Origin=_load_origin()
Peer=Origin.Role._Peer
INSTALL_ENROLLMENT_DIR=Path("/run/post-apollo/clock/sessions-v1")
TEST_ENROLLMENT_NAME="bg1-protected-session-fixture"
SESSION_FILE="clock-ui-bridge-session-v1.json"
SIGNATURE_FILE="clock-ui-bridge-session-v1.sig"
SCHEMA="postapollo.clock.bg1.installed-session.v1"
PURPOSE="postapollo.clock.bg1.supervisor-enrollment.v1"
DOMAIN=b"postapollo.clock.bg1.supervisor-enrollment.v1\x00"
SOCKET_SCOPE="post-apollo-clock/clock-supervisor-v1.sock"
MAX_ENROLLMENT=2048
MAX_EPOCH=2147483647
EXPECTED_FIELDS=frozenset((
    "schema","purpose","role","bootId","pid","startTicks","uid","gid",
    "releaseEpoch","releaseSequence","socketScope"
))
NO_AUTHORITY={
    "roleAuthenticated":False,
    "writerStopped":False,
    "releaseAcknowledged":False,
    "oldWriterRestartPrevented":False,
    "ownsRealAlarmFile":False,
    "canTransferOwnership":False,
    "canRing":False,
    "canNotify":False,
}


class Refused(ValueError):
    """No paths, notes, alarm contents, secrets or signed data in errors."""


def _unique_pairs(pairs):
    obj={}
    for k,v in pairs:
        if k in obj:
            raise Refused("DUPLICATE_CLOCK_SESSION_FIELD")
        obj[k]=v
    return obj


def canonical(data):
    if type(data) is not dict:
        raise Refused("INVALID_SIGNED_SESSION_SHAPE")
    try:
        return json.dumps(data,sort_keys=True,separators=(",",":"),
                          ensure_ascii=True,allow_nan=False).encode("ascii")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise Refused("INVALID_SIGNED_SESSION_ENCODING") from exc


def _manifest(raw):
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_ENROLLMENT:
        raise Refused("SIGNED_SESSION_LENGTH_REFUSED")
    try:
        data=json.loads(raw.decode("ascii"),object_pairs_hook=_unique_pairs,
                        parse_constant=lambda _:
                            (_ for _ in ()).throw(
                                Refused("NONFINITE_SIGNED_SESSION")))
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise Refused("INVALID_SIGNED_SESSION_JSON") from exc
    if (type(data) is not dict or set(data)!=EXPECTED_FIELDS
            or canonical(data)!=raw
            or data["schema"]!=SCHEMA or data["purpose"]!=PURPOSE
            or data["role"]!="clock-ui-bridge"
            or data["socketScope"]!=SOCKET_SCOPE
            or any(type(data[k]) is not int for k in (
                "pid","startTicks","uid","gid","releaseEpoch",
                "releaseSequence"))
            or data["pid"]<=1 or data["startTicks"]<=0
            or data["uid"]<0 or data["gid"]<0
            or not 1<=data["releaseEpoch"]<=MAX_EPOCH
            or not 1<=data["releaseSequence"]<=MAX_EPOCH
            or type(data["bootId"]) is not str):
        raise Refused("INVALID_SIGNED_SESSION_POLICY")
    try:
        if data["bootId"]!=str(uuid.UUID(data["bootId"])):
            raise ValueError("noncanonical boot ID")
    except (ValueError, AttributeError) as exc:
        raise Refused("INVALID_SIGNED_SESSION_BOOT_ID") from exc
    return data


def _kernel_boot():
    try:
        value=Path("/proc/sys/kernel/random/boot_id").read_text(
            encoding="ascii").strip()
        if value!=str(uuid.UUID(value)):
            raise ValueError("noncanonical")
        return value
    except (OSError, ValueError, UnicodeError) as exc:
        raise Refused("KERNEL_BOOT_UNVERIFIED") from exc


def _protected_dir(path, *, disposable):
    if not path.is_absolute() or str(path)!=os.path.normpath(str(path)):
        raise Refused("SIGNED_SESSION_DIRECTORY_INVALID")
    if disposable:
        if path.name!=TEST_ENROLLMENT_NAME:
            raise Refused("DISPOSABLE_SESSION_DIRECTORY_REQUIRED")
        for ancestor in (path.parent,path):
            try:
                st=os.lstat(ancestor)
            except OSError as exc:
                raise Refused("DISPOSABLE_SESSION_DIRECTORY_MISSING") from exc
            if (not stat.S_ISDIR(st.st_mode) or st.st_uid!=os.getuid()
                    or stat.S_IMODE(st.st_mode)!=0o700):
                raise Refused("UNSAFE_DISPOSABLE_SESSION_DIRECTORY")
        return
    if path!=INSTALL_ENROLLMENT_DIR:
        raise Refused("PROTECTED_SESSION_DIRECTORY_REQUIRED")
    ancestor=Path("/")
    for part in path.parts[1:]:
        ancestor=ancestor/part
        try:
            st=os.lstat(ancestor)
        except OSError as exc:
            raise Refused("PROTECTED_SESSION_DIRECTORY_MISSING") from exc
        if (not stat.S_ISDIR(st.st_mode) or st.st_uid!=0
                or st.st_mode & 0o022):
            raise Refused("UNSAFE_PROTECTED_SESSION_DIRECTORY")


def _read_file(path, *, length, disposable):
    fd=None
    try:
        fd=os.open(path,os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
                   | getattr(os,"O_NONBLOCK",0))
        original=os.fstat(fd)
        if (not stat.S_ISREG(original.st_mode)
                or original.st_nlink!=1
                or original.st_uid!=(os.getuid() if disposable else 0)
                or original.st_mode & 0o022
                or not 1<=original.st_size<=length):
            raise Refused("UNSAFE_SIGNED_SESSION_FILE")
        result=os.read(fd,length+1)
        after=os.fstat(fd)
        if (len(result)!=original.st_size
                or (original.st_dev,original.st_ino,original.st_size,
                    original.st_mtime_ns,original.st_ctime_ns)!=
                   (after.st_dev,after.st_ino,after.st_size,
                    after.st_mtime_ns,after.st_ctime_ns)):
            raise Refused("SIGNED_SESSION_CHANGED_DURING_READ")
        return result
    except OSError as exc:
        raise Refused("SIGNED_SESSION_UNAVAILABLE_OR_LINKED") from exc
    finally:
        if fd is not None:
            os.close(fd)


class ClockProtectedSessionEnrollment:
    """Read-only signed enrollment for one real AF_UNIX connected old writer.

    Production paths are FIXED. The root pin and release floor must be
    independently chosen by a protected package/supervisor; they are never
    accepted over the request socket. Even a fully valid result is deny-only.
    """

    def __init__(self, *, enrollment_directory, trust_directory,
                 pinned_root_sha256, minimum_epoch, minimum_sequence,
                 synthetic_only=False):
        if (type(synthetic_only) is not bool
                or type(minimum_epoch) is not int
                or type(minimum_sequence) is not int
                or not 1<=minimum_epoch<=MAX_EPOCH
                or not 1<=minimum_sequence<=MAX_EPOCH):
            raise Refused("INDEPENDENT_CLOCK_RELEASE_FLOOR_REQUIRED")
        self.synthetic=synthetic_only
        self.path=Path(enrollment_directory)
        self.origin=Origin.ClockInstalledRoleTrustPreflight(
            trust_directory=trust_directory,
            pinned_root_sha256=pinned_root_sha256,
            expected_role="clock-ui-bridge",
            minimum_epoch=minimum_epoch,
            minimum_sequence=minimum_sequence,
            disposable_test_mode=synthetic_only)
        self.floor=(minimum_epoch,minimum_sequence)
        _protected_dir(self.path,disposable=synthetic_only)
        if self.synthetic:
            if self.path.parent!=self.origin.trust.parent:
                raise Refused("DISPOSABLE_TRUST_AND_SESSION_SCOPE_MISMATCH")

    def _load(self):
        _protected_dir(self.path,disposable=self.synthetic)
        try:
            root,policy_raw,policy_sig=self.origin._load_bundle()
            signed_policy=Origin.Role._policy(policy_raw)
        except (Origin.Refused,Origin.Role.Refused,
                OSError,ValueError) as exc:
            raise Refused("CLOCK_ROLE_TRUST_NOT_VERIFIED") from exc
        manifest_raw=_read_file(self.path/SESSION_FILE,
                                length=MAX_ENROLLMENT,
                                disposable=self.synthetic)
        sig=_read_file(self.path/SIGNATURE_FILE,length=64,
                       disposable=self.synthetic)
        if len(sig)!=64:
            raise Refused("WRONG_SIGNED_SESSION_SIGNATURE_SIZE")
        try:
            root.verify(sig,DOMAIN+manifest_raw)
        except InvalidSignature as exc:
            raise Refused("WRONG_CLOCK_SESSION_SIGNATURE") from exc
        data=_manifest(manifest_raw)
        if data["bootId"]!=_kernel_boot():
            raise Refused("SIGNED_SESSION_PREVIOUS_BOOT")
        if ((data["releaseEpoch"],data["releaseSequence"])<
                self.floor):
            raise Refused("SIGNED_SESSION_RELEASE_DOWNGRADE")
        if (data["releaseEpoch"],data["releaseSequence"])!=(
                signed_policy["releaseEpoch"],
                signed_policy["releaseSequence"]):
            raise Refused("SESSION_AND_INSTALLED_ROLE_RELEASE_DIFFER")
        if (data["uid"],data["gid"])!=(
                signed_policy["uid"],signed_policy["gid"]):
            raise Refused("SESSION_AND_ROLE_CREDENTIALS_DIFFER")
        return data,(manifest_raw,sig,policy_raw,policy_sig)

    def inspect(self, connection):
        data,bundle=self._load()
        witness=None
        try:
            # Actual kernel peer is captured from this exact socket, not
            # by opening the PID reported in the enrollment manifest.
            try:
                role=Origin.Role._policy(bundle[2])
                witness=Peer.capture(connection,role["interpreterPath"])
            except (Peer.Refused,Origin.Role.Refused,
                    ValueError,OSError) as exc:
                raise Refused("SIGNED_SESSION_KERNEL_PEER_REFUSED") from exc
            if (witness["pid"],witness["ticks"],witness["uid"],witness["gid"])!=(
                    data["pid"],data["startTicks"],
                    data["uid"],data["gid"]):
                raise Refused("SIGNED_SESSION_AND_KERNEL_PEER_DIFFER")
            try:
                observed=self.origin.inspect(
                    connection,witness,
                    expected_pid=data["pid"],
                    expected_start_ticks=data["startTicks"])
            except (Origin.Refused,ValueError,OSError) as exc:
                raise Refused("SIGNED_SESSION_PROCESS_ORIGIN_REFUSED") from exc
            if (observed["originObserved"] is not True
                    or observed["releaseEpoch"]!=data["releaseEpoch"]
                    or observed["releaseSequence"]!=data["releaseSequence"]
                    or observed["roleAuthenticated"] is not False
                    or observed["canTransferOwnership"] is not False
                    or observed["canRing"] is not False):
                raise Refused("CLOCK_SESSION_WOULD_ESCALATE_AUTHORITY")
            _,after=self._load()
            if after!=bundle:
                raise Refused("SIGNED_SESSION_BUNDLE_CHANGED")
            try:
                Peer.verify(connection,witness,role["interpreterPath"])
            except Peer.Refused as exc:
                raise Refused("SIGNED_SESSION_PEER_LIFETIME_CHANGED") from exc
            return dict({
                "originObserved":True,
                "signedSessionObserved":True,
                "sameKernelPeer":True,
                "sameReleaseEpoch":True,
                "fixtureOnly":self.synthetic,
                "bootMatched":True,
            },**NO_AUTHORITY)
        finally:
            if witness is not None:
                Peer.close(witness)
