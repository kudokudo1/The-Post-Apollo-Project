#!/usr/bin/env python3
"""M11e explicit SYNTHETIC FileView fixture creation; no default target.

Only creates a NEW fixture-only.json inside a preexisting private
m11e-fileview-test directory. It refuses symlinks, existing targets,
insecure mode, unknown names, and real Apollo TASKS JSON paths.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat

DOCUMENT = {"fixture":"M11E_SYNTHETIC_ONLY","revision":0,
            "counter":0,"marker":"sample"}


def initialize(file: Path):
    if (not isinstance(file, Path) or not file.is_absolute()
            or file.name != "fixture-only.json"
            or file.parent.name != "m11e-fileview-test"):
        raise ValueError("EXPLICIT_DISPOSABLE_FIXTURE_REQUIRED")
    parent = file.parent
    if parent.is_symlink():
        raise ValueError("UNSAFE_TEST_DIRECTORY")
    try:
        info = parent.lstat()
    except FileNotFoundError as exc:
        raise ValueError("PREEXISTING_PRIVATE_DIRECTORY_REQUIRED") from exc
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) & 0o077):
        raise ValueError("UNSAFE_TEST_DIRECTORY")
    if file.is_symlink():
        raise ValueError("UNSAFE_TEST_LINK")
    # No overwrite or implicit parent creation. Zero auto-migration rights.
    descriptor = os.open(file, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                         getattr(os,"O_NOFOLLOW",0),0o600)
    with os.fdopen(descriptor,"w",encoding="utf-8") as handle:
        handle.write(json.dumps(DOCUMENT,separators=(",",":"))+"\n")
        handle.flush()
        os.fsync(handle.fileno())
    return file


if __name__ == "__main__":
    ap=argparse.ArgumentParser(description="M11e isolated synthetic FileView fixture")
    ap.add_argument("--file",type=Path,required=True)
    args=ap.parse_args()
    initialize(args.file)
    print("M11e synthetic fixture initialized. Not live TASKS.")
