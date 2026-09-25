# FILES ↔ Favorites reconstruction contract

Status: Team 2 proposal after certified FILES transplant `6c74628`.

## Ownership

`FileService` owns filesystem semantics and provider identity.

`FileFavoritesAdapter` owns translation between provider identity and persisted
Favorites membership/reconstruction references.

`FavoritesService` owns persisted membership state.

Favorites code must not stat, scan, probe, or otherwise rediscover filesystem
semantics behind `FileService`.

## Canonical provider identity

Normal FILE records emitted by `FileService` already use:

```
file:<full path>
```

That provider ID is the canonical semantic identity consumed by Favorites.

The navigation-only pseudo row:

```
file:parent:<current directory>
```

must never be persisted as a favorite.

## Legacy membership

Certified pre-reconstruction behavior stores FILE favorites through AppControl's
generic fallback:

```
mode:<FILES mode index>:<display label>
```

At `6c74628`, FILES mode index is `2`.

The display label is presentation-derived and is not canonical identity. Team 2
must continue recognizing it long enough to preserve existing saved favorites.

Migration should be lazy and lossless:

1. canonical membership wins when already present;
2. if only the exact legacy key for a live FILE row is present, it may be
   replaced in-place by the provider-owned `file:<full path>` key;
3. duplicate canonical + legacy membership collapses to canonical;
4. ambiguous legacy keys are not guessed or silently reassigned.

## Reconstruction dependency

A canonical saved key gives Favorites a stable path but not enough provider
semantics to recreate a full live FILE row. In particular, Favorites must not
guess whether the target is a file, directory, symlink, missing path, or other
filesystem object.

Therefore the provider needs a resolver contract before host reconstruction is
implemented.

Suggested semantic contract (exact API shape remains FILES-owned):

```
resolveFavoriteIdentity("file:<full path>")
    -> current FILE row
    -> explicit missing/unavailable result
```

The resolved row should use the same shape as ordinary `FileService` records,
including at least:

```
_fileRecord
id
name
label
path
isDir
isParent
kind
mime
detail
```

A missing path must be represented explicitly rather than converted into a
different file with a similar label.

## Activation rule

Favorites should hand the resolved provider row back to FILES behavior for
activation. Favorites must not implement its own `xdg-open`, directory
navigation, reveal, terminal, stat, or filesystem mutation path.

## Host integration is intentionally deferred

This contract does not authorize:

- `AppControlW.qml` changes;
- FAVORITES/COMBI insertion;
- FILES result-model rewiring;
- service lifetime changes.

Those remain serialized T3 host work after the provider-resolution contract is
available and Team 2 is explicitly given a host slot.
