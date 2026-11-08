#!/usr/bin/env python3
"""C3e-G: disposable crash-recovery protocol for C3e-F split commits.

A witness journal PREPARE is committed *before* C3e-C commits the client
checkpoint. A final witness transaction commits its own floor and deletes the
intent. After process death in the gap, a fresh authority GPG proof plus the
same root-signed release bytes are required to reconcile.

No automatic reset, unsigned repair, partial acceptance or production grants.
This is NOT a distributed atomic commit, hardware-backed history, production
installer, or real remote witness. All keys and SQLite files are CI fixtures.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import secrets
import sqlite3
import tempfile
from typing import Callable

HERE = Path(__file__).parent


def _import(name, relative):
    sp = importlib.util.spec_from_file_location(name, HERE / relative)
    if sp is None or sp.loader is None:
        raise RuntimeError("C3EG_DEPENDENCY_MISSING")
    module = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(module)
    return module


durable = _import("c3eg_durable", "C3eDurableFloor.py")
witness = _import("c3eg_witness", "C3eRollbackWitness.py")
proof = _import("c3eg_proof", "C3eExternalFloorProof.py")
admission = _import("c3eg_release", "C3eReleaseAdmission.py")

JOURNAL_SCHEMA = """CREATE TABLE split_intent (
    id INTEGER PRIMARY KEY CHECK(id=1),
    prior_epoch INTEGER NOT NULL CHECK(prior_epoch>=1),
    prior_sequence INTEGER NOT NULL CHECK(prior_sequence>=1),
    prior_policy_hash TEXT NOT NULL,
    prior_artifact_hash TEXT NOT NULL,
    target_epoch INTEGER NOT NULL CHECK(target_epoch>=1),
    target_sequence INTEGER NOT NULL CHECK(target_sequence>=1),
    target_policy_hash TEXT NOT NULL,
    target_artifact_hash TEXT NOT NULL,
    authority_epoch INTEGER NOT NULL CHECK(authority_epoch>=1),
    authority_sequence INTEGER NOT NULL CHECK(authority_sequence>=1)
)"""
JOURNAL_COLS = (
    "prior_epoch, prior_sequence, prior_policy_hash, prior_artifact_hash, "
    "target_epoch, target_sequence, target_policy_hash, target_artifact_hash, "
    "authority_epoch, authority_sequence"
)
SOURCES = ("root", "policy", "policy_signature", "delegate",
           "manifest", "manifest_signature", "artifact")
LIMITS = (
    durable.FILE_LIMITS["root"], durable.FILE_LIMITS["policy"],
    durable.FILE_LIMITS["policy_sig"], durable.FILE_LIMITS["delegate"],
    durable.FILE_LIMITS["manifest"], durable.FILE_LIMITS["manifest_sig"],
    durable.FILE_LIMITS["artifact"],
)
SUCCESS = "C3EG_SPLIT_COMMIT_RECOVERABLE_TEST_ONLY"


class Refused(Exception):
    pass


def deny(reason):
    raise Refused(reason)


def _db(path):
    try:
        return durable._connect(Path(path))
    except durable.Refused:
        deny("LEDGER_UNAVAILABLE")


def _witness(db):
    try:
        return witness._read(db)
    except witness.Refused:
        deny("WITNESS_CORRUPT_OR_UNAVAILABLE")


def _client(path):
    try:
        return durable.inspect(Path(path))
    except durable.Refused:
        deny("CLIENT_LEDGER_UNAVAILABLE")


def _intent(db):
    try:
        rows = db.execute("SELECT " + JOURNAL_COLS + " FROM split_intent").fetchall()
    except sqlite3.Error:
        deny("JOURNAL_NOT_INITIALIZED_OR_CORRUPT")
    if len(rows) > 1:
        deny("JOURNAL_CORRUPT")
    if not rows:
        return None
    values = rows[0]
    if (len(values) != 10 or
            any(type(v) is not int or v < 1
                for v in (values[0], values[1], values[4], values[5],
                          values[8], values[9])) or
            any(type(v) is not str or
                (v and admission.SHA256.fullmatch(v) is None)
                for v in (values[2], values[3])) or
            any(type(v) is not str or
                admission.SHA256.fullmatch(v) is None
                for v in (values[6], values[7]))):
        deny("JOURNAL_CORRUPT")
    return values


def _identity(saved, node_id, root_pin, anchor_pin):
    if saved[:3] != (node_id, root_pin, anchor_pin):
        deny("WITNESS_IDENTITY_REFUSED")


def _status(witness_db, client_db):
    if Path(witness_db) == Path(client_db):
        deny("WITNESS_CLIENT_LEDGER_NOT_SEPARATE")
    conn = _db(witness_db)
    try:
        saved = _witness(conn)
        pending = _intent(conn)
    finally:
        conn.close()
    return saved, _client(client_db), pending


def initialize_split_journal(*, witness_db: Path, client_db: Path):
    """Explicit CI-only schema initialization; never auto-recover missing state."""
    if Path(witness_db) == Path(client_db):
        deny("WITNESS_CLIENT_LEDGER_NOT_SEPARATE")
    db = _db(witness_db)
    in_transaction = False
    try:
        db.execute("BEGIN IMMEDIATE")
        in_transaction = True
        saved = _witness(db)
        client = _client(client_db)
        if client[0] != saved[1] or client[1:3] != saved[3:]:
            deny("UNTRACKED_SPLIT_BEFORE_JOURNAL_ENROLLMENT")
        existed = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='split_intent'").fetchone()
        if existed:
            deny("JOURNAL_ALREADY_ENROLLED")
        db.execute(JOURNAL_SCHEMA)
        db.execute("COMMIT")
        in_transaction = False
    except sqlite3.Error:
        deny("JOURNAL_BOOTSTRAP_FAILED")
    finally:
        if in_transaction:
            db.execute("ROLLBACK")
        db.close()


def inspect_split(*, witness_db: Path, client_db: Path):
    """Purely read-only diagnostics, never a write or implicit trust bootstrap."""
    saved, client, pending = _status(witness_db, client_db)
    return {
        "witness_floor": saved[3:],
        "client_floor": client[1:3],
        "pending": pending is not None,
        "phase": (
            "clear" if pending is None and client[1:3] == saved[3:]
            else "untracked_split" if pending is None
            else "client_committed" if client[1:] == (
                pending[4], pending[5], pending[6], pending[7])
            else "prepared_only" if client[1:] == pending[:4]
            else "conflict"
        ),
    }


def _signed_floor(*, request_proof, anchor_public, anchor_pin,
                  node_id, root_pin):
    if not callable(request_proof):
        deny("AUTHORITY_PROOF_UNAVAILABLE")
    challenge = secrets.token_hex(32)
    try:
        answer = request_proof(challenge)
    except Exception:
        deny("AUTHORITY_PROOF_UNAVAILABLE")
    if type(answer) is not tuple or len(answer) != 2:
        deny("BAD_AUTHORITY_RESPONSE")
    try:
        return proof._checked_proof(
            anchor_public=Path(anchor_public), anchor_pin=anchor_pin,
            proof=answer[0], signature=answer[1],
            challenge=challenge, node_id=node_id,
            release_root_pin=root_pin)
    except proof.Refused as exc:
        deny("INVALID_AUTHORITY_PROOF_" + str(exc))


def _candidate(folder: Path, sources: tuple[Path, ...],
               *, root_pin: str, external_epoch: int, external_sequence: int):
    files = {}
    for name, src, limit in zip(SOURCES, sources, LIMITS):
        dst = folder / name
        try:
            durable._stage_one(Path(src), dst, limit)
        except durable.Refused as exc:
            deny("UNSAFE_RELEASE_SNAPSHOT_" + str(exc))
        files[name] = dst
    try:
        verified = admission.verify(
            files["root"], root_pin, files["policy"],
            files["policy_signature"], files["delegate"],
            files["manifest"], files["manifest_signature"],
            files["artifact"], external_epoch, external_sequence)
        if verified != "C3E_TEST_POLICY_ACCEPTED_NO_PRODUCTION_AUTH":
            deny("SIGNED_RELEASE_UNEXPECTED")
        policy_obj = admission._unique_json(files["policy"])
        manifest_obj = admission._unique_json(files["manifest"])
    except admission.Refused as exc:
        deny("SIGNED_RELEASE_REFUSED_" + str(exc))
    target = (
        policy_obj["epoch"], manifest_obj["sequence"],
        hashlib.sha256(files["policy"].read_bytes()).hexdigest(),
        hashlib.sha256(files["artifact"].read_bytes()).hexdigest())
    return files, target


def _apply_client(*, db_path, root_pin, authority_floor, files, target):
    try:
        result = durable.admit_and_record(
            Path(db_path),
            external_root_pin=root_pin,
            external_epoch_floor=authority_floor[0],
            external_sequence_floor=authority_floor[1],
            root_public=files["root"], policy=files["policy"],
            policy_signature=files["policy_signature"],
            delegated_public=files["delegate"],
            manifest=files["manifest"],
            manifest_signature=files["manifest_signature"],
            artifact=files["artifact"])
    except durable.Refused as exc:
        deny("CLIENT_RELEASE_REFUSED_" + str(exc))
    if result != durable.SUCCESS or _client(db_path)[1:] != target:
        deny("CLIENT_NOT_AT_SIGNED_TARGET")


def _pending_rows(before_client, target, authority_floor):
    return (*before_client[1:], *target, *authority_floor)


def _phase(hook: Callable[[str], None] | None, name):
    if hook is not None:
        hook(name)


def _finish(*, witness_db, client_db, node_id, root_pin, anchor_pin,
            expected_pending):
    db = _db(witness_db)
    active = False
    try:
        db.execute("BEGIN IMMEDIATE")
        active = True
        saved = _witness(db)
        _identity(saved, node_id, root_pin, anchor_pin)
        pending = _intent(db)
        if pending != expected_pending:
            deny("PENDING_INTENT_CHANGED")
        if saved[3] > pending[4] or saved[4] > pending[5]:
            deny("WITNESS_ADVANCED_DURING_PENDING_INTENT")
        if _client(client_db)[1:] != pending[4:8]:
            deny("CLIENT_CHECKPOINT_NOT_AT_VERIFIED_TARGET")
        db.execute(
            """UPDATE witness SET minimum_policy_epoch=?,
               minimum_release_sequence=? WHERE id=1""",
            (pending[4], pending[5]))
        db.execute("DELETE FROM split_intent WHERE id=1")
        db.execute("COMMIT")
        active = False
    except sqlite3.Error:
        deny("WITNESS_FINAL_COMMIT_FAILED")
    finally:
        if active:
            db.execute("ROLLBACK")
        db.close()


def submit(*, witness_db: Path, client_db: Path,
           authority_anchor_public: Path, authority_anchor_pin: str,
           node_id: str, release_root_pin: str,
           request_proof: Callable[[str], tuple[bytes, bytes]],
           release_root_public: Path, policy: Path,
           policy_signature: Path, delegated_public: Path,
           manifest: Path, manifest_signature: Path, artifact: Path,
           recovery: bool = False,
           test_checkpoint_hook: Callable[[str], None] | None = None) -> str:
    """Prepare, commit client, then finalize witness. Recover only on replay
    of the exact signed candidate and a NEW authenticated authority challenge.
    """
    witness_db, client_db = Path(witness_db), Path(client_db)
    if witness_db == client_db:
        deny("WITNESS_CLIENT_LEDGER_NOT_SEPARATE")
    authority_floor = _signed_floor(
        request_proof=request_proof, anchor_public=authority_anchor_public,
        anchor_pin=authority_anchor_pin, node_id=node_id,
        root_pin=release_root_pin)
    with tempfile.TemporaryDirectory(prefix="c3eg-signed-snapshot-") as tmp:
        files, target = _candidate(
            Path(tmp), (release_root_public, policy, policy_signature,
                        delegated_public, manifest, manifest_signature, artifact),
            root_pin=release_root_pin,
            external_epoch=authority_floor[0],
            external_sequence=authority_floor[1])
        db = _db(witness_db)
        transaction = False
        try:
            db.execute("BEGIN IMMEDIATE")
            transaction = True
            saved = _witness(db)
            _identity(saved, node_id, release_root_pin, authority_anchor_pin)
            pending = _intent(db)
            client = _client(client_db)
            if not recovery:
                if pending is not None:
                    deny("PENDING_INTENT_REQUIRES_EXPLICIT_RECOVERY")
                if client[0] != release_root_pin or client[1:3] != saved[3:]:
                    deny("UNTRACKED_CLIENT_WITNESS_SPLIT")
                if target[0] < saved[3] or target[1] < saved[4]:
                    deny("WITNESS_ROLLBACK_REFUSED")
                rows = _pending_rows(client, target, authority_floor)
                db.execute(
                    """INSERT INTO split_intent(
                        prior_epoch, prior_sequence, prior_policy_hash,
                        prior_artifact_hash, target_epoch, target_sequence,
                        target_policy_hash, target_artifact_hash,
                        authority_epoch, authority_sequence)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", rows)
            else:
                if pending is None:
                    deny("NO_PENDING_INTENT_FOR_RECOVERY")
                rows = pending
                if target != pending[4:8]:
                    deny("RECOVERY_SIGNED_RELEASE_NOT_PENDING_TARGET")
                if authority_floor != pending[8:10]:
                    deny("RECOVERY_AUTHORITY_FLOOR_CHANGED")
                if saved[3] > target[0] or saved[4] > target[1]:
                    deny("WITNESS_STATE_OUTRAN_PENDING_INTENT")
                if client[0] != release_root_pin:
                    deny("CLIENT_ROOT_PIN_MISMATCH")
                if client[1:] not in (pending[:4], target):
                    deny("CONFLICTING_CLIENT_CHECKPOINT")
            db.execute("COMMIT")
            transaction = False
        except sqlite3.Error:
            deny("INTENT_WRITE_FAILED")
        finally:
            if transaction:
                db.execute("ROLLBACK")
            db.close()

        if not recovery:
            _phase(test_checkpoint_hook, "intent-committed")
        current = _client(client_db)[1:]
        if current == rows[:4]:
            _apply_client(db_path=client_db, root_pin=release_root_pin,
                          authority_floor=authority_floor,
                          files=files, target=target)
        elif current != target:
            deny("CONFLICTING_CLIENT_CHECKPOINT")
        _phase(test_checkpoint_hook, "client-committed")
        _finish(witness_db=witness_db, client_db=client_db, node_id=node_id,
                root_pin=release_root_pin, anchor_pin=authority_anchor_pin,
                expected_pending=rows)
        _phase(test_checkpoint_hook, "witness-committed")
    return SUCCESS
