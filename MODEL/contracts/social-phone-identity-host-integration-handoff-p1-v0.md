# Social Phone Bridge // Identity Center trusted-host integration handoff P1 v0

> **STATE //** PROPOSED CROSS-OWNER CONTRACT. Operator review and Identity Center/security acceptance required. This file is **not** an approved production architecture, authenticated service, real grant or runtime activation.
>
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`
>
> **DATE //** 2026-11-02. **BASE //** `main` at `20c3c9aa92c57ee896465fba04d7e092ebbf3bb6`. PR #1038 (serialized synthetic host) and PR #1041 (manual local organizations in Social Settings) verified merged before this branch. Recheck current main, diff and live ownership before changing any shared seam.
>
> **CONNECTION //** OPEN AI // CHATGPT, external Hospital-compatible; no live Room, Session, Staff Role, Assignment or registered checkpoint verified.
>
> **SCOPE //** This contract and MODEL index only. No edits to `services/identity/*`, `services/social/*`, `widgets/messanger/*`, `services/phone/*.py`, `services/phone/qt/*`, QML, KDE Connect, device configuration, tests, existing authorization fixtures or local machine.
>
> **STATUS OF OWNERSHIP //** Identity Center/security owner **unassigned for this integration**, Account Broker provider-permission/device-link owner to be coordinated, Phone Bridge provider worker bounded to isolated read-only diagnostics, shared Social UI integration owner retains router/settings control. This document does not grant or assume those ownership roles.

## 1 // The concrete gap to close

Today the Phone Bridge has tested but **non-authoritative** Python grant, subscription and serialized-delivery fixtures. The Qt SMS receiver listens only to the fake `org.postapollo.phone.fixture`, not to `org.kde.kdeconnect`. Identity Center already has experimental OIDC/desktop-host, scoped-policy and request-boundary code, but no approved production phone grant authority or end-to-end user/session/device/line trust binding.

[Identity Center local organization directory v1](./identity-center-local-organization-directory-v1.md) introduced by merged PR #1041 saves **local display names and branches**, not authenticated memberships, verified tenant IDs or grants. A user may create/rename `LLC`, `NONPROFIT` or `OTHER` labels locally. These are valid navigation data and **must never be used as authorization principals, tenants, roles, legal ownership proof or phone line grants**.

The current [Identity Center plan](./post-apollo-identity-center-upgrade-plan-v0.md) assigns authenticated principals, organization membership, revocation and consent to Identity Center; signed authentication to the identity provider; provider permission evidence/account linkage to Account Broker; and Social UI consumption to Social. The [network-first phone ADR](./social-phone-bridge-network-first-adr-v0.md) preserves Android/iPhone feature differences, per-capability routing and explicit Bluetooth fallback.

**Decision needed:** who owns a real privileged Phone Access Grant authority and its revocation/delivery barrier, and what minimally sufficient trusted API the Phone Bridge can call without touching session tokens or external provider credentials.

## 2 // Proposed trust boundary: no client-side authorization

```text
Social USER // SETTINGS -> CONNECTED ACCOUNTS / PHONE
  - labels, selectors, requested operation, sanitized status only
                     |
                     v
Identity Center authenticated, privileged host (PROPOSED OWNER)
  - IdP verification + issuer/audience/expiry/revocation
  - principal + active organization membership from trusted backend
  - explicit consent and audited grant issuance/revocation
  - device/line owner binding and generation/version
                     |
                     v
Privileged Phone Bridge operation broker (DESIGN PENDING)
  - per-operation, per-event, per-line authorization
  - provider/plugin/transport evidence and exact sender/daemon owner
  - serialized revocation and content-release barrier
                     |
                     v
KDE Connect Android provider (ONLY IF VERIFIED)
  - read-only pilot first; no send, contacts or calling by inheritance
                     |
                     v
Protected, scoped message projection -> existing Social UI
```

This separation is a **proposal**, not a promise that a Python object becomes a privileged process. The first implementation assignment must decide actual OS process isolation, IPC peer authentication, credential protection, grant storage and revocation transport. **A same-UID D-Bus client may be able to call KDE Connect directly outside our broker.** A lock in a Python test fixture does not prevent a different local program from querying the session bus. The host and security owner must define the real threat model and OS-level enforcement boundary before claiming confidentiality against other local applications.

The user's selected Social `identity-N`, manually entered organization name, portfolio, branch, phone number and KDE Connect device path are **untrusted selectors**, not proof of identity or ownership.

## 3 // Proposed host-internal records and operation contracts

These are *type/field proposals only*. No socket, HTTP method, D-Bus API, QML action or production return value is implemented by this document.

### 3.1 Trusted identity and phone ownership

**Host-resolved session facts** (never accepted as raw client claims):

- `principalId`, `issuer`, `audience`, `subject`, `sessionId`, `authenticationTime`, `expiresAt`, `revocationVersion` and assurance level, all validated with signed identity evidence and trusted clock.
- Active `organizationId` memberships plus separately checked delegation/administrator power to issue grants for an organizational phone. Branch/role selection may **further restrict**, never broaden, the rights.
- Device `deviceBindingId`, mobile `platform` (independently verified Android for P1), KDE Connect sender owner/connection identity, and `lineBindingId` established from approved device/SIM ownership proof. Raw phone number, Android `sub_id` or display name cannot serve as authority.
- Current network transport evidence, SMS plugin/Android-side permission attestation and revocation/expiry. `LOCAL_PLUGIN_LOADED` is **not** permission and a Bluetooth link must not silently satisfy network-only policy.

**Authoritative grant record, proposed:** `grantId`, `principalId`, exact `deviceBindingId`, exact `lineBindingId`, `ownerKind=PERSONAL|ORGANIZATION`, `organizationId|null`, `operation`, `consentReceiptId`, `approvedBy`, `issuedAt`, `expiresAt`, `revokedAt|null`, monotonic `grantGeneration`, and `auditCorrelationId`. No wildcard org, line or device. `messages.receive`, `messages.read`, `messages.send`, `contacts.read`, `notifications.receive`, `calls.dial`, `calls.answer`, `calls.audio` and `calls.hangup` remain independent permissions with independent backend evidence.

**Private owner-managed methods to be agreed**, not public endpoints: `resolveVerifiedSession`, `listAuthorizedDevicesAndLines`, `createPhoneAccessGrant`, `revokePhoneAccessGrant`, `evaluatePhoneOperation`, `registerRevocationWatch`, and `releaseScopedMessageEvent`. Only a trusted service can create/revoke grants and deliver data. The Social UI may request an approved flow, but it must not supply `principalId`, `grantId`, authorization flags, signed proof, or desired trust level.

### 3.2 Client request intent (illustrative, NOT authority)

```json
{
  "contract": "post-apollo.phone.host-intent.v0-proposal",
  "operation": "requestReceiveAccess",
  "deviceSelector": "device-fixture-a",
  "lineSelector": "line-fixture-a",
  "ownerKind": "ORGANIZATION",
  "organizationSelector": "org-fixture-a",
  "requestedCapability": "messages.receive"
}
```

The host authenticates the *actual calling session* via protected IPC and reads signed authoritative membership independently. Even a valid organization selector and locally displayed branch name cannot create a grant. The host may require explicit device-side consent and reauthentication. The proposed pilot supports `messages.receive` only; historical read, send, contacts and calling are separate authorizations.

### 3.3 Sanitized UI result (illustrative, NOT a capability grant)

```json
{
  "contract": "post-apollo.phone.host-status.v0-proposal",
  "status": "PERMISSION_REQUIRED",
  "operation": "messages.receive",
  "platform": "UNVERIFIED",
  "transport": "UNVERIFIED",
  "contentAccessEnabled": false,
  "routeEligible": false
}
```

Before a real signed session, real grant store and verifiable device exist, reports must remain `UNAVAILABLE`, `PERMISSION_REQUIRED`, `UNVERIFIED` or `UNSUPPORTED`, never `CONNECTED`/content-ready just because a fixture matched. Status reports contain no phone number, body, token, session handle, grant secret, principal/org ID or raw KDE metadata. UI copies are projections, never decision sources.

## 4 // Revocation-to-delivery ordering contract (proposed acceptance rule)

A *single authoritative host* must serialize content release and revocation **for the same grant generation and device/line scope**. A future implementation can use a serialized broker command loop or durable transaction barrier; the exact primitive remains an owner decision. A `threading.RLock` in `SerializedPhoneHostFixture.py` demonstrates local ordering **only**.

Proposed safety invariants:

1. At subscription start, prove person/session, exact device and line, owner organization membership, explicit receive grant, Android SMS permission, active permitted network path and KDE sender continuity. Do not reuse a prior context's grant.
2. At event ingress, bind one immutable `(principal, ownerKind, organization, device, line, operation, grantGeneration, subscriptionEpoch)` envelope **inside the privileged broker**; reject mismatched sender, device or context and buffer only minimum content.
3. Immediately before protected delivery, re-evaluate the trusted current grant and permission versions. If revoked, session expired, membership changed, sender changed, device unlinked, transport downgraded or the request switched context, discard buffered content, increment epoch and stop the receiver.
4. A revocation is **committed** at the accepted durable host-side barrier. Once committed, no event from that grant generation may be released. If a release already committed first, revoke cannot undo that delivery; host/UI retention and purge rules must address already displayed content.
5. Any callback from an earlier epoch is refused even after a new grant appears for the same device/line. Re-grant is a **new** authorization, not restoring an old subscription.
6. On ambiguous state, lost revocation feed, backend outage, verifier/clock error, conflicting grants or provider permission change, fail closed and cancel the stream; do not silently switch to Bluetooth.
7. `messages.send` must independently prevent duplicate sends and avoid retry when provider outcome is unknown. A receive grant must never authorize send.

**Cancellation triggers:** sign-out, explicit revoke, organization membership loss, device unlink, SIM/line switch, role/branch restriction change, host session expiry, OS screen/lock policy where required, KDE daemon sender replacement, SMS plugin denial, transport loss, or time rollback. The owner must define event delivery, cache invalidation and UI wipe semantics for each.

**Audit without leaking content:** actor/approver, scope reference or hashed surrogate, operation, grant generation, consent receipt, decision code, correlation ID and timestamp may be recorded in a protected audit store. Never log SMS bodies, recipient numbers, credentials, raw D-Bus replies or full message/attachment metadata. Audit retention and privacy obligations require a separate decision.

## 5 // Ownership and integration handoff

| Owner / affected subsystem | Proposed responsibility | Explicit non-goal in this slice |
| --- | --- | --- |
| Identity Center and security owner | Authenticate person, verify active org and delegation, decide grant store/IPC, audit and revocation generation | Do not infer legal ownership from Social's local organization editor |
| Account Broker | Resolve approved device/provider connection and exact permission evidence, coordinate consent and reconnect | Never treat a KDE plugin flag as provider-granted SMS permission |
| Phone Bridge owner | Verify KDE sender/transport/device binding, operation-specific probes, event epochs and cancellation | No real D-Bus SMS subscription or send before authority is accepted |
| Social integration owner | Show PHONE availability and scoped content in existing Social window, clear after context change | Do not edit shared QML/router or convert local labels into grants |
| Operator | Accept process ownership/trust boundary and authorize real desktop/device diagnostic separately | Merge of proposal is not production activation |

**Current collision note:** PR #1041 is merged, but its `services/social/SocialOrganizationDirectory.py` and settings QML remain **local metadata**, not Identity Center membership. This contract must not mutate or reinterpret their storage. Ownership is still required for changes to Identity Center APIs, `services/social` and the shared Social UI.

## 6 // Implementation sequence proposed for the assigned owners

- **Gate A, owner decision:** nominate the privileged host/security and Phone Bridge integration owners. Review process isolation and the same-UID D-Bus threat model, signed IdP verification, grant database, audit policy and protected IPC. Agree the authoritative revocation linearization point.
- **Gate B, disposable host test:** an isolated service runs authentication, exact device/line grant issuance/revoke and revocation barriers with fake sessions, fake provider evidence and no phone content. Test different principals and independent LLC/nonprofit contexts; do not reuse synthetic fixtures as actual auth.
- **Gate C, read-only Android acceptance:** separately approved test phone/session confirms platform, encrypted LAN route, KDE daemon sender, SMS plugin permissions and one disposable message only. Explicit opt-in, no history pull, no auto-start.
- **Gate D, Social integration:** integration owner connects a protected scoped message projection/status to the existing Social PHONE area; performs sign-out/tenant switch wipe and concurrent revoke tests. No send path.
- **Gate E, separate capabilities:** only after proven read-only path may history, send, contacts, call control and PC audio be evaluated individually. iPhone remains a separately evidence-gated track.

## 7 // HOSPITAL HANDOFF

### IMPLEMENTATION
Cross-owner **proposed** Identity Center ↔ Phone Bridge host contract. This change is documentation only; it creates no service, schema migration, test callback, IPC port or runtime change.

### HOW TO USE
Review this contract and assign the host/security and Phone Bridge owners. Compare the API/commit-barrier proposals with Identity Center's existing session host and policy source before accepting. No new Post-Apollo UI control exists.

### VERIFY
Check exact branch/files and the merged current code. Confirm this PR contains only the contract and index. Prior 176 Phone Bridge tests prove isolated fixtures, **not** a trusted host; no new runtime/CI test is claimed here.

### WATCH OUT FOR
The organization/branch editor is local-only. The Identity Center OIDC/session hosts are experimental; this is not an authenticated production Phone Grant implementation. Local same-UID D-Bus access must be threat-modelled. No personal data, SMS, secrets or real phone tests belong in this PR.

### CHECKLIST
- [x] Verify #1038 merged; inspect current main and relevant identity/phone code.
- [x] Verify #1041 merged and local-only organization semantics.
- [x] Preserve the Social, Identity Center and Phone Bridge ownership fences.
- [x] Define proposed grant record, status, revocation barrier, owner map and acceptance sequence.
- [ ] Operator/Identity Center security-owner review and acceptance of contract.
- [ ] Explicit grant-host implementation assignment and process boundary decision.
- [ ] Separately approved real host/device diagnostic and actual SMS read acceptance.

### NEXT
Ask the Identity Center/security owner to accept, revise or reject Gate A and establish actual implementation ownership. This cross-owner design must **not** be silently converted to a real subscriber by the current external Phone Bridge worker.

### DECISIONS
Preserve network-first per-capability routing, Bluetooth only explicit fallback, separate iPhone/Android evidence and single Social window. **No new security architecture is final until accepted.** No live Hospital registration, local machine modification, automatic PR merge or production activation.
