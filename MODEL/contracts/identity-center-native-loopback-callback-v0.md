# Identity Center // Native loopback browser callback receiver v0

> **STATE:** CI-only transport prototype. No deployed daemon, registered system-browser login, real QML IPC, production issuer, real employee identities, credential vault or machine activation.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`
>
> **SOURCE:** Operator continuation after merged PR #1007 (privileged native host state machine), #1000 (tokenless display projection), #995 (disposable real-Keycloak end-to-end API), and #990 (durable read-only Organizations API).
>
> **SCOPE:** `services/identity/native_loopback_callback_v0.py`, `tests/identity/test_native_loopback_callback_v0.py`, isolated CI workflow and this Model contract/index. Existing Social QML, Identity Center host contracts, IdP verifier, account stores, user records and Hospital files remain untouched.
>
> **HOSPITAL:** External Hospital-compatible browser contributor; no verified live Room, Staff Role, Assignment or connected operator desktop.

## The missing runtime link

The existing `DesktopSessionHost` creates random state/nonce and S256 PKCE challenge, validates an expected callback, delegates cryptographic token exchange, and passes only a tokenless read-only Organizations projection to a future UI adapter. What it did *not* have was a browser-facing HTTP receiver on an owned native loopback port.

This PR adds a **separate, explicitly started** one-use receiver. It creates **no listener on import or object construction**, and cannot be restarted after closing. Only the CI test calls `start()`. It binds to numeric IPv4 `127.0.0.1` on an ephemeral OS-assigned port, advertises the resulting host-only `redirect_uri` to the privileged host before login, then disposes of the server after the test.

```text
[ future privileged native host, NOT DEPLOYED ]
   |
   +-- creates LoopbackCallbackReceiver but does not expose it to QML
   +-- explicitly binds 127.0.0.1:ephemeral
   +-- configures DesktopSessionHost redirect from bound server's actual port
   +-- launches system browser using host-generated authorization URL
   |
[ future IdP redirects browser to GET /callback?code=...&state=...&iss=... ]
   |
[ loopback HTTP handler ]
   - exact numeric host:port header
   - callback path and query length bound, GET-only, no request body
   - no credential-bearing request/response logging
   - atomic one-use callback consumption via threading lock
   |
[ host.complete_callback ]
   - one-use PKCE verifier, state and issuer validation
   - exchange and verified ID JWT are separate TRUSTED callbacks (not built)
   |
[ DesktopContextProjection ]
   - returns only display IDs/scopes and canSwitchOrganization=false
   - no bearer, authorization code, nonce, session or IdP subject
   |
[ future read-only host -> Social UI IPC (NOT BUILT) ]
```

An incoming browser callback **never sends** the authorization code, state, bearer token or provider subject back in the HTTP response body, headers, logging or a redirect. Successful completion gets only a generic confirmation. Invalid callback fields, unexpected methods, untrusted Host/Origin headers and replay are refused. Non-callback requests do not consume the login attempt. A routed first callback, even invalid, consumes the receiver's only opportunity: a malicious local process can therefore deny service by racing the user, but it cannot authenticate without the unguessable state and a valid code.

There is no automatic restart, privileged process sandbox, OS user isolation, browser launcher, token endpoint client, signed JWT verification, keyring, HTTPS API client, token revocation or remote logout in this PR. A locally hostile process can still connect to loopback and DoS a one-use flow. The handler uses Python standard-library `ThreadingMixIn` and `HTTPServer`: despite no-store headers, bounded callback length and no request logging, it is **not hardened against slow connections, resource exhaustion, or untrusted desktop code with shared process access**. Do not deploy it directly as the final desktop listener.

## Exact tests

The isolated [native callback CI workflow](../../.github/workflows/identity-center-native-loopback-callback.yml) compiles modules, runs the new Python tests, and retains existing host PKCE and tokenless projection regressions.

```bash
python3 -m unittest discover -s tests/identity -p 'test_native_loopback_callback_v0.py' -v
python3 -m unittest discover -s tests/identity -p 'test_desktop_session_host_v0.py' -v
python3 -m unittest discover -s tests/identity -p 'test_desktop_context_projection_v0.py' -v
```

The new test creates **real HTTP requests** to a disposable listener bound to `127.0.0.1` and uses an injected fake cryptographic exchange. It checks actual success and a sanitized read-only Organizations snapshot; strong PKCE state/nonce handoff; one-shot callback replay denial; wrong issuer/state; duplicate/extra callback fields; wrong Host/Origin, method or body; incomplete path; expiry; suppressed request logging; silent verification failure; no token leakage and switcher always disabled.

**Do not mistake this for live desktop verification or a real Keycloak test.** The already-merged #995/#1000 Keycloak workflow exercises real signed tokens and file-backed API *separately*. The next bounded step is to run a host-owned browser authorization-code flow through this receiver against a disposable real Keycloak instance, with an explicit test-only HTTP/HTTPS trust-policy distinction rather than loosening production host rules.

## Recovery

The new receiver has no local deployment, real account provisioning, DB migration or secret storage. Leave the draft PR unmerged or revert its isolated receiver/tests/workflow/docs/index. CI always calls `close()` on teardown; no persistent loopback port, process or real company data remains.

## HOSPITAL REPORT

### IMPLEMENTATION
Explicit one-shot browser callback receiver on temporary numeric IPv4 loopback, separate from the previous host state machine and UI. Host callback gets the URL, QML receives no credentials.

### HOW TO USE
Only in an isolated repository test environment; GitHub CI runs the suite. No existing desktop menu/button is activated by this source change.

### VERIFY
Check exact-head CI and targeted negative tests. Separate live desktop and real signed-token integration remain required.

### WATCH OUT FOR
No host process isolation, real browser, public TLS, token exchange, session storage or QML IPC. Callback failure can terminate an attempted login and loopback cannot resist hostile same-user processes. Never interpret `SIGNED_IN` test receipt or Organizations scope preview as authority to access a company record.

### CHECKLIST
- [x] Confirm #1007 merged; latest main and current PR ownership inspected
- [x] Isolated receiver/HTTP tests, existing host state unchanged
- [x] One-time callback, explicit startup and no request-URL logging
- [x] CI and recoverable handoff authored
- [ ] Exact-head CI success
- [ ] Disposable real-Keycloak browser callback end-to-end
- [ ] Independent security review, live desktop verification and operator acceptance
- [ ] Approved native process/secret vault/one-way UI IPC implementation

### NEXT
Verify CI → connect to disposable real-Keycloak PKCE test only → separately review production listener/process isolation and secure one-way UI channel → operator-accepted desktop integration.

### DECISIONS
This is a CI transport seam, not a production server or selected IdP; no real company accounts, host service, callback registration, credentials, local machine writes, UI switcher or deployment.
