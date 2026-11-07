# Identity Center // explicit native host lifecycle composition v0

> **STATUS:** IMPLEMENTED ON GITHUB REVIEW BRANCH, CI verification and operator acceptance pending. No local installation, approved production trust roots, domain, IdP, real user, actual company account, running service, server-side permission mutation or privileged host isolation.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`
>
> **OWNER:** Identity Center owns protected session handling and verified scoped API requests. CPU++/Social consume token-free display snapshots only.
>
> **SOURCE:** Operator approved previous CPU++ read-only context PR #1456 and asked to proceed toward the separately protected identity host. PR #1456 was merged first; this work is a new separately reviewable milestone.
>
> **RECOVERY:** `services/identity/desktop_host_lifecycle_v0.py`, `tests/identity/test_desktop_host_lifecycle_v0.py`, workflow `identity-center-desktop-host-lifecycle-v0.yml`.

## Implementation: actual memory, threads, sockets and operations

The repository already had isolated pieces: `DesktopSessionHost` for PKCE state and short-lived bearer in host memory; `LoopbackCallbackReceiver` for an explicitly bound numeric `127.0.0.1` one-use callback; `PrivateContextSocket` for a bounded Unix-domain snapshot read; and `DesktopContextProjection` for strict, short-lived organization/scope display JSON.

This change composes them into **one host-owned object** `DesktopHostLifecycle`:

```text
[ Explicitly constructed host-owned object; NO auto-start ]
  Trusted HTTPS issuer, client, API audience + private 0700 directory
  injected host-only browser launcher, signed-token exchange,
  authenticated scoped API callback, trusted clock
                           |
                start() [EXPLICIT]
     +---------------------+----------------------+
     |                                            |
 [ 127.0.0.1 callback receiver ]       [ private 0600 AF_UNIX socket ]
  OS-selected port; once per host        only accepts SNAPSHOT\\n
     |                                            |
 begin_login() host-only                          |
  256-bit state/nonce, S256 PKCE                  |
  opens injected browser                          |
     |                                            |
 signed ID-token exchange inside host             |
  verified issuer, client, nonce                  |
  memory-only short-lived bearer                  |
     |                                            |
 host-only api_get(token) ------------------------+
  must independently verify HTTPS                 |
  and issuer/tenant grants                        |
     |                                            |
  DesktopContextProjection -> validated context-display.v0 JSON
     |                                            |
     +-------------------------------> PrivateContextSocket
                                       canSwitchOrganization=false
                                       no token, subject, role, login command
                                       |
                                       V
                                CPU++/Social read-only viewer
```

**No part of the display socket accepts OAuth codes, browser requests, passwords, user IDs, tenant selectors, role-change intents, or commands.** The loopback callback does not return the code, nonce or bearer to the web page. A valid callback is consumed once; retries require constructing a new explicitly started host object. Before login the display returns `NOT_CONNECTED`.

### Lifecycle and safety

- `__init__` only validates pinned configuration; creates no transport, process, file or browser and does not look at user-managed account settings.
- `start()` explicitly starts the callback receiver at an OS-chosen numeric loopback port and the preexisting private host-owned display socket. The caller **must provide a pre-existing 0700 directory**. No `mkdir`, systemd user service, keyring, config file or login side effect exists.
- `begin_login()` is callable only in the host Python process, never via the UI socket. It initiates a single injected trusted system-browser action. The real authorization endpoint and token verifier are **not supplied** by this PR.
- A callback must match the one-use receiver and the original S256/nonce/issuer/state contract. Calls are serialized against logout and snapshot reads using an owner-process lock.
- The host issues server-context requests through the injected `api_get(token)` callback, then returns only versioned, token-free validated organization and portfolio display metadata. If the API refuses, output is malformed, token expires or time rolls back, the host drops its local session and the display is empty. **No permission is granted by these previews**.
- `logout()` blocks late callbacks, clears the in-memory short-lived token and display. No remote IdP revocation/SSO logout is claimed.
- `close()` invalidates the session before closing sockets and listeners, and closes the listener outside the host mutex to avoid a shutdown deadlock. Unmerged code never starts automatically.
- Permission administration **is not implemented**. A future protected server must verify real issuer/subject, tenant role, current grant, request scope, audit, and revocation on every write. A local Social `identity-N` is not a person.

## What is deliberately absent

There is **no production HTTPS transport, IdP vendor choice, registered real client, secured issuer, signed token validator implementation, OS-backed secret custody, separate privileged host process, actual account login, company records, role editor, grant writer, runtime deployment, service unit, keyring, or production activation** in this PR. Injected test callbacks claim signed verification, but they are **synthetic test doubles, not proof of production trust**.

Private IPC's `SO_PEERCRED` check protects against other OS users, not malware with the same UID. Tokens are only isolated from QML when a separate trusted host process actually owns the Python object; this composition must be hosted in such a process and security-reviewed before production use.

## Verification

```bash
python3 -m unittest discover -s tests/identity -p 'test_desktop_host_lifecycle_v0.py' -v
python3 -m unittest discover -s tests/identity -p 'test_desktop_session_host_v0.py' -v
python3 -m unittest discover -s tests/identity -p 'test_native_loopback_callback_v0.py' -v
python3 -m unittest discover -s tests/identity -p 'test_private_context_ipc_v0.py' -v
python3 -m unittest discover -s tests/identity -p 'test_desktop_context_projection_v0.py' -v
python3 -m unittest discover -s tests/cpuplus -p 'test_cpuplus_identity_host_context_v0.py' -v
```

Tests use disposable 0700 directories, random 127.0.0.1 callback ports, synthetic PKCE/JWT/API callbacks and no company/person credentials. Confirm constructor non-activation; exact callback; state mismatch and replay refusal; one-shot retry; read-only IPC; private socket permissions; 401 and malformed claims; logout and callback race; token expiry/clock rollback; failure startup cleanup; close and post-close unavailability. GitHub actions assert the existing host, loopback, IPC and CPU++ read-only contracts still pass.

**These tests verify component composition only, not real company sign-in.**

## Hospital checkpoint / owner handoff

**IMPLEMENTATION:** Bounded identity-host lifecycle library + synthetic integration tests, new workflow and this contract/index. No CPU++ UI changes or use of local accounts.

**HOW TO USE:** For source/review only: inspect the PR and CI. No supported live UI action starts a production identity session. Existing CPU++ → ID MANAGEMENT → CHECK HOST CONTEXT remains read-only and will remain disconnected until a separately approved real host exists.

**VERIFY:** Require exact-head CI, then native host owner security review. No live desktop, OAuth issuer, actual user or production server verification.

**WATCH OUT FOR:** Callback and authenticated API clients are injected. A malicious client with the same UID may impersonate the view-only Unix socket. Do not expose host methods to QML, replace signed validation with boolean claims, or authorize edits from displayed grants.

**CHECKLIST:** Compose existing host/receiver/IPC; block stale/bad identity; add tests; index contract; CI; independent security owner review; operator acceptance. Live activation is explicitly outside this milestone.

**NEXT:** Security review of hardened pinned HTTPS transport, certificate validation, JWKS handling, real system-browser launch, account/session revocation and native host isolation. Then independently approve IdP config and first verified sign-in pilot before enabling account management actions.

**DECISIONS:** Preserve the CPU++ layout and local Social editors. No new secret storage, auto-start, production service or role authorization. A display snapshot is never permission. Operator has final authority.

**STAFF/ROOM:** External ChatGPT contributor, no verified live Hospital staff role, room assignment, staffing lease or checkpoint registration. Latest GitHub PR SHA must be reacquired at handoff.
