# Identity Center // real disposable Keycloak authorization-code + PKCE pilot v0

> **STATUS:** EXPERIMENTAL CI INTEGRATION. Real Keycloak server in an isolated GitHub runner, **synthetic** user and organization data only. Not a production login system, service selection, permanent IdP installation, public endpoint, desktop feature or security certification.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`
>
> **SOURCE:** Operator-directed continuation of the [Identity Center build plan](./post-apollo-identity-center-upgrade-plan-v0.md), following merged synthetic permission, request, JWT signature and OIDC discovery prototypes (#964, #966, #967, #974).
>
> **OWNING SEAM:** Additive `services/identity/keycloak_loopback_pilot_verifier_v0.py`, `tests/identity/keycloak_pilot_fixture_v0.py`, `tests/identity/keycloak_real_oidc_pilot_v0.py`, isolated GitHub workflow, this contract and its index.
>
> **HOSPITAL:** External Hospital-compatible repository work, **no verified live Room, Staff Role, Session, or worker assignment**. No desktop, Social, employee identity, Vault, or actual company records are touched.

## Goal and actual mechanism

This is the first test against a **real software identity-provider server** rather than the prior in-memory fake issuer. Keycloak 26.8.1 is a disposable **evaluation candidate**, not a selected vendor or permanent service.

```text
[ GitHub Actions disposable runner ]
       |
       +-- Generates a temporary Keycloak realm
       |    - random test passwords, synthetic worker
       |    - public OIDC client with required S256 PKCE
       |    - disabled implicit/password grant
       |    - confidential API client only for introspection
       |
       +-- Starts real Keycloak 26.8.1 in Docker on 127.0.0.1:8080
       |
       +-- Exercises browser-equivalent form over a cookie-preserving
       |    test HTTP session (no actual visible Chrome browser)
       |      authorize?response_type=code, state, nonce, S256 challenge
       |      -> Keycloak username/password form
       |      -> short-lived authorization code
       |      -> token endpoint with the original code_verifier
       |
       +-- Retrieves real trusted issuer discovery + public JWKS
       |      -> signature verification, issuer, ID-token audience, nonce
       |      -> API-access-token audience and azp check
       |      -> authenticated introspection (active)
       |
       +-- Feeds real verified subject into existing synthetic
       |    organization/branch/division grant engine
       |      -> LLC A authorized
       |      -> unrelated nonprofit / customer denied
       |
       +-- Tests wrong PKCE verifier -> rejected
       +-- Revokes disposable Keycloak session via logout
       +-- Introspects old token -> inactive
       +-- Old token denied at the request boundary
       |
       +-- Destroys the container and test realm
```

### Why the Keycloak-specific adapter is isolated

The previous `OfflineJWKSVerifier` intentionally uses a strict RFC 9068-like `at+jwt` header profile. Keycloak may issue access tokens with `typ=JWT`, its own subject/session claims and client-specific audience. Disabling the original verifier's security rules to "make the test pass" would be a terrible architectural decision.

Instead, the **loopback-only** `LoopbackKeycloakPilotVerifier` supports only the exact test issuer `http://127.0.0.1:8080/realms/post-apollo-disposable`, the specific public client and protected API audience; it validates RSA signatures against the Keycloak JWKS published from the preapproved discovery endpoint. Its introspection callback queries the disposable Keycloak server each time to make post-logout denial observable. It produces the existing `VerifiedSession` contract for the unchanged `SyntheticRequestBoundary`.

**This is not production-ready cryptographic trust:** the test uses ordinary HTTP on loopback, a test-only signed-token profile and credentials provisioned in a disposable realm. A production host must use authenticated HTTPS, vetted JWKS refresh, persistent revocation, session management, audits, replay protections, proper user provisioning and security review. Keycloak remains a *candidate*.

## How CI executes it

The review branch adds [`identity-center-keycloak-real-pkce-pilot.yml`](../../.github/workflows/identity-center-keycloak-real-pkce-pilot.yml). On GitHub Actions it:

1. Installs only test dependencies `PyJWT[crypto]` and `requests`.
2. Creates a fresh CI-only realm file and random synthetic passwords in the runner's temporary directory. No actual user/organization credentials are committed or printed.
3. Starts a real Keycloak Docker image `quay.io/keycloak/keycloak:26.8.1` bound to `127.0.0.1:8080`, using development mode **only** for disposable CI.
4. Runs the real HTTP OAuth authorization-code + S256 PKCE test. The test uses a cookie-preserving HTML form client to drive Keycloak's login page, not the resource-owner password grant. It doesn't launch a graphical browser.
5. Validates wrong-verifier rejection, ID-token nonce, access-token signature and audience, confidential introspection, org isolation, Keycloak logout and inactive old token.
6. Runs the merged offline tenant tests, removes the container even on failure. No external company systems are contacted.

GitHub Actions must finish successfully on the **exact PR head** before the tests are called verified. Only a successful workflow run proves that Keycloak actually started and these interactions happened. Compiled files or source-level checks are not runtime evidence.

## Security and compatibility limits

- The CI account exists only inside a container. Its generated passwords and the confidential introspection client's secret are test-only, never production secrets. The importer creates the realm in the temporary runner directory and the container is deleted after CI.
- The test creates a public login client with `authorization_code` and **required S256 PKCE**. The offline client simulates browser form submission with an HTTP session; it is not a Post-Apollo UI and does not handle an actual personal login.
- The Keycloak admin bootstrap password is ephemeral and never used by the test to access real user accounts. Production must not run Keycloak `start-dev`, expose the admin console publicly or use HTTP for issuer requests.
- Keycloak's **confidential introspection** and API audience mapper are fixture-only. These are necessary for checking server-side session invalidation and ensure a signed token cannot automatically read a separate company.
- The CI logout uses Keycloak's legacy refresh-token logout POST only for this disposable test. Production logout must use reviewed RP-initiated / backchannel logout and revocation design.
- No OAuth callback web server, production browser redirect validation, rotating production key store, durable DB, worker onboarding, MFA, passkeys, Account Broker, Social UI, or production network path exists.
- Keycloak's `typ=JWT` access-token behavior is **not** a reason to treat an OIDC ID token as an API bearer token. The adapter pins API audience plus `azp` and performs additional live introspection. The ID token is checked separately using its client audience and nonce.
- GitHub Actions network access is used for **downloading test packages and the official Keycloak container image**. All actual login, token, JWKS and introspection requests are restricted by test code to loopback. Don't claim it is a zero-network test.

## Verification gates

- Keycloak container actually starts and real discovery metadata describes the expected issuer, authorization, token, JWKS and introspection URLs.
- A user submits a real Keycloak login form through a cookie-preserving session; a PKCE S256 authorization code exchanges for signed access, ID and refresh tokens.
- Wrong code verifier is rejected; response state and ID-token nonce are checked.
- Signatures and API audience checks succeed for Keycloak's real public keys; fake tenant-role claims cannot give the user unrelated organization access.
- Confidential introspection is **active** before logout and **inactive** after logout; previous access request is then rejected.
- All original synthetic organization tests remain passing, including tenant boundaries.
- No real human, company or Social credentials enter the test, and no desktop change or production deployment occurs.

## Recovery and next step

PR additions are isolated and reversible by leaving them unmerged or reverting the changed paths. No persistent account, database, client registration, real user session or on-device change needs rollback.

**NEXT (separate owner/permission gate):** evaluate IdP/host selection with operator/security owners; formalize a protected trusted API, production HTTPS and approved JWKS refresh; real signed identity mapping to durable tenant principals, auditable grant administration and revocation semantics; then native desktop authorization-code + PKCE using the external system browser. Real organizations and workers may be onboarded only after those are reviewed and accepted.

## HOSPITAL-COMPATIBLE REPORT

### IMPLEMENTATION
Real disposable Keycloak CI integration with synthetic worker, public PKCE client, real token/JWKS signatures, confidential introspection, synthetic tenant access checks and tested logout.

### HOW TO USE
Inspect GitHub CI and review the acceptance gates. It is **not** a usable Post-Apollo sign-in screen. No local setup or real credentials required.

### VERIFY
Use CI conclusion on exact PR head, not a fabricated success report. Live desktop, public API and real IdP ownership remain untested.

### WATCH OUT FOR
Keycloak is a *pilot candidate*, not adopted production technology. HTTP is restricted to CI loopback. The compatibility adapter is deliberately not reusable on a public network.

### CHECKLIST
- [x] Current upstream merged identity PRs and unrelated worker PRs checked
- [x] Disposable Keycloak fixture and real PKCE test implemented
- [x] Isolation and operator restrictions documented
- [ ] CI Keycloak integration successful on exact head
- [ ] Independent security review and operator acceptance
- [ ] Production IdP, API, storage, secret/role policy selected separately

### NEXT
Evaluate CI evidence; design production-capable authentication boundary under a separate approved assignment.

### DECISIONS
Only experimental Keycloak 26.8.1, CI-only authorization-code + PKCE, test-only confidential introspection and separate provider compatibility profile. No production hosting, user enrollment, company authority, vault, PKI or signing-key service selected.
