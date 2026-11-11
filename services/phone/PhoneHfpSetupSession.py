#!/usr/bin/env python3
"""Explicit, portable oFono + WirePlumber HFP setup in Social PHONE's terminal.

This is NOT a phone pairing, call control, package installer or silent repair.
Read-only preflight runs before any confirmation. System service start, user
configuration creation and audio restart each require separate typed consent.
Supported: systemd desktop, WirePlumber >= 0.5 and an existing oFono unit.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Callable

from PhoneOfonoInstallSession import _review_then_exit

CONFIG_NAME = "51-bluez-ofono.conf"
CONFIG_TEXT = 'monitor.bluez.properties = {\n  bluez5.hfphsp-backend = "ofono"\n}\n'
BACKEND = re.compile(r"\bbluez5\.hfphsp-backend\s*=\s*([^\s}]+)")
VERSION = re.compile(r"Compiled with libwireplumber\s+(\d+)\.(\d+)")
ACK_START = "START OFONO"
ACK_CONFIG = "CONFIGURE HFP"
ACK_RESTART = "RESTART WIREPLUMBER"


def _call(argv: list[str], runner: Callable[..., object]) -> tuple[bool, str]:
    try:
        result = runner(argv, capture_output=True, text=True, timeout=20, check=False)
        output = getattr(result, "stdout", "")
        if type(output) is not str or len(output) > 32768:
            return False, ""
        return getattr(result, "returncode", 1) == 0, output.strip()
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return False, ""


def _service(runner: Callable[..., object]) -> tuple[str, str]:
    ok, output = _call(
        ["systemctl", "show", "ofono.service", "--no-pager",
         "-p", "LoadState", "-p", "ActiveState"], runner)
    if not ok:
        return "unknown", "unknown"
    values = dict(line.split("=", 1) for line in output.splitlines()
                  if line.count("=") == 1 and line.split("=", 1)[0]
                  in ("LoadState", "ActiveState"))
    return values.get("LoadState", "unknown"), values.get("ActiveState", "unknown")


def _wireplumber_supported(runner: Callable[..., object]) -> bool:
    ok, version = _call(["wireplumber", "--version"], runner)
    match = VERSION.search(version) if ok else None
    return bool(match and tuple(map(int, match.groups())) >= (0, 5))


def _user_audio_active(runner: Callable[..., object]) -> bool:
    ok, value = _call(
        ["systemctl", "--user", "is-active", "wireplumber.service"], runner)
    return ok and value == "active"


def _dbus_allowed(runner: Callable[..., object]) -> bool:
    ok, _ = _call(
        ["busctl", "--system", "call", "org.ofono", "/", "org.ofono.Manager",
         "GetModems"], runner)
    return ok


def _config_status(target: Path, roots: tuple[Path, ...]) -> str:
    """Fail closed on symlinks, unreadable files or competing HFP properties.

    A matching distro-level ofono override needs no user-level file.
    Never overwrite or remove an existing configuration.
    """
    desired = False
    for root in roots:
        if root.is_symlink():
            return "CONFLICT"
        if not root.exists():
            continue
        if not root.is_dir():
            return "CONFLICT"
        try:
            files = sorted(root.glob("*.conf"))
        except OSError:
            return "CONFLICT"
        for item in files:
            if item.is_symlink() or not item.is_file():
                return "CONFLICT"
            try:
                data = item.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                return "CONFLICT"
            if item == target and data != CONFIG_TEXT:
                return "CONFLICT"
            for line in data.splitlines():
                match = BACKEND.search(line.split("#", 1)[0])
                if not match:
                    continue
                if match.group(1).strip('"') != "ofono":
                    return "CONFLICT"
                desired = True
    if target.is_symlink():
        return "CONFLICT"
    return "CONFIGURED" if desired else "NEEDS_CONFIG"


def _write_new_config(target: Path) -> bool:
    """Only create an absent user-owned file, never replace a prior choice."""
    if target.is_symlink() or target.exists():
        return False
    parent = target.parent
    base = parent.parent
    if base.is_symlink() or parent.is_symlink():
        return False
    try:
        parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(target, flags, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as output:
                output.write(CONFIG_TEXT)
        except Exception:
            if target.is_file() and not target.is_symlink():
                target.unlink()
            raise
        return target.read_text(encoding="utf-8") == CONFIG_TEXT
    except (OSError, UnicodeError, ValueError):
        return False


def _rollback_our_file(target: Path) -> None:
    try:
        if (not target.is_symlink() and target.is_file()
                and target.read_text(encoding="utf-8") == CONFIG_TEXT):
            target.unlink()
    except (OSError, UnicodeError):
        pass


def run_session(
    *, interactive: Callable[[], bool] = sys.stdin.isatty,
    runner: Callable[..., object] = subprocess.run,
    approve: Callable[[str], str] = input,
    home: Path | None = None,
    system_roots: tuple[Path, ...] | None = None,
    sudo: str | None = None,
    review: Callable[[], None] = _review_then_exit,
) -> int:
    if interactive() is not True:
        print("Social PHONE requires an interactive, user-approved terminal.")
        return 3
    directory = home if home is not None else Path.home()
    user_root = directory / ".config" / "wireplumber" / "wireplumber.conf.d"
    target = user_root / CONFIG_NAME
    roots = (user_root, *(system_roots if system_roots is not None else (
        Path("/etc/wireplumber/wireplumber.conf.d"),
        Path("/usr/share/wireplumber/wireplumber.conf.d"),
    )))

    print("Social PHONE // HANDS-FREE CALLING SETUP")
    print("This uses an installed oFono service on systemd + WirePlumber 0.5+.")
    print("No package install, iPhone pairing, calls opt-in or reboot is performed.")
    print("A system service start and WirePlumber restart may interrupt Bluetooth audio.")
    print("Every change requires its own exact confirmation.")
    if not _wireplumber_supported(runner) or not _user_audio_active(runner):
        print("WirePlumber 0.5+ and a running user WirePlumber service are required.")
        return 2
    load, active = _service(runner)
    if load != "loaded" or active not in ("active", "inactive"):
        print("A healthy installed oFono systemd unit is required.")
        print("On non-Fedora distributions, install oFono with the distro's package manager.")
        return 2
    current = _config_status(target, roots)
    if current == "CONFLICT":
        print("Existing HFP configuration conflicts or cannot be verified. No changes made.")
        print("Review other WirePlumber HFP backend settings; no file was overwritten.")
        return 2
    if active == "inactive":
        sudo_path = sudo if sudo is not None else (
            "/usr/bin/sudo" if Path("/usr/bin/sudo").is_file() else "/bin/sudo"
        )
        if (sudo_path not in ("/usr/bin/sudo", "/bin/sudo")
                or not Path(sudo_path).is_file()
                or not Path("/usr/bin/systemctl").is_file()):
            print("Trusted sudo/systemctl is unavailable. No service change attempted.")
            return 2
        if approve("Type START OFONO to start the system service once: ") != ACK_START:
            print("Canceled. No changes made.")
            return 1
        ok, _ = _call([sudo_path, "/usr/bin/systemctl", "start", "ofono.service"], runner)
        if not ok or _service(runner) != ("loaded", "active"):
            print("oFono service did not become active. No audio config changed.")
            review()
            return 2
        print("oFono service is active (not enabled permanently).")

    if not _dbus_allowed(runner):
        print("Your user cannot confirm oFono GetModems on the system D-Bus.")
        print("Do not widen D-Bus permissions automatically; review the policy separately.")
        review()
        return 2

    created = False
    if current == "NEEDS_CONFIG":
        print("Proposed new file: ~/.config/wireplumber/wireplumber.conf.d/"
              + CONFIG_NAME)
        print(CONFIG_TEXT)
        print("The file selects only the ofono HFP/HSP backend, not media routing.")
        if approve("Type CONFIGURE HFP to create this new user file: ") != ACK_CONFIG:
            print("Canceled. No audio config changed.")
            review()
            return 1
        if _config_status(target, roots) != "NEEDS_CONFIG" or not _write_new_config(target):
            print("Configuration changed or could not be created. No overwrite attempted.")
            review()
            return 2
        created = True
        if approve("Type RESTART WIREPLUMBER to apply (rollback if declined): ") != ACK_RESTART:
            _rollback_our_file(target)
            print("Restart declined; newly created file removed.")
            review()
            return 1
        if _config_status(target, roots) != "CONFIGURED":
            _rollback_our_file(target)
            print("HFP configuration changed before restart; review it separately.")
            review()
            return 2
        ok, _ = _call(
            ["systemctl", "--user", "restart", "wireplumber.service"], runner)
        if not ok or not _user_audio_active(runner):
            _rollback_our_file(target)
            _call(["systemctl", "--user", "restart", "wireplumber.service"], runner)
            print("Audio restart not confirmed. New file rolled back; check WirePlumber.")
            review()
            return 2

    print("oFono service and user D-Bus access verified.")
    if _config_status(target, roots) != "CONFIGURED":
        print("Configuration did not remain valid; check before enabling calls.")
        review()
        return 2
    print("WirePlumber oFono HFP configuration present" +
          (" and restarted." if created else " (no changes needed)."))
    print("HFP phone link and microphone/speaker remain UNVERIFIED.")
    print("Return to PHONE, refresh and explicitly select CALLS ON PC.")
    review()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args != ["--interactive-hfp"]:
        return 2
    return run_session()


if __name__ == "__main__":
    raise SystemExit(main())
