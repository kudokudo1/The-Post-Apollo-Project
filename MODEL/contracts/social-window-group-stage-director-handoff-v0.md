# Social W // Stage Director grouped-window handoff v0

**STATUS // PROPOSED COMPOSITOR CONTRACT. External activation code merged; CI-only geometry candidate tested; same-frame rendering NOT implemented.**  
**PATIENT //** `kudokudo1/The-Post-Apollo-Project` (Social W UI/lifecycle); implementation dependency `kudokudo1/Post-Apollo-SwayPx` (compositor/Stage Director).  
**ROOM //** Social W unified external-app activation and geometry (chat-compatible; live Hospital Room not verified).  
**ASSIGNMENT //** Preserve a unified Social shell during externally initiated opening and eliminate visible chassis/guest drag and resize separation.  
**PROVENANCE //** Operator screenshot and discussion, 2026-11-07. See Social PR [#1427](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1427).  
**OWNERSHIP //** Social W controls the UI and app-selection lifecycle. SwayPX Stage Director owner must independently accept compositor surgery; its Company M30 and Weather/Chrome work are not transferred.

## Observed implementation and limitations

- `widgets/messanger/MessagingW.qml` holds `sharedPanelX/Y/Width/Height`, normally with the app rail at the left. Its `socialWindow` is a Sway floating toplevel; a separate Vesktop/Chromium toplevel fills the external app slot. Sway `$mod` move/resize is supported on both.
- `widgets/messanger/DiscordGeometry.py` uses direct Sway IPC and an **8 ms configured sampling interval** while the Social menu is open. Its `fast_follow` skips the previous Python → QML → Python loop but still observes one compositor rectangle and commands the other window to follow. Deferred focus and docking safeguards are separate from this sampling.
- Existing safety requires Social's real mapped rectangle before provider placement, skips Vesktop splash geometry, and grants bidirectional geometry only after verified initial docking. A focused app cannot arbitrarily reset the shared size during startup.
- Merged first implementation milestone, PR #1427, adds externally focused **Vesktop main** recognition while the menu is closed and reuses the current Social docking path. It does **not** provide compositor-atomic motion or support automatic external activation of every provider.

## Requested experience, to be verified by the operator

1. Dock-button, native/tray, desktop launcher, and notification activation of a supported app all yield the same visible Social W chassis + selected guest.
2. User dragging **either** chassis or guest sees them move as one assembly, with no visible frame where the rail and guest borders are split apart.
3. User resizing **either** window sees the outer boundaries remain aligned each rendered compositor frame. A guest may take additional frames to redraw its **contents**; that must not move the shared border or shrink Social.
4. Switching internal modes never changes the established outer Social rectangle. Hiding or closing a guest does not destroy the last valid shared position/size.
5. Application splash/unknown windows, identities, logins and unrelated windows are never silently absorbed or granted focus/movement authority.

## Proposed minimum SwayPX compositor seam

**Group identity:** The Social host is uniquely identified through trusted compositor-side surface/client evidence, and the guest is one exact validated mapped main window belonging to an approved application family. App ID/title text alone is insufficient. A pairing is bound to the two live surfaces, their session/generation, current output and a revocable epoch. One active guest at a time.

**Geometry:** Social remains the canonical outer rectangle. The actual guest slot comes from the real Social selector width/inset, not guessed constants on the compositor side. The initial position is **Social-led** until compositor evidence confirms the guest is in its assigned slot.

**Motion:** After the pair is accepted, a move/resize of either member is interpreted as a group operation. The compositor should update the visible geometry of both members **in the same render transaction / scene update**, instead of waiting for `GET_TREE` polling and sending a second Sway move/resize. Explore compositor scene/viewport motion before forcing guest reconfigure on every pointer step. Measure the output; do not claim zero latency from source review alone.

**Input and focus:** Preserve the existing masked rail, Settings++ control surface, guest pointer focus, and deliberate Sway modifier operations. Untrusted popups, dragged surfaces and off-slot content must not escape hit-test or clipping bounds. Fallback to the existing bridge if the group cannot be established safely.

**Teardown/recovery:** Revoke the pair on host/guest unmap, generation/output change, ambiguity or stale role. Never accept splash/hidden scratchpad geometry as a new leader. Restore using the last verified shared Social rectangle, not the app's startup dimensions.

## Required isolated acceptance matrix

| Scenario | Required observation |
|---|---|
| Vesktop notification / tray / native external focus | Social opens, active app selected, no second launch request |
| Cold Vesktop splash → real main window | Splash remains untrusted; main docks to Social before it may lead |
| Mod-move Social, then mod-move Vesktop | Both visible outer edges translate together each frame |
| Mod-resize Social, then mod-resize Vesktop | No separated borders, min-size collapse or stale follower commands |
| Close/reopen; hide to scratchpad; restart Quickshell | Last valid shared geometry survives its permitted lifecycle |
| Switch to Sessions / Telegram / browser | Existing shell size stable; previous guest loses geometry authority |
| Unrelated/spoofed/duplicated app; guest exit; output change | Fail closed, preserve other windows and recoverable Social state |
| Multi-output and different scaling | Correct output/work-area and no stale global coordinates |

Automated verification must include an isolated native SwayPX/Quickshell scene-frame or pixel observation, compositor build, focus/keyboard/masked-input regressions, and rollback proof. Synthetic JSON/QML tests alone are insufficient for the zero-gap claim. Operator-controlled workstation update and live visual acceptance remain separate gates.

## Ownership and next work

1. PR #1427 is merged on Taskbars main as the **external activation** milestone; do not mistake CI success for live acceptance. SwayPX draft PR [#94](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/94) passed CI for a **geometry-only** paired rectangle policy, not for render-frame atomicity.
2. SwayPX Stage Director owner examines the current compositor integration/Company and Weather work, claims or delegates the Social group seam, and chooses a **small CI-only proof** isolated from those active branches.
3. Compare real compositor frame captures during two-way move/resize with existing fast-follow baseline. If same-frame grouping is infeasible under the current SwayPX stage, report that limit instead of lowering the user's requirement silently.
4. Prepare a separate reviewed Stage Director PR and an operator-approved local test only after safety and collision checks.

**ROLLBACK //** Revert merged Social PR #1427 independently if external activation regresses. Any future compositor group must be individually feature-gated and reversible to existing Social fast-follow. No local files, Sway/Quickshell processes or compositor builds were changed by this document.
