#!/usr/bin/env python3
"""Explicit QtLocation 6.11.2 user-local staging in the existing Fedora 44 Toolbox.

check is read-only. stage/remove mutate only ~/postapollo-vector-lab
and require separate operator authorization. Never installs on the host.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile

SCHEMA = "post-apollo.company.qtlocation-runtime.v1"
VERSION = "6.11.2"
PACKAGE = "qt6-qtlocation"
SOURCE = Path("/usr/lib64/libQt6Location.so.6.11.2")
LIBRARY = "libQt6Location.so.6"
MANIFEST = "qtlocation-m16-manifest.json"
BUNDLE_PATH = ("postapollo-vector-lab", "qtlocation-runtime", "lib64")


def _regular_owned(path: Path, uid: int) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    return (stat.S_ISREG(info.st_mode) and info.st_uid == uid
            and not info.st_mode & (0o022 | 0o6000))


def _directory_owned(path: Path, uid: int) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    return (stat.S_ISDIR(info.st_mode) and info.st_uid == uid
            and not info.st_mode & 0o022)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verified_source(source: Path = SOURCE) -> bool:
    if source != SOURCE or not _regular_owned(source, 0):
        return False
    with source.open("rb") as stream:
        if stream.read(4) != bytes.fromhex("7f454c46"):
            return False
    try:
        version = subprocess.run(
            ["/usr/bin/rpm", "-q", "--qf", "%{VERSION}", PACKAGE],
            capture_output=True, text=True, timeout=3)
        integrity = subprocess.run(
            ["/usr/bin/rpm", "-V", PACKAGE],
            capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return (version.returncode == 0 and version.stdout.strip() == VERSION
            and integrity.returncode == 0 and not integrity.stdout.strip())


def bundle_dir(home: Path) -> Path:
    return home.joinpath(*BUNDLE_PATH)


def valid_bundle(home: Path) -> bool:
    path = home
    for part in BUNDLE_PATH:
        if not _directory_owned(path, os.getuid()):
            return False
        path = path / part
    if not _directory_owned(path, os.getuid()):
        return False
    library, manifest = path / LIBRARY, path / MANIFEST
    if not (_regular_owned(library, os.getuid())
            and _regular_owned(manifest, os.getuid())):
        return False
    try:
        record = json.loads(manifest.read_text())
        if (set(record) != {"schema", "version", "sha256"}
                or record["schema"] != SCHEMA or record["version"] != VERSION):
            return False
        with library.open("rb") as stream:
            if stream.read(4) != bytes.fromhex("7f454c46"):
                return False
        return record["sha256"] == _sha256(library)
    except (OSError, ValueError, TypeError):
        return False


def operation(action: str, home: Path | None = None, source: Path = SOURCE) -> dict:
    root = Path.home() if home is None else home
    if action not in ("check", "stage", "remove"):
        return {"schema": SCHEMA, "status": "INVALID_ACTION"}
    if (os.getuid() == 0 or os.geteuid() != os.getuid()
            or not _directory_owned(root, os.getuid())):
        return {"schema": SCHEMA, "status": "REFUSED_IDENTITY"}
    output = bundle_dir(root)
    if action == "check":
        state = "STAGED" if valid_bundle(root) else (
            "NOT_STAGED" if not output.exists() and not output.is_symlink()
            else "UNVERIFIED_BUNDLE")
        return {"schema": SCHEMA, "status": state}

    lab = root / BUNDLE_PATH[0]
    if not _directory_owned(lab, os.getuid()):
        return {"schema": SCHEMA, "status": "UNSAFE_LAB"}
    if action == "remove":
        if not valid_bundle(root):
            return {"schema": SCHEMA, "status": "REFUSED_UNVERIFIED_BUNDLE"}
        if {p.name for p in output.iterdir()} != {LIBRARY, MANIFEST}:
            return {"schema": SCHEMA, "status": "REFUSED_EXTRA_FILES"}
        (output / MANIFEST).unlink()
        (output / LIBRARY).unlink()
        output.rmdir()
        output.parent.rmdir()
        return {"schema": SCHEMA, "status": "REMOVED"}

    # Never overwrite or replace any existing runtime bundle directory.
    if (output.exists() or output.is_symlink()
            or output.parent.exists() or output.parent.is_symlink()):
        return {"schema": SCHEMA, "status":
                "ALREADY_STAGED" if valid_bundle(root) else "REFUSED_EXISTING"}
    if not verified_source(source):
        return {"schema": SCHEMA, "status": "SOURCE_UNVERIFIED"}
    staged = Path(tempfile.mkdtemp(prefix=".qtlocation-m16-", dir=lab))
    try:
        libdir = staged / "lib64"
        libdir.mkdir(mode=0o700)
        destination = libdir / LIBRARY
        with source.open("rb") as reader, destination.open("xb") as writer:
            shutil.copyfileobj(reader, writer)
            writer.flush()
            os.fsync(writer.fileno())
        destination.chmod(0o600)
        manifest = libdir / MANIFEST
        manifest.write_text(json.dumps({
            "schema": SCHEMA, "version": VERSION, "sha256": _sha256(destination)
        }, sort_keys=True))
        manifest.chmod(0o600)
        if output.parent.exists() or output.parent.is_symlink():
            return {"schema": SCHEMA, "status": "REFUSED_EXISTING"}
        staged.rename(output.parent)
        return {"schema": SCHEMA, "status": "STAGED"}
    except OSError:
        return {"schema": SCHEMA, "status": "STAGE_FAILED"}
    finally:
        if staged.exists():
            shutil.rmtree(staged)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        return 2
    result = operation(args[0])
    print(json.dumps(result, separators=(",", ":")))
    return 0 if result["status"] in (
        "STAGED", "NOT_STAGED", "ALREADY_STAGED", "REMOVED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
