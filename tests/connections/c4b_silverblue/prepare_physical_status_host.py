#!/usr/bin/env python3
"""C4b-only CI runner staging of one-line physical interpreter shebang.

The C3d signed test RPM builder and C2r host source remain unmodified.
This tool stages an exact one-line shebang variant in RUNNER_TEMP for an
additional read-only Docker bind mount during C4b's disposable RPM build.
No workstation, /opt, runtime service or C3b policy mutation.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "tests/connections/c2r_selinux_domain/C2rStatusHost.py"
ORIGINAL = b"#!/opt/postapollo-c2o-venv/bin/python3\n"
PHYSICAL = b"#!/var/opt/postapollo-c2o-venv/bin/python3\n"
OUTPUT_NAME = "c4b-physical-status-host.py"


def convert(source: bytes) -> bytes:
    """Preserve signed source body byte for byte, alter ONLY exact shebang."""
    if type(source) is not bytes or not source.startswith(ORIGINAL):
        raise ValueError("C4B_PHYSICAL_HOST_UNEXPECTED_ORIGINAL_SHEBANG")
    converted = PHYSICAL + source[len(ORIGINAL):]
    if converted[len(PHYSICAL):] != source[len(ORIGINAL):]:
        raise ValueError("C4B_PHYSICAL_HOST_BODY_CHANGED")
    return converted


def main() -> int:
    if (
        len(sys.argv) != 2
        or os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("POST_APOLLO_C4B_CI_SOURCE") != "1"
    ):
        print("C4B_PHYSICAL_HOST_REFUSED_OUTSIDE_CI", file=sys.stderr)
        return 2
    runner_temp = os.environ.get("RUNNER_TEMP", "")
    if not runner_temp:
        print("C4B_PHYSICAL_HOST_MISSING_RUNNER_TEMP", file=sys.stderr)
        return 2
    temp = Path(runner_temp).resolve(strict=True)
    dest = Path(sys.argv[1])
    if (
        not dest.is_absolute()
        or dest.name != OUTPUT_NAME
        or dest.is_symlink()
        or dest.parent.resolve(strict=True) != temp
        or dest.resolve() == SOURCE.resolve()
        or temp == ROOT
        or ROOT in temp.parents
    ):
        print("C4B_PHYSICAL_HOST_UNTRUSTED_DESTINATION", file=sys.stderr)
        return 2
    try:
        source = SOURCE.read_bytes()
        target = convert(source)
        # Fail on old output rather than follow an attacker-controlled alias.
        with dest.open("xb") as stream:
            stream.write(target)
        dest.chmod(0o600)
        if dest.read_bytes() != target:
            raise ValueError("C4B_PHYSICAL_HOST_STAGING_VERIFY_FAILED")
    except (OSError, ValueError) as error:
        print("C4B_PHYSICAL_HOST_STAGING_FAILED // " + type(error).__name__, file=sys.stderr)
        return 2
    print("C4B_PASS // PHYSICAL_INTERPRETER_SHEBANG_STAGED_ONE_LINE_ONLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
