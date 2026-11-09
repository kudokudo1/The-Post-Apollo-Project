#!/usr/bin/env python3
"""C3e-U: read-only *diagnostic* import of actual C4c guest report format.

C4c #1646 executed in a real offline booted Silverblue guest, checked the
signed C3d RPM, actual root-owned Python source, separate interpreter,
systemd/D-Bus/SELinux identity, and full real rollback. Its C4B_OBSERVED
UART report is nevertheless GUEST SELF-REPORTED PLAINTEXT, not independently
authenticated. This importer checks exact report schema and *independent*
caller-owned expected pins, never issues a trusted-host proof or C3e-Q
signed envelope, and never enables credentials.

One bounded input line. No network, filesystem mutation, signing or keys.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

SCHEMA = "postapollo.connections.c4b-booted-signed-host-observation.v1"
RECEIPT_SCHEMA = "postapollo.connections.c3eu-observed-guest-import.v1"
REFUSAL_SCHEMA = "postapollo.connections.c3eu-refused.v1"
PREFIX = b"C4B_OBSERVED // "
MAX_LINE = 4096
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
UNIT = "postapollo-connections-status.service"
FIELDS = frozenset({
    "schema", "signed_rpm_sha256", "signed_script_sha256",
    "running_script_sha256", "interpreter_sha256", "service_pid",
    "dbus_owner_pid", "process_start_ticks", "service_uid", "service_gid",
    "systemd_unit", "selinux_enforcing", "signedGuestOriginAuthenticated",
    "evidenceCryptographicallyAttested", "hostAuthenticated", "canApprove",
    "credentialActionsEnabled", "productionAuthority",
})
DENY_FLAGS = (
    "signedGuestOriginAuthenticated", "evidenceCryptographicallyAttested",
    "hostAuthenticated", "canApprove", "credentialActionsEnabled",
    "productionAuthority",
)


class Refused(Exception):
    pass


def deny(code: str):
    raise Refused(code)


def _positive(value):
    return type(value) is int and 1 <= value <= 2147483647


def _ticks(value):
    return (type(value) is str and 1 <= len(value) <= 24 and
            value.isascii() and value.isdecimal() and
            str(int(value)) == value and int(value) > 0)


def _hash(value):
    return type(value) is str and HEX64.fullmatch(value) is not None


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            deny("DUPLICATE_C4C_FIELD")
        result[key] = value
    return result


def _decode(raw):
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_LINE:
        deny("C4C_LINE_SIZE_REFUSED")
    if raw.endswith(b"\n"):
        raw = raw[:-1]
    if b"\n" in raw or b"\r" in raw or b"\0" in raw or not raw.startswith(PREFIX):
        deny("C4C_LINE_PREFIX_OR_DELIMITER_REFUSED")
    try:
        doc = json.loads(raw[len(PREFIX):].decode("utf-8"),
                         object_pairs_hook=_unique)
    except (ValueError, UnicodeError):
        deny("C4C_REPORT_JSON_REFUSED")
    if type(doc) is not dict or set(doc) != FIELDS:
        deny("C4C_REPORT_SHAPE_REFUSED")
    return doc


def inspect(*, report_line: bytes,
            independent_signed_rpm_sha256: str,
            independent_signed_script_sha256: str,
            independent_interpreter_sha256: str,
            expected_service_pid: int,
            expected_start_ticks: str,
            expected_service_uid: int,
            expected_service_gid: int):
    """Validate a diagnostic candidate, NEVER an authenticated guest origin."""
    pins = (
        independent_signed_rpm_sha256,
        independent_signed_script_sha256,
        independent_interpreter_sha256,
    )
    if any(not _hash(x) for x in pins):
        deny("INDEPENDENT_HASH_PIN_INVALID")
    if (not _positive(expected_service_pid) or
            not _positive(expected_service_uid) or
            not _positive(expected_service_gid) or
            not _ticks(expected_start_ticks)):
        deny("INDEPENDENT_PROCESS_PIN_INVALID")
    doc = _decode(report_line)
    if (doc["schema"] != SCHEMA or doc["systemd_unit"] != UNIT or
            doc["selinux_enforcing"] is not True):
        deny("C4C_ROLE_OR_SELINUX_REFUSED")
    if any(doc[name] is not False for name in DENY_FLAGS):
        deny("C4C_CLAIMED_UNAUTHORIZED_AUTHORITY")
    for name in (
        "signed_rpm_sha256", "signed_script_sha256",
        "running_script_sha256", "interpreter_sha256",
    ):
        if not _hash(doc[name]):
            deny("C4C_HASH_FORMAT_REFUSED")
    if (doc["running_script_sha256"] != doc["signed_script_sha256"] or
            doc["signed_rpm_sha256"] != independent_signed_rpm_sha256 or
            doc["signed_script_sha256"] != independent_signed_script_sha256 or
            doc["interpreter_sha256"] != independent_interpreter_sha256):
        deny("C4C_SIGNED_ARTIFACT_OR_RUNNING_BYTES_PIN_MISMATCH")
    for name in ("service_pid", "dbus_owner_pid", "service_uid", "service_gid"):
        if not _positive(doc[name]):
            deny("C4C_PROCESS_FIELD_INVALID")
    if not _ticks(doc["process_start_ticks"]):
        deny("C4C_START_FIELD_INVALID")
    if (doc["service_pid"] != expected_service_pid or
            doc["dbus_owner_pid"] != expected_service_pid or
            doc["process_start_ticks"] != expected_start_ticks or
            doc["service_uid"] != expected_service_uid or
            doc["service_gid"] != expected_service_gid):
        deny("C4C_SYSTEMD_DBUS_PROCESS_PIN_MISMATCH")
    return {
        "schema": RECEIPT_SCHEMA,
        "c4cSchemaCompatible": True,
        "reportMatchesSuppliedIndependentPins": True,
        "observedServicePid": doc["service_pid"],
        "observedStartTicks": doc["process_start_ticks"],
        "reportSourceIsGuestSelfObservation": True,
        # Observations are not signatures, independently attested facts,
        # C3e-Q/R enrollment or operator consent. Never upgrade authority.
        "signedGuestOriginAuthenticated": False,
        "evidenceCryptographicallyAttested": False,
        "installedGuestMeasured": False,
        "hostAuthenticated": False,
        "canApprove": False,
        "credentialActionsEnabled": False,
        "productionAuthority": False,
    }


def _decimal(value):
    try:
        number = int(value, 10)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError("positive canonical decimal required")
    if not _positive(number) or str(number) != value:
        raise argparse.ArgumentTypeError("positive canonical decimal required")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="C4c guest self-observation diagnostic importer, no authentication")
    parser.add_argument("--rpm-sha256", required=True)
    parser.add_argument("--script-sha256", required=True)
    parser.add_argument("--interpreter-sha256", required=True)
    parser.add_argument("--service-pid", type=_decimal, required=True)
    parser.add_argument("--start-ticks", required=True)
    parser.add_argument("--service-uid", type=_decimal, required=True)
    parser.add_argument("--service-gid", type=_decimal, required=True)
    args = parser.parse_args(argv)
    try:
        # One line only: read at most MAX_LINE+1 bytes to avoid unbounded log
        # ingestion. No attempt is made to search through arbitrary guest logs.
        raw = sys.stdin.buffer.read(MAX_LINE + 1)
        result = inspect(
            report_line=raw,
            independent_signed_rpm_sha256=args.rpm_sha256,
            independent_signed_script_sha256=args.script_sha256,
            independent_interpreter_sha256=args.interpreter_sha256,
            expected_service_pid=args.service_pid,
            expected_start_ticks=args.start_ticks,
            expected_service_uid=args.service_uid,
            expected_service_gid=args.service_gid)
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except Refused as error:
        print(json.dumps({
            "schema": REFUSAL_SCHEMA, "refused": str(error),
            "signedGuestOriginAuthenticated": False,
            "evidenceCryptographicallyAttested": False,
            "hostAuthenticated": False, "canApprove": False,
            "credentialActionsEnabled": False, "productionAuthority": False,
        }, sort_keys=True, separators=(",", ":")))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
