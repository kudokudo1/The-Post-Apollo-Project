#!/usr/bin/env python3
"""Explicit, interactive Fedora oFono package installation inside PHONE.

Prefer PackageKit's pkcon when available. Minimal Fedora desktops may instead
have DNF5 + Polkit, which require the same user's interactive authorization.
This helper never invokes an installer on import or without a real TTY and
the exact --interactive-ofono flag. It never auto-answers transaction prompts.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from typing import Callable, Any

from PhoneInstallCommandDiscovery import (
    find_os_program, trusted_program, trusted_dnf5,
)


def _ostree_host() -> bool:
    return os.path.exists("/run/ostree-booted")


def _ostree_idle(rpm_ostree: str, runner: Callable[..., Any]) -> bool:
    """Read-only check: no other pending/staged deployment may be displaced."""
    try:
        response = runner(
            [rpm_ostree, "status", "--json"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        if getattr(response, "returncode", None) != 0:
            return False
        status = json.loads(getattr(response, "stdout", ""))
        deployments = status.get("deployments") if type(status) is dict else None
        return (
            type(deployments) is list and bool(deployments)
            and all(type(item) is dict for item in deployments)
            and deployments[0].get("booted") is True
            and not any(item.get("staged") is True for item in deployments)
            and not any(item.get("booted") is True for item in deployments[1:])
        )
    except Exception:
        return False


def run_session(
    *,
    interactive: Callable[[], bool] = sys.stdin.isatty,
    find: Callable[[str], str | None] = find_os_program,
    runner: Callable[..., Any] = subprocess.run,
    hold: Callable[[str], str] = input,
    is_ostree: Callable[[], bool] | None = None,
    approve: Callable[[str], str] = input,
) -> int:
    if interactive() is not True:
        print("The oFono installer requires an interactive terminal.")
        return 3

    try:
        atomic = _ostree_host() if is_ostree is None else is_ostree()
        if type(atomic) is not bool:
            raise ValueError("unverified host")
    except Exception:
        print("Cannot determine the host installation type. No installation attempted.")
        return 3

    if atomic:
        # oFono is a host service. Toolbox DNF and ordinary mutable Fedora
        # installers cannot install it into the active Silverblue deployment.
        rpm_ostree = trusted_program("rpm-ostree", find=find)
        if not rpm_ostree:
            print("Trusted host rpm-ostree is unavailable. No installation attempted.")
            return 3
        if not _ostree_idle(rpm_ostree, runner):
            print("Cannot verify an idle Silverblue deployment with no pending "
                  "changes. Nothing installed; review rpm-ostree status first.")
            return 3
        print("Silverblue host: this stages ofono in a new OS deployment.")
        print("It does not install into the running system or reboot.")
        print("Existing BlueFerry, Bluetooth pairing and audio are not changed.")
        try:
            consent = approve("Type INSTALL OFONO to stage the next boot deployment: ")
        except (EOFError, KeyboardInterrupt):
            consent = ""
        if consent != "INSTALL OFONO":
            print("Canceled. No deployment requested.")
            return 1
        backend = "rpm-ostree (host deployment)"
        command = [rpm_ostree, "install", "ofono"]
    else:
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
        if atomic:
            print("The new deployment is NOT active. Verify it with rpm-ostree status.")
            print("Reboot separately when approved, then use PHONE / CHECK AGAIN.")
            print("Do not start oFono or enable PC calls before that verification.")
        else:
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
