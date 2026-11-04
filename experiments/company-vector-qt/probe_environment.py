#!/usr/bin/env python3
"""Read-only host inventory for optional MapLibre Qt compatibility.

Does not start QML, access network, install packages, change compositor
or edit any user files. Output is diagnostic, not a readiness certificate.
"""
import json
import os
import shutil
import subprocess

def command_version(*args):
    if not shutil.which(args[0]):
        return None
    try:
        outcome = subprocess.run(args, capture_output=True, text=True,
                                 timeout=3, check=False)
        text = (outcome.stdout or outcome.stderr).strip()
        return text[:250] if outcome.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None

def inventory():
    return {
        "pkg_config_qt": {
            "Qt6Core": command_version("pkg-config", "--modversion", "Qt6Core"),
            "Qt6Quick": command_version("pkg-config", "--modversion", "Qt6Quick"),
            "Qt6Location": command_version("pkg-config", "--modversion", "Qt6Location"),
            "Qt6Positioning": command_version("pkg-config", "--modversion", "Qt6Positioning")
        },
        "commands_present": {
            name: bool(shutil.which(name))
            for name in ("cmake", "ninja", "qml", "quickshell", "glxinfo", "eglinfo")
        },
        "qmaplibre_dir_declared": bool(os.environ.get("QMapLibre_DIR")),
        "qml_import_path_declared": bool(os.environ.get("QML_IMPORT_PATH")),
        "opengl_backend_declared": os.environ.get("QSG_RHI_BACKEND") == "opengl",
        "note": "Read-only inventory. No proof of plugin loading or compositor compatibility."
    }

if __name__ == "__main__":
    print(json.dumps(inventory(), sort_keys=True, indent=2))
