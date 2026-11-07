#!/usr/bin/env python3
"""C3e offline, CI-only release authorization gate.

A separately supplied, *pre-pinned* root authorizes delegated signing keys and
exact expected artifact digests. Detached signatures are checked with gpgv.
The signing keys and public material in a candidate bundle are never authority.
No real signing keys, package installation, application identity or grants.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

POLICY_SCHEMA = "postapollo.connections.release-policy.v1"
MANIFEST_SCHEMA = "postapollo.connections.release-manifest.v1"
RELEASE_ID = "postapollo-connections-status"
FPR = re.compile(r"(?:[0-9A-F]{40}|[0-9A-F]{64})")
SHA256 = re.compile(r"[0-9a-f]{64}")
VALID_SIG = re.compile(r"^\[GNUPG:\] VALIDSIG ([0-9A-F]{40}|[0-9A-F]{64})(?:\s|$)")
MAX_JSON = 65536
MAX_ARTIFACT = 16 * 1024 * 1024


class Refused(Exception):
    pass


def refuse(code: str):
    raise Refused(code)


def _unique_json(path: Path) -> dict:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_JSON:
        refuse("BAD_DOCUMENT_FILE")
    def unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                refuse("DUPLICATE_JSON_KEY")
            result[k] = v
        return result
    try:
        value = json.loads(path.read_text("utf-8"), object_pairs_hook=unique)
    except (OSError, UnicodeError, ValueError):
        refuse("BAD_JSON")
    if type(value) is not dict:
        refuse("BAD_JSON_SHAPE")
    return value


def _fields(obj: object, keys: set[str], code: str):
    if type(obj) is not dict or set(obj) != keys:
        refuse(code)


def _integer(value: object, minimum: int, code: str) -> int:
    if type(value) is not int or value < minimum:
        refuse(code)
    return value


def _fingerprint(value: object) -> str:
    if type(value) is not str or FPR.fullmatch(value) is None:
        refuse("INVALID_FINGERPRINT")
    return value


def _hex_digest(value: object) -> str:
    if type(value) is not str or SHA256.fullmatch(value) is None:
        refuse("INVALID_DIGEST")
    return value


def _cmd(args: list[str]):
    try:
        run = subprocess.run(args, capture_output=True, text=True, timeout=20,
                             stdin=subprocess.DEVNULL, check=False)
    except (OSError, subprocess.TimeoutExpired):
        refuse("CRYPTO_TOOL_UNAVAILABLE")
    return run


def _isolated_ring(home: Path, armored: Path, keyname: str) -> Path:
    if not armored.is_file() or armored.is_symlink():
        refuse("UNTRUSTED_KEY_FILE")
    ring = home / (keyname + ".gpg")
    base = ["gpg", "--homedir", str(home), "--batch", "--no-tty",
            "--no-default-keyring", "--keyring", str(ring)]
    load = _cmd([*base, "--import", str(armored)])
    if load.returncode != 0:
        refuse("KEY_IMPORT_REFUSED")
    listed = _cmd([*base, "--with-colons", "--fingerprint", "--list-keys"])
    if listed.returncode != 0:
        refuse("KEY_LIST_REFUSED")
    pubs = [x for x in listed.stdout.splitlines() if x.startswith("pub:")]
    fprs = [x.split(":")[9] for x in listed.stdout.splitlines()
            if x.startswith("fpr:")]
    # One public primary identity per ring. No borrowed local GPG trust store.
    if len(pubs) != 1 or not fprs:
        refuse("UNEXPECTED_KEYRING_IDENTITY")
    return ring


def _check_detached(ring: Path, signature: Path, message: Path) -> str:
    if (not signature.is_file() or signature.is_symlink() or
            not message.is_file() or message.is_symlink()):
        refuse("MISSING_SIGNATURE_INPUT")
    result = _cmd(["gpgv", "--keyring", str(ring), "--status-fd", "1",
                   str(signature), str(message)])
    if result.returncode != 0:
        refuse("INVALID_DETACHED_SIGNATURE")
    good = [m.group(1) for line in result.stdout.splitlines()
            if (m := VALID_SIG.match(line))]
    if len(good) != 1:
        refuse("NO_UNIQUE_VALID_SIGNER")
    return _fingerprint(good[0])


def verify(root_public: Path, root_pin: str, policy_path: Path,
           policy_signature: Path, delegated_public: Path,
           manifest_path: Path, manifest_signature: Path, artifact: Path,
           min_epoch: int, min_sequence: int) -> str:
    root_pin = _fingerprint(root_pin)
    _integer(min_epoch, 1, "NO_EXTERNAL_EPOCH_FLOOR")
    _integer(min_sequence, 1, "NO_EXTERNAL_SEQUENCE_FLOOR")
    # No network, RPM database, keys or real service touched.
    with tempfile.TemporaryDirectory(prefix="c3e-offline-") as tmp:
        home = Path(tmp)
        os.chmod(home, 0o700)
        root_ring = _isolated_ring(home, root_public, "root")
        # An attacker-supplied root key is useless unless it exactly matches
        # the separately supplied, pre-enrolled fingerprint.
        listed = _cmd(["gpg", "--homedir", str(home), "--batch",
                       "--no-default-keyring", "--keyring", str(root_ring),
                       "--with-colons", "--fingerprint", "--list-keys"])
        primary = [x.split(":")[9] for x in listed.stdout.splitlines()
                   if x.startswith("fpr:")]
        if listed.returncode != 0 or not primary or primary[0] != root_pin:
            refuse("ROOT_PIN_MISMATCH")
        actual_root = _check_detached(root_ring, policy_signature, policy_path)
        if actual_root != root_pin:
            refuse("ROOT_SIGNATURE_MISMATCH")

        p = _unique_json(policy_path)
        _fields(p, {"schema", "release_id", "epoch", "min_sequence",
                    "signers", "approved_artifacts"}, "POLICY_SHAPE_REFUSED")
        if p["schema"] != POLICY_SCHEMA or p["release_id"] != RELEASE_ID:
            refuse("UNEXPECTED_RELEASE_POLICY")
        if _integer(p["epoch"], 1, "INVALID_POLICY_EPOCH") < min_epoch:
            refuse("POLICY_ROLLBACK_REFUSED")
        floor = max(min_sequence,
                    _integer(p["min_sequence"], 1, "INVALID_POLICY_FLOOR"))

        m = _unique_json(manifest_path)
        _fields(m, {"schema", "release_id", "sequence", "sha256", "size"},
                "MANIFEST_SHAPE_REFUSED")
        if m["schema"] != MANIFEST_SCHEMA or m["release_id"] != RELEASE_ID:
            refuse("UNEXPECTED_RELEASE_MANIFEST")
        seq = _integer(m["sequence"], 1, "BAD_RELEASE_SEQUENCE")
        if seq < floor:
            refuse("RELEASE_ROLLBACK_REFUSED")
        digest = _hex_digest(m["sha256"])
        size = _integer(m["size"], 1, "INVALID_ARTIFACT_SIZE")
        if size > MAX_ARTIFACT or not artifact.is_file() or artifact.is_symlink():
            refuse("UNSAFE_ARTIFACT_FILE")
        if artifact.stat().st_size != size:
            refuse("ARTIFACT_SIZE_MISMATCH")
        with artifact.open("rb") as src:
            actual_digest = hashlib.file_digest(src, "sha256").hexdigest()
        if actual_digest != digest:
            refuse("ARTIFACT_DIGEST_MISMATCH")

        approved = p["approved_artifacts"]
        if type(approved) is not list or not approved or len(approved) > 32:
            refuse("INVALID_APPROVED_RELEASES")
        observed_sequences: set[int] = set()
        known = False
        for item in approved:
            _fields(item, {"sequence", "sha256", "size"},
                    "INVALID_APPROVED_RELEASE")
            n = _integer(item["sequence"], 1, "INVALID_APPROVED_RELEASE")
            d = _hex_digest(item["sha256"])
            z = _integer(item["size"], 1, "INVALID_APPROVED_RELEASE")
            if n in observed_sequences:
                refuse("DUPLICATE_RELEASE_SEQUENCE")
            observed_sequences.add(n)
            if n == seq and d == digest and z == size:
                known = True
        if not known:
            refuse("RELEASE_NOT_APPROVED_BY_ROOT")

        signer_ring = _isolated_ring(home, delegated_public, "delegate")
        signer = _check_detached(signer_ring, manifest_signature, manifest_path)
        allowed = p["signers"]
        if type(allowed) is not list or not allowed or len(allowed) > 16:
            refuse("INVALID_SIGNER_POLICY")
        seen: set[str] = set()
        state = None
        for entry in allowed:
            _fields(entry, {"fingerprint", "state"}, "INVALID_SIGNER_ENTRY")
            key = _fingerprint(entry["fingerprint"])
            if entry["state"] not in ("active", "revoked"):
                refuse("INVALID_SIGNER_STATE")
            if key in seen:
                refuse("DUPLICATE_SIGNER")
            seen.add(key)
            if key == signer:
                state = entry["state"]
        if state == "revoked":
            refuse("REVOKED_SIGNER")
        if state != "active":
            refuse("UNAPPROVED_SIGNER")
        return "C3E_TEST_POLICY_ACCEPTED_NO_PRODUCTION_AUTH"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root-public", "root-fingerprint", "policy", "policy-signature",
                 "delegated-public", "manifest", "manifest-signature", "artifact"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--minimum-policy-epoch", type=int, required=True)
    parser.add_argument("--minimum-release-sequence", type=int, required=True)
    args = parser.parse_args()
    try:
        result = verify(
            Path(args.root_public), args.root_fingerprint, Path(args.policy),
            Path(args.policy_signature), Path(args.delegated_public),
            Path(args.manifest), Path(args.manifest_signature),
            Path(args.artifact), args.minimum_policy_epoch,
            args.minimum_release_sequence)
    except Refused as exc:
        print("C3E_REFUSED // " + str(exc))
        return 2
    print("C3E_PASS // " + result)
    print("C3E_LIMITATION // EPHEMERAL_ROOT_NOT_OPERATOR_TRUST_OR_RPM_AUTH")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
