#!/usr/bin/env python3
"""MACHINE // CI-only simulated protected archive copy and rollback.

CAUTION: This test runs as root ONLY on a disposable CI runner. It does not
provide a production migrator, service, authorizer, or installation script.
Only synthetic ciphertext in an owned /tmp fixture is ever copied. A browser
UID, a different destination-owner UID, and an unrelated UID are exercised
against the real Linux kernel, not mocked file permission decisions.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/time"))
import MachineBraveSealedVault as vault

BROWSER_UID = 24211
SERVICE_UID = 24212
FOREIGN_UID = 24213
SOURCE_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
SENTINEL_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
DIRECT_ACTIONS = ("read", "list", "write", "unlink", "chmod", "create")
NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
DIRECTORY = getattr(os, "O_DIRECTORY", 0)


class FixtureRefusal(ValueError):
    pass


class InjectedFailure(Exception):
    pass


def refuse():
    raise FixtureRefusal("DISPOSABLE PROTECTED TRANSFER REFUSED")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def b64(raw):
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def record(identifier, label):
    value = {
        "kind": vault.RECORD_KIND,
        "record_id": identifier,
        "created_at_utc": "2026-11-11T17:00:00+00:00",
        "envelope": {
            "kind": vault.ENVELOPE_KIND, "version": 1,
            "algorithm": "AES-256-GCM",
            "kdf": "PBKDF2-HMAC-SHA256", "iterations": 600000,
            "salt": b64(b"0123456789abcdef"),
            "nonce": b64(b"0123456789ab"),
            "aad": vault.AAD,
            "ciphertext": b64(b"synthetic sealed ciphertext " + label + b" fake tag"),
        }
    }
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    assert vault._record(raw, identifier) == value
    return raw


def make_owned_file(folder, identifier, raw, uid):
    path = folder / (identifier + ".json")
    path.write_bytes(raw)
    os.chown(path, uid, uid)
    path.chmod(0o600)
    return path


def private_dir_fd(path, uid):
    if path.is_symlink():
        refuse()
    fd = os.open(path, os.O_RDONLY | DIRECTORY | NOFOLLOW)
    info = os.fstat(fd)
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != uid or
            stat.S_IMODE(info.st_mode) != 0o700):
        os.close(fd)
        refuse()
    return fd


def read_owned_record(fd, uid, identifier):
    identifier = vault._id(identifier)
    descriptor = os.open(identifier + ".json", os.O_RDONLY | NOFOLLOW,
                         dir_fd=fd)
    try:
        info = os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != uid or
                stat.S_IMODE(info.st_mode) != 0o600 or
                info.st_nlink != 1 or not 1 <= info.st_size <= vault.MAX_RECORD):
            refuse()
        chunks = []
        size = 0
        while True:
            part = os.read(descriptor, min(16384, vault.MAX_RECORD + 1 - size))
            if not part:
                break
            chunks.append(part)
            size += len(part)
            if size > vault.MAX_RECORD:
                refuse()
        raw = b"".join(chunks)
        if size != info.st_size or vault._record(raw, identifier)["record_id"] != identifier:
            refuse()
        return raw
    finally:
        os.close(descriptor)


def fixture_transfer(source, protected, identifier, expected_digest, *,
                     inject=None, after_stage=None):
    """Synthetic root-only transaction, not reusable operational migration.

    Source is never moved or unlinked. A failure before/after publication
    cleans only a newly staged fixture record. An uncertain replacement
    is intentionally left for independent recovery, never blindly deleted.
    """
    if not (os.geteuid() == 0 and
            source.parent == protected.parent and
            source.parent.parent == Path("/tmp") and
            source.parent.name.startswith("machine-destination-ci-")):
        refuse()
    identifier = vault._id(identifier)
    if (type(expected_digest) is not str or
            vault.DIGEST_RE.fullmatch(expected_digest) is None):
        refuse()
    srcfd = private_dir_fd(source, BROWSER_UID)
    try:
        dstfd = private_dir_fd(protected, SERVICE_UID)
        try:
            original = read_owned_record(srcfd, BROWSER_UID, identifier)
            if digest(original) != expected_digest:
                refuse()
            temp = ".tmp-ci-" + str(uuid.uuid4())
            target = identifier + ".json"
            staged = False
            published = False
            published_stat = None
            try:
                fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                             NOFOLLOW, 0o600, dir_fd=dstfd)
                staged = True
                with os.fdopen(fd, "wb") as out:
                    out.write(original)
                    out.flush()
                    os.fchown(out.fileno(), SERVICE_UID, SERVICE_UID)
                    os.fchmod(out.fileno(), 0o600)
                    os.fsync(out.fileno())
                if inject == "after_stage":
                    raise InjectedFailure("staging failure")
                if after_stage is not None:
                    after_stage()
                # Recheck source immediately before publish. This is not
                # an atomic or adversarially safe same-UID migration lock.
                observed = read_owned_record(srcfd, BROWSER_UID, identifier)
                if observed != original or digest(observed) != expected_digest:
                    refuse()
                os.link(temp, target, src_dir_fd=dstfd, dst_dir_fd=dstfd,
                        follow_symlinks=False)  # fails if target already exists
                published = True
                published_stat = os.stat(target, dir_fd=dstfd,
                                         follow_symlinks=False)
                os.unlink(temp, dir_fd=dstfd)
                staged = False
                os.fsync(dstfd)
                if inject == "after_publish":
                    raise InjectedFailure("post-publication failure")
                saved = read_owned_record(dstfd, SERVICE_UID, identifier)
                if saved != original:
                    refuse()
                return digest(saved)
            except BaseException:
                if staged:
                    os.unlink(temp, dir_fd=dstfd)
                if published:
                    # Roll back only the inode just published by this fixture,
                    # not any other writer's possibly substituted record.
                    current = os.stat(target, dir_fd=dstfd,
                                      follow_symlinks=False)
                    if ((current.st_dev, current.st_ino) !=
                            (published_stat.st_dev, published_stat.st_ino) or
                            current.st_uid != SERVICE_UID or
                            current.st_nlink != 1):
                        raise FixtureRefusal("UNCERTAIN CI TARGET; NO BLIND UNLINK")
                    os.unlink(target, dir_fd=dstfd)
                os.fsync(dstfd)
                raise
        finally:
            os.close(dstfd)
    finally:
        os.close(srcfd)


ATTACK = r'''
import json, os, pathlib, sys
mode,folder,name=sys.argv[1:]
directory=pathlib.Path(folder)
target=directory/name
try:
    if mode=="read":
        target.read_bytes()
    elif mode=="list":
        list(directory.iterdir())
    elif mode=="write":
        with target.open("ab") as stream:stream.write(b"ATTACK")
    elif mode=="unlink":
        target.unlink()
    elif mode=="chmod":
        directory.chmod(0o755)
    elif mode=="create":
        (directory/"unwanted.json").write_bytes(b"ATTACK")
    else:
        raise RuntimeError("invalid test mode")
except PermissionError:
    print("permission_denied")
else:
    print("access_allowed")
'''


def run_as(uid, mode, directory, identifier):
    def demote():
        os.setgroups([])
        os.setresgid(uid, uid, uid)
        os.setresuid(uid, uid, uid)
    result = subprocess.run(
        [sys.executable, "-I", "-c", ATTACK, mode, str(directory),
         identifier + ".json"],
        capture_output=True, text=True, timeout=8,
        preexec_fn=demote)
    assert result.returncode == 0, (result.stderr, result.stdout)
    assert result.stderr == ""
    return result.stdout.strip()


def expect_refusal(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except (FixtureRefusal, InjectedFailure, FileExistsError, vault.VaultError,
            PermissionError, OSError):
        return
    raise AssertionError("UNEXPECTED TRANSFER ALLOWED")


def verify_isolation(source, protected):
    for op in DIRECT_ACTIONS:
        assert run_as(BROWSER_UID, op, protected, SOURCE_ID) == "permission_denied"
        assert run_as(FOREIGN_UID, op, protected, SOURCE_ID) == "permission_denied"
    # The protected-service UID cannot open the ordinary account's source.
    for op in ("read", "list", "write", "unlink"):
        assert run_as(SERVICE_UID, op, source, SOURCE_ID) == "permission_denied"
    assert run_as(BROWSER_UID, "read", source, SOURCE_ID) == "access_allowed"
    assert run_as(SERVICE_UID, "list", protected, SENTINEL_ID) == "access_allowed"


def main():
    assert os.geteuid() == 0, "CI-only test needs sudo; never weaken to mock access"
    assert sys.platform.startswith("linux")
    for uid in (BROWSER_UID, SERVICE_UID, FOREIGN_UID):
        try:
            pwd.getpwuid(uid)
        except KeyError:
            continue
        raise RuntimeError("CI fixture UID assigned to real account: stop")

    temp = Path(tempfile.mkdtemp(prefix="machine-destination-ci-"))
    assert temp.parent == Path("/tmp")
    temp.chmod(0o711)  # may traverse to child; cannot read service tree
    try:
        source, protected = temp / "source", temp / "protected"
        source.mkdir(mode=0o700)
        protected.mkdir(mode=0o700)
        os.chown(source, BROWSER_UID, BROWSER_UID)
        os.chown(protected, SERVICE_UID, SERVICE_UID)
        source.chmod(0o700)
        protected.chmod(0o700)

        primary = record(SOURCE_ID, b"alpha")
        sentinel = record(SENTINEL_ID, b"unchanged")
        srcpath = make_owned_file(source, SOURCE_ID, primary, BROWSER_UID)
        sentinelpath = make_owned_file(protected, SENTINEL_ID,
                                       sentinel, SERVICE_UID)
        original_mode = stat.S_IMODE(srcpath.stat().st_mode)
        original_stat = srcpath.stat()
        sentinel_stat = sentinelpath.stat()
        original_digest = digest(primary)

        verify_isolation(source, protected)
        assert srcpath.read_bytes() == primary
        assert sentinelpath.read_bytes() == sentinel

        # Inject failure before any record becomes visible.
        expect_refusal(fixture_transfer, source, protected, SOURCE_ID,
                       original_digest, inject="after_stage")
        assert not (protected / (SOURCE_ID + ".json")).exists()
        assert not list(protected.glob(".tmp-ci-*"))
        assert sentinelpath.read_bytes() == sentinel
        assert srcpath.read_bytes() == primary

        # Inject failure after publication. Roll back ONLY the new inode.
        expect_refusal(fixture_transfer, source, protected, SOURCE_ID,
                       original_digest, inject="after_publish")
        assert not (protected / (SOURCE_ID + ".json")).exists()
        assert not list(protected.glob(".tmp-ci-*"))
        assert sentinelpath.read_bytes() == sentinel
        assert srcpath.read_bytes() == primary

        # Source changes between preflight and publication; no target.
        changed = record(SOURCE_ID, b"mutated")
        def mutate():
            srcpath.write_bytes(changed)
        expect_refusal(fixture_transfer, source, protected, SOURCE_ID,
                       original_digest, after_stage=mutate)
        assert srcpath.read_bytes() == changed  # test mutation, not transfer
        assert not (protected / (SOURCE_ID + ".json")).exists()
        assert sentinelpath.read_bytes() == sentinel
        srcpath.write_bytes(primary)

        # Invalid checksum, source hardlink and mode, unsafe destination
        # owner/mode all refuse without changing either existing record.
        expect_refusal(fixture_transfer, source, protected, SOURCE_ID, "0" * 64)
        alias = source / "hardlink.json"
        os.link(srcpath, alias)
        expect_refusal(fixture_transfer, source, protected, SOURCE_ID,
                       original_digest)
        alias.unlink()
        # A symlink offered under the expected UUID must not follow the
        # replacement path even if it points to otherwise valid ciphertext.
        backup = source / "saved-real-record"
        srcpath.rename(backup)
        srcpath.symlink_to(backup.name)
        expect_refusal(fixture_transfer, source, protected, SOURCE_ID,
                       original_digest)
        assert srcpath.is_symlink()
        srcpath.unlink()
        backup.rename(srcpath)
        assert srcpath.read_bytes() == primary
        srcpath.chmod(0o644)
        expect_refusal(fixture_transfer, source, protected, SOURCE_ID,
                       original_digest)
        srcpath.chmod(0o600)
        protected.chmod(0o755)
        expect_refusal(fixture_transfer, source, protected, SOURCE_ID,
                       original_digest)
        protected.chmod(0o700)
        os.chown(protected, BROWSER_UID, BROWSER_UID)
        expect_refusal(fixture_transfer, source, protected, SOURCE_ID,
                       original_digest)
        os.chown(protected, SERVICE_UID, SERVICE_UID)

        # A preexisting target filename is never replaced, even if its
        # contents do not match source. Existing sentinel also untouched.
        conflict = protected / (SOURCE_ID + ".json")
        conflict_raw = record(SOURCE_ID, b"different target")
        make_owned_file(protected, SOURCE_ID, conflict_raw, SERVICE_UID)
        expect_refusal(fixture_transfer, source, protected, SOURCE_ID,
                       original_digest)
        assert conflict.read_bytes() == conflict_raw
        assert sentinelpath.read_bytes() == sentinel
        conflict.unlink()

        # Successful simulation copies ciphertext bytes with an unchanged
        # record ID; source is never moved, deleted, or made service-owned.
        assert fixture_transfer(source, protected, SOURCE_ID,
                                original_digest) == original_digest
        copied = protected / (SOURCE_ID + ".json")
        assert copied.read_bytes() == primary
        assert copied.stat().st_uid == SERVICE_UID
        assert copied.stat().st_gid == SERVICE_UID
        assert stat.S_IMODE(copied.stat().st_mode) == 0o600
        assert srcpath.read_bytes() == primary
        assert srcpath.stat().st_uid == BROWSER_UID
        assert stat.S_IMODE(srcpath.stat().st_mode) == original_mode
        assert (srcpath.stat().st_dev, srcpath.stat().st_ino) == (
            original_stat.st_dev, original_stat.st_ino)
        assert (sentinelpath.stat().st_dev, sentinelpath.stat().st_ino) == (
            sentinel_stat.st_dev, sentinel_stat.st_ino)

        # Repeat import refuses rather than overwriting a sealed record.
        expect_refusal(fixture_transfer, source, protected, SOURCE_ID,
                       original_digest)
        assert copied.read_bytes() == primary
        assert sentinelpath.read_bytes() == sentinel
        assert not list(protected.glob(".tmp-ci-*"))
        verify_isolation(source, protected)

        # A foreign UID and browser UID still cannot read any ciphertext
        # from the service-owned directory even after successful publish.
        assert run_as(BROWSER_UID, "read", protected, SOURCE_ID) == "permission_denied"
        assert run_as(FOREIGN_UID, "read", protected, SOURCE_ID) == "permission_denied"
        assert run_as(SERVICE_UID, "read", protected, SOURCE_ID) == "access_allowed"

    finally:
        assert temp.parent == Path("/tmp")
        assert temp.name.startswith("machine-destination-ci-")
        shutil.rmtree(temp)
    print("MACHINE CI-only protected destination: distinct-UID bypass denial, ciphertext-only staging, injected failures and source preservation PASS")


if __name__ == "__main__":
    main()
