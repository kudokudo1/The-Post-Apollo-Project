#!/usr/bin/env python3
"""C5d disposable signed reviewer peer. NOT a real human-consent authority.

Adds a second independently signed role to C5c's signed client test. All
permission flags remain disabled, and the operator input originates in a fake
CI harness. This demonstrates *which program sent the reviewer decision*,
not that a real human approved or saw anything.
"""
from __future__ import annotations

import os
import importlib.util
from pathlib import Path
import stat
import sys

_module_path = Path(__file__).resolve().with_name("C5cSignedCallerHost.py")
_spec = importlib.util.spec_from_file_location("c5d_pinned_c5c", _module_path)
if _spec is None or _spec.loader is None:
    raise RuntimeError("C5C_SOURCE_MISSING")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)
B = C.B
A = C.A
E = C.E

REVIEW_ROLE = "postapollo.connections.test-reviewer.v1"
MARKER = "C5D_DISPOSABLE_SEPARATE_SIGNED_REVIEWER_NO_HUMAN_CONSENT"


def private_gate() -> bool:
    if not C.private_gate() or os.environ.get("POST_APOLLO_C5D_DISPOSABLE") != "1":
        return False
    root = Path(os.environ["POST_APOLLO_C5B_FIXTURE_ROOT"])
    marker = root / ".c5d-test-only"
    try:
        info = marker.lstat()
        return (stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid()
                and info.st_nlink == 1 and stat.S_IMODE(info.st_mode) == 0o600
                and marker.read_text() == MARKER + "\n")
    except (OSError, UnicodeError):
        return False


class SignedReviewerBroker(C.SignedCallerBroker):
    """Extend C5c signed *requester* with a distinct signed review process."""
    def __init__(self, root: Path):
        super().__init__(root)
        self.reviewer_pin: tuple[int, int, int, int, str, int] | None = None

    def allowed_reviewer(self, sender, original) -> bool:
        # Do NOT fallback to the origin of an inherited socketpair. Its
        # creator may have no reviewer role. Every packet must come from the
        # independently authorized reviewer process.
        if not private_gate() or sender is None:
            return False
        try:
            pid = int(os.environ["POST_APOLLO_C5D_REVIEWER_PID"])
            uid = int(os.environ["POST_APOLLO_C5D_REVIEWER_UID"])
            gid = int(os.environ["POST_APOLLO_C5D_REVIEWER_GID"])
            if (pid < 2 or uid <= 0 or gid < 0
                    or sender != (pid, uid, gid)):
                return False
            start = B.process_start_ticks(pid)
            if start is None:
                return False
            if self.reviewer_pin is None:
                digest, size = C.expected_artifact_digest(
                    Path(os.environ["POST_APOLLO_C5D_ROOT_PUBLIC"]),
                    os.environ["POST_APOLLO_C5D_ROOT_PIN"],
                    Path(os.environ["POST_APOLLO_C5D_POLICY"]),
                    Path(os.environ["POST_APOLLO_C5D_POLICY_SIGNATURE"]),
                    Path(os.environ["POST_APOLLO_C5D_DELEGATE_PUBLIC"]),
                    Path(os.environ["POST_APOLLO_C5D_MANIFEST"]),
                    Path(os.environ["POST_APOLLO_C5D_MANIFEST_SIGNATURE"]),
                    int(os.environ["POST_APOLLO_C5D_MIN_EPOCH"]),
                    int(os.environ["POST_APOLLO_C5D_MIN_SEQUENCE"]),
                    role=REVIEW_ROLE)
                current_hash, current_size = C.running_executable(pid)
                if digest != current_hash or size != current_size:
                    return False
                self.reviewer_pin = (pid, uid, gid, start, digest, size)
            pinned = self.reviewer_pin
            if pinned[:4] != (pid, uid, gid, start):
                return False
            # Recheck actual executing inode each time to reject execve from
            # the same PID with the same /proc start ticks.
            actual_hash, actual_size = C.running_executable(pid)
            return (actual_hash, actual_size) == pinned[4:]
        except (E.Refused, OSError, ValueError, KeyError):
            return False


def main() -> int:
    if not private_gate():
        print("C5D_REFUSED_OUTSIDE_DISPOSABLE_CI")
        return 2
    if len(sys.argv) != 4 or sys.argv[1] != "--host":
        print("C5D_REFUSED_MODE")
        return 2
    try:
        reviewer_fd, client_fd = int(sys.argv[2]), int(sys.argv[3])
        if min(reviewer_fd, client_fd) < 3 or reviewer_fd == client_fd:
            return 2
        return B.serve(reviewer_fd, client_fd, SignedReviewerBroker)
    except (ValueError, OSError):
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
