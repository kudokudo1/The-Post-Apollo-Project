# Identity Center // trusted OIDC discovery and signing-key rotation v0

> **STATUS:** Experimental **offline** provider-metadata/JWKS trust boundary. Synthetic disposable issuer fixture. No network fetch implementation, real IdP, browser sign-in, employee records, production trust, or service deployment.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`.
>
> **OWNING SEAM:** Isolated `services/identity` and `tests/identity` only. Existing Social, Telegram, Hospital, Quickshell, workflows and local sessions unchanged.
>
> **SOURCE:** Operator requested continued implementation after merged synthetic tenant (#964), verified-session request (#966) and signed-token verifier (#967) foundations. See [Identity Center master plan](./post-apollo-identity-center-upgrade-plan-v0.md) and [offline RSA verifier contract](./identity-center-oidc-jwks-verifier-v0.md).
>
> **HOSPITAL:** External Hospital-compatible contribution, no live Room, worker role, attached Session, or production owner verified.
>
> **VERIFY:** Test and CI output required. No actual account sign-in or internet communication should be inferred.

## What this builds

The earlier RSA verifier accepted a preconfigured set of trusted public keys. Real OIDC providers publish metadata (issuer, authorization/token endpoints, `jwks_uri`) and rotate signing keys. This slice implements an **explicit, guarded discovery snapshot**:

```text
[ Host-pinned HTTPS issuer and exact JWKS URI ]
                  |
         Host calls refresh()
                  |
                  v
[ Injected protected fetch_json(url) ]
          |                 |
          v                 v
[ Issuer metadata ]   [ Trusted JWKS ]
  - exact issuer       - public RSA keys only
  - fixed JWKS URI     - fixed RS256
  - HTTPS same origin  - no token-selected keys
  - code + S256 PKCE
          |                 |
          +--------+--------+
                   |
        Atomic validated snapshot
                   |
                   v
[ OfflineJWKSVerifier ] <- token, server clock, revocation status
                   |
          VerifiedSession
                   |
[ Existing SyntheticRequestBoundary ]
                   |
[ Tenant, division, branch grant evaluator ]
```

The test issuer returns metadata and JWKS from an **in-memory dictionary**, not a server. It can replace, remove, or poison signing keys to test rotation and failure without a third-party account or credential. The verifier only calls two fixed, preapproved URLs and does not use token-provided `jku`, `x5u`, or `jwk`.

### v0 rules (strict pilot, not universal provider support)

- Configure `issuer` and `trusted_jwks_uri` separately in trusted code; both must be HTTPS and the JWKS URI must have the exact issuer origin. Metadata `issuer` and `jwks_uri` must match byte-for-byte.
- The issuer metadata must advertise an HTTPS authorization endpoint and token endpoint on that same origin, an authorization-code response type, and S256 PKCE capability. No implicit flow or password grant is enabled.
- The verifier fetches metadata first, then **only** the preapproved JWKS URI. On invalid metadata/JWKS or fetch failure, the current key snapshot is cleared. The last good signing key is **not** kept indefinitely.
- Validated snapshots expire after a trusted-clock TTL (default 300 seconds, maximum 900). Without a current snapshot, even correctly signed access tokens are rejected.
- A refreshed key set can add a new key and remove an old one. Unknown `kid` never triggers a token-driven network fetch. Signature, audience, issuer, claim, expiration and session revocation checks remain inside the existing RSA verifier.
- This version intentionally restricts all endpoints to the issuer's HTTPS origin. Some legitimate providers use different endpoint origins or omit a metadata capability flag. Those need an approved compatibility profile, **not** bypassing the checks.

## Run offline tests

In a disposable developer environment with approved dependencies:

```bash
python3 -m pip install -r services/identity/requirements-jwks-verifier-v0.txt
python3 -m unittest discover -s tests/identity -p 'test_*.py' -v
```

The [CI workflow](../../.github/workflows/identity-center-discovery-rotation.yml) runs compile checks and the full identity suite. This task does not authorize installation on the operator's own machine. Test signing keys exist only in test memory.

## Trust and safety boundary

**Do not connect `fetch_json` to an arbitrary URL downloader and call it secure.** A future protected host MUST enforce approved exact endpoints, TLS certificate validation, redirect refusal, bounded response size, timeouts, proxy/DNS/SSRF defenses, network error handling and trustworthy key refresh scheduling. These transport mechanisms are **not implemented here**. A caller capable of injecting the fetcher, issuer, clock or revocation function can subvert this experimental interface.

The issuer fixture does **not** perform OAuth authorization, PKCE callback handling, user login, MFA, logout or token issuance over a network. Testing a signed JWT against mock OIDC metadata is **not** the same as integrating a real identity provider. The next worker must decide which IdP and token profile will actually be tested. The earlier strict `at+jwt`, `sid`, and `jti` access-token requirements may require an explicit provider-specific adapter without weakening the trust model.

An eventual production service also needs durable sessions and revocation, a recognized user subject mapped to a stable internal principal, correct cross-organization authorization, secure transport, key custody, audit logging, rate limits and incident recovery. This fixture has none of those.

## Acceptance checks

- Before successful trusted discovery, the API denies a validly signed synthetic token.
- Correct metadata and public JWKS produce a validated snapshot; a signed token is authorized only when the person has the required organization and resource grant.
- A tenant switch to an unrelated company or nonprofit fails despite valid issuer authentication.
- Bad issuer, swapped JWKS URI, insecure/foreign endpoints, missing code/PKCE metadata and malformed key sets fail closed.
- Rotating from key A to both A+B to B-only accepts only the keys currently published after explicit refresh.
- Refresh failure, expired cached metadata and revocation failure deny access without leaking claims, tokens or secrets.
- Portfolios remain filtered by separately granted organization membership, not by family or software-publisher status.
- No network, local machine, production credentials, Social session or real company records are involved.

## Recovery and next handoff

This is an additive, bounded PR. Rollback means not merging it or reverting the new source, test, workflow and link. Existing merged policy/request/JWT code remains independent. No user data or credentials require migration or cleanup.

**NEXT:** select a disposable **real** IdP for an isolated end-to-end authorization-code + PKCE pilot; verify issuer-specific token claims and signing-key distribution, then implement a protected HTTP transport/refresh service and session/audit authority. Do not run password-grant flows, ship an embedded fake IdP, connect real employees, or declare production login complete.

## HOSPITAL REPORT

### IMPLEMENTATION
In-memory OIDC issuer metadata/JWKS fixture, exact URL trust policy, atomic refresh, short-lived snapshot, forced denial on fetch/rotation failures, request-boundary integration.

### HOW TO USE
Review the code and CI. No live Post-Apollo UI or user operations exist for this fixture.

### VERIFY
Only offline test/CI results are applicable. Runtime provider integration remains untested.

### WATCH OUT FOR
`fetch_json` is an injected trusted transport contract, not a secure downloader. An in-memory issuer is not a real IdP. Do not enable public-facing authorization.

### CHECKLIST
- [x] Previous identity foundation and current GitHub ownership checked
- [x] Isolated discovery/key lifecycle code and tests written
- [ ] Exact-head CI green
- [ ] Independent security and provider compatibility review
- [ ] Real IdP/host/transport/credential decisions authorized
- [ ] Live employee login and server protections verified separately

### NEXT
Real disposable IdP evaluation and secure transport design as a separately bounded assignment.

### DECISIONS
Provisional strict same-origin HTTPS discovery, fixed JWKS URI, code+S256 metadata and fail-closed TTL. No production vendor, host, OAuth flow, key custody or legal-entity governance selection.
