#!/usr/bin/env python3
"""DOC 1: test-only two-DB history comparison, NEVER independent authority.

One root-owned SQLite database belongs to the existing C3e development ledger.
A distinct test-only SQLite database retains a shadow head in a second
disposable process. The same CI host/admin can roll BOTH databases back, so
even matching heads NEVER establish a protected or independently current root.
No production verifier, transport, key management, or actual NAS implementation.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys

HERE = Path(__file__).resolve().parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3E_SPLITSTORE_ORIGINAL_SOURCE_REQUIRED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


S = _load("c3e_splitstore_original_trust_boundary",
          HERE / "C3eStorageIndependentTrustBoundary.py")

SCHEMA = "postapollo.connections.c3e-split-store-rollback-witness-ci-v1"
STATUS = "TWO_LOCAL_DATABASES_NOT_INDEPENDENT_CUSTODY"
MATCH = "MATCH_NOT_INDEPENDENTLY_AUTHENTICATED"
STALE = "GUEST_BEHIND_SHADOW_STALE_HOLD"
FORK = "SAME_SEQUENCE_DIFFERENT_HEAD_HOLD"
AHEAD = "GUEST_AHEAD_OF_SHADOW_UNVERIFIED_HOLD"
DB = "shadow-development-only.sqlite"
HEX = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
DENIED = {
    **S.DENIED,
    "independentlyEnrolledRootVerified": False,
    "authoritativeCurrentHistoryVerified": False,
    "independentHistoryWitnessVerified": False,
    "independentChallengeSpentVerified": False,
    "protectedTerminalReceiptVerified": False,
    "realHostSeatVerified": False,
    "safeToRetry": False,
    "canBeginSignIn": False,
    "productionSignInAllowed": False,
}


class Refused(ValueError):
    """Malformed test input, unsafe directory or guessed authority."""


def _deny(reason):
    raise Refused(reason)


def _guard_root(root):
    if (sys.platform != "linux"
            or os.geteuid() != 0
            or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
        _deny("C3E_SPLITSTORE_HOSTED_ROOT_DISPOSABLE_ONLY")
    if (not isinstance(root, Path) or not root.is_absolute()
            or root.parent != Path("/run")
            or not root.name.startswith("c3ew-ci-")
            or root.is_symlink()):
        _deny("C3E_SPLITSTORE_UNSAFE_FIXTURE_ROOT")
    try:
        info = root.lstat()
    except OSError as exc:
        raise Refused("C3E_SPLITSTORE_ROOT_MISSING") from exc
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != 0
            or stat.S_IMODE(info.st_mode) != 0o700):
        _deny("C3E_SPLITSTORE_UNSAFE_ROOT_OWNER_OR_MODE")
    return root


def _db_path(root):
    root = _guard_root(root)
    path = root / DB
    if path.is_symlink():
        _deny("C3E_SPLITSTORE_SYMLINK_DB_REFUSED")
    try:
        info = path.lstat()
    except OSError as exc:
        raise Refused("C3E_SPLITSTORE_DATABASE_MISSING_NO_AUTO_CREATE") from exc
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0
            or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1):
        _deny("C3E_SPLITSTORE_UNSAFE_DATABASE_FILE")
    return path


def _head(value):
    if type(value) is not str or HEX.fullmatch(value) is None:
        _deny("C3E_SPLITSTORE_EXACT_LOWERCASE_HEAD_REQUIRED")
    return value


def _sequence(value):
    if type(value) is not int or value < 1:
        _deny("C3E_SPLITSTORE_POSITIVE_INTEGER_SEQUENCE_REQUIRED")
    return value


def _snapshot(raw):
    expected = {"schema", "status", "source",
                "testHeadSha256", "testSequence", *S.DENIED}
    if (type(raw) is not dict or set(raw) != expected
            or raw["schema"] != S.SCHEMA
            or raw["status"] != S.STATUS_LOCAL
            or raw["source"] != S.LOCAL_DEVELOPMENT
            or any(raw[k] is not False for k in S.DENIED)):
        _deny("C3E_SPLITSTORE_UNTRUSTED_LOCAL_SNAPSHOT_REFUSED")
    return _head(raw["testHeadSha256"]), _sequence(raw["testSequence"])


def _connect(root):
    db = _db_path(root)
    connection = sqlite3.connect(db, isolation_level=None, timeout=3.0)
    connection.execute("PRAGMA busy_timeout=3000")
    connection.execute("PRAGMA synchronous=FULL")
    return connection


def _read(db):
    try:
        rows = db.execute("SELECT head, seq FROM shadow WHERE id=1").fetchall()
    except sqlite3.Error as exc:
        raise Refused("C3E_SPLITSTORE_INVALID_SHADOW_DATABASE") from exc
    if len(rows) != 1:
        _deny("C3E_SPLITSTORE_MISSING_OR_DUPLICATED_SHADOW_HEAD")
    return _head(rows[0][0]), _sequence(rows[0][1])


def _report(*, relation, guest_head, guest_sequence,
            shadow_head, shadow_sequence):
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "relation": relation,
        "localObservedHeadSha256": guest_head,
        "localObservedSequence": guest_sequence,
        "shadowObservedHeadSha256": shadow_head,
        "shadowObservedSequence": shadow_sequence,
        "next": "HOLD_NO_AUTOMATIC_RETRY_OPERATOR_ENROLLED_CUSTODIAN_REQUIRED",
        **DENIED,
    }


def initialize_ci_only(root, *, initial_local_snapshot):
    """Bootstrap untrusted shadow from test snapshot, not a genesis ceremony."""
    root = _guard_root(root)
    head, seq = _snapshot(initial_local_snapshot)
    db = root / DB
    try:
        fd = os.open(db, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
                     | os.O_CLOEXEC, 0o600)
    except OSError as exc:
        raise Refused("C3E_SPLITSTORE_NO_REINITIALIZATION_OR_SYMLINK") from exc
    os.close(fd)
    with _connect(root) as conn:
        conn.execute("CREATE TABLE shadow (id INTEGER PRIMARY KEY CHECK(id=1), "
                     "head TEXT NOT NULL, seq INTEGER NOT NULL)")
        conn.execute("INSERT INTO shadow (id, head, seq) VALUES (1, ?, ?)",
                     (head, seq))
    return _report(
        relation=MATCH, guest_head=head, guest_sequence=seq,
        shadow_head=head, shadow_sequence=seq)


def compare_ci_only(root, *, local_snapshot):
    """Comparison reveals divergence, but a matching pair grants nothing."""
    guest_head, guest_seq = _snapshot(local_snapshot)
    with _connect(root) as conn:
        ref_head, ref_seq = _read(conn)
    if guest_seq < ref_seq:
        relation = STALE
    elif guest_seq > ref_seq:
        relation = AHEAD
    elif guest_head != ref_head:
        relation = FORK
    else:
        relation = MATCH
    return _report(
        relation=relation, guest_head=guest_head, guest_sequence=guest_seq,
        shadow_head=ref_head, shadow_sequence=ref_seq)


def advance_ci_only(root, *, old_head, old_sequence, new_local_snapshot):
    """Test-only compare-and-swap: NO signature/root/currentness verification.

    A true independent authority would authenticate and atomically validate
    source, purpose, challenge spend, key roster, release and signed history.
    Here every input is caller-supplied and remains explicitly nonauthorizing.
    """
    old_head, old_sequence = _head(old_head), _sequence(old_sequence)
    new_head, new_seq = _snapshot(new_local_snapshot)
    if new_seq != old_sequence + 1 or new_head == old_head:
        _deny("C3E_SPLITSTORE_NOT_EXACTLY_ONE_NEW_LOCAL_HISTORY_LINK")
    with _connect(root) as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            saved_head, saved_seq = _read(conn)
            if (saved_head != old_head or saved_seq != old_sequence):
                conn.execute("ROLLBACK")
                _deny("C3E_SPLITSTORE_FORK_OR_STALE_EXPECTATION_REFUSED")
            conn.execute(
                "UPDATE shadow SET head=?, seq=? WHERE id=1",
                (new_head, new_seq))
            conn.execute("COMMIT")
        except sqlite3.Error as exc:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise Refused("C3E_SPLITSTORE_ATOMIC_UPDATE_REFUSED") from exc
    return _report(
        relation=MATCH, guest_head=new_head, guest_sequence=new_seq,
        shadow_head=new_head, shadow_sequence=new_seq)


def protected_admission(*_args, **_kwargs):
    _deny("C3E_SPLITSTORE_CI_SHADOW_NOT_AN_INDEPENDENT_TRUST_CUSTODIAN")
