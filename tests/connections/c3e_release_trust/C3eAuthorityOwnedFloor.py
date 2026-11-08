#!/usr/bin/env python3
"""C3e-E: disposable *separate-process* release-history authority fixture.

This program receives a bounded untrusted JSON request over stdin. It NEVER
takes minimum release floors from that request. Instead, it reads its OWN
CI-only SQLite checkpoint and signs the current committed floors for a
verifier-generated challenge. Advancing that checkpoint requires the existing
C3e-A root-authorized real OpenPGP release verification via C3e-C.

The ledger and signing home are supplied by a trusted *CI harness*, not by
the untrusted request. This is NOT an OS-isolated, production-controlled or
hardware rollback-resistant authority. It installs nothing and grants nothing.
"""
from __future__ import annotations

import argparse
import base64
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).parent


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, HERE / path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3EE_DEPENDENCY_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


durable = _load("c3ee_durable", "C3eDurableFloor.py")
proof = _load("c3ee_proof", "C3eExternalFloorProof.py")
admission = _load("c3ee_release", "C3eReleaseAdmission.py")

MAX_REQUEST = 8192
ADVANCE_FIELDS = frozenset({
    "op", "policy", "policy_signature", "delegated_public",
    "manifest", "manifest_signature", "artifact",
})
ATTEST_FIELDS = frozenset({
    "op", "challenge", "node_id", "release_root_pin",
})


class Refused(Exception):
    pass


def deny(code: str):
    raise Refused(code)


def _fingerprint(value):
    try:
        return admission._fingerprint(value)
    except admission.Refused:
        deny("BAD_PIN")


def _strict_json(data: bytes) -> dict:
    if not 0 < len(data) <= MAX_REQUEST:
        deny("REQUEST_SIZE_REFUSED")

    def unique(pairs):
        obj = {}
        for key, val in pairs:
            if key in obj:
                deny("DUPLICATE_REQUEST_FIELD")
            obj[key] = val
        return obj

    try:
        obj = json.loads(data.decode("utf-8"), object_pairs_hook=unique)
    except (ValueError, UnicodeError):
        deny("REQUEST_JSON_REFUSED")
    if type(obj) is not dict:
        deny("REQUEST_SHAPE_REFUSED")
    return obj


def _state(args) -> tuple[int, int, str, str]:
    try:
        root_pin, epoch, sequence, policy_hash, artifact_hash = durable.inspect(
            args.state_db)
    except durable.Refused:
        deny("AUTHORITY_LEDGER_UNAVAILABLE")
    if root_pin != args.release_root_pin:
        deny("AUTHORITY_ROOT_PIN_MISMATCH")
    return epoch, sequence, policy_hash, artifact_hash


def _advance(args, request: dict) -> dict:
    if set(request) != ADVANCE_FIELDS:
        deny("ADVANCE_REQUEST_SHAPE_REFUSED")
    epoch, sequence, _, _ = _state(args)
    paths = {}
    for key in ADVANCE_FIELDS - {"op"}:
        raw = request[key]
        if type(raw) is not str or not raw.startswith("/") or len(raw) > 2048:
            deny("INVALID_RELEASE_INPUT_PATH")
        paths[key] = Path(raw)

    try:
        durable.admit_and_record(
            args.state_db,
            external_root_pin=args.release_root_pin,
            # Authority derives its floors from ITS checkpoint. The caller
            # has no "floor", "epoch", or "sequence" request fields.
            external_epoch_floor=epoch,
            external_sequence_floor=sequence,
            root_public=args.release_root_public,
            policy=paths["policy"],
            policy_signature=paths["policy_signature"],
            delegated_public=paths["delegated_public"],
            manifest=paths["manifest"],
            manifest_signature=paths["manifest_signature"],
            artifact=paths["artifact"],
        )
    except durable.Refused as error:
        deny("SIGNED_RELEASE_REFUSED_" + str(error))
    current_epoch, current_seq, _, _ = _state(args)
    return {
        "status": "C3EE_SIGNED_RELEASE_COMMITTED_TEST_ONLY",
        "epoch": current_epoch,
        "sequence": current_seq,
    }


def _sign(args, payload: bytes) -> bytes:
    # The disposable signing home must contain exactly the independently
    # pinned test identity. Never import keys from the candidate or request.
    secret = admission._cmd([
        "gpg", "--homedir", str(args.anchor_secret_home), "--batch",
        "--with-colons", "--fingerprint", "--list-secret-keys",
    ])
    fingerprints = [
        line.split(":")[9] for line in secret.stdout.splitlines()
        if line.startswith("fpr:")
    ]
    if (secret.returncode != 0 or len(fingerprints) != 1 or
            fingerprints[0] != args.anchor_pin):
        deny("PINNED_AUTHORITY_SIGNER_UNAVAILABLE")
    with tempfile.TemporaryDirectory(prefix="c3ee-sign-") as td:
        p = Path(td)
        message = p / "statement.json"
        signature = p / "statement.sig"
        message.write_bytes(payload)
        result = subprocess.run(
            ["gpg", "--homedir", str(args.anchor_secret_home),
             "--batch", "--no-tty", "--yes", "--pinentry-mode", "loopback",
             "--passphrase", "", "--local-user", args.anchor_pin,
             "--detach-sign", "--output", str(signature), str(message)],
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
            timeout=20, check=False)
        if result.returncode != 0 or not signature.is_file():
            deny("AUTHORITY_SIGNING_FAILED")
        return signature.read_bytes()


def _attest(args, request: dict) -> dict:
    if set(request) != ATTEST_FIELDS:
        deny("ATTEST_REQUEST_SHAPE_REFUSED")
    if (request["node_id"] != args.node_id or
            type(request["node_id"]) is not str):
        deny("UNAUTHORIZED_NODE")
    if request["release_root_pin"] != args.release_root_pin:
        deny("UNAUTHORIZED_RELEASE_ROOT")
    challenge = request["challenge"]
    if (type(challenge) is not str or
            proof.CHALLENGE_PATTERN.fullmatch(challenge) is None):
        deny("INVALID_VERIFIER_CHALLENGE")

    epoch, sequence, policy_digest, artifact_digest = _state(args)
    # An explicitly bootstrapped but never independently verified release
    # is NOT proof of any admitted artifact. Refuse signing before admission.
    if not policy_digest or not artifact_digest:
        deny("NO_VERIFIED_RELEASE_HISTORY")
    statement = {
        "schema": proof.SCHEMA,
        "audience": proof.AUDIENCE,
        "release_id": admission.RELEASE_ID,
        "node_id": args.node_id,
        "challenge": challenge,
        "release_root_pin": args.release_root_pin,
        "minimum_policy_epoch": epoch,
        "minimum_release_sequence": sequence,
    }
    message = json.dumps(
        statement, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = _sign(args, message)
    return {
        "proof_b64": base64.b64encode(message).decode("ascii"),
        "signature_b64": base64.b64encode(signature).decode("ascii"),
    }


def handle(args, request: dict) -> dict:
    if type(request) is not dict:
        deny("REQUEST_SHAPE_REFUSED")
    op = request.get("op")
    if op == "advance":
        return _advance(args, request)
    if op == "attest":
        return _attest(args, request)
    deny("UNSUPPORTED_AUTHORITY_OPERATION")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-db", type=Path, required=True)
    parser.add_argument("--release-root-public", type=Path, required=True)
    parser.add_argument("--release-root-pin", required=True)
    parser.add_argument("--anchor-secret-home", type=Path, required=True)
    parser.add_argument("--anchor-pin", required=True)
    parser.add_argument("--node-id", required=True)
    args = parser.parse_args()
    try:
        _fingerprint(args.release_root_pin)
        _fingerprint(args.anchor_pin)
        if args.anchor_pin == args.release_root_pin:
            deny("AUTHORITY_NOT_INDEPENDENT_OF_RELEASE_ROOT")
        if (not proof.NODE_PATTERN.fullmatch(args.node_id) or
                not args.state_db.is_absolute() or
                not args.release_root_public.is_absolute() or
                not args.anchor_secret_home.is_absolute()):
            deny("UNSAFE_AUTHORITY_CONFIGURATION")
        request = _strict_json(sys.stdin.buffer.read(MAX_REQUEST + 1))
        answer = handle(args, request)
    except Refused as error:
        print(json.dumps({"refused": str(error)}, sort_keys=True))
        return 2
    except (OSError, subprocess.TimeoutExpired, ValueError):
        print(json.dumps({"refused": "AUTHORITY_IO_UNAVAILABLE"}))
        return 2
    print(json.dumps(answer, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
