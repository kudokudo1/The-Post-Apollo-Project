#!/usr/bin/env python3
"""DOC 1 development-only SQLite history: NEVER an independent trust authority.

Combines unchanged #2192 signed-history verification with one atomic, local
challenge spend + history-head advance. Reuses C3e-R's disposable GitHub
root-only test directory guard. A whole-DB restore can still replay an old
challenge. Do not import into production services or treat this as enrollment.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import re
import sqlite3

HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3E_LOCAL_DEPENDENCY_MISSING")
    import sys
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


R = _load("c3e_local_existing_root_guard", HERE / "C3eRDurableChallengeLedger.py")
H = _load("c3e_local_existing_history_verifier",
          HERE / "C3eOperatorWitnessHistoryContinuity.py")

SCHEMA = "postapollo.connections.c3e-local-history-development-only.v1"
STATUS = "C3E_LOCAL_HISTORY_DEVELOPMENT_ONLY_ROLLBACKABLE"
DB = "local-development-history.sqlite"
HEX = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
MAX_TIME = 2**63 - 1
DENIED = {
    "operatorEnrollmentRootCustodyVerified": False,
    "independentlyPersistedPreviousHeadVerified": False,
    "externallyRecordedNextHeadVerified": False,
    "externallyConsumedOneUseChallengeVerified": False,
    "externalRollbackResistanceVerified": False,
    "realInstalledHostAuthenticated": False,
    "authenticatedActiveSeatVerified": False,
    "c5HumanConsentVerified": False,
    "hostAuthenticated": False,
    "canBeginSignIn": False,
    "credentialActionsEnabled": False,
    "productionAuthority": False,
}
DDL = """
CREATE TABLE meta (
    id INTEGER PRIMARY KEY CHECK(id=1),
    schema TEXT NOT NULL,
    epoch TEXT NOT NULL,
    head TEXT NOT NULL CHECK(length(head)=64),
    seq INTEGER NOT NULL CHECK(seq>=1)
);
CREATE TABLE challenges (
    nonce_hash TEXT PRIMARY KEY CHECK(length(nonce_hash)=64),
    purpose TEXT NOT NULL,
    host TEXT NOT NULL,
    release_epoch INTEGER NOT NULL,
    release_seq INTEGER NOT NULL,
    previous_head TEXT NOT NULL,
    previous_seq INTEGER NOT NULL,
    deadline INTEGER NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('issued','consumed')),
    next_head TEXT
);
CREATE TABLE history (
    seq INTEGER PRIMARY KEY,
    previous_head TEXT NOT NULL,
    next_head TEXT NOT NULL UNIQUE,
    nonce_hash TEXT NOT NULL UNIQUE,
    record_hash TEXT NOT NULL,
    FOREIGN KEY(nonce_hash) REFERENCES challenges(nonce_hash)
);
"""
PURPOSE = "c3e-identity-local-development-only"


class Refused(ValueError):
    pass


class UnknownAfterCommit(RuntimeError):
    """Lost ACK; query outcome, do not automatically retry."""


def deny(reason: str):
    raise Refused(reason)


def digest(blob: bytes):
    return hashlib.sha256(blob).hexdigest()


def connect(root: Path):
    root = R.validate_root(root)  # /run/c3er-ci-* root-only GitHub fixture
    path = root / DB
    R.check_file(path)  # existing mode, owner, nlink and regular-file guard
    if (root / (DB + "-wal")).exists() or (root / (DB + "-shm")).exists():
        deny("LOCAL_UNEXPECTED_WAL")
    try:
        db = sqlite3.connect(path.as_uri() + "?mode=rw", uri=True,
                             isolation_level=None, timeout=8)
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA foreign_keys=ON")
        row = db.execute("SELECT schema,head,seq FROM meta WHERE id=1").fetchone()
        if (row is None or row[0] != SCHEMA or type(row[1]) is not str
                or HEX.fullmatch(row[1]) is None or type(row[2]) is not int
                or row[2] < 1 or
                db.execute("PRAGMA quick_check").fetchone() != ("ok",)):
            db.close()
            deny("LOCAL_SCHEMA_OR_INTEGRITY_REFUSED")
        return db
    except sqlite3.DatabaseError as exc:
        raise Refused("LOCAL_DATABASE_UNAVAILABLE") from exc


def initialize_ci_only(root: Path):
    """Explicit fixture bootstrap: never called automatically from reads."""
    root = R.validate_root(root)
    path = root / DB
    if os.path.lexists(path):
        deny("LOCAL_LEDGER_EXISTS_NO_REINIT")
    previous_umask = os.umask(0o077)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR |
                     os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        os.close(fd)
        db = sqlite3.connect(path, isolation_level=None)
        try:
            db.execute("PRAGMA journal_mode=DELETE")
            db.execute("PRAGMA synchronous=FULL")
            db.executescript(DDL)
            epoch = os.urandom(16).hex()
            head = digest(b"UNTRUSTED_C3E_LOCAL_GENESIS\x00" + bytes.fromhex(epoch))
            db.execute("INSERT INTO meta VALUES(1,?,?,?,1)",
                       (SCHEMA, epoch, head))
        finally:
            db.close()
    except (OSError, sqlite3.DatabaseError) as exc:
        raise Refused("LOCAL_FIXTURE_INITIALIZE_REFUSED") from exc
    finally:
        os.umask(previous_umask)
    check = connect(root)
    check.close()


class DevelopmentLedger:
    """All methods remain nonauthoritative, even after a successful commit."""

    def __init__(self, root: Path):
        self.root = R.validate_root(root)
        connection = connect(self.root)
        connection.close()

    def snapshot(self):
        db = connect(self.root)
        try:
            epoch, head, seq = db.execute(
                "SELECT epoch,head,seq FROM meta WHERE id=1").fetchone()
        finally:
            db.close()
        return {"schema": SCHEMA, "status": STATUS,
                "testEpoch": epoch, "previousHeadSha256": head,
                "previousSequence": seq, **DENIED}

    def issue(self, *, host: str, release_epoch: int, release_seq: int,
              now_ms: int, ttl_ms: int):
        if (type(host) is not str or not 0 < len(host) <= 128
                or any(ord(c) < 33 or ord(c) > 126 for c in host)
                or type(release_epoch) is not int or release_epoch < 1
                or type(release_seq) is not int or release_seq < 1
                or type(now_ms) is not int or not 0 <= now_ms < MAX_TIME
                or type(ttl_ms) is not int or not 0 < ttl_ms <= 60000
                or now_ms + ttl_ms >= MAX_TIME):
            deny("LOCAL_ISSUANCE_FIELDS_INVALID")
        challenge = os.urandom(32)
        db = connect(self.root)
        try:
            db.execute("BEGIN IMMEDIATE")
            head, seq = db.execute("SELECT head,seq FROM meta WHERE id=1").fetchone()
            db.execute("INSERT INTO challenges VALUES(?,?,?,?,?,?,?,?,'issued',NULL)",
                       (digest(challenge), PURPOSE, host, release_epoch,
                        release_seq, head, seq, now_ms + ttl_ms))
            db.execute("COMMIT")
        except BaseException:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()
        return challenge

    def record(self, *, challenge: bytes, enrollment_inputs: dict,
               signed_history_record: bytes, history_signature: bytes,
               pinned_history_authority, expected_history_authority_sha256: str,
               revoked_history_authority_sha256: tuple, now_ms: int,
               fault: str | None = None):
        if (type(challenge) is not bytes or len(challenge) != 32
                or type(enrollment_inputs) is not dict
                or type(now_ms) is not int or not 0 <= now_ms < MAX_TIME
                or fault not in (None, "before_commit", "lost_ack")):
            deny("LOCAL_COMMIT_INPUT_INVALID")
        db = connect(self.root)
        committed = False
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT purpose,host,release_epoch,release_seq,previous_head,"
                "previous_seq,deadline,state FROM challenges WHERE nonce_hash=?",
                (digest(challenge),)).fetchone()
            if row is None:
                deny("LOCAL_CHALLENGE_UNKNOWN")
            purpose, host, epoch, release, head, seq, deadline, state = row
            if state != "issued":
                deny("LOCAL_CHALLENGE_ALREADY_CONSUMED")
            if purpose != PURPOSE or now_ms >= deadline:
                deny("LOCAL_CHALLENGE_EXPIRED")
            if db.execute("SELECT head,seq FROM meta WHERE id=1").fetchone() != (head, seq):
                deny("LOCAL_HISTORY_STALE_OR_FORK")
            if (enrollment_inputs.get("expected_host_id") != host
                    or enrollment_inputs.get("expected_release_epoch") != epoch
                    or enrollment_inputs.get("expected_release_sequence") != release):
                deny("LOCAL_RELEASE_OR_HOST_MISMATCH")
            try:
                proof = H.inspect_next_history_proposal_ci_only(
                    enrollment_inputs=enrollment_inputs,
                    signed_history_record=signed_history_record,
                    history_signature=history_signature,
                    independently_pinned_history_authority=pinned_history_authority,
                    separately_expected_history_authority_sha256=(
                        expected_history_authority_sha256),
                    independently_pinned_previous_head_sha256=head,
                    independently_pinned_previous_sequence=seq,
                    independently_issued_challenge=challenge,
                    revoked_history_authority_sha256=revoked_history_authority_sha256,
                )
            except (H.Refused, ValueError, TypeError) as exc:
                raise Refused("LOCAL_EXISTING_SIGNED_VERIFIER_REFUSED") from exc
            next_head = proof.get("nextHistoryHeadSha256")
            if (proof.get("status") != H.STATUS
                    or proof.get("nextHistorySequence") != seq + 1
                    or type(next_head) is not str or HEX.fullmatch(next_head) is None
                    or any(proof.get(k) is not False for k in H.DENIED)
                    or any(proof.get(k) is not False for k in DENIED)):
                deny("LOCAL_POSITIVE_AUTHORITY_PROMOTION_REFUSED")
            db.execute(
                "UPDATE challenges SET state='consumed',next_head=? "
                "WHERE nonce_hash=? AND state='issued'",
                (next_head, digest(challenge)))
            if db.execute("SELECT changes()").fetchone() != (1,):
                deny("LOCAL_CHALLENGE_RACE_REFUSED")
            db.execute("INSERT INTO history VALUES(?,?,?,?,?)",
                       (seq + 1, head, next_head, digest(challenge),
                        digest(signed_history_record)))
            db.execute(
                "UPDATE meta SET head=?,seq=? WHERE id=1 AND head=? AND seq=?",
                (next_head, seq + 1, head, seq))
            if db.execute("SELECT changes()").fetchone() != (1,):
                deny("LOCAL_HEAD_RACE_REFUSED")
            if fault == "before_commit":
                deny("LOCAL_SIMULATED_CRASH_BEFORE_COMMIT")
            db.execute("COMMIT")
            committed = True
        except BaseException:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()
        if committed and fault == "lost_ack":
            raise UnknownAfterCommit("LOCAL_LOST_ACK_QUERY_OUTCOME_NOT_AUTORETRY")
        return {"schema": SCHEMA, "status": STATUS,
                "developmentOnlyHeadAdvanced": True,
                "nextHistoryHeadSha256": next_head,
                "nextHistorySequence": seq + 1, **DENIED}

    def outcome(self, challenge: bytes):
        if type(challenge) is not bytes or len(challenge) != 32:
            deny("LOCAL_OUTCOME_INPUT_INVALID")
        db = connect(self.root)
        try:
            row = db.execute(
                "SELECT state,next_head FROM challenges WHERE nonce_hash=?",
                (digest(challenge),)).fetchone()
        finally:
            db.close()
        if row is None:
            deny("LOCAL_UNKNOWN_OUTCOME_NO_REPLAY")
        return {"schema": SCHEMA, "status": STATUS,
                "developmentOnlyState": row[0],
                "developmentOnlyCommittedHeadSha256": row[1],
                **DENIED}

    def production_admission(self, *_args, **_kwargs):
        deny("LOCAL_DEVELOPMENT_LEDGER_NEVER_AUTHORIZES_PRODUCTION")
