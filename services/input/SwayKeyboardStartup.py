#!/usr/bin/env python3
"""Opt-in Sway keyboard startup fragment installer, v2.

The operator's ~/.config/sway/config is often a symlink to a Git checkout.
Treat the config and its resolved source as READ-ONLY; never rewrite or
replace either. Require its approved include before writing only our fragment.
Only an explicit apply action writes the managed fragment.
No Sway reload, key injection, shell, polling or privileged operations.
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
APPROVED_INCLUDE = "include ~/.config/sway/post-apollo-keyboard-locks.conf"
MODES = frozenset(("system", "on", "off"))
SAFE_PATH = re.compile(r"^/[A-Za-z0-9_./-]+$")


class LockConfigError(Exception):
    pass


def paths(config_home: Path | None = None):
    if config_home is None:
        configured = os.environ.get("XDG_CONFIG_HOME")
        config_home = Path(configured) if configured else Path.home() / ".config"
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


def read_config_without_writes(config: Path):
    """Accept an existing single/multi-hop symlink only if its final target
    is a regular file inside the operator's home, never outside it."""
    try:
        kind = config.lstat().st_mode
    except FileNotFoundError as exc:
        raise LockConfigError("DEFAULT_SWAY_CONFIG_MISSING") from exc
    if stat.S_ISLNK(kind):
        # config = <home>/.config/sway/config on a standard install. The
        # explicit config_home fixture form uses its parent as allowed root.
        home = config.parent.parent.parent.resolve(strict=True)
        try:
            target = config.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise LockConfigError("UNSAFE_SYMLINK_TARGET") from exc
        if target == home or not target.is_relative_to(home):
            raise LockConfigError("UNSAFE_SYMLINK_TARGET")
        return read_regular(target, required=True)
    return read_regular(config, required=True)


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
    # Legacy v1 installations can be recognized but are never rewritten.
    return START + f"include {fragment}\n" + END


def has_approved_include(config_source: str, fragment: Path) -> bool:
    active = [line.strip() for line in config_source.splitlines()
              if line.strip() and not line.lstrip().startswith("#")]
    approved_count = active.count(APPROVED_INCLUDE)
    legacy = include_block(fragment)
    legacy_count = config_source.count(legacy)
    if approved_count > 1 or legacy_count > 1:
        raise LockConfigError("CONFLICTING_INCLUDE")
    if (START in config_source or END in config_source) and legacy_count != 1:
        raise LockConfigError("CONFLICTING_INCLUDE")
    # Reject any additional active keyboard fragment include, not a silent
    # attempt to resolve precedence among conflicting configuration sources.
    other = [line for line in active if "post-apollo-keyboard-locks.conf" in line
             and line not in (APPROVED_INCLUDE, f"include {fragment}")]
    if other:
        raise LockConfigError("CONFLICTING_INCLUDE")
    if approved_count + legacy_count > 1:
        raise LockConfigError("CONFLICTING_INCLUDE")
    return approved_count == 1 or legacy_count == 1


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
    config_source = read_config_without_writes(config)
    if not has_approved_include(config_source, fragment):
        return {"status": "not_installed", "reason": "CONFIG_INCLUDE_MISSING"}
    fragment_source = read_regular(fragment, required=False)
    if fragment_source is None:
        return {"status": "not_installed", "reason": "FRAGMENT_MISSING"}
    return {"status": "installed", **installed_modes(fragment_source)}


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
    config_source = read_config_without_writes(config)
    if not has_approved_include(config_source, fragment):
        raise LockConfigError("CONFIG_INCLUDE_MISSING")
    old_fragment = read_regular(fragment, required=False)
    if old_fragment is not None:
        installed_modes(old_fragment)  # Never overwrite an unowned file.
    try:
        if old_fragment != desired_fragment:
            atomic_write(fragment, desired_fragment, 0o600)
    except OSError as exc:
        raise LockConfigError("FRAGMENT_WRITE_FAILED") from exc
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
