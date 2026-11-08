#!/usr/bin/env python3
"""C3e-F: offline synthetic independent release-history witness (CI ONLY).

A witness owned by a *separate logical principal* remembers the highest
authenticated release floors it has observed. It rejects a freshly signed but
STALE proof after an authority's SQLite database has been restored. This
fixture does not protect the witness's own DB/keys from privileged rollback:
no real separate host, TPM/HSM, remote ledger or production trust is present.

The verifier creates a fresh challenge; the witness checks the existing
C3e-D detached OpenPGP signature and binds its stored pins/node, then invokes
unchanged C3e-C signed-release admission before committing witness floors.
No real credential grants, RPM installation, network or service activation.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import secrets
import sqlite3
from typing import Callable

HERE = Path(__file__).parent


def _load(name, source):
    spec = importlib.util.spec_from_file_location(name, HERE / source)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3EF_DEPENDENCY_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


durable = _load("c3ef_durable", "C3eDurableFloor.py")
proof = _load("c3ef_signed_proof", "C3eExternalFloorProof.py")
admission = _load("c3ef_admission", "C3eReleaseAdmission.py")

SCHEMA = """CREATE TABLE witness (
    id INTEGER PRIMARY KEY CHECK(id=1),
    release_id TEXT NOT NULL CHECK(release_id='postapollo-connections-status'),
    node_id TEXT NOT NULL,
    release_root_pin TEXT NOT NULL,
    authority_anchor_pin TEXT NOT NULL,
    minimum_policy_epoch INTEGER NOT NULL CHECK(minimum_policy_epoch>=1),
    minimum_release_sequence INTEGER NOT NULL CHECK(minimum_release_sequence>=1)
)"""
SUCCESS = "C3EF_TEST_INDEPENDENT_WITNESS_ACCEPTED_NO_PRODUCTION_AUTH"


class Refused(Exception):
    pass


def deny(code):
    raise Refused(code)


def _pins(anchor_pin, release_root_pin, node_id, epoch, sequence):
    try:
        admission._fingerprint(anchor_pin)
        durable._anchor(release_root_pin, epoch, sequence)
    except (admission.Refused, durable.Refused):
        deny("INVALID_WITNESS_ENROLLMENT")
    if (anchor_pin == release_root_pin or
            type(node_id) is not str or
            proof.NODE_PATTERN.fullmatch(node_id) is None):
        deny("INVALID_WITNESS_ENROLLMENT")


def bootstrap_witness(path: Path, *, authority_anchor_pin: str,
                      release_root_pin: str, node_id: str,
                      initial_policy_epoch: int, initial_release_sequence: int):
    """Explicit synthetic enrollment only; NEVER recover a missing DB silently."""
    path = Path(path)
    _pins(authority_anchor_pin, release_root_pin, node_id,
          initial_policy_epoch, initial_release_sequence)
    if not path.is_absolute() or path.exists() or path.is_symlink():
        deny("WITNESS_EXISTS_OR_UNSAFE_PATH")
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600)
        os.close(fd)
    except OSError:
        deny("WITNESS_BOOTSTRAP_FAILED")
    connection = None
    try:
        connection = durable._connect(path)
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(SCHEMA)
        connection.execute(
            """INSERT INTO witness(id, release_id, node_id,
                 release_root_pin, authority_anchor_pin,
                 minimum_policy_epoch, minimum_release_sequence)
                 VALUES (1, ?, ?, ?, ?, ?, ?)""",
            (admission.RELEASE_ID, node_id, release_root_pin,
             authority_anchor_pin, initial_policy_epoch,
             initial_release_sequence))
        connection.execute("COMMIT")
    except (sqlite3.Error, durable.Refused):
        if connection and connection.in_transaction:
            connection.execute("ROLLBACK")
        deny("WITNESS_BOOTSTRAP_FAILED")
    finally:
        if connection:
            connection.close()


def _read(db):
    try:
        rows = db.execute(
            """SELECT release_id, node_id, release_root_pin,
                      authority_anchor_pin, minimum_policy_epoch,
                      minimum_release_sequence FROM witness""").fetchall()
    except sqlite3.Error:
        deny("WITNESS_STATE_CORRUPT_OR_MISSING")
    if len(rows) != 1:
        deny("WITNESS_STATE_CORRUPT_OR_MISSING")
    release_id, node_id, root, anchor, epoch, seq = rows[0]
    _pins(anchor, root, node_id, epoch, seq)
    if release_id != admission.RELEASE_ID:
        deny("WITNESS_STATE_CORRUPT_OR_MISSING")
    return node_id, root, anchor, epoch, seq


def inspect_witness(path: Path):
    try:
        connection = durable._connect(Path(path))
    except durable.Refused:
        deny("WITNESS_STATE_UNAVAILABLE")
    try:
        return _read(connection)
    finally:
        connection.close()


def admit_with_witness(*, witness_db: Path, client_db: Path,
                       authority_anchor_public: Path, authority_anchor_pin: str,
                       node_id: str, release_root_pin: str,
                       request_proof: Callable[[str], tuple[bytes, bytes]],
                       release_root_public: Path, policy: Path,
                       policy_signature: Path, delegated_public: Path,
                       manifest: Path, manifest_signature: Path,
                       artifact: Path) -> str:
    """Reject the authority's rolled-back floor before admitting a release.

    Root and signer pins must match the explicit, separately enrolled witness
    state. Holding a witness write lock across CLIENT admission ensures two
    concurrent verifiers cannot lower the witness's highest seen floors.
    Witness DB and client DB are separate; this is not a distributed atomic
    commit, and no actual external authority/witness isolation is provided.
    """
    witness_db, client_db = Path(witness_db), Path(client_db)
    if witness_db == client_db:
        deny("WITNESS_AND_CLIENT_STATE_NOT_SEPARATE")
    if not callable(request_proof):
        deny("AUTHORITY_CALLBACK_UNAVAILABLE")
    challenge = secrets.token_hex(32)
    try:
        response = request_proof(challenge)
    except Exception:
        deny("AUTHORITY_CALLBACK_UNAVAILABLE")
    if type(response) is not tuple or len(response) != 2:
        deny("MALFORMED_AUTHORITY_RESPONSE")
    try:
        epoch, sequence = proof._checked_proof(
            anchor_public=Path(authority_anchor_public),
            anchor_pin=authority_anchor_pin,
            proof=response[0], signature=response[1],
            challenge=challenge, node_id=node_id,
            release_root_pin=release_root_pin)
    except proof.Refused as exc:
        deny("AUTHORITY_SIGNATURE_REFUSED_" + str(exc))
    try:
        connection = durable._connect(witness_db)
    except durable.Refused:
        deny("WITNESS_STATE_UNAVAILABLE")
    try:
        connection.execute("BEGIN IMMEDIATE")
        saved_node, root, anchor, min_epoch, min_seq = _read(connection)
        if (saved_node != node_id or root != release_root_pin or
                anchor != authority_anchor_pin):
            deny("WITNESS_ENROLLED_IDENTITY_MISMATCH")
        if epoch < min_epoch:
            deny("WITNESS_POLICY_ROLLBACK_REFUSED")
        if sequence < min_seq:
            deny("WITNESS_RELEASE_ROLLBACK_REFUSED")
        try:
            result = durable.admit_and_record(
                client_db,
                external_root_pin=release_root_pin,
                external_epoch_floor=epoch,
                external_sequence_floor=sequence,
                root_public=Path(release_root_public),
                policy=Path(policy),
                policy_signature=Path(policy_signature),
                delegated_public=Path(delegated_public),
                manifest=Path(manifest),
                manifest_signature=Path(manifest_signature),
                artifact=Path(artifact))
        except durable.Refused as exc:
            deny("CLIENT_RELEASE_REFUSED_" + str(exc))
        if result != durable.SUCCESS:
            deny("CLIENT_UNEXPECTED_ADMISSION_RESULT")
        connection.execute(
            """UPDATE witness SET minimum_policy_epoch=?,
                  minimum_release_sequence=? WHERE id=1""",
            (max(min_epoch, epoch), max(min_seq, sequence)))
        connection.execute("COMMIT")
    except (sqlite3.Error, Refused):
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()
    return SUCCESS
