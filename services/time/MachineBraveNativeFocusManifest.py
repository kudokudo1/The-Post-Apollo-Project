#!/usr/bin/env python3
"""Propose a separate native host manifest for a disposable Brave trial.

Prints JSON only; never writes, registers, launches Brave or touches HOME.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

HOST_NAME = "org.postapollo.machine_brave_focus_observe"
EXTENSION_ID = re.compile(r"[a-p]{32}\Z")


def generate(extension_id, host_executable):
    if not isinstance(extension_id, str) or not EXTENSION_ID.fullmatch(extension_id):
        raise ValueError("INVALID EXTENSION ID")
    if not isinstance(host_executable, str):
        raise ValueError("INVALID HOST PATH")
    path = Path(host_executable)
    if (not path.is_absolute()
            or path.name != "MachineBraveNativeFocusObserve.py"
            or any(ord(c) < 32 or ord(c) == 127 for c in host_executable)):
        raise ValueError("INVALID HOST PATH")
    return {
        "name": HOST_NAME,
        "description": "MACHINE separate opt-in read-only Sway focus observation; no pairing or restoration",
        "path": str(path),
        "type": "stdio",
        "allowed_origins": ["chrome-extension://" + extension_id + "/"],
    }


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 2:
        return 2
    try:
        proposed = generate(*arguments)
    except ValueError:
        return 2
    print(json.dumps(proposed, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
