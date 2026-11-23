"""Forest B4g // SYNTHETIC ONLY attempt-scoped outbox expectation inspection.

This class labels ambiguity, never settles it. Both the marker and B4f event
reside in a mutable/restorable Forest SQLite database, NOT protected custody.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from local_terminal_outbox_b4f import (
    ForestLocalTerminalOutboxInspector, OutboxRefusal,
)
from turn_bridge_b3 import OUTBOX_EXPECTATION_B4G

SCHEMA = "post-apollo.forest.local-outbox-expectation.synthetic-b4g"


class ForestOutboxExpectationInspector:
    """Read-only host-scoped local diagnostic. No actor authentication here."""

    def __init__(self, journal):
        self._base = ForestLocalTerminalOutboxInspector(journal)
        self._db = journal.db
        try:
            columns = {c[1] for c in self._db.execute(
                "PRAGMA table_info(forest_attempts_b3)")}
        except sqlite3.Error as exc:
            raise OutboxRefusal("LOCAL_EXPECTATION_UNAVAILABLE") from exc
        # Pre-B4g synthetic DBs lack this field; their provenance is UNKNOWN.
        self._has_marker = "outbox_expectation_b4g" in columns

    def inspect(self, *, owner: str, session_id: str,
                attempt_id: str) -> dict[str, Any]:
        # B4e lineage, B4f event scope and basic status checks run first.
        base = self._base.inspect(
            owner=owner, session_id=session_id, attempt_id=attempt_id)
        marker = None
        if self._has_marker:
            try:
                row = self._db.execute(
                    "SELECT outbox_expectation_b4g FROM forest_attempts_b3 "
                    "WHERE attempt_id=? AND owner_key=? AND session_id=?",
                    (attempt_id, owner, session_id),
                ).fetchone()
            except sqlite3.Error as exc:
                raise OutboxRefusal("LOCAL_EXPECTATION_UNAVAILABLE") from exc
            if row is None:
                raise OutboxRefusal("LOCAL_ATTEMPT_UNAVAILABLE")
            marker = row[0]
        if marker not in (None, OUTBOX_EXPECTATION_B4G):
            raise OutboxRefusal("LOCAL_EXPECTATION_INTEGRITY_HOLD")

        event = base["localTerminalEvent"]
        state = base["forestWriteState"]
        if marker == OUTBOX_EXPECTATION_B4G:
            if event == "LOCAL_EVENT_NOT_OBSERVED":
                classification = (
                    "EXPECTED_TERMINAL_EVENT_MISSING_HOLD"
                    if state in ("FOREST_COMMITTED", "FOREST_ABORTED")
                    else "EXPECTED_EVENT_PENDING_HOLD"
                )
            elif event in ("LOCAL_COMMITTED", "LOCAL_ABORTED"):
                classification = "EXPECTED_EVENT_OBSERVED_LOCAL_ONLY"
            else:
                raise OutboxRefusal("LOCAL_EXPECTATION_INTEGRITY_HOLD")
            expectation = "LOCAL_EXPECTED_V1"
        else:
            # A missing marker may be genuinely old, erased, or restored.
            # NEVER label it confirmed LEGACY or release a held permit.
            expectation = "INSTRUMENTATION_UNDETERMINED"
            classification = (
                "EVENT_OBSERVED_EXPECTATION_UNDETERMINED"
                if event in ("LOCAL_COMMITTED", "LOCAL_ABORTED")
                else "INSTRUMENTATION_UNDETERMINED_HOLD"
            )

        return {
            **base,
            "schema": SCHEMA,
            "localOutboxExpectation": expectation,
            "recoveryClassification": classification,
            "c5Settlement": "UNKNOWN_HOLD",
            "terminalReceiptAuthenticated": False,
            "custodyAuthenticated": False,
            "safeToRetryInference": False,
            "safeToReleaseRevocation": False,
            "productionAuthority": False,
        }
