"""Identity DOC 6 disposable local pre-send outcome HOLD reference.

This models *one* possible durable, fail-closed command ambiguity marker on a
pre-existing SQLite test database. It never sends a command, opens a browser,
verifies host authenticity, settles an issuer outcome or permits any retry.

Even a valid or empty local DB is NOT an independently protected history.
Same-UID replacement/backup rollback can destroy records. Every public
projection is UNKNOWN_HOLD and all authority fields remain False.
Production admission and real command wiring are forbidden in this reference.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import sqlite3
from urllib.parse import quote

from signed_command_receipt_v0 import build_request, ReceiptRejected

SCHEMA = "post-apollo.identity.local-command-outcome-hold.test-v0"
ACTIONS = frozenset(("BEGIN", "STATUS", "CANCEL", "RECOVER"))
_ATTEMPT = re.compile(r"[0-9a-f]{32}\Z", re.ASCII)
_REQUEST = re.compile(r"[A-Za-z0-9_-]{8,128}\Z", re.ASCII)
_DIGEST = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)


class OutcomeHoldRefused(ValueError):
    """A local diagnostic cannot reserve another ambiguous native operation."""


@dataclass(frozen=True, slots=True)
class PreparedCommandCommitment:
    """Exact prepared frame digests, NOT an observation of actual transmission."""

    request_sha256: str | None
    nonce_sha256: str
    frame_sha256: str


@dataclass(frozen=True, slots=True)
class LocalOutcomeHold:
    schema: str
    state: str
    reason: str
    attempt_id: str | None = None
    action: str | None = None
    safe_actions: tuple[str, ...] = ()
    can_begin_sign_in: bool = False
    can_cancel: bool = False
    can_recover: bool = False
    can_connect_provider: bool = False
    issuer_reconciled: bool = False
    production_authority: bool = False
    prepared_commitment: PreparedCommandCommitment | None = None


class TestOnlyLocalOutcomeFence:
    """Disk-backed *negative* rehearsal. No privileged capability in this API.

    Test setup must create a disposable SQLite database with exactly the
    documented schema. This class never creates a database or repairs missing
    state. A successful local reservation cannot enable command transmission.
    """

    def __init__(self, database_path: Path) -> None:
        if (not isinstance(database_path, Path)
                or not database_path.is_absolute()
                or str(database_path) in ("/", "")):
            raise OutcomeHoldRefused("Existing absolute development database path required")
        self._path = database_path
        self._uri = "file:" + quote(str(database_path), safe="/")

    def _connect(self, *, write: bool) -> sqlite3.Connection:
        # mode=rw / mode=ro explicitly refuse implicit DB creation. The
        # caller's same-UID path remains untrusted; this is not key custody.
        mode = "rw" if write else "ro"
        db = sqlite3.connect(
            self._uri + "?mode=" + mode, uri=True,
            timeout=1, isolation_level=None,
        )
        db.execute("PRAGMA busy_timeout=1000")
        db.execute("PRAGMA foreign_keys=ON")
        if write:
            db.execute("PRAGMA synchronous=FULL")
        else:
            db.execute("PRAGMA query_only=ON")
        return db

    @staticmethod
    def _schema_version(db: sqlite3.Connection) -> int | None:
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (1, 2):
            return None
        # This recognizes the local developer fixture, NOT trusted custody.
        columns = db.execute("PRAGMA table_info(command_attempt)").fetchall()
        expected = (
            ("slot", "INTEGER", 1),
            ("attempt_id", "TEXT", 0),
            ("action", "TEXT", 0),
            ("request_digest", "TEXT", 0),
        )
        if version == 2:
            expected += (("nonce_digest", "TEXT", 0),
                         ("frame_digest", "TEXT", 0))
        if (len(columns) == len(expected)
                and all((row[1], row[2], row[5]) == want
                        for row, want in zip(columns, expected))):
            return version
        return None

    @staticmethod
    def _validate(*, attempt_id: str, action: str,
                  request_id: str | None) -> str | None:
        if (type(attempt_id) is not str or
                _ATTEMPT.fullmatch(attempt_id) is None or
                type(action) is not str or action not in ACTIONS):
            raise OutcomeHoldRefused("Invalid local command attempt or action")
        if action == "BEGIN":
            if request_id is not None:
                raise OutcomeHoldRefused("BEGIN cannot supply host request ID")
            return None
        if type(request_id) is not str or _REQUEST.fullmatch(request_id) is None:
            raise OutcomeHoldRefused("Host-issued request identifier required")
        # Do not store raw host identifiers, cookies, tokens or credentials.
        return hashlib.sha256(request_id.encode("ascii")).hexdigest()

    @staticmethod
    def _held(reason: str, *, attempt_id: str | None = None,
              action: str | None = None,
              prepared_commitment: PreparedCommandCommitment | None = None
              ) -> LocalOutcomeHold:
        return LocalOutcomeHold(
            schema=SCHEMA, state="UNKNOWN_HOLD", reason=reason,
            attempt_id=attempt_id, action=action,
            prepared_commitment=prepared_commitment,
        )

    def reserve_before_possible_send(self, *, attempt_id: str,
                                     action: str,
                                     request_id: str | None = None
                                     ) -> LocalOutcomeHold:
        """Permanently mark a local test attempt ambiguous *before* any send.

        This method cannot dispatch a command. There is deliberately no
        clear, delete, settle, retry, or release method. Even a signed
        receipt reported by the caller is not independent issuer evidence.
        """
        digest = self._validate(
            attempt_id=attempt_id, action=action, request_id=request_id)
        return self._reserve(attempt_id=attempt_id, action=action,
                             request_digest=digest, prepared=None)

    def reserve_prepared_command(self, *, attempt_id: str, action: str,
                                 request_id: str | None,
                                 client_nonce: str) -> LocalOutcomeHold:
        """Rehearse exact native pre-send binding in an explicit V2 fixture.

        Derive the commitments from the existing strict request serializer;
        never accept independently supplied frame/nonce hashes as matching.
        Store no raw nonce, request ID or serialized bytes. No actual send,
        native client integration, authority, auto migration or settlement.
        """
        digest = self._validate(attempt_id=attempt_id, action=action,
                                request_id=request_id)
        try:
            wire = build_request(action, request_id, client_nonce)
        except ReceiptRejected:
            raise OutcomeHoldRefused("Invalid prepared native command") from None
        prepared = PreparedCommandCommitment(
            request_sha256=digest,
            nonce_sha256=hashlib.sha256(client_nonce.encode("ascii")).hexdigest(),
            frame_sha256=hashlib.sha256(wire).hexdigest(),
        )
        return self._reserve(attempt_id=attempt_id, action=action,
                             request_digest=digest, prepared=prepared)

    def _reserve(self, *, attempt_id: str, action: str,
                 request_digest: str | None,
                 prepared: PreparedCommandCommitment | None) -> LocalOutcomeHold:
        version = 1 if prepared is None else 2
        try:
            with closing(self._connect(write=True)) as db, db:
                db.execute("BEGIN IMMEDIATE")
                if self._schema_version(db) != version:
                    raise OutcomeHoldRefused("Local hold schema missing or changed")
                if db.execute("SELECT COUNT(*) FROM command_attempt").fetchone()[0]:
                    raise OutcomeHoldRefused("Prior local command outcome remains unresolved")
                if prepared is None:
                    db.execute(
                        "INSERT INTO command_attempt"
                        " (slot, attempt_id, action, request_digest)"
                        " VALUES (1, ?, ?, ?)",
                        (attempt_id, action, request_digest),
                    )
                else:
                    db.execute(
                        "INSERT INTO command_attempt"
                        " (slot, attempt_id, action, request_digest,"
                        " nonce_digest, frame_digest) VALUES (1, ?, ?, ?, ?, ?)",
                        (attempt_id, action, request_digest,
                         prepared.nonce_sha256, prepared.frame_sha256),
                    )
                db.execute("COMMIT")
        except sqlite3.Error:
            raise OutcomeHoldRefused("Local hold store unavailable") from None
        return self._held("LOCAL_ATTEMPT_UNSETTLED", attempt_id=attempt_id,
                          action=action, prepared_commitment=prepared)

    def inspect(self) -> LocalOutcomeHold:
        """Fail closed for missing, empty, malformed, rolled-back, or valid DB."""
        try:
            with closing(self._connect(write=False)) as db:
                db.execute("BEGIN")
                version = self._schema_version(db)
                if version is None:
                    return self._held("UNTRUSTED_OR_INVALID_LOCAL_SCHEMA")
                fields = "slot, attempt_id, action, request_digest"
                if version == 2:
                    fields += ", nonce_digest, frame_digest"
                rows = db.execute(
                    "SELECT " + fields + " FROM command_attempt LIMIT 2"
                ).fetchall()
                if not rows:
                    # Could be a genuine fresh fixture or a same-UID rollback.
                    return self._held("EMPTY_OR_ROLLED_BACK_LOCAL_HISTORY")
                if len(rows) != 1:
                    return self._held("AMBIGUOUS_LOCAL_HISTORY")
                slot, attempt_id, action, digest = rows[0][:4]
                if (type(slot) is not int or slot != 1
                        or type(attempt_id) is not str
                        or _ATTEMPT.fullmatch(attempt_id) is None
                        or type(action) is not str or action not in ACTIONS
                        or (action == "BEGIN" and digest is not None)
                        or (action != "BEGIN"
                            and (type(digest) is not str
                                 or re.fullmatch(r"[0-9a-f]{64}", digest) is None))):
                    return self._held("INVALID_LOCAL_HISTORY")
                prepared = None
                if version == 2:
                    nonce_digest, frame_digest = rows[0][4:]
                    if not all(type(value) is str and _DIGEST.fullmatch(value)
                               for value in (nonce_digest, frame_digest)):
                        return self._held("INVALID_LOCAL_HISTORY")
                    prepared = PreparedCommandCommitment(
                        request_sha256=digest, nonce_sha256=nonce_digest,
                        frame_sha256=frame_digest,
                    )
                return self._held("LOCAL_ATTEMPT_UNSETTLED",
                                  attempt_id=attempt_id, action=action,
                                  prepared_commitment=prepared)
        except (sqlite3.Error, OSError, ValueError):
            return self._held("MISSING_OR_UNREADABLE_LOCAL_HISTORY")
