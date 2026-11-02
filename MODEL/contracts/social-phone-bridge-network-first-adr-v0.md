# ADR // Social Phone Bridge: network-first, Bluetooth as optional capability fallback (v0)

> **STATUS //** OPERATOR-SELECTED ARCHITECTURAL DIRECTION (2026-11-02); detailed contracts and feasibility remain PROPOSED / UNVERIFIED. Documentation only.
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`
> **DOMAIN //** Social Hub / cross-platform phone integration (iPhone and Android)
> **SOURCE //** Operator discussion, 2026-11-02: use the user's phone, contacts, messages and cellular calling from the PC; support both iOS and Android; minimize Bluetooth and reserve it as an alternate backend when an approved network method cannot provide the function.
> **OWNER //** Proposed Social Phone Integration owner for its phone bridge; shared Social router/UI changes stay with the designated Social integration owner; Identity Center/Account Broker retains authorization and account-link ownership. No owner or worker assignment is created here.
> **SCOPE //** Architecture decision, capability boundaries, research gates, safe handoff. No source implementation, host install, pairing, credentials, account provisioning, remote service or runtime activation.
> **RELATION //** Complements [Shared Messaging Adapter Contract v1.0](../../services/messaging/ADAPTER-CONTRACT.md), [Provider Access](../../services/messaging/PROVIDER-ACCESS.md), [Social Account Manager handoff](./social-account-manager-handoff-v0.md), and [Identity Center multi-organization plan](./post-apollo-identity-center-upgrade-plan-v0.md). Does not supersede their ownership/security rules.

## 1 // Decision

**Select a network-first, per-capability phone integration architecture for the existing Post-Apollo Social Hub.** A verified, consented local-network provider or explicitly approved network service is preferred for each supported function. Bluetooth is an **optional alternate backend** only for functions with no usable, verified network route, or after an explicit and safe user-approved switch.

Do **not** equate “paired phone” with “all functions supported.” Bluetooth must not be continuously activated, polled, or connected for unrelated functions merely because it is paired. No predetermined '70% coverage' claim or automatic promise of iMessage/cellular-call access.

Users should see one integrated **PHONE** area in the existing Social window, with messages, calls and contacts. Platform-specific implementation differences are hidden behind truthful capability and connection states. The pre-existing Social selector and USER // SETTINGS -> CONNECTED ACCOUNTS are the intended entry points; exact UI placement and controls require shared UI-owner review. No second permanent floating window.

**Selected product intent (not a certified implementation):** use a real iPhone or Android phone from the Linux desktop for sending/receiving supported messages, making/answering supported phone calls through PC audio, contact selection, and notifications. A feature is available only when the actual paired/linked device and backend verify it.

## 2 // Why this choice

- **Network first:** local Wi-Fi/LAN, encrypted peer connection, or a provider-supported network API can offer better throughput and separation of features without monopolizing Bluetooth audio/profile ownership.
- **Bluetooth second:** Bluetooth HFP, MAP, PBAP or ANCS may expose a *subset* of otherwise unavailable iPhone/Android capabilities but are device-, OS-, firmware- and permission-dependent.
- **Capability first, not platform-first:** contacts can use Wi-Fi while cellular audio uses HFP; an Android SMS link can be ready while Android phone-call audio is not.
- **One product experience:** reuse the Social Hub, its contact/conversation surface, notification styling, and future Identity Center integration rather than inventing three independent Apple buttons or a second messenger.
- **Truth and reversibility:** an absent backend stays UNAVAILABLE/UNSUPPORTED; there is no fabricated message history, delivery receipt, login, or phone feature.

## 3 // Proposed logical architecture (design only)

```text
existing Social window / PHONE surface
    Messages | Calls | Contacts | Device status / settings
                       |
            Phone Integration Manager
     identity/device scope + capability routing + state
             /                      \
   message/contact facade       call control + audio facade
             |                      |
      verified backend registry per feature
          /             |             \
  LAN companion/     approved       opt-in Bluetooth
  KDE Connect        network API    MAP/PBAP/HFP/ANCS
          \             |             /
           Android or iPhone as actual device
```

**Phone Integration Manager (proposed owner):** device discovery and pairing references, user-selected transport policy, liveness, per-capability probing, request correlation, backend arbitration, fail-closed defaults, disconnected/degraded status and revocation. It must not become a credentials vault, enterprise authorization authority or telephony provider.

**Provider adapters (separate ownership envelopes):** network companion / KDE Connect candidate for Android, permission-scoped iOS companion for supported APIs, approved telephony/network service adapters, and isolated Bluetooth fallbacks. Do not use one provider's 'connected' state as another's capability proof.

**Messaging seam:** reuse the existing `services/messaging/ADAPTER-CONTRACT.md` with stable `(serviceId, nativeConversationId)` identity, provider-confirmed send semantics and inactive-adapter lifecycle. Do not modify `MessagingW.qml`, `AppSelector.qml`, `ContactList.qml`, `ConversationFeed.qml`, shared router or adapter schema without coordination with their integration owner. Expose phone-native message limitations accurately.

**Calling seam:** cellular call control and live audio are distinct from text messaging. Define a dedicated call-state controller and PC microphone/speaker routing, not fake 'calls' as message events. HFP audio/profile ownership may collide with PipeWire/WirePlumber/oFono/BlueZ; probe first. A network VoIP account is not automatically the user's existing carrier phone number.

**Contacts seam:** a device-scoped, permission-scoped contact projection with provenance and deduplication, not a silent replacement for Social identities, company directories, or a merged global address book. Store minimum necessary contact data; revocation invalidates protected local projections.

**Notifications:** show incoming messages/calls only when supported by the active backend and authorized notification scope. Do not claim a notification is a full synchronized conversation.

## 4 // Candidate capability matrix; verification required

| Capability | Preferred network route | Optional alternate / limitation | Current evidence level |
| --- | --- | --- | --- |
| Android SMS/MMS send/read | KDE Connect over encrypted local network (or verified companion) | Bluetooth message path only if independently implemented/tested | Existing third-party product capability, not Post-Apollo integration |
| Android contacts / notifications | KDE Connect or verified permissioned companion on LAN | PBAP when permitted; contact/notification coverage varies | Candidate, must verify exact API/device |
| Android carrier call handling and PC audio | Only if a verified phone/telephony companion or carrier route supports full audio/control | Bluetooth HFP + Linux audio stack if verified | Research; KDE Connect call notifications do **not** prove desktop call audio |
| iPhone contacts | Permissioned iOS contacts companion on LAN, if feasible | Bluetooth PBAP, explicit phone permission | Research / Bluetooth candidate |
| iPhone personal SMS/RCS/iMessage | No generic supported iOS LAN inbox/send API identified; evaluate lawful supported paths | Experimental iPhone MAP bridge candidate (e.g. BlueFerry), only after hardware and behavior verification | Unverified for Post-Apollo and user's iPhone; no assumed full-history/reaction/attachment fidelity |
| iPhone carrier call audio/control | Only an approved service genuinely routing the user's call/number to the desktop; iOS CallKit alone is not that bridge | Bluetooth HFP with verified PC audio and call control | Research; no verified network path for iPhone's ordinary carrier calls |
| FaceTime | Supported Apple device handoff; supported FaceTime link/browser participation where offered | No equivalent Bluetooth FaceTime desktop engine | Out of native call-audio scope |

**Important:** A custom iOS app may access user-approved contacts and app-owned data; this does **not** grant third-party access to the user's complete iMessage inbox or cellular call audio. Apple MessageUI is a user-approved compose sheet, not a background message transport. Apple CallKit primarily integrates an app's own calling/VoIP service, not arbitrary relaying of the cellular Phone app. KDE Connect iOS does not provide the same SMS/notification sync as Android. Never conflate these mechanisms.

BlueFerry (a third-party, experimental Bluetooth project) reports iPhone MAP messages and PBAP contacts, including iMessage observations; these are **project claims, not official Apple guarantees or independent acceptance on Post-Apollo hardware**. Treat iOS version, phone model, adapter, pairing permission, capability claims, send acknowledgements, attachment and group semantics as test variables. Licensing and service integration require review before reuse.

## 5 // Selection policy, fallback, and delivery safety

1. Evaluate the requested operation (`messages.read`, `messages.send`, `contacts.read`, `calls.dial`, `calls.answer`, `calls.audio`, etc.) for the **specific device, authenticated person/account scope, recipient, and active provider**.
2. Prefer an authenticated/authorized **network** implementation only if it advertises the exact capability and passes its current health and authorization check.
3. If none is usable, check whether the user explicitly enabled **Bluetooth fallback for that device and capability**; use only a verified compatible profile. Respect `Network only` and `Manual` modes.
4. If no reliable route exists, show `UNSUPPORTED`, `UNAVAILABLE`, `PERMISSION_REQUIRED` or an equivalent truthful state. Never substitute a different number/account/recipient.
5. Failed or timed-out sends remain **outcome unknown** until provider evidence resolves them. No automatic second-route retry when the first may have accepted the message. Correlate request IDs and provider-native identifiers, de-duplicate incoming events, and expose cancel/retry only when safe.
6. Do not move an active call's control/audio between network and Bluetooth mid-call without explicit proven support and operator-approved UX. Do not treat initiating a call as evidence that the call connected.

**Controls proposed in existing Social settings:** `Automatic (network first)`, `Network only`, `Choose manually`, plus per-device opt-in Bluetooth fallback and per-capability status. These are design labels, not current UI controls. Show exactly which backend carried each action in diagnostics without leaking content.

## 6 // Security, privacy, identity

- Pairing and contact/SMS/call permissions are user-initiated, explicit, revocable and bound to a device; do not collect phone passwords, Apple IDs, cookies, unlock codes or message bodies in GitHub/issues/logs.
- Encrypt in transit; prefer direct LAN transport; a hosted relay or carrier integration requires separate informed opt-in, threat review and retention policy. Do not send phone content to a cloud service by default.
- Use per-user/per-device authorization and scoped protected storage. A local Social `identity-N` label is **not** an authenticated human principal and is **not** company membership.
- Identity Center / Account Broker own person authentication, account links, grants and revocation. A person may separately link a personal phone and an organization-managed line; organization/portfolio switching never shares personal messages or contacts with other tenants automatically.
- Hide protected notifications when locked or switching identities; clear sensitive projections on explicit unlink/revocation according to approved retention policy.
- Discover platform support and libraries before code ownership changes. Do not change local Bluetooth daemon, PipeWire, services, firewall, iPhone settings or install packages without separate explicit operator approval.

## 7 // Staged plan and acceptance gates (proposed, not assigned)

- **P0 Contract and inventory:** map current Social registry, shared router, phone-state UI, Syntagma UI grammar, device presence and identity scope. Agree per-capability type/status/event contract without changing shared routing.
- **P1 Android network pilot:** isolated KDE Connect read/send SMS and contacts/notifications on disposable fixtures, then permissioned real-device acceptance; show service-specific status, revoke and reconnect.
- **P2 iPhone network feasibility:** test legally available iOS Contacts / companion LAN functions; document the inability to access unsupported messages/cellular audio via ordinary third-party iOS APIs. Do not fabricate a network solution.
- **P3 iPhone Bluetooth fallback feasibility:** inspect BlueFerry/BlueZ MAP/PBAP only in an isolated test environment, then explicitly approved device pilot with safe test messages. Evaluate optional HFP calling/audio separately.
- **P4 Calls:** implement a distinct call-state/audio bridge only for a verified path, with incoming/missed/outgoing controls, mic/speaker/mute, teardown and restoration acceptance.
- **P5 Shared Social UI and Identity Center:** integration-owner-owned selector, conversations, contacts, notifications and settings wiring; separate per-user phone links and business scope; regression tests and real desktop geometry/focus checks.

Minimum verification per route: documented supported phone/OS/controller; permission state; connect/disconnect/reconnect; send accepted vs sent vs delivered semantics; duplicate prevention; contact provenance; missed call; call audio routing; battery and background behavior; revocation; identity switch isolation; no unrelated provider regressions. Evidence must distinguish mock/unit tests from live Quickshell/BlueZ/device results. No percent-complete claim without a defined scored test matrix.

## 8 // Alternatives and decision boundaries

- **Bluetooth-first:** rejected as the default; too much hardware/profile coupling and avoidable transport use, especially where Android Wi-Fi already works.
- **iOS-only or Android-only:** rejected as product direction; both device families are first-class, but may have different honest capability sets.
- **Mac as iMessage relay:** not a required dependency; current operator has an iPhone and no Mac. A later user-provided Mac could be a separate opt-in provider without changing the network-first manager.
- **Carrier or VoIP replacement:** out of scope as automatic substitution for personal phone number/cellular call experience. Can be considered as a separately authenticated provider.
- **Full iMessage and FaceTime parity:** not promised; platform constraints and individual device tests govern capabilities.

## 9 // Continuity / permissions / handoff

**DECIDED BY OPERATOR:** network-first per feature; Bluetooth only as optional alternate when no supported route (or explicit approved manual selection); iPhone and Android both supported as product targets; existing Social Hub remains the UI host.

**STILL PROPOSED:** concrete API schema, service/process name, library choice, specific transport priority weights, UI arrangement, implementation staffing, test device matrix, hosted relay decisions and release sequencing.

**NOT AUTHORIZED:** modifying running desktop, pairing devices, installing helpers, editing live QML/service code, moving shared router ownership, merging a PR or production activation. This ADR does not create a live Hospital Room, Assignment, Staff Role or Checkpoint.

**NEXT WORKER:** reacquire current GitHub main HEAD, open PRs, current Social integration ownership and any live Hospital room/assignment before work. Read this ADR, the shared adapter contract, Identity Center plan, Syntagma `AGENTS.md` and the Hospital protocols. Propose a bounded capability contract and experimental verification plan before implementing changes. Preserve separate personal/business phone scopes and all existing Social providers. Report using IMPLEMENTATION / HOW TO USE / VERIFY / WATCH OUT FOR / CHECKLIST / NEXT / DECISIONS.

## 10 // Sources for subsequent feasibility reviews

- KDE Connect desktop repository and documented SMS capabilities: https://github.com/KDE/kdeconnect-kde
- KDE Connect platform feature matrix (iOS missing SMS/notification sync, Android support): https://userbase.kde.org/KDEConnect/en
- Apple MessageUI compose surface: https://developer.apple.com/documentation/messageui/mfmessagecomposeviewcontroller
- Apple CallKit overview: https://developer.apple.com/documentation/callkit
- BlueZ Linux Bluetooth profile stack: https://bluez.github.io/
- Experimental BlueFerry research candidate and observed MAP limitations: https://github.com/erikwb/blueferry and https://github.com/erikwb/blueferry/blob/main/PROTOCOL.md

**Verification statement:** references support *design feasibility research* only. This document is not proof that iPhone/Android phone calls, messages, contacts or Bluetooth fallback already work in Post-Apollo.
