# Surface Launch Contract — T5 Domain Authority

Architecture ruling: **SURFACE-LAUNCH OWNERSHIP SEAM RESOLVED**

This is a shared, launcher-neutral contract owned by Team 5's surface domain.
It does not make Team 5 a launcher.

Current Team 5 branch remains parallel-safe. No AppControl host rewiring or donor
removal is authorized by this contract.

## Ownership chain

```text
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
    argv/env/bootstrap augmentation construction
    transient endpoint / logical lease coordination
    correlation/bootstrap metadata
              |
              v
launched application instance
    actual socket/debug listener lifetime
              |
              v
TabSurfaceProvider
    post-launch discovery / activation / diagnostics
              |
              v
Team 7
    semantic interpretation / joins
```

## One shared lease authority

APPS, RUN, and future launch domains must all consume the same stateful
`SurfaceLaunchCoordinator` authority.

The implementation is registered as the singleton:

```text
qs.services.surface.SurfaceLaunchCoordinator
```

`SurfaceLaunchRequirements` is also a singleton sibling because its policy is
shared and stateless.

This is forbidden:

```text
APPS -> SurfaceLaunchCoordinator instance A
RUN  -> SurfaceLaunchCoordinator instance B
```

because those independent lease maps could both allocate the same debug port or
socket coordinate.

The required topology is:

```text
APPS ─┐
      ├──> ONE SurfaceLaunchCoordinator singleton
RUN  ─┘
```

Launch domains consume the authority; they never instantiate their own
coordinator or copy its lease state locally.

## Frozen capability boundary

The capability boundary is:

```text
KITTY_REMOTE
ACCESSIBILITY
DEVTOOLS
```

This is explicit opt-in.

An empty requested-capability list is a true no-op: it produces no launch
mutation, no correlation id, no logical lease, and no coordinator lifetime
state even when T5 can recognize discoverability opportunities from the
supplied launch evidence.

Unknown capability names are preserved long enough to be rejected explicitly;
they are never silently dropped into a misleading ready no-op.

`suggestedCapabilities(...)` is advisory domain knowledge. It does not mutate or
launch anything. A launch domain must explicitly pass capabilities to
`buildAugmentation(...)`.

There is no `augmentEverything` mode.

## Launcher-neutral evidence input

Current implementation accepts a small evidence record such as:

```text
displayName
localId
startupClass
executable
argv[]
stableHint
```

These are launch observations/hints, not semantic identity.

T8 may adapt DesktopEntry data into this record. RUN may adapt command/executable
data into the same record. Future launch domains may do likewise.

Team 5 must not require a DesktopEntry object merely to construct surface
instrumentation.

## Augmentation output

The coordinator returns launch data rather than executing it:

```text
correlationId
ready
requestedCapabilities[]
appliedCapabilities[]
unsupportedCapabilities[]
conflicts[]

env {}

argvAfterExecutable []
argvAppend []

bootstrap {
    correlationId
    kittyListenOn
    debugAddress
    debugPort
}

leases[]
```

The launch domain owns applying these values to its actual Native / Toolbox /
Bottle / terminal execution mechanism.

### Why two argv buckets exist

Kitty remote-control flags must be placed with Kitty's own executable options,
while Chromium/Electron accessibility and DevTools flags are appendable launch
arguments.

The shared coordinator describes the placement requirement. It does not own the
mechanism that applies it.

## Current donor behavior preserved

### KITTY_REMOTE

When requested for a Kitty launch:

```text
-o allow_remote_control=socket-only
--listen-on <unix abstract endpoint>
```

A caller-supplied `--listen-on` endpoint is preserved instead of overwritten.

The donor security boundary is also preserved: `KITTY_REMOTE` requires
`allow_remote_control=socket-only`. A caller-supplied broader remote-control
mode is a preparation conflict rather than being treated as equivalent.

Generated endpoint metadata remains discoverable because Kitty exposes the
listen address through its running process environment.

### ACCESSIBILITY

When requested for a supported Chromium/Electron-family launch:

```text
NO_AT_BRIDGE=0
ACCESSIBILITY_ENABLED=1
QT_ACCESSIBILITY=1
QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1

--force-renderer-accessibility=complete
```

An existing renderer-accessibility flag is not duplicated.

### DEVTOOLS

Preferred donor-compatible ports remain:

```text
Brave              9222
Chrome              9223
Chromium            9224
VS Code / Code OSS  9225
VSCodium            9226
generic Electron    9300-9499 deterministic preferred slot
```

The coordinator treats these as preferred coordinates, not persistent identity.
If a preferred port is already logically leased by this coordinator, another
free slot in 9300-9499 is selected.

A caller-supplied `--remote-debugging-port` is preserved. The coordinator
registers that coordinate as a `caller-supplied` logical lease so later
generated augmentations do not unknowingly reuse it. This is coordination
bookkeeping, not a claim that T5 created or owns the runtime listener.

Caller-supplied Kitty listen addresses are handled the same way.

If a caller-supplied coordinate conflicts with an existing logical lease, the
augmentation returns `ready: false` plus a conflict record. A launcher should
not execute a non-ready augmentation unchanged.

The coordinator does not claim that logical lease availability proves the OS
TCP port is free. The launched application owns the actual listener and runtime
failure remains launch/runtime evidence.

## Three independent clocks

The architecture explicitly separates:

### Launch transaction

```text
base launch plan
  -> requirements
  -> augmentation construction
  -> launcher applies augmentation
  -> launch succeeds/fails
```

### Instrumentation/application instance

```text
socket/debug endpoint
logical lease
correlation/bootstrap metadata
actual application/listener lifetime
```

### Surface provider

```text
provider active/inactive
scans
records
activation
diagnostics
```

Invariant:

```text
instrumentation lifetime
!=
TabSurfaceProvider.active lifetime
```

No SurfaceLaunch object reads `TabSurfaceProvider.active`, and provider
deactivation must never release a running application's instrumentation.

## Lease bookkeeping

`buildAugmentation(...)` may reserve generated or caller-supplied endpoint
coordinates for logical collision avoidance.

`ready` is true only when every explicitly requested capability is supported
and no endpoint conflict occurred.

Unsupported or unknown requests fail before endpoint allocation. If a conflict
is discovered after some sibling capability already reserved an endpoint, the
coordinator releases that transaction's partial reservations before returning
`ready: false`. A rejected augmentation therefore owns no instrumentation
lease and creates no application-instance correlation state.

`markLaunchSucceeded(...)` accepts only a known prepared correlation and keeps
its logical leases. Unknown/stale ids do not create state.

`markLaunchFailed(...)` releases the known transaction state/leases.

`releaseCorrelation(...)` is an explicit application/lease-lifetime hook for a
future launcher/process-lifetime owner. It removes correlation state even when a
capability such as ACCESSIBILITY has no endpoint lease.

Transaction callbacks are useful bookkeeping but are not required for ordinary
T5 post-launch discovery.

## Team 7 boundary

SurfaceLaunch metadata such as:

```text
correlationId
kittyListenOn
debugPort
targetId (later observed)
PID (later observed)
```

may become evidence for Team 7 joins.

They must not become persistent semantic application identity merely because
they were generated at launch.

## Team 8 / RUN boundary

T8/RUN own:

- whether a launch occurs
- base plan construction
- Native / Toolbox / Bottle / terminal mechanics
- applying `env`, `argvAfterExecutable`, `argvAppend`, and bootstrap data
- process execution

They do not need to duplicate knowledge of how Kitty remote control, Chromium
accessibility, or DevTools discoverability should be instrumented.

## Host integration rule

This contract is parallel-safe today.

Replacement of donor launch paths such as
`launchApplicationWithTabProvider(...)`, RUN Kitty launch code, or future live
launch wiring remains serialized through T3 Overhead and requires re-anchoring
to the exact certified patient at that time.
