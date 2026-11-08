# Favorites++ U3a // Local collections and ordered membership

> STATUS: proposed implementation in a draft PR, awaiting operator visual acceptance.
> PATIENT: The-Post-Apollo-Project. OWNER: Favorites++ service family.
> SCOPE: Local grouping metadata only. U0, U1 and U2 remain authoritative for their contracts.

## What changed

U3a introduces named collections and ordered membership as a reusable Favorites++ capability.
Unlike adding a favorite, adding a reference to a collection never writes the underlying provider's favorite list, subscribes to any data, launches an item, changes availability, or modifies process safety policy.
Existing favorites remain owned by AppControl, Clock, Places, Weather, Radio, Notifications and Hospital.

## Storage

- New local single-writer service: services/favorites/FavoritesCollectionsStore.qml.
- Distinct on-disk file: Quickshell.dataDir + /favorites-collections-v1.json.
- Versioned schema: post-apollo.favorites.collections.v1.
- Schema fields: schema, version, revision, nextId, collections; each collection has id, name, members.
- Each member is a canonical U0 `fav1:local` key, not a provider record or live measurement.
- Hard limits: 24 groups, 80 references per group, 600 references total, 48 characters per name, 262144 characters per document.
- Missing file starts empty with no immediate write. Unsupported/invalid files are preserved, never silently repaired or overwritten.
- FileView atomic writes, deferred dispatch, a single pending edit and latest queued revision prevent overlapping writes and reentrant callback races.
- The visible state can include pending changes. Only collectionsSaved(revision) / savedRevision confirm durable persistence.

## Initial provider eligibility

U3a accepts canonical, non-secret references for installed timezone identities (TimeSettings), stable numeric saved-place IDs (PlaceRegistry), and new U1 providers with compact, opaque, restricted identifiers.
AppControl saved commands/paths, Notifications, Hospital, Radio and Weather HOME refs are intentionally excluded until their owners provide explicit safe collection adapters. This prevents storing sensitive command/path data by copying raw legacy keys.
Acceptance into a collection is not permission to open, execute, restore, protect or otherwise act upon an item.
Collection refs are retained even when the original item is later unavailable; no automatic data deletion or provider mutation.

## Public API

FavoritesCollectionsStore exposes collections, revision, savedRevision, canEdit, busy, errorCode, lastResultCode and immutable edit operations:

- createCollection(name) -> new ID on accepted request, empty string on rejection.
- renameCollection(id,name), deleteCollection(id).
- setMember(id,key,enabled), toggleMember(id,key), moveMember(id,key,direction).
- hasMember(id,key), acceptsKey(key).
- collectionsLoaded(), collectionsSaved(revision), collectionsSaveFailed(reason).

Reusable UI components: FavoritesCollectionToggleButton.qml and FavoritesCollectionPanel.qml. They receive an injected owner and an explicit U0 resource descriptor supporting the `collection` capability.

## First Clock UI

Use Clock / TimeW → CLOCK → WORLD → ALL FAVS → GROUPS. Create a name, select an installed zone, click ADD to include the current zone, use arrows to order a selected member, and use two clicks to confirm collection deletion.
The existing WORLD star still writes only through TimeSettings. Grouping a zone is separate from starring it.
Other widgets can embed the same panel after an owner-reviewed resource adapter is implemented.

## Verification

- tests/favorites/test_favorites_universal_u3.cjs covers strict parsing, capacity, ordering, source namespace isolation, malformed states, and existing UI contracts.
- Fedora Xvfb native suite clicks the CREATE button, processes rapid edits, checks saved ordering, restarts, verifies byte-preserving corrupt/unsupported file refusal, and confirms that no existing favorites store was written.
- U0/U1/U2 and original World Clock regressions must continue passing.
- Operator visual acceptance on the actual monitors is a separate gate. No local desktop writes or Quickshell restart are part of this PR.

## Follow-up (not part of U3a)

Read-only collection browsing across more widgets, safe adapters for other provider families, collection search/filter and verified availability, recents, watch subscriptions, and explicitly authorized recall actions.
Preserve independent permissions and never equate pinning/grouping with HUNTER or Hospital protection.

## Rollback

Revert the U3 PR. The new collections file is independent of all existing favorites stores. No existing data schema migration or rollback transformation is required.
