#!/usr/bin/env python3
"""C3e-Q: CI-only challenge-bound signed guest-measurement envelope consumer.

A verifier-originated one-use challenge binds one signed statement containing
C3e-O's signed RPM digest + Python host payload hash, and C3e-P's observed
runtime script/interpreter/process facts. An isolated GPG keyring enforces a
separately pinned test signer fingerprint. This NEVER signs for a guest,
measures C4b, installs services, authenticates production, or releases keys.

A signer in the same CI trust domain as a compromised guest can lie. Signature
verification proves only WHICH test key signed the report, NOT that the guest,
kernel or interpreter data are true. Issuer/enrollment and nonce persistence
are unsolved; this is a protocol seam for the independent C4b owner.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile

SCHEMA = "postapollo.connections.c3eq-signed-guest-evidence.v1"
RECEIPT_SCHEMA = "postapollo.connections.c3eq-ci-verification-receipt.v1"
HEX64 = re.compile(r"[0-9a-f]{64}")
FPR = re.compile(r"[A-F0-9]{40}")
POLICY = re.compile(r"postapollo.connections.c3e[o-p].*")
MAX_EVIDENCE = 4096
MAX_SIG = 8192
MAX_PUBLIC = 65536
FIELDS = {
    "schema", "challenge_sha256", "release_rpm_sha256",
    "signed_script_sha256", "running_script_sha256", "service_pid",
    "process_start_ticks", "service_uid", "service_gid", "interpreter_sha256",
    "systemd_unit", "dbus_owner_pid", "selinux_enforcing",
    "guest_provenance", "hostAuthenticated", "canApprove",
    "credentialActionsEnabled", "productionAuthority",
}
UNIT = "postapollo-connections-status.service"
GUEST = "c4b-disposable-silverblue-observed-not-authenticated"


class Refused(Exception):
    pass


def deny(code: str):
    raise Refused(code)


def exact_json(data: bytes):
    def unique(items):
        out = {}
        for key, value in items:
            if key in out:
                deny("DUPLICATE_EVIDENCE_FIELD")
            out[key] = value
        return out
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=unique)
    except (ValueError, UnicodeError):
        deny("EVIDENCE_JSON_INVALID")
    if type(value) is not dict or set(value) != FIELDS:
        deny("EVIDENCE_SHAPE_REFUSED")
    if (value["schema"] != SCHEMA or value["systemd_unit"] != UNIT or
            value["guest_provenance"] != GUEST or
            value["selinux_enforcing"] is not True):
        deny("EVIDENCE_ROLE_OR_DOMAIN_REFUSED")
    if any(value[k] is not False for k in (
            "hostAuthenticated", "canApprove",
            "credentialActionsEnabled", "productionAuthority")):
        deny("EVIDENCE_CLAIMS_AUTHORITY")
    for name in ("challenge_sha256", "release_rpm_sha256",
                 "signed_script_sha256", "running_script_sha256",
                 "interpreter_sha256"):
        if type(value[name]) is not str or not HEX64.fullmatch(value[name]):
            deny("EVIDENCE_HASH_INVALID")
    if value["running_script_sha256"] != value["signed_script_sha256"]:
        deny("RUNNING_SCRIPT_DIFFERS_FROM_SIGNED_PACKAGE")
    for name in ("service_pid", "dbus_owner_pid", "service_uid",
                 "service_gid"):
        if type(value[name]) is not int or value[name] <= 0:
            deny("EVIDENCE_PROCESS_IDENTITY_INVALID")
    if value["dbus_owner_pid"] != value["service_pid"]:
        deny("DBUS_SYSTEMD_PROCESS_MISMATCH")
    if (type(value["process_start_ticks"]) is not str or
            not value["process_start_ticks"].isdecimal() or
            int(value["process_start_ticks"]) <= 0):
        deny("PROCESS_START_TICKS_INVALID")
    return value


def safe_bytes(path: Path, ceiling: int, code: str):
    fd = None
    try:
        fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or
                st.st_uid != os.geteuid() or stat.S_IMODE(st.st_mode) & 0o022
                or st.st_size < 1 or st.st_size > ceiling):
            deny(code)
        out = bytearray()
        while len(out) <= ceiling:
            chunk = os.read(fd, min(32768, ceiling + 1 - len(out)))
            if not chunk:
                break
            out.extend(chunk)
        after = os.fstat(fd)
        if (len(out) != st.st_size or len(out) > ceiling or
                (st.st_dev, st.st_ino, st.st_mtime_ns, st.st_ctime_ns) !=
                (after.st_dev, after.st_ino, after.st_mtime_ns, after.st_ctime_ns)):
            deny(code)
        return bytes(out)
    except OSError:
        deny(code)
    finally:
        if fd is not None:
            os.close(fd)


def tool(args):
    try:
        r = subprocess.run(args, capture_output=True, timeout=12, check=False,
                           stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        deny("GPG_TOOL_UNAVAILABLE")
    if r.returncode:
        deny("SIGNED_EVIDENCE_CRYPTO_REFUSED")
    return r.stdout, r.stderr


def verify_detached(*, evidence: Path, signature: Path,
                    public_key: Path, pinned_signer: str):
    if (type(pinned_signer) is not str or
            not FPR.fullmatch(pinned_signer)):
        deny("PINNED_TEST_SIGNER_INVALID")
    raw = safe_bytes(evidence, MAX_EVIDENCE, "EVIDENCE_FILE_UNSAFE")
    sig = safe_bytes(signature, MAX_SIG, "SIGNATURE_FILE_UNSAFE")
    pub = safe_bytes(public_key, MAX_PUBLIC, "PUBLIC_KEY_UNSAFE")
    with tempfile.TemporaryDirectory(prefix="c3eq-gpg-") as temp:
        home = Path(temp)
        home.chmod(0o700)
        a = home / "evidence.json"
        b = home / "signature.bin"
        c = home / "key.asc"
        a.write_bytes(raw)
        b.write_bytes(sig)
        c.write_bytes(pub)
        for path in (a, b, c):
            path.chmod(0o600)
        tool(["gpg", "--homedir", str(home), "--batch",
              "--no-auto-key-retrieve", "--import", str(c)])
        listing, _ = tool(["gpg", "--homedir", str(home), "--batch",
                            "--with-colons", "--fingerprint", "--list-keys"])
        fingerprints = [line.split(":")[9] for line in listing.decode().splitlines()
                        if line.startswith("fpr:")]
        if fingerprints != [pinned_signer]:
            deny("SIGNED_EVIDENCE_SIGNER_MISMATCH")
        status, _ = tool(["gpg", "--homedir", str(home), "--batch",
                          "--no-auto-key-retrieve", "--status-fd", "1",
                          "--verify", str(b), str(a)])
        valid = [line.split() for line in status.decode().splitlines()
                 if line.startswith("[GNUPG:] VALIDSIG ")]
        if len(valid) != 1 or valid[0][2] != pinned_signer:
            deny("SIGNED_EVIDENCE_SIGNER_MISMATCH")
    return raw


class OneUseTestChallenge:
    """Volatile one-use challenge only. Not a persistent replay ledger."""
    def __init__(self, challenge: bytes):
        if type(challenge) is not bytes or len(challenge) != 32:
            deny("CHALLENGE_BYTES_INVALID")
        self.digest = hashlib.sha256(challenge).hexdigest()
        self.consumed = False

    def verify(self, *, evidence: Path, signature: Path, public_key: Path,
               pinned_signer: str, expected_rpm_sha256: str,
               expected_script_sha256: str, expected_interpreter_sha256: str,
               expected_service_pid: int, expected_start_ticks: str):
        if self.consumed:
            deny("CHALLENGE_ALREADY_CONSUMED")
        for h in (expected_rpm_sha256, expected_script_sha256,
                  expected_interpreter_sha256):
            if type(h) is not str or HEX64.fullmatch(h) is None:
                deny("INDEPENDENT_PIN_INVALID")
        if (type(expected_service_pid) is not int or expected_service_pid <= 0
                or type(expected_start_ticks) is not str or
                not expected_start_ticks.isdecimal() or
                int(expected_start_ticks) <= 0):
            deny("INDEPENDENT_PROCESS_PIN_INVALID")
        signed = verify_detached(
            evidence=evidence, signature=signature,
            public_key=public_key, pinned_signer=pinned_signer)
        statement = exact_json(signed)
        if statement["challenge_sha256"] != self.digest:
            deny("CHALLENGE_NOT_BOUND_TO_SIGNED_EVIDENCE")
        if (statement["release_rpm_sha256"] != expected_rpm_sha256 or
                statement["signed_script_sha256"] != expected_script_sha256 or
                statement["interpreter_sha256"] != expected_interpreter_sha256):
            deny("SIGNED_ARTIFACT_OR_INTERPRETER_PIN_MISMATCH")
        if (statement["service_pid"] != expected_service_pid or
                statement["process_start_ticks"] != expected_start_ticks):
            deny("SIGNED_RUNTIME_PROCESS_PIN_MISMATCH")
        self.consumed = True
        return {
            "schema": RECEIPT_SCHEMA,
            "signedEvidenceValidInCI": True,
            "challengeConsumedInMemory": True,
            "signedGuestOriginAuthenticated": False,
            "installedGuestMeasured": False,
            "hostAuthenticated": False,
            "canApprove": False,
            "credentialActionsEnabled": False,
            "productionAuthority": False,
        }
