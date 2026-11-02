# Social Phone Bridge // Synthetic receive-subscription cancellation P1 v0

> **STATUS //** Offline, non-authoritative subscription lifecycle model. No permission to read phone content, no real KDE Connect signal registration.
>
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`
>
> **DATE //** 2026-11-02. **BASELINE //** `main` at `2a4c88d6c03be8aa8d421c346e40e6428046595c` after PR #1035 merged at `e7b0447e7b1d50649d73763b9eef8e30b3d399ea`. Recheck latest main and ownership before continuation.
>
> **PROVIDER //** OpenAI / ChatGPT, external Hospital-compatible Doctor. No verified live Room, Staff Role, Assignment, Session or registered checkpoint.
>
> **OWNED SCOPE //** `services/phone/PhoneSubscriptionLifecycleFixture.py`, `tests/phone/test_phone_subscription_lifecycle_fixture.py`, dedicated CI, this contract and `MODEL/README.md` pointer.
>
> **PROTECTED //** No changes to Identity Center, Account Broker, Social UI, shared messaging router, existing Phone Bridge grant model, Qt native SMS decoder/fixture, local Quickshell, paired phones, KDE Connect daemon or deployment.

## 1 // Why an access grant is not enough

A phone access grant may be valid at subscription start, then be revoked while an SMS event is queued. A correct implementation cannot cache `authorized=true` and release the queued text later. It must recheck actual authenticated session, principal, owner organization, device, SIM/line, operation and permission **before every event is released**, and explicitly stop the receiver when authorization changes. Queued content must be dropped on revocation or identity/line switch; old callbacks must be invalidated.

This PR tests only the **control lifecycle** with made-up event IDs. It never accepts an SMS body and does not carry real personal data.

## 2 // Behavioral model

`PhoneSubscriptionLifecycleFixture` receives a test-only injected `check_grant` callback (typically the merged `TrustedPhoneGrantFixture.check`). That callback is **not** a trustworthy authorization source. Its `MATCHED_FIXTURE_ONLY` state means a simulated grant matches, while its `routeEligible=false` and `contentAccessEnabled=false` must remain false.

The receiver model offers:

- `arm(request)`: explicit `messages.receive` fixture only, requires an exact scoped grant request. Never allows read/history, send, contacts, calls or silent reuse of an active binding. Returns `ARMED_FIXTURE_ONLY` and an epoch integer for test sequencing.
- `queue_synthetic_event(event_ref, epoch)`: validates a short *synthetic ID only*, rechecks the fixture grant for each attempted event, enforces at most eight pending IDs and rejects duplicates or stale epoch values. **No content field exists.**
- `consume_synthetic(epoch)`: rechecks the grant **after** queueing and immediately before synthetic consumption. Returns only a count of 1, no event ID/body/phone number/tenant info. Revocation/expiry/sign-out results in `CANCELLED`, cleared queue and invalidated epoch.
- `reconcile()`: explicit fixture host call when membership, session, permission or organization context changes. Denied checks cancel immediately.
- `cancel()`: clears all queued IDs, drops the bound request, and increments the epoch so callbacks from a prior subscription cannot be mistaken for current events.

Everything remains single-process, single-threaded, in memory and **SIMULATION ONLY**. There is no D-Bus connection, daemon, network, filesystem, SMS call, QML action, timer or actual subscription. Epoch numbers are not secrets, unforgeable tokens or grant evidence. No live message is ever delivered, and every output keeps `contentAccessEnabled=false` and `routeEligible=false`.

A fixed reply consists of `schema`, `execution=FIXTURE_ONLY`, `state`, `epoch`, `syntheticDeliveredCount`, `routeEligible=false`, `contentAccessEnabled=false`. No principal/session/device/line/org/grant ID, event ref, message body or backend metadata is output.

## 3 // Verification

Run from repository root in a disposable development environment:

```bash
python3 -m py_compile services/phone/PhoneSubscriptionLifecycleFixture.py tests/phone/test_phone_subscription_lifecycle_fixture.py
python3 -m unittest discover -s tests/phone -p 'test_phone_subscription_lifecycle_fixture.py' -v
python3 -m unittest discover -s tests/phone -p 'test_*.py' -q
```

Dedicated CI: `.github/workflows/social-phone-subscription-lifecycle-fixture.yml`.

The 27 offline tests cover explicit arming, deny-by-default, per-event grant checks, grant/member/session revocation between queue/consume, expiry and clock rollback, device/line/principal scope, tenant isolation, duplicate ID rejection, bounded queue fail-closed behavior, callback exceptions, forged fixture decision output, content-bearing input rejection, context-switch epochs, and absence of identifying data in replies.

## 4 // Production bridge still blocked

Implementing a real host-side Phone Bridge grant service is an **Identity Center and security ownership decision**, not implied by a matching synthetic grant. Before writing a live `org.kde.kdeconnect` subscriber:

1. The assigned Identity Center owner must expose cryptographically verified sessions, trusted principal and fresh organization membership, plus audited creation/revocation of phone/device/line/operation grants from explicit consent. Current synthetic request boundary does not secure a production phone.
2. The phone/adapter owner must verify actual Android device identity, active network transport (rather than assuming from plugin flags), SMS plugin permission and sender-owner continuity. No iOS equivalence is implied.
3. The privileged host must own **one serialized check/consume boundary**, including racing revocations, concurrent event callbacks, device unlink and line/tenant switches. A one-time check followed by an unsynchronized deliver creates a TOCTOU security gap.
4. All production message content must stay in protected host memory/IPC, be cleared on cancellation, and never be emitted into broad QML signals, stdout, GitHub logs or organization-inappropriate views.
5. Explicitly separate receive, message history read, SMS send, contact read, notification events and call control/audio. Unknown send outcomes must not auto-fallback across transport.
6. Obtain operator-approved hardware testing and an integration-owner handoff before any real subscription, production UI, local daemon or machine change.

Do **not** turn this class or the older `TrustedPhoneGrantFixture` into an HTTP/IPC service. The host callbacks, grant seed/revoke methods and epoch are forgeable and have no production security boundary.

## 5 // Hospital handoff

### IMPLEMENTATION
Isolated, offline subscription lifecycle fixture with explicit cancellation, per-event simulated grant recheck and stale-event invalidation. No production receiver or identity code edited.

### HOW TO USE
Review code and run offline tests; no local Post-Apollo menu, Qt receiver activation, KDE permission, or pairing operation added.

### VERIFY
Check exact PR SHA, GitHub Actions status and test logs. A green CI certifies only invented event lifecycle behavior; it does not prove an Android message or deployed authorization.

### WATCH OUT FOR
Pure test methods are not authoritative access control. Production host must synchronize grant revocation with content delivery, not merely copy the in-memory epoch protocol.

### CHECKLIST
- [x] PR #1035 merge and latest main verified; Syntagma/Identity Center scope inspected.
- [x] Created bounded lifecycle model without real phone content.
- [x] Added strict negative tests, workflow and documented recovery.
- [ ] Exact-head CI success and operator review.
- [ ] Security/Identity Center ownership and production grant design.
- [ ] Explicit local device and message access approval.

### NEXT
Design a host-owned serialized authorization-and-delivery boundary with the Identity Center owner, including auditable grant issuance/revocation, actual session proof and trusted device/line binding. Leave the fixture and real Qt receiver disconnected until those gates are accepted.

### DECISIONS
Keep the network-first Phone Bridge, Bluetooth as opt-in fallback per operation, Android and iPhone as separate platform tracks, and a single existing Social workspace. No merge, production activation or local-machine modification authorized by this PR.
