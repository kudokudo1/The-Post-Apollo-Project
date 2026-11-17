#!/usr/bin/env python3
"""Conservatively install Post-Apollo widget hotkeys into the user's Sway config.

No overwritten keybinds, no invented Sway config, no automatic Sway reload.
Refuse unknown includes, concurrent changes, and uncertain compositor identity.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import fcntl
import glob
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import sys
import tempfile

# Reuse the tested SwayPX-aware validator and symlink-safe candidate checks.
from enable_koinoikos_focus import checked_config, resolve_validator

ROOT = Path(__file__).resolve().parents[1]
INCLUDE = ROOT / "config/sway/post-apollo-widget-hotkeys.conf"
CHORDS = ("Mod4+t", "Mod4+m", "Mod4+Shift+m", "Mod4+n",
          "Mod4+a", "Mod4+Shift+t", "Mod4+Shift+w", "Mod4+r")
VAR = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")
SOCKET = re.compile(r"sway-ipc\.(\d+)\.(\d+)\.sock")


class UnsafeConfig(ValueError):
    """An existing binding or dynamic config cannot be safely overridden."""


def config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "sway/config"


def normalize_chord(chord: str) -> str:
    parts = chord.split("+")
    aliases = {"super": "mod4", "logo": "mod4", "control": "ctrl"}
    mods = sorted(aliases.get(x.lower(), x.lower()) for x in parts[:-1])
    return "+".join(mods + [parts[-1].lower()])


EXPECTED = {normalize_chord(chord) for chord in CHORDS}


def logical_lines(text: str) -> list[str]:
    lines = []
    pending = ""
    for line in text.splitlines():
        line = line.rstrip()
        if line.endswith("\\"):
            pending += line[:-1] + " "
        else:
            lines.append(pending + line)
            pending = ""
    if pending:
        raise UnsafeConfig("Unterminated continued Sway config line")
    return lines


def expand_vars(value: str, variables: dict[str, str]) -> str:
    if chr(36) + "{" in value:
        raise UnsafeConfig("Unresolved braced Sway variable")
    def replace(m: re.Match[str]) -> str:
        key = m.group(1)
        if key not in variables:
            raise UnsafeConfig("Unknown Sway variable $" + key)
        return variables[key]
    return VAR.sub(replace, value)


def inspect(config: Path, include: Path) -> tuple[set[str], bool, dict[Path, str]]:
    """Read all accessible nested includes before any installation."""
    collisions: set[str] = set()
    loaded = False
    snapshot: dict[Path, str] = {}
    visited: set[Path] = set()
    variables = {"HOME": str(Path.home()),
                 "XDG_CONFIG_HOME": str(config_path().parent.parent)}
    managed = include.resolve(strict=True)

    def visit(path: Path, depth: int) -> None:
        nonlocal loaded
        if depth > 20 or len(snapshot) >= 128:
            raise UnsafeConfig("Sway include tree too large")
        # Resolve file content for race checks, but keep the *visible*
        # include path's parent for Sway's relative-include semantics.
        visible = path.expanduser().absolute()
        real = visible.resolve(strict=True)
        if real == managed:
            loaded = True
            return
        if visible in visited:
            return
        if real in snapshot and real.parent != visible.parent:
            raise UnsafeConfig("Included symlink changes relative-path context")
        visited.add(visible)
        if not real.is_file() or real.stat().st_size > 2_000_000:
            raise UnsafeConfig("Uninspectable include " + str(real))
        raw = real.read_text(encoding="utf-8")
        snapshot[real] = raw
        for line in logical_lines(raw):
            try:
                words = shlex.split(line, comments=True, posix=True)
            except ValueError as exc:
                raise UnsafeConfig("Cannot parse Sway file " + str(path)) from exc
            if not words:
                continue
            directive = words[0].lower()
            if directive == "set" and len(words) >= 3 and words[1].startswith("$"):
                variables[words[1][1:]] = expand_vars(" ".join(words[2:]), variables)
            elif directive == "include":
                if len(words) < 2:
                    raise UnsafeConfig("Empty include directive in " + str(path))
                for arg in words[1:]:
                    value = os.path.expanduser(expand_vars(arg, variables))
                    candidate = Path(value)
                    if not candidate.is_absolute():
                        candidate = visible.parent / candidate
                    children = sorted(glob.glob(str(candidate)))
                    if not children and not any(x in str(candidate) for x in "*?["):
                        raise UnsafeConfig("Missing include " + str(candidate))
                    for child in children:
                        visit(Path(child), depth+1)
            elif directive in ("bindsym", "bindcode"):
                args = words[1:]
                while args and args[0].startswith("--"):
                    if args[0] == "--input-device" and len(args) >= 2:
                        args = args[2:]
                    else:
                        args = args[1:]
                if not args:
                    raise UnsafeConfig("Binding missing its chord")
                chord = expand_vars(args[0], variables)
                normalized = normalize_chord(chord)
                if directive == "bindcode" and "mod4" in normalized.split("+"):
                    raise UnsafeConfig("Super bindcode requires manual review: " + chord)
                if normalized in EXPECTED:
                    collisions.add(normalized)
                # Uppercase keysyms may imply Shift. Refuse any ambiguity.
                tail = chord.split("+")[-1]
                if len(tail) == 1 and tail.isupper():
                    shifted = normalize_chord("+".join(chord.split("+")[:-1]
                                                      + ["Shift", tail]))
                    if shifted in EXPECTED:
                        collisions.add(shifted)

    visit(config, 0)
    return collisions, loaded, snapshot


def correct_live_config(config: Path) -> bool:
    """Never patch the default path when the session used an explicit -c."""
    sock = Path(os.environ.get("SWAYSOCK") or os.environ.get("I3SOCK") or "").name
    matched = SOCKET.fullmatch(sock)
    if not matched or int(matched.group(1)) != os.getuid():
        return False
    try:
        raw = (Path("/proc") / matched.group(2) / "cmdline").read_bytes()
        args = [x.decode("utf-8") for x in raw.split(b"\0") if x]
        for i, value in enumerate(args):
            if value in ("-c", "--config"):
                return i+1 < len(args) and Path(args[i+1]).expanduser().resolve() == config.resolve()
            if value.startswith("--config="):
                return Path(value.partition("=")[2]).expanduser().resolve() == config.resolve()
        return True
    except (OSError, UnicodeError, ValueError):
        return False


def appended(original: str, managed: Path) -> str:
    quoted = '"' + str(managed).replace("\\", "\\\\").replace('"', '\\"') + '"'
    return (original.rstrip("\n")
            + "\n\n# Post-Apollo // guarded widget hotkey include\ninclude " + quoted + "\n")


def enable(config: Path, *, sway: str | None = None,
           dry_run: bool = False) -> tuple[bool, str]:
    config = config.expanduser()
    try:
        target = config.resolve(strict=True)
        if not target.is_file():
            return False, "SKIPPED // no regular user Sway config"
        if not target.is_relative_to(Path.home().resolve()):
            return False, "SKIPPED // config target is outside user home"
        managed = INCLUDE.resolve(strict=True)
        original = target.read_text(encoding="utf-8")
        collisions, already, snapshot = inspect(config, managed)
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        return False, "SKIPPED // unsafe or uninspectable config: " + str(exc)
    if collisions:
        return False, "SKIPPED // user shortcuts take priority: " + ", ".join(sorted(collisions))
    if already:
        return True, "ALREADY // include present; nothing changed"
    if sway is None and not correct_live_config(config):
        return False, "SKIPPED // running Sway config not positively identified"
    if dry_run:
        return True, "READY // all eight widget chords are free"
    validator, description = resolve_validator(sway)
    if validator is None:
        return False, "SKIPPED // " + description
    candidate = appended(original, managed)
    valid, evidence = checked_config(config, candidate, validator)
    if not valid:
        return False, "SKIPPED // SwayPX validation failed; original untouched: " + evidence

    def snapshot_unchanged() -> bool:
        # Re-scan the *include graph*, not merely contents of paths we saw
        # earlier. A new file in an include glob or a retargeted symlink can
        # introduce an existing binding while Sway validates the candidate.
        if config.resolve(strict=True) != target:
            return False
        new_collisions, new_loaded, new_snapshot = inspect(config, managed)
        return not new_collisions and not new_loaded and new_snapshot == snapshot

    try:
        if not snapshot_unchanged():
            return False, "SKIPPED // config or included tree changed during validation"
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = target.with_name(target.name + ".before-widget-hotkeys-" + timestamp + ".bak")
        serial = 2
        while backup.exists():
            backup = target.with_name(target.name + ".before-widget-hotkeys-"
                                      + timestamp + "-" + str(serial) + ".bak")
            serial += 1
        shutil.copy2(target, backup)
        fd, temp_name = tempfile.mkstemp(prefix=".post-apollo-hotkeys-",
                                         dir=str(target.parent), text=True)
        temp = Path(temp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(candidate)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temp, stat.S_IMODE(target.stat().st_mode))
            if not snapshot_unchanged():
                return False, "SKIPPED // config or included tree changed before commit; backup retained"
            os.replace(temp, target)
        finally:
            temp.unlink(missing_ok=True)
    except (OSError, RuntimeError, UnicodeError) as exc:
        return False, "SKIPPED // installation refused: " + str(exc)
    return True, ("INSTALLED // config backed up to " + str(backup)
                  + "; no Sway reload, effective on next compositor login")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--config", type=Path, default=config_path())
    parser.add_argument("--sway", default=None, help="Explicit validator for testing")
    args = parser.parse_args(argv)
    if not args.install:
        ok, message = enable(args.config, sway=args.sway, dry_run=True)
    else:
        if not args.config.expanduser().parent.is_dir():
            print("SKIPPED // no user Sway config directory")
            return 0
        lock = args.config.expanduser().parent / ".post-apollo-hotkeys.lock"
        try:
            with lock.open("a+") as stream:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                ok, message = enable(args.config, sway=args.sway)
        except (OSError, BlockingIOError):
            print("SKIPPED // installer lock unavailable")
            return 0
    print(message)
    # Hotkeys are optional: no installation problem may kill the shell.
    return 0 if ok or args.install else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
