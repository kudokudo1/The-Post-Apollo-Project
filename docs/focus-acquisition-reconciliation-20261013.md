# Syntagma // focus-acquisition reconciliation

**Evidence kind:** read-only source audit + operator runtime observations.
**Date:** October 13, 2026.
**Scope:** first step AFTER the settled window-mapping lifecycle.
**Decision state:** investigative; **no keyboard-focus implementation changes authorized or implied by this report**.
**Baseline:** `main` snapshot at `6c6007ab07f6ffe3e999f92151ba54c9862c87d2`.

## What we know

The opening presentation policy is separate from how the window receives
keyboard focus. Git, Hospital and Notifications use persistent mapped
`PanelWindow` surfaces with a click-through closed mask. Git/Hospital's
October 13 opt-in *unmap/remap* experiment crashed on repeated reopen;
do not revive that experiment when investigating keyboard focus.

A single logical **keyboard acquisition** may currently be issued by
multiple QML call sites. Those call sites are not automatically safe to
remove: pre-open and post-open events may fall on different compositor
lifecycle boundaries. Conversely, two calls that restart a shared timer
do not establish that two acquisitions were needed.

### Shared-owner focus requests // current source

| Window | First opening request | Second opening request | Additional request | Runtime necessity |
| --- | --- | --- | --- | --- |
| Git | `GitW.open()` calls `keyboardOwnershipRequested()` **before** `menuOpen = true` | `shell.qml` `onMenuOpenChanged` calls `requestControlKeyboard("git", "open")` after opening | Pointer entry / Koinoikos / cross-widget actions independently claim focus | Neither opening request has been separately proven removable |
| Hospital | `HospitalW.open()` calls `keyboardOwnershipRequested()` **before** changing mode/opening | `shell.qml` `onMenuOpenChanged` claims Hospital after opening | Pointer entry / Koinoikos / cross-widget actions | Neither opening request has been separately proven removable |
| Notifications Hub | `menuOpen = true` triggers `shell.qml` `onMenuOpenChanged` ownership claim | `NotificationsHubW.open()` or `toggle()` then emits `keyboardOwnershipRequested()` | A single 48 ms fallback tries again if its Qt window is not active; pointer entry/Koinoikos also claim | Runtime history includes Tab going to the window *behind* Notifications; do not erase a potential recovery path without a focused test |

**Important:** in `shell.qml`, each `onKeyboardOwnershipRequested`
signal is presently forwarded with reason `"pointer"`, including signals
from explicit `open()` functions and Notifications' retry. That label
does not currently affect behavior: `KeyboardOwnershipCoordinator.claim(id,
reason)` accepts `reason` but **does not inspect or record it**. Treat it
as an inaccurate label, not proof that a pointer event occurred.

### Shared coordinator's actual behavior

`claim(id, reason)` accepts only `git`, `hospital`, and `notifications`.
It writes `owner = id` and `boostOwner = id`, then
`releaseBoost.restart()`. After **120 ms**, the timer clears
`boostOwner`; the selected open menu drops from its brief
`WlrKeyboardFocus.Exclusive` acquisition to `OnDemand`.
An additional same-owner claim restarts the **release timer**; this is
not a pre-opening wait and cannot alone explain visual rendering lag.

`owner` is **intent**, not the real SwayFX keyboard seat owner.
`forceActiveFocus()` affects Qt's item focus **inside a window**,
not whether that window has compositor keyboard focus.

### Other window families (no shared-coordinator claims)

| Widget | Mechanism | Why it differs / boundary |
| --- | --- | --- |
| AppControl | Independently managed `OnDemand` in normal operation, `Exclusive` when Koinoikos selects it, and an internal search input receives Qt focus | Search-first interaction; does not call the three-member shared coordinator |
| CPU++ | Own `focusable` policy tied to Koinoikos; its mode keys use window shortcuts | Independent root focus behavior, not shared coordinator |
| Weather | `Exclusive` while open outside Koinoikos; during Koinoikos only selected Weather holds it | Legacy whole-menu capture, with risk of keyboard lockout when another native app is clicked |
| Power | `Exclusive` while its menu or confirmation is open | Dedicated confirmation controls; still not a demonstrated requirement for indefinite Exclusive |
| Social | Ordinary Sway `FloatingWindow` with separate native Discord/Vesktop focus handoff | Not a layer-shell focus-policy equivalent; requires an adapter |
| Media Deck / passive toasts / dock buttons | No generic menu-keyboard ownership | Do not force acquisition without an interactive keyboard requirement |

## Standardization hypothesis, NOT the new default yet

**One logical request per actual acquisition event**, using a common
entry point, is a good target. Acquisition events include: **open**,
**real panel pointer entry**, **Koinoikos selection**, and **explicit return**.
A fallback retry is an *exception* with an observable missing-focus predicate,
not a universal timer.

Avoid confusing these distinct jobs:
1. **Present** the native window using its already established safe lifecycle.
2. **Claim** logical ownership exactly when intended.
3. **Acquire** compositor keyboard focus, with bounded mechanism if needed.
4. **Set** Qt focus to the appropriate navigation input/anchor or editor.
5. **Validate** that keyboard events reached the expected window/item.
6. **Refresh** expensive data independently of focus readiness.

## Safe decision gates

1. First measure/log the ordered acquisition events with reason,
   `menuOpen`, coordinator `owner/boostOwner`, Qt window active state,
   Qt item `activeFocus`, and an actual harmless key received.
2. Choose **one** of the overlapping opening call sites in one widget
   to disable **only in a reversible, explicitly tested experiment**;
   do not change the 120 ms pulse, window mapping, or unrelated widgets
   in the same comparison.
3. Verify first open, rapid repeat, pointer re-entry, multi-widget transfer,
   Koinoikos and native Kitty/Discord recovery. Retain both calls if removing
   one breaks actual key acquisition.
4. Keep Notifications' conditional recovery path intact until its real
   compositor-focus failure is understood.
5. Once one minimal path is accepted on device, promote the proven behavior
   to the composite opening protocol. No universal default from CI alone.

**No live key-delivery, latency, Qt or compositor measurement was made
for this source report.** The October 13 Git/Hospital unmap crashes are a
separate, already-observed lifecycle failure, not evidence that the
focus-acquisition calls themselves are faulty.
