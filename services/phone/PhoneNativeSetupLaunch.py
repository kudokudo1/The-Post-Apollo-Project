#!/usr/bin/env python3
"""Open an installed native phone setup UI on an explicit Social PHONE choice.

One-shot launcher, NOT a phone pairing service, authorization gate, content
reader or daemon manager. BlueFerry/KDE Connect retain OS-native pairing and
phone-side consent. This helper never installs, pairs or logs identifiers.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Callable, Any

SCHEMA = "post-apollo.phone.native-setup-launch.v0"
TARGETS = {
    "iphone": ("blueferry-quickshell", "blueferry-gtk", "blueferry-qt"),
    "android": ("kdeconnect-app",),
}
# Fedora setups often have blueferry-backend (with its CLI) but no GTK/Qt
# client. The terminal pairing wizard is officially supported and is selected
# only when a person explicitly asks for iPhone setup.
TERMINALS = (
    ("foot", ("-e",)),
    ("kitty", ("--hold",)),
    ("alacritty", ("-e",)),
    ("konsole", ("-e",)),
)
STAGE_APP_ID = "post-apollo-social-phone-setup"


def _has_blueferry_configuration() -> bool:
    # BlueFerry owns this file and the OS bond. Never read its identifiers or
    # create a second phone registry. File presence is NOT proof of pairing.
    try:
        return Path(os.path.expanduser("~/.config/blueferry/local.env")).is_file()
    except (OSError, ValueError):
        return False
STATUS = frozenset({"OPEN_REQUESTED", "CLIENT_UNAVAILABLE", "LAUNCH_FAILED"})


def _result(target: str, status: str, *, stage_candidate: bool = False) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "execution": "USER_INITIATED_NATIVE_SETUP",
        "target": target,
        "status": status,
        "stageCandidate": stage_candidate,
        "trustedPhoneLink": "UNVERIFIED",
        "routeEligible": False,
        "contentAccessEnabled": False,
    }


def open_setup(
    target: str,
    *,
    find_executable: Callable[[str], str | None] = shutil.which,
    launcher: Callable[..., Any] = subprocess.Popen,
    configured: Callable[[], bool] = _has_blueferry_configuration,
) -> dict[str, object]:
    """Launch a known desktop client or explicit native pairing wizard; no shell.

    OPEN_REQUESTED means only the process spawned. It does not certify that
    a window opened, a device paired, an app linked, or a grant was issued.
    Neither target nor executable path comes from device metadata.
    """
    if type(target) is not str or target not in TARGETS:
        return _result("UNSUPPORTED", "CLIENT_UNAVAILABLE")

    launch_failed = False
    for executable in TARGETS[target]:
        try:
            path = find_executable(executable)
        except Exception:
            path = None
        if type(path) is not str or not os.path.isabs(path):
            continue
        # A resolved GUI is explicit; no shell, arbitrary args, scripts,
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
            # Try another installed GUI client if available, never expose
            # executable paths or environmental errors to Social.
            launch_failed = True
    # Only the explicitly chosen iPhone setup may use the upstream wizard.
    # Launch a real interactive terminal, not a shell or automatic pair command.
    # A paired phone need not be re-paired; the user remains in control of
    # wizard prompts and can cancel before changing anything.
    if target == "iphone":
        try:
            wizard = find_executable("blueferry")
        except Exception:
            wizard = None
        if type(wizard) is str and os.path.isabs(wizard):
            try:
                existing_config = configured() is True
            except Exception:
                existing_config = False
            # A present BlueFerry config is handled by its normal terminal
            # CLIENT, not by re-running its forget/re-pair wizard.
            client_command = "tui" if existing_config else "pair-setup"
            for terminal, flags in TERMINALS:
                try:
                    terminal_path = find_executable(terminal)
                except Exception:
                    terminal_path = None
                if type(terminal_path) is not str or not os.path.isabs(terminal_path):
                    continue
                try:
                    command = ([terminal_path, "--app-id", STAGE_APP_ID,
                                *flags, wizard, client_command]
                               if terminal == "foot"
                               else [terminal_path, *flags, wizard, client_command])
                    launcher(
                        command,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                        close_fds=True,
                    )
                    return _result(target, "OPEN_REQUESTED",
                                   stage_candidate=terminal == "foot")
                except Exception:
                    launch_failed = True
    return _result(target, "LAUNCH_FAILED" if launch_failed else "CLIENT_UNAVAILABLE")


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
