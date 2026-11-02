-- EXPERIMENTAL Identity Center read-only API persistence fixture v0.
-- Create ONLY inside a disposable CI temp directory. This is not a migration,
-- approved production schema, audit trail, or a worker administration API.
PRAGMA foreign_keys = ON;

CREATE TABLE principals (
    principal_id TEXT PRIMARY KEY
);
CREATE TABLE provider_subjects (
    issuer TEXT NOT NULL,
    subject TEXT NOT NULL,
    principal_id TEXT NOT NULL REFERENCES principals(principal_id),
    PRIMARY KEY (issuer, subject)
);
CREATE TABLE organizations (
    org_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('llc', 'nonprofit', 'customer'))
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
CREATE TABLE grants (
    grant_id TEXT PRIMARY KEY,
    principal_id TEXT NOT NULL,
    org_id TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('records.read', 'records.write')),
    division_id TEXT,
    unit_id TEXT,
    expires_at INTEGER,
    FOREIGN KEY (principal_id, org_id)
        REFERENCES memberships(principal_id, org_id),
    FOREIGN KEY (org_id, division_id)
        REFERENCES divisions(org_id, division_id),
    FOREIGN KEY (org_id, unit_id)
        REFERENCES units(org_id, unit_id),
    CHECK (expires_at IS NULL OR expires_at >= 0)
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

CREATE INDEX idx_memberships_org_state ON memberships (org_id, state);
CREATE INDEX idx_grants_principal_org_expiry
    ON grants (principal_id, org_id, expires_at);
CREATE INDEX idx_portfolio_orgs_org ON portfolio_organizations (org_id);

PRAGMA user_version = 1;
