#!/usr/bin/env python3
"""Pure manifest generator for an *optional disposable* title-marker host."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

HOST_NAME = "org.postapollo.machine_brave_title_marker"
EXTENSION_ID = re.compile(r"[a-p]{32}\Z")


def generate(extension_id, executable):
    if not isinstance(extension_id, str) or not EXTENSION_ID.fullmatch(extension_id):
        raise ValueError("INVALID EXTENSION ID")
    if not isinstance(executable, str):
        raise ValueError("INVALID HOST PATH")
    path = Path(executable)
    if (not path.is_absolute()
            or path.name != "MachineBraveNativeTitleMarker.py"
            or any(ord(c) < 32 or ord(c) == 127 for c in executable)):
        raise ValueError("INVALID HOST PATH")
    return {
        "name": HOST_NAME,
        "description": "MACHINE disposable opt-in transient title marker verification; no restore",
        "path": str(path),
        "type": "stdio",
        "allowed_origins": ["chrome-extension://" + extension_id + "/"],
    }


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        return 2
    try:
        value = generate(*args)
    except ValueError:
        return 2
    print(json.dumps(value, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
