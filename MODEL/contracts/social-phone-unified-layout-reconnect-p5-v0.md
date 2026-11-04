# Social PHONE P5 // Same-world conversation layout and iPhone setup fallback

> **STATE //** Review candidate, not live Fedora verification or phone-content grant.
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`
> **ROOM //** Social Phone Bridge continuation. **STAFF ROLE //** DOC, external Hospital-compatible, unregistered.
> **OPERATOR FEEDBACK //** 2026-11-04: SET UP IPHONE reports native setup client missing despite earlier iPhone/Fedora Bluetooth audio; Bluetooth settings staying open does not solve it; PHONE's left vertical button rail lacks the familiar Social contact list + chat feed.

## IMPLEMENTATION

1. **Correct the missing-client assumption.** `PhoneNativeSetupLaunch.py` previously looked only for `blueferry-gtk` and `blueferry-qt`. This is insufficient when `blueferry-backend` is installed without those optional GUIs. It now tries the official `blueferry-quickshell` GUI as well; if there is no GUI, it may launch the installed `blueferry pair-setup` interactive wizard inside an available, allowlisted terminal (`foot`, `kitty`, `alacritty`, `konsole`). Fixed argv only, no shell and no arbitrary provider metadata. **Only a user click on SET UP IPHONE permits that launch.** If neither a supported native client nor terminal/wizard is installed, say so without implying the phone or Bluetooth bridge is unpaired. Never install packages, run service controls, or forget/re-pair devices automatically.
2. **Match Social's native layout.** `PhonePane.qml` now uses existing `ContactList` (left) and `ChatFeed` (right) components, identical family to Sessions/Telegram. Device, Calls, Messages and Contacts are horizontal `ActionButton` tabs across the top. An always-visible CONNECT PHONE button in the shared PHONE header runs only the existing read-only provider check and brings up an inline DEVICE setup view over the chat column. On opening PHONE, MESSAGES is selected so the normal two-column structure is immediately visible.
3. **Honest empty state.** The contact list is an actual `ContactList` bound to `conversations: []`; `ChatFeed` has `conversation: null`, `messages: []`, and `sendEnabled: false`. No fake contacts, private-message reading, send button, call controls, copied session tokens or local Social identity grants. The device setup is kept in a scrollable subview in the feed column, diagnostics behind DETAILS, no separate security panel and no replacement of shared Social router/QML.
4. **Clarify Bluetooth.** Initial BlueFerry pairing may need an unlocked iPhone and Bluetooth settings open for phone-side approval. Once configured, BlueFerry documents automatic background reconnection after interruptions. The app must not demand that Settings stay open just to maintain an existing bond. A prior Bluetooth audio observation does not certify that MAP/PBAP permissions or a Social content grant exist.

## HOW TO USE

**Once reviewed/merged/deployed:** Social → PHONE opens the familiar conversation list and feed. Choose CONNECT PHONE (top-right) to check local bridge state and see the DEVICE setup panel. If first-time BlueFerry setup really is needed, choose SET UP IPHONE. On installations with no GTK/Qt GUI but a BlueFerry backend CLI and a terminal, this offers the upstream interactive pairing wizard. If the phone is already paired, do not automatically reset it. Approve any actual first-time pairing on the phone; return to Social and recheck.

The visible CALLS, MESSAGES and CONTACTS tabs have distinct honest non-connected content. They are not functional sync until the separately scoped trusted host exists. The network bridge status refers to KDE Connect/Android and does not determine iPhone Bluetooth pairing.

## VERIFY

CI uses `.github/workflows/social-phone-one-action-setup.yml`, including:
- `tests/phone/test_phone_native_setup_launch.py`: GUI precedence, Quickshell recognition, installed backend with CLI wizard/terminal fallback, unsupported target and no auto-pair.
- `tests/messaging/test_social_phone_unified_layout.py`: ContactList/ChatFeed reuse, top rail, empty model, disabled send, explicit navigation, no auto launch.
- Existing native setup, read-only MENU and provider diagnostics regressions.

**No current phone, Sway/Quickshell geometry, Bluetooth pairing, installed binary inventory or live Fedora runtime was inspected or modified.** CI can check Python and QML source contracts but does not visually certify the desktop or guarantee available terminal binaries.

## WATCH OUT FOR

- The user reports actual runtime failure: two optional graphical BlueFerry launchers were not found. The backend may still be present, but its installed CLI/GUI inventory and compatibility have not been verified on the user's machine. Do not claim the new fallback will definitely launch until actual test.
- `blueferry pair-setup` may initiate pairing flows. It is restricted to the separate deliberate SET UP IPHONE click; paired devices should not be forgotten or forcibly re-paired. Native confirmation remains in provider/phone control.
- Even after successful pairing, existing `BlueFerryReadiness.py` projects only MAP/PBAP *self-reports*. It does not authenticate a person, device line, organization or phone content delivery. The new visual ContactList/ChatFeed is empty on purpose.
- iPhone Bluetooth audio and BlueFerry messaging are independent profiles; the reported `network bridge service not running` refers to KDE Connect and is not evidence that iPhone Bluetooth must remain discoverable.
- Shared Social/Identity Center/Account Broker files are untouched. Gate A production content grant and verified line/session bridge remain assigned to their owning teams.
- ContactList and ChatFeed now instantiate inside PHONE; after approval/deployment verify true width/height, focus and scroll behavior at actual resized Social window geometries before accepting.
- No local machine package install, Bluetooth restart, Quickshell reload, file edits, automatic merge, or real phone test was performed.

## CHECKLIST

- [x] Reacquire current `main`, Syntagma Hospital rules and open PHONE/Social PR ownership.
- [x] Diagnose two-GUI-only launcher assumption against upstream BlueFerry supported clients.
- [x] Extend native, explicit handoff to Quickshell and backend terminal wizard fallback.
- [x] Reuse Social's real ContactList and ChatFeed with top tabs and zero unverified content.
- [x] Preserve one primary CONNECT PHONE, details collapsed, no automatic pairing.
- [x] Extend synthetic and source-level tests + CI workflow.
- [ ] Verify exact-head CI, inspect conflicts/changes.
- [ ] Obtain Social integration owner/operator review and merger authorization.
- [ ] Test on the user's Fedora desktop with real installed BlueFerry programs and phone (separately authorized).
- [ ] Complete Identity Center, Account Broker and Phone Bridge trusted message/contact integration.
- [ ] Final operator visual and functional acceptance.

## NEXT

Review the draft PR's code and CI. After authorized desktop deployment, inspect BlueFerry's installed clients and backend status, confirm that paired iPhone audio remains untouched, check the pairing/permissions only if needed, then visually test PHONE's shared two-column geometry. The future true Social message/contacts bridge remains a separate cross-owner job requiring Gate A security/identity ownership and actual phone authorization.

## DECISIONS

Operator requires PHONE to look and behave like the rest of Social, with contacts and chat feed and horizontal tabs. Setup must work without forcing the iPhone Bluetooth settings to remain open after pairing. This branch is bounded to PhonePane, native setup launcher, tests, workflow and contract index. No content transport, fake data, security dashboard, merge or local activation. Final DONE belongs to the operator.
