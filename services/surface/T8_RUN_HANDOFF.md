# SurfaceLaunch — T8 / RUN Consumer Handoff

Status: minimal shared contract frozen by T3 architecture ruling.

Implementation names in this branch are current working names; the capability
boundary and ownership invariants are the frozen part.

## Consumer flow

A launch domain keeps ownership of its own base plan:

```text
launch intent
    ↓
base launch plan
    ↓
neutral launch evidence
    ↓
T5 SurfaceLaunchRequirements
    ↓
explicit capability request
    ↓
T5 SurfaceLaunchCoordinator
    ↓
augmentation
    ↓
launch domain applies augmentation
    ↓
launch domain executes
```

## Neutral evidence

T8/RUN should adapt their own records into launch evidence rather than passing a
DesktopEntry, RUN record, or host UI record directly into T5.

Current evidence shape:

```text
displayName
localId
startupClass
executable
argv[]
stableHint
```

Not every field is required.

For APPS:
- `displayName` may come from DesktopEntry name
- `localId` may be the DesktopEntry-local id
- `startupClass` may come from DesktopEntry startup class
- `argv` should be the cleaned launch argv
- `stableHint` is only used for deterministic bootstrap preference, not
  semantic identity

For RUN:
- evidence should describe the executable that receives the augmentation
- if RUN is launching a command *inside Kitty*, describe the Kitty launcher
  when requesting `KITTY_REMOTE`; do not pretend the inner workload is Kitty

## Explicit capability request

T5 may suggest:

```text
KITTY_REMOTE
ACCESSIBILITY
DEVTOOLS
```

The consumer must explicitly pass the requested list.

Calling `suggestedCapabilities(...)` is advisory. It is not a global launch
hook.

## Augmentation application

Current output separates:

```text
env
argvAfterExecutable
argvAppend
bootstrap
leases
conflicts
ready
```

The launch domain owns translating that into its own mechanism.

Examples:

### Native argv

`argvAfterExecutable` belongs immediately after the launched executable's own
program token. `argvAppend` belongs with ordinary app arguments.

### Shell command

The shell-launch owner must quote/compose the supplied values safely. T5 does
not construct shell syntax.

### Toolbox

T8/RUN decide whether env/argv augmentation belongs outside or inside the
Toolbox boundary according to the actual process that must expose the surface.

### Bottles/Wine

T8 owns how, or whether, the supplied augmentation can be represented through a
Bottle launch. T5 does not become a Bottles adapter.

## Readiness

Do not execute a returned augmentation unchanged when:

```text
ready == false
```

Reasons include:

- requested capability unsupported for supplied evidence
- caller-supplied endpoint collides with an existing logical lease
- no coordinator DevTools port remains available

The caller decides whether to fall back to an uninstrumented launch, ask for a
different capability set, or surface an error.

## Transaction hooks

After execution attempt:

```text
success -> markLaunchSucceeded(correlationId)
failure -> markLaunchFailed(correlationId)
```

Success does not release instrumentation leases.

Application/process lifetime bookkeeping later calls:

```text
releaseCorrelation(correlationId)
```

Provider deactivation is never a release trigger.
