# Identity Center // Native command gateway V1: Request-bound CANCEL and STATUS

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** Universal Sign-In host integration, external Hospital-compatible continuation  
**STAFF ROLE //** DOC-compatible implementation worker; no verified live Hospital registration  
**DOCTOR / PROVIDER //** ChatGPT / OpenAI  
**ASSIGNMENT //** Implement genuine pending-only command cancellation and host-sourced status on merged real AF_UNIX BEGIN gateway; preserve security-worker boundaries and zero production activation  
**BASE //** `6aa41b692d219680f572571baf7aeb0096e141a3`  
**SCOPE / PERMISSIONS //** GitHub branch and PR only, bounded Identity Center host-lifecycle/gateway/session code, disposable native tests and documentation. No C3e/C4b/C5 owner files, real user credentials, production provider grants, Fedora workstation modifications, daemon installation, Quickshell restart, PR merge or live authentication.

## IMPLEMENTATION

V0 [#1680](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1680) merged an **actual explicitly started AF_UNIX BEGIN listener** that invokes the existing Identity Center one-shot PKCE host through injected peer, seat and operator-intent callbacks. The callbacks are mandatory but not yet backed by independently signed production host/consent implementations. The operator's current CPU++ has Sign In disabled as intended.

This V1 continues the actual backend:

- **Real command parser:** `desktop_command_gateway_v0.py` now accepts exactly `{schema,action,requestId}` for `BEGIN`, `STATUS`, `CANCEL`. BEGIN requires `requestId: null`; STATUS and CANCEL require the **existing host-minted 16–96-character ID**. Only fixed schema/action, strict UTF-8, one LF frame, no duplicate JSON fields, no extra sender/trust/credential fields, 1024-byte request bound. RECOVER and provider operations still denied.
- **Request owner binding:** Gateway remembers the Linux `SO_PEERCRED` `KernelPeer(pid,uid,gid)` captured on successful BEGIN. Every STATUS/CANCEL must supply exactly the original host-issued request ID and kernel peer, plus fresh exact-True host-owned `active_seat()`, `verified_peer(peer)` and `approved_intent(peer,action)`. The requester cannot supply an approval boolean. The request ID *alone* is not authorization or host attestation; callback implementers must also bind process start ticks/signed installed executable and actual human consent.
- **Real STATUS:** The server asks its **actual in-process `DesktopHostLifecycle.command_phase()`**, never the separate same-UID private SNAPSHOT display socket or a client-provided `AUTHENTICATED` field. It returns a token-free bounded request receipt in `PENDING`, `AUTHENTICATED`, `CANCELLED`, `FAILED`, `HOST_LOST` or uniform `UNAVAILABLE`. Host phase uses its real callback/one-use session state and a host-only active-token expiry/clock rollback check; expired credentials stop reporting authenticated. A successful callback phase is *experimental host observation*, NOT operator authorization, signed proof or provider grant.
- **Pending-only CANCEL:** New `DesktopHostLifecycle.cancel_pending_login()` takes the *same host RLock* used by the actual PKCE callback. It can succeed only after a BEGIN attempt, before a callback has completed, on an active seat, and only if the host is **not signed in**. It atomically blocks further callbacks, marks the attempt cancelled and calls `DesktopSessionHost.logout()` to discard only this **pending, unauthenticated** code/state. It does **not** call the unconditional `DesktopHostLifecycle.logout()`, never revokes an already authenticated host session and never retries on the one-shot lifecycle. A late callback is rejected.
- **Token liveness:** New host-only `DesktopSessionHost.has_active_session()` observes token age/clock validity and clears expired local host state. It returns only a boolean to the owning lifecycle; neither token nor subject is serialized to the command socket.
- **No client:** CPU++ remains fixed to `ConnectionsSignInHostBoundary.offline()`, Sign In / Cancel / Retry disabled, with the old read-only Identity Center context viewer unchanged. This PR does not provide a deployable, independently attested production command service.

### Proposed V1 command exchange (development-only)

```json
{"schema":"post-apollo.identity.command-intent.proposed-v0","action":"BEGIN","requestId":null}
```

The gateway returns an unpredictable host-generated request identifier in a `REQUESTED` receipt. Subsequent caller-bound queries use that exact identifier:

```json
{"schema":"post-apollo.identity.command-intent.proposed-v0","action":"STATUS","requestId":"HOST_MINTED_EXAMPLE_0001"}
```

The same format with `"action":"CANCEL"` can cancel only when the real host says PENDING. A `CANCELLED` receipt is a **local pending-login cancellation acknowledgement**; it does not claim remote IdP logout/revocation. `RECOVER` remains unavailable, requiring a fresh separately authorized host attempt in the next milestone.

## HOW TO USE

No new operator-facing action. Until the separately approved native Identity host installation, C3e/C4b process/seat attestation and C5 one-use operator consent, **do not enable CPU++ Sign In**, do not connect QML to the gateway, and do not install or start it on the operator's machine.

For reviewers/test maintainers, the existing `IdentityCommandGateway` can be explicitly started in a disposable CI directory with injected host factory and fail-closed identity/seat/intent callbacks. Tests connect through a real Unix socket and send BEGIN/STATUS/CANCEL, execute real existing PKCE callback with *fake IdP/exchange*, and verify denial and state. Production callback implementations remain a distinct security ownership decision.

## VERIFY

The extended `tests/identity/test_desktop_command_gateway_v0.py` exercises:
- Real pending BEGIN → STATUS PENDING → CANCEL acknowledged → STATUS CANCELLED; late OAuth callback rejects and no member data survives
- Real successful PKCE callback → STATUS AUTHENTICATED observation; **late CANCEL denied**, existing signed-in private display remains READY
- Failed/corrupt callback → FAILED and CANCEL unavailable
- Token expiry → FAILED; host secrets and organization display cleared
- Host session loss → HOST_LOST, never stale AUTHENTICATED
- Wrong/replayed/malformed request IDs, changed Linux owner peer, fake authorization fields, revoked peer/seat/intent → UNAVAILABLE without cancellation
- Existing tests: one BEGIN per lifecycle, unavailable unsupported commands, strict envelope, no implicit daemon/browser, private socket permissions and safe cleanup
- Existing host lifecycle, IPC, CPU++ V1–V6 fail-closed and Qt tests remain independent.

Exact-head GitHub CI is a separate verification gate. A passing fake IdP test is NOT real user authentication, production C5 consent or signed installed host evidence.

## WATCH OUT FOR

1. The **host command service** is still experimental and not registered/installed with verified production service identity. Linux SO_PEERCRED proves a kernel process identity, not trusted executable provenance or a continuing session after PID reuse; `verified_peer` must be backed by independent C3e/C4b checks.
2. `approved_intent` must verify a genuine authorized human operation rather than a stub `True`. In tests, fixtures explicitly inject approvals to exercise the real logic. C5 real provider-specific grants are separate from identity sign-in.
3. The experimental `AUTHENTICATED` state reports local verification, not a signed receipt for Quickshell. CPU++ must NOT enable actions based on this JSON alone.
4. Local CANCEL blocks the callback and clears pending state; it does not close a remote IdP browser tab, revoke an IdP web session or silently log out a completed user. Such effects require independent owner-supported semantics.
5. Host STATUS verifies token liveness in-process without network I/O. It does not assert current enterprise organization membership, active provider consent or server-side session revocation.
6. `RECOVER` is still absent. A fresh host instance/request must be separately authorized and never silently reuse the cancelled terminal request.

## CHECKLIST

- [x] Recheck merged #1680, main/active PRs, canonical Hospital rules and protected-host coordination #1662
- [x] Extend real gateway with request-bound STATUS/CANCEL commands and strict parser
- [x] Bind follow-up requests to same original kernel peer + fresh peer, seat and intent decisions
- [x] Add host atomic pending-only cancellation, reject late callback and late cancel after verified login
- [x] Add host-only token liveness and expiry checks for STATUS
- [x] Extend real socket/PKCE/negative replay tests
- [ ] Exact-head CI/repair and independent reviewer acceptance
- [ ] Operator PR merge and native service review
- [ ] Real independently verified host process/seat and C5 operator intent integrations
- [ ] Fresh host-owned RECOVER and independently authenticated STATUS receipt/provenance
- [ ] Real installed native service, QML external client and first approved user login

## NEXT

**V2 backend: guarded fresh RECOVER and authenticated receipt transport**. Implement recovery with a new one-use host lifecycle/request, rather than re-opening an exhausted or authenticated session. Authorize a fresh operator gesture and protect host-key/session rollover. Coordinate C3e/C4b verified *Identity Center* installed executable/process/seat attestations and C5 real operator consent. Once independently reviewed, add the out-of-QML trusted client that can connect CPU++'s existing disabled buttons; don't create a second OAuth provider.

## DECISIONS

Continue actual host implementation under this external DOC-compatible assignment while preserving other workers' owned C3e/C4b/C5 implementation. No live Hospital registration claim, local workstation writes, direct QML OAuth/client activation, browser login, credentials, PR merge or production deployment. Operator retains final approval.

**RECOVERY //** this file, branch `feat/identity-command-cancel-status-v1-20261109`, issue [#1662](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1662), merged BEGIN #1680.
