#!/usr/bin/env python3
"""C3e-M: disposable signed native host process provenance (CI ONLY).

An independently pinned test root signs a purpose-bound policy delegating one
specific host ELF release. Verify actual /proc/PID/exe *opened inode* under a
privileged Linux test supervisor, not a client-supplied path or process name.
This function gives no consent or production authentication; it never edits
witness state, installs software, or enables provider credentials.
"""
from __future__ import annotations

import hashlib
import hmac
import importlib.util
import os
from pathlib import Path
import stat
import tempfile

HERE = Path(__file__).resolve().parent
ROLE = "postapollo.connections.test-native-status-host.v1"
POLICY_SCHEMA = "postapollo.connections.c3em-host-policy.v1"
MANIFEST_SCHEMA = "postapollo.connections.c3em-host-manifest.v1"
RESULT_SCHEMA = "postapollo.connections.c3em-host-observation.v1"
MARKER = "C3EM_DISPOSABLE_SIGNED_NATIVE_HOST_NO_PRODUCTION_AUTH"
MAX_ELF = 2 * 1024 * 1024
MAX_SIGNATURE = 8192
MAX_PUBLIC = 65536
MAX_JSON = 4096


class Refused(Exception):
    pass


def deny(code: str):
    raise Refused(code)


def load(filename: str, name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    if spec is None or spec.loader is None:
        deny("REQUIRED_SIGNING_SOURCE_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A = load("C3eReleaseAdmission.py", "c3em_pinned_c3e_release")
L = load("C3eLHostStatusObservation.py", "c3em_pinned_c3el_status")


def _private_ci_root(root: Path):
    """Explicitly scoped temporary runner, not a production activation gate."""
    if os.name != "posix" or os.geteuid() != 0 or os.getuid() != 0:
        deny("DISPOSABLE_ROOT_TEST_REQUIRED")
    root = Path(root)
    if (not root.is_absolute() or root.parent != Path("/run") or
            not root.name.startswith("c3ek-ci-")):
        deny("CI_FIXTURE_PATH_REFUSED")
    private = root / "private"
    marker = private / ".c3em-test-only"
    try:
        st = os.lstat(private)
        ms = os.lstat(marker)
        if (not stat.S_ISDIR(st.st_mode) or st.st_uid != 0 or
                stat.S_IMODE(st.st_mode) != 0o700 or
                not stat.S_ISREG(ms.st_mode) or ms.st_uid != 0 or
                stat.S_IMODE(ms.st_mode) != 0o600 or ms.st_nlink != 1 or
                marker.read_text() != MARKER + "\n"):
            deny("TEST_ENROLLMENT_MARKER_REFUSED")
    except OSError:
        deny("TEST_ENROLLMENT_MARKER_MISSING")
    return private


def _snapshot(source: Path, dest: Path, ceiling: int):
    """One nofollow root-owned bounded snapshot per signing input."""
    fd = None
    try:
        fd = os.open(str(source), os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or
                st.st_nlink != 1 or stat.S_IMODE(st.st_mode) & 0o022 or
                st.st_size < 1 or st.st_size > ceiling):
            deny("UNSAFE_SIGNED_INPUT")
        blocks = []
        size = 0
        while True:
            data = os.read(fd, min(65536, ceiling + 1 - size))
            if not data:
                break
            size += len(data)
            if size > ceiling:
                deny("UNSAFE_SIGNED_INPUT")
            blocks.append(data)
        if size != st.st_size:
            deny("SIGNING_INPUT_CHANGED")
        with dest.open("xb") as out:
            os.chmod(dest, 0o600)
            for block in blocks:
                out.write(block)
    except OSError:
        deny("SIGNING_INPUT_UNAVAILABLE")
    finally:
        if fd is not None:
            os.close(fd)


def _verify_signatures(work: Path, *, root_pin: str,
                       minimum_epoch: int, minimum_sequence: int):
    if (type(root_pin) is not str or A.FPR.fullmatch(root_pin) is None or
            type(minimum_epoch) is not int or minimum_epoch < 1 or
            type(minimum_sequence) is not int or minimum_sequence < 1):
        deny("INVALID_TEST_ENROLLMENT")
    try:
        root_ring = A._isolated_ring(work, work / "root-public", "root")
        listing = A._cmd(["gpg", "--homedir", str(work), "--batch",
                          "--no-default-keyring", "--keyring", str(root_ring),
                          "--with-colons", "--fingerprint", "--list-keys"])
        primaries = [x.split(":")[9] for x in listing.stdout.splitlines()
                     if x.startswith("fpr:")]
        if listing.returncode != 0 or primaries != [root_pin]:
            deny("PINNED_ROOT_IDENTITY_REFUSED")
        if A._check_detached(root_ring, work / "policy-sig",
                             work / "policy") != root_pin:
            deny("POLICY_ROOT_SIGNATURE_REFUSED")
        policy = A._unique_json(work / "policy")
        A._fields(policy, {"schema", "role", "epoch", "min_sequence",
                           "delegated_fingerprint"}, "POLICY_FIELDS_REFUSED")
        if (policy["schema"] != POLICY_SCHEMA or policy["role"] != ROLE or
                A._integer(policy["epoch"], 1, "POLICY_EPOCH_REFUSED")
                < minimum_epoch):
            deny("SIGNED_HOST_ROLE_OR_POLICY_FLOOR_REFUSED")
        delegate = A._fingerprint(policy["delegated_fingerprint"])
        seq_floor = max(minimum_sequence, A._integer(
            policy["min_sequence"], 1, "POLICY_SEQUENCE_REFUSED"))
        delegate_ring = A._isolated_ring(work, work / "delegate-public", "delegate")
        if A._check_detached(delegate_ring, work / "manifest-sig",
                             work / "manifest") != delegate:
            deny("UNAPPROVED_HOST_DELEGATE")
        manifest = A._unique_json(work / "manifest")
        A._fields(manifest, {"schema", "role", "epoch", "sequence",
                             "sha256", "size"}, "MANIFEST_FIELDS_REFUSED")
        if (manifest["schema"] != MANIFEST_SCHEMA or
                manifest["role"] != ROLE or
                type(manifest["epoch"]) is not int or
                manifest["epoch"] != policy["epoch"] or
                A._integer(manifest["sequence"], 1, "MANIFEST_SEQUENCE_REFUSED")
                < seq_floor or
                A._integer(manifest["size"], 1, "MANIFEST_SIZE_REFUSED") > MAX_ELF):
            deny("SIGNED_HOST_RELEASE_FLOOR_REFUSED")
        return A._hex_digest(manifest["sha256"]), manifest["size"], (
            manifest["epoch"], manifest["sequence"])
    except A.Refused:
        deny("SIGNED_RELEASE_CRYPTO_REFUSED")


def _running_native_elf(pid: int, *, expected_start: str):
    if type(pid) is not int or pid <= 1 or type(expected_start) is not str:
        deny("INVALID_RUNNING_HOST_PIN")
    if L.process_start(pid) != expected_start:
        deny("HOST_PROCESS_IDENTITY_CHANGED")
    try:
        proc = os.stat(Path("/proc") / str(pid))
        if proc.st_uid != 0 or proc.st_gid != 0:
            deny("RUNNING_HOST_NOT_ROOT")
        # Linux /proc/PID/exe resolves to the actual executing kernel inode.
        fd = os.open(f"/proc/{pid}/exe", os.O_RDONLY | os.O_CLOEXEC)
        try:
            st = os.fstat(fd)
            if (not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or
                    not 0 < st.st_size <= MAX_ELF):
                deny("UNSAFE_RUNNING_HOST_EXECUTABLE")
            magic = os.read(fd, 4)
            if magic != b"\x7fELF":
                deny("HOST_NOT_NATIVE_ELF")
            h = hashlib.sha256()
            h.update(magic)
            size = len(magic)
            while True:
                block = os.read(fd, 65536)
                if not block:
                    break
                size += len(block)
                if size > MAX_ELF:
                    deny("HOST_ELF_OVERSIZE")
                h.update(block)
        finally:
            os.close(fd)
    except OSError:
        deny("HOST_KERNEL_EXECUTABLE_UNAVAILABLE")
    if L.process_start(pid) != expected_start:
        deny("HOST_PROCESS_CHANGED_DURING_VERIFY")
    return h.hexdigest(), size


def verify(*, ci_fixture_root: Path, host_pid: int, host_start: str,
           root_public: Path, root_pin: str, policy: Path, policy_signature: Path,
           delegate_public: Path, manifest: Path, manifest_signature: Path,
           minimum_epoch: int, minimum_sequence: int):
    private = _private_ci_root(Path(ci_fixture_root))
    paths = {
        "root-public": (root_public, MAX_PUBLIC),
        "policy": (policy, MAX_JSON),
        "policy-sig": (policy_signature, MAX_SIGNATURE),
        "delegate-public": (delegate_public, MAX_PUBLIC),
        "manifest": (manifest, MAX_JSON),
        "manifest-sig": (manifest_signature, MAX_SIGNATURE),
    }
    with tempfile.TemporaryDirectory(prefix="c3em-verify-", dir=private) as td:
        work = Path(td)
        work.chmod(0o700)
        for name, (source, limit) in paths.items():
            _snapshot(Path(source), work / name, limit)
        digest, size, floor = _verify_signatures(
            work, root_pin=root_pin, minimum_epoch=minimum_epoch,
            minimum_sequence=minimum_sequence)
        actual_hash, actual_size = _running_native_elf(host_pid,
                                                      expected_start=host_start)
        if (not hmac.compare_digest(digest, actual_hash) or size != actual_size):
            deny("SIGNED_RUNNING_HOST_BYTES_MISMATCH")
    return {
        "schema": RESULT_SCHEMA,
        "host_pid": host_pid,
        "host_start": host_start,
        "signed_native_elf_verified_in_ci": True,
        "observed_policy_epoch": floor[0],
        "observed_release_sequence": floor[1],
        "hostAuthenticated": False,
        "canApprove": False,
        "credentialActionsEnabled": False,
        "productionAuthority": False,
    }
