#!/usr/bin/env python3
"""C4d CI-only capture of ONE bounded actual C4b guest UART observation.

The unchanged C2v QEMU controller writes guest ttyS0 to a temporary serial log
and removes the VM directory when the full two-reboot run ends. This separate
C4b-owned reader follows that ephemeral file while the VM is live, retains a
single allowlisted C4B_OBSERVED line, and exports it ONLY after the parent
workflow independently confirms that the original full boot/rollback PASSED.

This is diagnostic availability, NOT signed guest attestation or authorization.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys
import time

PREFIX = b"C4B_OBSERVED // "
SCHEMA = "postapollo.connections.c4b-booted-signed-host-observation.v1"
SHA = re.compile(r"[0-9a-f]{64}\Z")
FIELDS = {
    "schema", "signed_rpm_sha256", "signed_script_sha256",
    "running_script_sha256", "interpreter_sha256",
    "service_pid", "dbus_owner_pid", "process_start_ticks",
    "service_uid", "service_gid", "systemd_unit", "selinux_enforcing",
    "signedGuestOriginAuthenticated", "evidenceCryptographicallyAttested",
    "hostAuthenticated", "canApprove", "credentialActionsEnabled",
    "productionAuthority",
}
FALSE_FLAGS = {
    "signedGuestOriginAuthenticated", "evidenceCryptographicallyAttested",
    "hostAuthenticated", "canApprove", "credentialActionsEnabled",
    "productionAuthority",
}
REQUIRED_MARKERS = (
    b"C3B_PASS // OS_DBUS_PID_UID_SYSTEMD_SELINUX_ORIGIN_COHERENCE_TEST_ONLY",
    b"C4B_PASS // EXACT_RUNTIME_ORIGIN_AND_DENY_ONLY_CLIENT_CALLS",
    b"C4B_PASS // SAME_C3B_SERVICE_SIGNED_RPM_SCRIPT_AND_INTERPRETER_OBSERVED",
    b"C2V_PASS // REAL_SILVERBLUE_BOOTED_ROLLBACK_REMOVED_LAYER",
)
MAX_LINE = 2048
MAX_BYTES = 32 * 1024 * 1024
# No arbitrary guest-provided text in Actions diagnostics. These are exact,
# fixed failure labels emitted by the C4b guest-side diagnostic-only relay.
KNOWN_RELAY_REASONS = frozenset((
    b"LOG_PREP_REFUSED", b"UART_OPEN_REFUSED", b"UART_WRITE_REFUSED",
    b"GUEST_OBSERVATION_DUPLICATE_KEY",
    b"GUEST_RECORD_NOT_REGULAR", b"GUEST_RECORD_OWNER_MISMATCH",
    b"GUEST_RECORD_LINK_COUNT_INVALID", b"GUEST_RECORD_EMPTY",
    b"GUEST_RECORD_OVERSIZE", b"GUEST_LOG_CHANGED",
    b"GUEST_OBSERVATION_MISSING", b"GUEST_OBSERVATION_DUPLICATE",
    b"GUEST_OBSERVATION_OVERSIZE", b"GUEST_OBSERVATION_JSON_INVALID",
    b"GUEST_OBSERVATION_SCHEMA_INVALID",
    b"GUEST_OBSERVATION_DIGEST_INVALID",
    b"GUEST_OBSERVATION_PROCESS_INVALID",
    b"GUEST_OBSERVATION_DBUS_PID_MISMATCH",
    b"GUEST_OBSERVATION_START_INVALID",
    b"UART_NOT_CHARACTER_DEVICE", b"UART_WRITE_TIMEOUT",
    b"UART_WRITE_ZERO", b"UART_WRITE_INCOMPLETE",
))


class Refused(Exception):
    pass


def reject(reason: str):
    raise Refused(reason)


def unique_fields(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            reject("DUPLICATE_OBSERVATION_FIELD")
        result[name] = value
    return result


def validate_observation(raw: bytes) -> bytes:
    """Return exact observed UART bytes if narrow schema and deny flags hold."""
    if not (raw.startswith(PREFIX) and len(raw) <= MAX_LINE):
        reject("OBSERVATION_LINE_OVERSIZE_OR_MISSING")
    try:
        value = json.loads(raw[len(PREFIX):].decode("utf-8", "strict"),
                           object_pairs_hook=unique_fields)
    except (UnicodeError, ValueError, TypeError):
        reject("OBSERVATION_JSON_INVALID")
    if type(value) is not dict or set(value) != FIELDS:
        reject("OBSERVATION_SCHEMA_FIELDS_REFUSED")
    if value["schema"] != SCHEMA or value["systemd_unit"] != (
            "postapollo-connections-status.service"):
        reject("OBSERVATION_SCHEMA_OR_UNIT_REFUSED")
    if any(type(value[k]) is not bool or value[k] for k in FALSE_FLAGS):
        reject("OBSERVATION_CLAIMS_AUTHORITY")
    if value["selinux_enforcing"] is not True:
        reject("OBSERVATION_NOT_ENFORCING")
    for name in ("signed_rpm_sha256", "signed_script_sha256",
                 "running_script_sha256", "interpreter_sha256"):
        if type(value[name]) is not str or SHA.fullmatch(value[name]) is None:
            reject("OBSERVATION_HASH_REFUSED")
    if value["signed_script_sha256"] != value["running_script_sha256"]:
        reject("RUNNING_SCRIPT_SIGNED_HASH_MISMATCH")
    for name in ("service_pid", "dbus_owner_pid", "service_uid", "service_gid"):
        if type(value[name]) is not int or value[name] <= 0:
            reject("OBSERVATION_PROCESS_IDENTITY_REFUSED")
    if value["service_pid"] != value["dbus_owner_pid"]:
        reject("OBSERVATION_DBUS_PROCESS_MISMATCH")
    ticks = value["process_start_ticks"]
    if type(ticks) is not str or not ticks.isascii() or (
            not ticks.isdecimal()) or int(ticks) <= 0 or len(ticks) > 20:
        reject("OBSERVATION_KERNEL_START_REFUSED")
    return raw


def find_serial(root: Path) -> Path | None:
    candidates = list(root.glob("c2v-silverblue-*"))
    if len(candidates) > 1:
        reject("MULTIPLE_GUEST_BOOT_DIRECTORIES")
    if not candidates:
        return None
    folder = candidates[0]
    info = os.lstat(folder)
    if (not stat.S_ISDIR(info.st_mode) or
            info.st_uid != os.geteuid() or
            stat.S_IMODE(info.st_mode) != 0o700):
        reject("GUEST_BOOT_DIRECTORY_UNSAFE")
    path = folder / "guest-serial.log"
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid():
        reject("GUEST_SERIAL_SOURCE_UNSAFE")
    return path


def capture(root: Path, completed: Path, *, poll: float = 0.1) -> bytes:
    """Scan live UART while the owning C2v runner is still executing."""
    fd = None
    source = None
    # C2v deletes its temporary QEMU directory on successful return, before
    # the parent workflow can write the separate PASS/FAIL completion marker.
    # Keep reading the already-open inode after unlink, without following a
    # replacement pathname. The original C2v PASS remains mandatory.
    source_unlinked_at = None
    offset = 0
    pending = b""
    total = 0
    observed = None
    seen = {marker: False for marker in REQUIRED_MARKERS}
    # Exact source/transport boundary counters only. Never log UART payload,
    # process IDs, hashes, credentials, request IDs or guest-originated text.
    source_opened = False
    controller_tail_seen = False
    relay_status_seen = False
    relay_complete_seen = False
    relay_reasons = set()
    candidate_records = 0
    started = time.monotonic()
    try:
        while time.monotonic() - started < 3700:
            if fd is None:
                candidate = find_serial(root)
                if candidate is not None:
                    try:
                        fd = os.open(candidate, os.O_RDONLY | os.O_NOFOLLOW |
                                     os.O_CLOEXEC)
                    except OSError:
                        reject("GUEST_SERIAL_OPEN_REFUSED")
                    info = os.fstat(fd)
                    if not stat.S_ISREG(info.st_mode):
                        reject("GUEST_SERIAL_FD_NOT_REGULAR")
                    source = (info.st_dev, info.st_ino)
                    source_opened = True
            if fd is not None:
                # Drain the original open inode BEFORE checking its pathname.
                # C2v's cleanup unlinks the file immediately on full success.
                # An open descriptor preserves already-written UART bytes.
                os.lseek(fd, offset, os.SEEK_SET)
                while True:
                    chunk = os.read(fd, 65536)
                    if not chunk:
                        break
                    offset += len(chunk)
                    total += len(chunk)
                    if total > MAX_BYTES:
                        reject("GUEST_SERIAL_BOUND_EXCEEDED")
                    pending += chunk
                    records = pending.split(b"\n")
                    pending = records.pop()
                    if len(pending) > 8192:
                        reject("GUEST_SERIAL_LINE_OVERSIZE")
                    for line in records:
                        for marker in REQUIRED_MARKERS:
                            if marker in line:
                                seen[marker] = True
                        if b"C4B_CONTROLLER_GUEST_LOG_BEGIN" in line:
                            controller_tail_seen = True
                        tag = b"C4D_UART_DIAG // "
                        if tag in line:
                            relay_status_seen = True
                            if b"C4D_UART_DIAG // ONE_VALID_RECORD_WRITTEN_TO_UART" in line:
                                relay_complete_seen = True
                            # Use a fixed bounded whitelist, NOT printable
                            # guest text. A forged diagnostic cannot authorize
                            # acceptance and is never added to the evidence.
                            reason = line.split(tag, 1)[1].strip(b"\r ")
                            if reason in KNOWN_RELAY_REASONS:
                                relay_reasons.add(reason)
                            elif not relay_complete_seen:
                                relay_reasons.add(b"UNKNOWN")
                        index = line.find(PREFIX)
                        if index == -1:
                            continue
                        candidate_records += 1
                        extracted = line[index:].rstrip(b"\r")
                        validate_observation(extracted)
                        if observed is None:
                            observed = extracted
                        elif observed != extracted:
                            reject("CONFLICTING_GUEST_OBSERVATIONS")
                # Never switch to a new guest serial file. C2v normally
                # removes the original at the END of the successful two-boot
                # lifecycle. That unlink is not a security failure if the
                # original descriptor has been drained and the independently
                # reported C2v command later returns PASS. Reappearance or
                # inode substitution remains an unconditional refusal.
                current_path = find_serial(root)
                if current_path is None:
                    if source_unlinked_at is None:
                        source_unlinked_at = time.monotonic()
                else:
                    if source_unlinked_at is not None:
                        reject("GUEST_SERIAL_REAPPEARED_AFTER_REMOVAL")
                    try:
                        current = os.stat(current_path, follow_symlinks=False)
                    except FileNotFoundError:
                        if source_unlinked_at is None:
                            source_unlinked_at = time.monotonic()
                    else:
                        if (current.st_dev, current.st_ino) != source:
                            reject("GUEST_SERIAL_REPLACED")
                # No indefinite acceptance of disappearing input: bounded
                # grace covers C2v's cleanup-to-parent-exit handoff only.
                if (source_unlinked_at is not None and
                        not completed.exists() and
                        time.monotonic() - source_unlinked_at > 30):
                    reject("GUEST_SERIAL_MISSING_BEFORE_C2V_RESULT")
            if completed.exists():
                if completed.read_text(encoding="ascii").strip() != "PASS":
                    reject("ORIGINAL_TWO_BOOT_LIFECYCLE_DID_NOT_PASS")
                if observed is None:
                    reject("NO_REAL_GUEST_OBSERVATION_CAPTURED")
                if not all(seen.values()):
                    reject("REAL_GUEST_SECURITY_OR_ROLLBACK_MARKERS_MISSING")
                return observed
            time.sleep(poll)
        reject("GUEST_SERIAL_CAPTURE_TIMEOUT")
    finally:
        # Fixed labels and bounded counts help distinguish a missing relay
        # from a missing serial FD or an incomplete final record. This is
        # diagnostic-only: it cannot satisfy any C4d acceptance condition.
        print("C4D_CAPTURE_DIAG // "
              "serial_opened={} bytes_read={} candidate_records={} "
              "controller_tail={} relay_status={} relay_complete={} "
              "relay_reason={} c3b_origin={} c4b_runtime_origin={} "
              "c4c_signed_process={} c2v_rollback={} partial_prefix={}".format(
                  int(source_opened), min(total, MAX_BYTES + 1),
                  min(candidate_records, 100),
                  int(controller_tail_seen), int(relay_status_seen),
                  int(relay_complete_seen),
                  (next(iter(relay_reasons)).decode("ascii")
                   if len(relay_reasons) == 1 else
                   ("NONE" if not relay_reasons else "MULTIPLE")),
                  int(seen[REQUIRED_MARKERS[0]]),
                  int(seen[REQUIRED_MARKERS[1]]),
                  int(seen[REQUIRED_MARKERS[2]]),
                  int(seen[REQUIRED_MARKERS[3]]),
                  int(PREFIX in pending)), flush=True)
        if fd is not None:
            os.close(fd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner-temp", type=Path, required=True)
    parser.add_argument("--complete", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ready", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("GITHUB_ACTIONS") != "true":
        reject("CI_RUNNER_REQUIRED")
    root = args.runner_temp
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        reject("RUNNER_TEMP_NOT_ABSOLUTE_DIRECTORY")
    if list(root.glob("c2v-silverblue-*")):
        reject("STALE_C2V_BOOT_DIRECTORY_BEFORE_MONITOR")
    if args.output.parent.is_symlink() or not args.output.parent.is_dir():
        reject("OUTPUT_DIRECTORY_UNAVAILABLE")
    out_stat = os.stat(args.output.parent)
    if (out_stat.st_uid != os.geteuid() or
            stat.S_IMODE(out_stat.st_mode) != 0o700):
        reject("OUTPUT_DIRECTORY_NOT_PRIVATE")
    if args.output.exists() or args.output.is_symlink():
        reject("OUTPUT_ALREADY_EXISTS")
    # Signal readiness only AFTER all pre-existing-directory and output-path
    # safety checks. The CI parent MUST wait before starting C2v/QEMU; otherwise
    # C2v's fresh boot directory can be mistaken for a stale old directory.
    if (args.ready.parent != args.output.parent or
            args.ready.name != "observer-ready" or
            os.path.lexists(args.ready)):
        reject("OBSERVER_READINESS_SCOPE_REFUSED")
    ready_fd = os.open(args.ready, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                       os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    with os.fdopen(ready_fd, "wb") as signal:
        signal.write(b"READY\n")
        signal.flush()
        os.fsync(signal.fileno())
    line = capture(root, args.complete)
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(line + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        args.output.unlink(missing_ok=True)
        raise
    print("C4D_PASS // ONE_BOUNDED_ACTUAL_GUEST_SERIAL_OBSERVATION_EXPORTED")
    print("C4D_LIMITATION // UNSIGNED_GUEST_LOG_NOT_REMOTE_ATTESTATION")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (Refused, OSError, ValueError) as exc:
        print("C4D_REFUSED // " + (
            str(exc) if isinstance(exc, Refused) else type(exc).__name__),
            file=sys.stderr)
        sys.exit(2)
