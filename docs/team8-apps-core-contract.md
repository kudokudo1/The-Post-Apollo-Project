# Team 8 — APPS Core Integration Contract

Certified origin used by this branch: `943d27310f68d9941e7b19631fbd56aa9bd633e8`

Current canonical patient may advance independently. Do not rebase this branch merely to
look current. Re-anchor only when T3 Overhead releases an authorized host-integration slot.

## Scope

Team 8 owns APPS-specific behavior that remains after shared physiology is removed:

- DesktopEntries catalog consumption
- Native / Flatpak source classification
- HIDDEN adapter input from future RunService
- normal launch semantics
- Toolbox launch semantics
- Bottles launch semantics
- DesktopEntry action presentation
- browser-specific APPS actions
- APPS-local metadata / presentation helpers

## Explicit non-ownership

Team 8 does not own:

- process/resource scope or mutations — Team 1
- tab/surface discovery, activation or provider lifecycle — Team 5
- application/window/tab audio — Team 6
- cross-provider semantic application identity — Team 7
- Favorites persistence/reconstruction — Team 2
- RUN command discovery/history — future RunService
- generic AppControl navigation/detail/result/focus behavior — host-owned

## Current isolated files

### AppCoreProvider.qml

Owns APPS catalog/source/presentation behavior only.

Important contract points:

- `hiddenEntries` is an input seam; APPS must not build a second RUN catalog.
- `appOverrides` is presentation-only and must not become semantic identity.
- Native/Flatpak classification preserves current donor behavior.

### AppLaunchPlanner.qml

Pure planning layer. It does not execute processes.

Produces intent for:

- normal DesktopEntry launch
- Toolbox argv launch
- Toolbox shell launch
- Bottles launch
- HIDDEN dispatch
- unavailable launch states

Surface-launch ownership is now resolved. Team 5 owns the shared launcher-neutral
SurfaceLaunch requirements/coordinator domain; Team 8 owns launch intent, base plans,
launch mechanisms, and application of a supplied augmentation. AppLaunchPlanner carries
that supplied augmentation opaquely until the shared T5-domain contract freezes its exact
payload schema.

### AppCatalogPolicy.qml

Pure APPS catalog/search/ranking policy.

Owns:

- local DesktopEntry key fallback (id, then name)
- APPS search haystack semantics
- HIDDEN-row search over externally supplied RUN rows
- APPS result ordering
- Native/Flatpak source-match ranking

Important donor behavior preserved:

- Native/Flatpak source selection does **not** hide the other source from the catalog.
- HIDDEN switches to the externally supplied hidden-command catalog.
- Favorites may pin rows through an injected preference predicate, but Team 8 has no
  knowledge of Favorites persistence, keys, or reconstruction.

This keeps APPS result behavior reusable without creating an APPS -> Favorites or
APPS -> RUN implementation dependency.

### AppActionPlanner.qml

Pure DesktopEntry/browser action planner.

Owns:

- stable APPS action IDs compatible with the current Favorites detail-action shape
- browser action precedence
- browser shortcut intent
- browser launch-argument intent
- raw DesktopEntry action pass-through intent

It does not:

- focus Sway windows
- invoke `wtype`
- execute DesktopEntry actions
- launch browser processes
- own Favorites persistence
- own semantic application/window identity

That keeps browser action policy in Team 8 while execution/focus mechanics remain separately
integratable.

### AppBottleProvider.qml

Standalone Bottles discovery/state provider.

Owns:

- Bottles CLI discovery
- JSON payload parsing
- legacy text-output fallback
- available bottle names
- default/current bottle selection state
- loading/error state

It does not launch applications and has no AppControl host dependency.

Bottles launch intent remains in `AppLaunchPlanner.qml`, so discovery/state and launch
mechanism stay separately testable.

### AppActionCatalog.qml

Pure action-description layer.

Owns:

- DesktopEntry action harvesting
- browser-specific synthetic actions
- browser keyboard shortcut plans
- browser launch-argument plans

Its browser classifier is a behavior classifier only. It is not canonical identity.

## Future host integration rule

When T3 Overhead eventually releases Team 8 for host integration:

1. re-anchor to the exact certified patient named in that order
2. re-read APPS against that patient
3. preserve all already-landed shared services
4. adapt these isolated files to sibling contracts as they exist at that time
5. do not reintroduce Team 1/5/6/7 physiology into Team 8
6. submit a certification request to T0 Manager rather than giving runtime commands
   directly to the operator

## Identity rule

Until Team 7 freezes a shared contract:

- existing DesktopEntry IDs may be used as local catalog coordinates
- temporary provider keys are acceptable where required
- Team 8 must not publish a competing canonical application identity
- fuzzy browser/source classification remains behavior evidence, not semantic truth

## Launch rule

T3 Overhead resolved the SurfaceLaunch seam.

### Team 8 / launch domains own

- launch intent
- base launch plan
- Native / Toolbox / Bottles mechanism choice
- actual process-launch mechanism
- application of augmentation supplied by the shared SurfaceLaunch layer

### T5-domain-owned shared SurfaceLaunch layer owns

- discoverability requirement descriptions
- capability selection / requirement construction
- argv/env/bootstrap augmentation construction
- transient endpoint / lease coordination
- correlation/bootstrap metadata

This shared implementation is launcher-neutral and need not live physically under
TabSurfaceProvider.

### TabSurfaceProvider owns

- post-launch surface discovery
- activation
- provider lifecycle
- diagnostics

### Team 7 owns

- semantic interpretation of the resulting observations
- relationship evidence / joins

Team 7 must not turn ephemeral launch coordinates such as sockets, debug ports, leases,
or correlation tokens into persistent semantic identity.

### Lifetime separation

Keep these clocks separate:

```
launch transaction
    -> argv/env transformation

instrumentation/application instance
    -> socket / debug endpoint / lease / correlation state

surface provider
    -> scans / records / activation / diagnostics
```

In particular, SurfaceLaunch instrumentation lifetime is not governed by
`TabSurfaceProvider.active`.

### Capability rule

Surface instrumentation is explicit opt-in. The capability boundary currently includes
concepts such as:

```
KITTY_REMOTE
ACCESSIBILITY
DEVTOOLS
```

Team 8 must not implement an `augmentEverything`-style global interceptor.

The exact shared API/schema is not frozen yet. Until T5 publishes it, Team 8 carries the
supplied augmentation opaquely on its launch plans and does not infer provider-specific
requirements itself.

Conceptually:

```
APPS Core
  -> choose launch intent / base plan
  -> request or receive T5-domain SurfaceLaunch augmentation
  -> apply/carry supplied augmentation through Native / Toolbox / Bottles
  -> execute

launched application
  -> owns actual runtime socket/debug listener lifetime

TabSurfaceProvider
  -> discovers / activates / diagnoses

Team 7
  -> interprets relationships
```

This replaces the donor's `launchApplicationWithTabProvider()` coupling without turning
Team 5 into a launcher or Team 8 into the authority on provider instrumentation.

## Certification state

These files are currently standalone and unwired. They do not alter live AppControl
behavior, so there is no runtime certification request yet.

Do not call this work CERTIFIED unless T3 Overhead explicitly says so.
