#!/usr/bin/env python3
"""Safely opt in to Koinoikos Focus Mode without overwriting a custom Sway config.

No automatic Sway reload, Quickshell restart, or native glow recoloring.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import os
import re
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
INCLUDE = ROOT / "config/sway/koinoikos-focus.conf"


def updated_text(original: str, include_path: Path) -> str:
    """Append only our include, idempotently. Do not normalize user formatting."""
    include_line = "include " + str(include_path)
    if include_line in original.splitlines():
        return original
    prefix = "" if not original or original.endswith("\n") else "\n"
    return original + prefix + "\n# Koinoikos // opt-in relationship focus mode\n" + include_line + "\n"


def checked_config(config: Path, candidate_text: str, sway_bin: str) -> tuple[bool, str]:
    """Validate a candidate beside the real config before touching the original."""
    fd, name = tempfile.mkstemp(prefix=".koinoikos-check-", suffix=".conf",
                                dir=str(config.parent), text=True)
    candidate = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(candidate_text)
        try:
            run = subprocess.run([sway_bin, "-C", "-c", str(candidate)],
                                 text=True, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, check=False, timeout=25)
            return run.returncode == 0, (run.stdout + "\n" + run.stderr).strip()
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, str(exc)
    finally:
        candidate.unlink(missing_ok=True)


def running_compositor_executable() -> str | None:
    """Resolve the compositor that owns this session's Sway IPC socket.

    Never assume that plain /usr/bin/sway understands the features of a
    running SwayFX / SwayPX fork. Linux Sway sockets encode their owner's PID.
    Match the current UID, require a live Unix socket and a Sway-family
    executable, and validate with the *actual running executable*.
    """
    socket_path = os.environ.get("SWAYSOCK") or os.environ.get("I3SOCK") or ""
    match = re.fullmatch(r"sway-ipc\.(\d+)\.(\d+)\.sock",
                         Path(socket_path).name)
    if match is None or int(match.group(1)) != os.getuid():
        return None

    if not Path(socket_path).is_socket():
        return None

    executable = Path("/proc") / match.group(2) / "exe"
    try:
        target_name = Path(os.readlink(executable).removesuffix(" (deleted)")).name.lower()
    except (OSError, RuntimeError):
        return None

    if "sway" not in target_name:
        return None

    # /proc/<pid>/exe refers to the binary of the exact Sway session
    # identified by SWAYSOCK, even when PATH contains stock sway instead.
    return str(executable)


def resolve_validator(sway_bin: str | None) -> tuple[str | None, str]:
    if sway_bin:
        return sway_bin, sway_bin
    running = running_compositor_executable()
    if running:
        try:
            description = os.readlink(running)
        except OSError:
            description = running
        return running, description
    return None, (
        "Could not identify the running Sway/SwayFX/SwayPX executable from "
        "SWAYSOCK. No config changed. Pass --sway /absolute/path/to/"
        "your-running-compositor to validate explicitly."
    )


def enable(config: Path, sway_bin: str | None = None) -> tuple[bool, str]:
    # Sway dotfile managers often expose ~/.config/sway/config as a symlink
    # into their repository. Resolve its target, never os.replace() the link.
    # Keep the original config path when validating: an include in the
    # config may be relative to the location Sway was asked to load.
    config = config.expanduser()
    try:
        target = config.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        return False, "Sway config path is missing or cannot be resolved: " + str(exc)
    if not target.is_file():
        return False, "Sway config is not a regular file: " + str(config)
    include = INCLUDE.resolve()
    if not include.is_file():
        return False, "Focus mode include not found: " + str(include)

    original = target.read_text(encoding="utf-8")
    candidate = updated_text(original, include)
    if candidate == original:
        return True, "Focus Mode include already present; no changes made."

    validator, description = resolve_validator(sway_bin)
    if validator is None:
        return False, description

    valid, evidence = checked_config(config, candidate, validator)
    if not valid:
        return False, ("Running-compositor config validation failed "
                       + "(" + description + "); original untouched.\n"
                       + evidence)

    # A user or dotfile manager might edit or retarget the link during
    # validation. Refuse to clobber a newer version or another target.
    if config.resolve(strict=True) != target or target.read_text(encoding="utf-8") != original:
        return False, "Sway config changed during validation; nothing overwritten."

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = target.with_name(target.name + ".before-koinoikos-" + stamp + ".bak")
    suffix = 2
    while backup.exists():
        backup = target.with_name(
            target.name + ".before-koinoikos-" + stamp + "-" + str(suffix) + ".bak")
        suffix += 1

    # Back up the real file, then atomically replace it in its own folder.
    # The original config symlink (including any relative link chain) stays
    # exactly as it was, still pointing to this validated target.
    shutil.copy2(target, backup)
    fd, name = tempfile.mkstemp(prefix=".koinoikos-write-", suffix=".conf",
                                dir=str(target.parent), text=True)
    dest = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(candidate)
        os.chmod(dest, stat.S_IMODE(target.stat().st_mode))
        if config.resolve(strict=True) != target or target.read_text(encoding="utf-8") != original:
            return False, ("Sway config changed before installation; original and "
                           "its backup preserved, no replacement performed.")
        os.replace(dest, target)
    finally:
        dest.unlink(missing_ok=True)

    suffix = " (symlink preserved)" if config.is_symlink() else ""
    return True, ("Enabled after compositor validation with "
                  + description + suffix
                  + ". Original backed up at " + str(backup)
                  + "\nNo compositor reload performed. "
                  + "Restart Quickshell safely, then run: swaymsg reload")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path,
                        default=Path("~/.config/sway/config"),
                        help="Your actual Sway config (default: ~/.config/sway/config)")
    parser.add_argument("--sway", default=None,
                        help="Explicit Sway/SwayPX validation binary; "
                             "by default, detect the running compositor "
                             "from SWAYSOCK and /proc/<pid>/exe")
    args = parser.parse_args(argv)
    success, message = enable(args.config, args.sway)
    print(message, file=sys.stdout if success else sys.stderr)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
