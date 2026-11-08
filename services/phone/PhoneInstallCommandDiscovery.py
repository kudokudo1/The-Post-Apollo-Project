#!/usr/bin/env python3
"""Read-only discovery of trusted Fedora package-tool executables.

The desktop shell may have a trimmed PATH. The Fedora system executables
remain in /usr/bin or /bin, so discover them there without accepting custom
PATH replacements, modifying PATH, invoking installers, or reading phone data.
"""
from __future__ import annotations

import os
import shutil
from typing import Callable

OS_DIRS = ("/usr/bin", "/bin")
OS_PATH = ":".join(OS_DIRS)


def _trusted(candidate: object, name: str,
             realpath: Callable[[str], str]) -> str | None:
    if type(candidate) is not str or not os.path.isabs(candidate):
        return None
    if os.path.basename(candidate) != name:
        return None
    try:
        resolved = realpath(candidate)
    except (OSError, ValueError, TypeError):
        return None
    if (type(resolved) is not str or not os.path.isabs(resolved)
            or os.path.dirname(resolved) not in OS_DIRS):
        return None
    return candidate


def find_os_program(name: str) -> str | None:
    """Try process PATH, then system bin directories, only if OS-trusted.

    shutil.which checks the executable bit. A malicious earlier PATH entry
    must not prevent later discovery of the standard Fedora executable.
    """
    if name not in ("foot", "python3", "pkcon", "pkexec", "dnf5", "dnf", "rpm-ostree"):
        return None
    for env in (None, OS_PATH):
        try:
            candidate = (shutil.which(name) if env is None
                         else shutil.which(name, path=env))
        except (OSError, ValueError, TypeError):
            continue
        if _trusted(candidate, name, os.path.realpath) is not None:
            return candidate
    return None


def trusted_program(
    name: str,
    find: Callable[[str], str | None] = find_os_program,
    realpath: Callable[[str], str] = os.path.realpath,
) -> str | None:
    try:
        candidate = find(name)
    except Exception:
        return None
    return _trusted(candidate, name, realpath)


def trusted_dnf5(
    find: Callable[[str], str | None] = find_os_program,
    realpath: Callable[[str], str] = os.path.realpath,
) -> str | None:
    """Accept Fedora's /usr/bin/dnf alias ONLY when its target is DNF5.

    Never run DNF4 as a speculative replacement: the two use different
    transaction state, and the PHONE setup uses DNF5-specific options.
    """
    direct = trusted_program("dnf5", find=find, realpath=realpath)
    if direct is not None:
        try:
            if os.path.basename(realpath(direct)) == "dnf5":
                return direct
        except (OSError, TypeError, ValueError):
            pass
    alias = trusted_program("dnf", find=find, realpath=realpath)
    if alias is None:
        return None
    try:
        if os.path.basename(realpath(alias)) == "dnf5":
            return alias
    except (OSError, TypeError, ValueError):
        pass
    return None
