# Identity Center // synthetic tenant and permission gate v0

> **STATUS:** EXECUTABLE OFFLINE CONTRACT FIXTURE, not a real company database, authenticated service, policy authority, or production implementation.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`.
>
> **SOURCE:** [Identity Center multi-organization build plan `8](./post-apollo-identity-center-upgrade-plan-v0.md#8--worker-work-packages-and-dependency-plan); operator request 2026-10-31 to begin the first foundation work.
>
> **SCOPE / OWNERSHIP:** New isolated `services/identity/synthetic_policy_v0.py` and `tests/identity/test_synthetic_policy_v0.py` only; no modifications to Social, Hospital, login/auth providers or other workers' services.
>
> **CONNECTION:** External Hospital-compatible contribution; no verified live Hospital Room or Staff Role, no deployment.
>
> **VERIFICATION:** Synthetic test suite required; no live IdP/database/network/Quickshell acceptance.

## What this prototype proves

A fresh instance runs a **SQLite `:memory:` database** (never a disk file). It models immutable opaque identities for test persons, four isolated kinds of organization fixture records (two LLCs, nonprofit and unrelated customer), portfolios/participation, company memberships, divisions, geographic units, protected dummy records and time-limited action grants.

- **Portfolio membership is only a view.** It is not company ownership, nonprofit board status, identity federation or an automatic tenant permission. The portfolio listing only includes organizations where that person also has a separate active membership.
- **A resource belongs to one company.** SQLite composite foreign keys require the resource's functional division and geographic unit to exist within that same tenant.
- **Read or write requires an active organization membership AND a matching action grant.** Function- and geography-specific grants are intersected against stored resource attributes. An omitted scope means "all functions/units **inside this org only**".
- **No implicit manager/superuser rank.** All checks deny unless their exact action matches a grant. Cross-tenant and unrelated customer data remain isolated in fixtures.
- **Revocation, expiry, and bad IDs fail closed.** A revoked membership no longer exposes resources or portfolio entries. Expiry is exclusive and uses a test-supplied timestamp.
- **SQL parameters prevent strings being treated as query syntax.** Test-only seed operations rely on foreign key constraints; they are not authorized business mutations.

The prototype deliberately does **not** define a final persistence technology. Using SQLite `:memory:` for disposable tests does not select SQLite over PostgreSQL or any other production storage solution.

## Run the synthetic tests

From the repository root:

```bash
python3 -m unittest discover -s tests/identity -p 'test_*.py' -v
```

Tests use no network, device, secrets, installed IdP, company records or external libraries. Fixture-only actions are not exposed as a CLI or API. This suite proves **local policy semantics under test**, not that a remote API caller is authenticated or that a production server enforces those semantics.

## Explicit dangers and limits

1. The fixture's `seed_*` and `revoke_membership` methods are **trusted test setup**, not API endpoints; any caller with direct Python object access can write test data. Never route untrusted HTTP, QML or application input into them.
2. `allowed(principal_id, org_id, record_id, action, now=...)` assumes an upstream authenticated principal and trusted server clock, **neither exists here**. No frontend can use it as a security boundary. A future backend MUST authenticate the caller, derive principal/tenant context from verified credentials, and authorize in that trusted process.
3. This model is deliberately small: no actual board/owner governance, cross-tenant collaboration grants, approval/delegation, hiring lifecycle, hierarchical division/location inheritance, row-level audit, secure sessions, vault, credentials, or provider integrations. **Do not infer acceptance of any such unimplemented feature.**
4. The relationship `Portfolio → Organizations` is non-authoritative. A family relationship or platform operation does not grant rights in an LLC, nonprofit or independent customer's tenant.
5. A real service requires durable storage design, correct concurrent transactions, migrations, tenant query isolation, authN binding, grant administration, audit/revocation semantics, application-layer policy decisions, key management, resilience and review. This toy database must not be populated with production data or deployed as an API.

## Tests and acceptance for this narrow slice

- Organization A national Healthcare grant vs Organization B Maryland-only branch grant.
- Unauthorized access to unrelated customer and nonprofit records denied.
- Shared portfolio organization listing restricted to independently active org memberships.
- Revoke Organization A membership without affecting person's valid Organization B membership.
- Expired grants denied, exact action required, no accidental write/admin privilege.
- Matching **both** division and location required when a grant specifies both.
- Unknown or forged IDs denied, SQL injection-like record IDs treated as literal values.
- Composite foreign keys refuse cross-tenant resource reference and scope references.
- Organization-wide wildcard grant never extends beyond its organization.

**Next implementation milestone (separate assignment):** review stable record keys and relationship invariants, evaluate an IdP and data storage with separate security owners, implement a trusted API that binds an authenticated person to an authorized organization/function/location context and manages grants with auditable authority. Expand synthetic scenarios for cross-tenant partner agreements, governance, hierarchy, role lifecycle and revocation. Only then consider the management UI and provider account broker.

## Hospital-compatible handoff

### IMPLEMENTATION
Isolated in-memory synthetic tenant + permission evaluator and its tests, no production path.

### HOW TO USE
Run the test command above or inspect fixture source. No actual company records or credentials.

### VERIFY
Offline test results and GitHub commit required. Live desktop/IdP/security audit still not done.

### WATCH OUT FOR
Test seed methods are intentionally unprotected and are **not** business APIs. No user identity is verified by this fixture. External customer and nonprofit scope separation is essential.

### CHECKLIST
- [x] First bounded code slice created without changing current Social
- [x] SQL schema and positive/negative permission tests authored
- [ ] Synthetic test run and CI green on exact GitHub head
- [ ] Independent schema/security review
- [ ] Operator accepts this narrow slice as a foundation
- [ ] Authenticated backend implementation separately assigned

### NEXT
Run/tests → review tenant relationships and missing authorization cases → design separate trusted API with IdP integration and durable DB candidate.

### DECISIONS
Synthetic in-memory SQLite fixture only; zero real company identity, session, account or credential actions. System-of-record technology, authentication, API shape and policies remain undecided.
