#!/usr/bin/env python3
"""C3e-I: crash-recoverable, CI-only operator-supervised supersession.

Extends C3e-G's *synthetic* signed-intent journal. A DIFFERENT, bounded
supersession row is durably prepared after C3e-H's operator GPG approval,
new release signature validation, and a fresh authority proof. The client
may then commit the new release; one final local witness transaction advances
the witnessed floor and deletes BOTH intents. A killed process may resume
ONLY with the same root-signed new release, same still-valid operator approval,
and a new challenge-bound authority statement.

Not a distributed transaction, hardware root, protected signing key, actual
operator approval, real Silverblue installer, production recovery, or grant.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sqlite3
import tempfile
from typing import Callable

HERE = Path(__file__).parent


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3EI_SOURCE_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


split = _load("c3ei_split", "C3eSplitCommitRecovery.py")
gate = _load("c3ei_operator", "C3eOperatorRecoveryGate.py")
durable = _load("c3ei_durable", "C3eDurableFloor.py")

# This table is explicitly initialized. Existing C3e-G split_intent rows
# remain intact until the final witness transaction commits the new floor.
JOURNAL_SQL = """CREATE TABLE supersession_intent (
    id INTEGER PRIMARY KEY CHECK(id=1),
    pending_sha256 TEXT NOT NULL,
    operator_approval_sha256 TEXT NOT NULL,
    prior_epoch INTEGER NOT NULL CHECK(prior_epoch>=1),
    prior_sequence INTEGER NOT NULL CHECK(prior_sequence>=1),
    prior_policy_sha256 TEXT NOT NULL,
    prior_artifact_sha256 TEXT NOT NULL,
    target_epoch INTEGER NOT NULL CHECK(target_epoch>=1),
    target_sequence INTEGER NOT NULL CHECK(target_sequence>=1),
    target_policy_sha256 TEXT NOT NULL,
    target_artifact_sha256 TEXT NOT NULL,
    authority_epoch INTEGER NOT NULL CHECK(authority_epoch>=1),
    authority_sequence INTEGER NOT NULL CHECK(authority_sequence>=1)
)"""
COLS = (
    "pending_sha256, operator_approval_sha256, "
    "prior_epoch, prior_sequence, prior_policy_sha256, "
    "prior_artifact_sha256, target_epoch, target_sequence, "
    "target_policy_sha256, target_artifact_sha256, "
    "authority_epoch, authority_sequence"
)
SUCCESS = "C3EI_TEST_SIGNED_SUPERSESSION_COMMITTED_NO_PRODUCTION_AUTH"


class Refused(Exception):
    pass


def deny(code):
    raise Refused(code)


def _connect(path):
    try:
        return durable._connect(Path(path))
    except durable.Refused:
        deny("WITNESS_LEDGER_UNAVAILABLE")


def _row(db):
    try:
        values = db.execute("SELECT " + COLS + " FROM supersession_intent").fetchall()
    except sqlite3.Error:
        deny("SUPERSESSION_JOURNAL_UNAVAILABLE")
    if len(values) > 1:
        deny("SUPERSESSION_JOURNAL_CORRUPT")
    if not values:
        return None
    v = values[0]
    if (len(v) != 12 or any(type(x) is not str or
            durable.admission.SHA256.fullmatch(x) is None
            for x in (v[0], v[1], v[6], v[7])) or
            any(type(x) is not int or x < 1
                for x in (v[2], v[3], v[6], v[7], v[10], v[11])) or
            any(type(x) is not str or (x and
                durable.admission.SHA256.fullmatch(x) is None)
                for x in (v[4], v[5]))):
        deny("SUPERSESSION_JOURNAL_CORRUPT")
    return tuple(v)


def initialize(*, witness_db: Path, client_db: Path):
    """Explicit one-time schema enrollment, with a known compatible C3e-G."""
    if Path(witness_db) == Path(client_db):
        deny("WITNESS_CLIENT_LEDGER_NOT_SEPARATE")
    db = _connect(witness_db)
    begun = False
    try:
        db.execute("BEGIN IMMEDIATE")
        begun = True
        split._witness(db)
        split._intent(db)    # Requires existing C3e-G schema.
        split._client(client_db)
        exists = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='supersession_intent'").fetchone()
        if exists:
            deny("SUPERSESSION_JOURNAL_ALREADY_INITIALIZED")
        db.execute(JOURNAL_SQL)
        db.execute("COMMIT")
        begun = False
    except sqlite3.Error:
        deny("SUPERSESSION_JOURNAL_INITIALIZATION_FAILED")
    finally:
        if begun:
            db.execute("ROLLBACK")
        db.close()


def inspect(*, witness_db: Path, client_db: Path):
    """Diagnostic only; do not mistake it for a recovery authorization."""
    db = _connect(witness_db)
    try:
        witness = split._witness(db)
        old = split._intent(db)
        pending = _row(db)
    finally:
        db.close()
    client = split._client(client_db)
    if pending is None:
        phase = "clear" if old is None and client[1:3] == witness[3:] else "untracked"
    elif client[1:] == pending[6:10]:
        phase = "client_committed"
    elif client[1:] == pending[2:6]:
        phase = "prepared_only"
    else:
        phase = "conflict"
    return {
        "phase": phase,
        "supersession_pending": pending is not None,
        "legacy_intent_pending": old is not None,
        "client_floor": client[1:3],
        "witness_floor": witness[3:],
    }


def _snapshot(work: Path, sources):
    staged = {}
    sizes = {
        "operator_public": gate.MAX_PUBLIC,
        "operator_signed_approval": gate.MAX_APPROVAL,
        "operator_signature": gate.MAX_SIGNATURE,
        "release_root_public": durable.FILE_LIMITS["root"],
        "policy": durable.FILE_LIMITS["policy"],
        "policy_signature": durable.FILE_LIMITS["policy_sig"],
        "delegated_public": durable.FILE_LIMITS["delegate"],
        "manifest": durable.FILE_LIMITS["manifest"],
        "manifest_signature": durable.FILE_LIMITS["manifest_sig"],
        "artifact": durable.FILE_LIMITS["artifact"],
        "authority_anchor_public": gate.proof.MAX_ANCHOR_KEY_BYTES,
    }
    for name, src in sources.items():
        try:
            dest = work / name
            durable._stage_one(Path(src), dest, sizes[name])
            staged[name] = dest
        except (durable.Refused, OSError):
            deny("UNSAFE_SUPERSESSION_INPUT_" + name)
    return staged


def _original_hash(saved, pending):
    return gate.intent_digest(saved, pending)


def _operator_hash(staged):
    return hashlib.sha256(
        staged["operator_signed_approval"].read_bytes()).hexdigest()


def _prepare_tuple(pending_hash, op_hash, prior, target, authority):
    return (
        pending_hash, op_hash, *prior, *target, *authority
    )


def _read_and_assert(db, *, node_id, root_pin, anchor_pin, expected_old):
    saved = split._witness(db)
    split._identity(saved, node_id, root_pin, anchor_pin)
    old = split._intent(db)
    if old is None:
        deny("LEGACY_PENDING_INTENT_MISSING")
    if saved[3:] != old[:2]:
        deny("WITNESS_PENDING_BASELINE_CONFLICT")
    if _original_hash(saved, old) != expected_old:
        deny("ORIGINAL_PENDING_INTENT_CHANGED")
    return old


def _finish(*, witness_db, client_db, node_id, root_pin, anchor_pin, expected):
    db = _connect(witness_db)
    locked = False
    try:
        db.execute("BEGIN IMMEDIATE")
        locked = True
        old = _read_and_assert(
            db, node_id=node_id, root_pin=root_pin, anchor_pin=anchor_pin,
            expected_old=expected[0])
        found = _row(db)
        if found != expected:
            deny("SUPERSESSION_INTENT_CHANGED")
        if split._client(client_db)[1:] != expected[6:10]:
            deny("CLIENT_NOT_AT_NEW_SIGNED_RELEASE")
        # A local SQLite atomic commit updates the witness and deletes the
        # two intent rows. The *client* commit occurred separately.
        db.execute(
            "UPDATE witness SET minimum_policy_epoch=?, "
            "minimum_release_sequence=? WHERE id=1",
            expected[6:8])
        db.execute("DELETE FROM split_intent WHERE id=1")
        db.execute("DELETE FROM supersession_intent WHERE id=1")
        db.execute("COMMIT")
        locked = False
    except sqlite3.Error:
        deny("WITNESS_SUPERSESSION_COMMIT_FAILED")
    finally:
        if locked:
            db.execute("ROLLBACK")
        db.close()


def execute(*, witness_db: Path, client_db: Path,
    operator_public: Path, operator_pin: str,
    operator_signed_approval: Path, operator_signature: Path,
    authority_anchor_public: Path, authority_anchor_pin: str,
    node_id: str, release_root_pin: str, request_proof,
    release_root_public: Path, policy: Path, policy_signature: Path,
    delegated_public: Path, manifest: Path, manifest_signature: Path,
    artifact: Path, recovery: bool = False,
    test_checkpoint_hook: Callable[[str], None] | None = None):
    """Synthetic executor: every resume repeats C3e-H's signed preflight."""
    witness_db, client_db = Path(witness_db), Path(client_db)
    if witness_db == client_db:
        deny("WITNESS_CLIENT_LEDGER_NOT_SEPARATE")
    sources = {
        "operator_public": operator_public,
        "operator_signed_approval": operator_signed_approval,
        "operator_signature": operator_signature,
        "authority_anchor_public": authority_anchor_public,
        "release_root_public": release_root_public,
        "policy": policy, "policy_signature": policy_signature,
        "delegated_public": delegated_public,
        "manifest": manifest, "manifest_signature": manifest_signature,
        "artifact": artifact,
    }
    with tempfile.TemporaryDirectory(prefix="c3ei-supervised-") as td:
        staged = _snapshot(Path(td), sources)
        # The same bounded snapshots are passed to C3e-H AND later C3e-C.
        # No changes to raw candidate pathnames after verification.
        try:
            outcome = gate.inspect_operator_supersession(
                witness_db=witness_db, client_db=client_db,
                operator_public=staged["operator_public"],
                operator_pin=operator_pin,
                operator_signed_approval=staged["operator_signed_approval"],
                operator_signature=staged["operator_signature"],
                authority_anchor_public=staged["authority_anchor_public"],
                authority_anchor_pin=authority_anchor_pin,
                node_id=node_id, release_root_pin=release_root_pin,
                request_proof=request_proof,
                release_root_public=staged["release_root_public"],
                policy=staged["policy"],
                policy_signature=staged["policy_signature"],
                delegated_public=staged["delegated_public"],
                manifest=staged["manifest"],
                manifest_signature=staged["manifest_signature"],
                artifact=staged["artifact"],
            )
        except gate.Refused as exc:
            deny("OPERATOR_PREFLIGHT_REFUSED_" + str(exc))
        if outcome != gate.SUCCESS:
            deny("OPERATOR_PREFLIGHT_UNEXPECTED")
        approval_hash = _operator_hash(staged)
        op_doc = gate._strict_json(
            staged["operator_signed_approval"].read_bytes())
        target = (
            op_doc["new_policy_epoch"],
            op_doc["new_release_sequence"],
            op_doc["new_policy_sha256"],
            op_doc["new_artifact_sha256"],
        )
        authority = (
            op_doc["authority_policy_floor"],
            op_doc["authority_release_floor"],
        )
        db = _connect(witness_db)
        locked = False
        try:
            db.execute("BEGIN IMMEDIATE")
            locked = True
            saved = split._witness(db)
            old = split._intent(db)
            if old is None:
                deny("LEGACY_PENDING_INTENT_MISSING")
            split._identity(saved, node_id, release_root_pin, authority_anchor_pin)
            if saved[3:] != old[:2]:
                deny("WITNESS_PENDING_BASELINE_CONFLICT")
            if _original_hash(saved, old) != op_doc["pending_intent_sha256"]:
                deny("ORIGINAL_PENDING_INTENT_CHANGED")
            current = split._client(client_db)
            if current[0] != release_root_pin:
                deny("CLIENT_RELEASE_ROOT_CHANGED")
            pending = _row(db)
            if recovery:
                if pending is None:
                    deny("NO_PREPARED_SUPERSESSION")
                expected = pending
                if (pending[:2] != (
                        op_doc["pending_intent_sha256"], approval_hash) or
                        pending[6:10] != target or pending[10:12] != authority):
                    deny("RECOVERY_APPROVAL_OR_TARGET_MISMATCH")
                if current[1:] not in (pending[2:6], pending[6:10]):
                    deny("RECOVERY_CLIENT_CONFLICT")
            else:
                if pending is not None:
                    deny("SUPERSESSION_PENDING_REQUIRES_EXPLICIT_RECOVERY")
                if current[1:] not in (old[:4], old[4:8]):
                    deny("UNTRACKED_CLIENT_CHECKPOINT_CONFLICT")
                if (target[0] <= old[4] or target[1] <= old[5] or
                        target[0] < saved[3] or target[1] < saved[4]):
                    deny("NEW_SIGNED_RELEASE_NOT_HIGHER")
                expected = _prepare_tuple(
                    op_doc["pending_intent_sha256"], approval_hash,
                    current[1:], target, authority)
                db.execute(
                    """INSERT INTO supersession_intent (
                       pending_sha256, operator_approval_sha256,
                       prior_epoch, prior_sequence, prior_policy_sha256,
                       prior_artifact_sha256, target_epoch, target_sequence,
                       target_policy_sha256, target_artifact_sha256,
                       authority_epoch, authority_sequence)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", expected)
            db.execute("COMMIT")
            locked = False
        except sqlite3.Error:
            deny("SUPERSESSION_PREPARE_FAILED")
        finally:
            if locked:
                db.execute("ROLLBACK")
            db.close()

        if not recovery and test_checkpoint_hook:
            test_checkpoint_hook("supersession-prepared")
        current = split._client(client_db)[1:]
        if current == expected[2:6]:
            try:
                result = durable.admit_and_record(
                    client_db,
                    external_root_pin=release_root_pin,
                    external_epoch_floor=authority[0],
                    external_sequence_floor=authority[1],
                    root_public=staged["release_root_public"],
                    policy=staged["policy"],
                    policy_signature=staged["policy_signature"],
                    delegated_public=staged["delegated_public"],
                    manifest=staged["manifest"],
                    manifest_signature=staged["manifest_signature"],
                    artifact=staged["artifact"],
                )
            except durable.Refused as exc:
                deny("CLIENT_NEW_RELEASE_REFUSED_" + str(exc))
            if result != durable.SUCCESS:
                deny("CLIENT_NEW_RELEASE_UNEXPECTED")
        elif current != target:
            deny("CLIENT_CHECKPOINT_DIVERGED")
        if split._client(client_db)[1:] != target:
            deny("CLIENT_CHECKPOINT_NOT_AT_NEW_TARGET")
        if test_checkpoint_hook:
            test_checkpoint_hook("supersession-client-committed")
        _finish(
            witness_db=witness_db, client_db=client_db,
            node_id=node_id, root_pin=release_root_pin,
            anchor_pin=authority_anchor_pin, expected=expected,
        )
        if test_checkpoint_hook:
            test_checkpoint_hook("supersession-witness-committed")
    return SUCCESS
