#!/usr/bin/env python3
"""C3e-D CI-only, challenge-bound external release floor proof.

The local verifier generates an unpredictable challenge and checks that an
independent pinned *freshness signer* authenticated a floor for that challenge,
node and release root. It then feeds the signed floors to C3e-C's existing
signed-release SQLite admission. It does not provision or authenticate a real
external authority. No network, production keys, RPM installation or grants.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import secrets
import tempfile
from typing import Callable

HERE = Path(__file__).parent


def _import_source(module_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(module_name, HERE / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3ED_REQUIRED_MODULE_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


admission = _import_source("c3ed_release_admission", "C3eReleaseAdmission.py")
durable = _import_source("c3ed_durable_floor", "C3eDurableFloor.py")

SCHEMA = "postapollo.connections.external-floor-proof.v1"
AUDIENCE = "postapollo.connections.release-admission.test"
NODE_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{2,63}")
CHALLENGE_PATTERN = re.compile(r"[0-9a-f]{64}")
REQUIRED = frozenset({
    "schema", "audience", "release_id", "node_id", "challenge",
    "release_root_pin", "minimum_policy_epoch", "minimum_release_sequence",
})
MAX_PROOF_BYTES = 4096
MAX_SIGNATURE_BYTES = 8192
MAX_ANCHOR_KEY_BYTES = 65536
SUCCESS = "C3ED_SIGNED_FLOOR_COMMITTED_TEST_ONLY"


class Refused(Exception):
    pass


def deny(code: str):
    raise Refused(code)


def _fingerprint(value: str):
    try:
        return admission._fingerprint(value)
    except admission.Refused:
        deny("INVALID_ANCHOR_OR_RELEASE_FINGERPRINT")


def _strict_document(raw: bytes):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_PROOF_BYTES:
        deny("INVALID_PROOF_SIZE")

    def no_duplicates(pairs):
        data = {}
        for key, value in pairs:
            if key in data:
                deny("DUPLICATE_SIGNED_FIELD")
            data[key] = value
        return data

    try:
        obj = json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicates)
    except (ValueError, UnicodeError):
        deny("INVALID_SIGNED_JSON")
    if type(obj) is not dict or set(obj) != REQUIRED:
        deny("INVALID_SIGNED_SHAPE")
    return obj


def _checked_proof(*, anchor_public: Path, anchor_pin: str,
                   proof: bytes, signature: bytes, challenge: str,
                   node_id: str, release_root_pin: str) -> tuple[int, int]:
    if (type(signature) is not bytes or
            not 0 < len(signature) <= MAX_SIGNATURE_BYTES):
        deny("INVALID_SIGNATURE_SIZE")
    if (not isinstance(anchor_public, Path) or
            anchor_public.is_symlink() or not anchor_public.is_file() or
            not 0 < anchor_public.stat().st_size <= MAX_ANCHOR_KEY_BYTES):
        deny("INVALID_EXTERNAL_ANCHOR_FILE")
    if (type(challenge) is not str or
            CHALLENGE_PATTERN.fullmatch(challenge) is None):
        deny("INVALID_CHALLENGE")

    # A distinct release signer cannot fabricate its own external freshness.
    anchor_pin = _fingerprint(anchor_pin)
    release_root_pin = _fingerprint(release_root_pin)
    if anchor_pin == release_root_pin:
        deny("EXTERNAL_ANCHOR_NOT_INDEPENDENT")

    with tempfile.TemporaryDirectory(prefix="c3ed-anchor-proof-") as work:
        home = Path(work)
        public = home / "externally-pinned.asc"
        message = home / "signed-floor.json"
        detached = home / "signed-floor.sig"
        # Snapshot bounded inputs; never trust a pathname during gpgv.
        public.write_bytes(anchor_public.read_bytes())
        message.write_bytes(proof)
        detached.write_bytes(signature)
        try:
            ring = admission._isolated_ring(home, public, "anchor")
            query = admission._cmd([
                "gpg", "--homedir", str(home), "--batch",
                "--no-default-keyring", "--keyring", str(ring),
                "--with-colons", "--fingerprint", "--list-keys",
            ])
            fingerprints = [
                line.split(":")[9] for line in query.stdout.splitlines()
                if line.startswith("fpr:")
            ]
            if (query.returncode != 0 or len(fingerprints) != 1 or
                    fingerprints[0] != anchor_pin):
                deny("EXTERNAL_ANCHOR_PIN_MISMATCH")
            signer = admission._check_detached(ring, detached, message)
            if signer != anchor_pin:
                deny("EXTERNAL_SIGNATURE_NOT_PINNED")
        except admission.Refused:
            deny("EXTERNAL_SIGNATURE_REFUSED")

    obj = _strict_document(proof)
    if obj["schema"] != SCHEMA or obj["audience"] != AUDIENCE:
        deny("WRONG_SIGNED_PROOF_PURPOSE")
    if obj["release_id"] != admission.RELEASE_ID:
        deny("WRONG_SIGNED_RELEASE")
    if obj["node_id"] != node_id:
        deny("WRONG_SIGNED_NODE")
    if obj["release_root_pin"] != release_root_pin:
        deny("WRONG_SIGNED_RELEASE_ROOT")
    if obj["challenge"] != challenge:
        deny("REPLAYED_OR_UNSOLICITED_PROOF")
    epoch = obj["minimum_policy_epoch"]
    sequence = obj["minimum_release_sequence"]
    if (type(epoch) is not int or epoch < 1 or
            type(sequence) is not int or sequence < 1):
        deny("INVALID_SIGNED_FLOORS")
    return epoch, sequence


def admit_with_external_proof(*, db_path: Path,
                              anchor_public: Path, anchor_pin: str,
                              node_id: str, release_root_pin: str,
                              request_proof: Callable[[str], tuple[bytes, bytes]],
                              root_public: Path, policy: Path,
                              policy_signature: Path, delegated_public: Path,
                              manifest: Path, manifest_signature: Path,
                              artifact: Path) -> str:
    """Simulated challenge to an independently pinned signing authority.

    request_proof is an injected CI fixture, NOT a production transport.
    It must return a detached-signature and exact JSON bytes for this unique
    challenge. A real authority needs separate operator enrollment, custody,
    fresh protected state, authenticated transport and recovery rules.
    """
    if type(node_id) is not str or NODE_PATTERN.fullmatch(node_id) is None:
        deny("INVALID_NODE_ID")
    _fingerprint(anchor_pin)
    _fingerprint(release_root_pin)
    if not callable(request_proof):
        deny("EXTERNAL_AUTHORITY_UNAVAILABLE")

    challenge = secrets.token_hex(32)  # Generated inside the verifier, not the candidate.
    try:
        payload = request_proof(challenge)
    except Exception:
        deny("EXTERNAL_AUTHORITY_UNAVAILABLE")
    if type(payload) is not tuple or len(payload) != 2:
        deny("INVALID_AUTHORITY_RESPONSE")
    epoch, seq = _checked_proof(
        anchor_public=Path(anchor_public), anchor_pin=anchor_pin,
        proof=payload[0], signature=payload[1],
        challenge=challenge, node_id=node_id,
        release_root_pin=release_root_pin,
    )
    try:
        result = durable.admit_and_record(
            Path(db_path),
            external_root_pin=release_root_pin,
            external_epoch_floor=epoch,
            external_sequence_floor=seq,
            root_public=Path(root_public),
            policy=Path(policy),
            policy_signature=Path(policy_signature),
            delegated_public=Path(delegated_public),
            manifest=Path(manifest),
            manifest_signature=Path(manifest_signature),
            artifact=Path(artifact),
        )
    except durable.Refused as err:
        deny("RELEASE_CHECKPOINT_REFUSED_" + str(err))
    if result != durable.SUCCESS:
        deny("RELEASE_CHECKPOINT_UNEXPECTED")
    return SUCCESS
