# 🏥 Company Network M26 // M25 bridge to real Company map controls

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Company Network / Stage Director native MapLibre integration
STAFF ROLE // Nurse 2, operator-delegated external Hospital-compatible continuation
PROVIDER // OPEN AI // CHATGPT
CONNECTION // EXTERNAL, not live Hospital-registered
ASSIGNMENT // Connect installed-only-when-opted-in M25 Qt/QML private vector bridge to M18 rectangles and M15 launch/close actions
BASE // Company main 343160031584e1cda437c5e1d3bf0f0df07b1456
DEPENDENCIES // SwayPX M23 #78, M24 #79, M25 #80 merged; Company M18 #1365 and M19b #1369 merged
PHASE // Isolated GitHub implementation; no local install, no compositor activation

## IMPLEMENTATION

The current Company panel is a single Quickshell `PanelWindow` with a fixed Company layer namespace, a nested `companyFrame` and lazy Coverage Loader. M18's `activeVectorViewportRect` reports exactly the map canvas *inside companyFrame*. The existing M15/M17 attached `CompanyVectorSidecarController` controls a separate native Qt MapLibre window from explicit OFFLINE TEST/ONLINE STREETS buttons.

The SwayPX M25 `PostApollo.CompanyVector 1.0` QML plugin offers `enabled`, `frameRect`, `mapRect`, `wireBound`, `requestLaunch(bool online)`, `close()`, `launchCandidate`, `viewportCandidate` and status. **It is separately packaged, not installed by Company and has no authority to move/clip windows.**

M26 adds:
1. `widgets/CompanyVectorBridgeLink.qml`, a small optional runtime adapter. The file statically imports ONLY `QtQuick`. Its default `bridgeEnabled:false` does not resolve, import, instantiate, connect, or require the M25 plugin. Only an explicit enable transition creates `CompanyVectorBridge` from a dynamic Qt QML string importing `PostApollo.CompanyVector 1.0`. A missing plugin sets `OPTIONAL_BRIDGE_UNAVAILABLE` while preserving the standalone map. Disabling destroys the dynamically created QObject and closes any candidate; no separate Wayland socket, process, app-control or focus changes.
2. `CompanyNetworkW.qml` defines opt-in `vectorBridgeOptIn:false`, kept programmatic until the operator's planned Settings++ / Stage Director activation protocol and compatible Qt ABI are actually installed and approved. The new `activeVectorFrameInHostRect` uses `companyFrame.mapToItem(root,0,0)` and bounds it against the live **PanelWindow**, never guessed absolute screen coordinates. The old `activeVectorViewportRect` remains the M18 **frame-local** map rectangle. The optional link receives both via reactive bindings and goes to zero when Company closes or Coverage is hidden.
3. Coverage emits `nativeVectorLaunchRequested(bool online)` **only when the existing attached Quickshell native launch returns true**, and `nativeVectorClosed()` on process exit/stop. The Company Loader forwards those to the bridge's `requestLaunch` and `close` methods only when an actual M23 native Company private wire is bound. Intent report failure never blocks the existing launcher. The preview's explicit online network consent remains exactly unchanged.
4. Node tests, M18+M19b+M13 regression checks, CI and this handoff. No new run-time module installation, local file edit, production compositor activation, new keybinding or window embedding.

## HOW TO USE

There is no new user-facing button or manual terminal action in M26. On any normal Post-Apollo desktop the property `vectorBridgeOptIn` defaults false, therefore the existing Company → Coverage → VECTOR VIEW → OFFLINE TEST or separately approved ONLINE STREETS works as before.

A later, separately authorized controlled installation must provide the ABI-compatible M25 plugin and native SwayPX M24 physical Company pairing, then explicitly opt in to the bridge, confirm `vectorBridgeWireBound`, and only afterward treat `vectorBridgeStatus` or `viewportCandidate` as **candidate receipt diagnostics**. These are not pixel/input authority.

No local SwayPX/Quickshell restart or installation under this milestone.

## VERIFY

- Syntagma AGENTS, Hospital Agent and Authority inspected; no live Hospital registration assumed.
- Company main 3431600... and SwayPX master 6be2151... rechecked. No colliding open Company PRs as branch was created.
- M25 QML C++ API checked against exact bridge properties/methods. Existing Company M18 coordinate frames and M15 attached child process behavior inspected.
- Dedicated M26 source tests assert disabled optional QML import, nested frame/map geometry under compact/standard/fullscreen, explicit offline/online consent signals, process close, no process override, no Weather WATCH actor authority.
- CI re-runs the M18 map geometry tests, M19b layer namespace contract and M13 fixed-path native launcher tests. GitHub CI result must be separately checked against exact PR head.
- A source-level test does not establish that M25's QPA module has been installed or that QML dynamic import works on the operator's Fedora Qt version. An isolated QML engine test with M25 installed and a live selected native Company client remains pending.

## WATCH OUT FOR

- M26 is **transport wiring, not native window embedding**. M23/M24 geometry receipts are candidate-only. No M21 session has been bound to an actor actually proven to originate from this explicit Company launch. Do not grant scene, clipping, focus, keyboard or popup privileges.
- `vectorBridgeOptIn:false` must remain the default until SwayPX startup/Qt ABI/install and rollback are verified. Do not silently auto-enable on the user's live machine or make the Company PanelWindow fail if plugin is absent.
- One Quickshell Wayland connection is required. The M25 bridge borrows QPA's display; creating another display or dispatching other clients' events is prohibited.
- `frameRect` is **host-local**, whereas `mapRect` is **companyFrame-local**. Both may become zero on hidden/closed/invalid state. Do not report unverified desktop-global coordinates to the private wire.
- The original attached Qt child process remains owned by `CompanyVectorSidecarController`, not the new bridge.
- The user retains final visual acceptance and local installation/activation authority.

## CHECKLIST

- [x] Reconstruct Company M18, M19b and SwayPX M23–M25 source and protocol
- [x] Preserve the real native attached M15/M17 launcher and explicit online consent
- [x] Implement optional zero-dependency dynamic M25 QML adapter
- [x] Report PanelWindow frame and frame-local map rectangles separately
- [x] Forward explicit launcher accepted intent and native close, not speculative startup
- [x] Add M26 Node/static and M13/M18/M19b regression CI
- [ ] Exact-head M26 GitHub CI passes
- [ ] Review/merge under operator's delegated GitHub implementation authority
- [ ] Install M25 plugin on isolated matching-Qt host and run actual QML engine import test
- [ ] Verify SwayPX M24 physical Company selection plus report ACK
- [ ] Authenticate M15 map XDG process birth and M21 candidate custody
- [ ] Native scene/window resize/clip/seat/popup tests with rollback
- [ ] Operator final visual acceptance

## NEXT

Verify M26 PR CI. Do not turn on `vectorBridgeOptIn` in production. Continue the separate native M27 actor-origin/custody milestone in SwayPX and an isolated M25 client+M24 server integration test. Only after those pass should a later milestone offer an explicit UI control to safely enable the bridge on the live desktop.

## DECISIONS

Operator authorized Company integration GitHub implementation/ownership, but local desktop mutation was not performed. Preserve other Stage Director/Weather/Chrome rooms and their independent tests. M26 is scoped to CompanyNetworkW, CompanyCoveragePane, optional link, tests and documentation; no broader Company identity or Hub data changes.
