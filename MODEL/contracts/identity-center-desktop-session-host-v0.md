# Identity Center // native privileged session host contract v0

> **STATE:** Experimental offline host-owned state machine, NOT a runnable OAuth service or approved production desktop login. No network listener, real token exchange, credential file, company identities, or Social QML wiring.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`
>
> **SOURCE:** Operator-directed continuation after PR #1000 (tokenless desktop display projection) merged into main. Also follows real disposable Keycloak CI pilot #995 and read-only persisted context API #990.
>
> **SCOPE:** New `services/identity/desktop_session_host_v0.py`, `tests/identity/test_desktop_session_host_v0.py`, isolated CI, this indexed design/verification contract. No edits to the existing Social widget, user stores, provider-specific messaging clients, Identity Center WSGI APIs or existing cryptographic verifier.
>
> **HOSPITAL:** Browser/ChatGPT acting as external Hospital-compatible contributor, without verified live Staff Role, Room, Assignment, active Hospital session or local desktop attachment.

## What happens in memory

A real desktop sign-in needs a distinct **privileged host process**, because JavaScript/QML and Social layout data must not hold a company access token. This stage defines a strictly bounded *Python host state machine* and its test doubles:

```text
[ future trusted desktop host process ]           [ Social UI ]
   - pinned HTTPS issuer/config                     |
   - trusted system browser launcher                |  read-only
   - callback listener at 127.0.0.1                 |  display snapshot
   - real HTTPS code+PKCE exchange                  |  NO access/refresh tokens
   - signed ID JWT validation                       |  NO OAuth callbacks
   - secure token custody / logout                  |  NO tenant authority
   - pinned HTTPS API GET /v0/me/contexts           |
             |                                      ^
             v                                      |
[ DesktopSessionHost (this PR; test-only orchestration) ]
   generates random S256 PKCE code verifier, state, nonce
   constructs one issuer-pinned auth URL for injected browser launcher
   consumes a one-time callback containing code/state/iss
   validates exact loopback redirect URI and expected issuer
   delegates code exchange and SIGNATURE verification to injected trusted host
   requires signed ID token attestation, nonce, client, issuer, bounded expiry
   keeps only a short-lived access token in private in-process host state
   calls injected API requester with bearer exclusively inside host
             |
             v
[ merged DesktopContextProjection ]
   validates versioned membership response
   strips any extra credential/identity fields
   fails closed on server or session errors
   clears on stale snapshot, time rollback, expired display grant
   returns only copy-only Organizations data and canSwitchOrganization=false
             |
             v
[ future approved one-way host -> UI display channel (NOT BUILT) ]
```

The host's `start_login()` returns only `{"status":"LOGIN_PENDING"}`. It does **not** return the authorization URL, nonce, state, PKCE verifier or any credential to the widget. The injected browser-launch callback receives the generated URL inside the privileged host only.

The callback `complete_callback()` is exclusively for the *future approved loopback receiver*, not arbitrary Social QML. It accepts an exact URL `http://127.0.0.1:<pinned-port>/callback?code=...&state=...&iss=...` with exactly those fields, validates CSRF state, issuer mix-up protection, maximum 5-minute lifetime, and consumes pending state before calling the exchange. Replays and duplicate/extra query parameters are denied. It does not start that listener or select/register the port.

The `exchange_and_verify` callback is required to return a `VerifiedCodeExchange` attestation with successful **cryptographic OIDC ID-token signature**, issuer/client audience, nonce, subject, access-token type and expiry. This dataclass is only a receipt from a *trusted callback*, **not a verifier**. An attacker-controlled callback can lie; the production host must own and verify real trusted HTTPS discovery/JWKS and token exchange separately. No refresh token is retained; this initial stage only supports short-lived access tokens in memory.

The `api_get` callback likewise belongs solely to the privileged host. It must later use an allowlisted HTTPS API URL and TLS verification to send the bearer as an HTTP Authorization header; QML must not receive the header, host object or callback. This stage does not implement transport, account storage or process isolation. The stored bearer is **only inaccessible if the host actually runs isolated from UI**. No security isolation can be claimed while this object and QML share a Python process.

## Why this separation matters

- Local Social `identity-N` or a selected portfolio is never a trusted person and cannot authorize a business operation.
- Authentication only proves a validated *provider subject*. A durable `(issuer, subject)` mapping and current independent tenant grants are still required in the Identity Center API.
- The display snapshot contains only authorized organization ID/kind and scope *previews*, never tokens, subject, session or a write capability. It cannot authorize any action by itself.
- Authorization code is protected with RFC 7636 S256 PKCE and one-time state; OIDC nonce and issuer mix-up countermeasure are checked. See `RFC 8252` (native external browser and loopback redirects) and `RFC 9700` (OAuth Security BCP) for production-review requirements.
- Logging out clears local pending login, bearer and display. **It does not make an IdP logout/revocation call**; this must be implemented by a separately reviewed production host. Expiry checks reject old tokens, but true session revocation continues to depend on the server.
- Returning `SIGNED_IN` is a host-local test acknowledgement of verified exchange, not a UI login indicator nor a deployed authentication endpoint.

## Offline tests and workflow

[CI workflow](../../.github/workflows/identity-center-desktop-session-host.yml) checks the new host and existing projection/UI contracts.

```bash
python3 -m unittest discover -s tests/identity -p 'test_desktop_session_host_v0.py' -v
python3 -m unittest discover -s tests/identity -p 'test_desktop_context_projection_v0.py' -v
python3 -m unittest discover -s tests/messaging -p 'test_identity_center_desktop_display_v0.py' -v
```

The host test injects fake browser/verified-code-exchange/API callbacks with synthetic credentials **only inside a disposable test process**. It checks callback source, state, issuer and field whitelisting, one-time replay refusal, expiry, wrong nonce, fake signatures, invalid token type/length, sign-out, clock rollback, API failure, and token never reaching the display result. These tests cannot prove the security of a later actual browser receiver, network client, token verifier, OS keyring, host isolation, or UI IPC.

## Rollback and follow-on seam

Revert only the new host/test/workflow/contract/index, or leave the draft PR unmerged. There is no runtime service, browser window, SQLite migration, company credential, employee account, or desktop file to clean up.

**NEXT, separately scoped approval/review:** secure host deployment model and isolation; exact system-browser PKCE callback listener with OS port ownership, hardened loopback receiver, PKCE token exchange and real signed ID validation, allowlisted HTTPS IdP/API trust, OS credential custody and revocation, locking and process lifecycle; a secure read-only IPC push to the existing QML `organizationDisplaySnapshot`, clearing it on logout, suspend, revocation and host death. Before **any** actual organization switch, API must verify current grants on each operation.

## HOSPITAL-COMPATIBLE HANDOFF

### IMPLEMENTATION
Host-only OAuth authorization-code/PKCE state and callback verification, short-lived in-memory access token custody, tokenless context projection integration. No executable listening service.

### HOW TO USE
Review the draft PR and test results. Normal Social USER // SETTINGS still shows NOT CONNECTED. No local user action can sign in using this module yet.

### VERIFY
Run exact-head GitHub CI. Check independent security audit and later real browser/native-host test separately. Avoid treating fake callbacks as trusted real identity.

### WATCH OUT FOR
This is not a production privileged process. The injected cryptographic validator and network requester are not implemented by this module. QML has no link to it; no credentials, access tokens, endpoint selection or tenant role may be passed to QML.

### CHECKLIST
- [x] #1000 merged; upstream current main and concurrent PR ownership checked
- [x] Host-only S256 PKCE + one-shot issuer/state callback contract
- [x] Token never part of display snapshot
- [x] Negative security and lifecycle tests plus isolated workflow
- [ ] Exact-head CI green
- [ ] Production host isolation, trust, secret custody and remote revocation approved
- [ ] Live desktop and operator acceptance

### NEXT
Review CI and security gates; explicitly authorize a protected real browser/token host before implementation, then review a one-way display IPC boundary.

### DECISIONS
No real IdP, public API endpoint, persistent credentials, callback port listener, OS keyring, separate process, deployment, real company data, or production account created. UI and switcher unchanged.
