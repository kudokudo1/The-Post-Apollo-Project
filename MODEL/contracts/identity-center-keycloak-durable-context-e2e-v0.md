# Identity Center // real disposable Keycloak to durable Organizations API v0

> **STATUS:** CI-ONLY experimental end-to-end evidence. No production deployment, permanent IdP, real employees or company database. This does not confer operator acceptance or authorize merging.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`
>
> **SOURCE:** Operator-directed continuation after verified and merged #986 (in-memory context summary), #990 (file-backed read-only WSGI context API), and #978 (disposable real Keycloak PKCE pilot). The Social settings UI from merged #981 remains unchanged.
>
> **OWNING SEAM:** New `tests/identity/keycloak_durable_context_e2e_v0.py` and a bounded amendment to `.github/workflows/identity-center-keycloak-real-pkce-pilot.yml`, plus this contract and MODEL index. No edits to the existing authentication verifiers, permission store, WSGI handler, Social UI, or Hospital files.
>
> **HOSPITAL:** External Hospital-compatible ChatGPT contributor. No confirmed live Staff Role, Room, Assignment or desktop connection.
>
> **VERIFY:** Requires GitHub Actions success on the exact PR revision. Static contracts and prior CI alone do not prove this new end-to-end behavior.

## Goal and data flow

Previously, one CI run proved real Keycloak code grant and token revocation against an **in-memory** synthetic policy; a separate run proved a **persisted SQLite** Organizations API behind an injected fake session verifier. They were not yet the same request path.

This new test exercises both **in the same disposable runner**:

```text
[ Real Keycloak 26.8.1 in isolated GitHub CI, loopback 127.0.0.1:8080 ]
             |
    [ Browser-form authorization code + S256 PKCE ]
             |
   [ Keycloak ID JWT, signed API access JWT, refresh token ]
             |
   [ Trusted Keycloak JWKS + issuer/audience/azp validation ]
             |
   [ Confidential real Keycloak introspection (active) ]
             |
   [ WSGI GET /v0/me/contexts at 127.0.0.1:ephemeral ]
             |
   [ issuer + signed token subject -> internal principal mapping ]
             |
   [ Read-only SQLite persistent file ]
       - active LLC A and LLC B memberships
       - LLC A division + geography scope-grant preview
       - LLC B membership with no grant
       - unrelated nonprofit and customer not disclosed
       - family portfolio filtered to independently joined LLCs
             |
   [ JSON Organizations summary, no-store ]
             |
   [ simulate trusted admin revocation in separate test SQLite connection ]
             |
   [ Next signed request loses revoked LLC, keeps independent LLC B ]
             |
   [ real Keycloak session logout -> introspection inactive ]
             |
   [ Same, still-cryptographically-signed JWT now HTTP 401 DENIED ]
```

The fixture is created only under a Python `TemporaryDirectory` in the CI runner. It is populated by a synthetic test administrator with `llc_a`, `llc_b`, `nonprofit`, and `unrelated_customer`; it maps the genuine *disposable* Keycloak `iss+sub` to a separate internal database principal only *after* an initial HTTP 401 verifies that unknown subjects are refused. The test revokes LLC A via a direct *test-only* SQLite admin connection and observes an immediate reduction in the subsequent API JSON.

## What this proves

- Authorization-code + S256 PKCE, real Keycloak-issued signed access token, ID-token nonce, issuer, API audience, authorized client and confidential introspection all participate before any organization data is returned.
- The API **does not create** a corresponding Post-Apollo principal automatically just because Keycloak issued a valid access token. Trusted mapping is explicitly needed.
- The persisted reader exposes only active, independently authorized organizations and **scope-grant previews**. Portfolio membership cannot grant access to unrelated nonprofit/customer data.
- Organization membership without a grant remains a visible membership with an empty `scopeGrants` list; **it does not grant record access**.
- Changing client query inputs `principalId`, `organizationId`, or `role` is refused. Mutation methods (POST) are rejected.
- The fresh read-only SQLite connection reflects a separate trusted test-side membership revocation on the next request, even with an unchanged valid token.
- A Keycloak logout makes the originally valid access token fail live introspection and the API denies the bearer on the next HTTP request.

The test prints no real token, password, provider subject or private record. It does not modify or create any real account.

## How to run

The amended [existing real Keycloak workflow](../../.github/workflows/identity-center-keycloak-real-pkce-pilot.yml) runs:

1. Create random test-only credentials and realm import in the GitHub runner's temporary directory.
2. Boot the official Keycloak 26.8.1 container with Docker `start-dev --import-realm` bound only to `127.0.0.1:8080`.
3. Execute the original PKCE/signing/log-out pilot.
4. Execute `python3 tests/identity/keycloak_durable_context_e2e_v0.py --fixture-dir "$RUNNER_TEMP/post-apollo-keycloak-v0"` using a fresh auth-code sign-in on the same disposable Keycloak realm.
5. Run existing offline Identity Center tests, then stop and delete the disposable Keycloak container even when a test fails.

A reviewable result requires the workflow name **Identity Center Real Disposable Keycloak PKCE Pilot** to finish successfully for the *exact* branch commit. The CI runner also needs Docker and to download the image and test dependencies. All actual auth and API requests remain on loopback; this is not a no-network test.

## Boundaries and next work

The **Keycloak-specific verifier is loopback-only**, intentionally hard-pinned to this test realm and client, and not usable as a public production security boundary. Keycloak is still an evaluation candidate, not a selected vendor. The WSGI handler's verifier and clock are injected by the test process, and the server uses ordinary HTTP on loopback. A production implementation requires reviewed TLS/proxy ingress, trusted provider transport, secure key refresh, durable revocation/auditing, replay and abuse protection, persistent organization administration and explicit authorization for actual data operations.

The synthetic direct SQL writer is **not** an employee onboarding/offboarding UI or approved production policy administration. The API `scopeGrants` list is a display-only snapshot, not a capability token. A valid UI organization selection alone must never authorize any privileged action.

**No Social QML changes.** `USER // SETTINGS → ORGANIZATIONS` remains disconnected and its organization switcher stays disabled until a production-worthy protected API and secure desktop session adapter are approved and separately verified. No local machine, employer, nonprofit, customer or personal social login was changed.

**Rollback:** leave the draft PR unmerged or revert only the new test/CI/doc/index entries. The previous merged IdP, WSGI and tenant prototypes remain unaffected.

## HOSPITAL-COMPATIBLE HANDOFF

### IMPLEMENTATION
Single disposable CI chain: real Keycloak PKCE -> signed/introspected JWT -> stable issuer+subject mapping -> SQLite file-backed read-only Organizations response -> independent membership revocation -> actual Keycloak logout -> API denial.

### HOW TO USE
Inspect CI and contract. No user-facing UI activation or real account registration exists; use no real credentials.

### VERIFY
Check exact-head GitHub Actions conclusion and log for PASS results. No live Quickshell or production authorization validation.

### WATCH OUT FOR
Experimental development-mode Keycloak on loopback HTTP and test-only read-only WSGI with an injected pilot verifier. No permanent service, SSL certificate, deployed database, audit trail, production admin API or vendor adoption.

### CHECKLIST
- [x] Verified #990 and #986 merged; current GitHub open PR seams inspected
- [x] Added real signed-token + file-backed tenant API end-to-end test
- [x] CI workflow wired and existing offline gates retained
- [ ] CI successful on exact head
- [ ] Independent security review and production host/IdP/DB decision
- [ ] Real, authenticated UI consumer authorized and tested

### NEXT
Review green CI, then define the independently authorized secure transport/desktop session adapter contract. Only after protected backend and security review should the Social Organizations panel read real signed-in context. Continue to disable actual context switching until current server grants are enforced per operation.

### DECISIONS
Keycloak remains CI-only candidate; SQLite file-backed reader and WSGI remain experimental; no production service, desktop installation, real users or organization grants.
