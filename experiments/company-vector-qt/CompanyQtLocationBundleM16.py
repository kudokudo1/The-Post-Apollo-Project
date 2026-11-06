#!/usr/bin/env python3
"""M17: explicit, reversible QtLocation runtime + QML staging from Fedora 44 Toolbox.

Read-only: check. Local writes: stage/remove, requiring operator authorization.
This supersedes M16's incomplete library-only bundle. No host package changes.
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

SCHEMA = "post-apollo.company.qtlocation-runtime.v2"
VERSION = "6.11.2"
SOURCE = Path("/usr/lib64/libQt6Location.so.6.11.2")
QML_SOURCE = Path("/usr/lib64/qt6/qml/QtLocation")
LIBRARY = "libQt6Location.so.6"
MANIFEST = "qtlocation-m16-manifest.json"
BUNDLE_PATH = ("postapollo-vector-lab", "qtlocation-runtime", "lib64")
QML_FILES = ("libdeclarative_locationplugin.so", "MapView.qml", "plugins.qmltypes", "qmldir")
HASHED_PATHS = ("lib64/" + LIBRARY,) + tuple("qml/QtLocation/" + f for f in QML_FILES)
EXPECTED_TREE = {
    ".": {"lib64", "qml"},
    "lib64": {LIBRARY, MANIFEST},
    "qml": {"QtLocation"},
    "qml/QtLocation": set(QML_FILES),
}


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


def _module_descriptor_valid(data: bytes) -> bool:
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return False
    entries = [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]
    return ("module QtLocation" in entries
            and any(line.startswith("plugin declarative_locationplugin") for line in entries)
            and "typeinfo plugins.qmltypes" in entries)


def verified_source(source: Path = SOURCE, qml_source: Path = QML_SOURCE) -> bool:
    """Check real RPM-owned source contents, not just a similarly named file."""
    if source != SOURCE or qml_source != QML_SOURCE:
        return False
    sources = [source] + [qml_source / name for name in QML_FILES]
    if not all(_regular_owned(p, 0) for p in sources):
        return False
    try:
        with source.open("rb") as stream:
            if stream.read(4) != bytes.fromhex("7f454c46"):
                return False
        with (qml_source / QML_FILES[0]).open("rb") as stream:
            if stream.read(4) != bytes.fromhex("7f454c46"):
                return False
        if not _module_descriptor_valid((qml_source / "qmldir").read_bytes()):
            return False
        packages = set()
        for path in sources:
            result = subprocess.run(
                ["/usr/bin/rpm", "-qf", "--qf", "%{NAME} %{VERSION}", str(path)],
                capture_output=True, text=True, timeout=3, check=False)
            if result.returncode != 0:
                return False
            parts = result.stdout.strip().split()
            if len(parts) != 2 or not parts[0].startswith("qt6-qtlocation") or parts[1] != VERSION:
                return False
            packages.add(parts[0])
        for package in packages:
            integrity = subprocess.run(
                ["/usr/bin/rpm", "-V", package],
                capture_output=True, text=True, timeout=6, check=False)
            if integrity.returncode != 0 or integrity.stdout.strip():
                return False
    except (OSError, subprocess.TimeoutExpired):
        return False
    return True


def bundle_dir(home: Path) -> Path:
    return home.joinpath(*BUNDLE_PATH)


def _tree_valid(root: Path, uid: int) -> bool:
    for rel, expected in EXPECTED_TREE.items():
        folder = root if rel == "." else root / rel
        if not _directory_owned(folder, uid):
            return False
        try:
            if {entry.name for entry in folder.iterdir()} != expected:
                return False
        except OSError:
            return False
    return True


def valid_bundle(home: Path) -> bool:
    owner = os.getuid()
    path = home
    for part in ("postapollo-vector-lab", "qtlocation-runtime"):
        if not _directory_owned(path, owner):
            return False
        path = path / part
    if not _tree_valid(path, owner):
        return False
    manifest = path / "lib64" / MANIFEST
    if not _regular_owned(manifest, owner):
        return False
    try:
        record = json.loads(manifest.read_text())
        if (set(record) != {"schema", "version", "sha256"}
                or record["schema"] != SCHEMA or record["version"] != VERSION
                or set(record["sha256"]) != set(HASHED_PATHS)):
            return False
        for rel in HASHED_PATHS:
            p = path / rel
            if not _regular_owned(p, owner) or _sha256(p) != record["sha256"][rel]:
                return False
        for rel in ("lib64/" + LIBRARY, "qml/QtLocation/libdeclarative_locationplugin.so"):
            with (path / rel).open("rb") as stream:
                if stream.read(4) != bytes.fromhex("7f454c46"):
                    return False
        return _module_descriptor_valid((path / "qml/QtLocation/qmldir").read_bytes())
    except (OSError, ValueError, TypeError, KeyError):
        return False


def operation(action: str, home: Path | None = None, source: Path = SOURCE,
              qml_source: Path = QML_SOURCE) -> dict:
    root = Path.home() if home is None else home
    if action not in ("check", "stage", "remove"):
        return {"schema": SCHEMA, "status": "INVALID_ACTION"}
    if (os.getuid() == 0 or os.geteuid() != os.getuid()
            or not _directory_owned(root, os.getuid())):
        return {"schema": SCHEMA, "status": "REFUSED_IDENTITY"}

    output = bundle_dir(root)
    runtime = output.parent
    if action == "check":
        status = ("STAGED" if valid_bundle(root) else
                  "NOT_STAGED" if not runtime.exists() and not runtime.is_symlink()
                  else "UNVERIFIED_BUNDLE")
        return {"schema": SCHEMA, "status": status}

    lab = root / "postapollo-vector-lab"
    if not _directory_owned(lab, os.getuid()):
        return {"schema": SCHEMA, "status": "UNSAFE_LAB"}
    if action == "remove":
        if not valid_bundle(root):
            return {"schema": SCHEMA, "status": "REFUSED_UNVERIFIED_BUNDLE"}
        # Only this known five-file bundle can be removed, never foreign content.
        for rel in HASHED_PATHS:
            (runtime / rel).unlink()
        (runtime / "lib64" / MANIFEST).unlink()
        for rel in ("qml/QtLocation", "qml", "lib64"):
            (runtime / rel).rmdir()
        runtime.rmdir()
        return {"schema": SCHEMA, "status": "REMOVED"}

    if runtime.exists() or runtime.is_symlink():
        return {"schema": SCHEMA, "status":
                "ALREADY_STAGED" if valid_bundle(root) else "REFUSED_EXISTING"}
    if not verified_source(source, qml_source):
        return {"schema": SCHEMA, "status": "SOURCE_UNVERIFIED"}

    staged = Path(tempfile.mkdtemp(prefix=".qtlocation-m17-", dir=lab))
    try:
        (staged / "lib64").mkdir(mode=0o700)
        (staged / "qml" / "QtLocation").mkdir(mode=0o700, parents=True)
        mappings = { "lib64/" + LIBRARY: source }
        mappings.update({"qml/QtLocation/" + name: qml_source / name for name in QML_FILES})
        hashes = {}
        for rel, original in mappings.items():
            target = staged / rel
            with original.open("rb") as reader, target.open("xb") as writer:
                shutil.copyfileobj(reader, writer)
                writer.flush()
                os.fsync(writer.fileno())
            target.chmod(0o600)
            hashes[rel] = _sha256(target)
        metadata = staged / "lib64" / MANIFEST
        metadata.write_text(json.dumps({
            "schema": SCHEMA, "version": VERSION, "sha256": hashes
        }, sort_keys=True))
        metadata.chmod(0o600)
        if runtime.exists() or runtime.is_symlink():
            return {"schema": SCHEMA, "status": "REFUSED_EXISTING"}
        staged.rename(runtime)
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
