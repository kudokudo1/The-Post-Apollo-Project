# Identity Center // fail-closed trusted desktop seat/session events v0

> **STATE:** Review-branch host lifecycle safety contract, CI synthetic seat-event tests. This change does NOT deploy a systemd unit, OS seat monitor, production host, provider login or permission administration.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`
>
> **SOURCE / HANDOFF:** After operator requested continuation, GitHub confirmed signed-OIDC-host PR #1469 merged to main. Current `DesktopHostLifecycle` is a one-shot test host; no installed listener, signed-in production principal, OS session bus or staff lease was verified.
>
> **OWNER:** Identity Center protected host; session state must originate in independently authenticated OS/logind/desktop events, never QML, Social labels, an account nickname or client IPC.

## Physical mechanism

The current system keeps a short-lived bearer in a Python `DesktopSessionHost` object inside the host process. A private AF_UNIX read socket lets the widget request a token-free organization display. A one-use numeric-loopback HTTP receiver accepts an OAuth redirect. Without a seat/session gate, those host objects could still answer after the desktop was locked or suspended.

This milestone adds an optional *trusted host-owned* `session_is_active()` probe to `DesktopHostLifecycle`, plus a host-only event method `session_event(kind)` for `lock`, `suspend`, `user-switch` and `session-end`. It also adds a `threading.Event` revocation latch, set **before** waiting for the host's RLock. The latch permanently ends this host session. Restoring activity requires constructing a fresh, explicitly started host object. It cannot revive a previously accepted bearer.

```text
host-only OS seat/logind/session probe (still unimplemented; security-owned)
             |
       session_is_active()    --------- false/exception --> revocation
             |
  start() / begin_login() / OAuth callback / every display request
             |
       DesktopHostLifecycle._seat_ok()
             |
    one-shot host-local revocation Event
       |                          |
       |                    session_event(lock/suspend/user-switch/session-end)
       |                          |
       +----------- mark revoked immediately (no lock wait)
                                   |
       in-progress verified HTTPS request completes or fails
                                   |
       post-request revocation check refuses stale organization result
                                   |
                 DesktopSessionHost.logout()
                    clears in-memory bearer and display projection
                                   |
           close() closes loopback and AF_UNIX socket
                                   |
        CPU++/Social reader receives an empty/unavailable view
```

The gate checks before native login, after the host's browser-launch callback, both before and **after** the code-exchange callback, and both before and **after** API context fetch. On any observed false/exception, the host clears token and display state permanently. `logout()` and `close()` now set the revocation latch immediately, before their lock acquisition, ensuring a context fetch whose **post-fetch check** occurs after revocation returns no former-company data. A lock/suspend/user-switch/session-end event shuts down transports and cancels the session. **There remains a narrow interval between that last check and AF_UNIX socket send** where an already-validated display payload may escape; this mechanism is defense in depth, not an atomic security guarantee. A production host requires independently reviewed seat event delivery, IPC send synchronization and viewer invalidation.

**Legacy test callers that omit `session_is_active` preserve their previous synthetic behavior** so the existing host interface remains compatible. This optional path is **not** acceptable as a production seat integration: a production host must supply a verified, bounded-latency OS-owned session probe, subscribe to real lock/session lifecycle events and fail closed if those mechanisms are unavailable. This PR does not add those OS integrations or claim they are live.

## Verification

The new `tests/identity/test_desktop_seat_invalidation_v0.py` creates a disposable `0700` directory, private AF_UNIX socket and one-use loopback OAuth callback listener with synthetic host-only bearer. It covers:

- Invalid inactive session at startup: no socket, browser or bearer.
- Lock while host is ready but before login: no browser launch.
- Probe exception or false after valid callback: no companies and no retry.
- Seat changes during browser opener, code-to-token exchange and context API fetch: fail closed.
- Explicit lock, suspend, user-switch and session-end events: old host closed, socket removed, no token-free display of former companies.
- Concurrent revocation while a context API request is blocked: revocation event wins before any stale display response can escape.
- Concurrent logout while a context API request is blocked: similarly no stale display.
- Invalid/untrusted event kinds cannot invoke a new authority or restore the session.

Existing host lifecycle, one-use callback, signed OIDC PKCE, pinned TLS, private IPC and CPU++ regression tests continue as CI checks. Exact-head workflows and native-runtime operator verification remain to be reviewed.

## Boundaries / remaining production gates

1. **No real OS seat detection:** Nothing subscribes to `org.freedesktop.login1`, screen lock state, Sway idle, Wayland compositor signals, PAM or user switching. Those are security- and desktop-ownership choices, not inferable from a QML label or guessed bus. If the event never arrives and no probe is supplied, this module cannot detect it.
2. **No systemd user service or desktop install:** This PR does not create a service unit, install scripts, modify `$XDG_RUNTIME_DIR`, clean stale sockets or auto-start a process. It only changes host library logic and tests in GitHub.
3. **No session refresh or privileged mutations:** It does not issue OAuth tokens, store refresh tokens, enable organization switching, grant roles, start login from QML, or authorize resource actions from membership previews. Real server-side access checks must remain independent.
4. **No proven hostile same-UID isolation:** The existing read-only Unix socket validates UID and filesystem permissions but cannot authenticate the real identity of a local process with the same UID. No display snapshot is a grant.
5. **No crypto security certification:** The existing signed ID-token exchange tests are synthetic; IdP issuer configuration, server revocation, TLS trust, protected OS process and real first sign-in all require separate owner acceptance.

## Hospital-compatible checkpoint

### IMPLEMENTATION
Extend the preexisting Identity Center host class with host-owned seat probe, trusted explicit event handling and permanent immediate revocation latch. Add race/lifecycle tests and CI. No CPU++ chassis or local Social storage modifications.

### HOW TO USE
In a future, separately authorized host service, supply `session_is_active=verified_os_probe` on constructing `DesktopHostLifecycle`; its independently trusted seat listener calls `session_event("lock")`, `session_event("suspend")`, `session_event("user-switch")`, or `session_event("session-end")`. These methods **must not be bridged to QML or the display socket**. No live user action is available in this milestone.

### VERIFY
Review exact PR-head GitHub checks and synthetic concurrency tests. Do not treat absence of a real seat event in these tests as proof of live desktop safety.

### WATCH OUT FOR
The host gate is optional for legacy synthetic callers. An injected true-only fake would provide no real lock safety. OS event selection, process isolation and service ownership remain separate blockers.

### CHECKLIST
- [x] Reconstruct merged code and ownership
- [x] Add fail-closed host-only session probe
- [x] Lock/session-end event invalidates host and sockets
- [x] Prevent stale IPC data escaping during concurrent network operations
- [x] Add synthetic tests and workflow coverage
- [ ] Verify exact PR commit CI
- [ ] Security owner reviews OS event source and deployment lifecycle
- [ ] Operator accepts new milestone and separately approves any live installation

### NEXT
Approve and implement an actual platform-specific session detector and isolated native host service using the existing fixed private socket path, hardened OS identity and revocation contract. Only after security review should a real IdP client and explicit UI sign-in intent be connected. Company roles/permission changes remain server-owned.

### DECISIONS
No local user-machine mutation, no desktop reload, no new UI buttons, no production service, no host auto-start, no real login, no role writes and no merge/activation without operator authorization.

**Hospital status:** External ChatGPT worker using Hospital-compatible reporting, but no technically verified live Room, Assignment, Staff Role, Session lease or Checkpoint registration. GitHub PR and this document are recovery pointers.
