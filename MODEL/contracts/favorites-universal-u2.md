# Favorites++ U2 // Injectable cross-widget read-only catalog

> STATUS: draft implementation; independent review and operator visual acceptance pending.
> PATIENT: The-Post-Apollo-Project
> OWNER: Favorites++ U2 presentation and read-only contract
> BASELINE: U0 and U1 merged; no storage migration or action transfer.

## Purpose

Make Favorites++ visibly useful outside AppControl while preserving all established provider ownership. The initial U2 Clock WORLD pilot shows AppControl, World Clock and saved Places favorites together via the already-existing singleton owners.

## Components and data flow

- services/favorites/FavoritesUnifiedCatalog.qml is an injectable, non-singleton catalog. Existing FavoritesStore, TimeSettings and PlaceRegistry singleton objects are passed in by the consumer. It does not create owners, poll providers, or write anything.
- services/favorites/FavoritesReadOnlyAdapters.js (from U0) projects current owner snapshots into provider-neutral descriptors.
- services/favorites/FavoritesCatalogPolicy.js bounds/redacts the display, deduplicates identities, reports invalid records and shows explicit store readiness independently of item availability.
- components/FavoritesUnifiedPreview.qml is a reusable compact display, with source counts, scrollable items and an explicit READ ONLY notice. It cannot invoke any original action.
- widgets/TimeW.qml exposes an opt-in ALL FAVS button alongside the original WORLD favorites controls and an overlay preview. WORLD timezone selection and original star still use TimeSettings.

## Identity, privacy and authority

AppControl saved identities may contain command text, process names and file paths. The universal preview does not expose AppControl raw keys or labels, using only generic type names. Clock timezone strings and saved Places labels are displayed locally. All displayed saved resources remain availability=unresolved, regardless of whether a source file has loaded successfully.

Store states (READY, LOADING, ERROR, UNSUPPORTED, UNVERIFIED) reflect the status of the source file only. They are not live data/provenance claims.

No universal mutation, provider launch, favorite migration, process/HUNTER safety alteration, inter-widget command, browser call, network access, org/account scope or synchronization is introduced. No new writer file exists.

## U2 UI path

Open existing Clock/TimeW > CLOCK > WORLD section > ALL FAVS. Close with CLOSE ALL or the popup X. This is a read-only preview of three provider families; it does not replace Clock's own favorite stars or AppControl's FAVS/COMBI view.

## Evidence and test scope

- tests/favorites/test_favorites_universal_u2.cjs: pure policy checks for counts, duplicate/invalid entries, redaction, bounded display, source state vs resource availability, and source/UI integration invariants.
- tests/favorites/fixtures/FavoritesU2NativeProbe.qml and scripts/favorites/verify_unified_catalog_fedora_u2.sh: synthetic Fedora Quickshell display and reactive QML-owner change probe, no real user data.
- .github/workflows/favorites-universal-u2.yml also runs U0, U1 and Clock regression tests.
- Native source/production UI acceptance is separate. The native fixture does not click the actual TimeW ALL FAVS control or assert geometry on the user's monitors.

## Future gates

- Expose the same opt-in component to other widgets without rewriting its implementation.
- Add real Weather HOME/Radio/Notifications/Hospital adapters only through their existing live owner objects; never create duplicate stores.
- Add provider-owned identity/liveness resolvers and explicitly authorized recall controls in a separately reviewed milestone.
- Build the full Favorites Center only after its input, focus, and privacy behavior are operator-accepted.

## Rollback

Revert this additive PR. No previous favorites document was modified or migrated, so rollback needs no data migration. Existing Clock WORLD favorite controls remain independently functional.
