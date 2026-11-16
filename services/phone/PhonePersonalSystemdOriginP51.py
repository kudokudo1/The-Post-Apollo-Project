"""P51 // Read-only actual systemd PHONE STATUS candidate observation.

This checks a running OS-supervised *candidate* service, not a verified
signed release or enrolled production host. Real Linux systemctl MainPID,
procfs starttime/UID/GID/cgroup, executable, capabilities, arguments, unit
and root-owned staged source are cross-checked. The verifier is intentionally
read-only and exposes no process ID, path, contact, or personal information.

Do NOT use it to admit signer/seat/SELinux, unlock Secret Service, or save.
Independent C4b/C3e root and one-use challenge, C5 consent, native Fedora
installed RPM/OSTree/SELinux/logind and signed rollback have not been proven.
"""
from __future__ import annotations

import os
from pathlib import Path
import pwd
import grp
import socket
import stat
import subprocess
import sys

UNIT = "post-apollo-phone-personal-status-ci.service"
USER = "postapollo-phone-status-ci"
BUNDLE = Path("/usr/libexec/post-apollo/phone")
UNIT_PATH = Path("/run/systemd/system") / UNIT
SOCKET_DIR = Path("/run/postapollo-phone-status-ci")
SOCKET_PATH = SOCKET_DIR / "phone-personal-status-p47.sock"
MARKER = Path("/run/postapollo-phone-status-test-only/explicit-test.marker")
SOURCE_FILES = (
    "PhonePersonalHostSocketP47.py",
    "PhonePersonalPeerEvidenceP48.py",
    "PhonePersonalStatusHostP49.py",
    "PhonePersonalInstalledReleaseP50.py",
)
UNIT_COPY = BUNDLE / "systemd" / UNIT
FIELDS = frozenset((
    "MainPID", "User", "Group", "ControlGroup",
    "FragmentPath", "LoadState", "ActiveState", "SubState",
))
MAX_OUTPUT = 8192
MAX_PROC = 8192
EXPECTED_CMD = (
    "/usr/bin/python3", "-I", "-B",
    "/usr/libexec/post-apollo/phone/PhonePersonalStatusHostP49.py",
    "--private-status-dir", "/run/postapollo-phone-status-ci",
)
REFUSED = {
    "status": "INSTALLED_STATUS_CANDIDATE_REFUSED",
    "systemdCandidateObserved": False,
    "kernelProcessConsistent": False,
    "rootOwnedSourceObserved": False,
    "installedHostVerified": False,
    "signedReleaseIndependentlyEnrolled": False,
    "selinuxEnforcingVerified": False,
    "logindSeatVerified": False,
    "c3eChallengeConsumed": False,
    "c5HumanConsentVerified": False,
    "keyReleaseAuthorized": False,
    "personalSaveAuthorized": False,
}
OBSERVED = {
    **REFUSED,
    "status": "SYSTEMD_CANDIDATE_OBSERVED_NOT_AUTHENTICATED",
    "systemdCandidateObserved": True,
    "kernelProcessConsistent": True,
    "rootOwnedSourceObserved": True,
}


def _refuse() -> None:
    raise ValueError("P51_STATUS_CANDIDATE_REFUSED")


def _root_file(path: Path, mode: int) -> bytes:
    if path.is_symlink():
        _refuse()
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
                 | getattr(os, "O_NOFOLLOW", 0))
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode)
                or info.st_uid != 0 or info.st_nlink != 1
                or stat.S_IMODE(info.st_mode) != mode
                or not 0 < info.st_size <= 128 * 1024):
            _refuse()
        raw = os.read(fd, 128 * 1024 + 1)
        if len(raw) != info.st_size:
            _refuse()
        return raw
    finally:
        os.close(fd)


def _root_dir(path: Path, mode: int) -> None:
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != 0
            or stat.S_IMODE(info.st_mode) != mode
            or path.resolve(strict=True) != path):
        _refuse()


def _source_present() -> None:
    _root_dir(BUNDLE, 0o555)
    _root_dir(BUNDLE / "systemd", 0o555)
    unit = _root_file(UNIT_PATH, 0o644)
    if _root_file(UNIT_COPY, 0o644) != unit:
        _refuse()
    for name in SOURCE_FILES:
        _root_file(BUNDLE / name, 0o555)
    _root_dir(MARKER.parent, 0o700)
    _root_file(MARKER, 0o600)


def _systemd_show() -> dict[str, str]:
    # Actual OS query, no shell or caller-selectable command/unit.
    p = subprocess.run(
        ["/usr/bin/systemctl", "--system", "--no-pager", "show",
         UNIT, *[f"-p{field}" for field in sorted(FIELDS)]],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        timeout=3, check=False,
    )
    if p.returncode != 0 or len(p.stdout) > MAX_OUTPUT:
        _refuse()
    out: dict[str, str] = {}
    for line in p.stdout.decode("ascii").splitlines():
        key, sep, value = line.partition("=")
        if not sep or key not in FIELDS or key in out:
            _refuse()
        out[key] = value
    if set(out) != FIELDS:
        _refuse()
    return out


def _start_ticks(data: bytes, pid: int) -> int:
    # /proc/pid/stat comm may contain ")" and spaces. Use last delimiter.
    end = data.rfind(b") ")
    if end < 0 or not data.startswith(str(pid).encode() + b" ("):
        _refuse()
    fields = data[end + 2:].split()
    if len(fields) < 20 or not fields[19].isdigit():
        _refuse()
    value = int(fields[19])
    if value < 1:
        _refuse()
    return value


def _proc(path: Path, max_size=MAX_PROC) -> bytes:
    with path.open("rb") as f:
        data = f.read(max_size + 1)
    if not 0 < len(data) <= max_size:
        _refuse()
    return data


def _proc_credentials(data: bytes, uid: int, gid: int) -> None:
    entries: dict[bytes, bytes] = {}
    for row in data.splitlines():
        k, sep, v = row.partition(b":")
        if sep and k in (b"Uid", b"Gid", b"NoNewPrivs", b"CapEff"):
            if k in entries:
                _refuse()
            entries[k] = v.strip()
    if (entries.get(b"Uid") != b"\t".join([str(uid).encode()] * 4)
            and entries.get(b"Uid") != b" ".join([str(uid).encode()] * 4)):
        # Linux status generally uses tabs, but whitespace may vary.
        values = entries.get(b"Uid", b"").split()
        if len(values) != 4 or values != [str(uid).encode()] * 4:
            _refuse()
    values = entries.get(b"Gid", b"").split()
    if len(values) != 4 or values != [str(gid).encode()] * 4:
        _refuse()
    if entries.get(b"NoNewPrivs") != b"1":
        _refuse()
    caps = entries.get(b"CapEff", b"")
    if not caps or any(c not in b"0123456789abcdefABCDEF" for c in caps):
        _refuse()
    if int(caps, 16) != 0:
        _refuse()


def _kernel_process(pid: int, group: str, uid: int, gid: int) -> None:
    base = Path("/proc") / str(pid)
    before = _start_ticks(_proc(base / "stat"), pid)
    _proc_credentials(_proc(base / "status"), uid, gid)
    cgroup = _proc(base / "cgroup")
    if cgroup != ("0::" + group + "\n").encode("ascii"):
        _refuse()
    cmdline = _proc(base / "cmdline")
    if tuple(x.decode("utf-8") for x in cmdline.rstrip(b"\x00").split(b"\x00")) != EXPECTED_CMD:
        _refuse()
    if (base / "exe").resolve(strict=True) != Path(EXPECTED_CMD[0]).resolve(strict=True):
        _refuse()
    after = _start_ticks(_proc(base / "stat"), pid)
    if before != after or _proc(base / "cgroup") != cgroup:
        _refuse()


def _socket_check(uid: int, gid: int) -> None:
    info = SOCKET_DIR.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != uid
            or info.st_gid != gid or stat.S_IMODE(info.st_mode) != 0o700):
        _refuse()
    info = SOCKET_PATH.lstat()
    if (not stat.S_ISSOCK(info.st_mode) or info.st_uid != uid
            or info.st_gid != gid or stat.S_IMODE(info.st_mode) != 0o600):
        _refuse()


def _candidate() -> None:
    if sys.platform != "linux":
        _refuse()
    _source_present()
    snapshot = _systemd_show()
    if (snapshot["User"] != USER or snapshot["Group"] != USER
            or snapshot["FragmentPath"] != str(UNIT_PATH)
            or snapshot["LoadState"] != "loaded"
            or snapshot["ActiveState"] != "active"
            or snapshot["SubState"] != "running"
            or not snapshot["MainPID"].isdigit()
            or not snapshot["ControlGroup"].startswith("/system.slice/")
            or not snapshot["ControlGroup"].endswith("/" + UNIT)):
        _refuse()
    pid = int(snapshot["MainPID"])
    if pid <= 1:
        _refuse()
    user = pwd.getpwnam(USER)
    group = grp.getgrnam(USER)
    if user.pw_uid == 0 or group.gr_gid == 0 or user.pw_gid != group.gr_gid:
        _refuse()
    _kernel_process(pid, snapshot["ControlGroup"], user.pw_uid, group.gr_gid)
    _socket_check(user.pw_uid, group.gr_gid)
    if _systemd_show() != snapshot:
        _refuse()
    _source_present()


def observe_installed_status_candidate() -> dict[str, object]:
    """Real read-only host observation. Never grants signed/consent/key rights."""
    try:
        _candidate()
        return dict(OBSERVED)
    except Exception:
        return dict(REFUSED)


# No C4b/C3e/C5 trust root, RPM/OSTree verification, SELinux/seat proof,
# Secret Service key release, Personal contact, metadata write or UI SAVED.
