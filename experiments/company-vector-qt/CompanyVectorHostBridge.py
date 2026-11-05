#!/usr/bin/python3
"""M15 fixed-path, single-PID native Company map bridge (no Toolbox spawn).

Installed as ~/.local/libexec/post-apollo/company-vector-probe only after
operator approval. M13's trusted_executable gate checks this entry point.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
import sys

SCHEMA = "post-apollo.company-vector-host-bridge.v1"
EXPECTED_QT_VERSION = "6.11.2"  # Fedora 44 / M14 build checkpoint.
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
    for variable, value in (
        ("LD_LIBRARY_PATH", prefix / "lib64"),
        ("QT_PLUGIN_PATH", prefix / "plugins"),
        ("QML_IMPORT_PATH", prefix / "qml"),
        ("QML2_IMPORT_PATH", prefix / "qml"),
    ):
        existing = env.get(variable, "")
        env[variable] = str(value) + (":" + existing if existing else "")
    return env


def _check_host_qt() -> bool:
    """Conservative ABI gate: refuse rather than guess at host Qt compatibility."""
    if not Path("/usr/bin/pkg-config").is_file():
        return False
    for module in ("Qt6Core", "Qt6Quick", "Qt6Location", "Qt6Positioning"):
        try:
            result = subprocess.run(
                ["/usr/bin/pkg-config", "--modversion", module],
                capture_output=True, text=True, timeout=2, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        if result.returncode != 0 or result.stdout.strip() != EXPECTED_QT_VERSION:
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
    env = runtime_environment(home)
    try:
        result = subprocess.run(
            ["/usr/bin/ldd", str(binary)], env=env,
            capture_output=True, text=True, timeout=4, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"schema": SCHEMA, "status": "HOST_RUNTIME_UNVERIFIED"}
    if result.returncode != 0 or "not found" in (result.stdout + result.stderr):
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
