#!/usr/bin/env python3
"""C3e-Y: signed complete Identity CI evidence + root-local issued one-use challenge.

This is a format/signature/replay experiment. Guest/process snapshots and
public-key pins are supplied by a synthetic CI caller; no installed-host
origin, independent issuer custody, C5 human consent, external rollback
resistance or production authorization is established by a passing result.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import stat
import sys

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "c3ey_identity_consistency", HERE / "C3eXIdentityRunningEvidence.py")
if _spec is None or _spec.loader is None:
    raise RuntimeError("C3EY_REQUIRED_C3EX_RECEIVER_MISSING")
X = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(X)

SCHEMA = "postapollo.connections.c3ey-signed-full-identity-evidence.ci-v1"
RECEIPT_SCHEMA = "postapollo.connections.c3ey-challenge-consumed.ci-v1"
ROLE = X.ROLE
PURPOSE = "postapollo.identity.c3ey-deny-only-full-record.ci"
AUDIENCE = "postapollo.connections.c3ey-disposable-root-issuer.ci"
DOMAIN = b"postapollo.connections.c3ey-signed-full-identity-evidence.ci-v1\x00"
DB_SCHEMA = "postapollo.connections.c3ey-root-local-one-use.ci-v1"
DIR_PREFIX = "c3ey-ci-"
DB_FILE = "challenge-ledger.sqlite"
SIGNED_KEYS = frozenset((
    "schema", "role", "purpose", "audience", "releaseEpoch",
    "releaseSequence", "challengeSha256", "evidenceSha256",
    "receiptSha256", "snapshotSha256", "receiptKeySha256",
))
CREATE_SQL = """
CREATE TABLE ledger_meta (
    id INTEGER PRIMARY KEY CHECK(id=1),
    schema TEXT NOT NULL CHECK(schema='postapollo.connections.c3ey-root-local-one-use.ci-v1')
);
CREATE TABLE challenges (
    digest TEXT PRIMARY KEY CHECK(length(digest)=64),
    audience TEXT NOT NULL,
    release_epoch INTEGER NOT NULL CHECK(release_epoch>0),
    release_sequence INTEGER NOT NULL CHECK(release_sequence>0),
    state TEXT NOT NULL CHECK(state IN ('issued','consumed')),
    signed_record_sha256 TEXT,
    CHECK ((state='issued' AND signed_record_sha256 IS NULL) OR
           (state='consumed' AND length(signed_record_sha256)=64))
);
INSERT INTO ledger_meta(id,schema) VALUES(
    1, 'postapollo.connections.c3ey-root-local-one-use.ci-v1');
"""


class Refused(ValueError):
    """A CI-only gate failed closed; never a host-authorization outcome."""


def _deny(code: str):
    raise Refused(code)


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _positive_number(value):
    return type(value) is int and 0 < value < 2**63


def _public_bytes(key: Ed25519PublicKey):
    if not isinstance(key, Ed25519PublicKey):
        _deny("INDEPENDENT_PUBLIC_KEY_REQUIRED")
    return key.public_bytes(Encoding.Raw, PublicFormat.Raw)


def _file(root: Path):
    path = root / DB_FILE
    try:
        st = os.lstat(path)
    except OSError as exc:
        raise Refused("ISSUER_LEDGER_MISSING_NO_AUTOBOOTSTRAP") from exc
    if (not stat.S_ISREG(st.st_mode) or stat.S_IMODE(st.st_mode) != 0o600
            or st.st_uid != 0 or st.st_gid != 0 or st.st_nlink != 1
            or not 0 < st.st_size < 1_000_000):
        _deny("ISSUER_LEDGER_FILE_UNSAFE")
    return path


def _root(root):
    if (sys.platform != "linux" or os.geteuid() != 0
            or os.environ.get("GITHUB_ACTIONS") != "true"):
        _deny("DISPOSABLE_ROOT_GITHUB_CI_ONLY")
    if not isinstance(root, (Path, str)):
        _deny("ISSUER_LEDGER_ROOT_TYPE_REFUSED")
    root = Path(root)
    if (not root.is_absolute() or root.parent != Path("/run")
            or not root.name.startswith(DIR_PREFIX)):
        _deny("ISSUER_LEDGER_ROOT_SCOPE_REFUSED")
    try:
        st = os.lstat(root)
    except OSError as exc:
        raise Refused("ISSUER_LEDGER_ROOT_MISSING") from exc
    if (not stat.S_ISDIR(st.st_mode) or stat.S_IMODE(st.st_mode) != 0o700
            or st.st_uid != 0 or st.st_gid != 0):
        _deny("ISSUER_LEDGER_ROOT_UNSAFE")
    return root


def _connect(root):
    path = _file(_root(root))
    try:
        # mode=rw forbids untrusted callers from bootstrapping missing state.
        db = sqlite3.connect(path.as_uri() + "?mode=rw", uri=True,
                             timeout=8, isolation_level=None)
        db.execute("PRAGMA busy_timeout=8000")
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=FULL")
        if db.execute("SELECT schema FROM ledger_meta WHERE id=1").fetchone() != (DB_SCHEMA,):
            db.close()
            _deny("ISSUER_LEDGER_SCHEMA_REFUSED")
        if db.execute("PRAGMA quick_check").fetchone() != ("ok",):
            db.close()
            _deny("ISSUER_LEDGER_CORRUPT")
        return db
    except (sqlite3.Error, OSError) as exc:
        raise Refused("ISSUER_LEDGER_OPEN_REFUSED") from exc


def initialize_for_disposable_ci(root):
    """Explicit privileged fixture setup; verification never creates a ledger."""
    root = _root(root)
    target = root / DB_FILE
    if os.path.lexists(target):
        _deny("ISSUER_LEDGER_ALREADY_EXISTS")
    old = os.umask(0o077)
    try:
        fd = os.open(str(target), os.O_CREAT | os.O_EXCL | os.O_RDWR |
                     os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        with sqlite3.connect(target, isolation_level=None) as db:
            db.execute("PRAGMA journal_mode=DELETE")
            db.execute("PRAGMA synchronous=FULL")
            db.executescript(CREATE_SQL)
        _file(root)
    except (OSError, sqlite3.Error) as exc:
        raise Refused("ISSUER_LEDGER_INIT_REFUSED") from exc
    finally:
        os.umask(old)


class DisposableCIChallengeIssuer:
    """Root-owned CI issuer, separate from the synthetic signed-host signer."""

    def __init__(self, root):
        self.root = _root(root)
        with _connect(self.root):
            pass

    def issue(self, *, release_epoch: int, release_sequence: int):
        if not _positive_number(release_epoch) or not _positive_number(release_sequence):
            _deny("RELEASE_FLOOR_INVALID")
        challenge = os.urandom(32)
        digest = _hash(challenge)
        with _connect(self.root) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                db.execute(
                    "INSERT INTO challenges VALUES(?,?,?,?,? ,?)",
                    (digest, AUDIENCE, release_epoch, release_sequence,
                     "issued", None))
                db.execute("COMMIT")
            except sqlite3.Error as exc:
                db.execute("ROLLBACK")
                raise Refused("ISSUER_CHALLENGE_ISSUE_REFUSED") from exc
        return challenge

    def _issued(self, challenge: bytes, epoch: int, sequence: int):
        if type(challenge) is not bytes or len(challenge) != 32:
            _deny("ISSUER_CHALLENGE_SIZE_REFUSED")
        if not _positive_number(epoch) or not _positive_number(sequence):
            _deny("RELEASE_FLOOR_INVALID")
        with _connect(self.root) as db:
            row = db.execute(
                "SELECT audience,release_epoch,release_sequence,state "
                "FROM challenges WHERE digest=?", (_hash(challenge),)).fetchone()
        if row is None:
            _deny("CHALLENGE_NOT_ISSUED")
        if row[:3] != (AUDIENCE, epoch, sequence):
            _deny("CHALLENGE_AUDIENCE_OR_RELEASE_FLOOR_REFUSED")
        if row[3] != "issued":
            _deny("CHALLENGE_ALREADY_CONSUMED")

    def _consume(self, challenge, epoch, sequence, signed_record_hash):
        # A competing verifier can pass _issued; the conditional transaction
        # must still make exactly one commit succeed, including after restart.
        with _connect(self.root) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                cursor = db.execute(
                    "UPDATE challenges SET state='consumed',signed_record_sha256=? "
                    "WHERE digest=? AND audience=? AND release_epoch=? "
                    "AND release_sequence=? AND state='issued'",
                    (signed_record_hash, _hash(challenge), AUDIENCE, epoch, sequence))
                if cursor.rowcount != 1:
                    db.execute("ROLLBACK")
                    _deny("CHALLENGE_REPLAY_OR_REPLACED")
                db.execute("COMMIT")
            except sqlite3.Error as exc:
                db.execute("ROLLBACK")
                raise Refused("CHALLENGE_CONSUMPTION_REFUSED") from exc


def _statement(raw: bytes):
    if (type(raw) is not bytes or not 1 <= len(raw) <= 4096
            or b"\n" in raw):
        _deny("SIGNED_STATEMENT_FRAME_REFUSED")
    try:
        record = json.loads(raw.decode("ascii"), object_pairs_hook=X._unique,
                            parse_constant=lambda _: _deny("NONFINITE_SIGNED_STATEMENT"))
        if type(record) is not dict or set(record) != SIGNED_KEYS:
            _deny("SIGNED_STATEMENT_FIELD_ROSTER_REFUSED")
        if X._canonical(record) != raw:
            _deny("NONCANONICAL_SIGNED_STATEMENT")
    except (UnicodeError, ValueError, TypeError, RecursionError, OverflowError) as exc:
        raise Refused("SIGNED_STATEMENT_JSON_REFUSED") from exc
    return record


def inspect_and_consume(*, ledger_root, challenge: bytes,
                        signed_statement: bytes, witness_signature: bytes,
                        independently_pinned_witness_key: Ed25519PublicKey,
                        independently_pinned_receipt_key: Ed25519PublicKey,
                        evidence_line: bytes, signed_receipts,
                        independently_measured: dict,
                        expected_release_epoch: int,
                        expected_release_sequence: int):
    """Verify full-record signature and existing C3e-X, then consume once in CI.

    Both pinned keys, source measurements, epoch and sequence are CI caller
    inputs; this function CANNOT prove their real-world independent custody.
    """
    issuer = DisposableCIChallengeIssuer(ledger_root)
    issuer._issued(challenge, expected_release_epoch, expected_release_sequence)
    witness_public = _public_bytes(independently_pinned_witness_key)
    receipt_public = _public_bytes(independently_pinned_receipt_key)
    if witness_public == receipt_public:
        _deny("WITNESS_AND_RECEIPT_KEY_ROLES_MUST_DIFFER")
    if (type(signed_statement) is not bytes
            or type(witness_signature) is not bytes or len(witness_signature) != 64
            or type(evidence_line) is not bytes
            or type(signed_receipts) not in (tuple, list)
            or len(signed_receipts) != 4
            or any(type(frame) is not bytes or not 1 <= len(frame) <= 1024
                   for frame in signed_receipts)
            or type(independently_measured) is not dict):
        _deny("SIGNED_INPUTS_INVALID")
    # Freeze all caller-owned mutable collections once. A caller could
    # otherwise swap a valid receipt bundle or expected pins between the
    # signed hash comparison and the C3e-X verification below.
    frames = tuple(signed_receipts)
    measured_pins = dict(independently_measured)
    try:
        measured_sha256 = _hash(X._canonical(measured_pins))
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise Refused("SNAPSHOT_PINS_NOT_CANONICAL") from exc
    record = _statement(signed_statement)
    if (record["schema"] != SCHEMA or record["role"] != ROLE
            or record["purpose"] != PURPOSE or record["audience"] != AUDIENCE
            or type(record["releaseEpoch"]) is not int
            or record["releaseEpoch"] != expected_release_epoch
            or type(record["releaseSequence"]) is not int
            or record["releaseSequence"] != expected_release_sequence
            or record["challengeSha256"] != _hash(challenge)
            or record["evidenceSha256"] != _hash(evidence_line)
            or type(record["receiptSha256"]) is not list
            or record["receiptSha256"] != [_hash(x) for x in frames]
            or record["snapshotSha256"] != measured_sha256
            or record["receiptKeySha256"] != _hash(receipt_public)):
        _deny("FULL_RECORD_SIGNATURE_BINDING_REFUSED")
    try:
        independently_pinned_witness_key.verify(
            witness_signature, DOMAIN + signed_statement)
    except (InvalidSignature, ValueError) as exc:
        raise Refused("WITNESS_SIGNATURE_REFUSED") from exc

    # C3e-X validates strict Identity service role and actual Ed25519
    # denial-frame signatures against the SAME caller-pinned receipt key.
    try:
        receipt = X.inspect_running_denials(
            evidence_line=evidence_line, signed_receipts=frames,
            independently_pinned_receipt_key=independently_pinned_receipt_key,
            independently_measured=measured_pins)
    except (X.Refused, UnicodeError, ValueError, TypeError) as exc:
        raise Refused("C3EX_IDENTITY_DENIAL_CONSISTENCY_REFUSED") from exc
    if (receipt.get("fourSignedDenialsConsistentInCI") is not True
            or any(receipt.get(name) is not False for name in X.NEGATIVE)):
        _deny("C3EX_RECEIPT_NOT_DENY_ONLY")

    issuer._consume(challenge, expected_release_epoch, expected_release_sequence,
                    _hash(signed_statement))
    return {
        "schema": RECEIPT_SCHEMA,
        "completeHostRecordSignatureVerifiedInCI": True,
        "fourSignedDenialsBoundToFullRecordInCI": True,
        "separatelyIssuedChallengeConsumedInRootLocalCI": True,
        # The root-local disposable SQLite database can be copied/rolled back
        # by a privileged actor. CI keys and snapshots are synthetic.
        "externalIssuerCustodyVerified": False,
        "externalRollbackResistanceVerified": False,
        "independentHostOriginVerified": False,
        **X.NEGATIVE,
    }
