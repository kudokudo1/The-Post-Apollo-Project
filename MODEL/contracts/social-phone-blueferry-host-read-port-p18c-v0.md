# Social PHONE P18c // Unique-owner BlueFerry host read port

> **STATE:** Provider-side GitHub implementation only. This is **not** the trusted Identity Center host, an approved authorization policy, a consent grant, a live Social inbox or a production deployment.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project` · **ROOM:** Social PHONE P18c provider read-port continuation, external Hospital-compatible only. **STAFF:** OPEN AI // CHATGPT, DOC-style external worker, not a verified live Hospital assignment. **BASE:** main `b8d3e83fdfe180691253988e098385ae30312cff`, P18b PR #1370 merged, no active PHONE PR collision at the first check.

## IMPLEMENTATION

The existing P18a converter handles decoded BlueFerry data. This bounded change introduces **`services/phone/BlueFerryHostReadPort.py`**, an importable, host-only provider port that can read the running BlueFerry daemon **if and only if a future host explicitly calls it**. The module has **no executable CLI or QML binding**, does not read at import time, and is not called by CONNECT PHONE.

`UniqueOwnerBlueFerrySource` resolves `io.weirdware.BlueFerry` on an already-running **session** D-Bus using `name_has_owner`, then calls only the returned unique owner such as `:1.99` with `introspect=False`. It never method-calls the activatable well-known name. The supported provider interfaces, verified from upstream BlueFerry source, are:

- `Messages1.GetStatus()`, bounded to 32 KiB; `phone_profile_id`, `api_version=2`, `daemon=true`, typed MAP/PBAP evidence.
- `Messages1.ListThreads(u)`, called only for the exact `messages.read` operation, bounded to 64 threads and a 2 MiB decoded JSON budget. The P18a converter retains native message handles and explicit timestamps; no sending, marking read or replying.
- `Messages1.ListContactCards(uus)`, first bounded page only (offset 0, max 100, empty search); JSON capped at 256 KiB; call only for `contacts.read` after GetStatus reports a valid `contact_card_epoch` and contact-card support.
- No contact photos, GetContact detail fetch, system calls, service startup, Bluetooth changes, oFono or audio routing.

`read_for_trusted_host(operation, profile_id, source, host_guard, host_release)` is a **host integration seam**, not a grant validator. The supplied guard is called before private data retrieval and after backend recheck. Every read checks the current provider **unique owner**, exact current **opaque phone profile**, capability and, for contacts, matching daemon epoch **both before and after** fetching. A changed owner/profile/capability/epoch or malformed provider payload blocks the host-release callback.

The provider snapshot is sent *only* to the caller-supplied **`host_release` callback**, not returned as a CLI result. The callback must be implemented by a separately approved privileged host that authenticates its actual client, holds the real consent/device/line/session scope, serializes release against revocation, audits without exposing content, and clears UI data after revoke/context switch. A Python guard returning True alone is **not** authentication, a secure IPC boundary or atomic revocation; an untrusted program could provide a fake callback. This module therefore must not be exposed directly to QML.

The return envelope is a small content-free result with `HOST_HANDOFF_REPORTED`, `HOST_RELEASE_REFUSED`, `HOST_DENIED`, `PROVIDER_CHANGED`, `PROVIDER_UNAVAILABLE` or `REFUSED`. `HOST_HANDOFF_REPORTED` means only that the caller-supplied callback reported completion. It is **not** evidence that Social is connected or that a production grant exists.

## HOW TO USE

**Future host owner only:** construct the source inside the approved phone-data process, provide its authenticated/revocable `host_guard` and atomic `host_release`, and call the read port for exactly `messages.read` or `contacts.read`. Check the provider permission and BlueZ/device/line binding in the **trusted host**. The user-facing PHONE panel still shows channel diagnostics only.

**Current operator:** no new steps, login requirement, system service or terminal. Do not test a real iPhone by importing the provider reader directly from a desktop script; it is not an approved access path.

## VERIFY

Offline tests:
- `tests/phone/test_blueferry_host_read_port.py`: fake provider session bus, actual D-Bus method names/arguments and unique destination; invented synthetic thread and contact payloads; scope mismatch, provider owner replacement, MAP/PBAP state changes, stale contact epochs, malformed private data, guard denial before and after read, refused host release and content-free errors.
- `tests/messaging/test_social_phone_host_read_port_boundary.py`: the read port has no executable CLI or direct QML wiring, conforms to P18a and leaves the existing PHONE `ContactList`/`ChatFeed` empty and sending disabled.
- Existing PHONE CI workflow compiles and runs both suites.

GitHub checks do **not** verify installed BlueFerry API compatibility on the user's host, physical iPhone pairing/permissions, real D-Bus reads, Identity Center grants, organization isolation, revocation or Quickshell rendering.

## WATCH OUT FOR

The current cross-owner `MODEL/contracts/social-phone-identity-host-integration-handoff-p1-v0.md` remains **PROPOSED** and identifies **unassigned security/Identity and Account Broker authority**. Until the operator and owning workers accept the process boundary, the code must remain disconnected from the Social UI. Merely being the same Linux UID as a BlueFerry D-Bus session does not create confidentiality against other same-UID applications. BlueFerry's own D-Bus authorization is distinct from Post-Apollo's account/organization authorization.

Unverified provider status is not a content grant. The saved device nickname is not a login, and a local organization name is not a verified tenant. Messages and contacts are separate permissions, and a message-read capability never authorizes send.

Working iPhone media routing and FaceTime audio are not modified by this PR. oFono remains a separate HFP/calling workstream.

## CHECKLIST

- [x] Verify P18b merge, fresh main and no open PHONE ownership collision.
- [x] Inspect canonical Syntagma/Hospital and shared Social adapter/Identity ownership.
- [x] Verify upstream BlueFerry real D-Bus signatures and async `ListThreads` compatibility.
- [x] Implement explicit host-constructed, unique-owner-bounded read methods.
- [x] Tie reads to exact profile, capability and contact epoch before/after.
- [x] Require externally supplied host guard and release callback.
- [x] Add mocked D-Bus and per-operation regression tests; extend PHONE CI.
- [ ] Exact-head GitHub CI.
- [ ] Operator review and PR merge.
- [ ] Assign/approve Identity Center + Account Broker host authority and threat model.
- [ ] Implement and verify authenticated host IPC and atomic revocation barrier.
- [ ] Connect a trusted, revocable Social adapter and perform live iPhone acceptance.
- [ ] Independently verify oFono/HFP path for calls on PC.

## NEXT

A cross-owner **host implementation decision** is the next blocking dependency. Once accepted, the privileged host can use this provider reader and P18a converter, then release scoped data through a reviewed adapter into the existing Social contact list/conversation feed. First release should be **read-only** for a specifically selected Personal iPhone, with independent contact permission and a revoke/context-change wipe. Phone sends, multiple-iPhone profile switching, organizational phone-line grants and automatic background updates require separate authorized assignments.

## DECISIONS

The provider component does real read-method integration work **without installing or activating any reader**. GitHub draft PR only; no local machine writes, pairing, audio changes, consent bypass, merge or production deployment. Operator retains final acceptance. Rollback: close the draft PR, or revert only this bounded PR if later merged.
