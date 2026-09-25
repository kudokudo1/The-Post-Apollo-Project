# Favorites provider reconstruction requirements

Status: Team 2 consumer requirements. This document is NOT a semantic identity schema and does not supersede Team 7.

## Why this exists

Favorites persists interest. Providers own semantic identity and domain behavior. Team 2 therefore needs a narrow reconstruction contract that lets a saved favorite return to its provider without teaching Favorites how APPS, FILES, WINDOWS, TABS, RUN, or future providers work internally.

The contract below describes what Favorites needs to consume. Providers and Team 7 remain authoritative for the identity they expose.

## Required provider-facing concepts

For any persistable favorite, Team 2 needs:

- provider
- provider-owned persistent key
- reconstruction reference
- provider resolver
- provider activation path
- presentation snapshot or resolved presentation

The provider-owned key is opaque to Favorites except where a provider-specific adapter explicitly documents legacy compatibility.

Favorites must not derive a supposedly canonical identity from display label, mutable title, PID alone, Sway container id alone, tab index, result position, or provider-local coordinates unless that provider explicitly declares them persistent.

## Resolution states

A provider resolver must distinguish resolved, missing/unavailable, ambiguous, and invalid. Favorites must not convert ambiguity into first-match-wins.

## Reconstruction result

The resolved object should be a normal provider record, not a Favorites-owned parallel model. Favorites wrappers may attach _favoriteRecord, _favoriteKey, _sourceModeIndex and _sourceItem, but those wrappers must not become a second provider implementation.

## Activation

After reconstruction, activation must route back through provider/domain behavior. FILES should use FileService behavior; APPS should use APPS launch adapters; RUN should use RUN launch behavior; WINDOWS should use the Sway/window provider; TABS should use Team 5 activation. Favorites should not duplicate those mutations.

## Current domain state at certified patient 6c74628

### FILES

Provider rows already expose file:<full path>. Team 2 has a parallel-safe FileFavoritesAdapter for membership and legacy compatibility. Provider resolution is still required before global Favorites reconstruction is implemented.

### RUN

Current donor keys are structured as run:<encoded command>, run:kitty:<encoded command>, and run:toolbox:<encoded command>. They are reconstructable today because AppControl owns both parsing and RUN record creation.

Future rule: RunService/provider owns that semantic contract. Team 2 consumes it rather than moving RUN parsing or launch semantics into FavoritesService.

### APPS

Current donor membership uses entry.id with fallback to entry.name. Team 7 identifies DesktopEntry identity as a primary source but has not frozen the shared semantic identity schema. Team 2 should not hard-code a new APPS adapter until that contract stabilizes.

### WINDOWS

Current Favorites membership still falls through mode:<modeIndex>:<label>. That is explicitly temporary and not persistent semantic window identity. Team 2 must wait for Team 7 and the eventual window provider contract before migration.

### TABS / surfaces

Provider-native keys exist for Kitty, DevTools, AT-SPI and related sources, but these are provider-local or lifetime-scoped observations. Team 2 must not promote them into cross-provider application identity.

Persistent tab/surface Favorites require a provider-supported reconstruction contract from Team 5 plus semantic relationship guidance from Team 7.

## Legacy migration rule

Provider adapter recognizes the old key and emits an old->new migration plan. FavoritesService owns replacement, deduplication and persistence. The adapter does not rewrite storage itself.

## Host integration boundary

This document does not authorize AppControlW changes, FAVORITES/COMBI result insertion, provider lifetime integration, or navigation/detail/result rewiring. Those remain serialized T3 work.

## Team 2 go/no-go rule

Team 2 may build a provider adapter when the provider can answer both:

1. What persistent semantic key should Favorites store?
2. How does the provider resolve that key back into a current provider record?

If either answer is missing, Team 2 stops at contract/recon/test preparation rather than inventing the missing semantics.
