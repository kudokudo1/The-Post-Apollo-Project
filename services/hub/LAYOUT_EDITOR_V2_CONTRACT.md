# 🏥💜 ApolloHubW // P1 Layout Editor 2.0, stage 1

**Status:** Stage 1 tile removal and Undo accepted on the operator's desktop. Stage 2 width/height edit controls are committed to GitHub `main` with source/behavior checks passing; stage 2 runtime acceptance is pending. The current release does **not** implement drag-and-drop, cross-mode transfer, module picker, or full preset management.

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
- [ ] Operator runtime acceptance after syncing
- [x] Stage 2 edit controls for one/two-column width and one/two/three-row chassis heights
- [ ] Stage 2 operator runtime acceptance
- [ ] Richer grid packing and tile content expansion
- [ ] Main mode/group removal controls
- [ ] Searchable module picker, move between modes, and durable undo/presets

## P1 Stage 2 // Explicit width and height controls

The tile EDIT toolbar now reads **← → SWAP W:1/W:2 H:1/H:2/H:3 ×**, preserving the red destructive `×` after the sizing controls. The `W` and `H` buttons use existing shared `ActionButton` geometry and hover/selection states. This adds no new resize gesture, timer, service, or polling source.

- **W:1** = one column (half of the available Flow width). Click to switch to **W:2** = two columns (full width). Clicking W:2 returns to W:1.
- **H:1** = existing 140px card, **H:2** = 288px, **H:3** = 436px, based on the observed original 140px height and existing 8px tile-flow spacing. Clicking H:3 returns to H:1.
- Both buttons operate only in EDIT mode, refuse writes when layout storage reports corruption or an unsupported version, use `Layout.resizeTile`, and persist only metadata for the selected tile.
- The existing **UNDO** button restores earlier widths/heights, and the default layout retains the same visual sizes and order.
- Height is *tile chassis size*, not a promise that every mini-widget uses all additional space internally. Vertical content expansion and grid-packing polish are separate design work.

**Stage 2 validation:** `tests/hub/test_apollo_hub_foundation.py` checks labels, placement, visibility, signals, storage guard and Undo connection. `tests/hub/test_apollo_hub_layout_v2.cjs` tests dimension cycles, stable identities, adjacent-tile isolation, no-op invalid inputs, swap preservation, and serialization across restarts. Both run under `.github/workflows/apollo-hub-foundation.yml`.

**Desktop acceptance:** after operator pulls latest `main` and restarts Quickshell, enter EDIT, choose a disposable tile, cycle W and H independently, UNDO both, close/reopen the Hub and restart (when convenient) to confirm dimensions persist. Check that a half-width tall tile may leave a blank area beside it under the existing `Flow` layout; this is not a data-loss bug. A future true grid editor will address packing.

## NEXT

After Stage 2 runtime acceptance, the next P1 increment can add mode/submode removal with confirmation and Undo, then searchable module selection. The true grid packing and expansion behavior needs a separate visual and geometry review.

## DECISIONS

No new widget services, polling, external sync, unrelated UI change, local desktop action, or merge operation. GitHub is the source of truth; the operator remains responsible for pulling and accepting changes.
