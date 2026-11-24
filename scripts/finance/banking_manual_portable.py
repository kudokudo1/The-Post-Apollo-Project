#!/usr/bin/env python3
"""M4r offline portable encrypted manual Banking snapshot.

The operator moves only the sealed file between devices. No bank/Actual
credentials, automatic import, ledger merge, or desktop activation.
Passphrases and decrypted bytes travel only over private process pipes.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import uuid

import banking_manual_store as manual
import banking_manual_archive as archive

PREFIX = "FINANCEW_BANKING_PORTABLE_"
MAX_ENVELOPE = 380000
MAX_REVISION = 2147483646  # existing QML signed int
NAME = re.compile(r"banking-[0-9a-f]{32}\.sealed\.json")
HEX = re.compile(r"[0-9a-f]{64}")
KIND = "post-apollo-financew-manual-portable-v1"


def fail(code):
    raise manual.Refusal(code)


def b64(raw):
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def unb64(value, maximum):
    if (type(value) is not str or not re.fullmatch(r"[A-Za-z0-9_-]+", value)
            or len(value) > (maximum * 4 + 2) // 3):
        fail("INVALID_BASE64")
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except ValueError:
        fail("INVALID_BASE64")
    if len(raw) > maximum or b64(raw) != value:
        fail("INVALID_BASE64")
    return raw


def validate_envelope(e):
    if (not manual.exact(e, ("kind", "version", "algorithm", "kdf",
                             "iterations", "salt", "nonce", "ciphertext"))
            or e["kind"] != KIND or type(e["version"]) is not int or e["version"] != 1
            or e["algorithm"] != "AES-256-GCM" or e["kdf"] != "PBKDF2-HMAC-SHA256"
            or type(e["iterations"]) is not int or e["iterations"] != 600000
            or len(unb64(e["salt"], 16)) != 16 or len(unb64(e["nonce"], 12)) != 12
            or len(unb64(e["ciphertext"], manual.MAX_BYTES + 16)) <= 16):
        fail("INVALID_ENVELOPE")
    return e


def crypto(frame):
    # Do not pass passphrases via argv/environment, or echo subprocess errors.
    # Ignore Node injection options and unrelated inherited credentials.
    node = shutil.which("node")
    if not node:
        fail("NODE_CRYPTO_UNAVAILABLE")
    script = Path(__file__).resolve().with_name("banking_portable_crypto.mjs")
    try:
        result = subprocess.run([node, str(script)],
            input=archive.compact(frame), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=25, check=False,
            env={"PATH": os.defpath, "LANG": "C.UTF-8"})
    except (OSError, subprocess.TimeoutExpired):
        fail("PORTABLE_CRYPTO_UNAVAILABLE")
    if result.returncode != 0 or len(result.stdout) > MAX_ENVELOPE:
        fail("PORTABLE_CRYPTO_REFUSED")
    return manual.decode(result.stdout)


def valid_password(value):
    if (type(value) is not str or len(value) < 12 or len(value.encode("utf-8")) > 1024
            or re.search(r"[\x00-\x1f\x7f]", value)):
        fail("INVALID_PASSPHRASE")


def name_ok(name):
    return type(name) is str and NAME.fullmatch(name) is not None


def portable_dir(directory, create=False):
    if not manual.private_dir(directory, create):
        return None
    target = directory / "portable"
    if not manual.private_dir(target, create):
        return None
    return target


def load_sealed(directory, name):
    if not name_ok(name):
        fail("INVALID_PORTABLE_ID")
    target = portable_dir(directory)
    if target is None:
        fail("PORTABLE_NOT_FOUND")
    try:
        fd = os.open(target / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        fail("PORTABLE_NOT_FOUND_OR_UNSAFE")
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or info.st_nlink != 1
                or info.st_size > MAX_ENVELOPE):
            fail("UNSAFE_PORTABLE_FILE")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(MAX_ENVELOPE + 1)
        current = os.fstat(fd)
        if (len(raw) != info.st_size or len(raw) > MAX_ENVELOPE
                or current.st_mtime_ns != info.st_mtime_ns
                or current.st_ctime_ns != info.st_ctime_ns):
            fail("PORTABLE_FILE_CHANGED")
        return raw, validate_envelope(manual.decode(raw))
    finally:
        os.close(fd)


def publish(directory, envelope):
    target = portable_dir(directory, True)
    name = "banking-" + uuid.uuid4().hex + ".sealed.json"
    temp = target / ("." + uuid.uuid4().hex + ".tmp")
    raw = archive.compact(validate_envelope(envelope)) + b"\n"
    if len(raw) > MAX_ENVELOPE:
        fail("PORTABLE_LIMIT")
    fd = None
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                     os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(raw)
            stream.flush()
        os.fsync(fd)
        os.close(fd)
        fd = None
        os.link(temp, target / name, follow_symlinks=False)
        os.unlink(temp)
        for path in (target, directory):
            dfd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
        return name, hashlib.sha256(raw).hexdigest()
    finally:
        if fd is not None:
            os.close(fd)
        temp.unlink(missing_ok=True)


def unpack(directory, name, password, expected=None):
    raw, envelope = load_sealed(directory, name)
    digest = hashlib.sha256(raw).hexdigest()
    if expected is not None and digest != expected:
        fail("STALE_PORTABLE_SELECTION")
    result = crypto({"action": "open", "password": password, "envelope": envelope})
    if not manual.exact(result, ("plain",)):
        fail("INVALID_CRYPTO_RESPONSE")
    doc = manual.validate_doc(manual.decode(unb64(result["plain"], manual.MAX_BYTES)))
    if doc["revision"] < 1 or doc["session"]["mode"] != "manual":
        fail("PORTABLE_MANUAL_REQUIRED")
    return doc, digest


def summary(doc, digest):
    return {"sourceRevision": doc["revision"], "sha256": digest,
            "accountCount": len(doc["session"]["accounts"]),
            "entryCount": len(doc["session"]["entries"]),
            "ciphertextAuthenticated": True, "originAuthenticated": False}


def run(directory, command):
    if type(command) is not dict:
        fail("INVALID_COMMAND")
    action = command.get("action")
    if action == "prepare" and manual.exact(command, ("action", "confirmPrepare")):
        if command["confirmPrepare"] is not True:
            fail("EXPLICIT_PREPARE_REQUIRED")
        portable_dir(directory, True)
        return {"action": "prepare", "directoryName": "portable"}
    if action == "export" and manual.exact(
            command, ("action", "expectedRevision", "password", "confirmExport")):
        if command["confirmExport"] is not True:
            fail("EXPLICIT_EXPORT_REQUIRED")
        revision = command["expectedRevision"]
        if type(revision) is not int or not 1 <= revision < MAX_REVISION:
            fail("INVALID_REVISION")
        valid_password(command["password"])

        def export():
            doc = manual.read_doc(directory)
            if doc["revision"] != revision:
                fail("STALE_REVISION")
            if doc["session"]["mode"] != "manual":
                fail("PORTABLE_MANUAL_REQUIRED")
            raw = archive.compact(doc)
            if len(raw) > manual.MAX_BYTES:
                fail("PORTABLE_LIMIT")
            result = crypto({"action": "seal", "password": command["password"],
                             "plain": b64(raw)})
            if not manual.exact(result, ("envelope",)):
                fail("INVALID_CRYPTO_RESPONSE")
            name, digest = publish(directory, result["envelope"])
            return {"action": "export", "portableId": name, "sha256": digest,
                    "sourceRevision": revision, "encrypted": True}

        return archive.with_store_lock(directory, export)
    if action == "preview" and manual.exact(command, ("action", "portableId", "password")):
        valid_password(command["password"])
        doc, digest = unpack(directory, command["portableId"], command["password"])
        return {"action": "preview", "portableId": command["portableId"],
                **summary(doc, digest)}
    if action == "import" and manual.exact(command, (
            "action", "portableId", "password", "expectedSha256",
            "expectedRevision", "confirmImport", "confirmClientsClosed")):
        if command["confirmImport"] is not True or command["confirmClientsClosed"] is not True:
            fail("EXPLICIT_IMPORT_REQUIRED")
        revision = command["expectedRevision"]
        if type(revision) is not int or not 0 <= revision < MAX_REVISION:
            fail("INVALID_REVISION")
        if type(command["expectedSha256"]) is not str or not HEX.fullmatch(command["expectedSha256"]):
            fail("INVALID_EXPECTED_DIGEST")
        valid_password(command["password"])

        def restore():
            current = manual.read_doc(directory)
            if current["revision"] != revision:
                fail("STALE_REVISION")
            if current["session"]["mode"] != "empty":
                fail("DESTINATION_NOT_EMPTY")
            doc, digest = unpack(directory, command["portableId"], command["password"],
                                 command["expectedSha256"])
            # Source revision is provenance, not destination authority.
            next_revision = max(revision, doc["revision"]) + 1
            if next_revision > MAX_REVISION:
                fail("REVISION_LIMIT")
            restored = {"version": 1, "revision": next_revision,
                        "session": doc["session"]}
            manual.write_doc(directory, restored)
            return {"action": "import", "newRevision": next_revision,
                    **summary(doc, digest)}

        if portable_dir(directory) is None:
            fail("PORTABLE_NOT_FOUND")
        return archive.with_store_lock(directory, restore)
    fail("INVALID_ACTION_OR_FIELDS")


def main():
    # Private JSON stdin frame only; never supply passphrases as CLI arguments.
    raw = sys.stdin.buffer.readline(8193)
    if len(raw) > 8192 or not raw.endswith(b"\n"):
        fail("INVALID_INPUT_FRAME")
    result = run(manual.store_dir(), manual.decode(raw))
    print(PREFIX + "RESULT " + json.dumps({
        "source": "LOCAL_OPERATOR_BANKING_PORTABLE",
        "bankVerified": False, "connected": False, **result}, separators=(",", ":")))


if __name__ == "__main__":
    try:
        main()
    except manual.Refusal as error:
        print(PREFIX + "ERROR " + str(error), file=sys.stderr)
        raise SystemExit(1)
    except Exception:
        print(PREFIX + "ERROR OPERATION_FAILED", file=sys.stderr)
        raise SystemExit(1)
