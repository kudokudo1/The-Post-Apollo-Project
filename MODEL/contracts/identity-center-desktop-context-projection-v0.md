# Identity Center // tokenless desktop context projection v0

> **STATE:** Experimental read-only adapter and staged Social Organizations display. No session manager, live QML-to-backend connection, real company membership, local installation, deployed API, or authority grant.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`
>
> **SOURCE:** Operator continuation after merged real-Keycloak-to-file-backed API pilot #995; earlier #990 persistent API and #981 existing Social USER // SETTINGS workspace are also on main.
>
> **OWNING SEAM:** `services/identity/desktop_context_projection_v0.py`, `tests/identity/test_desktop_context_projection_v0.py`, minimal display-only `widgets/messanger/IdentityCenterSettingsSections.qml` changes, `tests/messaging/test_identity_center_desktop_display_v0.py`, isolated CI and this index/contract.
>
> **HOSPITAL:** External Hospital-compatible contributor. No live Hospital Staff Role, Room, Assignment, ownership lease or operator desktop connection claimed.
>
> **VERIFY:** Exact-head source/contract CI plus later authorized interactive Quickshell verification. Neither CI nor this branch makes an employee able to log in.

## Actual memory, processes and trust ownership

```text
[ FUTURE privileged desktop identity host (NOT YET IMPLEMENTED) ]
    - system browser handles PKCE authorization/login
    - host owns bearer tokens, refresh, revocation and session lifecycle
    - host owns TLS validation, trusted API URL, error handling
    - host calls GET /v0/me/contexts using its private credentials
                                  |
                                  v
[ DesktopContextProjection (new Python class) ]
    - accepts ONLY host-returned status, media-type and bounded JSON bytes
    - validates exact versioned read-only membership schema
    - rejects duplicate keys, extra claims, invalid tenant IDs and stale grants
    - exposes only organization IDs/kinds/grant-display hints + portfolio IDs
    - erases previous organizations on denied/malformed/unavailable response
    - clears data when local trusted clock rolls back or 30 seconds elapse
    - canSwitchOrganization is ALWAYS false
                                  |
                                  v
[ read-only display snapshot object; no token or provider subject ]
                                  |
                                  v
[ FUTURE privileged UI transport (NOT YET IMPLEMENTED) ]
                                  |
                                  v
[ EXISTING Social USER // SETTINGS -> ORGANIZATIONS QML ]
    - optional organizationDisplaySnapshot defaults null
    - never directly starts an API request, reads credentials or stores data
    - if a valid display-only snapshot is supplied by the trusted host,
      it can render ID/kind/scope count without implying company authorization
    - otherwise stays "NOT CONNECTED // TRUSTED BACKEND REQUIRED"
    - organization switching remains DISABLED
```

The adapter does not import `requests`, access network/filesystem, launch subprocesses, accept bearer tokens in its public interface, or know the authentication provider. It receives an injected `host_fetch(): HostContextReply` callback and an injected trusted clock from an operator-reviewed owner process. **Those dependencies are not automatically trustworthy merely because they are Python callables.** This is a constrained *display projection*, not a security boundary against hostile code in the same process.

Nothing connects this class to the live QML process yet. The QML property may eventually be populated only through a separately accepted trusted host channel. A caller could counterfeit a display label inside its own desktop process; it could not obtain a record grant from this UI because this UI has no company-write/API actions. Never use a displayed organization or `scopeGrants` as a backend permission token.

## Safe response contract

The existing WSGI API emits `post-apollo.identity.context-summary.v0` after verifying an IdP token, matching `(issuer, subject)` to an internal person, and reading active scoped records. The adapter rejects any additional authority-looking fields, including `role`, `accessToken`, `principalId` and `sessionId`, and refuses malformed or oversized JSON.

On successful validation it creates:

```json
{
  "schema": "post-apollo.identity.desktop-context-display.v0",
  "status": "READY",
  "organizations": [
    {"organizationId":"llc_a","kind":"llc",
     "scopeGrants":[{"action":"records.read","divisionId":"health",
                     "unitId":"maryland","expiresAt":null}]}
  ],
  "portfolios": [
    {"portfolioId":"family","organizationIds":["llc_a"]}
  ],
  "canSwitchOrganization": false
}
```

States: `NOT_CONNECTED` (no host session/explicit disconnect), `READY` (verified response with organizations), `NO_MEMBERSHIPS` (recognized person with zero authorized memberships), `SIGNED_OUT` (401/403), `UNAVAILABLE` (bad schema, data, expired display grant, clock issue, transport or server outage).

All non-READY/NO_MEMBERSHIPS states expose empty organization and portfolio arrays. All returned structures are detached copies; the UI cannot mutate the internal Python snapshot. A successful projection expires after **30 seconds** without refresh. The UI may opt not to refresh during an outage, but invoking `snapshot()` after staleness or grant expiry will fail closed. A future live bridge must schedule its own bounded refresh and explicitly clear on logout/lock/suspend; this pilot does **not** schedule updates or create a background process.

The projection is intentionally strict: organization/portfolio IDs are bounded ASCII identifiers, kinds and actions are known fixture values, and portfolio IDs can list only organizations already present in active memberships. A future production contract needs explicit versioning/migration for expanded organization types, richer names, accessible labels, roles and IDs.

## Tests

The CI workflow [tokenless desktop projection](../../.github/workflows/identity-center-desktop-context-projection.yml) runs tests for the Python display model and existing Social Settings UI checks. The Python test's **fake privileged host** invokes the existing `ReadOnlyContextApp` with an in-memory bearer header inside a test closure; only the sanitized response reaches the adapter, and no bearer reaches Social QML.

Coverage includes real WSGI response structure, subject mapping and tenant filtering, revoked sessions and memberships, clock/grant expiry, 30-second staleness, no stale cache after bad responses, malformed and duplicate JSON, unexpected sensitive claims, portfolio escalation attempts, copy-only snapshots and no switch permission. The Social static tests protect the same Settings window, default Social Layout, no credential/process/network action and disabled switcher.

Run in CI or a separate approved test checkout:

```bash
python3 -m unittest discover -s tests/identity -p 'test_desktop_context_projection_v0.py' -v
python3 -m unittest discover -s tests/messaging -p 'test_identity_center_desktop_display_v0.py' -v
```

**These are not live Quickshell UI tests or production security certification.** In addition, the existing disposable real-Keycloak integration now exercises the tokenless projection across signed JWT authentication, persisted membership revocation and server logout. That is a real provider test only inside GitHub CI, not a production desktop session host.

## Recovery, implementation handoff and future security gates

Revert the new projection/test files, UI display-only additions, workflow, index and document, or leave the draft PR unmerged. No database migration, personal credentials, Social accounts, secrets, live local files, company records or deployed system requires rollback.

**NEXT (requires new scoped operator-approved contract):** implement privileged desktop identity host and session manager, system-browser PKCE redirect/nonce/state protection, platform credential storage/refresh/revocation, authenticated HTTPS host/API transport, a one-way UI presentation channel, live lifecycle invalidation on logout/lock and API revocation. Only then inject a validated display snapshot into Social. Company switching and per-action authorization require their own server-validated context design, not client-side property changes.

### IMPLEMENTATION
Read-only, tokenless Python display projection with explicit strict schema, fail-closed staleness and copy-only state; new optional QML display slot in existing Social settings.

### HOW TO USE
For review, inspect the PR and CI tests. The user-facing Social Organizations page **does not become connected** or display real company data on deployment of this slice alone.

### VERIFY
Check exact-head CI, then separate authorized interactive Quickshell assessment. Never mistake read-only display for backend access.

### WATCH OUT FOR
No actual desktop privileged host, bearer custody, native login, TLS client, account enrollment or UI IPC. The injected fake host in CI is not an authentication system.

### CHECKLIST
- [x] Rechecked #995/#990 merged and current GitHub code/ownership
- [x] Tokenless projection, strict bounds and staleness invalidation
- [x] Read-only QML display slot, default null and disabled switcher
- [x] Focused Python and Social source-contract tests
- [x] Extend disposable real-Keycloak end-to-end CI to validate tokenless projection
- [ ] Exact-head CI green
- [ ] Independent security/architecture review
- [ ] Operator acceptance and live Quickshell UI verification
- [ ] Separate approved privileged host, real sign-in and protected UI transport

### NEXT
Verify CI, review the host/session ownership architecture, and only then implement a properly protected session host and its one-way UI channel.

### DECISIONS
No production IdP, token vault, host endpoint, local service, SQLite schema migration, real organization account, provider login, or desktop integration activated. QML never receives tokens or authorizes companies.
