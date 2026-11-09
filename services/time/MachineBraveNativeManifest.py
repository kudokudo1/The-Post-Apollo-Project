#!/usr/bin/env python3
"""Build a *proposed* Chrome/Brave Linux native-host manifest. Never install it.

Only an operator can authorize copying the resulting manifest into a
browser's NativeMessagingHosts directory and enabling the host executable.
No ID or absolute executable path is known to this repository.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HOST_NAME = "org.postapollo.machine_brave_probe"
EXTENSION_ID = re.compile(r"[a-p]{32}\Z")


def generate(extension_id, host_executable):
    if not isinstance(extension_id, str) or not EXTENSION_ID.fullmatch(extension_id):
        raise ValueError("INVALID EXTENSION ID")
    if not isinstance(host_executable, str):
        raise ValueError("INVALID HOST PATH")
    path = Path(host_executable)
    if (not path.is_absolute() or path.name != "MachineBraveNativeProbe.py"
            or any(ord(c) < 32 or ord(c) == 127 for c in host_executable)):
        raise ValueError("INVALID HOST PATH")
    return {
        "name": HOST_NAME,
        "description": "Post-Apollo MACHINE one-shot read-only Brave connection probe",
        "path": str(path),
        "type": "stdio",
        "allowed_origins": ["chrome-extension://" + extension_id + "/"],
    }


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        return 2
    try:
        candidate = generate(*args)
    except ValueError:
        return 2
    print(json.dumps(candidate, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
