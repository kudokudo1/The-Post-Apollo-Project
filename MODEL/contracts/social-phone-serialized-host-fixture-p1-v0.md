# Social Phone Bridge // Serialized host check-and-consume fixture P1 v0

> **STATUS:** Non-authoritative, OFFLINE host *concurrency model*. No production authorization, no real SMS event, no real grant host.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`. **BASE:** main `794c408acf2e7abf88f32045dba626377a4820f2`, after PR #1036 merged, 2026-11-02.
>
> **PROVIDER:** OPEN AI // CHATGPT, external Hospital-compatible worker. No verified live Staff Role, Room, Assignment, Session or Hospital registration.
>
> **SCOPE:** New `services/phone/SerializedPhoneHostFixture.py`, `tests/phone/test_serialized_phone_host_fixture.py`, dedicated CI, this contract, and MODEL index. No changes to existing synthetic grant or lifecycle models, Identity Center, Qt decoder, KDE Connect, shared Social router, local desktop or production services.

## 1 // Mechanism and purpose

The existing [synthetic Phone Access Grant fixture](./social-phone-access-grant-fixture-p1-v0.md) and [receive subscription fixture](./social-phone-subscription-lifecycle-fixture-p1-v0.md) model permission and cancellation. They do **not** order grant revocations against message delivery when two threads run concurrently.

The new `SerializedPhoneHostFixture` *composes those existing models* rather than inventing another grant schema. It keeps both objects private and protects all public grant seed/revoke and subscription arm/queue/consume/reconcile/cancel operations with **one Python `threading.RLock`**.

The important ordering: A `consume_synthetic` operation that enters the lock first completes its grant recheck + synthetic count consumption before a host-owned `revoke_fixture_grant` can take effect. If revocation takes the lock first, it removes the grant, clears the pending queue, invalidates the subscription epoch and later consumption cannot succeed. Concurrent claims for one invented message count only once, and two simultaneous arming requests cannot silently replace device or line scope.

These are **linearizable outcomes in the single Python fixture process**, not instantaneous cancellation of an already delivered message. Neither a revoked grant nor a session switch can retroactively undo an event already consumed before revocation's lock acquisition. A future real host must define its revocation-commit point and, if required, ensure UI content is not already exposed.

## 2 // Exact scope and non-authority

The module has no D-Bus access, network, IPC, socket, subprocess, disk persistence, Android permission, SMS text body, QML view, background thread or real sending. Tests use Python threads and **invented event references only**. The only output is the existing sanitized lifecycle response: `execution=FIXTURE_ONLY`, `routeEligible=false`, `contentAccessEnabled=false`, epoch, state and synthetic consumed-count; no message, participant, principal, device, organization, line, grant ID or session handle.

Test-only `seed_fixture_grant` and `revoke_fixture_grant` remain unauthenticated. The injected `resolve_session` and `clock` callbacks and their `HostVerifiedPhoneContext` results are **forgeable fixtures**. A Python `RLock` does not protect against a second process, direct mutation of a real grant database, hostile callbacks, or changes to Identity Center state that bypass this host instance. Nothing in this code is a credential verifier, real permission service, delivery authorization or secure mailbox.

`arm()`, `queue_synthetic_event()`, `consume_synthetic()`, `reconcile()`, `cancel()` and `revoke_fixture_grant()` must be thought of as a single **test-owned** operation surface. For a future privileged host, the session, tenancy, device/line, active transport and Android permission checks must be performed with trusted evidence. Real revocation events must reach that authority, and no phone content can be released until the complete authorization decision and content transfer have one accepted concurrency model.

The prior Qt SMS signal fixture remains hardcoded to a synthetic bus service. The normalizer and native decoder remain unchanged. **Do not attach this Python fixture or its callbacks to real `org.kde.kdeconnect` or expose grant mutation through QML/HTTP/IPC.**

## 3 // Verification

From repo root, in a disposable development environment:

```bash
python3 -m py_compile services/phone/SerializedPhoneHostFixture.py tests/phone/test_serialized_phone_host_fixture.py
python3 -m unittest discover -s tests/phone -p 'test_serialized_phone_host_fixture.py' -v
python3 -m unittest discover -s tests/phone -p 'test_*.py' -q
```

Dedicated GitHub Actions: `.github/workflows/social-phone-serialized-host-fixture.yml`.

Synthetic cases cover independent device/line/org scoping, session/grant expiry, sign-out, context changes, duplicate grants, two concurrent consumers and queue attempts, two concurrent arms, cancel-versus-consume and both explicit revoke-versus-consume orders. A fake resolver uses synchronization events to force delivery to hold the host lock while revocation contends, producing a deterministic serial order. Test assertions intentionally never use personal SMS data.

**A passing test proves only this fixture's local concurrency contract.** It does not establish Qt signal sender trust, process isolation, real carrier/SIM scope, KDE Android SMS permission, transport assurance, audit durability, Identity Center integration or real user acceptance.

## 4 // Host owner security acceptance gates

Before any live phone receiver may subscribe to the real KDE Connect D-Bus service, the assigned Identity Center/security owner must explicitly decide:

1. Which privileged process owns authentication, audited phone-grant issuance/revocation, device/SIM and organization linkage, event delivery and subscription cancellation, and how a caller is constrained from directly opening another phone's D-Bus path.
2. Whether a single-process mutex, a durable versioned transaction, an IPC queue with revocation barriers, or a broker-owned serialized command loop is the accepted *real* ordering primitive. Python `RLock` is **not** automatically suitable across processes or asynchronous Qt/QML callbacks.
3. Exactly when a revocation is committed versus a content release, and whether buffered, cached or already rendered content is purged on sign-out, line switch, membership loss, device unlink or sender change.
4. How current valid Identity Center session/organization grants are checked from a trusted source and how phone-side permissions, network-first transport, device identity and line-specific SMS subscription are independently attested.
5. How to audit grants/revocations without logging phone numbers, SMS bodies, sessions or credentials. Real credentials must never appear in QML, generic Social logs or GitHub Actions.
6. A disposal-only Android device acceptance plan, separate from iPhone and Bluetooth feasibility, and the existing Social integration owner's review of the message handoff.

No real host service, connection or UI is selected or implemented in this PR. The signed-in organization/portfolio UI is only a display context, **never** a phone access grant.

## 5 // Hospital handoff

### IMPLEMENTATION
Single host-owned in-memory `RLock` composes existing two synthetic Phone Bridge fixtures and gives revocation/consume an explicit serialized order.

### HOW TO USE
Review the isolated source, run the above offline tests or inspect the GitHub Action. No local desktop changes or new Social control.

### VERIFY
Check PR exact head, CI step outcomes and concurrency test logs; distinguish mock serialized operations from authenticated live access.

### WATCH OUT FOR
The lock only covers this object. A real Identity Center host, backend, Qt D-Bus receiver and UI crossing process boundaries must use security-reviewed atomic delivery and cancellation. The test's callback is forgeable and no real grant authority exists.

### CHECKLIST
- [x] PR #1036 merged and current main/ownership checked.
- [x] Reused existing grant and subscription fixtures rather than duplicating them.
- [x] Implemented and tested concurrent revoke/consume ordering and scope checks.
- [ ] Exact-head CI and operator review.
- [ ] Security/Identity Center host owner acceptance, signed session and audited grant design.
- [ ] Separately approved real Android device acceptance.

### NEXT
Request explicit owner selection and interface acceptance for an actual Identity Center-backed privileged host. Only then implement host-owned signed-session and device/line grant issuance/revocation, actual provider evidence, and an authorized content receiver. No production or local machine activation in this slice.

### DECISIONS
Maintain operator-approved network-first architecture, Bluetooth opt-in per-capability fallback, separate iPhone/Android paths, original Social menu, and independent personal/company/nonprofit boundaries. No PR merge, production activation, workstation change or live Hospital registration performed.
