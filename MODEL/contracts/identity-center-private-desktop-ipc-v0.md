# Identity Center // private read-only desktop IPC v0

> **STATE:** Linux-only CI prototype, NOT deployed or bound to your live desktop. A separate-process test demonstrates that a privileged host can keep its access token out of the Social display channel. This is not production authentication, host process hardening, OS vault or QML integration.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`
>
> **SOURCE:** Operator-directed continuation after merged PR #1011 (real disposable Keycloak redirect, signed tokens, durable API and tokenless projection), #1010 (native loopback receiver), #1007 (native host state machine) and #1000 (staged Social read-only display).
>
> **SCOPE:** `services/identity/private_context_ipc_v0.py`, `tests/identity/test_private_context_ipc_v0.py`, isolated workflow and this indexed contract. NO change to QML, live services, installer, runtime launcher, IdP, database, existing login code or Hospital records.
>
> **HOSPITAL:** External browser contributor operating Hospital-compatible; no live Room, Assignment, Staff Role, ownership lease or desktop attachment verified.

## Mechanism: actual process memory and socket bytes

Previously the session host, tokenless projection and browser callback were separate Python modules or CI fixtures. There was no cross-process display transport. This PR adds a **Unix-domain socket** used to transmit only validated, versioned display data to a view-only client.

```text
[ FUTURE isolated native host process, not deployed ]
    - real system browser & HTTPS IdP login: future separately owned work
    - OAuth access token: host memory ONLY
    - host-owned verified API GET /me/contexts: already modeled
    - DesktopContextProjection validates/fails closed
                |
     PrivateContextSocket.start() [EXPLICIT; no auto activation]
     <host private 0700 runtime directory>/identity-display-v0.sock
     - numeric local Linux AF_UNIX socket, mode 0600
     - Linux SO_PEERCRED UID check
     - accepts ONLY "SNAPSHOT\n"
     - no arguments, account choice, roles, tenant IDs or mutations
     - obtains current host-owned, validated display snapshot
     - scrubs invalid, oversized or expired data to empty UNAVAILABLE
                |
           JSON bytes ONLY:
     schema: post-apollo.identity.desktop-context-display.v0
     status: READY / NO_MEMBERSHIPS / SIGNED_OUT / ...
     organizationId, kind, scopeGrants (display previews only)
     portfolioId and independently joined organizationIds
     canSwitchOrganization: false
                |
        read_private_display(host-selected socket_path)
     - validates private socket path, UID and strict display schema AGAIN
     - rejects extra fields, bad IDs, expired scopes or portfolio escalation
     - on absence/error/host death => empty UNAVAILABLE, no stale cache
                |
     [ future authorized Quickshell/QML adapter, NOT IMPLEMENTED ]
     - existing organizationDisplaySnapshot default still null
     - no bearer, OAuth code or session object received by Social
     - original "SWITCH ORGANIZATION // UNAVAILABLE" stays disabled
```

The IPC client does send a **fixed read-only request** to retrieve the latest snapshot; "one-way" here means **no privileged commands or credentials cross from the Social-side viewer to the host**, not literal unidirectional network traffic. Do not call this a fully one-way or cryptographically authenticated transport.

## Test-specific process isolation

The new test creates a Linux `multiprocessing` child process using `spawn`. Only the child constructs the disposable `DesktopSessionHost` and generates a new random test bearer. It completes a synthetic, verified PKCE callback using an injected fake exchange and API client **inside that child**, then exposes a snapshot provider through the private socket.

A different process, acting as the Social-side viewer, reads the versioned JSON. Tests assert that it sees only its sample LLC membership, never the bearer, subject, PKCE verifier or a switch permission. After a test-only local logout event, a new display request returns SIGNED_OUT or an empty nonready state; killing the host makes subsequent reads return empty UNAVAILABLE. No shared Python host object or bearer is passed to the parent reader. Other tests inject malformed display data, duplicate/unauthorized roles, wrong scope expiry, forged portfolios, invalid request verbs and stale clock.

**This is separate from the merged real-Keycloak CI test.** The new IPC test verifies process separation and socket transport with synthetic host callbacks, while #1011 verifies the real disposable Keycloak browser callback and signed token chain. Production acceptance requires exercising all of these components in an actual isolated host with a real HTTPS IdP and real QML runtime, not just passing separate CI tests.

## Security restrictions and open questions

- Private runtime directory must preexist, be an absolute directory, be owned by the running user and have no group/world permissions. The server refuses symlinks at that directory entry and refuses to overwrite an existing socket path. It binds its own socket mode `0600` and removes only the inode it created.
- Linux `SO_PEERCRED` checks same-user peers. **Same UID is NOT a sandbox or sufficient protection against malware running as that user.** Such a process can read display metadata and attempt denial of service. A hostile desktop or QML process with the same OS UID cannot be considered fully isolated from the eventual host without additional host hardening, sandboxing and audit.
- Socket service is test-only, synchronous and deliberately capped to 64 KiB. It is not hardened for concurrent hostile clients, service discovery, systemd activation, slow-reader denial of service, long-lived session management or crash-safe restart. It has no OS credential store and does not revoke remote sessions.
- IPC includes grant **display previews**. These are **not** authorization receipts. Every business data operation must recheck live trusted grants and tenant scope on the server. No organization selection or write API exists on this socket.
- No external URL, browser redirect, token, credential, user ID, company ID or tenant selector is accepted in the IPC request. The viewer gets only the current verified person's existing server-filtered list.
- A valid JSON snapshot could still be forged by another process controlling a same-UID host; do not treat this viewer as an identity proof. The backend remains the authority.
- The QML `organizationDisplaySnapshot` input is still null. This branch **does not attach** the viewer to Quickshell, write a runtime socket under the user's home, or start an actual desktop service.

## Verification and handoff

[GitHub Actions: private desktop IPC](../../.github/workflows/identity-center-private-desktop-ipc.yml)

```bash
python3 -m unittest discover -s tests/identity -p 'test_private_context_ipc_v0.py' -v
python3 -m unittest discover -s tests/identity -p 'test_desktop_session_host_v0.py' -v
python3 -m unittest discover -s tests/identity -p 'test_desktop_context_projection_v0.py' -v
python3 -m unittest discover -s tests/messaging -p 'test_identity_center_desktop_display_v0.py' -v
```

Rollback: decline draft PR or revert the new module, test, workflow and MODEL document/index entry. The runtime sockets are created only inside CI temporary directories and removed in test teardown, and any spawned child is joined/terminated by the test. No desktop or production user data is touched.

### IMPLEMENTATION
Linux private 0700 directory + 0600 Unix socket, UID checking, fixed display-only request and validated JSON return, with a spawned, token-holding test process.

### HOW TO USE
Inspect CI and source. No live menu or service to start. No local installation.

### VERIFY
Require exact-head CI with real separate-process test, then review security limits; live Quickshell UI and real network IdP remain unverified.

### WATCH OUT FOR
A socket is **not** an OS credential vault or security sandbox. Same-user hostile processes remain a threat; no access token can be sent via display JSON. Real QML wiring and deployment require separate approval.

### CHECKLIST
- [x] Recheck merged #1011, current GitHub source and open ownership
- [x] Tokenless Linux AF_UNIX read-only snapshot contract
- [x] Explicit private path ownership and fail-closed checks
- [x] Dedicated child-process host custody test and negative cases
- [x] CI and Hospital-compatible handoff/rollback
- [ ] Exact PR-head CI green
- [ ] Native process sandbox, OS credential vault and production transport review
- [ ] Live UI integration, real HTTPS IdP session and operator acceptance

### NEXT
Verify CI; then choose an approved native process supervision and OS-secret-custody scheme. After security review, implement a restricted, read-only Quickshell bridge to the existing Organizations display, clearing on logout/lock/crash. Only later enable organization switching if independently authorized server-side.

### DECISIONS
CI-only Linux socket, **not** a production IPC standard or deployment. No real IdP vendor, local system modifications, QML credentials, company switching, access migration, merge or production activation.
