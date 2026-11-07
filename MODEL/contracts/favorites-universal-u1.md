# Favorites++ U1 // Default local membership writer and reusable controls

> STATUS: draft implementation, pending independent review and operator acceptance.
> OWNER: services/favorites, new-provider default storage only.
> BASELINE: U0 contract from merged PR #1438.

## Scope and ownership

U1 provides a default local Favorites++ store for NEW providers that do not already own favorites data.
The seven existing AppControl, Weather HOME, RADIO, Time, Places, Notifications and Hospital writers remain unchanged and authoritative. Their U0 read-only adapters are not writers.
Legacy provider namespaces are explicitly refused by FavoritesDefaultPolicy.js to prevent silent duplicate ownership.

## Data model

File: Quickshell.dataDir + /favorites-default-v1.json

Schema: post-apollo.favorites.default.v1

Fields: schema, version=1, revision, favorites, pins.

Each favorites/pins entry is a U0 canonical local key: fav1:local:provider:kind:percent-encoded-resourceId. The store adds no separate labels, measurements, URLs, credentials, account records, executable actions, or source snapshots. **A resourceId is still serialized verbatim (percent-encoded), so a provider must not construct it from secrets, tokens, private content, raw sensitive URLs or commands. Prefer opaque, non-secret, stable identifiers.**
Maximums: 2048 favorite keys, 512 pin keys, 8192 characters per serialized key, 1,048,576 characters per document.
Unsupported versions, extra document fields, noncanonical keys, reserved providers, duplicates, and invalid data block writes until reviewed.
Unfavoriting does not remove an independent pin; no implicit semantic relationship or safety protection is created.

## Persistence lifecycle

Exactly one Quickshell FileView writer uses atomicWrites=true and watchChanges=false.
Missing file means empty writable state, with no automatic write at startup.
One pending FileView write and a latest queued document handle rapid button taps. The visible state is pending/queued, but acceptance of an edit is NOT proof of persistence.
Only onSaved acknowledges the durable revision. onSaveFailed keeps the last acknowledged document, drops pending/queued edits, disables writing, and reports the error.
Malformed, unknown-version, and unsupported-field documents are preserved without silent migration, repair or overwrite.
The writer has no network, process, provider, HUNTER, or permission operations.

## New public API

FavoritesDefaultStore.qml singleton:

- Properties: storageState, errorCode, lastResultCode, favoriteKeys, pinnedKeys, revision, savedRevision, canEdit, busy.
- Read: acceptsKey(key), isFavorite(key), isPinned(key).
- Edits: setFavorite(key,enabled), toggleFavorite(key), setPinned(key,enabled), togglePinned(key).
- Events: favoritesLoaded(), favoritesSaved(revision), favoritesSaveFailed(reason).

An edit returning true means queued or accepted; call sites must use favoritesSaved / savedRevision to confirm durable state.
Editing requires a canonical key for a new provider. Membership is display preference only; not proof of a live resource, subscription, permission, watch, process exemption or device context.

Reusable UI: components/FavoritesToggleButton.qml inherits the established ActionButton style and takes resource (U0 descriptor) and feature (favorite or pin). It validates the descriptor and capability, checks writer readiness and provider ownership, and calls the default store only on a real left click. It has no automatic persistence side effect on creation.

## Verification

tests/favorites/test_favorites_universal_u1.cjs checks malformed/unscoped keys, exact versioned schema, bounds, immutability, reserved owner refusal, UI contract, legacy data isolation and queued revisions.
.github/workflows/favorites-universal-u1.yml runs U0/U1 and legacy regression suites, plus native Fedora 44 Quickshell with synthetic XDG directories.
The native fixture tests actual click -> atomic write, rapid changes -> queued final state, clean process restart and read-only load, corrupt-file bytes preserved, and unsupported-version bytes preserved.
No real user preferences, working desktop, legacy writer or production service is involved.

## Deferred

- U2: runtime provider snapshots, native availability resolvers and actual widget integrations.
- U3: collections, watches, recents, rotations and recall modules with explicit provider authorization.
- U4: universal cross-provider Favorites Center, account/org isolation, and separately approved sync.
- Native production acceptance and independent security review are required before merging/activation.
