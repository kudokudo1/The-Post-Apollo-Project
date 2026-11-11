#!/usr/bin/env python3
"""Opt-in Kitty scroll settings: no terminal restart, no synthetic input.

status: read-only; enroll: explicit backup + include; apply: write only an
owned fragment. Existing symlinked kitty.conf is not rewritten or replaced.
Kitty may auto-reload its configuration after confirmed user changes.
"""
from __future__ import annotations
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

HEADER = "# Post-Apollo Kitty scroll preferences // managed v1\n"
MAX_BYTES = 262144
FLOAT_RE = re.compile(r"^\d+(?:\.\d{1,2})?$")


class KittyConfigError(Exception):
    pass


def paths(home=None, base=None):
    home = Path(home) if home is not None else Path.home()
    if base is None:
        override = os.environ.get("KITTY_CONFIG_DIRECTORY")
        xdg = os.environ.get("XDG_CONFIG_HOME")
        base = Path(override) if override else (
            Path(xdg) / "kitty" if xdg else home / ".config" / "kitty"
        )
    base = Path(base)
    if not home.is_absolute() or not base.is_absolute():
        raise KittyConfigError("UNSUPPORTED_PATH")
    if base == home or not base.is_relative_to(home):
        raise KittyConfigError("CONFIG_OUTSIDE_HOME")
    if not base.is_dir() or base.is_symlink():
        raise KittyConfigError("CONFIG_DIR_UNAVAILABLE")
    return (base / "kitty.conf", base / "post-apollo-scroll.conf",
            base / "kitty.conf.post-apollo-before-scroll-v1.bak")


def read_regular(path, missing_ok=False):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except FileNotFoundError:
        if missing_ok:
            return None
        raise KittyConfigError("CONFIG_MISSING")
    except OSError as exc:
        raise KittyConfigError("UNSAFE_FILE") from exc
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_uid != os.getuid()):
            raise KittyConfigError("UNSAFE_FILE")
        if info.st_size > MAX_BYTES:
            raise KittyConfigError("FILE_TOO_LARGE")
        raw = os.read(fd, MAX_BYTES + 1)
        try:
            return raw.decode("utf-8"), stat.S_IMODE(info.st_mode)
        except UnicodeError as exc:
            raise KittyConfigError("INVALID_UTF8") from exc
    finally:
        os.close(fd)


def include_line(fragment):
    return "include " + str(fragment)


def enrolled(text, fragment):
    line = include_line(fragment)
    active = [x.strip() for x in text.splitlines()
              if x.strip() and not x.lstrip().startswith("#")]
    if active.count(line) > 1 or any(
        "post-apollo-scroll.conf" in x and x != line for x in active
    ):
        raise KittyConfigError("CONFLICTING_INCLUDE")
    return line in active


def factor(raw, minimum, maximum):
    if not isinstance(raw, str) or not FLOAT_RE.fullmatch(raw):
        raise KittyConfigError("INVALID_FACTOR")
    val = float(raw)
    if not math.isfinite(val) or not minimum <= val <= maximum:
        raise KittyConfigError("OUT_OF_RANGE")
    return val


def fragment_text(wheel, touch):
    w = factor(wheel, 0.5, 16)
    t = factor(touch, 0.25, 8)
    return (HEADER + "# Mouse wheel / high-precision Wayland touchpad.\n"
            + f"wheel_scroll_multiplier {w:.2f}\n"
            + f"touch_scroll_multiplier {t:.2f}\n")


def parse_fragment(text):
    if not text.startswith(HEADER):
        raise KittyConfigError("UNOWNED_FRAGMENT")
    matches = re.findall(
        r"^(wheel_scroll_multiplier|touch_scroll_multiplier) (\d+\.\d{2})$",
        text, re.MULTILINE)
    if len(matches) != 2 or len({x[0] for x in matches}) != 2:
        raise KittyConfigError("MODIFIED_FRAGMENT")
    settings = dict(matches)
    if text != fragment_text(settings["wheel_scroll_multiplier"],
                            settings["touch_scroll_multiplier"]):
        raise KittyConfigError("MODIFIED_FRAGMENT")
    return {"wheel": float(settings["wheel_scroll_multiplier"]),
            "touch": float(settings["touch_scroll_multiplier"])}


def atomic_write(path, content, mode):
    temp = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=".post-apollo-kitty-", delete=False
        ) as f:
            temp = Path(f.name)
            os.fchmod(f.fileno(), mode)
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
        temp = None
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def status(home=None, base=None):
    main, fragment, backup = paths(home, base)
    cfg = read_regular(main, missing_ok=True)
    if cfg is None:
        return {"status": "needs_config", "config": str(main)}
    included = enrolled(cfg[0], fragment)
    frag = read_regular(fragment, missing_ok=True)
    values = parse_fragment(frag[0]) if frag is not None else {}
    state = ("installed" if included and frag is not None
             else "needs_include" if not included else "needs_fragment")
    return {"status": state, "enrolled": included, "config": str(main),
            "fragment": str(fragment), "backup_exists": backup.exists(),
            **values}


def enroll(home=None, base=None):
    main, fragment, backup = paths(home, base)
    cfg, mode = read_regular(main)
    if enrolled(cfg, fragment):
        return {"status": "already_enrolled", "fragment": str(fragment)}
    if backup.exists() or backup.is_symlink():
        raise KittyConfigError("BACKUP_ALREADY_EXISTS")
    try:
        backup_fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                            | os.O_NOFOLLOW, 0o600)
        with os.fdopen(backup_fd, "wb") as sink:
            sink.write(cfg.encode("utf-8"))
            sink.flush()
            os.fsync(sink.fileno())
        new = cfg + ("" if not cfg or cfg.endswith("\n") else "\n")
        new += "\n# Post-Apollo optional Kitty scroll configuration\n"
        new += include_line(fragment) + "\n"
        atomic_write(main, new, mode)
    except OSError as exc:
        raise KittyConfigError("ENROLL_WRITE_FAILED") from exc
    return {"status": "enrolled", "backup": str(backup),
            "fragment": str(fragment), "runtime_verified": False}


def apply(wheel, touch, home=None, base=None):
    desired = fragment_text(wheel, touch)
    main, fragment, _ = paths(home, base)
    cfg, _mode = read_regular(main)
    if not enrolled(cfg, fragment):
        raise KittyConfigError("INCLUDE_MISSING")
    old = read_regular(fragment, missing_ok=True)
    if old is not None:
        parse_fragment(old[0])
    try:
        if old is None or old[0] != desired:
            atomic_write(fragment, desired, 0o600)
    except OSError as exc:
        raise KittyConfigError("FRAGMENT_WRITE_FAILED") from exc
    return {"status": "saved", "wheel": factor(wheel, 0.5, 16),
            "touch": factor(touch, 0.25, 8),
            "activation": "KITTY_CONFIG_RELOAD",
            "runtime_verified": False}


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        if args == ["status"]:
            out = status()
        elif args == ["enroll"]:
            out = enroll()
        elif len(args) == 3 and args[0] == "apply":
            out = apply(args[1], args[2])
        else:
            raise KittyConfigError("INVALID_ACTION")
        print(json.dumps(out, separators=(",", ":")))
        return 0
    except KittyConfigError as exc:
        print(json.dumps({"status": "unavailable", "code": str(exc)},
                         separators=(",", ":")))
        return 2


if __name__ == "__main__":
    sys.exit(main())
