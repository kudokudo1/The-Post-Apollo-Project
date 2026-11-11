#!/usr/bin/env python3
"""Opt-in, fail-closed Zellij pane-scroll settings.

Zellij has no supported numeric wheel-speed option or global config include.
A confirmed change inserts/updates one clearly marked root-level KDL block,
preserving every other byte of an ordinary user-owned config.kdl. The initial
write creates a one-time backup. Existing root options, symlinks, stale files,
and unknown/altered managed blocks are refused instead of being overwritten.
Nothing sends mouse events, changes Kitty, or restarts/reconfigures Zellij.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

START = "// BEGIN POST-APOLLO ZELLIJ SCROLL V1"
END = "// END POST-APOLLO ZELLIJ SCROLL V1"
OPTIONS = ("mouse_mode", "mouse_scroll_resize", "scroll_mode_sync",
           "scroll_buffer_size")
BUFFER_CHOICES = (1000, 5000, 10000, 20000, 50000, 100000)
MAX_CONFIG_BYTES = 262144
KEY_RE = re.compile(r"^\s*(mouse_mode|mouse_scroll_resize|scroll_mode_sync|scroll_buffer_size)(?:\s|$)")
TRUE_FALSE = {"true": True, "false": False}


class ZellijScrollError(Exception):
    pass


def paths(home=None, config_file=None):
    home = Path(home) if home is not None else Path.home()
    if config_file is None:
        chosen = os.environ.get("ZELLIJ_CONFIG_FILE")
        if chosen:
            config_file = Path(chosen)
        else:
            config_dir = os.environ.get("ZELLIJ_CONFIG_DIR")
            config_file = (Path(config_dir) if config_dir
                           else home / ".config" / "zellij") / "config.kdl"
    config = Path(config_file)
    if not home.is_absolute() or not config.is_absolute():
        raise ZellijScrollError("UNSUPPORTED_CONFIG_PATH")
    # Never follow symlinks from the config's parent outside the home.
    canonical_home = home.resolve()
    try:
        parent = config.parent.resolve(strict=True)
    except (RuntimeError, OSError) as exc:
        raise ZellijScrollError("CONFIG_DIRECTORY_UNAVAILABLE") from exc
    if (not parent.is_relative_to(canonical_home) or parent == canonical_home
            or config.parent.is_symlink()):
        raise ZellijScrollError("CONFIG_DIRECTORY_UNSAFE")
    return config, config.with_name("config.kdl.post-apollo-scroll-v1.bak")


def read_config(config):
    try:
        fd = os.open(config, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except FileNotFoundError:
        raise ZellijScrollError("CONFIG_MISSING")
    except OSError as exc:
        raise ZellijScrollError("UNSAFE_CONFIG") from exc
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_uid != os.getuid() or info.st_size > MAX_CONFIG_BYTES):
            raise ZellijScrollError("UNSAFE_CONFIG")
        raw = os.read(fd, MAX_CONFIG_BYTES + 1)
        if len(raw) > MAX_CONFIG_BYTES:
            raise ZellijScrollError("CONFIG_TOO_LARGE")
        try:
            return raw.decode("utf-8"), stat.S_IMODE(info.st_mode)
        except UnicodeError as exc:
            raise ZellijScrollError("INVALID_ENCODING") from exc
    finally:
        os.close(fd)


def revision(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize(mouse, resize, sync, buffer):
    for val in (mouse, resize, sync):
        if val not in TRUE_FALSE:
            raise ZellijScrollError("INVALID_BOOLEAN")
    if not isinstance(buffer, str) or not buffer.isdecimal():
        raise ZellijScrollError("INVALID_BUFFER")
    count = int(buffer)
    if count not in BUFFER_CHOICES:
        raise ZellijScrollError("BUFFER_UNSUPPORTED")
    return mouse, resize, sync, count


def managed_block(mouse, resize, sync, buffer):
    mouse, resize, sync, buffer = normalize(mouse, resize, sync, str(buffer))
    return (START + "\n"
            + "mouse_mode " + mouse + "\n"
            + "mouse_scroll_resize " + resize + "\n"
            + "scroll_mode_sync " + sync + "\n"
            + "scroll_buffer_size " + str(buffer) + "\n"
            + END + "\n")


def block_parts(text):
    if text.count(START) > 1 or text.count(END) > 1:
        raise ZellijScrollError("DUPLICATE_MARKER")
    if (START in text) != (END in text):
        raise ZellijScrollError("ALTERED_MARKER")
    if START in text:
        start = text.index(START)
        end = text.index(END) + len(END)
        if text[end:end+1] == "\n":
            end += 1
        before, block, after = text[:start], text[start:end], text[end:]
        lines = block.splitlines()
        if len(lines) != 6 or lines[0] != START or lines[-1] != END:
            raise ZellijScrollError("ALTERED_BLOCK")
        values = []
        for line, key in zip(lines[1:-1], OPTIONS):
            prefix = key + " "
            if not line.startswith(prefix):
                raise ZellijScrollError("ALTERED_BLOCK")
            values.append(line[len(prefix):])
        try:
            if block != managed_block(*values):
                raise ZellijScrollError("ALTERED_BLOCK")
        except ZellijScrollError as exc:
            raise ZellijScrollError("ALTERED_BLOCK") from exc
    else:
        before, block, after = text, None, ""
        values = None
    # Fail closed for any other un-commented option declarations, including
    # potential duplicate root nodes. Do not guess KDL precedence.
    remaining = before + after
    for line in remaining.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("//") or stripped.startswith("#"):
            continue
        if KEY_RE.match(line):
            raise ZellijScrollError("EXTERNAL_SCROLL_OPTIONS")
    return before, block, after, values


def status(home=None, config_file=None):
    config, backup = paths(home, config_file)
    source, _mode = read_config(config)
    before, block, after, values = block_parts(source)
    reply = {"status": "managed" if block is not None else "available",
             "config": str(config), "revision": revision(source),
             "backup_exists": backup.exists(), "runtime_verified": False,
             "scope": "zellij_config_only"}
    if values is not None:
        reply.update(mouse=values[0], resize=values[1],
                     sync=values[2], buffer=int(values[3]))
    return reply


def atomic_write(path, text, mode):
    pending = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=".post-apollo-zellij-", delete=False
        ) as file:
            pending = Path(file.name)
            os.fchmod(file.fileno(), mode)
            file.write(text)
            file.flush()
            os.fsync(file.fileno())
        os.replace(pending, path)
        pending = None
        dir_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if pending is not None:
            pending.unlink(missing_ok=True)


def apply(expected_revision, mouse, resize, sync, buffer,
          home=None, config_file=None):
    block_new = managed_block(mouse, resize, sync, buffer)
    config, backup = paths(home, config_file)
    source, mode = read_config(config)
    if not isinstance(expected_revision, str) or revision(source) != expected_revision:
        raise ZellijScrollError("STALE_CONFIG")
    before, block_old, after, _ = block_parts(source)
    if block_old is None:
        if backup.exists() or backup.is_symlink():
            raise ZellijScrollError("BACKUP_ALREADY_EXISTS")
        # Write a byte-identical original once, before editing the config.
        try:
            fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                         | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as file:
                file.write(source.encode("utf-8"))
                file.flush()
                os.fsync(file.fileno())
        except OSError as exc:
            raise ZellijScrollError("BACKUP_FAILED") from exc
        updated = source + ("" if source.endswith("\n") else "\n")
        updated += "\n" + block_new
    else:
        updated = before + block_new + after
    if len(updated.encode("utf-8")) > MAX_CONFIG_BYTES:
        raise ZellijScrollError("CONFIG_TOO_LARGE")
    try:
        # Refuse a concurrent editor before atomic replacement.
        latest, _ = read_config(config)
        if revision(latest) != expected_revision:
            raise ZellijScrollError("STALE_CONFIG")
        if updated != source:
            atomic_write(config, updated, mode)
    except OSError as exc:
        raise ZellijScrollError("CONFIG_WRITE_FAILED") from exc
    return {"status": "saved", "revision": revision(updated),
            "mouse": mouse, "resize": resize, "sync": sync,
            "buffer": int(buffer), "runtime_verified": False,
            "activation": "ZELLIJ_CONFIG_RELOAD_OR_RESTART"}


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        if args == ["status"]:
            result = status()
        elif len(args) == 6 and args[0] == "apply":
            result = apply(*args[1:])
        else:
            raise ZellijScrollError("INVALID_ACTION")
        print(json.dumps(result, separators=(",", ":")))
        return 0
    except ZellijScrollError as exc:
        print(json.dumps({"status": "unavailable", "code": str(exc)},
                         separators=(",", ":")))
        return 2


if __name__ == "__main__":
    sys.exit(main())
