# CPU++ Favorites++ management mode // U4 pilot

> STATUS: draft implementation, not operator-accepted. GitHub-only.
> PATIENT: The-Post-Apollo-Project.
> DEPENDENCY: CPU++ ID Management filter work PR #1481, in progress.

## Operator request

Add an actual Favorites main-mode button in CPU++, placed after SYSTEM and before ID MANAGEMENT and SETTINGS, with an interface for viewing and managing Favorites++ resources.

## Main mode order

OVERVIEW → PROCESS → THERMAL → SYSTEM → FAVORITES → ID MANAGEMENT → SETTINGS.

The older first-slot FAVORITES face was a placeholder. Its face/artwork/entry semantics remain at slot 0, renamed OVERVIEW so only one button says FAVORITES. THERMAL index 2 and SYSTEM index 3, used by shell notification routes and widget callbacks, remain unchanged. Existing ID MANAGEMENT stays at index 5. SETTINGS changes from index 4 to index 6, including TIME resync cancellation, input-focus guards, three-bay visibility and sub-mode cycling. Existing full-size panel dimensions and three bays remain unchanged.

## Data and action flow

Left bay: Existing FavoritesUnifiedCatalog reads the original AppControl, World Clock and saved Places owners. AppControl identity and command text remains redacted; source-readiness is not claimed to be live resource availability. Summary cards display collection and new-default-store counts.

Middle bay: a safe selectable projection from FavoritesManagementPolicy.js of stored WORLD timezone IDs, saved-place IDs and U1 default favorite/pin keys, with ALL/CLOCK/PLACES/NEW filters. Existing AppControl/Weather/Hospital/RADIO source items remain read-only in the left overview until provider-owned privacy-safe action contracts exist. Candidate source records are bounded; new-provider raw IDs are not printed.

Right bay: selected-resource details and original-owner operations. A two-click confirmation removes eligible Clock/Place/U1 favorites through TimeSettings.toggleWorldFavorite, PlaceRegistry.removeSavedPlace or FavoritesDefaultStore.setFavorite. World Clock removal is gated by installed tzdata validation; when not loaded, the operator can explicitly request the existing owner to load it. U1 pin state is toggled through FavoritesDefaultStore. Collections use the existing FavoritesCollectionPanel and FavoritesCollectionsStore for create, add/remove, reorder and guarded group deletion.

No new favorites JSON files, FileView instances, network sources, provider automation, HUNTER exemptions, process controls or cross-widget launch permissions have been created by the CPU++ panel. A collection is organizational metadata, not a replacement for an owner's original favorite.

## UI path

CPU++ → FAVORITES. The top order ends SYSTEM → FAVORITES → ID MANAGEMENT → SETTINGS. Use middle filters to choose a saved entry and right panel to manage that entry or organize it in collections. The left side displays source overview and counts. Other supported providers can be added later through source-owned adapters.

## Verification

- tests/cpuplus/test_cpuplus_favorites_center.cjs checks bounded safe projection, provider privacy, mode ordering, bay integration and owner action contracts.
- Updated legacy CPU++ tests preserve TIME/LOCATION, existing ID MANAGEMENT, focus and three-bay/monitor semantics.
- scripts/favorites/verify_cpuplus_hub_fedora_u4.sh tests an actual native synthetic selector click with injected owner stubs and no writing to existing user data.
- The full live desktop, exact geometry on operator monitors and visual acceptance are not yet verified by this PR.

## Existing constraints and watch points

- Because PR #1481 still owns an overlapping CPU++ file, this branch was created directly from its head. Merge #1481 first or update the dependency branch before integrating the Favorites manager; do not overwrite its current edits.
- Legacy CPU++ tests that assumed a six-mode rail are adjusted to this new operator-approved seven-mode order.
- Removing a source favorite does not automatically remove its independent U3 collection reference. Orphaned references remain organizational metadata until deliberately removed.
- Owner save methods may accept a queued operation before it is durably persisted. Do not report success merely because an ActionButton was clicked.
- New-provider resource identifiers are persisted in the U1 default store already. They must remain opaque and non-secret.

## Rollback

Revert the additive CPU++ Favorites mode and associated tests. No existing favorites provider storage schema is modified; reverting does not require data conversion or destructive cleanup.

## Next

Operator visual approval, dependency PR integration, then wider owner-safe providers and search/managing more favorite types without elevating permissions.
