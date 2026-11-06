#!/usr/bin/env python3
"""Explicit, interactive Fedora oFono package installation inside PHONE.

Prefer PackageKit's pkcon when available. Minimal Fedora desktops may instead
have DNF5 + Polkit, which require the same user's interactive authorization.
This helper never invokes an installer on import or without a real TTY and
the exact --interactive-ofono flag. It never auto-answers transaction prompts.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Callable, Any

from PhoneInstallCommandDiscovery import (
    find_os_program, trusted_program, trusted_dnf5,
)


def run_session(
    *,
    interactive: Callable[[], bool] = sys.stdin.isatty,
    find: Callable[[str], str | None] = find_os_program,
    runner: Callable[..., Any] = subprocess.run,
    hold: Callable[[str], str] = input,
) -> int:
    if interactive() is not True:
        print("The oFono installer requires an interactive terminal.")
        return 3

    pkcon = trusted_program("pkcon", find=find)
    if pkcon:
        backend = "PackageKit"
        command = [pkcon, "install", "ofono"]
    else:
        pkexec = trusted_program("pkexec", find=find)
        dnf5 = trusted_dnf5(find=find)
        if not (pkexec and dnf5):
            print("No supported embedded installer: PackageKit's pkcon or "
                  "both Polkit pkexec and DNF5 must be installed.")
            return 3
        backend = "Polkit / DNF5"
        # Force the interactive no-by-default behavior even when a user's
        # DNF5 configuration has assumeyes/defaultyes enabled.
        # pkexec requests normal system authorization; no password or
        # credential is supplied or handled by Social PHONE.
        command = [
            pkexec, dnf5,
            "--setopt=assumeyes=False",
            "--setopt=defaultyes=False",
            "install", "ofono",
        ]

    print("Social PHONE // Fedora oFono calling support")
    print("Requested package: ofono")
    print("Installer: " + backend)
    print("Review the package transaction and approve only if you agree.")
    print("Your Bluetooth pairing, media preferences and services stay unchanged by Social.")
    print("")
    try:
        result = runner(command, check=False)
        code = getattr(result, "returncode", 1)
    except Exception:
        print("The package installer could not complete the request.")
        code = 1
    print("")
    if code == 0:
        print("The package installer reports its transaction completed.")
        print("Return to PHONE and use CHECK AGAIN to independently verify oFono.")
    else:
        print("The package installer did not confirm completion.")
        print("Hands-free calling remains unverified.")
    try:
        hold("Press Enter to close this terminal and recheck PHONE...")
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
