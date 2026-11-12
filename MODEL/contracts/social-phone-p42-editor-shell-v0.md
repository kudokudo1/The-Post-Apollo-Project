# Social PHONE // P42 complete Favorite/Notes editor shell, fail-closed

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Staff role:** external Hospital-compatible PHONE DOC; live Hospital registration unverified  
**Checkpoint:** P41a merged; P41b draft #1944 independently open and in CI; C4b #1785 and issue #1885 unresolved  
**Scope:** isolated additive Social PHONE editor UI + pure JavaScript draft state, tests, workflow, no runtime activation.

## IMPLEMENTATION
To reduce serial micro-patches, P42 builds the **complete in-memory native Favorite/Notes draft editor shell as one UI work package**. It includes two magenta favorite choices, magenta text with orange cursor, a note draft field bounded to 4096 characters, summary of intended changes without showing note contents, red clear-draft and orange cancel, plus a visible SAVE control permanently disabled pending independently verified host and C5 consent.

The draft state is ephemeral: starts fresh for a selected **temporary** BlueFerry row only, discards automatically if the selection or previewEnabled changes, has no persistence methods, does not create a stable contact identity, cannot pull saved notes from an encrypted vault, and never sends notes to iPhone. Its current source is **not mounted into the live P40 `PhoneContactDetail` or `PhonePane`**, so it cannot accidentally turn on note editing without a save host. The default `previewEnabled` is false. The existing public P40 disabled controls, CALL/MESSAGE buttons and security checks remain unchanged.

This delivers the native edit UI source and a discrete testable draft-state implementation in one review package, rather than continuing one status or cryptographic increment per PR. A future approved integration can mount the shell in the actual detail view, map the state into the P41b exact-change commitment, and enable SAVE only when C5 and real host evidence authorize it.

## HOW TO USE
No live operator UI changes. The isolated editor is a **prepared, non-production preview component**. Its SAVE action has no onTriggered, while the real PHONE contact detail remains read-only and disabled. Do not type real private notes into any unsupported preview or infer that data was saved.

## VERIFY
- JavaScript node tests exercise favorite ON/OFF, note replacement/explicit clear, missing/invalid input, selection mixing, discard, privacy-safe statuses and absence of persistence methods.
- Python source tests inspect QML presentation colors, exact safety flags, discard lifecycle and lack of production service calls.
- The dedicated workflow also reruns P40 live locked-detail regressions to ensure no accidental activation. Native Quickshell layout still requires separately authorized Fedora testing; these source tests are not equivalent.

## WATCH OUT FOR
**This is not live Favorites.** C4b #1785 remains in owner work and C3e-AB #1939 reports incomplete real Silverblue rollback. PHONE-specific genuine C5 one-use consent, independently enrolled C3e challenge/replay authority and protected key lifecycle remain missing. The P34/P35 encrypted vault and P41a write lock are existing building blocks but cannot be treated as permission to save. No local-only plaintext shortcut, fake saved flag or reuse of global Favorites++ is introduced.

## CHECKLIST
- [x] Reconfirm scope, active P41b and C4b/C3e owner collisions.
- [x] Build complete native Favorite/Notes draft editor shell with correct color semantics and explicit save denial.
- [x] Build isolated local state transitions, strict bounded draft, discard on context switch.
- [x] Add synthetic QML source and JS behavior tests with dedicated CI.
- [ ] Exact PR-head CI and operator acceptance.
- [ ] Authenticate actual C3e/C4b/Identity and C5 source; production PHONE protected host/key lifecycle.
- [ ] Mount editor in live contact view and wire exact one-use save with revision and saved/readback states.
- [ ] Native Fedora/Quickshell testing after operator approval and final acceptance.

## NEXT
**One integrated feature release** after owners supply actual signed evidence: map selected contact only under approved snapshot, obtain independently verified signed C5 one-action request, bind to P41b change commitment, hold a genuinely verified host-owned lease through P35 commit, return content-free saved/error status plus separately authorized sealed readback, then wire this editor and favorite state into the existing Social menu.

Track owner blocker on issue #1885. Do not open more generic CI-only cryptography PRs without advancing this release path.

## DECISIONS
Additive editor-only source, not a live host, QML activation or change to existing read-only P40 UI. No merge, local machine mutation, production keyring/Secret Service use or external owner modification.
