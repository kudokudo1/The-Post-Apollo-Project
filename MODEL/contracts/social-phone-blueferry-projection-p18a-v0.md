# Social PHONE P18a // BlueFerry conversation and contact projection

> **STATUS:** GitHub-only provider normalization milestone, **not** a live content bridge. No SMS/iMessage read, contact read, send, permission grant, pairing, Bluetooth, audio, or oFono host change was authorized or performed.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project` · **STAFF:** OPEN AI // CHATGPT external DOC-compatible worker · **ROOM:** Social PHONE P18a recovery/normalization continuation, Hospital-compatible only; no verified registered live assignment.
>
> **BASE:** fresh main `67c1ea5952bf4c189d6383b7c4b50986971534e7`; P17 PR #1363 merged; no colliding open Social PHONE PR at preflight.

## IMPLEMENTATION

`services/phone/BlueFerrySocialProjection.py` is a **pure, offline, service-scoped converter** for decoded results that a future **trusted and authorized host** may supply after independent authentication and consent checks. It imports no D-Bus, BlueZ, networking, OS storage, QML, or provider client, and exports no command that reads the user's phone.

Upstream-verified BlueFerry interfaces on the existing session D-Bus:
- `io.weirdware.BlueFerry.Messages1.ListThreads(u)`: list of threads, each with `key`, `name`, `is_group`, `reply_ready`, `unread`, `messages_truncated`, and `messages` containing `handle`, `body`, `timestamp`, `outgoing`, `read`, and optional `sender`. These native fields are defined in the BlueFerry `threads.py`, `models.py`, and `dbus_service.py` sources and are **not** an official Apple Messages API.
- `Messages1.ListContactCards(uus)`: a paged `{"contacts": [], "total": 0, "offset": 0, "query": ""}` shape with per-card `id`, `name`, `organization`, `primary`, `phone_count`, `email_count`, `has_photo`. Upstream documents that **card IDs are ephemeral** and must be reloaded after the daemon's `contact_card_epoch` changes.
- This is a **snapshot of BlueFerry's local cache**, not a promise of every historical iMessage. BlueFerry's experimental MAP/PBAP sessions and encrypted history/phone permissions determine availability.

`normalize_threads(payload, profile_id=opaque_uuid)` maps conversations to the existing approved shared contract's `id`, `serviceId=blueferry`, `type`, `displayNameInProfile`, `lastMessage`, `unreadCount`, and messages to `id`, `conversationId`, `body`, `direction`, `sent_at`. Conversation identity namespaced to the exact BlueFerry profile ID plus native thread key, never to an unverified user label. Message IDs retain the provider message handle; missing handles fail closed rather than fabricate stable identifiers. Duplicate identical records collapse, conflicting IDs fail closed. Messages sort oldest to newest; native timezone-aware ISO timestamps are retained explicitly with `timestampUnit=iso8601-offset` because the common Social timestamp unit is not frozen. Truncated histories explicitly mark unread counts non-exact.

`normalize_contact_page(payload, profile_id=opaque_uuid, daemon_epoch=...)` returns **contact-card rows separate from conversations**, scoped by the supplied BlueFerry profile and the provider daemon epoch; contact IDs are **not** durable cross-restart identities. There is no photo-byte access, contact merge into personal/company directories, or automatic message composer enablement.

Both functions bound array and text sizes and reject malformed native payloads with content-free error text. Returned metadata says `execution=OFFLINE_PROJECTION_ONLY`, `authorization=NOT_EVALUATED`, `routeEligible=false` specifically to prevent a conversion result being mistaken for an access grant.

## HOW TO USE

**Developers / future authorized bridge only:** import `BlueFerrySocialProjection` and pass already-validated, already-authorized, decoded BlueFerry `ListThreads` or `ListContactCards` results. Use the provider's matching opaque `phone_profile_id`. For contact cards, also pass an epoch observed from the **same D-Bus daemon owner and current contact cache**. It is the future host's responsibility to check real desktop principal, active session, paired profile/device, phone line, permission evidence and user-selected PERSONAL/verified ORGANIZATION scope, enforce revocation and constrain the returned projection to that exact scope.

**Current Social user:** the PHONE feed remains empty by design. No Connect Phone action invokes this converter or reads private data. This is a prerequisite for the actual data path, **not** completion of it.

## VERIFY

Offline tests under `tests/phone/test_blueferry_social_projection.py` use *synthetic* messages and contacts to verify native shape handling, stable scoped identity, chronological order, duplicate/replay conflicts, unread/truncated logic, group senders, permanent-vs-ephemeral ID semantics, strict size/type checks and no side-effect imports. `tests/messaging/test_social_phone_blueferry_projection_contract.py` checks the existing approved Social field names and that `PhonePane.qml` stays locked to empty contacts/messages until an authorized host exists. The PHONE setup workflow compiles and executes these tests.

**Not yet verified:** Identity Center/Account Broker owner acceptance, production private IPC peer-authentication, host-to-provider D-Bus authentication/authorized read, Apple-side MAP/PBAP permissions, end-to-end revocation before UI release, live phone content, Quickshell rendering or real send/read outcomes.

## WATCH OUT FOR

- **Cross-owner gate is still open.** Canonical `MODEL/contracts/social-phone-identity-host-integration-handoff-p1-v0.md` describes the proposed protected host and says the verified Identity Center/Account Broker owner is unassigned. Syntax validation and a same-UID D-Bus session do **not** create a trusted device/session/line grant. Never activate `ListThreads`/contacts from the untrusted QML layer or command subprocess based only on `phone_profile_id`, nickname, BlueFerry GetStatus, or a local organization name.
- No bridge that automatically reads or displays personal messages is included here. Personal texts must not silently follow a switch to one of the user's LLC or nonprofit identities.
- BlueFerry may have no local message history even while A2DP audio is working. Sync-Contacts permission and MAP are independent of the media route. oFono/HFP affects calling, not the message/contact data parser.
- Group threads may be ambiguous. This mapper exports the provider's `reply_ready` **as observation only**; it does not enable sending, retry ambiguous sends, or transfer group-reply decisions to Social.

## CHECKLIST

- [x] Verify merged P17 and fresh main / no active PHONE collision.
- [x] Re-read Syntagma AGENTS/Hospital/working and Identity trusted-host contracts.
- [x] Inspect actual upstream BlueFerry messages/contacts wire and models.
- [x] Implement pure, bounded conversion with scope-specific IDs and content-free failures.
- [x] Add synthetic backend and shared-contract tests, wire CI.
- [ ] Verify exact-head CI.
- [ ] Obtain Identity/Account Broker owner acceptance and actual trusted host assignment.
- [ ] Build verified private content read/revocation boundary, then QML adapter integration under Social router owner.
- [ ] Test actual iPhone permissions, live contacts/messages, organization switching and history behavior.
- [ ] Separately repair/verify oFono HFP without changing working A2DP.

## NEXT

**P18b blocked pending cross-owner security acceptance:** build an authorized provider-read broker, keyed to exact authenticated desktop user + BlueFerry profile + phone line/capability + active organization and revocation generation, with caller peer authentication and no persistence of decrypted data beyond the approved scope. Then feed the existing Social PHONE ContactList/ChatFeed through a shared router-owned adapter; enable send only after provider-specific confirmation semantics and group safeguards are tested. If the approved host is not yet available, keep `conversations: []`, `messages: []`, `sendEnabled: false`.

**Separate lanes:** verify genuine provider-supported multi-iPhone switching; finish Fedora oFono installer and WirePlumber/HFP test for calls. Neither requires this mapper to change working Bluetooth audio.

## DECISIONS

No new login ceremony, no second Social phone window, no private data read without approved host, no duplicate phone-content database, no guessed histories, no fake recipient IDs, no production activation. Operator owns final review, merge and acceptance. Close the draft PR to drop the proposal; if later merged, revert only the bounded P18a commits for rollback.
