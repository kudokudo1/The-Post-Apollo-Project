# Identity Center // durable read-only membership API contract v0

> **STATE:** Experimental developer/CI pilot, no production database or running server. Test-only SQLite file in disposable runner and WSGI handler that *does not bind* ports itself.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`
>
> **SOURCE:** Operator requested continuation after UI navigation #981 merged. Read-only synthetic membership response PR #986 is **open and unmerged** at creation. This separate main-based PR is an independent candidate, not a silent merge or replacement for #986.
>
> **OWNING SEAM:** `services/identity/durable_context_schema_v0.sql`, `services/identity/durable_context_store_v0.py`, `services/identity/read_only_context_wsgi_v0.py`, `tests/identity/test_durable_context_service_v0.py`, CI and Model contract/index. Social QML, existing synthetic IdP verifiers, real account stores and Hospital code remain untouched.
>
> **HOSPITAL:** External Hospital-compatible contribution. No live Staff Role, Room, Assignment or local computer connection verified.
>
> **VERIFY:** Exact-head GitHub CI and independent review. Passing CI does **not** validate a real production IdP, transport, durable database governance or frontend acceptance.

## Actual data and process flow

The prior proof uses SQLite `:memory:` and fake session strings. This slice demonstrates that an **existing persisted SQLite file** can be read as a versioned, tenant-restricted membership context:

```text
[ GET /v0/me/contexts, Authorization: Bearer <opaque-test-session> ]
                            |
                 [ WSGI handler in CI only ]
                            |
                 [ injected session verifier ]
                - trusted backend clock, issuer, API audience
                - token subject from verifier, never request field
                            |
                 [ SQLite file: mode=ro ]
                - IdP issuer + subject -> internal principal
                - ACTIVE independent org memberships
                - unexpired per-org grant previews
                - portfolios joined through own memberships
                            |
           [ versioned, no-cache JSON context summary ]
                            |
             [ future Social Organizations reader ]
                        (NOT WIRED)
```

The WSGI module exports `ReadOnlyContextApp`. It does not start a daemon, choose a port, connect to Keycloak, or expose an administration API. Its test harness starts a disposable standard-library WSGI HTTP server on `127.0.0.1` with an automatically assigned port and then shuts it down. The test's verifier is explicitly fake. **Never run this as a public network API.**

## Durable schema candidate

The additive SQL candidate includes:

- `principals`: internal stable person key, **not** Social's `identity-N` label.
- `provider_subjects`: composite key (`issuer`, `subject`) mapped to an internal person. Identical subjects from different IdPs cannot be treated as the same principal accidentally.
- `organizations` and `memberships`: LLC/nonprofit/customer test kinds and independently revocable person-org relationships.
- `divisions`, `units`, `grants`: org-scoped action and optional division/location intersection, expiry. These are **preview data only** here. No write/admin endpoint exists.
- `portfolios`, `portfolio_members`, `portfolio_organizations`: management grouping only; cross-tenant visibility still requires independent active membership.
- `PRAGMA user_version=1` and foreign keys. Reader rejects unknown schema version and never creates/migrates a missing database.

Only test code creates/writes the fixture. API reader uses `file:...mode=ro` plus `PRAGMA query_only=ON` and opens a fresh read-only connection for each request. An independently authorized test writer can revoke a membership on disk; the next GET reflects that revocation.

**No production DB choice has been made.** SQLite is a compact way to verify durable subject mapping and SQL restrictions. Production concurrency, migrations, isolation, encryption, backups, reporting, retention, consent, monitoring, role administration, cross-region tenancy and PostgreSQL evaluation remain future decisions.

## Request/response

Request:

```http
GET /v0/me/contexts HTTP/1.1
Authorization: Bearer <test-access-token>
```

The client cannot supply company, portfolio, role, scope, clock or person in a query string or body. No POST/PUT/PATCH/DELETE exists. A real deployment needs a protected ingress and issuer-specific token verification (including signature, key lifecycle, revocation, trusted audience and session handling). Test responses return `401 DENIED` for unrecognized/expired sessions or unmapped IdP subjects, `400 DENIED` for query/body input, and `503 DENIED` for storage/verifier failures. A trusted, mapped person who simply lacks organizations returns an empty `200 OK` list.

Illustrative response with **synthetic fixtures only**:

```json
{
  "status": "OK",
  "schema": "post-apollo.identity.context-summary.v0",
  "organizations": [
    {
      "organizationId": "llc_a",
      "kind": "llc",
      "scopeGrants": [
        {
          "action": "records.read",
          "divisionId": "health",
          "unitId": null,
          "expiresAt": null
        }
      ]
    }
  ],
  "portfolios": [
    {
      "portfolioId": "family",
      "organizationIds": ["llc_a"]
    }
  ]
}
```

The response does NOT contain the external IdP subject, internal principal, access token, password, grant ID, HR personal data, or unrelated tenant listings. Scope grants are **NOT authorization receipts**. Any future operational data API must recheck the current action, tenant, division, location, membership, grant expiry and session.

Headers include `Cache-Control: no-store`, `Vary: Authorization` and `X-Content-Type-Options: nosniff`; no cross-origin credential access or cookie session is enabled. No key-selection or remote download is delegated to the client.

## Tests and reproducibility

CI [durable context workflow](../../.github/workflows/identity-center-durable-context-api.yml) uses standard-library Python, a `TemporaryDirectory`, file-backed SQLite and an injected fake verifier. No credential vault, local desktop, real organization, Keycloak process or third-party network connection.

```bash
python3 -m unittest discover -s tests/identity -p 'test_durable_context_service_v0.py' -v
```

Tests verify:
- Persistent data across new read-only connections and a new store instance.
- Stable issuer+subject mapping, including same subject from **another** issuer.
- LLC A/LLC B independent grants, nonprofit and external customer isolation.
- Portfolio association does not expose unjoined companies.
- Revoked memberships and expired grants reflected on later GETs.
- Known identity with no tenant returns empty success; unknown identity denied.
- Expired/revoked sessions, wrong issuer/audience, fake admin/company/role query, invalid bearer headers and credential leaks fail closed.
- No write HTTP methods, no storage creation/migration and standard no-store response headers.
- Actual test-only loopback HTTP request with real JSON response, never a public listener.

## Security and operation limitations

1. The injected verifier is controlled by test code. Neither the verifier nor the WSGI app establishes security against hostile Python running in the same process. WSGI can be hosted publicly by someone else, but **that is strictly prohibited until a separate production design, approval and review**.
2. This is not a selected production database architecture. No migration runner, write authorization, per-tenant key custody, audit event trail, invite/onboarding, revocation service, backup, lockout policy, or production secrets.
3. The WSGI test handler has no TLS, reverse-proxy trust configuration, request size/rate/resource limits, service identity, host hardening, observability, or distributed revocation. The only real HTTP listener is in a disposable test, bound to loopback.
4. A provider subject and a Social layout identity are fundamentally different. Do not map `identity-N` to internal people by string equality. A trusted, explicit account-link enrollment and audit is a separate needed workflow.
5. A company's appearance in `organizations` proves only active membership summary availability. `scopeGrants` is a display preview and may become stale instantly. Re-read grants server-side for real actions. Portfolio membership never implies grants.
6. Revocation tests use a **trusted test admin** directly writing SQLite. They do not demonstrate a reviewed admin/offboarding interface or auditability.

## Rollback and next worker seam

The PR adds isolated modules, SQL fixture, tests, workflow, contract/index. It does not change any existing API, Social QML, real provider account, machine service, or durable user DB. Revert the files or leave PR unmerged to roll back. All test DB files are deleted by CI temporary-directory cleanup.

**NEXT:** reconcile this durable candidate with PR #986's in-memory readMyContexts contract; security review and production IdP/DB/host selection; implement protected API with real signed provider sessions, TLS and audit; only then connect Social USER // SETTINGS Organizations to a read-only verified result. Keep organization switching unavailable until server-side selection validation exists.

## HOSPITAL REPORT

### IMPLEMENTATION
Separate file-backed membership/portfolio/subject schema, read-only SQL access and test-only WSGI GET current-user context.

### HOW TO USE
In CI, run the test command or inspect the PR. No operator UI or desktop changes. The test endpoint exists only during loopback testing.

### VERIFY
Require exact-head CI and follow with security review. No claim of deployed or production authentication.

### WATCH OUT FOR
This is a candidate transport/schema, not an approved backend; the authentication verifier is injected and fake in unit tests. No client-provided ID is allowed to assign company rights.

### CHECKLIST
- [x] Existing PR #986 and main/owners checked
- [x] Independent durable/read-only service seam
- [x] Test-only stable IdP subject mapping
- [x] Offline and loopback HTTP tests authored
- [ ] CI green on exact commit
- [ ] Independent security/architecture review and operator acceptance
- [ ] Durable production administration, IdP, audit and hosting decisions

### NEXT
Review and reconcile with #986; then protected real provider service integration and read-only Social consumer.

### DECISIONS
Experimental SQLite persistence and WSGI transport **only in tests**. No production DB, IdP, hosting, role admin, company data, real account enrollment or local machine changes.
