# Team 8 / Team 5 Surface-Launch Seam

## Status

```
SURFACE-LAUNCH OWNERSHIP SEAM
RESOLVED ✅
```

T3 Overhead approved the shared architecture after review.

No AppControlW wiring or donor removal is authorized here.

Certified patient when the seam was resolved:
`6c74628baeaf7cf2f37808f9e57293aaad7e1788`

Team 8 remains on its parallel branch rooted at `943d273` until an authorized host slot
requires re-anchoring.

## Approved ownership

```
T8 / RUN / future launch domains
    launch intent
    base launch plan
    launch mechanism
    application of supplied augmentation
              |
              v
SurfaceLaunchRequirements / SurfaceLaunchCoordinator
    T5 domain authority
    shared + launcher-neutral implementation
    discoverability requirements
    argv/env/bootstrap augmentation
    endpoint / lease coordination
    correlation/bootstrap metadata
              |
              v
launched process
    runtime socket/debug listener lifetime
              |
              v
T5 TabSurfaceProvider
    discovery
    activation
    provider lifecycle
    diagnostics
              |
              v
T7
    semantic interpretation
    relationship evidence / joins
```

T5 owns why and what instrumentation is required. T5 does not become the launcher.

Team 8, RUN, and future launch domains own how a supplied augmentation is carried through
their launch mechanisms. They do not become authorities on Kitty, DevTools, AT-SPI, or
other provider internals.

T7 may consume PID/socket/port/target/correlation evidence, but must not decide whether
those coordinates are injected and must not promote ephemeral bootstrap coordinates into
persistent semantic identity.

## Lifetime rule

Three clocks remain independent:

```
launch transaction
    -> argv/env transformation

instrumentation/application instance
    -> socket / debug endpoint / lease / correlation state

surface provider
    -> scans / records / activation / diagnostics
```

`instrumentation lifetime != TabSurfaceProvider.active lifetime`

Provider inactivity must not tear down instrumentation still required by a running
application.

## Capability rule

SurfaceLaunch is explicit opt-in.

Current capability boundary:

```
KITTY_REMOTE
ACCESSIBILITY
DEVTOOLS
```

Exact API names are not frozen.

The architecture must not become:

```
augmentEverything = true
```

Transaction success/failure callbacks may be used for endpoint or lease bookkeeping but
are not required for basic Team 5 discovery.

## Physical implementation rule

`SurfaceLaunchRequirements` and `SurfaceLaunchCoordinator` are T5-domain-owned shared
siblings.

They need not be children of `TabSurfaceProvider` and need not live in a Tabs-only
namespace.

Invariant:

```
T5 owns contract/domain knowledge
!=
T5 owns process launching
```

That keeps the shared layer usable by APPS, RUN, and later launch domains without creating
APPS -> Tabs or RUN -> APPS dependencies.

## Donor behavior preserved for reconstruction

### Kitty

The donor enables socket-only Kitty remote control and creates a per-launch listen socket.
Team 5 later discovers the resulting socket through process evidence.

### Chromium / Electron accessibility

The donor may enable accessibility environment/argv state so native accessibility
surfaces exist after launch.

### DevTools

The donor may allocate/inject a local debug endpoint so Team 5 can discover page/webview
targets.

The exact donor values remain reference behavior until the T5-domain shared requirements /
coordinator reproduces them.

## Team 8 implementation consequence

Team 8 must:

- keep launch policy independent of Team 5 provider internals
- accept a supplied SurfaceLaunch augmentation
- carry/apply it through Normal / Toolbox / Bottles launch mechanisms
- preserve returned bootstrap/correlation metadata for the transaction boundary
- avoid inventing requirement/capability rules locally

Until the shared T5 contract freezes its exact payload schema, Team 8 treats the supplied
augmentation as opaque data.

`AppLaunchPlanner.qml` now supports this by attaching an opaque
`surfaceLaunchAugmentation` to mechanism-specific plans without inspecting capability
semantics.

## Surgical impact

```
NEW TEAM             NO
HOST SURGERY NOW     NO
SERIAL QUEUE CHANGE  NO
```

T3-R retains the serialized AppControlW host slot.

This issue is no longer an ownership ambiguity. Future disagreement belongs to contract
implementation review.
