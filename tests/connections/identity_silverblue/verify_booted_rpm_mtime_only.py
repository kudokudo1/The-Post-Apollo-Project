#!/usr/bin/env python3
"""Fail-closed parser for rpm -V in the disposable Identity Silverblue guest.

RPM-OSTree can give checked-out immutable files different modification times.
Only T (mtime) differences for the nine exact signed test-RPM paths are
tolerated here. Any digest, size, owner, mode, link, type, capability, missing,
extra path, duplicate record, or unsupported verifier exit remains refusal.
This parser does not itself authenticate a release signer or process.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PREFIX = "/usr/libexec/post-apollo/identity/"
FILES = frozenset(
    PREFIX + name for name in (
        "identity-gateway-ci",
        "desktop_command_gateway_v0.py",
        "desktop_host_lifecycle_v0.py",
        "desktop_context_projection_v0.py",
        "desktop_session_host_v0.py",
        "native_loopback_callback_v0.py",
        "private_context_ipc_v0.py",
        "signed_command_receipt_v0.py",
    )
) | {"/usr/lib/systemd/system/post-apollo-identity-silverblue-ci.service"}
# RPM verify output has a nine-character result field and a four-space
# separator. Exact expression excludes non-T flags (including missing files).
MTIME_ONLY = re.compile(r"^\.{7}T\.    (/[^ \t\r\n]+)$")


class Refused(ValueError):
    pass


def verify_mtime_only(output: str, returncode: int) -> int:
    if type(output) is not str or type(returncode) is not int:
        raise Refused("INVALID_RPM_VERIFIER_EVIDENCE")
    if len(output) > 4096:
        raise Refused("OVERSIZE_RPM_VERIFIER_EVIDENCE")
    if not output:
        if returncode == 0:
            return 0
        raise Refused("UNEXPLAINED_RPM_VERIFIER_FAILURE")
    if returncode != 1:
        raise Refused("RPM_VERIFIER_RETURN_CODE_REFUSED")
    seen: set[str] = set()
    for line in output.splitlines():
        match = MTIME_ONLY.fullmatch(line)
        if match is None:
            raise Refused("RPM_FILE_DIFFERENCE_NOT_TIMESTAMP_ONLY")
        path = match.group(1)
        if path not in FILES:
            raise Refused("RPM_FILE_OUTSIDE_SIGNED_ROSTER")
        if path in seen:
            raise Refused("RPM_FILE_DUPLICATE_VERIFICATION_RECORD")
        seen.add(path)
    if not seen:
        raise Refused("EMPTY_RPM_VERIFIER_EVIDENCE")
    return len(seen)


def main(argv: list[str]) -> int:
    if len(argv) != 2 or not argv[1].isdigit():
        print("C4B_ID_FAIL // INVALID_RPM_VERIFY_INPUT", file=sys.stderr)
        return 2
    path = Path(argv[0])
    try:
        output = path.read_text(encoding="utf-8")
        count = verify_mtime_only(output, int(argv[1]))
    except (Refused, UnicodeError, OSError) as exc:
        print("C4B_ID_FAIL // RPM_VERIFY_DIFFERENCE_REFUSED", file=sys.stderr)
        print(f"C4B_ID_RPM_VERIFY_REASON // {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(f"C4B_ID_PASS // RPM_VERIFY_ONLY_EXPECTED_MTIME_DIFFERENCES count={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
