"""Experimental persistent SQLite context reader, not an approved HR database.

Only reads a PREEXISTING SQLite file from an operator-supplied absolute path.
Creates no database, tables, users, grants, files, or organization records.
Every request opens a fresh read-only connection, so membership revocation
made by an independent trusted writer takes effect on the next request.

This intentionally does not export seed/write methods. The fixture creator
lives exclusively in tests; NEVER point this class at a real worker database
until its schema, owner, storage security, migration and auditing are reviewed.
"""
from __future__ import annotations

from pathlib import Path
import sqlite3
from urllib.parse import quote


CONTEXT_SCHEMA = "post-apollo.identity.context-summary.v0"


class DurableContextStore:
    def __init__(self, database_path: Path) -> None:
        if (not isinstance(database_path, Path)
                or not database_path.is_absolute()
                or not database_path.is_file()):
            raise ValueError("An existing absolute SQLite database is required")
        self._uri = "file:" + quote(str(database_path.resolve(strict=True)),
                                    safe="/") + "?mode=ro"
        with self._connect() as db:
            if db.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise ValueError("Unsupported synthetic context schema")

    def _connect(self) -> sqlite3.Connection:
        # URI mode=ro fails closed if the file disappears. No per-request
        # write-capable sqlite handle is ever created by the API reader.
        db = sqlite3.connect(self._uri, uri=True, timeout=2)
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA query_only=ON")
        return db

    def summary(self, issuer: str, provider_subject: str, *,
                now: int) -> dict[str, object] | None:
        """Read only the *verified issuer+subject* principal's memberships.

        None => no mapped principal, unknown schema, malformed trusted input,
        or storage failure. The API must deny, not issue a successful empty
        context for an unprovisioned/failing identity.
        """
        if (type(issuer) is not str or not issuer
                or type(provider_subject) is not str or not provider_subject
                or type(now) is not int or now < 0):
            return None
        with self._connect() as db:
            if db.execute("PRAGMA user_version").fetchone()[0] != 1:
                return None
            match = db.execute(
                """SELECT principal_id FROM provider_subjects
                   WHERE issuer = ? AND subject = ?""",
                (issuer, provider_subject),
            ).fetchone()
            if match is None:
                return None
            principal_id = match[0]
            organizations = []
            rows = db.execute(
                """SELECT o.org_id, o.kind
                   FROM memberships AS m
                   JOIN organizations AS o ON o.org_id = m.org_id
                   WHERE m.principal_id = ? AND m.state = 'active'
                   ORDER BY o.org_id""",
                (principal_id,),
            ).fetchall()
            for org_id, kind in rows:
                grants = db.execute(
                    """SELECT DISTINCT action, division_id, unit_id, expires_at
                       FROM grants
                       WHERE principal_id = ? AND org_id = ?
                         AND (expires_at IS NULL OR expires_at > ?)
                       ORDER BY action, division_id, unit_id, expires_at""",
                    (principal_id, org_id, now),
                ).fetchall()
                organizations.append({
                    "organizationId": org_id,
                    "kind": kind,
                    # Display hints, not permission receipts. Real actions
                    # still require current server-side resource checks.
                    "scopeGrants": [
                        {"action": action, "divisionId": division,
                         "unitId": unit, "expiresAt": expires_at}
                        for action, division, unit, expires_at in grants
                    ],
                })
            joined = db.execute(
                """SELECT pm.portfolio_id, po.org_id
                   FROM portfolio_members AS pm
                   JOIN portfolio_organizations AS po
                     ON po.portfolio_id = pm.portfolio_id
                   JOIN memberships AS m
                     ON m.org_id = po.org_id
                    AND m.principal_id = pm.principal_id
                    AND m.state = 'active'
                   WHERE pm.principal_id = ?
                   ORDER BY pm.portfolio_id, po.org_id""",
                (principal_id,),
            ).fetchall()
            portfolios = []
            for portfolio_id, org_id in joined:
                if not portfolios or portfolios[-1]["portfolioId"] != portfolio_id:
                    portfolios.append({"portfolioId": portfolio_id,
                                       "organizationIds": []})
                portfolios[-1]["organizationIds"].append(org_id)
            return {"status": "OK", "schema": CONTEXT_SCHEMA,
                    "organizations": organizations, "portfolios": portfolios}
