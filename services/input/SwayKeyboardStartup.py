#!/usr/bin/env python3
"""Opt-in startup lock configuration for the default user Sway config.

No Sway reload, key injection, polling, privileged operations or shell usage.
Only an explicit apply action may edit these two managed user config files.
The caller must not claim this works for a custom Sway --config path.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

MAX_BYTES = 256 * 1024
HEADER = "# Post-Apollo keyboard startup locks // managed v1\n"
START = "# BEGIN POST-APOLLO KEYBOARD LOCKS V1\n"
END = "# END POST-APOLLO KEYBOARD LOCKS V1\n"
MODES = frozenset(("system", "on", "off"))
SAFE_PATH = re.compile(r"^/[A-Za-z0-9_./-]+$")


class LockConfigError(Exception):
    pass


def paths(config_home: Path | None = None):
    if config_home is None:
        configured = os.environ.get("XDG_CONFIG_HOME")
        if configured:
            config_home = Path(configured)
        else:
            config_home = Path.home() / ".config"
    config_home = Path(config_home)
    sway = config_home / "sway"
    config = sway / "config"
    fragment = sway / "post-apollo-keyboard-locks.conf"
    if not config_home.is_absolute() or not SAFE_PATH.fullmatch(str(fragment)):
        raise LockConfigError("UNSUPPORTED_CONFIG_PATH")
    for item in (config_home, sway):
        if item.is_symlink() or not item.is_dir():
            raise LockConfigError("SWAY_DIRECTORY_UNAVAILABLE")
    return config, fragment


def read_regular(path: Path, required: bool):
    try:
        info = path.lstat()
    except FileNotFoundError:
        if required:
            raise LockConfigError("DEFAULT_SWAY_CONFIG_MISSING")
        return None
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise LockConfigError("UNSAFE_CONFIG_FILE")
    if info.st_size > MAX_BYTES:
        raise LockConfigError("CONFIG_TOO_LARGE")
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeError, OSError) as exc:
        raise LockConfigError("CONFIG_UNREADABLE") from exc


def fragment_text(num: str, caps: str) -> str:
    if num not in MODES or caps not in MODES:
        raise LockConfigError("INVALID_MODE")
    lines = [HEADER, "# Startup defaults only; physical keys may still toggle.\n"]
    for lock, mode in (("numlock", num), ("capslock", caps)):
        if mode != "system":
            setting = "enabled" if mode == "on" else "disabled"
            lines.append(f"input type:keyboard xkb_{lock} {setting}\n")
    return "".join(lines)


def include_block(fragment: Path) -> str:
    return START + f"include {fragment}\n" + END


def installed_modes(fragment: str):
    if not fragment.startswith(HEADER):
        raise LockConfigError("UNOWNED_FRAGMENT")
    modes = {"num": "system", "caps": "system"}
    for lock, choice in (("numlock", "num"), ("capslock", "caps")):
        hits = re.findall(rf"^input type:keyboard xkb_{lock} (enabled|disabled)$",
                          fragment, re.MULTILINE)
        if len(hits) > 1:
            raise LockConfigError("DUPLICATE_LOCK_RULE")
        if hits:
            modes[choice] = "on" if hits[0] == "enabled" else "off"
    if fragment != fragment_text(modes["num"], modes["caps"]):
        raise LockConfigError("MODIFIED_FRAGMENT")
    return modes


def inspect(config_home: Path | None = None):
    config, fragment = paths(config_home)
    config_source = read_regular(config, required=True)
    fragment_source = read_regular(fragment, required=False)
    block = include_block(fragment)
    if START not in config_source and END not in config_source:
        return {"status": "not_installed"}
    if config_source.count(START) != 1 or config_source.count(END) != 1:
        raise LockConfigError("CONFLICTING_INCLUDE")
    if block not in config_source:
        raise LockConfigError("CONFLICTING_INCLUDE")
    if fragment_source is None:
        raise LockConfigError("FRAGMENT_MISSING")
    modes = installed_modes(fragment_source)
    return {"status": "installed", **modes}


def atomic_write(path: Path, content: str, mode: int):
    name = None
    try:
        with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=str(path.parent),
                prefix=".post-apollo-locks-", delete=False) as handle:
            name = Path(handle.name)
            os.fchmod(handle.fileno(), mode)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
        name = None
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if name is not None:
            name.unlink(missing_ok=True)


def apply(num: str, caps: str, config_home: Path | None = None):
    desired_fragment = fragment_text(num, caps)
    config, fragment = paths(config_home)
    old_config = read_regular(config, required=True)
    old_fragment = read_regular(fragment, required=False)
    if old_fragment is not None:
        installed_modes(old_fragment)  # only overwrite our own exact format
    block = include_block(fragment)
    if START in old_config or END in old_config:
        if old_config.count(START) != 1 or old_config.count(END) != 1:
            raise LockConfigError("CONFLICTING_INCLUDE")
        if block not in old_config:
            raise LockConfigError("CONFLICTING_INCLUDE")
        new_config = old_config
    else:
        if f"include {fragment}" in old_config:
            raise LockConfigError("EXISTING_UNMANAGED_INCLUDE")
        new_config = old_config.rstrip("\n") + "\n\n" + block
    old_mode = stat.S_IMODE(config.stat().st_mode)
    try:
        if old_fragment != desired_fragment:
            atomic_write(fragment, desired_fragment, 0o600)
        if new_config != old_config:
            atomic_write(config, new_config, old_mode)
    except OSError as exc:
        # Best-effort rollback of fragment if an include update fails.
        try:
            if old_fragment is None:
                fragment.unlink(missing_ok=True)
            elif old_fragment != desired_fragment:
                atomic_write(fragment, old_fragment, 0o600)
        except OSError:
            pass
        raise LockConfigError("CONFIG_WRITE_FAILED") from exc
    return {"status": "installed", "num": num, "caps": caps,
            "activation": "NEXT_SWAY_START", "runtime_changed": False}


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        if args == ["status"]:
            result = inspect()
        elif len(args) == 3 and args[0] == "apply":
            result = apply(args[1], args[2])
        else:
            raise LockConfigError("INVALID_ACTION")
        print(json.dumps(result, separators=(",", ":")))
        return 0
    except LockConfigError as exc:
        print(json.dumps({"status": "unavailable", "code": str(exc)},
                         separators=(",", ":")))
        return 2


if __name__ == "__main__":
    sys.exit(main())
