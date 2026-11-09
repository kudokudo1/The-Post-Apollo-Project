#!/usr/bin/env python3
"""C3e-O: verify the real signed C3d RPM's EXACT Python host payload (CI only).

Do not confuse /proc/PID/exe (the Python interpreter) with the script executed
from the signed C3d package. This gate authenticates one disposable signed RPM
against a separately supplied test signer pin in an *isolated RPM database*,
extracts the three package members, and compares their actual bytes and modes
to the tracked C2r host, C2n unit and C2n D-Bus policy source.

The RPM signer is generated inside disposable CI, not a real release root.
No guest measurements, installed runtime, release admission, or authority.
This module NEVER installs the RPM, modifies system RPM trust, or grants access.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile

SCHEMA = "postapollo.connections.c3eo-signed-python-payload.v1"
FPR = re.compile(r"[A-F0-9]{40}")
PACKAGE_NAME = "postapollo-connections-c3d-ci-status"
EXPECTED = {
    "/usr/libexec/post-apollo/connections-status-host":
        ("tests/connections/c2r_selinux_domain/C2rStatusHost.py", 0o555),
    "/usr/lib/systemd/system/postapollo-connections-status.service":
        ("services/connections/experiments/c2n_package/"
         "postapollo-connections-status.service.template", 0o644),
    "/usr/share/dbus-1/system.d/org.postapollo.ConnectionsStatus1.conf":
        ("services/connections/experiments/c2n_package/"
         "org.postapollo.ConnectionsStatus1.conf.template", 0o644),
}
MAX_RPM = 4 * 1024 * 1024
MAX_MEMBER = 128 * 1024


class Refused(Exception):
    pass


def deny(reason: str):
    raise Refused(reason)


def _run(argv, *, timeout=25, input_bytes=None, cwd=None):
    try:
        result = subprocess.run(
            argv, input=input_bytes, capture_output=True, cwd=cwd,
            timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        deny("CI_TOOL_UNAVAILABLE")
    if result.returncode:
        deny("CI_TOOL_REFUSED")
    return result.stdout


def _root_owned_regular(path: Path, *, maximum: int):
    try:
        st = os.lstat(path)
    except OSError:
        deny("SIGNED_INPUT_NOT_FOUND")
    if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.geteuid() or
            st.st_nlink != 1 or stat.S_IMODE(st.st_mode) & 0o022 or
            not 0 < st.st_size <= maximum):
        deny("SIGNED_INPUT_UNSAFE")
    return st


def _digest(path: Path, *, maximum: int):
    size = _root_owned_regular(path, maximum=maximum).st_size
    hasher = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            counted = 0
            while True:
                chunk = stream.read(65536)
                if not chunk:
                    break
                counted += len(chunk)
                if counted > maximum:
                    deny("SIGNED_INPUT_OVERSIZE")
                hasher.update(chunk)
    except OSError:
        deny("SIGNED_INPUT_UNAVAILABLE")
    if counted != size:
        deny("SIGNED_INPUT_CHANGED")
    return hasher.hexdigest(), counted


def verify(*, rpm_file: Path, public_key: Path, pinned_fingerprint: str,
           source_root: Path):
    """CI-only package payload provenance. Does NOT verify running guest."""
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.geteuid() != 0:
        deny("DISPOSABLE_CI_REQUIRED")
    if type(pinned_fingerprint) is not str or not FPR.fullmatch(pinned_fingerprint):
        deny("INVALID_PIN")
    rpm_file, public_key, source_root = map(
        Path, (rpm_file, public_key, source_root))
    if not (rpm_file.is_absolute() and public_key.is_absolute() and
            source_root.is_absolute()):
        deny("ABSOLUTE_INPUTS_REQUIRED")
    rpm_digest, rpm_size = _digest(rpm_file, maximum=MAX_RPM)
    _root_owned_regular(public_key, maximum=65536)
    if not source_root.is_dir() or source_root.is_symlink():
        deny("SOURCE_ROOT_UNSAFE")

    with tempfile.TemporaryDirectory(prefix="c3eo-ci-") as td:
        work = Path(td)
        work.chmod(0o700)
        homedir = work / "gpg"
        homedir.mkdir(mode=0o700)
        _run(["gpg", "--homedir", str(homedir), "--batch",
              "--import", str(public_key)])
        listing = _run(["gpg", "--homedir", str(homedir), "--batch",
                        "--with-colons", "--fingerprint", "--list-keys"])
        ids = [line.split(":")[9] for line in listing.decode().splitlines()
               if line.startswith("fpr:")]
        if ids != [pinned_fingerprint]:
            deny("RPM_SIGNER_PIN_MISMATCH")
        db = work / "rpmdb"
        db.mkdir(mode=0o700)
        _run(["rpm", "--dbpath", str(db), "--initdb"])
        _run(["rpm", "--dbpath", str(db), "--import", str(public_key)])
        signature = _run(["rpmkeys", "--dbpath", str(db), "--checksig",
                          "--verbose", str(rpm_file)])
        if (not re.search(rb"signature.{0,120}\bOK\b", signature, re.I) and
                not re.search(rb"signatures\s+OK", signature, re.I)):
            deny("RPM_SIGNATURE_NOT_VERIFIED")
        identity = _run(["rpm", "-qp", "--qf",
                         "%{NAME} %{VERSION} %{ARCH}", str(rpm_file)])
        if identity.decode().strip() != PACKAGE_NAME + " 0.1 noarch":
            deny("RPM_IDENTITY_REFUSED")
        paths = _run(["rpm", "-qpl", str(rpm_file)]).decode().splitlines()
        if len(paths) != len(EXPECTED) or set(paths) != set(EXPECTED):
            deny("RPM_MEMBER_LIST_REFUSED")
        if _run(["rpm", "-qp", "--scripts", str(rpm_file)]).strip():
            deny("RPM_SCRIPTLETS_REFUSED")
        if _run(["rpm", "-qp", "--triggers", str(rpm_file)]).strip():
            deny("RPM_TRIGGERS_REFUSED")
        # First authenticate the signed package, then extract into an isolated
        # temporary directory; no RPM install, hooks or system DB operations.
        archive = _run(["rpm2cpio", str(rpm_file)])
        if not 0 < len(archive) <= 16 * 1024 * 1024:
            deny("RPM_ARCHIVE_SIZE_REFUSED")
        extracted = work / "extracted"
        extracted.mkdir(mode=0o700)
        _run(["cpio", "-idm", "--no-absolute-filenames", "--quiet"],
             input_bytes=archive, cwd=extracted)
        actual_paths = {
            "/" + str(p.relative_to(extracted))
            for p in extracted.rglob("*") if p.is_file() or p.is_symlink()
        }
        if actual_paths != set(EXPECTED):
            deny("RPM_EXTRACTED_MEMBERS_REFUSED")
        evidence = {}
        for installed, (source, expected_mode) in EXPECTED.items():
            payload = extracted / installed.lstrip("/")
            expected = source_root / source
            try:
                pstat = os.lstat(payload)
                sstat = os.lstat(expected)
            except OSError:
                deny("RPM_MEMBER_NOT_FOUND")
            if (not stat.S_ISREG(pstat.st_mode) or
                    stat.S_IMODE(pstat.st_mode) != expected_mode or
                    not stat.S_ISREG(sstat.st_mode) or
                    stat.S_IMODE(sstat.st_mode) & 0o022):
                deny("RPM_PAYLOAD_MODE_OR_TYPE_REFUSED")
            phash, psize = _digest(payload, maximum=MAX_MEMBER)
            shash, ssize = _digest(expected, maximum=MAX_MEMBER)
            if phash != shash or psize != ssize:
                deny("RPM_PAYLOAD_SOURCE_MISMATCH")
            evidence[installed] = phash
        script = extracted / "usr/libexec/post-apollo/connections-status-host"
        if not script.read_bytes().startswith(
                b"#!/opt/postapollo-c2o-venv/bin/python3\n"):
            deny("SIGNED_HOST_SHEBANG_REFUSED")
        unit = extracted / "usr/lib/systemd/system/postapollo-connections-status.service"
        body = unit.read_text()
        # systemd ignores comments; the canonical unit deliberately has a
        # comment saying "no [Install] stanza". Check ACTIVE directives,
        # never count a comment as an actual install/enablement section.
        active = [line.strip() for line in body.splitlines()
                  if line.strip() and not line.lstrip().startswith(("#", ";"))]
        required = {
            "ExecStart=/usr/libexec/post-apollo/connections-status-host --read-only",
            "NoNewPrivileges=yes", "RestrictAddressFamilies=AF_UNIX",
            "IPAddressDeny=any", "Restart=no", "DynamicUser=no",
            "CapabilityBoundingSet=", "AmbientCapabilities=",
        }
        if (active.count("[Service]") != 1 or
                active.count("ExecStart=/usr/libexec/post-apollo/connections-status-host --read-only") != 1 or
                not required.issubset(set(active)) or
                "[Install]" in active):
            deny("SIGNED_UNIT_SCOPE_REFUSED")
        return {
            "schema": SCHEMA, "rpm_sha256": rpm_digest,
            "rpm_size": rpm_size, "package_signature_checked_ci": True,
            "payload_sha256": evidence,
            "host_script_is_python_not_native_elf": True,
            "installedGuestMeasured": False,
            "hostAuthenticated": False,
            "canApprove": False,
            "credentialActionsEnabled": False,
            "productionAuthority": False,
        }
