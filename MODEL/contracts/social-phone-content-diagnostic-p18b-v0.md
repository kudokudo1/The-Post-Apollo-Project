# Social PHONE P18b // iPhone message and contact channel diagnostics

> **STATUS:** Github-only bounded implementation, no live data bridge or approved protected host.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`
> **ROOM:** Social PHONE continuation / P18b content-free channel diagnostics (external Hospital-compatible, no live Room registration verified).
> **STAFF:** OPEN AI // CHATGPT, DOC-compatible external developer, no global Identity/Account Broker authorization.
> **BASE:** main `5c1faab33836388175038c59d52231fad6c921e5` (freshly checked 2026-11-06). Prior P18a PR #1366 merged and no open PHONE collisions.

## IMPLEMENTATION

The existing Social PHONE UI already probes BlueFerry pairing/service readiness via P16 and displays a data-free phone content panel. This slice adds a **single-click, content-free data channel diagnostic** in the same one-button workflow.

- `services/phone/PhoneContentDiagnostic.py --inspect` calls existing `PhoneDeviceObservation.observe()` and `_running_profile()` helpers. It requires the same exact opaque active BlueFerry profile ID from the BlueZ-verified paired device and BlueFerry GetStatus before interpreting MAP/PBAP booleans. It does not open Contacts or Messages interfaces.
- It can return `BACKEND_REPORTED`, `DEVICE_OFFLINE`, or `UNAVAILABLE`. MAP and PBAP each have distinct `*_ACTIVE_BACKEND_REPORT` and `*_INACTIVE_BACKEND_REPORT` values. Optional `contact_card_count` is accepted only as a bounded integer; null means unreported, not zero. This is provider **self-report**, not proof messages/contacts are populated, consented, complete, or available to Social.
- The CLI prints only the fixed status shape and optional numeric contact card count. It exposes **no** phone name, Bluetooth address, device profile ID, phone number, message handle or message text. Backend errors fail closed without printing their content.
- In `widgets/messanger/PhonePane.qml`, the existing CONNECT PHONE action runs this helper once. The DEVICE panel gets separate `IPHONE MESSAGE DATA` and `IPHONE CONTACT DATA` explanations. MESSAGES and CONTACTS use the same status to explain their empty native Social feed. The helper is also rechecked after an explicit native setup stage closes.
- Existing ContactList and ChatFeed remain `conversations: []`, `messages: []`, `sendEnabled: false`. No third-party data, authorization, pairing, music/call audio settings, oFono installer flow, or persistent phone database is modified.
- No unrequested background polling is introduced, and the diagnostic state resets on menu reopen. READ_ONLY is not content-ready.

## HOW TO USE

After operator review/merge and separately approved desktop update, open **Social → PHONE → CONNECT PHONE**. On DEVICE, inspect the message MAP and contact PBAP states; in MESSAGES or CONTACTS, read the specific explanation of the absent feed.

- If MAP/PBAP is not reported active while desktop audio works, the phone's **data profiles** may need separate Bluetooth permissions or BlueFerry setup. iOS availability remains version/provider-dependent.
- If MAP/PBAP is reported active, that **does not** mean Social has messages or contacts. A separate trusted, consented, revocable host reader is still needed. BlueFerry may have no cached messages even when MAP is active.
- A reported number of cached contact cards is an observation of BlueFerry's local cache only. Zero and unavailable are different conditions.

## VERIFY

- `tests/phone/test_phone_content_diagnostic.py` uses mock observations: exact UUID/profile match, disconnected vs paired, wrong/malformed backend, independent MAP/PBAP flags, valid/missing/zero contact counts, sanitized errors, no backend invocation when paired-offline, and explicit CLI flag enforcement.
- `tests/messaging/test_social_phone_content_diagnostic_ui.py` checks only the intended one-button QML flow, fail-closed schema validation, visible per-tab explanations, reset behavior and no live message/contact/sending access.
- The existing PHONE setup workflow compiles and runs both tests with the prior suites.
- Source-check and CI are not live Fedora/iPhone or actual Quickshell screenshot verification.

## WATCH OUT FOR

**Remaining production blocker:** `MODEL/contracts/social-phone-identity-host-integration-handoff-p1-v0.md` is a proposal, not an approved host or actual authenticated grant. Its named Identity/security and Account Broker owners are not verified assigned here. A backend-reported MAP/PBAP session must never be used as authority to call BlueFerry ListThreads/ListContactCards from the untrusted Social QML process. A same-UID D-Bus session is not a completed cross-account privacy boundary. Never claim org-specific authority from a Personal phone nickname, manual LLC/nonprofit label, or active BlueZ pairing.

**Device count and audio:** BlueFerry may support one selected iPhone only. No multiple simultaneous iPhone management is inferred. Working A2DP/iPhone FaceTime audio is separate from MAP/PBAP and oFono/HFP calling. Do not reset it while diagnosing content.

## CHECKLIST

- [x] Recheck main, merged P18a, active PR ownership and Syntagma protocols.
- [x] Verify BlueFerry's real GetStatus `map`, `pbap`, and `contact_card_count` fields.
- [x] Reuse P16 exact-profile observation without exposing the profile ID in diagnostics.
- [x] Add content-free MAP/PBAP diagnostic with honest inactive/unverified states.
- [x] Integrate the explanation into the existing PHONE UI, preserve empty feed.
- [x] Add synthetic Python and UI contract tests and CI hooks.
- [ ] Exact-head GitHub CI.
- [ ] Operator merge approval.
- [ ] Separately authorized live desktop verification.
- [ ] Real Identity/Account Broker security ownership and protected host approval.
- [ ] Authorized BlueFerry reader → P18a converter → existing Social feed.

## NEXT

**P18c** is a cross-owner assignment, not a safe unilateral source patch: approved privileged service authenticates session/principal, exact provider profile/phone line and operation-specific consent; binds D-Bus unique owner; checks revocation at release; then calls real BlueFerry ListThreads/ListContactCards and feeds sanitized scoped data into the existing Social router. Real send and group confirmation still need a separate grant and provider confirmation lifecycle.

**Parallel:** retain oFono calling installer repair and independent HFP mic/speaker tests without touching the working Bluetooth media route.

## DECISIONS

Keep one primary Connect Phone, one existing Social PHONE window, network-first per capability where supported, optional Bluetooth only where required, and no false content authorization. Never confuse BlueFerry's provider status with a signed user-device grant. Repo draft PR only, no local OS change, merge or deployment. Rollback is to close the draft PR or revert its bounded commit if later merged. Operator retains acceptance.
