# Team 7 — Surface launch ownership seam

Status: **CLOSED / RESOLVED by T3 Overhead**.

Current certified patient when observed:
`6c74628baeaf7cf2f37808f9e57293aaad7e1788`

Team 8 documented an ownership seam around launch-time instrumentation whose
purpose is making Team 5 surfaces discoverable. T3 Overhead has now resolved
that seam.

Approved ownership:

```text
T8 / RUN / future launch domains
    own launch intent, launch mechanism, and application of supplied augmentation

T5-domain SurfaceLaunchRequirements / SurfaceLaunchCoordinator
    own discoverability requirement descriptions
    own argv/env/bootstrap augmentation construction
    own transient endpoint / lease coordination
    own correlation/bootstrap metadata

launched process
    owns actual runtime socket/debug listener lifetime

T5 TabSurfaceProvider
    owns post-launch discovery, activation, provider lifecycle, diagnostics

T7
    owns semantic interpretation, relationship evidence, and joins
```

The SurfaceLaunch components are T5-domain-owned but physically launcher-neutral
shared siblings. They do not make Team 5 the launcher and do not require APPS→Tabs
or RUN→APPS coupling.

Examples currently preserved in donor behavior include:

- Kitty remote-control socket preparation
- accessibility-enabling environment/flags
- Chromium/Electron remote-debugging ports

## Team 7 boundary

Team 7 should **not** own these mutations.

Semantic identity may eventually supply evidence such as:

- application family / aliases
- DesktopEntry relationship
- running instance relationship
- ambiguity state

That evidence can help an authorized launch/provider adapter decide whether an
augmentation applies. It does not make Team 7 the owner of argv/environment
mutation or provider bootstrap policy.

## Resolved capability boundary

Surface instrumentation is explicit opt-in, never a global launch interceptor.

Conceptually:

```text
surfaceCapabilitiesRequested:
    KITTY_REMOTE
    ACCESSIBILITY
    DEVTOOLS
```

Exact API names are not frozen. The capability boundary is.

## Lifetime invariant

Keep these clocks independent:

```text
launch transaction
    -> argv/env transformation

instrumentation/application instance
    -> socket / debug endpoint / lease / correlation state

surface provider
    -> scans / records / activation / diagnostics
```

In particular:

```text
instrumentation lifetime
!=
TabSurfaceProvider.active lifetime
```

Provider inactivity must not destroy instrumentation still required by the
running application.

## Team 7 consequence

Team 7 may consume resulting:

- PID
- socket/listener coordinate
- debug port
- DevTools target
- launch correlation/lease metadata

as relationship evidence.

Team 7 must not:

- decide whether launch augmentation is injected
- own argv/environment mutation
- own provider bootstrap policy
- make socket/port/target/correlation coordinates persistent semantic identity
- conflate instrumentation lifetime with surface-provider lifetime

The safe architecture is now:

```text
launch intent / mechanism              T8 / RUN / launch domain
        |
        v
surface requirement + augmentation     T5-domain shared SurfaceLaunch
        |
        v
execution / running process
        |
        v
surface observation                    T5 TabSurfaceProvider
        |
        v
semantic interpretation                T7
```

Ownership is resolved. Future disagreement here is a contract implementation
issue rather than an ownership ambiguity.
