# Team 1 — Shared Process / Resource Contract

Baseline authority at time of writing:

```text
certified patient: 943d27310f68d9941e7b19631fbd56aa9bd633e8
Team 1 branch:     team1/system-liberation
```

This document defines the intended contract boundary for Team 1's shared
Process/Resource physiology. It is architecture guidance for future consumers;
it does not authorize AppControl host rewiring.

## Principle

Process control is shared physiology, not a Task Manager backend.

Known consumers:

```text
Task / HUNTER
APPS
WINDOWS
TABS
RUN
```

Visible UI ownership does not imply backend ownership.

## Team 1 owns

Team 1 provides shared process/resource primitives and policy that can operate
on explicit process records or explicit PID scopes.

Current and emerging shared organs:

```text
ProcessScope
    PID validation/deduplication
    row lookup by PID
    descendant-tree expansion
    root PID -> concrete PID scope

ProcessControl
    SIGSTOP
    SIGCONT
    SIGTERM
    restart

ProcessLimits
    memory limit state
    min/max policy
    limit mutation
    mutation verification

Process safety/policy
    protected-process classification
    unlock requirements
    action safety
    destructive-operation policy
```

The current implementation of the last category is still named
`TaskSafety.qml`. Do not duplicate or rename it merely to satisfy this
document; migration must happen only when a real consumer contract is ready.

## Team 1 does not own

Team 1 must not become canonical authority for:

```text
DesktopEntry identity
application identity
Sway window identity
tab/surface identity
RUN command identity
audio-stream identity
Favorites identity/persistence
```

Desktop/application semantic identity belongs to Team 7's provider/identity
architecture.

Domain/provider teams answer:

```text
"What entity is this?"
"Which root PID(s) belong to this entity?"
```

Team 1 answers:

```text
"Given these process records / PID roots, what concrete scope exists?"
"What safe process/resource operation may be requested?"
"How is the mutation performed?"
```

## Boundary: scope discovery vs process scope

Do not confuse semantic matching with PID-scope expansion.

Examples:

```text
APPS
    provider/identity resolves Brave -> root PID(s)
    Team 1 expands/processes the concrete PID scope

WINDOWS
    Sway/provider layer resolves window -> root PID(s)
    Team 1 expands/processes the concrete PID scope

TABS
    Tab provider + identity bridge resolves surface -> root PID(s)
    Team 1 expands/processes the concrete PID scope

RUN
    RunService resolves command/context -> root PID(s)
    Team 1 expands/processes the concrete PID scope

HUNTER
    task telemetry/ranking resolves selected process set
    Team 1 performs shared process/resource operations
```

Temporary provider-specific keys are acceptable upstream. Team 1 should not
promote them into a competing canonical application identity.

## Mutation contract

Shared mutation backends should accept concrete process targets, not AppControl
mode indexes or UI records.

Preferred shape:

```text
resolved record/PID scope
        |
        v
safety/policy check
        |
        v
confirmation request if needed
        |
        v
ProcessControl / ProcessLimits mutation
        |
        v
refresh/reconciliation signal
```

The backend must not own host keyboard/focus/navigation state.

## Confirmation ownership

Process mutation and host confirmation are separate concerns.

Shared process policy may determine:

```text
operation is destructive
target is protected
confirmation is required
warning/reason text
```

The host owns:

```text
modal visibility
focused button
keyboard routing
cancel/confirm interaction
return focus
```

This is the same principle being used for shared SYSTEM control.

## Safety invariants

A future consumer must not bypass:

```text
PID > 1 validation
protected-process policy
per-action unlock behavior
one-shot/sticky relock semantics where applicable
confirmation policy
live-state reconciliation after optimistic UI
```

Do not create separate APPS/WINDOWS/RUN safety implementations if the policy is
the same physiology.

## Favorites / HUNTER compatibility

Current HUNTER protection still consumes Favorites compatibility:

```text
favoriteStoreObject.favoriteKeys
        ->
HunterOperationController protection behavior
```

Until Team 1 and Team 2 deliberately replace this artery, changes to Favorites
must preserve `favoriteKeys` semantics.

Team 1 must not remove or reinterpret that contract independently.

## Current ProcessPresentationController warning

`ProcessPresentationController.qml` already exposes reusable operations but
still carries Task-oriented state such as:

```text
currentTask
taskRows
```

and Task-oriented request helpers.

Do not deepen those assumptions into the shared lower layer.

Future extraction should separate:

```text
generic process/resource physiology
        from
Task/HUNTER presentation + selected-task convenience state
```

without forcing every consumer through one giant controller.

## Current Team 1 shared organs

As of branch `team1/system-liberation`:

```text
services/system/ProcessScope.qml
services/system/ProcessControl.qml
services/system/ProcessLimits.qml
services/system/TaskSafety.qml

services/system/SystemControl.qml
widgets/system/SystemPresentation.qml
```

The new SYSTEM/Process files on this branch are isolated preparation only.
AppControl host rewiring is still serialized through T3 Overhead.

## Future consumer acceptance test

A process/resource organ is not considered truly reusable until at least one
non-Task consumer can use it without:

```qml
appControlWindow.someProcessFunction()
```

and without inventing its own duplicate mutation backend.

Expected consumer pattern:

```text
provider/identity layer
        |
        v
root PID(s) / process records
        |
        v
ProcessScope
        |
        v
shared safety + ProcessControl / ProcessLimits
```

## Integration traffic law

Parallel-safe work:

```text
services
providers
probes
tests
docs
recon
adapters
```

Serialized through T3 Overhead:

```text
AppControlW.qml rewiring
donor-block removal
shared navigation/detail/result changes
shared selectors
service lifetime integration
```

This document is a contract, not a host-integration authorization.
