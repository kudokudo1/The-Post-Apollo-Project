"""Identity Center v0: OFFLINE, IN-MEMORY, SYNTHETIC tenancy permission gate.

This is an executable contract fixture, NOT an authenticated API, user
database, IdP, management console, production policy engine, or secret vault.
No disk paths, network, credentials, real company data, or service imports.
The test harness alone seeds rows: those seed methods are not user endpoints.
"""
from __future__ import annotations

import sqlite3


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE principals (
    principal_id TEXT PRIMARY KEY
);

CREATE TABLE organizations (
    org_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('llc', 'nonprofit', 'customer'))
);

CREATE TABLE portfolios (
    portfolio_id TEXT PRIMARY KEY
);

CREATE TABLE portfolio_members (
    portfolio_id TEXT NOT NULL REFERENCES portfolios(portfolio_id),
    principal_id TEXT NOT NULL REFERENCES principals(principal_id),
    PRIMARY KEY (portfolio_id, principal_id)
);

CREATE TABLE portfolio_organizations (
    portfolio_id TEXT NOT NULL REFERENCES portfolios(portfolio_id),
    org_id TEXT NOT NULL REFERENCES organizations(org_id),
    PRIMARY KEY (portfolio_id, org_id)
);

CREATE TABLE memberships (
    principal_id TEXT NOT NULL REFERENCES principals(principal_id),
    org_id TEXT NOT NULL REFERENCES organizations(org_id),
    state TEXT NOT NULL CHECK (state IN ('active', 'revoked')),
    PRIMARY KEY (principal_id, org_id)
);

CREATE TABLE divisions (
    org_id TEXT NOT NULL REFERENCES organizations(org_id),
    division_id TEXT NOT NULL,
    PRIMARY KEY (org_id, division_id)
);

CREATE TABLE units (
    org_id TEXT NOT NULL REFERENCES organizations(org_id),
    unit_id TEXT NOT NULL,
    PRIMARY KEY (org_id, unit_id)
);

CREATE TABLE records (
    org_id TEXT NOT NULL,
    record_id TEXT NOT NULL,
    division_id TEXT NOT NULL,
    unit_id TEXT NOT NULL,
    PRIMARY KEY (org_id, record_id),
    FOREIGN KEY (org_id, division_id) REFERENCES divisions(org_id, division_id),
    FOREIGN KEY (org_id, unit_id) REFERENCES units(org_id, unit_id)
);

CREATE TABLE grants (
    grant_id TEXT PRIMARY KEY,
    principal_id TEXT NOT NULL,
    org_id TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('records.read', 'records.write')),
    division_id TEXT,
    unit_id TEXT,
    expires_at INTEGER,
    FOREIGN KEY (principal_id, org_id) REFERENCES memberships(principal_id, org_id),
    FOREIGN KEY (org_id, division_id) REFERENCES divisions(org_id, division_id),
    FOREIGN KEY (org_id, unit_id) REFERENCES units(org_id, unit_id),
    CHECK (expires_at IS NULL OR expires_at >= 0)
);
"""


class SyntheticPolicyStore:
    """Disposable fixture. Caller-controlled seed methods have NO auth checks."""

    def __init__(self) -> None:
        self._db = sqlite3.connect(":memory:")
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.executescript(SCHEMA)

    def close(self) -> None:
        self._db.close()

    def _seed(self, query: str, values: tuple[object, ...]) -> None:
        # Test-only writes, never exposed as a service or accepted as auth.
        with self._db:
            self._db.execute(query, values)

    def seed_principal(self, principal_id: str) -> None:
        self._seed("INSERT INTO principals VALUES (?)", (principal_id,))

    def seed_organization(self, org_id: str, kind: str) -> None:
        self._seed("INSERT INTO organizations VALUES (?, ?)", (org_id, kind))

    def seed_portfolio(self, portfolio_id: str) -> None:
        self._seed("INSERT INTO portfolios VALUES (?)", (portfolio_id,))

    def seed_portfolio_member(self, portfolio_id: str, principal_id: str) -> None:
        self._seed("INSERT INTO portfolio_members VALUES (?, ?)",
                   (portfolio_id, principal_id))

    def seed_portfolio_organization(self, portfolio_id: str, org_id: str) -> None:
        self._seed("INSERT INTO portfolio_organizations VALUES (?, ?)",
                   (portfolio_id, org_id))

    def seed_membership(self, principal_id: str, org_id: str) -> None:
        self._seed("INSERT INTO memberships VALUES (?, ?, 'active')",
                   (principal_id, org_id))

    def revoke_membership(self, principal_id: str, org_id: str) -> None:
        self._seed("UPDATE memberships SET state='revoked' WHERE principal_id=? AND org_id=?",
                   (principal_id, org_id))

    def seed_division(self, org_id: str, division_id: str) -> None:
        self._seed("INSERT INTO divisions VALUES (?, ?)", (org_id, division_id))

    def seed_unit(self, org_id: str, unit_id: str) -> None:
        self._seed("INSERT INTO units VALUES (?, ?)", (org_id, unit_id))

    def seed_record(self, org_id: str, record_id: str, division_id: str,
                    unit_id: str) -> None:
        self._seed("INSERT INTO records VALUES (?, ?, ?, ?)",
                   (org_id, record_id, division_id, unit_id))

    def seed_grant(self, grant_id: str, principal_id: str, org_id: str,
                   action: str, *, division_id: str | None = None,
                   unit_id: str | None = None,
                   expires_at: int | None = None) -> None:
        self._seed("INSERT INTO grants VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (grant_id, principal_id, org_id, action,
                    division_id, unit_id, expires_at))

    def allowed(self, principal_id: str, org_id: str, record_id: str,
                action: str, *, now: int) -> bool:
        """Fail closed; check stored record + membership + action + scopes.

        The caller MUST authenticate the principal and supply trusted server
        time before any future production integration. Neither is done here.
        A NULL grant scope is an intentional wildcard ONLY inside that org.
        Both non-NULL dimensions must match the stored record (intersection).
        """
        if type(now) is not int or now < 0:
            return False
        if action not in ("records.read", "records.write"):
            return False
        row = self._db.execute(
            """
            SELECT 1
            FROM records AS r
            JOIN memberships AS m
                ON m.org_id = r.org_id
                AND m.principal_id = ?
                AND m.state = 'active'
            JOIN grants AS g
                ON g.principal_id = m.principal_id
                AND g.org_id = r.org_id
                AND g.action = ?
                AND (g.division_id IS NULL OR g.division_id = r.division_id)
                AND (g.unit_id IS NULL OR g.unit_id = r.unit_id)
                AND (g.expires_at IS NULL OR g.expires_at > ?)
            WHERE r.org_id = ? AND r.record_id = ?
            LIMIT 1
            """,
            (principal_id, action, now, org_id, record_id),
        ).fetchone()
        return row is not None

    def visible_portfolio_orgs(self, principal_id: str,
                               portfolio_id: str) -> tuple[str, ...]:
        """Portfolio association does not grant tenant-private visibility.

        This restrictive prototype shows only orgs with active independent
        memberships. Real dashboards may later require explicit summary grants.
        """
        rows = self._db.execute(
            """
            SELECT po.org_id
            FROM portfolio_members AS pm
            JOIN portfolio_organizations AS po
              ON po.portfolio_id = pm.portfolio_id
            JOIN memberships AS m
              ON m.org_id = po.org_id
              AND m.principal_id = pm.principal_id
              AND m.state = 'active'
            WHERE pm.principal_id = ? AND pm.portfolio_id = ?
            ORDER BY po.org_id
            """,
            (principal_id, portfolio_id),
        ).fetchall()
        return tuple(row[0] for row in rows)
