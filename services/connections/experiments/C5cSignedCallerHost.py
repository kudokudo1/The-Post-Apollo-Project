#!/usr/bin/env python3
"""C5c CI-only signed-executable admission into the C5b private broker.

A C5b reviewer requests a PID bind. Before allowing that bind, this independent
test gate checks a root-signed, role-bound release policy; a delegated-signed
manifest; and the *running* kernel /proc/<pid>/exe bytes. C5b still checks the
SCM_CREDENTIALS sender on every packet. No one is authenticated as the human
operator. No production grants, TASKS text or keys are ever accepted.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

_HERE = Path(__file__).resolve().parent


def sibling(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C5C_PINNED_SOURCE_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


B = sibling(_HERE / "C5bTasksDurableConsentHost.py", "c5c_pinned_c5b")
A = B.C5a
E = sibling(_HERE.parents[2] / "tests/connections/c3e_release_trust"
            / "C3eReleaseAdmission.py", "c5c_pinned_c3e")
# The C3e helper above lives at repository /tests, not /services/tests.
# Use the exact repository-relative path in the source tree.
ROLE = "postapollo.tasks.recovery.test-client.v1"
POLICY_SCHEMA = "postapollo.connections.c5c-caller-policy.v1"
MANIFEST_SCHEMA = "postapollo.connections.c5c-caller-manifest.v1"
MAX_EXECUTABLE = 2 * 1024 * 1024
MAX_JSON = 4096
GATE_MARKER = "C5C_DISPOSABLE_SIGNED_EXECUTABLE_NO_PRODUCTION_IDENTITY"


def private_gate() -> bool:
    if not B.private_ci() or os.environ.get("POST_APOLLO_C5C_DISPOSABLE") != "1":
        return False
    root = Path(os.environ["POST_APOLLO_C5B_FIXTURE_ROOT"])
    try:
        marker = root / ".c5c-test-only"
        info = marker.lstat()
        return (stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid()
                and info.st_nlink == 1 and stat.S_IMODE(info.st_mode) == 0o600
                and marker.read_text() == GATE_MARKER + "\n")
    except (OSError, UnicodeError):
        return False


def expected_artifact_digest(root_pub: Path, pin: str,
                             policy: Path, policy_sig: Path,
                             delegate_pub: Path, manifest: Path,
                             manifest_sig: Path, epoch_floor: int,
                             sequence_floor: int,
                             role: str = ROLE) -> tuple[str, int]:
    """Verify two exact signatures and purpose-bound delegation, no key grants."""
    if (type(epoch_floor) is not int or epoch_floor < 1
            or type(sequence_floor) is not int or sequence_floor < 1
            or type(pin) is not str or E.FPR.fullmatch(pin) is None):
        raise E.Refused("BAD_TRUST_ANCHOR_OR_FLOOR")
    with tempfile.TemporaryDirectory(prefix="postapollo-c5c-gpg-") as temporary:
        home = Path(temporary)
        home.chmod(0o700)
        root_ring = E._isolated_ring(home, root_pub, "root")
        listed = E._cmd(["gpg", "--homedir", str(home), "--batch",
                         "--no-default-keyring", "--keyring", str(root_ring),
                         "--with-colons", "--fingerprint", "--list-keys"])
        primaries = [line.split(":")[9] for line in listed.stdout.splitlines()
                     if line.startswith("fpr:")]
        if listed.returncode != 0 or not primaries or primaries[0] != pin:
            raise E.Refused("ROOT_PIN_MISMATCH")
        if E._check_detached(root_ring, policy_sig, policy) != pin:
            raise E.Refused("POLICY_ROOT_MISMATCH")
        p = E._unique_json(policy)
        E._fields(p, {"schema", "role", "epoch", "min_sequence",
                      "delegated_fingerprint"}, "POLICY_SCHEMA_REFUSED")
        if (p["schema"] != POLICY_SCHEMA or p["role"] != role
                or E._integer(p["epoch"], 1, "POLICY_EPOCH_REFUSED")
                < epoch_floor):
            raise E.Refused("POLICY_SCOPE_OR_EPOCH_REFUSED")
        fingerprint = E._fingerprint(p["delegated_fingerprint"])
        floor = max(sequence_floor, E._integer(
            p["min_sequence"], 1, "MIN_RELEASE_REFUSED"))
        delegated_ring = E._isolated_ring(home, delegate_pub, "delegate")
        signer = E._check_detached(delegated_ring, manifest_sig, manifest)
        if signer != fingerprint:
            raise E.Refused("UNAPPROVED_SIGNER")
        m = E._unique_json(manifest)
        E._fields(m, {"schema", "role", "epoch", "sequence", "sha256", "size"},
                  "MANIFEST_SCHEMA_REFUSED")
        if (m["schema"] != MANIFEST_SCHEMA or m["role"] != role
                or m["epoch"] != p["epoch"]
                or E._integer(m["sequence"], 1, "RELEASE_SEQUENCE_REFUSED")
                < floor
                or E._integer(m["size"], 1, "EXECUTABLE_SIZE_REFUSED")
                > MAX_EXECUTABLE):
            raise E.Refused("RELEASE_SCOPE_OR_FLOOR_REFUSED")
        return E._hex_digest(m["sha256"]), m["size"]


def running_executable(pid: int) -> tuple[str, int]:
    """Hash the opened kernel process executable; a Python script is not enough."""
    start = B.process_start_ticks(pid)
    if start is None:
        raise E.Refused("PROCESS_NOT_RUNNING")
    path = Path("/proc") / str(pid) / "exe"
    try:
        # /proc/.../exe is a kernel-owned symbolic view. O_NOFOLLOW is not
        # appropriate here: we need the kernel-referenced executable inode.
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC)
        with os.fdopen(fd, "rb") as opened:
            status = os.fstat(opened.fileno())
            if (not stat.S_ISREG(status.st_mode)
                    or not 0 < status.st_size <= MAX_EXECUTABLE):
                raise E.Refused("PROCESS_EXECUTABLE_SIZE_REFUSED")
            h = hashlib.sha256()
            size = 0
            while True:
                chunk = opened.read(64 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_EXECUTABLE:
                    raise E.Refused("PROCESS_EXECUTABLE_OVERSIZE")
                h.update(chunk)
    except OSError:
        raise E.Refused("PROCESS_EXECUTABLE_UNAVAILABLE")
    if B.process_start_ticks(pid) != start:
        raise E.Refused("PROCESS_CHANGED_DURING_VERIFICATION")
    return h.hexdigest(), size


class SignedCallerBroker(B.DurableBroker):
    def bind_client(self, value: object) -> dict:
        if (not A.exact(value, {"op", "pid", "uid", "gid"})
                or any(type(value.get(k)) is not int for k in
                       ("pid", "uid", "gid"))
                or value["pid"] < 2):
            return A.reply("C5C_INVALID_BINDING")
        if not private_gate():
            return A.reply("C5C_NOT_DISPOSABLE")
        try:
            root = Path(os.environ["POST_APOLLO_C5C_ROOT_PUBLIC"])
            policy = Path(os.environ["POST_APOLLO_C5C_POLICY"])
            policy_sig = Path(os.environ["POST_APOLLO_C5C_POLICY_SIGNATURE"])
            delegate = Path(os.environ["POST_APOLLO_C5C_DELEGATE_PUBLIC"])
            manifest = Path(os.environ["POST_APOLLO_C5C_MANIFEST"])
            manifest_sig = Path(os.environ["POST_APOLLO_C5C_MANIFEST_SIGNATURE"])
            pin = os.environ["POST_APOLLO_C5C_ROOT_PIN"]
            epoch = int(os.environ["POST_APOLLO_C5C_MIN_EPOCH"])
            seq = int(os.environ["POST_APOLLO_C5C_MIN_SEQUENCE"])
            # Every path and anchor comes from the host-launch harness;
            # the requester never sends keys, paths, signature or hash.
            digest, expected_size = expected_artifact_digest(
                root, pin, policy, policy_sig, delegate, manifest,
                manifest_sig, epoch, seq)
            current_digest, current_size = running_executable(value["pid"])
            if current_digest != digest or current_size != expected_size:
                return A.reply("C5C_SIGNED_EXECUTABLE_MISMATCH")
            result = super().bind_client(value)
            if result["ok"]:
                return A.reply("C5C_SIGNED_TEST_EXECUTABLE_BOUND_NO_REAL_GRANT",
                               True)
            return result
        except (E.Refused, OSError, ValueError, KeyError):
            return A.reply("C5C_SIGNED_EXECUTABLE_REFUSED")


def main() -> int:
    if not private_gate():
        print("C5C_REFUSED_OUTSIDE_DISPOSABLE_TEST")
        return 2
    if len(sys.argv) != 4 or sys.argv[1] != "--host":
        print("C5C_NO_CLIENT_OR_PRODUCTION_MODE")
        return 2
    try:
        operator_fd, client_fd = int(sys.argv[2]), int(sys.argv[3])
        if min(operator_fd, client_fd) < 3 or operator_fd == client_fd:
            return 2
        return B.serve(operator_fd, client_fd, SignedCallerBroker)
    except (ValueError, OSError):
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
