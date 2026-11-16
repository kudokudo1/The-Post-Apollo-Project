#!/usr/bin/python3
"""P49 // Explicitly launched Linux PHONE status host. NO personal authority.

This is an actual process entry point for the existing P47/P48 Linux
STATUS-only socket, suitable for later *separately authorized* installed
host/SELinux verification. The checked-in unit is disabled/inert and no
installer or host startup is provided. Running this process never unlocks a
keyring, consults a vault, receives notes, approves C5, or saves a Favorite.

Two explicit TEST-only environment switches and a private caller-provisioned
directory are mandatory. These switches are NOT credentials or trust proof.
The process measures its own Linux kernel identity and bounded source files
but CANNOT independently authenticate its installation or signed release.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import signal
import stat
import sys
from threading import Event

# -I deliberately removes script-dir/PYTHONPATH resolution. Restore only the
# exact neighboring staged bundle directory. This is NOT a production origin
# pin: independent ownership, package signature and C4b/C3e review are absent.
BUNDLE = Path(__file__).resolve().parent
if str(BUNDLE) not in sys.path:
    sys.path.insert(0, str(BUNDLE))

import PhonePersonalHostSocketP47 as SocketHost
import PhonePersonalPeerEvidenceP48 as Peer
import PhonePersonalInstalledReleaseP50 as SignedRelease

ROSTER = (
    "PhonePersonalStatusHostP49.py",
    "PhonePersonalHostSocketP47.py",
    "PhonePersonalPeerEvidenceP48.py",
    "PhonePersonalInstalledReleaseP50.py",
)
MAX_SOURCE = 128 * 1024
ENV_TEST = "POST_APOLLO_PHONE_STATUS_CI_ONLY"
ENV_NO_SAVE = "POST_APOLLO_PHONE_STATUS_NO_SAVE"
ARG = "--private-status-dir"
CI_MANIFEST = "--ci-signed-manifest"
CI_SIGNATURE = "--ci-signed-signature"
CI_ROOT = "--ci-release-root"
FAIL = 78


def _self_source_snapshot() -> tuple[str, ...] | None:
    """Hash real adjacent module bytes; never compare to self-declared pins."""
    result = []
    try:
        if BUNDLE.is_symlink():
            return None
        folder = BUNDLE.lstat()
        if (not stat.S_ISDIR(folder.st_mode)
                or stat.S_IMODE(folder.st_mode) & 0o022):
            return None
        for name in ROSTER:
            path = BUNDLE / name
            metadata = path.lstat()
            if (not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1
                    or stat.S_IMODE(metadata.st_mode) & 0o022
                    or not 0 < metadata.st_size <= MAX_SOURCE
                    or metadata.st_uid not in (0, os.geteuid())):
                return None
            raw = path.read_bytes()
            if len(raw) != metadata.st_size:
                return None
            result.append(hashlib.sha256(raw).hexdigest())
        return tuple(result)
    except (OSError, ValueError, TypeError):
        return None


def _self_kernel_observed() -> bool:
    """Measure the running SERVER directly, not through client SO_PEERCRED.

    Our own PID cannot be recycled until this process terminates, so unlike
    P48's external peer checks a pidfd is unnecessary. This remains only a
    consistency observation, not signed installed-host authentication.
    """
    if not sys.platform.startswith("linux"):
        return False
    try:
        pid = os.getpid()
        proc = Path("/proc/self")
        before = Peer._start_ticks(
            Peer._bounded(proc / "stat", Peer.STAT_MAX), pid)
        if not Peer._uids_gids(
            Peer._bounded(proc / "status", Peer.STATUS_MAX),
            os.geteuid(), os.getegid()
        ):
            return False
        cgroup = Peer._bounded(proc / "cgroup", Peer.CGROUP_MAX)
        if b"\n" not in cgroup:
            return False
        digest, device, inode = Peer._hash_executable(proc / "exe")
        after = Peer._start_ticks(
            Peer._bounded(proc / "stat", Peer.STAT_MAX), pid)
        cgroup_after = Peer._bounded(proc / "cgroup", Peer.CGROUP_MAX)
        executable_after = (proc / "exe").stat()
        return (
            before > 0 and before == after and cgroup == cgroup_after
            and (device, inode)
                == (executable_after.st_dev, executable_after.st_ino)
            and len(digest) == 64
        )
    except (OSError, ValueError, TypeError, AttributeError):
        return False


def run_status_only(args: object) -> int:
    """Launch only the non-authorizing P47 socket until SIGTERM/SIGINT."""
    try:
        if (type(args) is not list or len(args) not in (2, 8)
                or args[0] != ARG or type(args[1]) is not str
                or (len(args) == 8 and
                    (args[2] != CI_MANIFEST or type(args[3]) is not str
                     or args[4] != CI_SIGNATURE or type(args[5]) is not str
                     or args[6] != CI_ROOT or type(args[7]) is not str))
                or os.environ.get(ENV_TEST) != "1"
                or os.environ.get(ENV_NO_SAVE) != "1"
                or os.getuid() != os.geteuid()
                or os.getgid() != os.getegid()):
            return FAIL
        directory = Path(args[1])
        # Check before starting. P47 rechecks path and rejects stale sockets.
        SocketHost._private_directory(directory)
        expected = _self_source_snapshot()
        if expected is None or not _self_kernel_observed():
            return FAIL
        # Additional CI-only signed source consistency. All three file paths
        # and the public root come from the caller, so even a valid signature
        # grants absolutely no installed-host, C3e/C5 or key authority.
        release_paths = (
            tuple(Path(x) for x in (args[3], args[5], args[7]))
            if len(args) == 8 else None
        )
        if release_paths is not None:
            if SignedRelease.verify_candidate_from_paths(
                bundle=BUNDLE, manifest_path=release_paths[0],
                signature_path=release_paths[1], root_path=release_paths[2]
            ) != SignedRelease.RESULT:
                return FAIL
        stop = Event()

        def shut_down(_signal: int, _frame: object) -> None:
            stop.set()

        old_term = signal.signal(signal.SIGTERM, shut_down)
        old_int = signal.signal(signal.SIGINT, shut_down)
        try:
            # Detect source tampering between preflight and socket creation.
            if _self_source_snapshot() != expected:
                return FAIL
            if release_paths is not None:
                if SignedRelease.verify_candidate_from_paths(
                    bundle=BUNDLE, manifest_path=release_paths[0],
                    signature_path=release_paths[1],
                    root_path=release_paths[2]
                ) != SignedRelease.RESULT:
                    return FAIL
            SocketHost.serve_status_only(directory, stop=stop)
            return 0
        finally:
            signal.signal(signal.SIGTERM, old_term)
            signal.signal(signal.SIGINT, old_int)
    except Exception:
        # Fixed refusal, no source paths, OS evidence, key identifiers or
        # user-provided arguments printed to stdout/stderr.
        return FAIL


if __name__ == "__main__":
    sys.exit(run_status_only(sys.argv[1:]))
