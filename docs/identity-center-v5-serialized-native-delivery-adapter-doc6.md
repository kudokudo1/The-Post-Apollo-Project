# DOC 6 // Serialize native Identity commands and expose delivery evidence through the existing adapter

**PATIENT //** The-Post-Apollo-Project · **ROOM //** Identity V5 · **ROLE //** DOC 6 (external Hospital-compatible)  
**PRODUCTION SIGN-IN //** HOLD

## IMPLEMENTATION

The actual AF_UNIX signed command client previously tracked one request, phase, sequence and attempted frame in mutable process memory, but permitted concurrent callers and reentry from trust guards. Also, the supported installed composite adapter did not expose the command delivery evidence used by the reviewed #2450 recovery comparison.

This milestone connects existing components, not a new authentication service. A per-client nonblocking lock covers the complete transaction, including pre-send validation, send, receive, post-receipt trust checks and state updates. A concurrent or reentrant call refuses before altering any command state, invoking a trust guard or opening a socket. No command queue, waiting for a prior operation, automatic retry or implicit cancellation is added. The lock releases in finally on successful and refused calls.

`InstalledIdentityCommandAdapterV1.delivery_snapshot()` now exposes the client's immutable `NativeCommandDeliverySnapshot` (wire outcome, last attempted fingerprint, faulted). The snapshot is read under the same lock; `None` means a transaction is in flight and gives no evidence of no send or no effect. Legacy individual read properties remain for CI compatibility, not an atomic pair. The last attempted pointer may predate the current refused call. No raw request, nonce, token, credential, permission or signing key is exposed. The adapter's existing installed/process/key/seat checks and the CPU++ offline rule remain unchanged.

## HOW TO USE

No production desktop action. In an approved disposable native test, use the mandatory installed adapter and read its snapshot after a command returns or refuses. Do not call the experimental raw client from shipped callers. A signed frame or local refusal never grants a new attempt. This only supplies local evidence to future recovery integration; it does not supply the original raw nonce/request or a durable operation ID. It is not a protected query endpoint.

## VERIFY

Four new real signed-client regression methods cover immutable initial/success/refusal snapshots, a reentrant Cancel at a real STATUS post-receipt guard, a competing thread's Cancel during an actual signed STATUS, and a sticky faulted snapshot after wrong-key verification. Existing disposable installed dpkg/systemd test cases now assert the same evidence through the real mandatory adapter, including signed UNAVAILABLE, denied duplicate BEGIN and post-reply seat loss. The existing signed-client, installed-gateway, recovery-join, synthetic and Grammar workflows must pass at the exact PR head. Do not infer a PASS before observing logs.

## WATCH OUT FOR

The lock serializes a single Python client instance, not processes, separately constructed clients, issuer storage, other adapters, or other applications. It does not cancel a running command, bound arbitrary callback execution, or guarantee a protected global original-operation fence. A busy rejection is not a terminal result. Process-local evidence disappears at restart, and a signed UNAVAILABLE frame is not authoritative no-effect proof. The dpkg/systemd witness is a disposable CI service, not independent production Silverblue enrollment. C3e history, C4b authentic gateway and seat, Identity-specific C5 consent and original effect-owner settlement remain unavailable.

## CHECKLIST / NEXT

- [x] Connect existing adapter to local delivery observations and enforce single-flight client behavior.
- [ ] Exact-head native/installed CI and independent Nurse 2 review.
- [ ] Operator merge decision.
- [ ] Cross-owner approved original-operation recovery interface (#2581 proposed; #1662 Identity handoff), durable protected pre-send reservation, independent current history, effect-owner receipt and C5 consent.
- [ ] Positive native acceptance and separate operator activation.

## DECISIONS

Bounded DOC 6 development only. No live registration, local workstation changes, hardware provisioning, keys, real IdP, UI activation, other-owner source or automatic merge. Production HOLD.
