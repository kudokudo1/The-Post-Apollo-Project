#!/usr/bin/env python3
"""Clock BG1-B2B2 experimental signed process-origin observation.

This is a DENY-ONLY supplement, not an owner authenticator. It uses an
independently pinned Ed25519 release key and independently witnessed PID/start
to compare signed *Clock-specific* policy to a pinned AF_UNIX kernel pidfd peer.
Even a perfect match has NO authority to write alarms, ring or notify.

Identity Center's signed gateway is purpose-separated and is not a Clock
signing authority. This code does not enroll, sign, fetch, install or actuate.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def _load_peer():
    target = Path(__file__).resolve().with_name("AlarmPeerIdentity.py")
    spec = importlib.util.spec_from_file_location("alarm_peer_origin", target)
    if spec is None or spec.loader is None:
        raise RuntimeError("Missing bundled Clock peer identity")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_Peer = _load_peer()
SCHEMA = "postapollo.clock.bg1-b2b2-signed-role-origin.experimental-v1"
PURPOSE = "postapollo.clock.alarm-role-origin.observe-only"
DOMAIN = b"postapollo.clock.bg1-b2b2-signed-role-origin.experimental-v1\x00"
ROLES = frozenset(("clock-ui-bridge", "clock-background-worker"))
FIELDS = frozenset((
    "schema", "purpose", "role", "releaseEpoch", "releaseSequence",
    "entrypointPath", "entrypointSha256", "interpreterPath",
    "argv", "uid", "gid",
))
HEX = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
MAX_POLICY = 3072
MAX_ENTRY = 1024 * 1024
MAX_CMD = 4096
PROTECTED_PREFIX = "/usr/libexec/post-apollo/clock/"


class Refused(ValueError):
    """Trusted inputs, file evidence or kernel-origin evidence did not match."""


@dataclass(frozen=True, slots=True)
class ClockRoleOriginObservation:
    role: str
    release_epoch: int
    release_sequence: int
    observed_pid: int
    signature_verified: bool
    process_verified: bool
    # This is intentionally not a grant, even for an installed signed host.
    role_authenticated: bool = False
    can_write_alarm_file: bool = False
    can_ring: bool = False
    can_notify: bool = False


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Refused("DUPLICATE_SIGNED_FIELD")
        result[key] = value
    return result


def canonical(policy):
    return json.dumps(policy, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _policy(raw):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_POLICY:
        raise Refused("SIGNED_POLICY_SIZE")
    try:
        policy = json.loads(raw.decode("utf-8", "strict"),
                            object_pairs_hook=_unique_pairs,
                            parse_constant=lambda _: (_ for _ in ()).throw(
                                Refused("NONFINITE_SIGNED_VALUE")))
    except (ValueError, UnicodeError, TypeError, RecursionError) as exc:
        raise Refused("SIGNED_POLICY_JSON") from exc
    if type(policy) is not dict or set(policy) != FIELDS:
        raise Refused("SIGNED_POLICY_FIELDS")
    if canonical(policy) != raw:
        raise Refused("NONCANONICAL_SIGNED_POLICY")
    if (policy["schema"] != SCHEMA or policy["purpose"] != PURPOSE
            or policy["role"] not in ROLES
            or type(policy["releaseEpoch"]) is not int
            or type(policy["releaseSequence"]) is not int
            or not 1 <= policy["releaseEpoch"] <= 2147483647
            or not 1 <= policy["releaseSequence"] <= 2147483647
            or type(policy["uid"]) is not int
            or type(policy["gid"]) is not int
            or not 0 <= policy["uid"] <= 2**32 - 1
            or not 0 <= policy["gid"] <= 2**32 - 1
            or type(policy["entrypointSha256"]) is not str
            or not HEX.fullmatch(policy["entrypointSha256"])):
        raise Refused("SIGNED_POLICY_IDENTITY")
    for key in ("entrypointPath", "interpreterPath"):
        path = policy[key]
        if (type(path) is not str or not path.startswith("/")
                or "\x00" in path or "//" in path
                or "/./" in path or "/../" in path
                or path.endswith(("/.", "/.."))):
            raise Refused("SIGNED_PATH_INVALID")
    argv = policy["argv"]
    if (type(argv) is not list or not 4 <= len(argv) <= 6
            or any(type(x) is not str or not x or "\x00" in x or len(x) > 1024
                   for x in argv)
            or argv[:4] != [policy["interpreterPath"], "-I", "-B",
                            policy["entrypointPath"]]):
        raise Refused("SIGNED_ARGV_INVALID")
    return policy


def _entrypoint_digest(path, *, disposable, uid):
    if not disposable and not str(path).startswith(PROTECTED_PREFIX):
        raise Refused("UNAPPROVED_INSTALL_PREFIX")
    if not disposable:
        ancestor = path.parent
        while True:
            try:
                info = os.lstat(ancestor)
            except OSError as exc:
                raise Refused("UNVERIFIED_INSTALL_ANCESTOR") from exc
            if (not stat.S_ISDIR(info.st_mode) or info.st_uid != 0
                    or stat.S_IMODE(info.st_mode) & 0o022):
                raise Refused("UNSAFE_INSTALL_ANCESTOR")
            if ancestor == Path("/"):
                break
            ancestor = ancestor.parent
    fd = None
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        before = os.fstat(fd)
        expected_owner = uid if disposable else 0
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != expected_owner
                or before.st_nlink != 1
                or stat.S_IMODE(before.st_mode) & 0o022
                or not 1 <= before.st_size <= MAX_ENTRY
                or (not disposable and stat.S_IMODE(before.st_mode) != 0o555)):
            raise Refused("UNSAFE_ENTRYPOINT")
        raw = bytearray()
        while len(raw) <= MAX_ENTRY:
            block = os.read(fd, min(65536, MAX_ENTRY + 1 - len(raw)))
            if not block:
                break
            raw.extend(block)
        after = os.fstat(fd)
        if (len(raw) != before.st_size
                or len(raw) > MAX_ENTRY
                or (before.st_dev, before.st_ino, before.st_size,
                    before.st_mtime_ns, before.st_ctime_ns) !=
                   (after.st_dev, after.st_ino, after.st_size,
                    after.st_mtime_ns, after.st_ctime_ns)):
            raise Refused("ENTRYPOINT_CHANGED")
        return hashlib.sha256(raw).hexdigest()
    except OSError as exc:
        raise Refused("ENTRYPOINT_UNREADABLE") from exc
    finally:
        if fd is not None:
            os.close(fd)


class SignedClockRoleProbe:
    """Observe a role-bound signed executable. NEVER authorize role takeover."""

    def __init__(self, *, signed_policy, policy_signature,
                 pinned_release_root, expected_role,
                 minimum_epoch, minimum_sequence,
                 expected_pid, expected_start_ticks,
                 disposable_test_mode=False):
        if (not isinstance(pinned_release_root, Ed25519PublicKey)
                or type(policy_signature) is not bytes
                or len(policy_signature) != 64
                or expected_role not in ROLES
                or type(minimum_epoch) is not int or minimum_epoch < 1
                or type(minimum_sequence) is not int or minimum_sequence < 1
                or type(expected_pid) is not int or expected_pid <= 1
                or type(expected_start_ticks) is not int
                or expected_start_ticks <= 0
                or type(disposable_test_mode) is not bool):
            raise Refused("INDEPENDENT_ROLE_PINS_REQUIRED")
        policy = _policy(signed_policy)
        if policy["role"] != expected_role:
            raise Refused("WRONG_SIGNED_CLOCK_ROLE")
        if ((policy["releaseEpoch"], policy["releaseSequence"])
                < (minimum_epoch, minimum_sequence)):
            raise Refused("SIGNED_RELEASE_ROLLBACK")
        try:
            pinned_release_root.verify(policy_signature,
                                       DOMAIN + signed_policy)
        except InvalidSignature as exc:
            raise Refused("UNTRUSTED_RELEASE_SIGNATURE") from exc
        self._policy = policy
        self._expected_pid = expected_pid
        self._expected_ticks = expected_start_ticks
        self._disposable = disposable_test_mode

    def inspect(self, accepted_socket, peer_witness):
        """Read-only observation; caller owns and must close peer_witness."""
        policy = self._policy
        if (not isinstance(peer_witness, dict)
                or peer_witness.get("pid") != self._expected_pid
                or peer_witness.get("ticks") != self._expected_ticks
                or peer_witness.get("uid") != policy["uid"]
                or peer_witness.get("gid") != policy["gid"]):
            raise Refused("INDEPENDENT_PROCESS_WITNESS_MISMATCH")
        try:
            _Peer.verify(accepted_socket, peer_witness,
                         policy["interpreterPath"])
        except _Peer.Refused as exc:
            raise Refused("KERNEL_PEER_UNVERIFIED") from exc
        pid = self._expected_pid
        try:
            expected_exe = os.stat(policy["interpreterPath"])
            live_exe = os.stat(f"/proc/{pid}/exe")
            raw_cmd = Path(f"/proc/{pid}/cmdline").read_bytes()
        except OSError as exc:
            raise Refused("RUNNING_PROGRAM_UNAVAILABLE") from exc
        if (expected_exe.st_dev, expected_exe.st_ino) != (
                live_exe.st_dev, live_exe.st_ino):
            raise Refused("WRONG_INTERPRETER_INODE")
        if (not 0 < len(raw_cmd) <= MAX_CMD or not raw_cmd.endswith(b"\x00")
                or [os.fsdecode(a) for a in raw_cmd[:-1].split(b"\x00")]
                    != policy["argv"]):
            raise Refused("UNENROLLED_PROCESS_ARGV")
        digest = _entrypoint_digest(Path(policy["entrypointPath"]),
                                    disposable=self._disposable,
                                    uid=policy["uid"])
        if digest != policy["entrypointSha256"]:
            raise Refused("SIGNED_ENTRYPOINT_DIGEST_MISMATCH")
        if Path(f"/proc/{pid}/cmdline").read_bytes() != raw_cmd:
            raise Refused("PROCESS_CHANGED_WHILE_MEASURING")
        try:
            _Peer.verify(accepted_socket, peer_witness,
                         policy["interpreterPath"])
        except _Peer.Refused as exc:
            raise Refused("KERNEL_PEER_CHANGED_WHILE_MEASURING") from exc
        return ClockRoleOriginObservation(
            role=policy["role"],
            release_epoch=policy["releaseEpoch"],
            release_sequence=policy["releaseSequence"],
            observed_pid=pid,
            signature_verified=True,
            process_verified=True,
        )

    def consistent(self, accepted_socket, peer_witness):
        try:
            result = self.inspect(accepted_socket, peer_witness)
            return result.signature_verified and result.process_verified
        except (Refused, ValueError, OSError):
            return False
