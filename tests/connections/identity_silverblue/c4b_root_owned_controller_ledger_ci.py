#!/usr/bin/env python3
"""C4b Package 1: disposable Linux root-owned controller trust ledger.

This is a CI-only protected-file *rehearsal*, NOT production enrollment.
A root-only test supervisor initializes a pinned controller public root,
policy and chain cursor; the same Linux root authority explicitly stages the
exact intended successor ID, root and policy hash. Only then can an existing
C4b dual-signed rotation commit a replacement in one SQLite transaction.

A desktop UID cannot read or write the root-owned 0700 directory and 0600
database. This is REAL Linux UID separation in disposable GitHub CI, but
root compromise, restoring the whole database, or CI test roots controlled
by the runner defeat the authority. No real keys, sign-in or host admission.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path
import sqlite3
import stat
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

import c4b_signed_trust_transition_ci as T
import controller_owned_policy_intake_ci as P
import controller_pinned_enrollment_gate_ci as E
import c4b_signed_external_checkpoint_ci as W

SCHEMA = "postapollo.identity.c4b-root-owned-controller-ledger.ci-v1"
DIR_PREFIX = "c4b-p1-controller-ci-"
DB_FILE = "controller-trust.sqlite"
MAX_DB_BYTES = 1024 * 1024
FIELDS = (
    "host_id", "controller_root_public", "controller_policy",
    "controller_policy_sha256", "transition_sha256", "transition_sequence",
    "pending_id", "pending_next_root_sha256", "pending_next_policy_sha256",
)
CREATE_SQL = """
CREATE TABLE schema_meta (
  id INTEGER PRIMARY KEY CHECK(id = 1),
  schema TEXT NOT NULL CHECK(schema = 'postapollo.identity.c4b-root-owned-controller-ledger.ci-v1')
);
CREATE TABLE controller_state (
  id INTEGER PRIMARY KEY CHECK(id = 1),
  host_id TEXT NOT NULL,
  controller_root_public BLOB NOT NULL CHECK(length(controller_root_public) = 32),
  controller_policy BLOB NOT NULL,
  controller_policy_sha256 TEXT NOT NULL CHECK(length(controller_policy_sha256) = 64),
  transition_sha256 TEXT NOT NULL CHECK(length(transition_sha256) = 64),
  transition_sequence INTEGER NOT NULL CHECK(transition_sequence >= 0),
  pending_id TEXT,
  pending_next_root_sha256 TEXT,
  pending_next_policy_sha256 TEXT,
  CHECK (
    (pending_id IS NULL AND pending_next_root_sha256 IS NULL
      AND pending_next_policy_sha256 IS NULL)
    OR
    (pending_id IS NOT NULL AND pending_next_root_sha256 IS NOT NULL
      AND pending_next_policy_sha256 IS NOT NULL)
  )
);
INSERT INTO schema_meta (id,schema)
VALUES(1,'postapollo.identity.c4b-root-owned-controller-ledger.ci-v1');
"""
NEGATIVE = {
    "operatorEnrollmentRootCustodyVerified": False,
    "independentlyAuthorizedHumanRotationVerified": False,
    "hardwareRollbackResistanceVerified": False,
    "productionProtectedAuthorityInstalled": False,
    "independentHostKernelAndSeatAttestationVerified": False,
    "c5HumanConsentVerified": False,
    "hostAuthenticated": False,
    "canBeginSignIn": False,
    "credentialActionsEnabled": False,
    "productionAuthority": False,
}


class Refused(ValueError):
    """Missing root CI authority or invalid one-use signed transition."""


def _deny(reason):
    raise Refused(reason)


def _hash(blob):
    return hashlib.sha256(blob).hexdigest()


def _root_dir(root):
    if (sys.platform != "linux" or os.geteuid() != 0
            or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"
            or os.environ.get("GITHUB_ACTOR") != "kudokudo1"
            or os.environ.get("POST_APOLLO_C4B_P1_ROOT_LEDGER_TEST_ONLY") != "1"):
        _deny("C4B_P1_DISPOSABLE_ROOT_GITHUB_CI_ONLY")
    if (not isinstance(root, Path) or not root.is_absolute()
            or root.parent != Path("/run")
            or not root.name.startswith(DIR_PREFIX)
            or len(root.name) > 100):
        _deny("C4B_P1_LEDGER_DIRECTORY_SCOPE_REFUSED")
    try:
        st = os.lstat(root)
    except OSError as exc:
        raise Refused("C4B_P1_LEDGER_DIRECTORY_MISSING") from exc
    if (not stat.S_ISDIR(st.st_mode) or st.st_uid != 0 or st.st_gid != 0
            or stat.S_IMODE(st.st_mode) != 0o700):
        _deny("C4B_P1_LEDGER_DIRECTORY_UNSAFE")
    return root


def _check_db(root):
    path = _root_dir(root) / DB_FILE
    try:
        st = os.lstat(path)
    except OSError as exc:
        raise Refused("C4B_P1_LEDGER_MISSING_NO_AUTO_BOOTSTRAP") from exc
    if (not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_gid != 0
            or stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1
            or not 0 < st.st_size <= MAX_DB_BYTES):
        _deny("C4B_P1_LEDGER_FILE_UNSAFE")
    if any((root / (DB_FILE + suffix)).exists()
           for suffix in ("-wal", "-shm")):
        _deny("C4B_P1_UNEXPECTED_SQLITE_SIDE_FILES")
    return path


def _connect(root):
    path = _check_db(root)
    db = None
    try:
        db = sqlite3.connect(path.as_uri() + "?mode=rw", uri=True,
                             isolation_level=None, timeout=8)
        db.execute("PRAGMA busy_timeout=8000")
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA trusted_schema=OFF")
        if db.execute("PRAGMA quick_check").fetchone() != ("ok",):
            _deny("C4B_P1_LEDGER_QUICK_CHECK_REFUSED")
        if db.execute("SELECT schema FROM schema_meta WHERE id=1").fetchone() != (SCHEMA,):
            _deny("C4B_P1_LEDGER_SCHEMA_REFUSED")
        return db
    except (sqlite3.Error, Refused) as exc:
        if db is not None:
            db.close()
        if isinstance(exc, Refused):
            raise
        raise Refused("C4B_P1_LEDGER_CONNECT_OR_INTEGRITY_REFUSED") from exc


def _read(db):
    row = db.execute(
        "SELECT " + ",".join(FIELDS) + " FROM controller_state WHERE id=1"
    ).fetchone()
    if row is None or len(row) != len(FIELDS):
        _deny("C4B_P1_CONTROLLER_LEDGER_STATE_MISSING")
    values = dict(zip(FIELDS, row))
    root_public = values["controller_root_public"]
    policy_raw = values["controller_policy"]
    if (type(root_public) is not bytes or len(root_public) != 32
            or type(policy_raw) is not bytes
            or type(values["controller_policy_sha256"]) is not str
            or _hash(policy_raw) != values["controller_policy_sha256"]
            or type(values["transition_sha256"]) is not str
            or E.HEX.fullmatch(values["transition_sha256"]) is None
            or type(values["transition_sequence"]) is not int
            or not 0 <= values["transition_sequence"] < 2**53 - 1):
        _deny("C4B_P1_LEDGER_FIELDS_OR_STORED_DIGEST_REFUSED")
    try:
        policy = P._parse_policy(policy_raw)
        key = Ed25519PublicKey.from_public_bytes(root_public)
    except (P.Refused, ValueError) as exc:
        raise Refused("C4B_P1_LEDGER_POLICY_OR_PUBLIC_ROOT_REFUSED") from exc
    if (not hmac.compare_digest(_hash(root_public), policy["rootPublicSha256"])
            or policy["hostId"] != values["host_id"]):
        _deny("C4B_P1_LEDGER_STORED_CONTROLLER_MISMATCH")
    pending = tuple(values[n] for n in
                    ("pending_id", "pending_next_root_sha256",
                     "pending_next_policy_sha256"))
    if (pending != (None, None, None)
            and (any(type(x) is not str for x in pending)
                 or E.IDENT.fullmatch(pending[0]) is None
                 or any(E.HEX.fullmatch(x) is None for x in pending[1:]))):
        _deny("C4B_P1_LEDGER_PENDING_INTENT_INVALID")
    return values, policy, key


def initialize_for_disposable_ci(root, *, initial_controller_policy: bytes,
                                  initial_controller_root_public: bytes,
                                  initial_transition_sha256: str,
                                  initial_transition_sequence: int):
    """Explicit CI-only bootstrapping; never auto-create a missing ledger."""
    root = _root_dir(root)
    if (type(initial_controller_root_public) is not bytes
            or len(initial_controller_root_public) != 32
            or type(initial_transition_sha256) is not str
            or E.HEX.fullmatch(initial_transition_sha256) is None
            or type(initial_transition_sequence) is not int
            or not 0 <= initial_transition_sequence < 2**53 - 1):
        _deny("C4B_P1_BOOTSTRAP_EXACT_ROOT_OR_CURSOR_REQUIRED")
    try:
        policy = P._parse_policy(initial_controller_policy)
        Ed25519PublicKey.from_public_bytes(initial_controller_root_public)
    except (P.Refused, ValueError) as exc:
        raise Refused("C4B_P1_BOOTSTRAP_POLICY_OR_ROOT_REFUSED") from exc
    if not hmac.compare_digest(
        _hash(initial_controller_root_public), policy["rootPublicSha256"]):
        _deny("C4B_P1_BOOTSTRAP_PINNED_ROOT_POLICY_MISMATCH")
    path = root / DB_FILE
    fd = None
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_RDWR |
                     os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        os.fchmod(fd, 0o600)
    except OSError as exc:
        raise Refused("C4B_P1_BOOTSTRAP_LEDGER_CREATE_REFUSED") from exc
    finally:
        if fd is not None:
            os.close(fd)
    db = None
    try:
        db = sqlite3.connect(path, isolation_level=None)
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=FULL")
        db.executescript(CREATE_SQL)
        db.execute("BEGIN IMMEDIATE")
        db.execute(
            """INSERT INTO controller_state
            (id,host_id,controller_root_public,controller_policy,
             controller_policy_sha256,transition_sha256,transition_sequence)
            VALUES(1,?,?,?,?,?,?)""",
            (policy["hostId"], initial_controller_root_public,
             initial_controller_policy, _hash(initial_controller_policy),
             initial_transition_sha256, initial_transition_sequence))
        db.execute("COMMIT")
    except sqlite3.Error as exc:
        if db is not None and db.in_transaction:
            db.execute("ROLLBACK")
        raise Refused("C4B_P1_BOOTSTRAP_SQLITE_REFUSED") from exc
    finally:
        if db is not None:
            db.close()
    # The file already existed before SQLite opened; a fresh explicit
    # protected ledger does not inherit a user-writable database.
    _check_db(root)


def _external_state(values, policy):
    """Exact read-only state pinned by a separately signed witness."""
    return {
        "hostId": values["host_id"],
        "controllerRootSha256": _hash(values["controller_root_public"]),
        "controllerPolicySha256": values["controller_policy_sha256"],
        "transitionSha256": values["transition_sha256"],
        "transitionSequence": values["transition_sequence"],
        "minimumReleaseEpoch": policy["minimumReleaseEpoch"],
        "minimumReleaseSequence": policy["minimumReleaseSequence"],
    }


def inspect_current_ci_only(root):
    db = _connect(root)
    try:
        values, policy, _ = _read(db)
        return {
            "schema": SCHEMA,
            "rootOwnedControllerLedgerReadInDisposableCi": True,
            **_external_state(values, policy),
            "hostId": values["host_id"],
            "controllerRootSha256": _hash(values["controller_root_public"]),
            "policySha256": values["controller_policy_sha256"],
            "transitionSha256": values["transition_sha256"],
            "transitionSequence": values["transition_sequence"],
            "pendingIntentExists": values["pending_id"] is not None,
            **NEGATIVE,
        }
    finally:
        db.close()


def stage_rotation_intent_for_disposable_ci(
    root, *, transition_id: str, next_root_sha256: str,
    next_policy_sha256: str,
):
    """Explicit privileged CI test-harness intent; NOT real human consent."""
    if (type(transition_id) is not str or
            E.IDENT.fullmatch(transition_id) is None
            or any(type(x) is not str or E.HEX.fullmatch(x) is None
                   for x in (next_root_sha256, next_policy_sha256))):
        _deny("C4B_P1_STAGE_CANONICAL_INTENT_REQUIRED")
    db = _connect(root)
    try:
        db.execute("BEGIN IMMEDIATE")
        values, _, _ = _read(db)
        if values["pending_id"] is not None:
            _deny("C4B_P1_STAGE_ALREADY_PENDING")
        if next_root_sha256 == _hash(values["controller_root_public"]):
            _deny("C4B_P1_STAGE_NEXT_ROOT_NOT_NEW")
        db.execute(
            """UPDATE controller_state SET pending_id=?,
              pending_next_root_sha256=?,pending_next_policy_sha256=?
              WHERE id=1""", (transition_id, next_root_sha256,
                               next_policy_sha256))
        db.execute("COMMIT")
    except (sqlite3.Error, Refused) as exc:
        if db.in_transaction:
            db.execute("ROLLBACK")
        if isinstance(exc, Refused):
            raise
        raise Refused("C4B_P1_STAGE_LEDGER_TRANSACTION_REFUSED") from exc
    finally:
        db.close()


def _verify_and_commit_rotation_core_ci_only(
    root, *, next_policy: bytes, next_root_public: bytes,
    transition: bytes, previous_signature: bytes,
    proposed_signature: bytes, next_controller_dir: Path,
    serial: bytes, controller_challenge: str,
    signed_external_checkpoint=None,
):
    """One-use root-owned transaction across signature check and commit.

    Only the trusted *disposable root test harness* can select root and
    initial state. A deployment would require approved native authority,
    real human approval, independent host evidence and rollback-resistant
    storage; this is deliberately not a production service or CLI.
    """
    if type(next_root_public) is not bytes or len(next_root_public) != 32:
        _deny("C4B_P1_NEXT_PUBLIC_ROOT_REQUIRED")
    try:
        proposed_root = Ed25519PublicKey.from_public_bytes(next_root_public)
        signed = T._record(transition)
    except (ValueError, T.Refused) as exc:
        raise Refused("C4B_P1_TRANSITION_RECORD_REFUSED") from exc
    db = _connect(root)
    try:
        db.execute("BEGIN IMMEDIATE")
        values, old_policy, old_root = _read(db)
        if signed_external_checkpoint is not None:
            if type(signed_external_checkpoint) is not dict or set(
                    signed_external_checkpoint) != {
                    "signed_checkpoint", "checkpoint_signature",
                    "independently_pinned_witness_root",
                    "independently_pinned_witness_sha256",
                    "independently_issued_challenge"}:
                _deny("C4B_P1_EXACT_EXTERNAL_WITNESS_PARAMS_REQUIRED")
            try:
                witness = W.inspect_current_checkpoint_ci_only(
                    controller_state=_external_state(values, old_policy),
                    **signed_external_checkpoint)
            except W.Refused as exc:
                raise Refused("C4B_P1_FRESH_EXTERNAL_WITNESS_STATE_REFUSED") from exc
            if (witness.get(
                    "externalPinnedSignedCheckpointMatchesRootOwnedLedgerInCi") is not True
                    or any(witness.get(key) is not False for key in W.NEGATIVE)):
                _deny("C4B_P1_WITNESS_ATTEMPTED_AUTHORITY_PROMOTION")
        if values["pending_id"] is None:
            _deny("C4B_P1_NO_STAGED_PRIVILEGED_INTENT")
        if (signed["transitionId"] != values["pending_id"]
                or signed["nextRootSha256"] != values["pending_next_root_sha256"]
                or signed["nextPolicySha256"] != values["pending_next_policy_sha256"]
                or not hmac.compare_digest(
                    signed["nextRootSha256"], _hash(next_root_public))
                or not hmac.compare_digest(
                    signed["nextPolicySha256"], _hash(next_policy))):
            _deny("C4B_P1_TRANSITION_NOT_PRIVILEGED_INTENT")
        try:
            verified = T.inspect_rotation_ci_only(
                previous_policy=values["controller_policy"],
                next_policy=next_policy, transition=transition,
                previous_root=old_root, proposed_root=proposed_root,
                previous_signature=previous_signature,
                proposed_signature=proposed_signature,
                independently_pinned_previous_policy_sha256=values[
                    "controller_policy_sha256"],
                independently_pinned_previous_transition_sha256=values[
                    "transition_sha256"],
                independently_pinned_transition_sequence=values[
                    "transition_sequence"],
                independently_expected_transition_id=values["pending_id"],
                next_controller_dir=next_controller_dir,
                serial=serial, controller_challenge=controller_challenge,
            )
        except T.Refused as exc:
            raise Refused("C4B_P1_ROTATION_SIGNATURE_OR_ENROLLMENT_REFUSED") from exc
        if (verified["nextControllerRootSha256"] != _hash(next_root_public)
                or verified["nextPolicySha256"] != _hash(next_policy)
                or verified["transitionSha256"] != _hash(transition)
                or verified["transitionSequence"] != values["transition_sequence"] + 1
                or any(verified.get(name) is not False for name in
                       (*T.NEGATIVE, *P.NEGATIVE, *E.NEGATIVE))):
            _deny("C4B_P1_ROTATION_AUTHORITY_OR_CURSOR_MISMATCH")
        db.execute(
            """UPDATE controller_state
               SET controller_root_public=?,controller_policy=?,
                   controller_policy_sha256=?,transition_sha256=?,
                   transition_sequence=?,pending_id=NULL,
                   pending_next_root_sha256=NULL,
                   pending_next_policy_sha256=NULL
               WHERE id=1""",
            (next_root_public, next_policy, _hash(next_policy),
             _hash(transition), verified["transitionSequence"]))
        db.execute("COMMIT")
        return {
            "schema": SCHEMA,
            "rootOwnedDisposableControllerRotationCommittedInCi": True,
            "singlePrivilegedTestIntentConsumedInCi": True,
            "transitionSequence": verified["transitionSequence"],
            "controllerRootSha256": verified["nextControllerRootSha256"],
            "transitionSha256": verified["transitionSha256"],
            "hostId": verified["hostId"],
            **T.NEGATIVE, **P.NEGATIVE, **E.NEGATIVE, **NEGATIVE,
        }
    except (sqlite3.Error, Refused) as exc:
        if db.in_transaction:
            db.execute("ROLLBACK")
        if isinstance(exc, Refused):
            raise
        raise Refused("C4B_P1_COMMIT_LEDGER_TRANSACTION_REFUSED") from exc
    finally:
        db.close()


def verify_and_commit_rotation_ci_only(
    root, *, next_policy: bytes, next_root_public: bytes,
    transition: bytes, previous_signature: bytes,
    proposed_signature: bytes, next_controller_dir: Path,
    serial: bytes, controller_challenge: str,
):
    """Legacy diagnostic fixture with no signed outside witness.

    Production must never call this entrypoint; all returned authorization
    fields remain FALSE, including if the root-owned local DB was replayed.
    """
    return _verify_and_commit_rotation_core_ci_only(
        root, next_policy=next_policy, next_root_public=next_root_public,
        transition=transition, previous_signature=previous_signature,
        proposed_signature=proposed_signature,
        next_controller_dir=next_controller_dir,
        serial=serial, controller_challenge=controller_challenge,
    )


def verify_and_commit_rotation_with_checkpoint_ci_only(
    root, *, signed_external_checkpoint: dict,
    next_policy: bytes, next_root_public: bytes,
    transition: bytes, previous_signature: bytes,
    proposed_signature: bytes, next_controller_dir: Path,
    serial: bytes, controller_challenge: str,
):
    """Fail closed unless a fresh external checkpoint agrees UNDER DB lock.

    Separate independently protected witness custody and real nonce
    consumption are still missing. This is a CI source boundary, not a live
    production rotation or an enrollment endpoint.
    """
    if type(signed_external_checkpoint) is not dict:
        _deny("C4B_P1_WITNESSED_COMMIT_REQUIRED")
    return _verify_and_commit_rotation_core_ci_only(
        root, next_policy=next_policy, next_root_public=next_root_public,
        transition=transition, previous_signature=previous_signature,
        proposed_signature=proposed_signature,
        next_controller_dir=next_controller_dir,
        serial=serial, controller_challenge=controller_challenge,
        signed_external_checkpoint=signed_external_checkpoint,
    )
