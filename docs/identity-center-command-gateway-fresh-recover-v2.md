# Identity Center // Native command gateway V2: Fresh host-owned RECOVER

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** Universal Sign-In backend integration, external Hospital-compatible, not live-registered  
**STAFF ROLE //** DOC-compatible implementation worker, no verified staffing attachment  
**DOCTOR / PROVIDER //** ChatGPT / OpenAI  
**ASSIGNMENT //** Implement functional request-bound RECOVER by replacing cancelled/failed Identity Center host lifecycle with a fresh independently authorized attempt, while leaving CPU++ login locked  
**BASE //** `74e5b17c7c8ed7f6fd704b5ccd4129fab077b066`  
**PERMISSIONS //** GitHub branch/PR only; bounded modifications to the already owned experimental Identity command gateway, its disposable tests, CI and documentation. Do not modify C3e/C4b/C5 workers' files, production signed gateway installation, local Fedora services, provider credentials or browser sessions. No automatic merge or live Hospital claim.

## IMPLEMENTATION

Operator confirmed V1 STATUS/CANCEL PR #1686 merged and passed, following merged native BEGIN PR #1680. The current Identity Center gateway already has strict BEGIN / STATUS / pending-only CANCEL with host-owned callback/session state. Previous code kept RECOVER unavailable.

**New V2 real operation:**
- `desktop_command_gateway_v0.py` command parser now accepts **RECOVER** only with the precise 16–96 character **existing host-minted request ID** (as for STATUS/CANCEL). No new schema keys, QML status flags, passwords, OAuth codes, provider IDs or raw URLs. The request is rejected for missing/extra/invalid fields.
- Every RECOVER is bound to the **original Linux SO_PEERCRED PID/UID/GID** and the exact old host-issued request ID; host also requires fresh exact-True independently supplied `active_seat`, `verified_peer` and **separately approved RECOVER operator intent**. As with V1, these callbacks are injection contracts in experimental tests, **not yet attested real C4b gateway provenance or C5 consent**.
- The host's actual `command_phase()` must be **CANCELLED** or **FAILED** before recovery. `PENDING`, `AUTHENTICATED`, `IDLE`, `HOST_LOST` and unrecognized status cannot recover. A completed session remains untouched by a RECOVER request. An expired credential may result in FAILED when the real host checks token lifetime; a fresh login still requires new user authorization.
- On accepted recovery, gateway **first invalidates the old request ID and peer binding**, closes the old native host (clearing pending/verified credentials and old loopback/private display socket), and only then constructs and starts a **new** `DesktopHostLifecycle` through the same externally owned factory. It calls that host's real one-use `begin_login()`, rechecks trusted seat/peer after browser dispatch, and mints a **different** cryptographically random request ID. A new `REQUESTED` receipt is returned with that new ID only.
- New `_begun_once` guard prevents a failed BEGIN/RECOVER from accidentally opening a new unapproved BEGIN path on the same gateway. A failed recovery consumes/invalidate the old terminal request and cannot replay it or silently retry. The security owner must re-establish the gateway after a partial failure and independently reauthorize subsequent activity.
- Repeating recovery after **another** cancelled/failed *new* request is possible only through another request-scoped RECOVER approval, fresh host lifecycle and new minted ID, never resurrecting any earlier host or PKCE verifier.
- The existing pending-only CANCEL is unchanged. General host Logout is not exposed as request cancellation. Request-bound STATUS remains a local experimental host phase, never a cryptographic grant to CPU++.

## HOW TO USE

**No new desktop operator action.** In CPU++ → SETTINGS → CONNECTIONS, Sign In/Cancel/Retry remain disabled until separately installed/attested native host, session and C5 consent are independently approved. This code is **not** deployed or connected to Quickshell.

Security reviewers can exercise the real native Unix command endpoint on disposable CI hosts:

```json
{"schema":"post-apollo.identity.command-intent.proposed-v0","action":"RECOVER","requestId":"HOST_MINTED_EXAMPLE_0001"}
```

A successful test returns `{"schema":"post-apollo.identity.command-receipt.experimental-v0","state":"REQUESTED","requestId":"<fresh ID>"}`. It is not a signed UI receipt or authenticated provider session. The gateway must be started explicitly under protected runtime directory with its existing host factory, kernel-reported peer, approved session and one-shot operator intent callbacks. Do **not** run it on the live Fedora machine or provide fake True callbacks outside isolated tests.

## VERIFY

The new cases in `tests/identity/test_desktop_command_gateway_v0.py` run through a **real Linux AF_UNIX socket and the existing host code**, using disposable browser/IdP/API/consent fixtures:
- CANCELLED → RECOVER creates a second host, fresh ID, rejects old ID/replays/second BEGIN and permits a new callback.
- Repeated CANCELLED → RECOVER issues an additional fresh ID, never the original or previous one.
- FAILED OAuth callback → RECOVER requires new explicit RECOVER permission, creates new PKCE state and accepts a new verified callback.
- PENDING and AUTHENTICATED → RECOVER denied, without revoking the authenticated host.
- Wrong/missing old ID, extra fields, credential injection, peer change, revoked operator/peer permission → denied.
- Replacement host construction failure → old host closed, request discarded and no implicit BEGIN possible.
- Seat/host loss cannot be recovered by restoring an untrusted test seat flag.

The scoped `.github/workflows/identity-center-command-gateway-v0.yml` runs the extended socket tests, existing Identity Center lifecycle/session/private-IPC regressions and CPU++ default-deny/security contracts, along with separately triggered Identity Center/OIDC/transport workflows. Exact-head GitHub verification and independent operator review must be reported separately.

## WATCH OUT FOR

- **Still not production authentication.** The gateway is experimental. Linux SO_PEERCRED identifies the kernel caller process, not independently signed installed executable/actual PID start tick or human intent. C3e/C4b must attest the actual **Identity Center gateway**, not the separate disposable Connections status host. C5 must supply real one-use human consent, not an injectable True fixture.
- V2 RECOVER replaces the native **local** login attempt; it does not close the browser tab, remotely revoke external IdP sessions, or grant Telegram/Discord/other provider permissions.
- A matching request ID alone never authorizes anything. The old ID is discarded before new startup. A failed new host startup does not leave the old session available through command receipt.
- `REQUESTED` and `AUTHENTICATED` remain **unsigned experimental local host observations**. CPU++ never imports this module, and `ConnectionsSignInHostBoundary.offline()` remains enforced.
- Closing a completed authenticated session on this path is prohibited by the phase gate; actual logged-in users need a separately authorized Logout feature. A prior FAILED status includes local token expiration/revocation and cannot be treated as proof of server-side session invalidation.
- No live Hospital registration, exact local desktop deployment or production IdP integration was verified.

## CHECKLIST

- [x] Recheck merged V1, main, live PR ownership and Syntagma/Hospital protocols
- [x] Add actual request-bound RECOVER action to the existing gateway
- [x] Create fresh native host/PKCE state/opaque ID after terminal cancellation/failure
- [x] Reject recovery from pending, authenticated or host-lost sessions
- [x] Add replay, spoofing, failure-recovery, multi-attempt and no-implicit-begin tests
- [ ] Exact-head GitHub CI, repair and independent security-owner review
- [ ] Operator PR merge and host acceptance
- [ ] C3e/C4b independently signed installed *Identity Center* gateway, protected peer/seat and C5 operator intent
- [ ] Cryptographically authenticated status/command receipts, authorized out-of-QML CPU++ bridge
- [ ] First approved real user login and provider-specific permission verification

## NEXT

**Native trust/receipt implementation**. Coordinate independent signed installed gateway executable/process/seat origin, protected operator consent, and authenticated token-free receipt transport with Identity Center/C3e/C4b/C5 workers. Then construct a narrow out-of-QML CPU++ command/status client and enable its controls only after host provenance, operator intent and replay defenses are independently accepted. Do not mistake disposable CI callbacks or a private same-UID socket for production authority.

## DECISIONS

The work stays in the existing Identity Center gateway implementation lane, no new OAuth host or additional decorative UI. No security worker ownership transfer, local Fedora mutation, production credential access, provider login, merge or release. Operator retains final authority.

**RECOVERY //** This file, V2 branch and PR; cross-Room owner issue [#1662](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1662); merged BEGIN [#1680](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1680) and STATUS/CANCEL [#1686](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1686).
