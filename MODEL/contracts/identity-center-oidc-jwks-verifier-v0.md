# Identity Center // offline signed JWT / trusted JWKS verifier v0

> **STATUS:** Experimental source and CI-only signed-token validation adapter. **NOT** a live OIDC deployment, JWT authorization server, production OAuth login, identity provider, employee account store, or approved secure API.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`.
>
> **SOURCE:** The operator's request to continue the [multi-organization Identity Center plan](./post-apollo-identity-center-upgrade-plan-v0.md) after merged [synthetic tenant gate](./identity-center-synthetic-gate-v0.md) and [verified-session request contract](./identity-center-request-boundary-v0.md).
>
> **WORK SCOPE:** New isolated `services/identity/oidc_jwks_verifier_v0.py`, dependency pin, test suite and CI. Existing Social widget, Hospital, native account managers and local credentials remain untouched.
>
> **OWNER/CONNECTION:** Experimental Identity Center security seam; external Hospital-compatible contribution. Live Hospital Room / Staff Role / Assignment not verified.
>
> **VERIFY:** GitHub CI on exact branch/head is required. No real IdP, key registry, network, login, server, audit, risk evaluation or production account credentials are involved.

## Mechanism

The existing `SyntheticRequestBoundary` accepts a `SessionVerifier` and passes its verified principal to the tenant policy gate. The earlier tests used fake opaque string sessions without cryptography. This slice supplies a **real cryptographic signature verification implementation** using the pinned `PyJWT[crypto]==2.15.1` library, with keys created in test memory.

```text
[ Synthetic signed JWT ]
          |
          v
[ Fixed RS256 and pinned, trusted public JWKS ]
  -> signature / issuer / audience / expiry / not-before
  -> required subject, session id, token id
  -> denylisted session/token lookup
          |
          v
[ VerifiedSession ] (NOT an unforgeable capability by itself)
          |
          v
[ Previously merged SyntheticRequestBoundary ]
          |
          v
[ Previously merged tenant + division + branch gate ]
          |
     ALLOWED / DENIED
```

The verifier is **offline**: it never downloads or auto-discovers JWKS. A future protected backend must obtain issuer metadata and keys through an operator-approved trusted configuration/refresh path with HTTPS validation, limits, outage handling and rotation. **Never trust token `jku`, `x5u`, embedded `jwk` or any user-provided key.**

This experimental policy accepts only:
- An exact configured HTTPS issuer and API audience.
- 1–8 **explicitly configured public RSA keys** with unique `kid`, `kty=RSA`, `use=sig`, `alg=RS256`, minimum 2048-bit modulus and exponent 65537. No private key fields and no key URLs.
- Access tokens with JOSE header containing only `typ=at+jwt`, `alg=RS256`, and a pinned `kid`. Fixed allowed algorithm is **not** taken from attacker-supplied headers.
- Signed `iss`, `aud`, `sub`, `sid`, `jti`, `iat`, `nbf` and `exp` claims, strictly typed subject/session/token IDs, maximal 900-second lifetime by default, and no expired or future-issued token.
- A trusted server-side revocation checker, invoked once and **fail closed** if invalid or unavailable. This fixture supplies a test-only revocation set; no production revocation service exists.

**Provider compatibility is not assumed.** Some identity providers issue tokens with different `typ`, `sid` or `jti` formats or opaque tokens. They require a separately reviewed adapter/introspection path, not disabling authentication gates. JWT validation by itself cannot provide comprehensive logout/revocation without trusted issuer/session state.

## How to test

On CI, the workflow installs the isolated dependency and runs:

```bash
python3 -m pip install -r services/identity/requirements-jwks-verifier-v0.txt
python3 -m unittest discover -s tests/identity -p 'test_*.py' -v
```

This is a **developer/test-environment instruction only**. Do not install it on the operator's live desktop without approval. Test code creates ephemeral RSA signing keys entirely in memory, signs synthetic tokens, rotates public keys and checks invalid signatures, header confusion, expiry, missing claims, revoked sessions, account scope and request-boundary integration. No test requires an external login or actual employee identity.

### Threats exercised

- Forged tenant/role fields in a correctly signed token do not grant tenant access: the server policy still enforces membership and per-division/location action grants.
- Wrong RSA key, unknown `kid`, no key, expired key profile, altered header, `alg=none`, and HS256/RS256 confusion are rejected.
- Wrong issuer/audience, incorrect token type, token-provided key URLs/embedded JWK, absent/invalid claims, bad clocks, long-lived tokens and revoked sessions fail closed.
- Authorized access to an LLC can be revoked without revoking unrelated company memberships; a separate customer's token cannot read family-portfolio data.

## Security and production caveats

1. These tests create private RSA keys **inside disposable CI fixtures** to simulate a real signature. No real IdP private key is stored, managed or accessed. Signature validation is delegated to PyJWT and the installed `cryptography` backend, not invented RSA.
2. No OAuth authorization code + PKCE login, OIDC discovery, device login, passkeys, MFA, IdP selection, real token issuance, JWKS refresh, rate limiting, public API, TLS, DB migration, audit, secret vault, consent or real company enrollment has been implemented.
3. The caller can inject a fake verifier, override server clock and mutate the in-memory policy object. This means **no untrusted code can treat the offline Python classes as a trusted security service**. The eventual real backend must own these dependencies and isolate them from UI/plugins.
4. A revocation callback is injected; a production system needs a protected, durable per-tenant/per-session revocation authority and tested IdP logout semantics. Trusted signing keys must be loaded from approved configuration and rotated without accepting token-supplied network locations.
5. `PyJWT[crypto]==2.15.1` is **only a pinned candidate library for the isolated CI harness**, not approval of a production dependency or authentication architecture. Reevaluate advisories, dependencies, issuer token shape and library versions before deployment.
6. Do not handle real worker names, passwords, tokens, nonprofit/healthcare information, live provider sessions, or organization records in these tests. Synthetic fixtures are deliberately isolated.

Library references: [PyJWT 2.15.1 API](https://pyjwt.readthedocs.io/en/stable/api.html), [JWT Best Current Practices, RFC 8725](https://www.rfc-editor.org/rfc/rfc8725), [JWT Profile for Access Tokens, RFC 9068](https://www.rfc-editor.org/rfc/rfc9068), [OAuth Native Apps, RFC 8252](https://www.rfc-editor.org/rfc/rfc8252).

## Recovery, ownership, and next gate

Files are additive on a separate GitHub PR branch. No local machine, Social UI or production state changes need reversal. To roll back, do not merge or revert this self-contained verifier slice; existing merged synthetic policy/request fixtures remain unchanged.

**NEXT:** review real IdP choices and token shape, the protected backend boundary and trusted JWKS fetch/refresh protocol; then implement a **separate bounded disposable issuer/login integration** plus persistent revocation/audit and tenant API gate. Confirm actual Hospital Team/Room ownership before cross-service integration.

## HOSPITAL-COMPATIBLE HANDOFF

### IMPLEMENTATION
Experimental signed JWT verifier adapter with pinned public JWKS, fixed RS256, strict issuer/audience/claims checks, revocation lookup and synthetic request-gate compatibility.

### HOW TO USE
Follow the test workflow in an approved isolated development environment. Never add real secrets or live provider accounts to fixtures.

### VERIFY
CI test result + exact head SHA required. No real IdP validation or runtime acceptance claimed.

### WATCH OUT FOR
The library verifies signatures, but trust in key ownership, key rotation, host isolation and revocation still needs a real backend. Do not make signed-token tests equal "production login done".

### CHECKLIST
- [x] Authentication source contract and trusted-key ownership documented
- [x] Signed-token verifier and synthetic negative tests authored
- [ ] CI passes on exact head and security review completed
- [ ] IdP, JWKS refresh and protected service host selected
- [ ] Real sign-in, logout and revocation tested before production

### NEXT
Review API/IdP provider options and replace test-only key/session state in a separate authorized implementation lane.

### DECISIONS
Provisional offline RS256 + trusted JWKS access-token profile and pinned PyJWT CI candidate. **No deployment, IdP vendor, real account, tenant or provider-login authority selected.**
