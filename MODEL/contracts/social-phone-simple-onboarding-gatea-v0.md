# Social PHONE // One-step connection UX and behind-the-scenes Gate A

> **DECISION //** Operator-directed connection UX, 2026-11-04. Personal phone setup should be straightforward and should not demand a vault-like sequence of Post-Apollo approvals.
>
> **PATIENT //** kudokudo1/The-Post-Apollo-Project
>
> **STATUS //** Selected USER EXPERIENCE, IMPLEMENTATION PENDING. Does not approve a production grant host, phone-content access, identity service, live pairing, UI activation, merge or local machine change.
>
> **RELATES TO //** [Network-first Phone ADR](./social-phone-bridge-network-first-adr-v0.md), [Identity trusted-host Gate A](./social-phone-identity-host-integration-handoff-p1-v0.md), [read-only provider observation](./social-phone-provider-observation-p2-v0.md).

## 1 // Product contract: one phone, one obvious connection action

The existing Social -> PHONE workspace is the ONLY primary surface. Do not build a separate security product or phone-control window.

**Disconnected state:**
- One prominent **CONNECT PHONE** action.
- Automatically find usable network-first providers and already-paired phones when a future approved backend can verify them. Offer a device picker only if more than one relevant device is found. Never present an arbitrary selection of transport protocols to a typical user.
- Use the existing OS-native pairing/consent process. A phone-side Bluetooth code confirmation or platform-required notification/contact/SMS permission cannot be bypassed. Reuse existing pairing where verifiably valid instead of forcing a new pairing wizard.
- The user chooses PERSONAL by default. For a separately owned organizational phone or line, show one understandable optional **Use for** ownership choice; do not make the user step through every portfolio, branch, role and device grant. Any organization option must be backed by authenticated membership, not a manually typed display name.

**Connected state (only after actual verification):**
- Clearly show the connected device, ordinary connection status, and available Messages, Calls, Contacts capabilities. Unsupported functions remain unavailable without misleading success claims.
- Messages send through the ordinary composer and calls through ordinary call controls. Do not repeat authorization prompts per message or per call.
- Show **MANAGE** as a secondary entry for reconnection, permission status, troubleshooting and **DISCONNECT**. Keep low-level MAP/PBAP, D-Bus and Bluetooth diagnostic detail collapsible behind a details/developer view. Avoid a permanent PERMISSIONS tab full of default toggles.
- After previously consented setup, reconnect in the normal allowed way. If the OS revokes a permission or the device link is lost, show a concise repair action, not a whole new registration process.
- Never label a BlueFerry MAP/PBAP daemon report or a KDE loaded plugin as verified account access.

## 2 // What the user MUST NOT need

No mandatory additional Post-Apollo password, PIN, security questions, organization login ceremony, multi-stage approval dashboard, or manual series of per-operation grant buttons just to connect their own phone.

The visible connect action authorizes **one guided setup**, not an unrestricted blanket grant. The OS/platform may still require distinct iOS message-notification/contacts controls or Android app permission prompts. Only ask for a permission when it is relevant and actually needed; explain what function needs it. A denied contact permission should not disable a separately working call or message route.

Avoid putting nine capability checkboxes, transport override selectors, audit logs, nonce copies, or separate security status buttons into the primary Social PHONE UI. Let the product do backend bookkeeping.

## 3 // Keep actual trust checks invisible, not absent

Implement behind the UI, under a verified owner:
- Bind the authenticated desktop user to a particular device and, where relevant, phone line. Do not interpret a local Social identity label as proof of ownership.
- Record consent and the actual OS/provider permissions for supported operations. A single guided setup may collect the necessary **distinct** approvals, without manufacturing repeated Post-Apollo approvals.
- Personal is the safe default and never silently exports personal phone messages/contacts into LLC/nonprofit contexts. Organizational association requires intentional selection and independently verified authority. A company switch cannot inherit personal-phone permission.
- Enforce grant expiry/revocation, safe content release and display clearing on sign-out, unlink, permission loss or organization switch without making users manually perform those checks.
- Prefer verified network transport. If an iPhone capability actually requires Bluetooth and has no supported network route, clearly obtain user consent for its use during setup. Do not silently enable Bluetooth or switch transports later. Scope fallback to the approved device and required capabilities internally.
- Do not auto-retry sends when a provider may already have accepted the message. Do not replace the phone's carrier line with an unrelated VoIP identity.
- **DISCONNECT** revokes future access promptly. A separate destructive **FORGET PHONE / DELETE LOCAL COPY** operation may require a clear final confirmation, but normal disconnect should not trap the user in an approval loop.
- Do not claim native FaceTime functionality unless a real supported route has been independently verified.

These are ordinary backend safety rules, NOT reasons to add extra account screens. Reuse OS session security and existing Identity Center mechanisms where actually verified; do not invent a second login system.

## 4 // Integration contract and ownership

**Social integration owner:** fit CONNECT PHONE, device status and MANAGE into existing PHONE pane, preserve existing Social selection/focus behavior. This document is not permission for a different worker to edit shared QML.

**Phone Bridge owner:** implement an actual device-discovery, pairing/connection and per-capability provider bridge behind the simple setup, reusing approved KDE Connect/BlueFerry observations but never treating observations as authorizations.

**Identity Center / security owner:** accept or revise the minimum trusted host model for session/device/line binding, personal/org separation and revocation. The same-UID D-Bus and cross-process release problem still needs a concrete architecture. It is not a justification for additional user-visible screens.

**Operator:** final approval of real host/pairing changes, the UX, and any merge or activation. Existing iPhone Bluetooth pairing and call audio are evidence, not proof of verified messages.

## 5 // Concrete acceptance checks

- One obvious desktop CONNECT PHONE action; show device selection only for genuine ambiguity.
- A phone already paired by the OS can skip re-pairing if exact authorization and capability checks succeed.
- Only native OS/provider prompts that are genuinely required; no repeated Post-Apollo authorizations for normal use.
- Screen reports per-feature availability honestly when messages, FaceTime, audio or contacts are unsupported.
- Reconnect after restart without a new approval ceremony while existing consent remains valid.
- A simple MANAGE -> DISCONNECT path works and stops future content delivery.
- Personal/LLC/nonprofit separation holds under connection, organization change, sign-out and revocation; tests exercise wrong-device/wrong-line/cross-org denial silently.
- Bluetooth is never automatically enabled/restarted or newly paired without operator action; no automatic duplicate send.
- Test on a real, authorized phone and Fedora/Quickshell runtime before claiming deployed/ready.
- Do not replace these user-centered acceptance tests with a large list of security UI controls.

## 6 // Immediate work boundary / recovery

Current PhonePane is a **read-only readiness** view. PR #1216 and #1225 added the Phone menu and BlueFerry reporting; PR #1236 introduced a non-authorizing two-provider observation projection and is already merged as of this decision. None is a live phone-content connection or trusted host.

This document records the operator's anti-friction direction for the Gate A coordination and later Social wiring. Gate A's host/security owner assignment remains unresolved. Before writing the production host or shared QML, reacquire current main, conflicting PRs, Room assignment and actual permission scope; get owner/operator approval for any host actuation.

**Recovery:** this proposal is documentation only. A draft PR can be closed without affecting Fedora, Bluetooth, paired devices or users. Preserve both the easy connection flow and the essential behind-the-scenes isolation. Final DONE belongs to the operator.
