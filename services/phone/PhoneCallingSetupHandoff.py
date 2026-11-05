#!/usr/bin/env python3
"""Explicit, non-installing Fedora GUI handoff for Social PHONE calling support.

The button opens a supported system package GUI for the official 'ofono'
package. That GUI owns repository selection, review, authorization, download,
and installation. This helper never executes privileged installation commands,
package transactions, shell commands, service mutations or phone identifiers.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Callable

from PhoneCallPrerequisites import diagnose

SCHEMA = "post-apollo.phone.calling-setup-handoff.v0"
PACKAGE_NAME = "ofono"
GUI_CLIENTS = (
    ("gnome-software", ("--details-pkg=ofono",)),
    ("gpk-install-package-name", ("ofono",)),
)


def _fedora() -> bool:
    """Read only an OS vendor identifier, never user-controlled device data."""
    try:
        lines = Path("/etc/os-release").read_text(encoding="utf-8").splitlines()
        for line in lines:
            key, sep, value = line.partition("=")
            if sep and key.strip() == "ID":
                return value.strip().strip('"') == "fedora"
        return False
    except (OSError, UnicodeError, ValueError):
        return False


def _result(status: str) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "execution": "USER_INITIATED_GUI_HANDOFF",
        "status": status,
        "package": PACKAGE_NAME,
        "installerOpened": status == "GUI_OPEN_REQUESTED",
        "packageInstalled": False,
        "hfpVerified": False,
        "trustedPhoneLink": "UNVERIFIED",
        "contentAccessEnabled": False,
    }


def open_support(
    *,
    prerequisite: Callable[[], object] = diagnose,
    is_fedora: Callable[[], bool] = _fedora,
    find: Callable[[str], str | None] = shutil.which,
    launcher: Callable[..., Any] = subprocess.Popen,
) -> dict[str, object]:
    # A GUI selection is only offered for the truly missing Fedora package
    # case. A stopped/failed service must be fixed by the owning audio team,
    # not "reinstalled" from a phone menu.
    try:
        evidence = prerequisite()
    except Exception:
        return _result("DIAGNOSIS_UNAVAILABLE")
    if (type(evidence) is not dict
            or evidence.get("schema") != "post-apollo.phone.calls-prerequisites.v0"
            or evidence.get("execution") != "READ_ONLY_CALL_DIAGNOSIS"
            or evidence.get("trustedPhoneLink") != "UNVERIFIED"
            or evidence.get("contentAccessEnabled") is not False
            or evidence.get("hfpVerified") is not False):
        return _result("DIAGNOSIS_UNAVAILABLE")
    if evidence.get("state") != "PACKAGE_NOT_INSTALLED" or (
        evidence.get("package") != "NOT_INSTALLED"
        or evidence.get("serviceLoad") != "not-found"
    ):
        return _result("NOT_APPLICABLE")
    try:
        if is_fedora() is not True:
            return _result("UNSUPPORTED_HOST")
    except Exception:
        return _result("UNSUPPORTED_HOST")

    failed = False
    for program, args in GUI_CLIENTS:
        try:
            executable = find(program)
        except Exception:
            executable = None
        if (type(executable) is not str or not os.path.isabs(executable)
                or os.path.basename(executable) != program):
            continue
        try:
            launcher(
                [executable, *args],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )
            # A successful Popen does not mean installation happened.
            return _result("GUI_OPEN_REQUESTED")
        except Exception:
            failed = True
    return _result("GUI_LAUNCH_FAILED" if failed else "GUI_UNAVAILABLE")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args != ["--open-ofono"]:
        value = _result("EXPLICIT_ACTION_REQUIRED")
        print(json.dumps(value, sort_keys=True))
        return 2
    value = open_support()
    print(json.dumps(value, sort_keys=True))
    # A missing GUI is still a successfully reported diagnosis, not a crash.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
