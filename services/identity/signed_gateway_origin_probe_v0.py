"""Identity Center gateway signed-enrollment + live Linux process probe, v0.

This is read-only evidence, NOT production authentication or an authorization
decision. A separately pinned release authority signs a purpose-bound manifest
for the exact Identity Center script digest AND Ed25519 receipt public key.
The probe corroborates a separately pinned PID/start with Linux /proc.

Passing means "measured process matches these independent inputs", NOT:
  - signed/installed RPM or Silverblue boot and supervised systemd identity
  - immutable Python modules or runtime memory
  - logind/compositor lock state, C5 one-use consent, hardware key custody
  - any permission for CPU++, providers, organization switching or QML login

The production process and release/witness pins must be provided by an
INDEPENDENT C3e/C4b authority, never received from the command socket.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
from dataclasses import dataclass
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from desktop_command_gateway_v0 import KernelPeer

SCHEMA = "post-apollo.identity.gateway-enrollment.experimental-v0"
PURPOSE = "post-apollo.identity.native-command-gateway.v0"
_DOMAIN = b"post-apollo.identity.gateway-enrollment.experimental-v0\x00"
_DIGEST = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_TICKS = re.compile(r"[1-9][0-9]{0,19}\Z", re.ASCII)
_KEYS = frozenset((
    "schema", "purpose", "releaseEpoch", "releaseSequence",
    "entrypointPath", "entrypointSha256", "interpreterPath",
    "receiptKeySha256", "uid", "gid",
))
_MAX_POLICY = 2048
_MAX_SCRIPT = 1024 * 1024
_MAX_CMD = 4096


class OriginRefused(ValueError):
    """Measured host or signed release did not satisfy the expected pins."""


@dataclass(frozen=True, slots=True)
class GatewayOriginObservation:
    """Bounded read-only result. NEVER a login or credential grant."""
    process_matches_enrollment: bool
    signer_matches_enrollment: bool
    observed_pid: int
    observed_start_ticks: str
    production_authority: bool = False
    can_begin_sign_in: bool = False
    can_connect_provider: bool = False


def _pairs_unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise OriginRefused("Duplicate policy field")
        out[key] = value
    return out


def canonical(policy: dict[str, Any]) -> bytes:
    """Canonical policy bytes. This is a signing format, not a trust source."""
    return json.dumps(policy, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii")


def _policy(raw: bytes) -> dict[str, Any]:
    if type(raw) is not bytes or not 0 < len(raw) <= _MAX_POLICY:
        raise OriginRefused("Invalid enrollment size")
    try:
        result = json.loads(raw.decode("utf-8", errors="strict"),
                            object_pairs_hook=_pairs_unique,
                            parse_constant=lambda _: (_ for _ in ()).throw(
                                OriginRefused("Nonfinite policy value")))
        if type(result) is not dict or set(result) != _KEYS:
            raise OriginRefused("Wrong enrollment fields")
        if canonical(result) != raw:
            raise OriginRefused("Noncanonical signed policy")
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        raise OriginRefused("Invalid signed enrollment") from exc
    if (result["schema"] != SCHEMA or result["purpose"] != PURPOSE
            or type(result["releaseEpoch"]) is not int
            or type(result["releaseSequence"]) is not int
            or not 1 <= result["releaseEpoch"] <= 2**31
            or not 1 <= result["releaseSequence"] <= 2**31
            or type(result["uid"]) is not int
            or type(result["gid"]) is not int
            or not 0 <= result["uid"] <= 2**32 - 1
            or not 0 <= result["gid"] <= 2**32 - 1
            or type(result["entrypointSha256"]) is not str
            or _DIGEST.fullmatch(result["entrypointSha256"]) is None
            or type(result["receiptKeySha256"]) is not str
            or _DIGEST.fullmatch(result["receiptKeySha256"]) is None):
        raise OriginRefused("Invalid enrolled release/identity")
    for field in ("entrypointPath", "interpreterPath"):
        value = result[field]
        if (type(value) is not str or not value.startswith("/")
                or "\x00" in value or "//" in value or "/./" in value
                or "/../" in value or value.endswith(("/.", "/.."))):
            raise OriginRefused("Invalid installed path pin")
    return result


def _start_ticks(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        # PID's comm is parenthesized and may contain spaces or ')' itself.
        # Index 19 after the *last* ') ' is stat field 22 (starttime).
        fields = raw.rsplit(") ", 1)[1].split()
        ticks = fields[19]
        if _TICKS.fullmatch(ticks) is None:
            raise OriginRefused("Invalid kernel process start")
        return ticks
    except (OSError, IndexError, ValueError) as e:
        raise OriginRefused("No stable kernel process start") from e


def _kernel_uid_gid(pid: int, uid: int, gid: int) -> None:
    try:
        fields = {}
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith(("Uid:", "Gid:")):
                name, rest = line.split(":", 1)
                fields[name] = [int(x) for x in rest.split()]
        if (fields.get("Uid") != [uid] * 4
                or fields.get("Gid") != [gid] * 4):
            raise OriginRefused("Process kernel UID/GID changed")
    except (OSError, ValueError) as e:
        raise OriginRefused("Kernel UID/GID unavailable") from e


def _safe_script_digest(path: Path, *, disposable: bool, expected_uid: int) -> str:
    # An installed, immutable entrypoint is root-owned, non-writable to
    # group/others, and lives below the specifically approved identity prefix.
    # Disposable CI uses an unprivileged scratch script for negative testing.
    if not disposable and not str(path).startswith(
            "/usr/libexec/post-apollo/identity/"):
        raise OriginRefused("Not the enrolled Identity Center install path")
    if not disposable:
        current = path.parent
        while True:
            st = os.lstat(current)
            if (not stat.S_ISDIR(st.st_mode) or st.st_uid != 0
                    or stat.S_IMODE(st.st_mode) & 0o022):
                raise OriginRefused("Unsafe installed script ancestor")
            if current == Path("/"):
                break
            current = current.parent
    fd = None
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        before = os.fstat(fd)
        owner = expected_uid if disposable else 0
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != owner
                or before.st_nlink != 1
                or (stat.S_IMODE(before.st_mode) & 0o022) != 0
                or (not disposable and stat.S_IMODE(before.st_mode) != 0o555)
                or not 1 <= before.st_size <= _MAX_SCRIPT):
            raise OriginRefused("Unsafe installed script bytes")
        digest = hashlib.sha256()
        n = 0
        while True:
            block = os.read(fd, min(65536, _MAX_SCRIPT + 1 - n))
            if not block:
                break
            n += len(block)
            if n > _MAX_SCRIPT:
                raise OriginRefused("Script size exceeded")
            digest.update(block)
        after = os.fstat(fd)
        if (n != before.st_size
                or (before.st_dev, before.st_ino, before.st_size,
                    before.st_mtime_ns, before.st_ctime_ns) !=
                   (after.st_dev, after.st_ino, after.st_size,
                    after.st_mtime_ns, after.st_ctime_ns)):
            raise OriginRefused("Script changed while observing")
        return digest.hexdigest()
    except OSError as e:
        raise OriginRefused("Installed script unavailable") from e
    finally:
        if fd is not None:
            os.close(fd)


class SignedGatewayOriginProbe:
    """Real Linux process corroboration against externally pinned release.

    expected_pid and expected_start_ticks must be learned from an independent
    protected witness, NEVER the connected peer or command JSON. The signed
    policy root public key must be operator-enrolled externally, not downloaded
    or learned via this socket. A positive observation is *not* C5 consent.

    disposable_test_mode allows CI to inspect an unprivileged temporary
    script, but it is permanently ineligible for production trust.
    """

    def __init__(
        self, *,
        signed_policy: bytes, policy_signature: bytes,
        pinned_release_root: Ed25519PublicKey,
        pinned_receipt_key: Ed25519PublicKey,
        minimum_epoch: int, minimum_sequence: int,
        expected_pid: int, expected_start_ticks: str,
        disposable_test_mode: bool = False,
    ) -> None:
        if (not isinstance(pinned_release_root, Ed25519PublicKey)
                or not isinstance(pinned_receipt_key, Ed25519PublicKey)
                or type(expected_pid) is not int or expected_pid <= 1
                or type(expected_start_ticks) is not str
                or _TICKS.fullmatch(expected_start_ticks) is None
                or type(minimum_epoch) is not int or minimum_epoch < 1
                or type(minimum_sequence) is not int or minimum_sequence < 1
                or type(disposable_test_mode) is not bool
                or type(policy_signature) is not bytes
                or len(policy_signature) != 64):
            raise OriginRefused("Independently pinned enrollment prerequisites missing")
        policy = _policy(signed_policy)
        if (policy["releaseEpoch"] < minimum_epoch
                or policy["releaseSequence"] < minimum_sequence):
            raise OriginRefused("Signed release floor rollback")
        try:
            pinned_release_root.verify(policy_signature, _DOMAIN + signed_policy)
        except InvalidSignature as e:
            raise OriginRefused("Unapproved release signature") from e
        pub = pinned_receipt_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        if hashlib.sha256(pub).hexdigest() != policy["receiptKeySha256"]:
            raise OriginRefused("Host signing key not enrolled under release root")
        self._policy = policy
        self._expected_pid = expected_pid
        self._expected_start_ticks = expected_start_ticks
        self._disposable = disposable_test_mode

    def inspect(self, peer: KernelPeer) -> GatewayOriginObservation:
        """Re-measure on every request; fail closed on process changes."""
        p = self._policy
        if (type(peer) is not KernelPeer
                or peer.pid != self._expected_pid
                or peer.uid != p["uid"] or peer.gid != p["gid"]
                or _start_ticks(peer.pid) != self._expected_start_ticks):
            raise OriginRefused("Unenrolled kernel peer or stale process start")
        _kernel_uid_gid(peer.pid, p["uid"], p["gid"])
        # For a Python service, the kernel exe is the interpreter: verifying
        # only /proc/PID/exe is INSUFFICIENT. We additionally measure the
        # manifest-pinned actual Python entrypoint's bytes and exact argv.
        try:
            interpreter = os.stat(p["interpreterPath"])
            observed = os.stat(f"/proc/{peer.pid}/exe")
            raw = Path(f"/proc/{peer.pid}/cmdline").read_bytes()
        except OSError as e:
            raise OriginRefused("Kernel executable/cmdline unavailable") from e
        if (interpreter.st_dev, interpreter.st_ino) != (
                observed.st_dev, observed.st_ino):
            raise OriginRefused("Wrong executing interpreter inode")
        if (not 0 < len(raw) <= _MAX_CMD or not raw.endswith(b"\0")):
            raise OriginRefused("Invalid process command line")
        argv = raw[:-1].split(b"\0")
        if (len(argv) != 2
                or os.path.realpath(os.fsdecode(argv[0])) !=
                    os.path.realpath(p["interpreterPath"])
                or os.fsdecode(argv[1]) != p["entrypointPath"]):
            raise OriginRefused("Not the enrolled Python entrypoint")
        digest = _safe_script_digest(
            Path(p["entrypointPath"]), disposable=self._disposable,
            expected_uid=p["uid"],
        )
        if digest != p["entrypointSha256"]:
            raise OriginRefused("Running entrypoint differs from signed release")
        if (_start_ticks(peer.pid) != self._expected_start_ticks
                or Path(f"/proc/{peer.pid}/cmdline").read_bytes() != raw):
            raise OriginRefused("Kernel process changed while measuring")
        return GatewayOriginObservation(
            process_matches_enrollment=True,
            signer_matches_enrollment=True,
            observed_pid=peer.pid,
            observed_start_ticks=self._expected_start_ticks,
        )

    def consistent(self, peer: KernelPeer) -> bool:
        """Supplemental *read-only* predicate, not a production grant."""
        try:
            return self.inspect(peer).process_matches_enrollment is True
        except (OriginRefused, OSError, ValueError):
            return False
