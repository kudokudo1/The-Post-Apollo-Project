#!/usr/bin/python3
"""M15 fixed-path, single-PID native Company map bridge (no Toolbox spawn).

Installed as ~/.local/libexec/post-apollo/company-vector-probe only after
operator approval. M13's trusted_executable gate checks this entry point.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

SCHEMA = "post-apollo.company-vector-host-bridge.v1"
EXPECTED_QT_VERSION = "6.11.2"  # Fedora 44 / M14 build checkpoint.
BUNDLE_PARTS = ("postapollo-vector-lab", "qtlocation-runtime", "lib64", "libQt6Location.so.6")
MANIFEST_PARTS = ("postapollo-vector-lab", "qtlocation-runtime", "lib64", "qtlocation-m16-manifest.json")
BUNDLE_SCHEMA = "post-apollo.company.qtlocation-runtime.v1"
LAB_FILES = (
    ("postapollo-vector-lab", "company-vector-build", "company-vector-probe"),
    ("postapollo-vector-lab", "maplibre-install", "lib64", "libQMapLibre.so.3.0.0"),
    ("postapollo-vector-lab", "maplibre-install", "lib64", "libQMapLibreLocation.so.3.0.0"),
    ("postapollo-vector-lab", "maplibre-install", "qml", "MapLibre", "qmldir"),
    ("postapollo-vector-lab", "maplibre-install", "plugins", "geoservices", "libqtgeoservices_maplibre.so"),
)


def owned_path(home: Path, parts: tuple[str, ...], executable: bool = False) -> Path | None:
    """Reject symlinks and unsafe ownership/modes at every path component."""
    if not home.is_absolute() or home.is_symlink() or not home.is_dir():
        return None
    candidate = home
    for index, part in enumerate(parts):
        candidate = candidate / part
        try:
            info = candidate.lstat()
        except OSError:
            return None
        if info.st_uid != os.getuid() or info.st_mode & 0o022:
            return None
        if index < len(parts) - 1:
            if not stat.S_ISDIR(info.st_mode):
                return None
        elif not stat.S_ISREG(info.st_mode) or info.st_mode & 0o6000:
            return None
        elif executable and not info.st_mode & 0o100:
            return None
    return candidate


def runtime_environment(home: Path) -> dict[str, str]:
    prefix = home / "postapollo-vector-lab" / "maplibre-install"
    env = os.environ.copy()
    bundle_dir = home.joinpath(*BUNDLE_PARTS[:-1])
    for variable, value in (
        ("LD_LIBRARY_PATH", prefix / "lib64"),
        ("QT_PLUGIN_PATH", prefix / "plugins"),
        ("QML_IMPORT_PATH", prefix / "qml"),
        ("QML2_IMPORT_PATH", prefix / "qml"),
    ):
        # Never inherit arbitrary Qt paths from the parent desktop session.
        env[variable] = (str(bundle_dir) + ":" + str(value)
                         if variable == "LD_LIBRARY_PATH" else str(value))
    return env


def _check_host_qt() -> bool:
    """Check actual host Qt modules; no assumption about -devel metadata."""
    if not Path("/usr/bin/pkg-config").is_file():
        return False
    for module in ("Qt6Core", "Qt6Quick"):
        try:
            result = subprocess.run(
                ["/usr/bin/pkg-config", "--modversion", module],
                capture_output=True, text=True, timeout=2, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        if result.returncode != 0 or result.stdout.strip() != EXPECTED_QT_VERSION:
            return False
    positioning = Path("/usr/lib64/libQt6Positioning.so.6")
    try:
        return positioning.resolve(strict=True).name == (
            "libQt6Positioning.so." + EXPECTED_QT_VERSION)
    except (OSError, RuntimeError):
        return False


def _bundle_valid(home: Path) -> bool:
    library = owned_path(home, BUNDLE_PARTS)
    manifest = owned_path(home, MANIFEST_PARTS)
    if not library or not manifest:
        return False
    try:
        doc = json.loads(manifest.read_text())
        if (set(doc) != {"schema", "version", "sha256"}
                or doc["schema"] != BUNDLE_SCHEMA
                or doc["version"] != EXPECTED_QT_VERSION):
            return False
        hasher = hashlib.sha256()
        with library.open("rb") as stream:
            if stream.read(4) != bytes.fromhex("7f454c46"):
                return False
            stream.seek(0)
            for block in iter(lambda: stream.read(1 << 20), b""):
                hasher.update(block)
        return hasher.hexdigest() == doc["sha256"]
    except (OSError, ValueError, TypeError):
        return False


def _dependencies_resolved(home: Path, env: dict[str, str]) -> bool:
    """Require linked QtLocation to resolve inside the verified bundle."""
    bundled = str(home.joinpath(*BUNDLE_PARTS))
    checked = (
        home.joinpath(*LAB_FILES[0]),
        home.joinpath(*LAB_FILES[2]),
        home.joinpath(*LAB_FILES[4]),
        home.joinpath(*BUNDLE_PARTS),
    )
    for artifact in checked:
        try:
            result = subprocess.run(
                ["/usr/bin/ldd", str(artifact)], env=env,
                capture_output=True, text=True, timeout=4, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        output = result.stdout + result.stderr
        if result.returncode != 0 or "not found" in output:
            return False
        if "libQt6Location.so.6 =>" in output and (
                "libQt6Location.so.6 => " + bundled + " ") not in output:
            return False
    return True

def probe(home: Path | None = None) -> dict[str, str]:
    home = home if home is not None else Path.home()
    if os.getuid() == 0 or os.geteuid() != os.getuid():
        return {"schema": SCHEMA, "status": "REFUSED_IDENTITY"}
    binary = None
    for parts in LAB_FILES:
        path = owned_path(home, parts, executable=(parts == LAB_FILES[0]))
        if path is None:
            return {"schema": SCHEMA, "status": "NOT_INSTALLED"}
        if parts == LAB_FILES[0]:
            binary = path
    if not _check_host_qt():
        return {"schema": SCHEMA, "status": "HOST_QT_UNVERIFIED"}
    if not _bundle_valid(home):
        return {"schema": SCHEMA, "status": "QTLOCATION_BUNDLE_UNVERIFIED"}
    env = runtime_environment(home)
    if not _dependencies_resolved(home, env):
        return {"schema": SCHEMA, "status": "HOST_RUNTIME_UNVERIFIED"}
    return {"schema": SCHEMA, "status": "READY"}


def main(argv: list[str] | None = None, home: Path | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args not in ([], ["--styled-online"], ["--probe"]):
        print(json.dumps({"schema": SCHEMA, "status": "INVALID_ACTION"}), flush=True)
        return 2
    root = home if home is not None else Path.home()
    state = probe(root)
    if args == ["--probe"] or state["status"] != "READY":
        print(json.dumps(state, separators=(",", ":")), flush=True)
        return 0 if args == ["--probe"] else 69
    binary = root.joinpath(*LAB_FILES[0])
    # os.execve replaces this PID. Quickshell's SIGTERM targets the native Qt
    # process itself, not a toolbox CLI that could leave an orphan behind.
    try:
        os.execve(str(binary), [str(binary), *args], runtime_environment(root))
    except OSError:
        print(json.dumps({"schema": SCHEMA, "status": "LAUNCH_FAILED"}), flush=True)
        return 70
    return 70


if __name__ == "__main__":
    raise SystemExit(main())
