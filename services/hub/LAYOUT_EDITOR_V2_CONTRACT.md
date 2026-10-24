# 🏥💜 ApolloHubW // P1 Layout Editor 2.0

**Status:** Stages 1–3, 5 MOVE, and Stage 6 grid packing have operator desktop acceptance (Stage 6 visual arrangement shown in screenshot); Stage 4 SWAP dropdown is in use. Stage 7A spatial keyboard navigation passes CI but still needs keyboard desktop acceptance. Stage 7B has begun with height-aware TIME presentation on GitHub `main`, with Hub source/validation CI green and desktop acceptance pending. Other mini-widgets, persistent undo, drag-and-drop and presets remain later scope.

## IMPLEMENTATION

`services/hub/ApolloHubLayout.js` now returns a version-2 layout document:

```json
{
  "version": 2,
  "nextTileId": 2,
  "modes": [
    {
      "id": "dashboard",
      "name": "Dashboard",
      "icon": "✦",
      "subModes": [
        {
          "id": "overview",
          "name": "Overview",
          "tiles": [
            {"id": "tile-1", "module": "time", "size": "half", "rowSpan": 1}
          ]
        }
      ]
    }
  ]
}
```

This is a schema illustration, not replacement user data. Existing version-1 `{module,size}` tile entries are migrated **in memory** through `Layout.parse()`/`Layout.normalize()`. Migration preserves mode/submode names, order, icons, chosen module IDs, half/wide tile widths, and number of tiles. Every tile receives a persistent unique `tile-N` ID. `nextTileId` advances monotonically, so deleting a tile does not reuse its identity. The v2 `rowSpan` allows values 1–3 for taller cards; `rowSpan:1` preserves the existing 140px appearance.

The live `widgets/ApolloHubW.qml` consumes `rowSpan` for height, but **no new resize buttons are exposed in stage 1**. `Layout.resizeTile()` is the tested backend foundation for a future deliberate sizing control. Two-column half/wide behavior, existing 6/6/8 capacity limits, and current Flow arrangement remain unchanged.

**Storage:** The existing `ApolloHubStore.layoutJson` (same `Quickshell.dataDir/apollo-hub-layout.json` path) persists layouts on explicit Hub edits. No layout reset, new local file, or write to To-do/Notes stores is requested by migration alone. An unsupported saved version or invalid JSON sets an explicit `LAYOUT READ ONLY` warning; editor saves are refused rather than silently overwriting the unrecognized file with defaults. Recovery/migration for corrupt files requires separately authorized action.

## HOW TO USE

1. Sync GitHub `main` and restart Quickshell by the operator's normal method.
2. Open **Apollo Hub → EDIT**.
3. Each tile's top-right actions now read **← → SWAP ×**. The red `×` is immediately to the right of `SWAP` and removes **only that tile placement** from the current submode. The tile's original module/service, downloaded media, saved notes, and To-do records remain untouched.
4. The EDIT toolbar now has **UNDO**. It restores the previous layout action, including an accidentally removed tile. Undo history contains up to 10 layout edits during the current running Hub session; it is not a persistent history.
5. **+ TILE** can add a tile again, which receives a new ID. Its underlying module data is shared and not duplicated.

The `×` is an **explicit one-click edit action**, not a destructive record deletion. It only appears when EDIT is enabled. **Do not treat it as a way to delete saved To-do items or Notes.** This stage does not yet add removal controls for entire main modes/submodes; those remain planned for the next editor increment.

## VERIFY

- `tests/hub/test_apollo_hub_layout_v2.cjs`: exercises actual v1→v2 conversion, stable IDs, round trips, empty submodes, position-only deletion, undo via saved layout snapshot, add-after-delete, invalid indices, row spans, and rejection of unsupported versions.
- `tests/hub/test_apollo_hub_foundation.py`: verifies UI source wiring, existing module contracts, the exact red `×` after `SWAP`, the undo hook and storage guard.
- `.github/workflows/apollo-hub-foundation.yml`: runs both tests when layout/UI changes.

**Live acceptance still needed:** The operator should verify an already customized v1 layout survives the new code, click `×` on a disposable tile, use UNDO, then reopen the Hub to verify persisted placement. Do not delete a personal note, task, or other stored data for this test. UI test outcomes are not established solely by CI.

## WATCH OUT FOR

- Stage 1 intentionally does not expose resize controls. Taller layouts are represented but only appear if a valid v2 rowSpan is present.
- UNDO is in-memory only; restart clears the undo stack. This is separate from on-disk layout persistence.
- The existing Hub limits (6 main modes, 6 groups/mode, 8 tiles/group) remain. Capacity and flexible grid design are not expanded by the schema update.
- Old `apollo_hub_click_preview.qml` does not attach the live bridge. Use the real Hub for checking service-backed tiles.
- Concurrent UI workers should inspect latest `main` before editing `ApolloHubW.qml` and `ApolloHubTile.qml`, and not silently replace the editor's new `removeTile` signal.

## CHECKLIST

- [x] P1 versioned layout schema and v1 migration
- [x] Stable tile IDs and row-span data field
- [x] X tile removal after SWAP
- [x] In-session Undo for layout edits
- [x] Guard against overwriting unsupported saved layout
- [x] Add source-level behavior and UI wiring tests
- [x] Operator runtime acceptance for Stage 1
- [x] Stage 2 edit controls for one/two-column width and one/two/three-row chassis heights
- [x] Stage 2 operator runtime acceptance
- [x] Gap-filling grid packing (Stage 6)
- [x] Stage 7B TIME mini H:1/H:2/H:3 presentation foundation
- [ ] Stage 7B TIME mini desktop acceptance
- [ ] Stage 7B content-density variants for other mini-widgets
- [x] Stage 3 mode/group removal with named confirmation and Undo
- [x] Stage 3 operator desktop acceptance
- [x] Stage 4 module picker: search, count, occupied-state hints, explicit selection
- [ ] Stage 4 operator desktop acceptance
- [x] Stage 5 cross-mode/cross-group MOVE dropdown and ID-safe backend
- [x] Stage 5 operator desktop acceptance
- [x] Stage 6 packed two-column tile geometry with no saved-layout migration
- [x] Stage 6 visual desktop acceptance
- [x] Stage 7A source-level spatial keyboard navigation
- [ ] Stage 7A desktop keyboard acceptance
- [ ] Durable undo/presets and full grid-packing polish

## P1 Stage 2 // Explicit width and height controls

The tile EDIT toolbar now reads **← → SWAP W:1/W:2 H:1/H:2/H:3 ×**, preserving the red destructive `×` after the sizing controls. The `W` and `H` buttons use existing shared `ActionButton` geometry and hover/selection states. This adds no new resize gesture, timer, service, or polling source.

- **W:1** = one column (half of the available Flow width). Click to switch to **W:2** = two columns (full width). Clicking W:2 returns to W:1.
- **H:1** = existing 140px card, **H:2** = 288px, **H:3** = 436px, based on the observed original 140px height and existing 8px tile-flow spacing. Clicking H:3 returns to H:1.
- Both buttons operate only in EDIT mode, refuse writes when layout storage reports corruption or an unsupported version, use `Layout.resizeTile`, and persist only metadata for the selected tile.
- The existing **UNDO** button restores earlier widths/heights, and the default layout retains the same visual sizes and order.
- Height is *tile chassis size*, not a promise that every mini-widget uses all additional space internally. Vertical content expansion and grid-packing polish are separate design work.

**Stage 2 validation:** `tests/hub/test_apollo_hub_foundation.py` checks labels, placement, visibility, signals, storage guard and Undo connection. `tests/hub/test_apollo_hub_layout_v2.cjs` tests dimension cycles, stable identities, adjacent-tile isolation, no-op invalid inputs, swap preservation, and serialization across restarts. Both run under `.github/workflows/apollo-hub-foundation.yml`.

**Desktop acceptance:** after operator pulls latest `main` and restarts Quickshell, enter EDIT, choose a disposable tile, cycle W and H independently, UNDO both, close/reopen the Hub and restart (when convenient) to confirm dimensions persist. Check that a half-width tall tile may leave a blank area beside it under the existing `Flow` layout; this is not a data-loss bug. A future true grid editor will address packing.

## P1 Stage 3 // Remove main modes and submodes safely

The EDIT toolbar provides **− MODE** and **− GROUP** in addition to the prior + MODE, + GROUP, + TILE, and UNDO. Both removal buttons use the canonical red destructive-action treatment.

**Two-click confirmation:**
1. Select the mode or group to remove and open EDIT.
2. Click **− MODE** or **− GROUP**. The toolbar temporarily displays the selected name, the count of groups/tiles under it, and distinct **CONFIRM** and **CANCEL** buttons. The change is not saved yet.
3. **CONFIRM** rechecks the current selected stable IDs, count limits, editing state, and layout-storage validity before removing the layout branch. **CANCEL** performs no write. Closing the Hub, leaving EDIT, or switching mode/group automatically cancels pending confirmation.
4. The existing UNDO button restores the prior hierarchy, including group names, tile order, unique tile IDs and W/H sizes, within the same session.

**Safety rules:**
- At least one main mode must remain; every surviving mode must retain at least one submode. A disabled removal button makes that invariant visible, and the pure policy independently rejects invalid calls.
- Removal changes only the `ApolloHubStore.layoutJson` arrangement. **It does not delete To-do records, Notes, media, application installations, shared services, or widget-local settings.**
- `Layout.removeMode(layout, modeIndex, expectedModeId, true)` and `Layout.removeSubMode(layout, modeIndex, subIndex, expectedGroupId, true)` refuse to mutate without explicit boolean confirmation and matching stable IDs.
- The same single-writer layout store, version-2 schema, unsupported-schema write lock, and ten-entry in-session UNDO history remain unchanged.
- The confirmation is displayed in place of the ordinary editable mode-name field; it adds no persistent modal window, timeout, service, or new polling process.

**Source verification:** `tests/hub/test_apollo_hub_layout_v2.cjs` exercises no-confirmation, stale/wrong IDs, invalid indexes, populated/empty groups, last-mode/last-group refusal, stable tile-ID preservation, and Undo round trips. `tests/hub/test_apollo_hub_foundation.py` verifies UI buttons, confirmation and cancellation hooks, minimum-one checks, and edit/close/navigation cancellation. These tests passed in the Stage 3 CI run.

**Desktop verification:** Sync `main`, restart Quickshell, add a disposable mode/group, test CANCEL, confirm removal, test UNDO, and verify the original named tabs and tile arrangement reappear. Check that the original Dashboard still opens if only one mode remains. This source checkpoint is **not** a live desktop PASS yet.

## P1 Stage 4 // Searchable Hub module picker

In EDIT, the tile's **SWAP** button (and EDIT + Enter on a keyboard-selected tile) now opens an in-Hub picker rather than silently cycling to the next module. The selected tile's current module, stable ID, W/H dimensions, and group ownership are retained until a new module is explicitly chosen.

- **Full inventory on empty search:** 10 Hub module IDs from `ApolloHubLayout.MODULE_IDS`, not applications from the operating-system desktop catalog. A typed query filters by case-insensitive display name or module ID. The result line displays matches/total and the number selectable.
- **Current and occupied choices:** The current module is labeled `CURRENT`. A module already occupying another tile in the same group is labeled `IN USE`. Both are visible but unavailable to select; choices used only in a *different* group remain available.
- **Selection:** clicking an available row changes exactly that tile through `Layout.setTileModule(layout, modeIndex, subIndex, tileIndex, expectedTileId, moduleId)`. The policy rechecks the tile's stable ID, authorized module ID, and sibling uniqueness. Module changes do **not** alter saved Notes/To-do data or instantiate any source processes. Existing UNDO can restore the previous module.
- **Keyboard safety:** Opening SWAP focuses the search field; ordinary typing and arrow keys stay in it, and the Hub's global mode-navigation shortcuts are disabled until the picker closes. Escape in the search field and the visible **CLOSE** action cancel without changing the layout. Enter only selects automatically when a *nonblank query* produces exactly one available choice; otherwise the user must click a specific row.
- **Lifecycle:** Opening the picker does not write a layout. The picker closes on explicit selection, canceled search, switching mode/group, leaving EDIT, closing the Hub, undo, or reloading the saved layout. Selection also checks the original mode/group IDs to prevent stale actions.
- **Layout/visual (revised):** The picker is a **368×342 floating dropdown anchored to the tile's actual SWAP button**, not a replacement for the tile grid. It opens below the button when space permits and otherwise flips above, clamped inside the Hub chassis. The underlying grid remains visible at the same scroll position. The dropdown has a text filter, a live match/selectable count, a bounded scrollable results list, a star-handled magenta rail, and CLOSE. Outside taps dismiss without activating another tile, using the same TapHandler input family as TimeW. No extra window, timer, database, app index, or source service is created.

The Stage 4 suite extends `tests/hub/test_apollo_hub_layout_v2.cjs` for filtering, empty-query show-all, duplication constraints, stale IDs, metadata/Undo round-trips and invalid indices. It also extends `tests/hub/test_apollo_hub_foundation.py` to guard search focus, close/escape, counts, selection and the absent cycling path.

**Desktop acceptance:** On the operator's installed Quickshell, open a disposable tile's SWAP dropdown, verify **the tile grid remains visible**, verify all 10 choices with an empty search, filter by `cpu` or `app`, check `IN USE` and `CURRENT`, and scroll the results with the star rail. Test CLOSE, Escape, an outside click, and flipping the dropdown above SWAP for tiles near the bottom of the Hub. Then choose an available module and use UNDO. Confirm W/H settings are preserved, clicking a blank area of the dropdown does not dismiss it, and typing never moves Hub modes. No destructive data operations are required.

## P1 Stage 5 // Move tiles across modes and groups

**What changed:** A compact **MOVE** button appears immediately after SWAP inside each tile's EDIT controls. Like SWAP, MOVE opens a floating dropdown anchored to its own real button; the tile grid stays visible and its scroll position is unchanged. The dropdown lists all *other* submodes, including groups in the current main mode and groups in other main modes, as `Mode / Group` destinations with `[used/8]` capacity counts.

- **Selectable destinations** have room for another tile and do not already contain the selected tile's module. Destinations labeled `FULL` or `IN USE` cannot be selected. The source group is intentionally omitted.
- **Transfer** moves the **original saved tile object** into the destination as its final placement. Stable tile ID, module, size (`half`/`wide`), `rowSpan` and the layout's `nextTileId` remain unchanged. No copy or new tile ID is allocated; the source loses one placement.
- **Selection safety:** `Layout.transferTile()` separately verifies source tile ID, source/destination mode IDs, group IDs, indexes, target capacity and module uniqueness against the current layout. A stale/invalid transfer returns the unchanged layout, without creating an UNDO event.
- **One-step UNDO:** Both source removal and destination insertion are persisted as **one** layout change through the existing `save()` and ten-entry session UNDO. The Hub navigates to the destination group and selects the moved tile after a successful transfer. UNDO restores the previous complete layout; it does not recreate source widget data.
- **Cancellation:** CLOSE, Escape, outside taps, leaving EDIT, closing the Hub, switching modes/groups, restoring layout and starting SWAP/removal cancel the MOVE picker without writing anything. Both pickers use the same floating overlay, flipping above the trigger when needed, and retain the same star-handle scrollbar grammar.
- **Scope:** These are *Hub placements* only. There is no new service, data store, network connection, background timer or modification to To-do, Notes, Media, Clock or other widget-local data. The v2 layout schema and capacity limits (6 main modes, 6 groups/mode, 8 tiles/group) remain the same.

**Source verification:** The extended `tests/hub/test_apollo_hub_layout_v2.cjs` covers same-mode cross-group moves, cross-main-mode moves, invalid IDs and indexes, duplicates, fully occupied targets, metadata preservation, JSON round-trip and UNDO document fidelity. `tests/hub/test_apollo_hub_foundation.py` checks MOVE button placement, dropdown lifecycle, shared overlay, source/destination ID guards, and canonical glow/scrollbar patterns. The foundation workflow runs both tests.

**Desktop acceptance:** After syncing and restarting Quickshell, test EDIT → MOVE on a disposable tile, verify two or more destinations, try an unavailable destination, cancel once, move into a different main mode, and press UNDO. Confirm the tile moves as a placement without losing its module or W/H dimensions. Then create a second group in the same main mode and verify a move between those groups. Reopen the Hub and inspect the saved arrangement. Do not delete or modify personal notes/tasks for this test.

## P1 Stage 6 // Gap-filling tile grid

**What changed:** The existing two-column `Flow` previously made a whole visual row as tall as its tallest tile. A H:3 half-width tile next to H:1 would create a 296px empty block underneath the smaller tile. P1 Stage 6 replaces only the view-positioning container with a deterministic two-column `Item` and a pure `Layout.packTiles(tiles)` projection.

- **First available cell:** Each saved tile is considered in saved array order, and placed in the first free rectangle of cells that fits its **one-/two-column width** and **one-/two-/three-row height**. Short half-width tiles can stack beside a tall half-width tile. A full-width tile always occupies both columns; no overlapping rectangles are allowed.
- **Source of truth unchanged:** The stored `ApolloHubStore.layoutJson` stays at version 2. `tileGrid` is a computed QML property; column/row coordinates are **never persisted**. The stable tile IDs, module data, W/H dimensions, saved order, capacity limits, and previous UNDO behavior remain intact.
- **Geometry:** The original **140px row height** and **8px gap** are unchanged. Half-width card widths remain `(availableWidth - 8)/2`; full-width cards continue filling the available width. The scrollable region measures the highest occupied grid row rather than inheriting Flow's extra height.
- **Visual order note:** A wide tile that cannot fit an early one-column gap may land beneath a tall tile, while subsequent half-width tiles backfill that gap. The saved array order is unchanged, but the resulting on-screen reading order can differ for some mixed W/H arrangements. Stage 7A now derives keyboard-arrow targets from the packed rectangles, rather than saved indexes; runtime arrow testing remains pending.
- **No hidden controls:** SWAP, MOVE, X, W/H, UNDO, navigation tabs and the existing star-scrollbars remain. The new grid does not add menus, settings, services, timers, file IO, an extra layout version, or any new QML parent window.
- **Scope limit:** Enlarged card chassis do not automatically make every mini-widget render more internal content. Internal widget density/expansion is a separate UI polish task.

**Source verification:** `tests/hub/test_apollo_hub_layout_v2.cjs` now checks ordinary layouts, tall-half hole filling, wide tile spans, read-only deterministic projections, invalid inputs, and **1,296 combinations of four mixed-size tiles** for collisions. `tests/hub/test_apollo_hub_foundation.py` requires the computed grid and disallows returning to the old height-wasting Flow. GitHub CI validates both.

**Desktop acceptance:** After syncing `main` and restarting Quickshell, set one disposable half-width tile to H:3 beside H:1 tiles. Check that the shorter tiles fill the column beside it rather than leaving a tall hole. Test W:2, MOVE, SWAP, UNDO and scrolling; verify all tile frames remain distinct, controls remain clickable, and closing/reopening Hub does not change the saved tile sequence. A screenshot is useful if any layout overlaps or clips.

## P1 Stage 7A // Spatial keyboard navigation

**Why:** After Stage 6 first-fit packing, the visible tile positions no longer necessarily match the source array's fixed `±1 / ±2` navigation. For example, a H:3 half-width tile can have three H:1 cards to its right, and a full-width card spans both columns. Stage 7A makes directional keyboard selection use the **same derived grid rectangles** as on-screen placement.

- **Pure selection:** `Layout.navigationTarget(grid, selectedIndex, "left"|"right"|"up"|"down")` selects a neighboring tile that actually lies beyond the source tile's edge in the requested direction, prioritizing perpendicular overlap, nearest edge, and center alignment, then a stable index for ties. At an edge without a matching candidate, selection stays on the same tile. This helper never modifies tile data, order, positions or storage.
- **One route for keys:** Both `hubKeyboardAnchor.Keys.onPressed` and the guarded `Shortcut` handlers call `hub.moveNavigationCursor(direction)`. The original typing guards for To-do/Notes and SWAP/MOVE dropdown focus still prevent global Hub arrows from intercepting text input.
- **Scroll tracking:** When arrows select a card outside the visible portion of `tileScroll`, its existing Flickable shifts to reveal the card; very tall cards prioritize showing their header first. Mouse-hover selection still works, and selection never activates a module by itself.
- **Safety:** The layout remains version 2 with no saved selection coordinates or new services. EDIT + Enter still opens SWAP for the selected tile; Tab and Shift+Tab continue changing main modes, and Shift+Left/Right continue changing submodes.

**Verification:** `tests/hub/test_apollo_hub_layout_v2.cjs` checks ordinary, tall, wide and hole-filling arrow behavior, invalid directions, nonmutation, and directional-edge invariants across **1,296 mixed W/H configurations**. `tests/hub/test_apollo_hub_foundation.py` checks all eight keyboard call sites and the scroll/header rules. Source-level tests and GitHub validation passed.

**Desktop acceptance:** After pulling `main` and restarting Quickshell, open Apollo Hub and enable keyboard focus as usual. Try a H:3 half-width tile beside three H:1 tiles, then navigate with Left/Right/Up/Down. The selection border should move to the nearest card in that actual direction, never to a card that appears on the opposite side. Try a W:2 tile and verify Left/Right stay put at the outer edges. Scroll to lower tiles with Down and verify the focused tile/header becomes visible. Confirm that typing in Notes, To-do and the SWAP filter is not intercepted.

## P1 Stage 7B // Height-aware TIME mini presentation

The initial Stage 7B polish targets the oversized **TIME** tile shown in the operator's Stage 6 screenshot. Before this change, TIME remained a compact clock at the very top of even an H:3 tile, leaving most of the otherwise correctly packed card blank.

- **No saved-data change:** `widgets/hub/ApolloHubTimeMini.qml` reads its allocated content height and derives a presentation-only `densityLevel` 1/2/3. H:1 stays top-aligned with its original 23/20px 24/12-hour clock, date, offset, row spacing, and format toggle.
- **Medium/tall cards:** At available content heights of 180px and 300px, the mini scales clock text, date, offset, and format-button geometry. Its content block is vertically centered within the already allocated tile height. Larger clocks stay color-coded white or orange for unavailable states, while date stays cyan and offset orange.
- **Behavior preserved:** The original tile's 1-second timer remains the only timer; the mini still consumes `TimePolicy.snapshot`, provides the existing 12H/24H toggle, and reports the same statusLine. No new clock service, process, second collector, editor state, persistence, or network access is introduced.
- **Scope:** This is specifically responsive **TIME** content inside larger H:2/H:3 cards, not a blanket scaling rule for other mini-widgets. Calendar, Notes, To-do, Media and CPU++ are separate follow-up layouts because they have interactive lists or specialized controls.

**Verification:** `tests/hub/test_apollo_hub_foundation.py` now checks the three height thresholds, original H:1 typography, centered tall layout, color/status paths, and unchanged source/toggle wiring. Hub source contracts and repository validation passed. An independent, pre-existing TimeW contract test still fails because it forbids the already-used `ApolloHubTimePolicy.js` import in `TimeW.qml`; Stage 7B does not change or claim to repair that unrelated assertion.

**Desktop acceptance:** Pull GitHub `main` and restart Quickshell. In Hub EDIT, set TIME to H:1, H:2 and H:3 in a half-width tile. The compact view should remain familiar, while medium and tall views show a substantially larger centered clock/date/offset block. Toggle 12H/24H and verify neither formatting clips. Try W:2 + H:3 to inspect readability at full width; confirm no new timer and that neighboring tile positions are unchanged. The time still updates every second.

## P1 Stage 7C // Responsive CALENDAR typography

Calendar already used the host tile's available height for its grid. Stage 7C now uses that space for larger, readable month headings, weekday labels, and day numbers at H:2 and H:3, while preserving the original compact H:1 sizes and six-week behavior. The thresholds are the same 180px / 300px heights as the accepted Stage 7B TIME presentation; no new state service, timer, event feed, disk write, or layout version is introduced. The existing previous/next month, Today and SUN/MON controls stay wired to the same calendar bridge.

**VERIFY:** `tests/hub/test_apollo_hub_foundation.py` checks density thresholds, original compact styles, larger typography, preserved bridge properties, and no new timer/file view. Source contracts and validation passed.

**Desktop acceptance:** Pull `main`, restart Quickshell, and set a CALENDAR tile to H:1, H:2 and H:3. Verify the month heading, weekdays, and date numbers become larger without overlapping the existing navigation buttons. Try months with five and six week rows and switch SUN/MON. Verify the active date remains highlighted. This is an appearance-only checkpoint.

## P1 Stage 7D // CPU++ and Uptime height-aware presentation

**Scope:** Two read-only Hub minis now adapt to H:1/H:2/H:3 without new sampling. H:1 preserves the original CPU++ 2x2 gauge arrangement, label/bar sizes, and three-column Uptime layout. H:2 increases typography and centers readings. Narrow H:3 CPU++ stacks all four gauges vertically, while wide H:3 retains two columns; Uptime grows its digits and unit labels.

**Data ownership:** CPU++ still consumes only injected `systemSnapshot` and preserves unknown percentages, stale masking and five-minute last-observation-on-LOADING rule. Uptime still reads only `uptimeSnapshot` and reports Linux boot age, not desktop session age. No `FileView`, `Process`, `Timer`, service, controller, persistence, layout schema, or shell modification is added.

**VERIFY:** `tests/hub/test_apollo_hub_foundation.py` guards H:1 defaults, H:2/H:3 responsive properties, data/view separation, and no new pollers or writes. GitHub CI and desktop rendering are separate acceptance gates.

**Desktop acceptance:** After an operator-authorized merge and normal desktop sync/reload, try EDIT → H:1/H:2/H:3 for CPU++ and Uptime. Confirm readable content without overlapping the tile title or status footer. Try W:1 H:3 vs W:2 H:3 for CPU++ and verify its four gauges stack only in the narrow case. Confirm optional unknown readings remain `--` rather than fake 0%; refreshing data retains truthful last-sample labeling. Uptime remains since Linux boot.

## P1 Stage 8A // Calendar mini TASKS agenda bridge (Level 2 pilot)

H:1 remains the original month grid. H:2/H:3 gain MONTH/AGENDA view controls. Calendar cells gain tap-to-select for the current month, and orange markers for outstanding locally dated **tasks**. AGENDA presents the selected day's due tasks read-only; it distinguishes task due dates from unconnected calendar appointments. The agenda reports empty dates and unavailable storage honestly.

**Single source:** `widgets/hub/ApolloHubCalendarMini.qml` imports the TASKS owner's existing `../tasks/TaskPlannerPolicy.js` and calls `Planner.view()` over the already-injected `ApolloHubTodoStore.snapshot`. `ApolloHubTile.qml` passes the existing `todoSnapshot` to the calendar. No duplicate task store, event service, timer, polling, persistence, backend action, schedule modification, or TASKS-owned source edit is introduced.

**VERIFY:** Hub source contracts guard the cross-widget import, old B9 month behavior, guarded read-only date selection, lack of writers, and the source/status boundary. CI is not desktop acceptance.

**Desktop acceptance:** On an authorized, updated desktop, test H:1 month-only behavior, H:2/H:3 MONTH/AGENDA toggle, day taps, orange due-date markers, selected date's OPEN/DONE list, empty dates and unavailable store; check five/six-week months and SUN/MON toggles. This does not create calendar events or allow task edits.

**NEXT boundary:** WEEK/DAY projections, opening a task in TASKS, and any Level 3 mutation require separate owner-coordinated navigation/focus and action contracts.

## P1 Stage 8B // Read-only WEEK and DAY navigation (Level 2)

Extend Stage 8A's H:2/H:3 Calendar to four compact view selectors: MONTH, WEEK, DAY, AGENDA. H:1 remains the existing month-only calendar. WEEK displays the TASKS owner's Monday-first seven-day projection with due-task counts and tap-to-select days; DAY shows the selected day's tasks with priority and project identifiers. Both WEEK and DAY have previous/next date controls (seven days or one day) and TODAY; AGENDA retains the existing compact selected-day list. Month view still has its separate SUN/MON header toggle.

**Ownership & safety:** All date parsing, cross-day navigation and week counts use existing `TaskPlannerPolicy.js`; the Hub passes only the established `todoSnapshot`. Cross-month moves advance the existing view-only Hub calendar bridge month offset without creating new event/timer data. Navigation is bounded by the original +/-120-month window. No TASKS source, local data, layout schema, media controller, weather feed, writer or user machine file changes. Task dates are **due dates**, never unverified appointments.

**Verification:** Source contracts cover the WEEK/DAY navigation, strict source ownership, H:1 preservation, and no extra poller/write operations. Runtime acceptance must test Monday-first WEEK vs SUN/MON MONTH, crossing month/year boundaries, multiple due tasks and unavailable store, H:2 vs H:3 labels, rapid view switching and no overflow or focus interception. No operator visual acceptance is presumed by CI.

## P1 Stage 8C // Weather Level 2 read-only domains

H:1 retains the original compact Weather card. H:2/H:3 mount `widgets/hub/ApolloHubWeatherExplore.qml`, presenting four independently selectable read-only domains over the **same `ApolloHubLiveBridge.weatherSnapshot`**. WEATHER shows temperature, condition, feels-like and wind. GROUND shows independently fresh AQI and label; pollen, gases, seismic and other Ground data are **NOT CONNECTED**. SKY shows current UV, wind, humidity and direction, but is not a forecast interface. SPACE exposes an explicit **PROVIDER NOT CONNECTED** state: solar, NOAA warning, X-ray, flare and aurora feeds are not present in the Hub bridge.

**Boundary:** No WeatherStation-owned source, weather/space/ground collector, timer, network request, media controller, file write, action authority or saved-layout version is changed. In particular, the WeatherStation's view-scoped seismic, aurora, flare and X-ray services must not be instantiated by a Hub tile; owner-approved shared read-only projections are a future integration seam. Domain selection is transient to each component instance, not persisted.

**Verify:** Hub foundation source contract guards compact presentation, domain selectors, independent weather/AQI readiness, intentional unavailable states and zero new collectors. Workflow now tracks the new Hub-only component. After operator-approved merge and normal desktop sync, compare H:1/H:2/H:3 and W:1/W:2; select all four tabs and verify title, readings, status footer and clipping. Test stale weather versus fresh AQI and the converse. No runtime acceptance or performance proof is inferred from CI.

## P1 Stage 8D // Network Level 2 STATUS / WI-FI / ETHERNET

The H:1 Network card retains the existing compact local-link display. Taller H:2/H:3 cards mount `widgets/hub/ApolloHubNetworkExplore.qml` with transient STATUS, WI-FI and ETHERNET views using the existing injected `ApolloHubNetworkPolicy.snapshot`. STATUS distinguishes active transport and both local links; WI-FI shows guarded SSID, interface, signal and **approximate received Wi-Fi link bitrate** only, not an internet speed test. ETHERNET shows wired presence/connection/interface and explicitly unobserved wired speed. Every mode displays **INTERNET UNVERIFIED**, including locally connected devices.

**Boundary:** No NetworkManager/network device observer, `nmcli`/`Process`/`FileView`/`Timer`, internet probing, connection mutation, shell integration or layout persistence. H:1 remains old presentation. Test unknown adapter/signal/rate, disconnected link, Wi-Fi-only, Ethernet-only, both connected, W:1/W:2, H:1/H:2/H:3, clipping and the status footer on the live desktop.

## DEFERRED WEATHER + RESOLVED TIME CONTRACT

Stage 8C's deeper shared solar, seismic, pollen, gas and forecast feeds are still **owner-dependent**, not silently populated. [Weather deferred-source checkpoint](WEATHER_DEFERRED_SOURCES_20261024.md) records the missing fields, freshness/status rules, service-lifetime constraint and reentry tests. The B10 TimeW CI contract repair was merged in PR #680; earlier PR #675 red checks are historical.

## P1 Stage 8E // Media Level 2 source exploration

The H:1 MEDIA tile retains the original two-column MPD/MPRIS status. H:2/H:3 mount `widgets/hub/ApolloHubMediaExplore.qml` with transient **BOTH / MPD / MPRIS** selection over the already-injected `mediaSnapshot`. BOTH reuses the original `ApolloHubMediaMini`; MPD details show observed state, track/artist, observation provenance/age (only if fresh) and a clearly labeled **LAST KNOWN LOADED** cassette title; MPRIS details show the explicitly selected player's metadata, album and known player count, never auto-select. Both source-specific views retain the **AUDIO OUTPUT NOT VERIFIED** footer.

**Safety boundary:** The existing `ApolloHubMediaPolicy.js` masks stale MPD observations and refuses unselected MPRIS metadata. This view does not create MPD/MPRIS/controller instances, subprocesses, second timers, playback actions, player selection, audio rerouting, preference persistence or external browser windows. It does not alter the Hi-Fi owner widgets. It is Level 2, not Level 3.

**VERIFY:** Hub foundation source contracts validate H:1 preservation, H:2/H:3 mount, MPD/MPRIS identity and stale behavior, provenance and nonactionable layout. Operator desktop acceptance checks W:1/W:2 H:1/H:2/H:3, idle/playing/paused/stopped/stale MPD, selection-required/player-missing MPRIS, title truncation, audio status footer, live media changes and freezes. CI is not a live desktop rendering check.

## P1 Stage 8F // Apps Level 2 catalog inspection

H:1 retains the existing `ApolloHubAppsMini` and its explicit exact-ID tap-to-launch. The H:2/H:3 `ApolloHubAppsExplore.qml` offers **CATALOG / DETAILS**. A tap on a visible entry selects its exact indexed ID and shows app icon, name, generic name and desktop-entry ID **within the Hub**, with BACK TO CATALOG to return. It does not activate an app, create a launch action or open a browser. If the selected indexed ID disappears, the details become unavailable, not stale.

**Dataset honesty:** the single existing `ApolloHubAppsPolicy.snapshot` projects only up to **24** sanitized desktop entries. The bigger tile reports installed count, matches, shown count and **FIRST N OF M MATCHES** when truncated; it does not pretend to show the complete catalog, add an independent scanner, perform filtering of unseen apps or infer active-window state.

**Boundary:** No changes to shared AppsPolicy, ApolloHubLiveBridge, the compact launch function, Quickshell DesktopEntries collection or saved layout. No subprocess, timer, disk access, autostart, implicit launch, program switch or focus action. Source contracts and CI guard the original H:1 launch separately from Level 2 browsing. Live acceptance must check W:1/W:2 H:1/H:2/H:3, selection/back, first-24 indication, app disappearance, empty/unavailable catalog, large names/IDs, scroll and no accidental launch.

## NEXT

Complete Stage 7A/7B/7C/7D/8A/8B/8C/8D/8E/8F desktop acceptance. Next can be Notes and To-do internal density, but those contain editable user data, so changes must preserve editor focus, draft and save-confirmation behavior. Durable undo/presets and drag-and-drop remain separate operator decisions.

## DECISIONS

No new widget services, polling, external sync, unrelated UI change, local desktop action, or merge operation. GitHub is the source of truth; the operator remains responsible for pulling and accepting changes.
