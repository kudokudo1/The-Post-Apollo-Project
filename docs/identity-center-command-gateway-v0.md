# Identity Center // Explicit host-side BEGIN command gateway v0

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Universal Sign-In integration, expanded operator-directed first host-side implementation  
ASSIGNMENT // Implement an actual, bounded `BEGIN` command-to-existing-login bridge, not another UI-only proposal  
STAFF ROLE // External Hospital-compatible DOC; no verified live Room/Assignment registration  
PROVIDER // OpenAI ChatGPT  
BASE // `ba247617a4b16e7bc9f037a76f8c60be7de9fc7e`  
PERMISSIONS // Isolated GitHub branch and PR, **additive** new Identity Center source/test/workflow/docs only. No edits to existing Identity, C3e/C4b/C5 source owners. No local Fedora writes, token file, service installation, production deployment or merge.

## IMPLEMENTATION

The operator explicitly asked this Universal Sign-In worker to take responsibility for the *actual host implementation*, after V1–V6 prepared and verified the CPU++ interface. Latest Github inspection found V6 #1670 merged, no open PR editing `services/identity` or the CPU++ Sign-In control, and coordination [#1662](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1662) still awaiting authenticated host contract approval. C4d #1657 and C2v are separately owned and unaffected.

**New `services/identity/desktop_command_gateway_v0.py`:**
- A **real** Linux AF_UNIX socket server that can receive one `BEGIN` JSON command and invoke the existing, real `DesktopHostLifecycle.start()` and `begin_login()`; it doesn't invent another OAuth/PKCE implementation.
- Constructing the gateway has no effects. Explicit `start()` requires an *already-owned 0700 directory*, binds a separate `identity-command-v0.sock` socket with 0600 permissions and refuses existing/symlink/unsafe origins. Explicit `close()` revokes the held host session and safely unlinks only the matching socket inode.
- Kernel `SO_PEERCRED` is mandatory. Admission requires **three independent host-owned callback decisions** that return exact `True`: `active_seat()`, `verified_peer(KernelPeer)`, `approved_intent(KernelPeer, "BEGIN")`. Same-UID alone never admits a request; client JSON contains no host/consent boolean. A production-quality callback is **not implemented here** and must come from the existing Identity/C3e/C4b/C5 owners.
- Accepts exactly `{"schema":"post-apollo.identity.command-intent.proposed-v0","action":"BEGIN","requestId":null}`. Strict UTF-8, <=1024-byte, exact keys, duplicate-key rejection. Deny unknown actions and extra fields, including fake host authorization/consent/token/issuer.
- On approval, the service creates one *real* existing host instance via a host-owned factory, starts its existing loopback + token-free context socket, invokes the already-reviewed one-time PKCE/login path, checks active seat again after host side effects, mints a fresh opaque request ID, and returns only `{"schema":"post-apollo.identity.command-receipt.experimental-v0","state":"REQUESTED","requestId":"..."}`. No URL/code/PKCE state/subject/token is returned.
- A second BEGIN is denied. `CANCEL`, `RECOVER`, `STATUS` and provider actions are denied. This does **not** falsely reuse `logout()` as request cancellation or claim usable host-owned progress yet.
- The real implementation has no service auto-start or QML import, never reads the user's credentials, and does not modify any existing service code.

This is a **functional, host-driven BEGIN boundary**, tested with disposable mocks only for the downstream browser, identity provider and API. It is **not yet an enrolled, attested, approved production authentication service**, because the callbacks and native deployment configuration still require independent implementation and review.

## HOW TO USE

There is **no new operator desktop step**. The CPU++ → SETTINGS → CONNECTIONS V4/V5 Sign In/Cancel/Retry remain disabled. Do not run or install this prototype on the operator's machine.

For trusted-host maintainers, the new `IdentityCommandGateway` constructor requires a factory for the existing real `DesktopHostLifecycle`, verified peer/seat/one-use intent callbacks, and an explicitly created protected runtime directory. Starting the gateway binds the isolated command socket. Its unit/integration tests use a temporary directory and injected disposable OIDC/browser/API functions. This is a *development integration component*, not an approved public endpoint.

## VERIFY

`tests/identity/test_desktop_command_gateway_v0.py` sends real AF_UNIX commands to the actual listener with Linux SO_PEERCRED. It exercises denial absent independent peer/consent/seat approvals, successful one-time BEGIN into the existing host, real loopback callback with fake exchange, token-free READY context reading, double-login denial, wrong/extra/secret-injected requests, unsupported CANCEL/RECOVER/STATUS, lost seat, same-inode cleanup, nonprivate directory rejection and session revocation on close.

The scoped workflow `.github/workflows/identity-center-command-gateway-v0.yml` also runs existing host-lifecycle/session/private-IPC tests and CPU++ fixed-offline/V5/V6 tests. GitHub exact-head CI and independent owner review are required before merge. A passing disposable end-to-end test **does not prove** real IdP verification or production trust.

## WATCH OUT FOR

**No production host authentication yet.** The injected `verified_peer` callback must be backed by independent signed-installed caller PID/start-tick/cgroup/process identity and kernel seat evidence, not a plain same-UID gate. `approved_intent` must be independently verified one-use human consent, and `active_seat` must observe actual logind plus compositor lock/session boundaries; missing callbacks fail closed. C3e/C4b/C5 ownership and pending C4d evidence remain separate. No QML code should discover/connect to the command socket until independent security acceptance.

The gateway **does call the existing real login host** after all injected gates approve. Therefore tests use no real keys, issuer, browser launches, credentials or persistent host installation. No first real sign-in has occurred. The receipt is an experimental development result without cryptographic host authentication to UI, not a signed release/authorization grant.

## CHECKLIST

- [x] Verify Syntagma AGENTS, Hospital ownership, V6 merge, active PR collisions and host implementation
- [x] Implement a real explicitly started native BEGIN socket and delegation into existing host
- [x] Require three separate deny-by-default host-owned admission callbacks
- [x] Deny unsupported CANCEL/RECOVER rather than repurpose Logout
- [x] Add actual socket + callback negative/integration tests and CI
- [ ] Exact-head CI success and repairs
- [ ] Identity Center owner review/acceptance of command transport and signed host provenance
- [ ] C3e/C4b installed-host/peer attestation, C5 real one-use operator consent
- [ ] Host-owned request-specific CANCEL, fresh RECOVER, signed progress/status receipts
- [ ] Production-approved installation, explicit operator activation, first real login and native UI acceptance

## NEXT

**Implement and independently review request-scoped CANCEL plus host-authenticated STATUS**, with atomic pending/verified callback semantics, and then fresh host-owned RECOVER. Do not map CANCEL to general Logout; do not show a signed-in UI based on schema-valid JSON. In parallel, approved C3e/C4b/C5 owner implementations must replace the prototype's injected callback fixtures with genuine installed host/process/seat/intent evidence. Only after those checks pass should CPU++ add an out-of-QML client and unlock SIGN IN.

## DECISIONS

A narrow additive, first actual service component is authorized by the operator's explicit continuation after correcting the perpetual handoff problem. No direct modification to established Identity Center host owner files, security-owner source, local workstation, production service or provider accounts. This source is **experimental and review-gated**, not an accepted production command interface. Operator retains final authority and merge acceptance.

RECOVERY // this file, new gateway/test/workflow branch, [#1662](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1662), and merged V6 #1670.
