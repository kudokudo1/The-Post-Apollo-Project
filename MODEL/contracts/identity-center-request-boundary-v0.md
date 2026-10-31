# Identity Center // verified-session request boundary v0 (synthetic)

> **STATUS:** EXPERIMENTAL OFFLINE REQUEST CONTRACT. Not a deployed HTTP server, real identity provider (IdP), login, approved key store, production API, or security certification.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`
>
> **SOURCE:** [Identity Center v0.2 foundation build plan](./post-apollo-identity-center-upgrade-plan-v0.md), following the merged [synthetic tenant/permission gate v0](./identity-center-synthetic-gate-v0.md).
>
> **SCOPE:** New isolated `services/identity/synthetic_request_boundary_v0.py` and `tests/identity/test_synthetic_request_boundary_v0.py`. Do not wire the class into Quickshell, Social, an HTTP listener or real company information.
>
> **OWNER / HOSPITAL:** New Identity Center experimental contract seam, external Hospital-compatible contribution; no verified live Room, Staff Role or production ownership.
>
> **VERIFY:** Offline static and CI test suite only. No real token-signature/introspection validation or security audit has happened.

## What changes from the previous fixture

The previous `SyntheticPolicyStore.allowed(principal_id, org_id, record_id, action, now)` accepts a principal ID supplied directly by a trusted caller. That is **unsafe to expose as an API** until authentication has established the principal.

This next fixture creates a read-only **request boundary**:

1. A synthetic request includes `accessToken` and the requested tenant/resource/action, **not** an authoritative person/role identity.
2. The boundary consults an **injected trusted `SessionVerifier`**. The test verifier recognizes only pre-seeded opaque fake session strings; real IdP integration is **not implemented**.
3. The boundary checks verifier output against configured issuer, audience, authenticated principal, session identifier, issue/expiry times and its own trusted clock. It does not accept a client-provided timestamp, principal, role, membership or permission.
4. Only the verified person's ID reaches the existing `SyntheticPolicyStore`, which independently checks **actual tenant membership + exact action grant + optional division/location intersection + expiry**.
5. Failures return a generic `{"status": "DENIED"}` without exposing credentials, exceptions, SQL or internal account information. The fixture emits no logs.
6. `listPortfolioOrganizations` produces a list only if a session is verified, and each organization still requires the user's own separate active membership. A portfolio label is not authorization.

### Accepted request shapes (examples; synthetic only)

```json
{
  "schema": "post-apollo.identity.synthetic-request.v0",
  "operation": "authorizeRecord",
  "accessToken": "opaque-test-session",
  "organizationId": "llc_a",
  "recordId": "health_md",
  "action": "records.read"
}
```

```json
{
  "schema": "post-apollo.identity.synthetic-request.v0",
  "operation": "listPortfolioOrganizations",
  "accessToken": "opaque-test-session",
  "portfolioId": "family"
}
```

Each operation uses an **exact, closed field set**. Adding `principalId`, `role`, `now` or another client-supplied authority claim fails closed. No create/update/grant/worker action exists.

## How to test

```bash
python3 -m unittest discover -s tests/identity -p 'test_*.py' -v
```

Both the previous tenant tests and the request-boundary tests execute with **only Python standard library**, using in-memory SQLite, synthetic workers/organizations and fake opaque sessions. They don't bind ports, contact any site, load real credentials, read existing application sessions or persist any data.

## Boundaries that must not be crossed

- The `VerifiedSession` dataclass is **not an unforgeable credential**. Anyone who controls the injected verifier can authorize anything. In a real deployment, only the protected backend initializes the verifier and validates IdP-issued signed tokens/introspection against trusted issuer/audience, expiration, revocation, signing keys and key rotation.
- The test verifier is deliberately fake, not a homemade authentication product. Do not ship or expose it as an identity provider, replace the real IdP with a static token table, or treat a client-filled principal ID as verified.
- `SyntheticRequestBoundary.handle()` is an **offline Python function**. It is not an HTTP endpoint or network service. A real transport needs TLS, request size/flow limits, secure session binding, proxy trust constraints, authentication policy, replay/revocation behavior, auditing, durable database and host threat review before use.
- The fixture's caller can directly access its policy object and seed data: it is **not sandboxed** or robust against untrusted Python running in the same process. Do not import into a UI process that executes arbitrary plugins and claim it is a security boundary.
- The tenant policy remains synthetic and uses its test-supplied resource names/roles. No actual governance, role-grant write authorization, company enrollment, HR records, partner agreements, provider accounts or secret storage exists.
- Generic denials protect status enumeration but are not production incident diagnostics. A real API needs a reviewed, private audit trail without secrets.

## Acceptance tests for this slice

- Known fake token and valid membership+grant grants a **read-only authorization decision**.
- Unknown, missing, malformed or revoked token fails closed; issuer/audience/issue/expiry mismatch fails closed.
- Tokens from a different company cannot be used to access a company for which no membership/grant exists, even if the request selects that org.
- Client-supplied `principalId`, `role` or `now` is rejected rather than trusted.
- A portfolio view remains independently membership-constrained; it does not expose private nonprofit/customer resources.
- Expired sessions, verifier outages, bad server clocks and unexpected fields result in generic denial.
- A per-tenant membership revocation does not delete the person's other organization membership/session.

**Not accepted by these tests:** real session authenticity, public HTTP safety, durable policy transactions, IdP recovery, vault storage, security certification, Quickshell behavior or operator desktop acceptance.

## Recovery and next owner seam

No user data or local files are created by this PR. Rollback is excluding/reverting the bounded GitHub PR before any future integration, leaving the merged `SyntheticPolicyStore` unchanged. No seeded token or real credential is migrated or revoked.

**NEXT (separate authorized work):** compare real IdP providers and verification libraries, design trusted backend API/transport and session lifecycle, design grant administration/audit and durable multi-tenant schema, then run end-to-end test IdP validation with expired/revoked/forged tokens. Keep UI, provider broker and worker onboarding outside this request-only slice.

## HOSPITAL-COMPATIBLE HANDOFF

### IMPLEMENTATION
Synthetic request adapter verifying an opaque session through an injected test-only verifier before invoking the previously merged tenant grant evaluator. No production network.

### HOW TO USE
Run the test discovery command, inspect the accepted field shapes and read the trust-warning section before attempting a real integration.

### VERIFY
CI result plus exact commit required. Never equate in-memory verifier tests with genuine IdP validation.

### WATCH OUT FOR
The verifier/test tokens are not production authentication. The injected verifier and clock must be protected backend dependencies. Do not wire this into an untrusted UI process.

### CHECKLIST
- [x] Read-only synthetic boundary and negative tests authored
- [ ] All identity tests and exact-commit GitHub CI pass
- [ ] Independent security review of trust boundary
- [ ] Real IdP, durable DB and API host ownership decided
- [ ] Operator accepts this separate slice and authorizes next implementation

### NEXT
Review backend/IdP options and durable tenant/role grant design; leave Social/UI untouched.

### DECISIONS
Proposed standard-backed authentication via a future external IdP. No IdP, deployment host, production security trust or key custody adopted by this experiment.
