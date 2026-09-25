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

### AppCoreFacade.qml

Standalone composition surface for future host integration.

It owns no new physiology. It instantiates and routes the isolated Team 8 organs behind one
host-neutral API:

- DesktopEntries catalog access
- HIDDEN adaptation from externally supplied RUN command names
- catalog/search/result policy
- source labels / launchability
- APPS presentation metadata
- action catalog + action planning
- launch planning + supplied SurfaceLaunch augmentation transport
- remembered-selection lookup
- Team 7 DesktopEntry evidence delegation
- Bottles discovery refresh/state

External inputs remain explicit:

```
identityEvidence      Team 7 contract
hiddenCommandNames    future RunService
preferencePredicate   optional Favorites/host ranking signal
surface augmentation  T5-domain shared contract
```

The facade deliberately contains no:

- AppControl mode or selection state
- generic navigation/detail wiring
- Team 1 process/resource implementation
- Team 5 TabSurfaceProvider lifecycle
- Team 6 audio implementation
- Team 7 semantic resolver implementation
- Team 2 persistence implementation

This is the preferred Team 8 integration surface when T3 eventually releases an APPS host
slot. The future host should not need to instantiate every Team 8 organ separately unless a
specific architectural reason emerges.

### AppIdentityAdapter.qml

Thin Team 7 identity handoff.

Expected injected contract:

```
desktopEntryObservation(entry) -> Team 7 observation envelope
```

The adapter may expose the resulting `providerKey` and `raw` fields for APPS consumers,
but it does not recreate Team 7 semantics.

It must not implement:

- alias normalization
- relationship kinds
- lifetime classification
- resolver scoring
- canonical application keys
- ambiguity resolution

This keeps Team 8 as DesktopEntry catalog/launch authority while Team 7 remains semantic
identity authority.

### AppSelectionPolicy.qml

Pure APPS selection-remembrance policy.

Owns only:

- deriving the remembered APPS key from the local catalog key
- resolving a remembered key back to an APPS row index
- donor fallback semantics: empty catalog -> `-1`, missing key -> first row

It explicitly does **not** mutate:

- `selectedResultIndex`
- ListView position
- focus
- detail pane state
- generic host navigation

Those remain serialized host concerns.

### AppHiddenAdapter.qml

Pure HIDDEN-to-APPS adapter.

Owns:

- converting externally discovered command names into APPS-shaped records
- donor-compatible hidden record metadata
- known CLI icon hints
- DesktopEntry icon fallback using Team 8 launch-executable parsing

It does **not**:

- discover commands
- own RUN history
- execute commands
- contain an AppControl callback
- define canonical application identity

Current records intentionally omit the donor's embedded `execute()` closure. HIDDEN
execution is represented later as `AppLaunchPlanner` HIDDEN intent.

The future RunService remains responsible for supplying the command catalog; Team 8 only
adapts those externally supplied rows into APPS presentation records.

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

## Pre-integration donor parity

`services/apps/validate_donor_parity.py` is a temporary semantic guard while the donor
APPS implementation still exists in `AppControlW.qml`.

It checks that the live donor and isolated Team 8 organs still agree on:

- Flatpak classification
- source labels
- launch-command availability
- DesktopEntry field-code cleanup
- browser classification
- browser action catalog
- browser shortcut policy
- browser launch arguments
- HIDDEN icon/record shape
- APPS local key fallback
- result-policy anchors

It also asserts the intended decoupling: the extracted HIDDEN adapter must not retain the
donor's `execute()` callback or an AppControl back-reference.

This guard is **pre-integration only**. Once T3 authorizes APPS donor-block removal, it
must be retired or converted to fixture/golden tests rather than being used to demand that
removed donor code remain present.

## Future host integration rule

When T3 Overhead eventually releases Team 8 for host integration:

1. re-anchor to the exact certified patient named in that order
2. re-read APPS against that patient
3. preserve all already-landed shared services
4. adapt these isolated files to sibling contracts as they exist at that time
5. do not reintroduce Team 1/5/6/7 physiology into Team 8
6. submit a certification request to T0 Manager rather than giving runtime commands
   directly to the operator

## Team 7 evidence contract

Team 7 has frozen the minimal observation/evidence envelope:

```
provider
providerKey
lifetimeClass
generation
raw
aliases[]
relationships[]
```

Current Team 7 artifacts consumed as contract references:

- `services/identity/TEAM7_CONTRACT.md`
  blob `87f87ba0c9484d879aef7da8dfd0be80c945faf8`
- `services/identity/DesktopIdentityEvidence.qml`
  blob `ae2d07329b4e4c97a13f79a67131c2363ec99eaf`
- `services/identity/DesktopIdentityRelations.qml`
  blob `378327a67a395f67c52b20cb9b829c10d3ce809e`

For Team 8, the important API is `desktopEntryObservation(entry)`.

Team 8 should delegate DesktopEntry evidence wrapping to Team 7 rather than duplicating:

- alias vocabulary
- normalization semantics
- lifetime classification
- relationship vocabulary
- resolver status/ambiguity semantics

DesktopEntry IDs remain valid Team 8 catalog coordinates but are not promoted by Team 8
into universal cross-provider application identity.

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

T5 has now published the launcher-neutral implementation on
`feature/team5-tab-surface-provider`.

Consumed contract artifacts at the time of this update:

- `services/surface/SurfaceLaunchRequirements.qml`
  blob `e23792b67bd2f3d0f5dbfe29d1348aa46f4f0b72`
- `services/surface/SurfaceLaunchCoordinator.qml`
  blob `45b10920f5940493815433df1e7cb8fb6b5f6fd1`
- Team 5 contract blob
  `e73d1a389fb321972a6c2834cb3d43f8e092e7be`

The launcher-facing augmentation shape currently includes:

```
ready
correlationId
env
argvAfterExecutable
argvAppend
bootstrap
requestedCapabilities
appliedCapabilities
unsupportedCapabilities
leases
conflicts
```

Team 8 consumes this generic structure and applies its argv/env transport semantics
without interpreting capability-domain policy.

Wrapper transport is mechanism-aware. In particular, `argvAfterExecutable` must not be
blindly inserted after token 0 for a Flatpak DesktopEntry because token 0 is `flatpak`,
not the application executable. Team 8 currently keeps Flatpak application-facing
augmentation after the existing wrapper/application coordinates, while direct/native argv
places `argvAfterExecutable` immediately after the executable token.

Shell and Bottles plans retain normalized SurfaceLaunch augmentation for their
mechanism-specific executors; Team 8 does not invent shell quoting or Bottles argument
transport before those executors are defined.

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
