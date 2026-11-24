#!/usr/bin/env python3
"""C4b: host-issued nonce ↔ actual signed BEGIN denial, real VM CI only.

The controller creates a fresh nonce BEFORE assembling the offline guest ISO.
The installed gateway's first UNAVAILABLE BEGIN receipt must sign that nonce.
After the guest's real two-boot rollback, the separate controller verifies the
Ed25519 receipt and nonce using the returned guest public key.

IMPORTANT: The public key itself is NOT independently enrolled; therefore a
forged guest may report another public key and sign its own receipt. This is
challenge-freshness and proof-of-possession diagnostics ONLY, not host
attestation, outside witness custody, C5 consent or any production permission.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import os
from pathlib import Path
import re
import secrets
import stat
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/identity"))
from signed_command_receipt_v0 import ReceiptRejected, verify_receipt

SCHEMA = "postapollo.identity.c4b.controller-challenge.ci-v1"
PROOF_PREFIX = b"C4B_ID_CHALLENGE_PROOF // "
MARKER_RE = re.compile(
    rb"C4B_ID_CHALLENGE_PROOF // pub=([A-Za-z0-9_-]{43}) "
    rb"frame=([A-Za-z0-9_-]{1,1400})\Z", re.ASCII,
)
NONCE_RE = re.compile(rb"[A-Za-z0-9_-]{43}\Z", re.ASCII)
B64_RE = re.compile(rb"[A-Za-z0-9_-]+\Z", re.ASCII)
MAX_SERIAL_BYTES = 64 * 1024 * 1024
NEGATIVE = {
    "operatorReleaseRootEnrolled": False,
    "remoteSignedLinuxOriginAuthenticated": False,
    "independentlyEnrolledReceiptSignerVerified": False,
    "externallyProtectedChallengeLedgerVerified": False,
    "externalRollbackResistanceVerified": False,
    "c5HumanConsentVerified": False,
    "hostAuthenticated": False,
    "canBeginSignIn": False,
    "credentialActionsEnabled": False,
    "productionAuthority": False,
}

class Refused(ValueError):
    """Host-issued fresh challenge or signed receipt refused."""

def _deny(reason):
    raise Refused(reason)

def _ci_guard():
    if (sys.platform != "linux"
            or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"
            or os.environ.get("POST_APOLLO_ID_SILVERBLUE_CI_ONLY") != "1"
            or os.environ.get("GITHUB_ACTOR") != "kudokudo1"):
        _deny("C4B_CONTROLLER_DISPOSABLE_GITHUB_CI_ONLY")

def _decode(value: bytes, limit: int) -> bytes:
    if (type(value) is not bytes or not 0 < len(value) <= limit
            or B64_RE.fullmatch(value) is None):
        _deny("C4B_CONTROLLER_NONCANONICAL_BASE64URL")
    try:
        output = base64.urlsafe_b64decode(value + b"=" * (-len(value) % 4))
    except (ValueError, binascii.Error) as exc:
        raise Refused("C4B_CONTROLLER_BASE64_DECODE_REFUSED") from exc
    if (base64.urlsafe_b64encode(output).rstrip(b"=") != value):
        _deny("C4B_CONTROLLER_BASE64_REENCODE_MISMATCH")
    return output

def _validate_challenge(value):
    if (type(value) is not bytes or NONCE_RE.fullmatch(value) is None
            or len(_decode(value, 43)) != 32):
        _deny("C4B_CONTROLLER_CHALLENGE_INVALID")
    return value.decode("ascii")

def generate_controller_challenge() -> str:
    """Only fresh host-controller entropy; never send a signing private key."""
    return _validate_challenge(
        base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"="),
    )

def _create_nonce_file(path: Path):
    _ci_guard()
    if not isinstance(path, Path) or not path.is_absolute():
        _deny("C4B_CONTROLLER_NONABSOLUTE_CHALLENGE_PATH")
    nonce = generate_controller_challenge().encode("ascii")
    fd = None
    try:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                     os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        os.fchmod(fd, 0o600)
        os.write(fd, nonce + b"\n")
        os.fsync(fd)
    except OSError as exc:
        raise Refused("C4B_CONTROLLER_CHALLENGE_FILE_CREATE_REFUSED") from exc
    finally:
        if fd is not None:
            os.close(fd)
    return hashlib.sha256(nonce).hexdigest()

def _read_nonce_file(path: Path):
    if not isinstance(path, Path) or not path.is_absolute():
        _deny("C4B_CONTROLLER_NONABSOLUTE_CHALLENGE_PATH")
    fd = None
    try:
        fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC |
                     os.O_NONBLOCK)
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.geteuid()
                or stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1
                or st.st_size != 44):
            _deny("C4B_CONTROLLER_CHALLENGE_FILE_UNSAFE")
        raw = os.read(fd, 45)
    except OSError as exc:
        raise Refused("C4B_CONTROLLER_CHALLENGE_FILE_UNAVAILABLE") from exc
    finally:
        if fd is not None:
            os.close(fd)
    if len(raw) != 44 or raw[-1:] != b"\n":
        _deny("C4B_CONTROLLER_CHALLENGE_FILE_MALFORMED")
    return _validate_challenge(raw[:-1])

def _proof_bytes(serial: bytes):
    if type(serial) is not bytes or not 0 < len(serial) <= MAX_SERIAL_BYTES:
        _deny("C4B_CONTROLLER_SERIAL_BOUNDS_REFUSED")
    matches = []
    for line in serial.split(b"\n"):
        if PROOF_PREFIX not in line:
            continue
        # QEMU UART wraps payload with control prefixes on some boots.
        # Unlike the general diagnostic sanitizer, never accept a proof
        # with arbitrary leading material or a second marker inside it.
        if line.endswith(b"\r"):
            line = line[:-1]
        if not line.startswith(PROOF_PREFIX):
            _deny("C4B_CONTROLLER_PROOF_PREFIX_OR_CONTROL_REFUSED")
        if any(not 32 <= b <= 126 for b in line):
            _deny("C4B_CONTROLLER_PROOF_NONPRINTABLE_REFUSED")
        matches.append(line)
    if len(matches) != 1:
        _deny("C4B_CONTROLLER_EXACTLY_ONE_PROOF_REQUIRED")
    m = MARKER_RE.fullmatch(matches[0])
    if m is None:
        _deny("C4B_CONTROLLER_PROOF_SHAPE_REFUSED")
    pub = _decode(m.group(1), 43)
    frame = _decode(m.group(2), 1400)
    if len(pub) != 32 or not 0 < len(frame) <= 1024:
        _deny("C4B_CONTROLLER_PROOF_KEY_OR_FRAME_SIZE_REFUSED")
    return pub, frame

def inspect_ci_only(*, serial: bytes, controller_challenge: str):
    if type(controller_challenge) is not str:
        _deny("C4B_CONTROLLER_CHALLENGE_TYPE_REFUSED")
    try:
        challenge = _validate_challenge(controller_challenge.encode("ascii"))
    except UnicodeEncodeError as exc:
        raise Refused("C4B_CONTROLLER_CHALLENGE_ASCII_REQUIRED") from exc
    pub, frame = _proof_bytes(serial)
    try:
        signed = verify_receipt(
            frame,
            pinned_key=Ed25519PublicKey.from_public_bytes(pub),
            action="BEGIN",
            command_request_id=None,
            client_nonce=challenge,
        )
    except (ReceiptRejected, ValueError) as exc:
        raise Refused("C4B_CONTROLLER_ACTUAL_SIGNED_BEGIN_CHALLENGE_REFUSED") from exc
    if (signed.get("state") != "UNAVAILABLE"
            or signed.get("requestId") is not None):
        _deny("C4B_CONTROLLER_NON_DENIAL_RECEIPT_REFUSED")
    return {
        "schema": SCHEMA,
        "freshControllerNonceInActualSignedBeginDenialInCI": True,
        "publicKeyVerifiedOnlyForThisCIReceipt": True,
        "controllerChallengeSha256": hashlib.sha256(
            challenge.encode("ascii")
        ).hexdigest(),
        "receiptFrameSha256": hashlib.sha256(frame).hexdigest(),
        "runtimePublicKeySha256": hashlib.sha256(pub).hexdigest(),
        **NEGATIVE,
    }

def _read_serial_file(path: Path):
    """Bounded regular-file read, including refusal of an idle named pipe."""
    fd = None
    try:
        fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW |
                     os.O_CLOEXEC | os.O_NONBLOCK)
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or
                not 0 < before.st_size <= MAX_SERIAL_BYTES):
            _deny("C4B_CONTROLLER_GUEST_SERIAL_UNSAFE")
        with os.fdopen(fd, "rb") as stream:
            fd = None
            raw = stream.read(MAX_SERIAL_BYTES + 1)
            after = os.fstat(stream.fileno())
        if (len(raw) != before.st_size or
                (before.st_dev, before.st_ino, before.st_size,
                 before.st_mtime_ns, before.st_ctime_ns) !=
                (after.st_dev, after.st_ino, after.st_size,
                 after.st_mtime_ns, after.st_ctime_ns)):
            _deny("C4B_CONTROLLER_GUEST_SERIAL_CHANGED")
        return raw
    except OSError:
        _deny("C4B_CONTROLLER_GUEST_SERIAL_UNAVAILABLE")
    finally:
        if fd is not None:
            os.close(fd)


def _main(argv):
    if ((len(argv) == 2 and argv[0] == "issue")
            or (len(argv) == 3 and argv[0] == "verify")):
        pass
    else:
        _deny("C4B_CONTROLLER_COMMAND_SCOPE_REFUSED")
    _ci_guard()
    if argv[0] == "issue":
        digest = _create_nonce_file(Path(argv[1]))
        print("C4B_ID_PASS // CONTROLLER_FRESH_NONCE_ISSUED_CI_ONLY")
        print("C4B_ID_STAGE // CONTROLLER_NONCE_SHA256=" + digest)
        return 0
    nonce_path, serial_path = map(Path, argv[1:])
    nonce = _read_nonce_file(nonce_path)
    raw = _read_serial_file(serial_path)
    result = inspect_ci_only(serial=raw, controller_challenge=nonce)
    if any(result.get(key) is not False for key in NEGATIVE):
        _deny("C4B_CONTROLLER_AUTHORITY_FLAG_PROMOTION")
    print("C4B_ID_PASS // HOST_CONTROLLER_FRESH_CHALLENGE_SIGNED_DENIAL_VERIFIED")
    print("C4B_ID_LIMITATION // CHALLENGE_KEY_NOT_EXTERNALLY_ENROLLED_NO_HOST_AUTH")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(_main(sys.argv[1:]))
    except Refused as exc:
        print("C4B_ID_BLOCKED // " + str(exc), file=sys.stderr)
        raise SystemExit(2)
