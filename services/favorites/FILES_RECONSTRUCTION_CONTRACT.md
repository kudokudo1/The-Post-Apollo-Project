# FILES ↔ Favorites reconstruction contract

Status: aligned to T3-F resolver commit `cfb1af0`.

## Ownership

`FileService` owns filesystem semantics, canonical FILE identity, current
filesystem resolution, and FILE activation/navigation behavior.

`FileFavoritesAdapter` owns Favorites-side translation between provider
identity and persisted membership plus legacy migration proposals.

`FileFavoriteResolutionClient` consumes the live FileService resolver without
reimplementing filesystem behavior.

`FavoritesService` owns persisted membership and generic key replacement /
deduplication.

## Canonical provider identity

Normal FILE records use:

```
file:<absolute provider path>
```

The navigation pseudo-record:

```
file:parent:<current directory>
```

is never persistable.

## Provider resolver — T3-F contract

T3-F exposes:

```
FileService.resolveFavoriteIdentity(identity)
FileService.favoriteResolutionFinished(identity, resolution)
```

Resolution is asynchronous for valid identities. Invalid identities may finish
synchronously.

Provider result states are:

```
resolved
missing
unavailable
invalid
```

A resolved result carries a normal current FileService row. Team 2 forwards
these result objects unchanged and does not reinterpret filesystem truth.

Known reasons include:

```
target-does-not-exist
filesystem-record-unavailable
filesystem-record-mismatch
provider-record-invalid
parent-navigation-record
invalid-canonical-file-identity
```

## Team 2 consumer behavior

`FileFavoriteResolutionClient`:

1. accepts a persisted FILE favorite key;
2. obtains the provider identity from `FileFavoritesAdapter`;
3. registers the pending identity before calling FileService so synchronous
   invalid completions cannot be lost;
4. calls `resolveFavoriteIdentity(identity)`;
5. relays only completions corresponding to requests made by that client;
6. forwards the provider resolution object unchanged.

It does not stat, scan, infer type, manufacture a FileService row, or activate a
file itself.

## Legacy membership

Legacy FILE favorites use:

```
mode:2:<display label>
```

Migration remains lazy:

- a live FileService row supplies canonical `file:<path>` identity;
- FileFavoritesAdapter proposes old -> new;
- FavoritesService performs replacement/deduplication;
- ambiguous legacy state is never guessed.

## Activation

After a successful resolution, a future serialized host integration must hand
the resolved ordinary FileService row back to normal FILES behavior.

Favorites must not duplicate `xdg-open`, directory navigation, reveal,
terminal, stat, or other FILES mutations.

## Host boundary

This work does not authorize:

- `AppControlW.qml` changes;
- FAVORITES/COMBI insertion;
- FILES result-model rewiring;
- service-lifetime host surgery.

Those remain serialized T3 work.
