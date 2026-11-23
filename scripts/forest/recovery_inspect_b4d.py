"""Forest B4d // read-only synthetic local attempt inspection, NO C5 authority.

Used by a future separately authenticated host to distinguish Forest's LOCAL
SQLite result from the (currently UNVERIFIED) Connections issuer outcome.

Never call Ollama, mutate an attempt, infer receipt authenticity, retry model
inference, authenticate the caller, open a user database, or reveal a prompt.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from session_journal_v0 import ForestSessionJournal, JournalRefusal, _key

SCHEMA = "post-apollo.forest.local-recovery.synthetic-b4d"
FOREST_STATES = {
    "RESERVED": "FOREST_RESERVED",
    "ABORTED": "FOREST_ABORTED",
    "COMMITTED": "FOREST_COMMITTED",
}


class RecoveryRefusal(Exception):
    """Fixed reason; never include a private record or SQL exception."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class ForestLocalRecoveryInspector:
    """Read-only inspection of B3's durable local attempt row.

    owner_key MUST be supplied by a verified host, never chosen by a client.
    This module cannot inspect the separately protected C5 issuer DB.
    """

    def __init__(self, journal: ForestSessionJournal):
        if type(journal) is not ForestSessionJournal:
            raise RecoveryRefusal("INVALID_JOURNAL")
        self._db = journal.db
        try:
            if self._db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='forest_attempts_b3'"
            ).fetchone() is None:
                raise RecoveryRefusal("ATTEMPT_SCHEMA_MISSING")
        except sqlite3.Error as exc:
            raise RecoveryRefusal("LOCAL_INSPECTION_UNAVAILABLE") from exc

    def inspect(self, *, owner: str, session_id: str,
                attempt_id: str) -> dict[str, Any]:
        """Expose only coarse LOCAL status, never C5 terminal confirmation.

        Even after FOREST_COMMITTED, an issuer that lost the writer's receipt
        may remain UNKNOWN_HOLD. Even after FOREST_ABORTED, issuer clearance
        cannot be inferred. RESERVED cannot tell live inference from a crash.
        """
        try:
            owner = _key(owner)
            session_id = _key(session_id)
            attempt_id = _key(attempt_id)
        except JournalRefusal as exc:
            raise RecoveryRefusal("INVALID_INSPECTION_SCOPE") from exc

        try:
            row = self._db.execute(
                "SELECT a.status,a.reply_turn_id,a.expected_revision,"
                "a.model_key,a.created_at_ms,a.updated_at_ms,s.revision,"
                "u.turn_id,u.role,u.session_id,u.ordinal,u.recorded_at_ms,"
                "t.turn_id,t.role,t.session_id,t.ordinal,t.model_key,"
                "t.provider_key,t.recorded_at_ms "
                "FROM forest_attempts_b3 AS a "
                "INNER JOIN forest_sessions AS s "
                "ON s.session_id=a.session_id "
                "LEFT JOIN forest_turns AS u ON u.turn_id=a.user_turn_id "
                "LEFT JOIN forest_turns AS t ON t.turn_id=a.reply_turn_id "
                "WHERE a.attempt_id=? AND a.session_id=? AND a.owner_key=? "
                "AND s.owner_key=?",
                (attempt_id, session_id, owner, owner),
            ).fetchone()
        except sqlite3.Error as exc:
            raise RecoveryRefusal("LOCAL_INSPECTION_UNAVAILABLE") from exc
        if row is None:
            # Same refusal for nonexistent, wrong owner, wrong Tree/session.
            raise RecoveryRefusal("ATTEMPT_UNAVAILABLE")
        (state, reply_id, expected_revision, model_key, created_at,
         updated_at, current_revision, user_id, user_role, user_session,
         user_ordinal, user_recorded_at, joined_id, reply_role,
         reply_session, reply_ordinal, reply_model, reply_provider,
         reply_recorded_at) = row
        # B4e synthetic lineage check: local FK existence is insufficient.
        # The original attempt must point to a genuine user turn in the same
        # owner-scoped session. Revision can exceed turn ordinal because B1's
        # state transitions also advance revision.
        if (state not in FOREST_STATES
                or type(expected_revision) is not int
                or type(current_revision) is not int
                or type(user_ordinal) is not int
                or type(created_at) is not int
                or type(updated_at) is not int
                or type(user_recorded_at) is not int
                or user_id is None or user_role != "user"
                or user_session != session_id or user_ordinal < 1
                or expected_revision < user_ordinal
                or current_revision < expected_revision
                or not model_key or created_at < user_recorded_at
                or updated_at < created_at):
            raise RecoveryRefusal("LOCAL_INTEGRITY_HOLD")
        if state == "COMMITTED":
            # The B3 writer appends one assistant turn immediately after the
            # reserved user turn and stores that reply ID atomically with the
            # session revision. Check this local lineage, not C5 settlement.
            if (type(reply_id) is not str or reply_id != joined_id
                    or reply_role != "assistant"
                    or reply_session != session_id
                    or type(reply_ordinal) is not int
                    or reply_ordinal != user_ordinal + 1
                    or reply_model != model_key
                    or reply_provider != "ollama"
                    or type(reply_recorded_at) is not int
                    or reply_recorded_at < created_at
                    or current_revision < expected_revision + 1):
                raise RecoveryRefusal("LOCAL_INTEGRITY_HOLD")
        elif reply_id is not None:
            # RESERVED/ABORTED must not point to any assistant or user reply.
            raise RecoveryRefusal("LOCAL_INTEGRITY_HOLD")

        return {
            "schema": SCHEMA,
            "attemptId": attempt_id,
            "sessionId": session_id,
            "forestWriteState": FOREST_STATES[state],
            # Deliberately unavailable without independently protected C5.
            "c5Settlement": "UNKNOWN_HOLD",
            "c5EvidenceAuthenticated": False,
            "terminalReceiptAuthenticated": False,
            "safeToRetryInference": False,
            "safeToReleaseRevocation": False,
            "productionAuthority": False,
        }
