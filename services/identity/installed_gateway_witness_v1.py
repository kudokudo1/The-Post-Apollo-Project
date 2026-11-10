"""Read-only Identity installed gateway witness V1. NEVER grants login.

A release-root-signed artifact manifest is checked against an actual dpkg
installation, systemd service, connected kernel peer, PID/start, cgroup, LSM,
module hashes, package SHA and receipt key pin. Inputs must be independently
provisioned; the gateway/socket cannot enroll or self-attest. CI package and
keys are disposable, not production trust, and no consent is issued here.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from desktop_command_gateway_v0 import KernelPeer
from signed_gateway_origin_probe_v0 import _start_ticks

SCHEMA = "post-apollo.identity.installed-release.ci-v1"
ROLE = "post-apollo.identity.native-command-gateway.ci-v1"
DOMAIN = b"post-apollo.identity.installed-release.ci-v1\x00"
PACKAGE = "post-apollo-identity-ci-fixture"
PREFIX = "/usr/libexec/post-apollo/identity/"
# V1 is a fixed CI release role, not a general-purpose Python package.
# A signature over a partial module list must never omit executable code
# from installed-file measurement. Changing this roster needs a new review.
REQUIRED_FILES = frozenset(PREFIX + name for name in (
    "identity-gateway-ci",
    "desktop_command_gateway_v0.py",
    "desktop_host_lifecycle_v0.py",
    "desktop_context_projection_v0.py",
    "desktop_session_host_v0.py",
    "native_loopback_callback_v0.py",
    "private_context_ipc_v0.py",
    "signed_command_receipt_v0.py",
))
KEYS = {"schema","role","epoch","sequence","package","packageSha256",
        "receiptKeySha256","unit","files"}
SHA = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
TICKS = re.compile(r"[1-9][0-9]{0,19}\Z", re.ASCII)
UNIT = re.compile(r"post-apollo-identity-ci-[a-z0-9-]{1,36}\.service\Z")


class WitnessRefused(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class InstalledObservation:
    pid: int
    start_ticks: str
    package_matches: bool
    module_bytes_match: bool
    supervisor_matches: bool
    receipt_key_matches: bool
    production_authority: bool = False
    can_begin_sign_in: bool = False
    host_authenticated: bool = False
    can_connect_provider: bool = False


def _unique_pairs(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise WitnessRefused("Duplicate policy field")
        d[k] = v
    return d


def canonical(m):
    return json.dumps(m, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def verify_release(raw, sig, root, epoch, sequence):
    if (type(raw) is not bytes or not 1 <= len(raw) <= 4096
            or type(sig) is not bytes or len(sig) != 64
            or not isinstance(root, Ed25519PublicKey)
            or type(epoch) is not int or epoch < 1
            or type(sequence) is not int or sequence < 1):
        raise WitnessRefused("Independent release enrollment missing")
    try:
        m = json.loads(raw.decode("utf-8", errors="strict"),
                       object_pairs_hook=_unique_pairs)
        if type(m) is not dict or set(m) != KEYS or canonical(m) != raw:
            raise WitnessRefused("Invalid canonical signed release")
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise WitnessRefused("Invalid signed release") from exc
    if (m["schema"] != SCHEMA or m["role"] != ROLE
            or m["package"] != PACKAGE
            or type(m["epoch"]) is not int or m["epoch"] < epoch
            or type(m["sequence"]) is not int or m["sequence"] < sequence
            or type(m["unit"]) is not str or UNIT.fullmatch(m["unit"]) is None
            or type(m["packageSha256"]) is not str
            or SHA.fullmatch(m["packageSha256"]) is None
            or type(m["receiptKeySha256"]) is not str
            or SHA.fullmatch(m["receiptKeySha256"]) is None
            or type(m["files"]) is not dict):
        raise WitnessRefused("Unapproved signed role, release or package")
    for path, digest in m["files"].items():
        if (type(path) is not str or not path.startswith(PREFIX)
                or "/" in path[len(PREFIX):]
                or type(digest) is not str or SHA.fullmatch(digest) is None):
            raise WitnessRefused("Invalid module pin")
    if set(m["files"]) != REQUIRED_FILES:
        raise WitnessRefused("Signed installed gateway manifest has missing or extra files")
    try:
        root.verify(sig, DOMAIN + raw)
    except InvalidSignature as exc:
        raise WitnessRefused("Untrusted release-root signature") from exc
    return m


def _hash_file(path, installed=True, ceiling=1024*1024):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError as exc:
        raise WitnessRefused("Installed file unavailable or symlink") from exc
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or not 0 < before.st_size <= ceiling
                or (installed and (before.st_uid != 0 or
                    stat.S_IMODE(before.st_mode) != 0o555))):
            raise WitnessRefused("Installed bytes not root-owned 0555")
        h = hashlib.sha256()
        size = 0
        while True:
            block = os.read(fd, min(65536, ceiling+1-size))
            if not block:
                break
            size += len(block)
            if size > ceiling:
                raise WitnessRefused("Installed file exceeded limit")
            h.update(block)
        after = os.fstat(fd)
        if (size != before.st_size or
                (before.st_dev,before.st_ino,before.st_mtime_ns,before.st_ctime_ns)
                != (after.st_dev,after.st_ino,after.st_mtime_ns,after.st_ctime_ns)):
            raise WitnessRefused("Installed file changed during measurement")
        return h.hexdigest()
    finally:
        os.close(fd)


def _run(args):
    try:
        r = subprocess.run(args, check=True, capture_output=True,
                           text=True, timeout=3)
        return r.stdout
    except (subprocess.SubprocessError, OSError) as exc:
        raise WitnessRefused("Independent OS observer unavailable") from exc


def _systemd(unit):
    lines = _run(["systemctl","show",unit,"--no-pager",
        "--property=Id,LoadState,ActiveState,MainPID,User,ControlGroup"])
    result = {}
    for line in lines.splitlines():
        key, sep, value = line.partition("=")
        if not sep or key in result:
            raise WitnessRefused("Untrusted supervisor fields")
        result[key] = value
    if set(result) != {"Id","LoadState","ActiveState","MainPID",
                       "User","ControlGroup"}:
        raise WitnessRefused("Incomplete real supervisor observation")
    return result


def _os_cred(pid, uid, gid):
    try:
        fields = {}
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith(("Uid:","Gid:")):
                k, v = line.split(":", 1)
                fields[k] = [int(x) for x in v.split()]
        if fields.get("Uid") != [uid]*4 or fields.get("Gid") != [gid]*4:
            raise WitnessRefused("Different kernel process identity")
    except (OSError, ValueError) as exc:
        raise WitnessRefused("Kernel process credentials missing") from exc


class InstalledGatewayWitness:
    """Independent signed-release and installed supervisor negative gate."""
    def __init__(self, *, signed_release, release_signature,
                 pinned_release_root, minimum_epoch, minimum_sequence,
                 expected_pid, expected_start_ticks, expected_uid, expected_gid,
                 expected_cgroup, expected_lsm, expected_receipt_key_sha256,
                 expected_package_file):
        self.manifest = verify_release(signed_release, release_signature,
                                      pinned_release_root, minimum_epoch,
                                      minimum_sequence)
        if (type(expected_pid) is not int or expected_pid <= 1
                or type(expected_start_ticks) is not str
                or TICKS.fullmatch(expected_start_ticks) is None
                or type(expected_uid) is not int or expected_uid < 0
                or type(expected_gid) is not int or expected_gid < 0
                or type(expected_cgroup) is not str
                or not expected_cgroup.startswith("/system.slice/")
                or type(expected_lsm) is not str or not expected_lsm.strip()
                or type(expected_receipt_key_sha256) is not str
                or SHA.fullmatch(expected_receipt_key_sha256) is None
                or not isinstance(expected_package_file, Path)
                or not expected_package_file.is_absolute()):
            raise WitnessRefused("Independent process/package/LSM pins missing")
        if expected_receipt_key_sha256 != self.manifest["receiptKeySha256"]:
            raise WitnessRefused("Receipt signer not enrolled in package release")
        self.pid, self.ticks = expected_pid, expected_start_ticks
        self.uid, self.gid = expected_uid, expected_gid
        self.cgroup, self.lsm = expected_cgroup, expected_lsm
        self.package_file = expected_package_file

    def inspect(self, peer):
        m = self.manifest
        if (type(peer) is not KernelPeer
                or (peer.pid,peer.uid,peer.gid) != (self.pid,self.uid,self.gid)
                or _start_ticks(self.pid) != self.ticks):
            raise WitnessRefused("Connected peer changed from independently pinned PID")
        unit = _systemd(m["unit"])
        if (unit["Id"] != m["unit"] or unit["LoadState"] != "loaded"
                or unit["ActiveState"] != "active"
                or unit["MainPID"] != str(self.pid)
                or unit["User"] not in (str(self.uid), pwd.getpwuid(self.uid).pw_name)
                or unit["ControlGroup"] != self.cgroup):
            raise WitnessRefused("Not the enrolled supervised service")
        _os_cred(self.pid, self.uid, self.gid)
        try:
            cgroup_lines = Path(f"/proc/{self.pid}/cgroup").read_text().splitlines()
            lsm = Path(f"/proc/{self.pid}/attr/current").read_text().strip()
        except OSError as exc:
            raise WitnessRefused("Cgroup or LSM unavailable") from exc
        if (not any(x.endswith(":"+self.cgroup) for x in cgroup_lines)
                or lsm != self.lsm):
            raise WitnessRefused("Cgroup or SELinux/LSM identity changed")
        if _hash_file(self.package_file, installed=False,
                      ceiling=8*1024*1024) != m["packageSha256"]:
            raise WitnessRefused("Signed package bytes changed")
        if _run(["dpkg-query","-W","-f="+"$"+"{Status}",m["package"]]) != "install ok installed":
            raise WitnessRefused("Signed package not installed")
        for path, expected_digest in m["files"].items():
            if _run(["dpkg-query","-S",path]).strip() != f"{m['package']}: {path}":
                raise WitnessRefused("Installed module package owner mismatch")
            if _hash_file(Path(path)) != expected_digest:
                raise WitnessRefused("Installed module hash changed")
        if _start_ticks(self.pid) != self.ticks:
            raise WitnessRefused("Process replaced during measurement")
        return InstalledObservation(
            pid=self.pid, start_ticks=self.ticks, package_matches=True,
            module_bytes_match=True, supervisor_matches=True,
            receipt_key_matches=True)

    def consistent(self, peer):
        """Supplemental consistency check; NEVER an authentication grant."""
        try:
            evidence = self.inspect(peer)
            return (evidence.package_matches is True
                    and evidence.module_bytes_match is True
                    and evidence.supervisor_matches is True
                    and evidence.receipt_key_matches is True
                    and evidence.production_authority is False
                    and evidence.can_begin_sign_in is False)
        except (WitnessRefused, ValueError, OSError, KeyError):
            return False
