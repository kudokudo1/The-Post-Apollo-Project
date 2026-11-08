# Identity Center // read-only Linux logind seat guard v0

> **STATUS:** A real D-Bus client implementation on a GitHub review branch. It is NOT installed on the operator's desktop, connected to Sway's screen locker, configured for real accounts, nor deployed as a protected host.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`. **OWNER:** Identity Center security and desktop session integration.
>
> **SOURCE:** Operator requested full security + switching + management, rather than more disconnected local-ID buttons. PR #1471 (host revocation latch) was confirmed merged at current main before this change. No other open GitHub PR owned the same identity-host files at preflight.

## Mechanism

`LogindSeatGuard` adds an **actual Linux system D-Bus logind reader** for an explicitly started, future isolated host. It uses the reviewed, pinned `dbus-next==0.2.3` client with `BusType.SYSTEM`, not a user-supplied bus address, shell command, QML IPC request or writable logind operation.

```text
future separately approved host process, bound to its own OS login session
    |  LogindSeatGuard.start() // explicit, never automatic
    V
  org.freedesktop.login1.Manager.GetSessionByPID(actual_host_pid)
    |  reject if process does not have a logind session
    V
  org.freedesktop.login1.Session (exact PID-bound object path)
    |  read exact Id, User UID, Active, State, LockedHint
    |  verify UID matches protected host OS uid; Active=true; State=active
    |  LockedHint=false; check full properties at bounded poll interval
    |  listen: Session.Lock, SessionRemoved, PrepareForSleep(true),
    |          and PropertiesChanged(Active/State/LockedHint/Id/User)
    V
  threading.Event permanent revocation latch
    |  on state change, D-Bus failure, bus disconnect, UID mismatch,
    |  stale monitor or active-session loss
    V
  future DesktopHostLifecycle(session_is_active=monitor.is_active)
    |  thread-safe host-only on_revoke -> host.session_event(kind)
    |  host clears memory-only bearer, cancels callback and closes socket
    V
  token-free CPU++/Social viewer is empty/unavailable
```

`start()` subscribes to session and manager events before accepting the first complete property snapshot, reducing the subscribe/snapshot race. A periodic `GetAll` bounds time since the last successfully verified sample. `is_active()` returns false on monitor failure or stale sample even before a shutdown callback completes. Signals may only **revoke**. Unlock/resume cannot revive a previous token, and the monitor cannot call logind mutations, start OAuth or issue company permissions.

### Explicit host wiring, not activated in this PR

In an **authorized future isolated native host**, construct the monitor with an approved host-only `on_revoke=lambda kind: host.session_event(kind)`. Start the monitor in the host's persistent asyncio loop **before** constructing/starting `DesktopHostLifecycle`; inject `session_is_active=monitor.is_active`. The monitor and host are one-shot. On shutdown close the host, then `await monitor.close()`. Never pass `on_revoke`, `session_event`, the bus path or a trusted session probe to QML. No service unit, package installation, D-Bus user-session script or Sway config is modified in this PR.

**Caveat:** `GetSessionByPID` intentionally fails if the privileged host process is in a detached `systemd --user` service that is not a PAM/logind session. Choosing a secure session-binding strategy requires separate desktop/identity owner approval. Do not bypass the PID requirement with an arbitrary `XDG_SESSION_ID` from an environment variable.

## Critical lock and security gaps

- **Sway compositor lock is not universally reflected in logind:** `LockedHint` is a hint set by a desktop environment; `Session.Lock` is a *request* to lock, not proof that a separate `swaylock` process is actually locked. A compositor-native lock event/source, authenticated to the protected host, remains required for complete production enforcement. The operator's existing Sway configuration was not inspected live and is not modified here.
- **Bus signals are asynchronous:** A frame already displayed before a lock event cannot be erased retroactively. The previous PR also documented a narrow race between final host context check and Unix socket send. A production design requires a hardened IPC boundary, compositor lock binding, and viewer invalidation.
- **D-Bus owner/transport failure** is fail closed while monitored. A fake same-UID process cannot get a host token via the display socket, but the current display socket is not proof of cryptographic host identity.
- **No production authentication activation:** A real issuer/client/API and protected service account, browser, verified OS keyring, server-side revocation/audit and request authorization must be approved separately. The module carries no credentials and has no direct access to organization writes.
- **Single sign-on across unrelated apps is not automatic:** PostWallet/Connections will eventually need provider-specific approved OAuth/OIDC integrations, a connection broker, vault-backed refresh/revoke policies, status display and per-provider consent. Local account labels must never be mistaken for an authorized connection.

## Verification

`tests/identity/test_logind_seat_guard_v0.py` exercises exact Manager/Session/Properties read-only API shapes using bounded synthetic bus doubles. It verifies startup binds to the host PID, only the system bus is selected by the default adapter, rejects wrong UID or missing PID session, sees lock/suspend/session removal, rejects user switch and stale/error snapshots, detects D-Bus disconnect and cannot revive on unlock. One integration test drives the **real existing loopback callback receiver**, synthetic bearer, Unix-domain organization display and host teardown when a synthetic logind `Lock` signal arrives. CI also reruns prior host, signed exchange and CPU++ regressions.

**Not verified in CI:** Authentic logind bus replies on the operator's Sway desktop, real compositor lock propagation, service shutdown signals, login1 permissions across distributions, and hostile same-UID IPC impersonation. Those require an explicit desktop acceptance test, not just passing Python mocks.

## Hospital report

### IMPLEMENTATION
Read-only PID-bound system-bus monitor, permanent revoke/lifecycle integration by existing host callbacks (no edit to host source), fixed dependency, tests, workflow and owning contract. Does not connect any production host.

### HOW TO USE
Review PR/CI; no new UI. A later approved protected host would inject `guard.is_active` and register the `guard` revocation callback. The current CPU++ → ID MANAGEMENT → CHECK HOST CONTEXT stays a token-free viewer.

### VERIFY
Exact GitHub commit and workflow checks pending. Native Sway/logind verification not claimed.

### WATCH OUT FOR
Logind lock *requests* and LockedHint do not prove Sway's actual ext-session-lock state. Host session binding fails closed for detached user-service processes. No automatic app SSO or permission writer.

### CHECKLIST
- [x] Read original Social, CPU++, Connections and identity ownership surfaces
- [x] Add bounded system-bus logind observer for protected host
- [x] Enforce host PID, OS UID, lock, active status, sleep and heartbeat
- [x] Add synthetic D-Bus and real host/IPC handoff tests
- [x] Pin dependency and CI
- [ ] Exact PR-head CI green
- [ ] Security owner review of session binding and compositor-native lock signal
- [ ] Native desktop acceptance and separately approved service activation

### NEXT
Build and review compositor-native Sway lock source and protected host process deployment. Only after these are verified, land provider connections and server-authorized organization switching. Preserve the full management menu handoff below.

### DECISIONS
No local machine writes, Quickshell reload, new role/permission controls, live host/service activation or merge. The operator remains final acceptance authority; no Hospital registration or staff lease is verified.

**Recovery:** `services/identity/logind_seat_guard_v0.py`, `tests/identity/test_logind_seat_guard_v0.py`, and this document under the PR's exact head.
