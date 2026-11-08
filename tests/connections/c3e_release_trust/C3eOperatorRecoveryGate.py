#!/usr/bin/env python3
"""C3e-H: read-only, CI-only signed operator supersession authorization.

When C3e-G has a pending release and the authority has advanced to a newer
release, the old transaction cannot complete automatically. This gate
authenticates a narrowly scoped operator SIGNATURE, a fresh authority proof,
the exact pending journal and exact newly root-signed release. It never writes
any ledger, cancels intent, installs a package, or grants production access.

Operator enrollment, independent witness and custody are simulated in CI.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import time
from urllib.parse import quote

HERE = Path(__file__).parent

def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3EH_REQUIRED_SOURCE_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

split = _load("c3eh_split", "C3eSplitCommitRecovery.py")
admission = _load("c3eh_admission", "C3eReleaseAdmission.py")
durable = _load("c3eh_durable", "C3eDurableFloor.py")
proof = _load("c3eh_proof", "C3eExternalFloorProof.py")

SCHEMA = "postapollo.connections.operator-recovery-authorization.v1"
ACTION = "inspect-pending-supersession-test-only"
AUDIENCE = "postapollo.connections.operator-recovery.test"
FIELDS = frozenset({
    "schema", "action", "audience", "release_id", "node_id",
    "release_root_pin", "authority_anchor_pin", "operator_signer_pin",
    "pending_intent_sha256", "new_policy_epoch", "new_release_sequence",
    "new_policy_sha256", "new_artifact_sha256",
    "authority_policy_floor", "authority_release_floor",
    "issued_at", "expires_at",
})
MAX_APPROVAL = 8192
MAX_SIGNATURE = 8192
MAX_PUBLIC = 65536
MAX_VALIDITY_SECONDS = 600
SUCCESS = "C3EH_TEST_SUPERSESSION_GATE_AUTHORIZED_READ_ONLY"


class Refused(Exception):
    pass


def deny(code):
    raise Refused(code)


def _strict_json(payload: bytes):
    if type(payload) is not bytes or not 0 < len(payload) <= MAX_APPROVAL:
        deny("OPERATOR_APPROVAL_SIZE_REFUSED")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                deny("DUPLICATE_SIGNED_APPROVAL_FIELD")
            result[key] = value
        return result
    try:
        result = json.loads(payload.decode("utf-8"), object_pairs_hook=unique)
    except (ValueError, UnicodeError):
        deny("INVALID_SIGNED_APPROVAL_JSON")
    if type(result) is not dict or set(result) != FIELDS:
        deny("INVALID_SIGNED_APPROVAL_SHAPE")
    return result


def intent_digest(saved: tuple, pending: tuple) -> str:
    """Canonical hash also binds enrolled context to the pending row."""
    if len(saved) != 5 or len(pending) != 10:
        deny("INVALID_PENDING_SHAPE")
    material = json.dumps(
        {"release_id": admission.RELEASE_ID,
         "node_id": saved[0], "root_pin": saved[1],
         "authority_pin": saved[2], "witness_epoch": saved[3],
         "witness_sequence": saved[4], "pending": list(pending)},
        sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(material).hexdigest()



def _open_read_only(path: Path, label: str):
    """SQLite file-descriptor is read-only; no PRAGMA journal_mode mutation."""
    path = Path(path)
    try:
        durable._db_path(path)
        connection = sqlite3.connect(
            "file:" + quote(str(path)) + "?mode=ro",
            uri=True, isolation_level=None, timeout=8)
        connection.execute("PRAGMA query_only=ON")
        return connection
    except (durable.Refused, sqlite3.Error):
        deny(label + "_LEDGER_UNAVAILABLE")


def _read_state(witness_db: Path, client_db: Path):
    w = _open_read_only(witness_db, "WITNESS")
    try:
        w.execute("BEGIN")
        saved = split._witness(w)
        pending = split._intent(w)
        w.execute("ROLLBACK")
    except sqlite3.Error:
        deny("WITNESS_LEDGER_UNAVAILABLE")
    finally:
        w.close()
    c = _open_read_only(client_db, "CLIENT")
    try:
        client = durable._read(c)
    except durable.Refused:
        deny("CLIENT_LEDGER_UNAVAILABLE")
    finally:
        c.close()
    return saved, pending, client


def _verify_operator(*, public: Path, pin: str, payload: Path,
                     signature: Path, directory: Path):
    try:
        ring = admission._isolated_ring(directory, public, "operator")
        listing = admission._cmd([
            "gpg", "--homedir", str(directory), "--batch",
            "--no-default-keyring", "--keyring", str(ring),
            "--with-colons", "--fingerprint", "--list-keys",
        ])
        fps = [x.split(":")[9] for x in listing.stdout.splitlines()
               if x.startswith("fpr:")]
        if listing.returncode != 0 or len(fps) != 1 or fps[0] != pin:
            deny("OPERATOR_PIN_MISMATCH")
        actual = admission._check_detached(ring, signature, payload)
        if actual != pin:
            deny("OPERATOR_SIGNER_MISMATCH")
    except admission.Refused:
        deny("OPERATOR_SIGNATURE_REFUSED")


def inspect_operator_supersession(*, witness_db: Path, client_db: Path,
    operator_public: Path, operator_pin: str,
    operator_signed_approval: Path, operator_signature: Path,
    authority_anchor_public: Path, authority_anchor_pin: str,
    node_id: str, release_root_pin: str, request_proof,
    release_root_public: Path, policy: Path, policy_signature: Path,
    delegated_public: Path, manifest: Path, manifest_signature: Path,
    artifact: Path, allow_supersession_target: bool = False) -> str:
    """Fail-closed PRE-EXECUTION authorization, not a transaction executor.

    All signatures and source bytes are snapshotted before validation.
    A real authority is not present. The operator key pin is a trusted CI
    harness argument, NOT a production trust-store enrollment.
    """
    if Path(witness_db) == Path(client_db):
        deny("WITNESS_CLIENT_LEDGER_NOT_SEPARATE")
    try:
        operator_pin = admission._fingerprint(operator_pin)
        root_pin = admission._fingerprint(release_root_pin)
        authority_pin = admission._fingerprint(authority_anchor_pin)
    except admission.Refused:
        deny("INVALID_TRUST_ANCHOR_PIN")
    if len({operator_pin, root_pin, authority_pin}) != 3:
        deny("OPERATOR_KEY_NOT_INDEPENDENT")
    if type(node_id) is not str or proof.NODE_PATTERN.fullmatch(node_id) is None:
        deny("INVALID_NODE_ID")
    try:
        saved, pending, client = _read_state(witness_db, client_db)
        if pending is None:
            deny("NO_PENDING_INTENT")
        split._identity(saved, node_id, root_pin, authority_pin)
        if saved[3:] != pending[:2]:
            deny("WITNESS_PENDING_BASELINE_CONFLICT")
        if client[0] != root_pin:
            deny("CLIENT_PENDING_STATE_CONFLICT")
        was_legacy_state = client[1:] in (pending[:4], pending[4:8])
        if not was_legacy_state and not allow_supersession_target:
            deny("CLIENT_PENDING_STATE_CONFLICT")
        pending_hash = intent_digest(saved, pending)
    except split.Refused as exc:
        deny("RECOVERY_STATE_REFUSED_" + str(exc))

    # A fresh nonce binds the independently signed authority floor now,
    # rather than trusting the old signed proof in the pending journal.
    try:
        floor = split._signed_floor(
            request_proof=request_proof,
            anchor_public=authority_anchor_public, anchor_pin=authority_pin,
            node_id=node_id, root_pin=root_pin)
    except split.Refused as exc:
        deny("FRESH_AUTHORITY_REFUSED_" + str(exc))
    if floor[0] <= pending[4] or floor[1] <= pending[5]:
        deny("AUTHORITY_NOT_STRICTLY_AHEAD_OF_PENDING")

    with tempfile.TemporaryDirectory(prefix="c3eh-signed-recovery-") as td:
        work = Path(td)
        try:
            durable._stage_one(Path(operator_public), work / "operator.asc",
                               MAX_PUBLIC)
            durable._stage_one(Path(operator_signed_approval),
                               work / "operator.json", MAX_APPROVAL)
            durable._stage_one(Path(operator_signature),
                               work / "operator.sig", MAX_SIGNATURE)
        except durable.Refused:
            deny("UNSAFE_OPERATOR_SIGNATURE_INPUT")
        _verify_operator(
            public=work / "operator.asc", pin=operator_pin,
            payload=work / "operator.json",
            signature=work / "operator.sig", directory=work)
        signed = _strict_json((work / "operator.json").read_bytes())
        release_snapshot = work / "release"
        release_snapshot.mkdir(mode=0o700)
        try:
            files, target = split._candidate(
                release_snapshot, (release_root_public, policy, policy_signature,
                                  delegated_public, manifest,
                                  manifest_signature, artifact),
                root_pin=root_pin, external_epoch=floor[0],
                external_sequence=floor[1])
        except split.Refused as exc:
            deny("NEW_SIGNED_RELEASE_REFUSED_" + str(exc))
        now = int(time.time())
        if (type(signed["issued_at"]) is not int or
                type(signed["expires_at"]) is not int or
                signed["issued_at"] > now or signed["expires_at"] <= now or
                signed["expires_at"] - signed["issued_at"] > MAX_VALIDITY_SECONDS):
            deny("OPERATOR_APPROVAL_EXPIRED_OR_INVALID")
        wanted = {
            "schema": SCHEMA, "action": ACTION, "audience": AUDIENCE,
            "release_id": admission.RELEASE_ID, "node_id": node_id,
            "release_root_pin": root_pin,
            "authority_anchor_pin": authority_pin,
            "operator_signer_pin": operator_pin,
            "pending_intent_sha256": pending_hash,
            "new_policy_epoch": target[0],
            "new_release_sequence": target[1],
            "new_policy_sha256": target[2],
            "new_artifact_sha256": target[3],
            "authority_policy_floor": floor[0],
            "authority_release_floor": floor[1],
        }
        if any(signed.get(k) != value for k, value in wanted.items()):
            deny("SIGNED_APPROVAL_CONTEXT_MISMATCH")
        if target[0] <= pending[4] or target[1] <= pending[5]:
            deny("NEW_RELEASE_MUST_SUPERSEDE_PENDING")
        # A crash after C3e-I's client commit legitimately leaves the client
        # at the *new* root-signed target while both witness intents remain
        # pending. Only explicit recovery may authorize this exact state.
        if not was_legacy_state and client[1:] != target:
            deny("RECOVERY_CLIENT_NOT_AT_SIGNED_TARGET")
        # Detect changed local ledgers while doing expensive GPG checks.
        # Still read-only: a later writer must recheck under a real lock.
        try:
            saved_again, pending_again, client_again = _read_state(
                witness_db, client_db)
        except split.Refused as exc:
            deny("RECOVERY_STATE_CHANGED_" + str(exc))
        if (saved_again != saved or pending_again != pending or
                client_again != client):
            deny("RECOVERY_STATE_CHANGED_DURING_VERIFICATION")
    return SUCCESS
