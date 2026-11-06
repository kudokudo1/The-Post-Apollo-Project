#!/usr/bin/env python3
"""Explicit Fedora oFono installer handoff for Social PHONE.

The GNOME Software app-details route does not reliably show system-only RPMs.
Prefer an interactive PackageKit transaction in a specially tagged foot window
that PHONE's existing Stage Director can position inside its own panel.
PackageKit handles transaction review and any OS authorization. No automatic
confirmation, system modifications, phone pairing or BlueFerry activation here.
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
from PhoneInstallCommandDiscovery import (
    find_os_program, trusted_program, trusted_dnf5,
)
from PhoneStageDirector import INSTALL_APP_ID, _read_tree, _stage_actor, _exe

SCHEMA = "post-apollo.phone.calling-setup-handoff.v0"
PACKAGE_NAME = "ofono"
# No external fallback: callers explicitly requested the in-PHONE stage.


def _fedora() -> bool:
    try:
        lines = Path("/etc/os-release").read_text(encoding="utf-8").splitlines()
        for line in lines:
            key, sep, value = line.partition("=")
            if sep and key.strip() == "ID":
                return value.strip().strip('"') == "fedora"
        return False
    except (OSError, UnicodeError, ValueError):
        return False


def _installer_active() -> bool:
    """Already-running exact foot actor, not another user's terminal/window."""
    try:
        actor = _stage_actor(_read_tree(), _exe, INSTALL_APP_ID)
        return actor is not None and actor.get("visible") is True
    except Exception:
        return False


# Fixed identifiers only: do not return command paths, environment variables,
# subprocess output, host usernames, or other local system details.
TOOL_IDS = ("FOOT", "PYTHON3", "INSTALLER_HELPER", "PKCON", "PKEXEC", "DNF5")


def _result(status: str, missing: tuple[str, ...] = ()) -> dict[str, object]:
    if (type(missing) is not tuple
            or any(x not in TOOL_IDS or type(x) is not str for x in missing)
            or len(set(missing)) != len(missing)):
        missing = ()
    return {
        "schema": SCHEMA,
        "execution": "USER_INITIATED_INSTALLER_HANDOFF",
        "status": status,
        "package": PACKAGE_NAME,
        "missingTools": list(missing),
        "installerOpened": status == "GUI_OPEN_REQUESTED",
        "stageCandidate": status in (
            "STAGED_TERMINAL_REQUESTED", "STAGED_TERMINAL_EXISTING",
        ),
        "packageInstalled": False,
        "hfpVerified": False,
        "trustedPhoneLink": "UNVERIFIED",
        "contentAccessEnabled": False,
    }


def open_support(
    *,
    prerequisite: Callable[[], object] = diagnose,
    is_fedora: Callable[[], bool] = _fedora,
    find: Callable[[str], str | None] = find_os_program,
    launcher: Callable[..., Any] = subprocess.Popen,
    already_open: Callable[[], bool] = _installer_active,
) -> dict[str, object]:
    """Launch only after exact missing-package diagnosis and an explicit click."""
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
    if (evidence.get("state") != "PACKAGE_NOT_INSTALLED"
            or evidence.get("package") != "NOT_INSTALLED"
            or evidence.get("serviceLoad") != "not-found"):
        return _result("NOT_APPLICABLE")
    try:
        if is_fedora() is not True:
            return _result("UNSUPPORTED_HOST")
    except Exception:
        return _result("UNSUPPORTED_HOST")

    # Never launch a second PackageKit transaction while the original exact
    # installer actor remains open, including after navigating away from PHONE.
    try:
        if already_open() is True:
            return _result("STAGED_TERMINAL_EXISTING")
    except Exception:
        return _result("STAGE_UNAVAILABLE")


    foot = trusted_program("foot", find=find)
    pkcon = trusted_program("pkcon", find=find)
    pkexec = trusted_program("pkexec", find=find)
    dnf5 = trusted_dnf5(find=find)
    python = trusted_program("python3", find=find)
    session_script = Path(__file__).with_name("PhoneOfonoInstallSession.py")
    # Fedora minimalist/Sway installs may omit PackageKit's pkcon client.
    # The alternate is a *user-authorized* Polkit + DNF5 transaction in the
    # SAME embedded foot terminal, never an automatic installation.
    backend_ready = bool(pkcon or (pkexec and dnf5))
    if not (foot and python and session_script.is_file()):
        absent = tuple(
            name for name, ready in (
                ("FOOT", bool(foot)),
                ("PYTHON3", bool(python)),
                ("INSTALLER_HELPER", session_script.is_file()),
            ) if not ready
        )
        return _result("TERMINAL_UNAVAILABLE", absent)
    if not backend_ready:
        # A failed installation should explain which executable paths were
        # unavailable in the running PHONE environment. Not a package audit:
        # this is only a sanitized executable-discovery result.
        absent = tuple(
            name for name, ready in (
                ("PKCON", bool(pkcon)),
                ("PKEXEC", bool(pkexec)),
                ("DNF5", bool(dnf5)),
            ) if not ready
        )
        return _result("PACKAGE_MANAGER_UNAVAILABLE", absent)
    try:
        launcher(
            [foot, "--app-id", INSTALL_APP_ID, "-e", python,
             str(session_script), "--interactive-ofono"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
        return _result("STAGED_TERMINAL_REQUESTED")
    except Exception:
        return _result("GUI_LAUNCH_FAILED")

def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args != ["--open-ofono"]:
        print(json.dumps(_result("EXPLICIT_ACTION_REQUIRED"), sort_keys=True))
        return 2
    result = open_support()
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
