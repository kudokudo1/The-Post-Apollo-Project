# Social Phone Bridge // iPhone without a Mac: Linux feasibility and opt-in pilot P2 v0

> **STATUS //** RESEARCH + PROPOSED ACCEPTANCE PLAN; **not** a verified compatible iPhone backend, approved Bluetooth integration, accepted license arrangement, host security decision or production implementation.
>
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`.
>
> **DATE //** 2026-11-02. **BASE //** `main` at `7ac0ceaa257022cbd5a85be166a4ee03513a553f`. PR #1052's exact-head and merged-main Phone Host Intent Boundary CI both completed successfully; the read-only Phone Host Intent Boundary remains **non-authoritative**.
>
> **PROVIDER //** OPEN AI // CHATGPT, external Hospital-compatible browser worker. No live Hospital Room, Staff Role, Assignment, Session or checkpoint verified.
>
> **SCOPE //** This file and MODEL/README.md index only. No `services/phone`, `services/identity`, `services/social`, `widgets/messanger`, Bluetooth, Quickshell, packages, daemon configuration or local files changed.
>
> **INTENT //** Actual iPhone + Linux desktop, no Mac assumed; user wants the existing Social PHONE surface, per-capability network preference and **Bluetooth fallback only when explicitly enabled**. Android and iPhone are separate provider tracks.

## 1 // Mechanism: iOS native API versus Linux Bluetooth accessory

Apple's publicly documented iOS MessageUI `MFMessageComposeViewController` presents a **user-approved compose UI** within an iOS app. It does not grant arbitrary background SMS/iMessage inbox sync, unread-message subscription or a Linux desktop relay. Apple's Contacts framework lets an installed app read **only user-authorized contacts** and supports limited access; it is not an SMS integration mechanism. Apple's CallKit is for integrating an app's own calling service, not by itself an authorization to relay the iPhone's carrier Phone app audio to Linux.

KDE Connect's current iOS capability listing continues to mark **SMS** and **notification sync** as missing and notes iOS background-connection limits. Therefore do not enable `kdeconnect_sms` merely because KDE Connect for iOS pairs over LAN. A custom LAN iOS companion could be evaluated for permissioned app-owned data/contacts, but no verified generic LAN route to the complete personal iMessage/SMS inbox has been identified. In the absence of evidence, its message capability stays **UNSUPPORTED/UNVERIFIED**, not `READY`.

By contrast, Linux Bluetooth **Message Access Profile (MAP)**, **Phone Book Access Profile (PBAP)** and **Apple Notification Center Service (ANCS)** may expose user-approved accessory features without a Mac, depending on actual iPhone firmware, adapter, BlueZ version and pairing. **This is an accessory/protocol path, not an Apple-documented general app API, and requires independent test evidence.** Bluetooth is an alternate route for *only those capabilities* proven unavailable via the preferred network route.

### Sources independently reviewed 2026-11-02

- [Apple: MessageUI](https://developer.apple.com/documentation/messageui) and [SMS compose controller](https://developer.apple.com/documentation/messageui/mfmessagecomposeviewcontroller) (composition, not inbox access).
- [Apple: Contacts permission/limited access](https://developer.apple.com/documentation/contacts/accessing-the-contact-store).
- [Apple: CallKit](https://developer.apple.com/documentation/callkit) (the app's own VoIP calling service).
- [KDE UserBase: KDE Connect iOS feature list](https://userbase.kde.org/KDEConnect/en).
- [BlueFerry main repository](https://github.com/erikwb/blueferry), [architecture](https://github.com/erikwb/blueferry/blob/main/ARCHITECTURE.md), [empirical protocol report](https://github.com/erikwb/blueferry/blob/main/PROTOCOL.md) and [testing isolation rules](https://github.com/erikwb/blueferry/blob/main/TESTING.md). Third-party observations are **claims, not Post-Apollo acceptance**.
- [BlueFerry GPL-2.0-or-later license](https://github.com/erikwb/blueferry/blob/main/LICENSE). No source code or packaged binaries copied into Post-Apollo.

## 2 // Candidate: BlueFerry, **experimental**, independently verified later

BlueFerry's upstream README and protocol report (current on 2026-11-02) say a Linux system with a paired iPhone can use Bluetooth MAP for SMS/RCS/iMessage, PBAP for contacts and optional ANCS for notification metadata. The maintainers report tests principally on an **iPhone 16 Pro Max running iOS 26.5**, with a later **iPhone 17 Pro Max on an iOS 27 beta**. That does **not** establish compatibility with the user's model, OS, Bluetooth controller or BlueZ version.

The upstream uses a **single per-user Bluetooth backend**, with its own session-D-Bus API and optional GTK/Qt/Quickshell clients. Its architecture currently describes `Messages1`, `Presence1`, `Events1` and `CallHistory1` interfaces, a BlueZ/system/OBEX backend, and storage under its own control. The existing Post-Apollo Social integration owner must review a narrow, per-operation adapter; **do not load another Quickshell dock/menu or run both full UIs just because one package ships a Quickshell client.**

Crucial limitations and provenance:

- **Transport ambiguity:** MAP may encode SMS and iMessage alike as `sms-gsm`. Never assert the carrier/app transport or delivery acknowledgement from that field.
- **History:** messages missed while disconnected and complete cloud/iCloud message history are **not guaranteed**; an apparent historical record may reflect only messages captured during an active accessory connection. Do not auto-import backups.
- **Groups:** MAP may not supply a stable native group ID or complete roster. Replying to ambiguous groups is blocked; do not guess recipients or merge conversations only because display names match.
- **Media:** attachments, reactions, typing, FaceTime and full read/delivery receipt semantics are not established by the basic MAP path. Status must be feature-specific.
- **Calling/audio:** BlueFerry currently describes an **optional experimental oFono integration, disabled by default**. Treat call controls and PC mic/speaker as a separately consented HFP/oFono/PipeWire investigation, not as a consequence of SMS pairing.
- **Connection:** a successful BT pairing or presence signal cannot authenticate Post-Apollo human principal, LLC/nonprofit ownership, phone line permissions or phone-content access. Host Gate A from [Identity Center trusted-host integration](./social-phone-identity-host-integration-handoff-p1-v0.md) remains a separate prerequisite.
- **Distribution/licensing:** upstream is GPL-2.0-or-later; legal/technical review is required before copying, linking, vendoring or modifying its code, bundling its backend or redistributing an integration. An independently written adapter that invokes public interfaces still requires an API/version/privacy review.

## 3 // Feasibility matrix, not a promise of support

| Desired feature | Network-first finding | Bluetooth candidate | Evidence needed before UI reports READY |
| --- | --- | --- | --- |
| iPhone SMS/iMessage receiving | No supported generic third-party LAN inbox route established; KDE Connect iOS lists SMS absent | **BlueFerry MAP**, experimental and user-consented | Exact phone+iOS+adapter+BlueZ capability, receive-only synthetic test, identity and line grant |
| iPhone message sending | iOS MessageUI is phone-side compose approval, not an unattended desktop send backend | **BlueFerry MAP PushMessage**, experimental | Separate send grant, confirm recipient/scope, provider-accepted outcome, no ambiguous retry |
| iPhone contacts | Limited permissioned iOS app companion may use Contacts framework; no such Post-Apollo companion is verified | **PBAP** with explicit iPhone permission | Consent, minimal fields, exact device scope, revocation and deletion |
| iPhone notifications | KDE Connect iOS documents notification sync absent | **ANCS** conditional on BLE/controller/BlueZ pairing | Explicit per-app opt-in, iPhone preview settings, no blanket cross-org mirroring |
| iPhone cellular call control | No verified network relay of existing carrier number | **HFP/oFono** research only | Separate call-state evidence, no silent dialing or carrier-number substitution |
| iPhone cellular call audio through PC | CallKit alone does not forward ordinary carrier audio | **HFP audio profile**, not guaranteed by MAP | End-to-end mic, speakers, PipeWire/BlueZ ownership, permissions and rollback |
| FaceTime | No generic native Linux handoff for full client features | None proved by MAP/PBAP/HFP | Remain unsupported unless an independently supported route exists |

Neither network-first preference nor iOS Bluetooth accessory research authorizes automatic fallback; the specific device/operation must be opted in by the operator.

## 4 // Consent-first test sequence (PROPOSED, not authorized to execute)

**Phase 0: read-only nonintrusive planning, no hardware access.** Collect the exact device model/iOS version, distro, Bluetooth controller chipset, BlueZ version and available MAP/PBAP/LE advertising capabilities *after separate permission to inspect the local system*. Identify whether BlueFerry is **installed**, its package/API version and whether its daemon is already active before issuing any D-Bus request. Do not infer installed software from a GitHub repo, or call methods that trigger D-Bus activation. No software installation, pairing or Bluetooth reset.

**Phase 1: operator-specific approval before changing local state.** Decide whether a disposable test account/device is needed. Review BlueFerry release/license, dependencies, package scripts, local persistence, wallet prompts, D-Bus API, Bluetooth/audio service ownership and rollback plan. Obtain explicit separate permission for **each** package installation, BlueZ state change, pairing, starting/restarting a backend or disabling existing Bluetooth services. Never auto-enable on the user's main phone as a side effect of CI.

**Phase 2: Bluetooth accessory pairing only if explicitly approved.** Present visible confirmation on both devices and enable only requested iPhone accessory permissions. Pairing, notification/contacts sync, cloud/cache retention and background service startup are **distinct choices**. Do not request unrelated notifications merely for SMS if the provider can operate safely without them.

**Phase 3: receive-only, disposable content and verified identity.** After Gate A host security acceptance, use an operator-approved test conversation, with no real message content in logs, PRs, screenshots or traces. Verify one inbound event, stable duplicate handling, correct sender/line and explicit denial after grant/session/device unlink. Record only sanitized `capability=messages.receive`, platform/build, transport provenance, error category, timestamp and test correlation ID. If the provider cannot distinguish line/org reliably, **deny cross-context routing**.

**Phase 4: independent permissions.** Test PBAP contacts and ANCS separately, with a privacy boundary and revoke/clear; send, read receipts, groups and call/audio require their own approved milestone. For an unknown send result, do not retry on network/Bluetooth automatically. No FaceTime/full-history promises.

**Phase 5: shared Social handoff.** Only the Social integration owner may wire provider status and scoped content into the existing PHONE area; avoid a second persistent window and do not import BlueFerry's Quickshell UI wholesale. The host must block personal-phone data from an LLC or nonprofit context unless a separately approved explicit grant exists.

### Stop / rollback criteria

Stop on unverified hardware, missing consent, ambiguous paired device or SIM/line, unexpected daemon autostart, external account/cloud requirement not accepted, active Bluetooth profile conflict, stale authorization, unbounded storage, uncertain message recipient, a provider send without independent confirmation, or any private content in logs. Unpairing/clearing history/reverting packages are **local state-changing operations requiring operator approval**, not automatic cleanup.

## 5 // Proposed Post-Apollo implementation seam

**Keep separate platform providers** in the Phone Bridge: KDE Connect Android on verified LAN; optional iPhone Bluetooth MAP/PBAP/ANCS candidate; iOS LAN companion for **only** APIs the phone actually supports. Each backend supplies evidence specific to the selected operation and exact device/line. An experimental third-party service's `connected` state is insufficient for Post-Apollo `CapabilityPolicy.py` `READY`.

If a BlueFerry adapter is later approved:
1. Prefer **a narrow, separately reviewed, no-autostart, read-only D-Bus discovery/status adapter first**, with bounded timeouts and redacted outputs. Do not call message-list, send or pairing methods under the guise of diagnostics.
2. Require trusted user/device/line binding and independently verified permission before obtaining message payloads. BlueFerry's same-user session bus and content store are not a Post-Apollo cross-tenant security boundary.
3. Use a version-gated `serviceId` and unique opaque native conversation/message IDs with explicit provenance. Never infer group identity or iMessage-vs-SMS from transport metadata; do not forge delivery acknowledgements.
4. Define stop/unsubscribe and buffered-content purge on identity switch, revoke, device disconnect or permission loss. Use the accepted cross-process revocation commit barrier, not the synthetic Python `RLock`.
5. Keep license compliance and upstream compatibility review in the owner's acceptance checklist. No source-code reuse in the current P2 feasibility work.

## 6 // HOSPITAL HANDOFF

### IMPLEMENTATION
Research-backed, explicit iPhone/Linux feasibility matrix and consent-first test plan with upstream sources, no code/runtime work. Documents BlueFerry as an **experimental candidate**, not a chosen or proven backend.

### HOW TO USE
Review this decision candidate and propose an owner for optional iPhone Bluetooth pilot. No Post-Apollo menu changes or terminal commands are required. There is nothing to install, pair or activate in this milestone.

### VERIFY
Verify only two documentation files are in the PR; review dated Apple/KDE/BlueFerry sources, upstream license and status. PR grammar CI may verify Markdown conventions, **not** any iPhone capability. Exact user hardware, actual installed daemon and phone permissions remain unverified.

### WATCH OUT FOR
BlueFerry is third-party experimental software, dependent on iOS and BlueZ behavior that may change. Its claims are not official Apple guarantees. Pairing and software installation modify the user's live environment and require separate approval. Same-UID D-Bus and organization isolation still need security-owner acceptance. Do not expose real SMS or contacts in tests or GitHub.

### CHECKLIST
- [x] Verify #1052 merge and exact-head/main CI pass; current main and no competing Phone PR.
- [x] Read Apple, KDE and BlueFerry upstream feature, architecture, protocol, test and license sources.
- [x] Record network-first preference and explicit per-capability Bluetooth opt-in conditions.
- [x] Preserve Android/iPhone backend differences and shared Social/Identity ownership.
- [ ] Operator accepts or revises pilot scope and iPhone fallback candidate.
- [ ] Identity Center/security owner accepts production host Gate A.
- [ ] Separately approved local read-only hardware inventory, then optional controlled pairing/pilot.

### NEXT
Seek operator review of this feasibility plan. After approval, inventory exact iPhone/Linux hardware in **read-only** mode and prepare a license-reviewed, no-autostart provider-status prototype on disposable fixtures before any live phone/pairing or Social UI integration.

### DECISIONS
No final selection or phone feature guarantee is made. Network first, Bluetooth only explicit opt-in alternative per operation, no Mac assumption, single Social PHONE experience, no cross-tenant/LLC/nonprofit leaks. No local machine writes, real phone access, device pairing, PR merge or production activation by this work.
