#!/usr/bin/env python3
"""An explicitly requested, interactive Fedora oFono package session.

Runs inside a dedicated foot terminal staged into the Social PHONE panel.
Only PackageKit's interactive CLI can request the exact 'ofono' package.
No noninteractive confirmation, root shell, credentials, DNF, auto service
activation, Bluetooth changes, scripts from network or arbitrary arguments.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Callable, Any


def run_session(
    *,
    interactive: Callable[[], bool] = sys.stdin.isatty,
    find: Callable[[str], str | None] = shutil.which,
    runner: Callable[..., Any] = subprocess.run,
    hold: Callable[[str], str] = input,
) -> int:
    if interactive() is not True:
        print("The oFono installer requires an interactive terminal.")
        return 3
    try:
        path = find("pkcon")
    except Exception:
        path = None
    if (type(path) is not str or not os.path.isabs(path)
            or os.path.basename(path) != "pkcon"):
        print("PackageKit's interactive installer is unavailable.")
        return 3

    print("Social PHONE // Fedora oFono calling support")
    print("Package requested: ofono")
    print("Review the PackageKit transaction and approve it only if you agree.")
    print("No phone pairing, audio routing, or system service is changed by Social.")
    print("")
    try:
        result = runner([path, "install", "ofono"], check=False)
        code = getattr(result, "returncode", 1)
    except Exception:
        print("PackageKit could not complete the installation request.")
        code = 1
    print("")
    if code == 0:
        print("PackageKit reports that its transaction completed.")
        print("Return to PHONE and use CHECK AGAIN to verify actual installation.")
    else:
        print("PackageKit did not confirm a completed installation.")
        print("No calling or hands-free audio connection has been verified.")
    try:
        hold("Press Enter to close this setup terminal and recheck PHONE...")
    except (EOFError, KeyboardInterrupt):
        pass
    return 0 if code == 0 else 2


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args != ["--interactive-ofono"]:
        return 2
    return run_session()


if __name__ == "__main__":
    raise SystemExit(main())
