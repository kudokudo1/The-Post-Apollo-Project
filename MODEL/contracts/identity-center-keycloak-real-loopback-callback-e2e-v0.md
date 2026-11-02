# Identity Center // real Keycloak browser redirect to loopback callback to Organizations v0

> **STATE:** CI-ONLY integration pilot. No installed desktop host, no production IdP, no real account data or on-machine registration. This is not independent operator acceptance or permission to merge.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`
>
> **SOURCE:** Operator-directed continuation after merged #1010 (explicit native callback receiver), #1007 (host-owned PKCE state contract), #1000 (tokenless display projection), #995 (real disposable Keycloak API integration), and #990 (file-backed read-only Organizations API).
>
> **SCOPE:** `tests/identity/keycloak_real_loopback_callback_e2e_v0.py`, bounded optional redirect hook in `tests/identity/keycloak_real_oidc_pilot_v0.py`, bounded test-only explicit port configuration in `services/identity/native_loopback_callback_v0.py`, its receiver tests, existing real-Keycloak CI workflow, this contract/index. No Social QML, production verifier, host TLS requirement or real local desktop was modified.
>
> **HOSPITAL:** External Hospital-compatible contributor; no verified active Room, Assignment, Staff Role, session attachment, operator desktop control or local Hospital checkpoint.

## What this tests, end to end

Previously the real Keycloak test used a form-simulating HTTP browser client that stopped at the final redirect URL. The callback receiver test separately used a fake verifier and synthetic code. This work combines them in a single disposable Keycloak CI run.

```text
[Keycloak 26.8.1 disposable CI realm, 127.0.0.1:8080, HTTP test-only]
     |
[form-simulating browser, actual authorization code + S256 PKCE]
     |
[ACTUAL Keycloak Location redirect to registered
 http://127.0.0.1:8765/callback?code=...&state=...&iss=... ]
     |
[LoopbackCallbackReceiver.start(port=8765) test-only]
     | -- exact host, GET, no OAuth URL logging, one-use callback
     |
[host-owned callback in TEST SCRIPT]
     | -- checks state and issuer
     | -- exchanges REAL returned code with original PKCE verifier
     | -- verifies signed ID JWT, audience, issuer and nonce with trusted JWKS
     | -- verifies signed API bearer and live Keycloak introspection
     |
[durable WSGI read-only API, independent 127.0.0.1:ephemeral]
     | -- valid token but unmapped issuer+subject => 401
     | -- explicitly mapped internal principal => two authorized LLC memberships
     | -- unrelated nonprofit/customer hidden from list and portfolio
     |
[DesktopContextProjection]
     | -- only sanitized organization/portfolio IDs and grant previews
     | -- canSwitchOrganization=false
     | -- no access/refresh token, subject, state, nonce, or code to UI
     |
[trusted CI admin revokes LLC A in file-backed SQLite]
     | -- next refresh displays only LLC B
     |
[real Keycloak logout + live token introspection inactive]
     | -- API 401, display SIGNED_OUT, empty company list
     |
[stop servers, remove disposable Keycloak container, delete temp DB]
```

The existing test Keycloak realm pins a registered callback on **port 8765**. To exercise the *actual issuer redirect*, this CI-only test passes `port=8765` to the existing receiver. Normal receiver startup still defaults to an OS-assigned ephemeral port `0`. Invalid, privileged, boolean and out-of-range ports are rejected. The test fails when the port is unavailable rather than forwarding to a different host.

The existing `open_provider()` remains backward-compatible; it now optionally calls a **CI test-owned** `on_redirect(actual_location, verifier, nonce, state)` callback after verifying the signed-in form produced a real auth-code Location with matching state. This callback follows that exact Keycloak redirect to the receiver using a separate HTTP client. It does not re-create the code or supply fake tokens.

## Important security distinction

The disposable Keycloak test image runs its IdP on HTTP loopback. The merged production-oriented `TrustedHostConfig` *correctly requires HTTPS issuer and authorization endpoints*. **No exception was added** and that host is NOT instantiated in this real-Keycloak experiment. The test's callback is an explicitly scoped fixture closure implementing real token verification with the existing loopback-only Keycloak adapter. Offline CI already tests `DesktopSessionHost` orchestration with the receiver and a fake verifier. These two tests are complementary, not proof of a complete production-native sign-in manager.

A successful end-to-end CI test is **not** a trusted desktop host. Missing security gates include: real browser process handoff, loopback port ownership/hardening, HTTPS IdP and Organizations API transport, trusted discovery/key rotation, OS vault, isolated host process, secure one-way UI IPC, auditable enrollments and offboarding, real RP-initiated remote logout, live Quickshell validation and operator approval.

The current Social `USER // SETTINGS → ORGANIZATIONS` page remains disconnected. This CI test does not make a login button appear or enable company switching. A read-only `scopeGrants` preview must never grant real business record access.

## Offline and CI verification

The existing [real disposable Keycloak PKCE workflow](../../.github/workflows/identity-center-keycloak-real-pkce-pilot.yml) continues to run all prior sign-in, JWT, Organizations API and offline tenant regression tests. Its added step runs:

```bash
python3 tests/identity/keycloak_real_loopback_callback_e2e_v0.py \
  --fixture-dir "$RUNNER_TEMP/post-apollo-keycloak-v0"
```

The CI runner generates synthetic random credentials, launches Keycloak as a restricted loopback container, performs genuine S256 authorization-code sign-in, follows the provider redirect to the receiver, validates code exchange and signed claims, reads the real test API and projection, revokes a synthetic membership, logs out, then removes the container unconditionally. No real company records or passwords are used.

The existing native loopback callback workflow runs the new bounded-port negative test alongside the original 19 receiver tests and host/projection tests.

**Verification status:** exact-head GitHub CI required. There is no claim of live workstation or deployed system verification.

## Recovery and next owner seam

Do not merge the draft PR or revert only the changed optional helper, explicit port field, test, workflow and docs/index. The test-only Identity Center database is in a `TemporaryDirectory`; the receiver and test HTTP server call `close()`/`shutdown()` and the disposable IdP workflow has unconditional Docker cleanup. No local machine, user login or Social files are changed.

### IMPLEMENTATION
Real disposable Keycloak authorization-code redirect delivered to a one-shot numeric-loopback HTTP callback, followed by real signed-token verification and an authorized tokenless Organizations response.

### HOW TO USE
Review GitHub Actions and this contract. No desktop command, user-facing activation or production login is created.

### VERIFY
Check exact PR-head real Keycloak workflow plus native callback, host and synthetic request regression tests. Production TLS and live UI verification remain untested.

### WATCH OUT FOR
CI Keycloak is HTTP loopback with special test-only cookie handling, **not** a real-tenant sign-in host. No production HTTPS validation was relaxed. Fixed callback port 8765 exists only to match the disposable realm registration. Real user sign-in and organization switching remain prohibited in this slice.

### CHECKLIST
- [x] Rechecked merged #1010, current main, open ownership and Syntagma/Hospital rules
- [x] Real IdP Location header delivered to actual callback receiver
- [x] Server-signed tokens and revocation tested with prior verified components
- [x] Existing native host HTTPS rules unchanged
- [x] Isolated CI and rollback documentation
- [ ] Exact-head CI success
- [ ] Security/architecture review and operator acceptance
- [ ] Secure process isolation/OS credential custody/UI IPC and live desktop testing

### NEXT
Review passing CI → separately scope and approve hardened desktop host using a real HTTPS IdP → one-way protected UI channel → live USER // SETTINGS read-only Organizations display. Switching remains disabled until backend context selection and per-action grants are reviewed.

### DECISIONS
Disposable Keycloak, HTTP localhost and fixed port are test-only. No IdP vendor, production host, employee identity, real organization records, machine deployment, Social UI change, merge or production activation authorized.
