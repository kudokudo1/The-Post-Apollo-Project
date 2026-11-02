# Social Phone Bridge // Trusted Phone Access Grant fixture P1 v0

> **STATUS //** Offline, non-authoritative grant lifecycle **fixture only**. NOT a real identity/phone authorization service.
>
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`.
>
> **DATE //** 2026-11-02. **BASE //** main at `034ab2a2ad775d590b130967b32136cdd3eefa3c` after PR #1033 merge; inspect current main before future edits.
>
> **HOSPITAL //** External browser ChatGPT, Hospital-compatible. No verified live Room, Assignment, Staff Role, worker registration or checkpoint.
>
> **SCOPE //** `services/phone/TrustedPhoneGrantFixture.py`, `tests/phone/test_trusted_phone_grant_fixture.py`, targeted CI, this contract and MODEL index. No changes to `services/identity/*`, Social UI or shared adapter/router, KDE Connect daemon, Qt SMS receiver/decoder, Quickshell, Bluetooth or local host.
>
> **REQUIREMENTS //** [Phone Bridge network-first ADR](./social-phone-bridge-network-first-adr-v0.md), [KDE synthetic SMS signal lifecycle](./social-phone-kdeconnect-sms-signal-fixture-p1-v0.md), [Identity Center upgrade plan](./post-apollo-identity-center-upgrade-plan-v0.md), [synthetic Identity request boundary](../../services/identity/synthetic_request_boundary_v0.py), [shared Messaging Adapter Contract](../../services/messaging/ADAPTER-CONTRACT.md).

## 1 // Real mechanism, not just a UI toggle

A future message receiver needs **three independently checked rights** *before* it delivers private phone content:

1. **Human authentication:** a protected Identity Center host verifies an actual session and determines the person. QML `identity-N`, a phone number, portfolio membership, self-declared principal ID or device path **cannot** establish identity.
2. **Phone/line access grant:** a host-authoritative, revocable grant binds one verified principal to one device, one phone line or SIM, one ownership context (**PERSONAL** or a specific **ORGANIZATION**), permitted operations, and expiry. An organization-controlled line additionally requires an independently active membership and org-delegation authority. A portfolio never gives inherited rights to a member company's phone.
3. **Provider and transport permission:** KDE Connect must actually have the permitted Android-side SMS feature/permission, a verified network transport and a process-bound sender/device identity. Loaded desktop plugin metadata is not proof. Bluetooth remains a separate explicit per-capability opt-in fallback.

A future production host must recheck these before **each received event and privileged operation**, and revoke subscriptions immediately on sign-out, membership removal, line unlink, device permission loss, grant revocation, trusted clock failure or backend connection loss. Never keep a one-time `authorized=true` boolean in the QML UI or an always-running receiver.

## 2 // What this repository slice does

`TrustedPhoneGrantFixture.py` models only the **second part**, with a synthetic host callback for the first part. It is in-memory and never reads actual content, makes a D-Bus request, opens a socket, issues a credential, stores data or touches a device.

The test harness has `seed_fixture_grant()` and `revoke_fixture_grant()` methods. These are deliberately **unauthenticated fixture APIs** and must never be exposed to a user, QML, IPC or HTTP. They are not production grant creation/revocation endpoints. The maximum fixture lifetime is 900 seconds and the store is bounded.

The model receives a host-only injected `clock()` and `resolve_session(sessionRef, now)`. A correct production counterpart must cryptographically authenticate the session and obtain fresh memberships from the **trusted Identity Center**, not trust a caller-created `HostVerifiedPhoneContext`. That Python dataclass is trivially forgeable, and the injected callback is just a CI test double. Neither one grants real rights.

Each `check()` request has **exactly** these fields:

| Field | Meaning |
| --- | --- |
| `schema` | `post-apollo.phone.synthetic-access-grant.v0` |
| `sessionRef` | Opaque test-session handle, not bearer token or authenticated proof |
| `deviceId`, `lineId` | Exact opaque synthetic device and phone-line reference |
| `ownerKind` | `PERSONAL` or `ORGANIZATION` |
| `organizationId` | Null for personal; exact org ID for organization-managed line |
| `operation` | Explicit single operation (e.g. `messages.receive`, `messages.read`) |

No request-side `principalId`, `grantId`, role, portfolio, phone number, password, token or `authorized` flag is accepted. The principal comes only from the injected host-only resolver. Organization grants additionally require a fresh independently verified active organization in the host context. The store then matches exact principal/device/line/owner/org/operation and non-expired grant. Ambiguous matching grants, invalid callback data, expired grants or sessions, invalid clock and clock rollback fail closed.

## 3 // What its output does NOT mean

The only outputs are identical fixed-field dictionaries:

- `state: DENIED` for no eligible fixture match, missing membership, revocation, expiry, or errors.
- `state: MATCHED_FIXTURE_ONLY` if a *synthetic* grant matches.
- Both states include `execution: FIXTURE_ONLY`, `routeEligible: false`, `contentAccessEnabled: false`.

**Neither state is an authorization decision for the operating system or Social UI**. Do not translate `MATCHED_FIXTURE_ONLY` into `CapabilityPolicy.py` `authorization=VERIFIED`, into `READY`, into an SMS receiver subscription, or into permission to read a text. No raw principal, session, grant, organization or phone identifiers appear in the result.

The grant fixture intentionally makes no claim about SMS read/history requests, delivery confirmation, iPhone iMessage access, call audio, third-party phone APIs or Android-side permissions. Its operation list models future scope boundaries, not implemented capabilities. The actual Qt receiver still listens exclusively to `org.postapollo.phone.fixture`, not a real KDE Connect daemon.

## 4 // Offline verification

From the repository root:

```bash
python3 -m py_compile services/phone/TrustedPhoneGrantFixture.py tests/phone/test_trusted_phone_grant_fixture.py
python3 -m unittest discover -s tests/phone -p 'test_trusted_phone_grant_fixture.py' -v
python3 -m unittest discover -s tests/phone -p 'test_*.py' -q
```

Dedicated CI: `.github/workflows/social-phone-trusted-grant-fixture.yml`.

Synthetic cases cover deny-by-default; exact owner/device/line/operation matches; no implicit read/send; independent personal vs company line; organization membership changes; cross-tenant and portfolio noninheritance; expiry; session revoke; immediate fixture grant revoke; malformed and forged request fields; duplicate ambiguous grants; invalid clocks, verifier failures and identifier redaction. No actual user account, phone, organization data or network is accessed.

## 5 // Next boundary: production design requires separate permission

Before a real KDE message stream may be enabled, Identity Center/Account Broker owners must select and accept:

- Where the **authoritative phone/device/SIM grant store** lives and how a person or authorized organization administrator approves and revokes each operation, with audit evidence and protected host-only write methods.
- How the existing session host verifies identity, active org membership, device ownership and the active selected line, including immediate revocation on all changes and a trusted clock. A session handle from a UI cannot itself be an authorization credential.
- How a narrow native receiver obtains a **host-issued, request-scoped, nonforgeable** permission to subscribe, and how permission is rechecked on each event; no personal message content goes to an untrusted QML, stdout, generic log or GitHub Actions.
- How KDE daemon D-Bus sender owner, device ID, Android platform, current transport and phone-side messaging permissions are independently attested. Evidence must not be assembled from untrusted QML labels.
- How to cancel subscriptions and erase queued content when authorization changes or the transport drops. Stale event callbacks must not cross personal/org/line context switches.

That is **outside this PR** and needs explicit integration-owner coordination plus a separately approved live test with an Android device. Existing Identity Center prototypes are not production-grant authorities.

## 6 // HOSPITAL HANDOFF

### IMPLEMENTATION
Pure, non-authoritative, in-memory phone grant fixture with revocation tests, workflow and indexed contract. No Identity Center code modified.

### HOW TO USE
Run offline tests only. There is no production grant admin menu and no phone access to activate.

### VERIFY
Check exact PR-head CI and read back branch files. The suite proves synthetic scope and revoke semantics, not a trusted phone login, network or messaging capability.

### WATCH OUT FOR
`HostVerifiedPhoneContext` can be forged in Python; the store's seed and revoke methods are unprotected. Never attach this class to a real bus, QML, identity IPC, phone permission API or production account. Real host-owned verification and revocation are **unimplemented**.

### CHECKLIST
- [x] Verify PR #1033 merged and reacquire current main.
- [x] Inspect Identity Center request boundary and Social/Phone ownership.
- [x] Implement synthetic per-person/device/line/org grant check and revocation.
- [x] Add adversarial CI fixtures and exact contract.
- [ ] Exact-head CI successful and operator review.
- [ ] Assign real grant host / Identity Center owner and security review.
- [ ] Explicit authorization for actual Android phone access and live tests.

### NEXT
Review this draft PR. The next separate task is a **host-side trusted grant design**, not automatically connecting the fixture receiver to a real KDE daemon. Confirm source ownership and live Hospital state before that assignment.

### DECISIONS
Preserve operator-selected network-first architecture, optional Bluetooth fallback, Android and iPhone targets, single Social Hub UI, separate personal/org boundaries and no duplicate-send policy. No local machine modifications, PR merge, live phone access or production activation.
