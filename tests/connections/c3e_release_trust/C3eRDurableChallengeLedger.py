#!/usr/bin/env python3
"""C3e-R: durable CI-only challenge-consumption ledger for C3e-Q signatures.

This addresses Q's *process-restart* replay gap. An explicit test-only root
supervisor initializes a protected SQLite ledger; challenges are generated
using os.urandom(32), registered DURABLY before issuance, and consumed once
with an atomic conditional update only AFTER C3e-Q verifies a detached
signature and independently pinned evidence.

No signer enrollment, live host, independent rollback-resistant witness,
human consent or provider authority. A privileged actor able to restore the
entire SQLite file can restore previously issued challenges. Never production.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import sqlite3
import stat
import sys

HERE = Path(__file__).resolve().parent
QPATH = HERE / "C3eQSignedGuestEvidence.py"
SPEC = importlib.util.spec_from_file_location("c3er_c3eq", QPATH)
assert SPEC is not None and SPEC.loader is not None
Q = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(Q)

SCHEMA = "postapollo.connections.c3er-durable-ci-challenge.v1"
RECEIPT = "postapollo.connections.c3er-ci-consumed-receipt.v1"
DIR_PREFIX = "c3er-ci-"
DB_FILE = "challenge-ledger.sqlite"
CREATE_SQL = """
CREATE TABLE ledger_meta (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    schema TEXT NOT NULL CHECK(schema = 'postapollo.connections.c3er-durable-ci-challenge.v1')
);
CREATE TABLE challenges (
    digest TEXT PRIMARY KEY CHECK(length(digest) = 64),
    state TEXT NOT NULL CHECK(state IN ('issued', 'consumed')),
    signed_evidence_sha256 TEXT,
    CHECK ((state='issued' AND signed_evidence_sha256 IS NULL) OR
           (state='consumed' AND length(signed_evidence_sha256)=64))
);
INSERT INTO ledger_meta(id,schema)
VALUES(1, 'postapollo.connections.c3er-durable-ci-challenge.v1');
"""


class Refused(Exception):
    pass


def deny(code):
    raise Refused(code)


def validate_root(root: Path):
    if (sys.platform != "linux" or os.geteuid() != 0 or
            os.environ.get("GITHUB_ACTIONS") != "true"):
        deny("DISPOSABLE_ROOT_CI_ONLY")
    root = Path(root)
    if (not root.is_absolute() or root.parent != Path("/run") or
            not root.name.startswith(DIR_PREFIX)):
        deny("LEDGER_PATH_SCOPE_REFUSED")
    try:
        st = os.lstat(root)
    except OSError:
        deny("LEDGER_DIRECTORY_MISSING")
    if (not stat.S_ISDIR(st.st_mode) or st.st_uid != 0 or st.st_gid != 0
            or stat.S_IMODE(st.st_mode) != 0o700):
        deny("LEDGER_DIRECTORY_UNSAFE")
    return root


def check_file(path: Path):
    try:
        st = os.lstat(path)
    except OSError:
        deny("LEDGER_MISSING_REFUSE_NOT_BOOTSTRAP")
    if (not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_gid != 0
            or stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1
            or st.st_size == 0):
        deny("LEDGER_FILE_UNSAFE")


def connect(root: Path):
    root = validate_root(root)
    path = root / DB_FILE
    check_file(path)
    if (root / (DB_FILE + "-wal")).exists() or (root / (DB_FILE + "-shm")).exists():
        deny("UNEXPECTED_WAL_FILE")
    # URI mode=rw guarantees that missing state is never silently created.
    uri = path.as_uri() + "?mode=rw"
    try:
        db = sqlite3.connect(uri, uri=True, timeout=8, isolation_level=None)
        db.execute("PRAGMA busy_timeout=8000")
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA foreign_keys=ON")
        row = db.execute("SELECT schema FROM ledger_meta WHERE id=1").fetchone()
        if row != (SCHEMA,):
            deny("LEDGER_SCHEMA_OR_ROOT_MISMATCH")
        table = db.execute("PRAGMA quick_check").fetchone()
        if table != ("ok",):
            deny("LEDGER_CORRUPT")
        return db
    except (sqlite3.DatabaseError, sqlite3.OperationalError):
        deny("LEDGER_UNAVAILABLE_OR_CORRUPT")


def initialize_for_disposable_ci(root: Path):
    """Explicit fixture creation; never invoked automatically from consume."""
    root = validate_root(root)
    target = root / DB_FILE
    if os.path.lexists(target):
        deny("LEDGER_ALREADY_EXISTS")
    original_umask = os.umask(0o077)
    try:
        fd = os.open(str(target), os.O_CREAT | os.O_EXCL | os.O_RDWR |
                     os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        db = sqlite3.connect(target, isolation_level=None)
        try:
            db.execute("PRAGMA journal_mode=DELETE")
            db.execute("PRAGMA synchronous=FULL")
            db.executescript(CREATE_SQL)
        finally:
            db.close()
    except (OSError, sqlite3.DatabaseError):
        deny("CI_LEDGER_BOOTSTRAP_REFUSED")
    finally:
        os.umask(original_umask)
    check_file(target)


class DurableTestVerifier:
    def __init__(self, root: Path):
        self.root = validate_root(Path(root))
        db = connect(self.root)
        db.close()

    def issue(self):
        """Only issuer controls randomness; commit before exposing challenge."""
        token = os.urandom(32)
        digest = hashlib.sha256(token).hexdigest()
        db = connect(self.root)
        try:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO challenges(digest,state) VALUES(?,'issued')",
                       (digest,))
            db.execute("COMMIT")
        except sqlite3.DatabaseError:
            db.execute("ROLLBACK")
            deny("CHALLENGE_ISSUANCE_REFUSED")
        finally:
            db.close()
        return token

    def consume(self, challenge: bytes, *, evidence: Path, signature: Path,
                public_key: Path, pinned_signer: str,
                expected_rpm_sha256: str,
                expected_script_sha256: str,
                expected_interpreter_sha256: str,
                expected_service_pid: int,
                expected_start_ticks: str):
        if type(challenge) is not bytes or len(challenge) != 32:
            deny("CHALLENGE_BYTES_INVALID")
        digest = hashlib.sha256(challenge).hexdigest()
        # Refuse unknown/previously consumed challenges BEFORE signature work.
        db = connect(self.root)
        try:
            state = db.execute(
                "SELECT state FROM challenges WHERE digest=?", (digest,)
            ).fetchone()
        finally:
            db.close()
        if state is None:
            deny("CHALLENGE_NOT_ISSUED")
        if state != ("issued",):
            deny("CHALLENGE_ALREADY_CONSUMED_DURABLY")

        verifier = Q.OneUseTestChallenge(challenge)
        try:
            verified_receipt = verifier.verify(
                evidence=evidence, signature=signature,
                public_key=public_key, pinned_signer=pinned_signer,
                expected_rpm_sha256=expected_rpm_sha256,
                expected_script_sha256=expected_script_sha256,
                expected_interpreter_sha256=expected_interpreter_sha256,
                expected_service_pid=expected_service_pid,
                expected_start_ticks=expected_start_ticks)
            # The trusted digest comes from Q's SAME verified byte snapshot,
            # not a second read of the replaceable caller-provided pathname.
            signed_sha = verified_receipt["verifiedEvidenceSHA256"]
            if (type(signed_sha) is not str or
                    Q.HEX64.fullmatch(signed_sha) is None):
                deny("VERIFIED_DIGEST_MISSING_OR_INVALID")
        except Q.Refused as exc:
            deny("SIGNED_Q_EVIDENCE_REFUSED:" + str(exc))

        db = connect(self.root)
        try:
            db.execute("BEGIN IMMEDIATE")
            cursor = db.execute(
                """UPDATE challenges SET state='consumed',
                   signed_evidence_sha256=?
                   WHERE digest=? AND state='issued'""",
                (signed_sha, digest))
            if cursor.rowcount != 1:
                db.execute("ROLLBACK")
                deny("CHALLENGE_ALREADY_CONSUMED_DURABLY")
            db.execute("COMMIT")
        except sqlite3.DatabaseError:
            db.execute("ROLLBACK")
            deny("CHALLENGE_CONSUMPTION_REFUSED")
        finally:
            db.close()
        return {
            "schema": RECEIPT,
            "challengeConsumedDurablyInCI": True,
            "signedEvidenceValidInCI": True,
            "signedGuestOriginAuthenticated": False,
            "installedGuestMeasured": False,
            "hostAuthenticated": False,
            "canApprove": False,
            "credentialActionsEnabled": False,
            "productionAuthority": False,
        }
