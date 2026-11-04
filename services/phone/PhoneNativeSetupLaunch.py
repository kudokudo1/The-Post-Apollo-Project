#!/usr/bin/env python3
"""Open an installed native phone setup UI on an explicit Social PHONE choice.

One-shot launcher, NOT a phone pairing service, authorization gate, content
reader or daemon manager. BlueFerry/KDE Connect retain OS-native pairing and
phone-side consent. This helper never installs, pairs or logs identifiers.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from typing import Callable, Any

SCHEMA = "post-apollo.phone.native-setup-launch.v0"
TARGETS = {
    "iphone": ("blueferry-gtk", "blueferry-qt"),
    "android": ("kdeconnect-app",),
}
STATUS = frozenset({"OPEN_REQUESTED", "CLIENT_UNAVAILABLE", "LAUNCH_FAILED"})


def _result(target: str, status: str) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "execution": "USER_INITIATED_NATIVE_SETUP",
        "target": target,
        "status": status,
        "trustedPhoneLink": "UNVERIFIED",
        "routeEligible": False,
        "contentAccessEnabled": False,
    }


def open_setup(
    target: str,
    *,
    find_executable: Callable[[str], str | None] = shutil.which,
    launcher: Callable[..., Any] = subprocess.Popen,
) -> dict[str, object]:
    """Launch only a known desktop pairing UI, with no arguments or shell.

    OPEN_REQUESTED means only the process spawned. It does not certify that
    a window opened, a device paired, an app linked, or a grant was issued.
    Neither the target name nor the program path comes from device metadata.
    """
    if type(target) is not str or target not in TARGETS:
        return _result("UNSUPPORTED", "CLIENT_UNAVAILABLE")

    for executable in TARGETS[target]:
        try:
            path = find_executable(executable)
        except Exception:
            path = None
        if type(path) is not str or not os.path.isabs(path):
            continue
        # A resolved binary is explicit; no shell, arbitrary args, scripts,
        # flags, phone addresses, tokens, content or service commands.
        try:
            launcher(
                [path],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )
            return _result(target, "OPEN_REQUESTED")
        except Exception:
            # Hide executable paths and environmental errors from Social.
            return _result(target, "LAUNCH_FAILED")
    return _result(target, "CLIENT_UNAVAILABLE")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2 or args[0] != "--open" or args[1] not in TARGETS:
        print(json.dumps(_result("UNSUPPORTED", "CLIENT_UNAVAILABLE"),
                         sort_keys=True))
        return 2
    print(json.dumps(open_setup(args[1]), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
