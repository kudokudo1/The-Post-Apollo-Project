# CPU++ Universal Sign-In V3 // Host-owned intent and progress contract

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** CPU++ Universal Sign-In visual integration (external Hospital-compatible; live Hospital registration not verified)  
**STAFF ROLE //** External DOC-compatible visual integration only  
**PROVIDER //** OPEN AI // CHATGPT  
**ASSIGNMENT //** Implement V3 operator UI for request/progress/cancel/recovery contract, strictly *without* an executable sign-in capability  
**BASE //** `39ab043809b4d54b03cf295f73da84cbc1bd1fdc`  
**PERMISSION //** Bounded GitHub UI, new pure contract, regression tests, workflow and document; no local workstation write, protected Identity/Connections backend change, credentials, production activation, merge or live login.

## IMPLEMENTATION

Current main has operator-confirmed V1 navigation (#1614), V1b upper-left placement above SHARED // STATUS (#1619) and V2's expandable token-free Identity Center display (#1623). The Connections DOC handoff in [#1623 comment](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1623#issuecomment-6742994086) explicitly authorizes developing **the V3 interface now** while real authentication remains disabled until independently verified installed-host and C5 consent integration. C3e-T #1643 is now merged on main, but none of these milestones grants CPU++ host authority.

V3 adds `ConnectionsSignInFlowContract.js`, a pure presentation/test-only host event grammar. It **does not register, subscribe, attest, or send events**. Its fixed runtime projection `offline()` unconditionally disables begin, cancel, retry, connect and batch connect. Test-only `simulate()` checks a strict allowlisted schema, host-minted opaque request ID shape, monotonically contiguous sequence, identity of the request, legal state transitions, denial/cancellation/expiry/failure/host-loss reasons and terminal request non-reuse. Every simulated state carries `simulated: true`; it never becomes an authenticated account or access grant.

The merged **upper-left** `CpuPlusUniversalSignInHeaderPane.qml` now includes **VIEW REQUEST FLOW / HIDE REQUEST FLOW** beneath the V2 Sign-In Status expansion. The six bounded rows describe REQUESTED → WAITING_FOR_USER → VERIFYING → RECEIPT/FAILURE, plus CANCEL ACK and FRESH REQUEST recovery. It shows **SIGN-IN COMMAND CHANNEL // NOT CONNECTED** and **REQUEST // NONE (NO TRUSTED HOST)**, plus visible but disabled **SIGN IN // HOST REQUIRED**, **CANCEL // UNAVAILABLE**, and **RETRY // UNAVAILABLE**. None has an onClicked handler or transport, and no readable source can inject success into the UI.

When the V2 status section hides or the CPU++ Connections menu closes, the V3 flow expansion collapses too. The read-only Identity Center view still clears in-flight data. Original **OPEN ID MANAGEMENT**, **INSPECT LOCAL HOST**, lower Social/inventory, middle provider selector, right Telegram OPEN/RECHECK and dual account-name editing paths are unchanged.

## HOW TO USE

After authorized merge/deploy:
1. **CPU++ → SETTINGS → CONNECTIONS → upper-left VIEW SIGN-IN STATUS.**
2. Select **VIEW REQUEST FLOW** to inspect expected future request, approval and recovery stages.
3. Use **HIDE REQUEST FLOW** or **HIDE SIGN-IN STATUS** to retract the explanation. Closing CPU++ or leaving Connections also resets it.
4. **SIGN IN**, **CANCEL** and **RETRY** remain visibly unavailable. **REFRESH CONTEXT VIEW** is the only newly established read operation from V2.

This is a functional UI explanation of the V3 contract, **not** a simulation of a live login in production. The contract's test-only state machine is never bound to the UI; no user-operable fake authentication success.

## V3 owner interface proposal // NOT YET APPROVED OR INSTALLED

**Precondition**: independently trusted installed Identity Center host, verified service/sender/command channel, operator-initiated intent, host-side consent/issuer configuration, protected token custody, one-use browser callback and independently authorized C5 provider grants. These must be designed and approved by their owners. The `context --json` display reader is not a command interface and cannot satisfy this precondition.

**Request (future):** UI presents a user gesture asking the protected host to `BEGIN`. The host generates an unpredictable fresh request ID and returns a bounded signed/authenticated receipt on its private authorized command/status channel. The UI may subsequently request `CANCEL` only for the currently bound host-issued request; `RETRY` starts a **new** host request ID, never reanimates an old one. Neither action may be inferred from a local request ID string or QML booleans. Cancel is not complete until the host acknowledges; host loss wipes local UI state, not backend tokens.

**Progress (future):** A host-authenticated message has exact *presentation* schema:

```json
{"schema":"post-apollo.identity.signin-event.v0","requestId":"HOST_MINTED_REQ_0001","sequence":1,"phase":"REQUESTED","reason":"NONE"}
```

Allowed phases are `REQUESTED`, `WAITING_FOR_USER`, `VERIFYING`, `AUTHENTICATED`, `DENIED`, `CANCELLED`, `EXPIRED`, `FAILED`, `HOST_LOST`. Terminal reason values: `NONE` (authenticated), `CONSENT_DENIED`, `USER_CANCELLED`, `EXPIRED`, `AUTH_FAILED`, `HOST_LOST`. No token, subject, nonce, URL, username, organization ID, account profile, vault reference, permission or raw diagnostic text belongs in this schema.

**Strict sequencing:** First receipt `REQUESTED` with `sequence=1`; each subsequent event for the same request must increase by exactly one. Replayed, out-of-order, cross-request, extra-field, malformed-reason or post-terminal events must be discarded. For terminal denial, host loss or cancellation, a recovery attempt requires new operator intent and a freshly host-generated request, rather than a stale UI replay. A `HOST_LOST` display never means a revoke has occurred.

**Security boundary:** The schema and simulation do not provide message authenticity. The **host owner** must implement provenance, operator intent, sender identity, C5 consent, security review, protected certificate/identity-provider policy, local seat/session invalidation and final authorization. Never wire `simulate()` to live QML, never trust `event.phase === AUTHENTICATED` for permission or profile switching, and do not add a QML OAuth launcher. The actual command protocol may evolve under owner review; this is an explicit reviewable handoff proposal, not a unilateral implementation of a host API.

## VERIFY

`tests/cpuplus/test_cpuplus_universal_signin_flow_v3.cjs` covers successful **synthetic** sequential lifecycle, terminal failures/denial/cancel/host loss, strict reason mapping, stale sequence/replay, ID mismatch, invalid identifiers, extra credentials/trust booleans and terminal reuse refusal. It asserts the live `offline()` view never enables actuators; QML contains only the flow-explanation toggle and disabled controls; V1/V2 Identity context, ID navigation, installed read-only editor/Telegram and upper-left geometry remain intact.

Dedicated workflow runs V1, V2 and V3 tests, original Connections C1/C2a, Telegram and Social/Identity context suites plus Qt6 QML parser. Exact-head CI and operator native Fedora visual acceptance remain independent gates.

## WATCH OUT FOR

- This PR must not activate credential or session operations, even if C3e-T and C4b signed host tests pass. Connections C3e signed-payload/run-time/process evidence is not a real authenticated Identity Center sign-in service, and C5 synthetic consent is not operator grant.
- The V2 private Unix socket is still only a token-free context viewer. Its `READY` status is not authoritative authentication and must not be used as a V3 command source.
- The contract's `AUTHENTICATED` phase exists **only in synthetic tests**. The live UI cannot receive or display a success phase at this milestone.
- Native 390px left-bay height and scrolling require operator visual acceptance. No existing layout or local workstation was modified by this PR.

## CHECKLIST

- [x] Read current canonical Hospital rules, PR/ownership state, merged V2 and C3e-T updates
- [x] Define strict reviewable request, progress, cancellation and recovery grammar
- [x] Add live upper-left flow information and disabled cancel/retry controls
- [x] Preserve current host untrusted/offline status and prior V1/V2 actions
- [x] Add adversarial synthetic lifecycle/replay tests and CI scope
- [ ] Exact-head GitHub CI pass and independent review
- [ ] Operator merge/deploy/native UI acceptance
- [ ] Identity Center and C3e/C4b/C5 owners approve real command/status channel, host attestation, consent and session-custody contract
- [ ] V4 trusted host adapter, authenticated progress receipt, cancel ack and recovery with native proof
- [ ] Real provider sign-in, reconnect/disconnect, and Connect All *after* per-provider authorization

## NEXT

**Owner-reviewed V4 command/status handshake**. Request Identity Center owner acceptance of exact host command transport, event signatures/provenance, request receipt binding, seat/pid identity, C5 consent channel, abort/cancel and host-loss behavior. Once an actual protected service is installed and verified, implement a narrow sign-in-intent adapter **outside** QML and make the existing disabled button interactive only when host-issued capability and operator gesture are independently verified. Keep provider logins and tenant membership authorization separately owned.

## DECISIONS

UI-only V3, contract-only fake state progression, no production login actions; no token, identity subject, account label-derived authority, direct browser launch or extra credential store. No security-owner reassignment, auto merge, local file writes or live Hospital registration. Operator retains final acceptance.

**Recovery:** `docs/cpuplus-universal-signin-flow-v3.md`, V3 branch/PR and existing merged V2 #1623.
