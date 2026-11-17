#!/usr/bin/env python3
"""C4b CI-only host filter for real Silverblue guest serial marker evidence.

The QEMU serial stream may contain CRLF and terminal control sequences.
Export only bounded printable C4B_ID_ marker text, never terminal prefixes,
command arguments or complete logs. This does not authenticate the guest.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import sys

MAX_RAW_BYTES = 32 * 1024 * 1024
MAX_MARKER_BYTES = 1536
MAX_MARKER_LINES = 200
MAX_ARTIFACT_BYTES = 65536
MARKER_KINDS = frozenset({
    b"C4B_ID_PASS", b"C4B_ID_FAIL", b"C4B_ID_BLOCKED",
    b"C4B_ID_STAGE", b"C4B_ID_PENDING", b"C4B_ID_LIMITATION",
    b"C4B_ID_RPM_VERIFY_RC", b"C4B_ID_RPM_VERIFY_DETAIL",
    b"C4B_ID_SERVICE_OBSERVED", b"C4B_ID_SERVICE_JOURNAL",
    b"C4B_ID_SERVICE_PROBE_DETAIL", b"C4B_ID_SERVICE_PROBE_RC",
    b"C4B_ID_SELINUX_OBSERVED", b"C4B_ID_SELINUX_STAGE",
    b"C4B_ID_SELINUX_MODULE_DETAIL", b"C4B_ID_SELINUX_LOAD_DETAIL",
    b"C4B_ID_SELINUX_UNLOAD_DETAIL", b"C4B_ID_SELINUX_NEGATIVE_DETAIL",
})


class MarkerArtifactRefused(ValueError):
    pass


def sanitize_marker_artifact(raw: bytes, vm_exit: int) -> bytes:
    if type(raw) is not bytes or len(raw) > MAX_RAW_BYTES:
        raise MarkerArtifactRefused("RAW_LOG_SIZE_REFUSED")
    if type(vm_exit) is not int or not 0 <= vm_exit <= 255:
        raise MarkerArtifactRefused("VM_EXIT_INVALID")
    markers: list[bytes] = []
    for serial_line in raw.split(b"\n"):
        offset = serial_line.find(b"C4B_ID_")
        if offset < 0:
            continue
        marker = serial_line[offset:]
        # QEMU UART commonly adds a single CR before LF. Only this precise
        # delimiter is removed; unexpected controls within markers fail.
        if marker.endswith(b"\r"):
            marker = marker[:-1]
        prefix = marker.split(b" // ", 1)[0]
        if prefix not in MARKER_KINDS:
            continue
        if not 0 < len(marker) <= MAX_MARKER_BYTES or any(
            not 32 <= character <= 126 for character in marker
        ):
            raise MarkerArtifactRefused("MARKER_NONPRINTABLE_OR_LONG_REFUSED")
        markers.append(marker + b"\n")
    if not markers:
        raise MarkerArtifactRefused("NO_C4B_MARKERS")
    markers.append(f"C4B_ID_VM_PROCESS_EXIT // {vm_exit}\n".encode("ascii"))
    output = b"".join(markers)
    if len(markers) > MAX_MARKER_LINES or len(output) > MAX_ARTIFACT_BYTES:
        raise MarkerArtifactRefused("MARKER_ARTIFACT_BOUNDS_REFUSED")
    return output


def main() -> int:
    if len(sys.argv) != 4 or not re.fullmatch(r"(?:0|[1-9][0-9]{0,2})", sys.argv[3]):
        print("C4B_ID_BLOCKED // MARKER_FILTER_ARGUMENTS_REFUSED")
        return 2
    try:
        source = Path(sys.argv[1])
        if source.stat().st_size > MAX_RAW_BYTES:
            raise MarkerArtifactRefused("RAW_LOG_SIZE_REFUSED")
        result = sanitize_marker_artifact(source.read_bytes(), int(sys.argv[3]))
        target = Path(sys.argv[2])
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(result)
    except (OSError, MarkerArtifactRefused) as exc:
        print("C4B_ID_BLOCKED // MARKER_FILTER_" + (
            str(exc) if isinstance(exc, MarkerArtifactRefused) else "IO_REFUSED"
        ))
        return 2
    print("C4B_ID_PASS // BOUNDED_PRINTABLE_GUEST_MARKERS_PREPARED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
