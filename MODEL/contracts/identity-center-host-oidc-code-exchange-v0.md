# Identity Center // pinned OIDC authorization-code exchange and signed ID token v0

> **STATE:** Experimental CI-only host adapter and real TLS/RS256 crypto fixture. Not a deployed Identity Center, secure operating-system service, selected production IdP, or permission authority.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`
>
> **SOURCE:** Operator confirmed PR #1463 merged and asked to continue. Main now contains the explicit host lifecycle, token-free read socket, and host-owned pinned HTTPS metadata/current-user context GET. This step adds the missing code-to-token and ID signature leg, not a QML login button.
>
> **TECHNICAL OWNERSHIP:** Identity Center trusted host; local Social labels and CPU++ are non-authoritative readers.

## Implementation: actual network bytes and trust flow

```text
[ operator-approved future isolated host ]
  pins HTTPS issuer, authorization endpoint, token endpoint, JWKS and
  public native client ID + CA trust + bounded timeout
  existing HostPinnedHttpsTransport
      |
      + GET exact pinned OIDC metadata and public JWKS over validated TLS
      |   issuer, auth, token, JWKS URIs must match HOST-pinned values
      |   response_type=code and PKCE S256 required
      |
[ HostOidcCodeExchange.from_pinned_transport ]
  installs only host-validated public RSA RS256 signing keys
  requires 2048-bit RSA minimum, e=65537, unique kid, key count <=8
  does NOT fetch keys from JWT header/jku/x5u or QML input
      |
[ existing DesktopHostLifecycle / DesktopSessionHost ]
  host's system-browser launcher receives S256 challenge, nonce/state
  existing one-use 127.0.0.1 callback validates code/state/iss
      |
[ HostOidcCodeExchange.exchange_and_verify ]
  POST to exact host-pinned HTTPS token endpoint, fixed form:
    grant_type=authorization_code
    code, code_verifier, client_id, redirect_uri
  TLS validates certificate and hostname; no redirects, proxy, custom URL,
  client secret, open redirect or credential logging
  finite <=64 KiB response; strict JSON duplicate-key failure
      |
  PyJWT/cryptography RS256 signature using HOST-pinned JWKS
  check issuer, exact client audience, nonce, sub, iat/exp and at_hash if given
  check lifetime against the protected host clock, max 900 seconds
  discard refresh_token and all provider-only extra fields
      |
[ VerifiedCodeExchange ]
  only short-lived access bearer + attested ID subject in host MEMORY
  DesktopSessionHost separately validates callback nonce/client/issuer/expiry
  host-owned API GET /v0/me/contexts with bearer using existing HTTPS transport
      |
[ DesktopContextProjection, private AF_UNIX read-only socket ]
  ONLY versioned, sanitized organization/scope display previews
  no access/refresh token, ID token, nonce, subject, capability or login command
      |
[ CPU++ → ID MANAGEMENT → CHECK HOST CONTEXT ]
  display only; **never grants/revokes organization access**
```

No network or file I/O occurs when `HostOidcExchangeConfig` or `HostOidcCodeExchange` is constructed (metadata/JWKS retrieval is an **explicit** classmethod call). A user, QML widget, local `identity-N` alias, signed JWT header or untrusted discovery response cannot choose a new network URL.

## Test confidence

A disposable test fixture binds to numeric loopback with a real short-lived self-signed `localhost` TLS certificate generated in GitHub CI. It uses an ephemeral RSA-2048 private key to issue actual RS256-signed ID JWTs. The synthetic IdP's POST endpoint enforces the received PKCE verifier against the browser's S256 challenge. The test initiates the existing real numeric-loopback OAuth callback receiver and then reads only the already-validated organization snapshot across the private Unix socket.

Test scenarios include accepted exchange with server-filtered membership, signature mismatch, wrong issuer, wrong client audience, wrong nonce, invalid access-token hash, expired/future claims, redirect refusal, wrong MIME/JSON, wrong lifetime/type, untrusted discovery metadata/JWKS, malformed code/verifier/redirect, certificate trust failures, host logout and host-loss invalidation. The JWT algorithm is allowlisted, not derived from the untrusted header. This tests **cryptographic correctness and HTTPS exchange behavior with synthetic data**, not live sign-in or a production identity provider.

Existing real Keycloak disposable CI tests are a separate pilot; they do not constitute a chosen vendor. Their response shapes may contain refresh tokens and additional claims. This adapter discards refresh tokens without persisting or using them. Vendor compatibility needs explicit integration tests against a separately approved issuer.

## Limits and security gates

This change does **not** implement service installation, systemd/user lifecycle, operating-system vault, protected process sandbox, production issuer selection, real accounts, server audit, roles/permissions writer, company switching, remote IdP logout or refresh-token management. The host exchange MUST be owned by an isolated process, not exposed as QML or a general-purpose request service. Existing private same-UID Unix socket is a display transport, not cryptographic identity attestation.

Signature-verified ID tokens prove the issuer authenticated a subject for the exact public client in this exchange; they do NOT prove the subject is a member/owner/employee of any organization. Business authorization is always independently enforced by the server on every operation. Access token is opaque to this adapter and must be validated against the API's independently configured issuer/audience/revocation policy before fetching memberships.

The production system additionally needs independent security review of issuer metadata/JWKS rotation, native loopback port registration and replays, HTTPS network trust, backend revocation, user-switch/suspend safety, token custody, audit and hardening.

## Hospital-compatible checkpoint

### IMPLEMENTATION
Host-only pinned code-post + RSA-signed ID verification callback, synthetic real-TLS/PKCE/JWT host-lifecycle test, workflow, and indexed handoff.

### HOW TO USE
Review code/CI. A future approved host can construct `HostOidcCodeExchange.from_pinned_transport(...)` and inject `.exchange_and_verify` into the already-existing `DesktopHostLifecycle`, and inject the existing `HostPinnedHttpsTransport.get_contexts` for read-only memberships. **No live UI integration or login activation follows merely from merging.**

### VERIFY
Check exact-head workflow and negative tests, then perform independent identity security review and issuer acceptance. Runtime/authenticated real account not verified.

### WATCH OUT FOR
No user secrets or production endpoints. Do not return a bearer or ID subject to QML. A read-only membership display cannot authorize account, role, grant or tenant actions.

### CHECKLIST
- [x] Merge status and source ownership preflight
- [x] Host-pinned metadata and signing key allowlist
- [x] Actual TLS POST and PKCE callback integration
- [x] RSA signature and issuer/audience/nonce/expiry checks
- [x] Token-free display and session cleanup
- [x] Dedicated CI and handoff
- [ ] Exact-head CI review
- [ ] Security owner production review
- [ ] Approved real issuer/client and isolated native host
- [ ] Operator acceptance for live sign-in

### NEXT
Verify all checks. Then design a separately authorized secure native host deployment and its explicit sign-in UI intent, server-side permission-check API, and revocation lifecycle. Never convert the experimental Context viewer into a login/role editor without those gates.

### DECISIONS
No selected IdP, no production credentials, no on-device writes, no deployment, no role management, no merge/activation without explicit operator authority. Local Social IDs remain unrelated to signed identities.

**Hospital:** External ChatGPT contributor using Hospital-compatible practice. No live Staff Role, Room, Session, Assignment or owner lease established. Source GitHub PR is the recovery pointer.
