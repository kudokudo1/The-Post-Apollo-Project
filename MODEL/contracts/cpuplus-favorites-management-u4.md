# CPU++ Favorites++ management mode // U4 pilot

> STATUS: draft implementation, not operator-accepted. GitHub-only.
> PATIENT: The-Post-Apollo-Project.
> BASELINE: CPU++ ID Management filter work PR #1481 merged November 8, 2026.

## Operator request

Add an actual Favorites main-mode button in CPU++, placed after SYSTEM and before ID MANAGEMENT and SETTINGS, with an interface for viewing and managing Favorites++ resources.

## Main mode order

OVERVIEW → PROCESS → THERMAL → SYSTEM → FAVORITES → ID MANAGEMENT → SETTINGS.

The older first-slot FAVORITES face was a placeholder. Its face/artwork/entry semantics remain at slot 0, renamed OVERVIEW so only one button says FAVORITES. THERMAL index 2 and SYSTEM index 3, used by shell notification routes and widget callbacks, remain unchanged. Existing ID MANAGEMENT stays at index 5. SETTINGS changes from index 4 to index 6, including TIME resync cancellation, input-focus guards, three-bay visibility and sub-mode cycling. Existing full-size panel dimensions and three bays remain unchanged.

## Data and action flow

Left bay: Existing FavoritesUnifiedCatalog reads the original AppControl, World Clock and saved Places owners. AppControl identity and command text remains redacted; source-readiness is not claimed to be live resource availability. Summary cards display the CPU++ vs APP CTRL category counts, collections and new-default-store counts.

Middle bay: a safe selectable projection from FavoritesManagementPolicy.js of **all four existing AppControl saved lists** (favorites, preferred actions, THERMAL/SYSTEM metric watches and process metric watches), alongside WORLD timezone IDs, saved-place IDs and U1 default favorite/pin keys. Filters now occupy two compact rows: ALL / CPU++ / APP CTRL / CLOCK / PLACES / NEW. Process, THERMAL and SYSTEM donor entries are classified as CPU++, while the remaining AppControl entries are APP CTRL. Both remain AppControl-owned and **read-only** here. Candidate records are bounded and redacted; AppControl's raw commands/paths are neither rendered nor forwarded as action or collection authority. Weather, Hospital and RADIO still await source-owned adapters.

Right bay: selected-resource details and original-owner operations. A two-click confirmation removes eligible Clock/Place/U1 favorites through TimeSettings.toggleWorldFavorite, PlaceRegistry.removeSavedPlace or FavoritesDefaultStore.setFavorite. World Clock removal is gated by installed tzdata validation; when not loaded, the operator can explicitly request the existing owner to load it. U1 pin state is toggled through FavoritesDefaultStore. Collections use the existing FavoritesCollectionPanel and FavoritesCollectionsStore for create, add/remove, reorder and guarded group deletion.

No new favorites JSON files, FileView instances, network sources, provider automation, HUNTER exemptions, process controls or cross-widget launch permissions have been created by the CPU++ panel. A collection is organizational metadata, not a replacement for an owner's original favorite.

## UI path

CPU++ → FAVORITES. The top order ends SYSTEM → FAVORITES → ID MANAGEMENT → SETTINGS. Use middle filters to choose a saved entry and right panel to manage that entry or organize it in collections. The left side displays source overview and counts. AppControl rows may be selected and inspected, but their REMOVE and collection actions remain disabled until their original owner exposes reviewed safe management contracts. Other providers can be added through source-owned adapters.

## Verification

- tests/cpuplus/test_cpuplus_favorites_center.cjs checks bounded safe projection, provider privacy, mode ordering, bay integration and owner action contracts.
- Updated legacy CPU++ tests preserve TIME/LOCATION, existing ID MANAGEMENT, focus and three-bay/monitor semantics.
- scripts/favorites/verify_cpuplus_hub_fedora_u4.sh tests an actual native synthetic selector click on a CPU++-classified AppControl process favorite and verifies no owner actions or file writes. The extended policy tests check all four AppControl lists, bounded admission, redacted numbered labels and separation of source ownership.
- The full live desktop, exact geometry on operator monitors and visual acceptance are not yet verified by this PR.

## Existing constraints and watch points

- This branch was created from PR #1481's head before it merged. PR #1481 is now merged, and current `main` has no overlapping post-merge CPU++ changes. Continue checking current HEAD before eventual integration.
- Legacy CPU++ tests that assumed a six-mode rail are adjusted to this new operator-approved seven-mode order.
- Removing a source favorite does not automatically remove its independent U3 collection reference. Orphaned references remain organizational metadata until deliberately removed.
- Owner save methods may accept a queued operation before it is durably persisted. Do not report success merely because an ActionButton was clicked.
- New-provider resource identifiers are persisted in the U1 default store already. They must remain opaque and non-secret.

## Rollback

Revert the additive CPU++ Favorites mode and associated tests. No existing favorites provider storage schema is modified; reverting does not require data conversion or destructive cleanup.

## Next

Operator visual approval of the two-row filter strip and categorized rows, then source-owned action adapters for AppControl and wider providers. Do not elevate permissions.

## U4b follow-up decision // AppControl category projection

This follow-up changes presentation, not storage or permissions. Explicit donor prefixes `task|`, `thermal|`, `system|`, `watchbox|thermal|`, `watchbox|system|`, and `taskmetric|` determine the CPU++ label. All other AppControl favorite and preferred-action keys remain categorized APP CTRL. Labels use type and ordinal only, never command names or raw filesystem/process identifiers. The original AppControl store remains the only writer; HUNTER behavior is unchanged.
