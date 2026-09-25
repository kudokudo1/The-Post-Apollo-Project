# Team 1 — Integration readiness packet

Status at preparation time:

```text
Team 1 branch:
team1/system-liberation

prepared-lineage marker:
d78f487f5df0932538445960eb081384713f8a0a
Add Team 1 integration readiness packet

live Team 1 HEAD:
verify team1/system-liberation at handoff time

current certified host:
8f5bb8f0cf67b526ed8cac577980e0416c176ed2
Wire AppControl to RemoteController

historical Team 1 merge base:
943d27310f68d9941e7b19631fbd56aa9bd633e8
```

This packet does not request or authorize serialized host surgery.

## Post-REMOTE donor-drift audit

The following donor targets were compared between certified pre-REMOTE
`6c74628` and certified post-REMOTE `8f5bb8` and were textually unchanged:

```text
SYSTEM:
systemAccent
systemIconAccent
systemRateMetricParts
systemIconFor
monitorResultIcon
systemRebootArmed
systemComponentWarning
runSystemComponentAction
terminateSystemContributor
contributorRows

APP/WINDOW/TAB resource physiology:
selectedResourceScopeContainsProtected
selectedResourceScopeContainsLockedProtected
resourceLimitPidPolicyKey
selectedResourceRootLimitState
selectedResourceLimitAvailable
setSelectedResourceMemoryLimitMiB
reconcileSelectedResourceLimitPolicy
selectedResourceScopeIsFrozen
toggleSelectedResourceFreeze
```

Therefore the REMOTE transplant created no known collision with Team 1's
prepared donor map.

## Prepared service dependency graph

```text
ProcessIdentity
       |
       +----------------------+
       |                      |
       v                      v
ProcessActionController   ProcessResourceState
       ^                      ^
       |                      |
ProcessSafety                |
ProcessLimits                |
ProcessControl               |
                              |
ProcessScope ----------------+
       |
       v
ProcessResourceScope
       |
       v
ProcessResourceController
       |             |
       v             v
ProcessControl   ProcessLimitMutation
```

Presentation:

```text
ProcessScope -> ProcessPresentation

SystemPresentation
SystemControl -> ProcessControl
SystemMonitorController
    <- selectionAdapter
    <- optional favoriteAdapter
    <- SystemPresentation
    <- SystemControl
```

## Lifetime requirements for a future serialized transplant

The shared runtime should eventually provide one lifetime each for:

```text
ProcessIdentity
ProcessScope
ProcessSafety
ProcessControl
ProcessLimitMutation
ProcessLimits
ProcessResourceScope
ProcessResourceState
ProcessResourceController
ProcessActionController
```

The exact shell/AppControl ownership location is a T3 integration decision.

Important wiring:

```text
ProcessActionController.processIdentity -> ProcessIdentity
ProcessActionController.safetyService   -> ProcessSafety
ProcessActionController.limitsService   -> ProcessLimits
ProcessActionController.controlService  -> ProcessControl

ProcessLimits.mutationService           -> ProcessLimitMutation

ProcessResourceScope.processScope       -> ProcessScope
ProcessResourceScope.safetyService      -> ProcessSafety

ProcessResourceState.processIdentity    -> ProcessIdentity
ProcessResourceState.resourceScope      -> ProcessResourceScope

ProcessResourceController.resourceScope -> ProcessResourceScope
ProcessResourceController.resourceState -> ProcessResourceState
ProcessResourceController.processControl-> ProcessControl
ProcessResourceController.limitMutation -> ProcessLimitMutation

SystemControl.processControl            -> ProcessControl
```

## SYSTEM donor replacement map

Future replacements:

```text
systemAccent
systemIconAccent
systemIconFor
systemRateMetricParts
systemComponentWarning
contributorRows
    -> SystemPresentation

runSystemComponentAction
terminateSystemContributor
    -> SystemControl
```

Do not move `monitorResultIcon` into shared SYSTEM physiology. It is a
host-level Task/Thermal/System aggregator.

Do not preserve `systemRebootArmed` as meaningful shared state. It is dead
legacy host state; current donor never arms it.

## Process/Resource donor replacement map

Generic physiology already prepared outside the host:

```text
PID dedup / row lookup / descendant tree
    -> ProcessScope

process persistent identity
captured target identity
PID policy keys
    -> ProcessIdentity

protected-process policy + unlock state
    -> ProcessSafety

STOP / CONT / TERM / restart
    -> ProcessControl

verified RLIMIT_AS mutation
    -> ProcessLimitMutation

single-process limit policy compatibility
    -> ProcessLimits

entry-driven Task-style destructive action policy
    -> ProcessActionController

resolved multi-process scope safety/ranges/text
    -> ProcessResourceScope

scope/PID resource policy state
    -> ProcessResourceState

multi-process LIMIT + FREEZE/THAW orchestration
    -> ProcessResourceController

pure process display helpers
    -> ProcessPresentation
```

Provider-specific root discovery remains outside Team 1:

```text
APP roots
WINDOW roots
TAB roots/lifecycle/debug-port matching
RUN contextual matching
semantic scope-key generation
```

## Cross-team boundaries

```text
Team 7:
DesktopEntry/Application/Sway/Tab semantic identity

Team 1:
Linux process identity + resolved process scope physiology

Team 2:
Favorites persistence and provider adapters

T3-F:
FILES filesystem truth / favorite reconstruction resolver

Team 5:
Tab/surface discovery and activation

Team 6:
Application audio
```

Do not promote `ProcessIdentity` into canonical application identity.

## Favorites / HUNTER invariant

The current HUNTER protection artery remains:

```text
favoriteKeys
    -> HunterOperationController favorite protection
```

A Team 1 transplant must preserve this until a separately coordinated Team 2
migration replaces it.

## Known lesions deliberately preserved

### RSS critical metric

```text
metricIsCritical(entry, "rss")
    -> checks entry.mem
```

Classification:

```text
PRE-EXISTING LESION
```

Do not silently repair during compatibility transplant.

### Resource freeze optimism

```text
resourceFrozenScopes / frozenScopes
    = optimistic state with no expiry
```

A partial failed STOP can leave visible frozen state optimistic indefinitely.

Classification:

```text
PRE-EXISTING LESION
```

Do not silently repair during compatibility transplant.

## Intentional hardening already present in prepared organs

These differ from the donor only to strengthen safety/accounting:

```text
confirmed destructive action:
PID + name + persistent process identity revalidation

Favorites-backed Task/process record:
normalize through ProcessIdentity.sourceEntry before safety/limit/state policy

multi-process RLIMIT:
verified per-PID kernel result wins over requested uniform UI policy

partial RLIMIT batch:
successful PID outcomes retained; scope not falsely reported uniform
```

Each hardening remains outside the live host until serialized integration and
runtime certification.

## Behavioral contract suite

Team 1 now carries a non-destructive QtTest suite:

```text
tests/system/tst_Team1ProcessSystemContracts.qml
```

It exercises pure/process-policy behavior only. It does not instantiate the real
RLIMIT mutation backend or call real `Quickshell.execDetached()` mutations.

The suite locks:

```text
favorite-wrapper process identity normalization
PID reuse / captured-target revalidation
descendant process-scope expansion
protected-process unlock + cancel/relock behavior
protected process-resource blocking
verified per-PID RLIMIT state
partial RLIMIT result accounting
hard-limit clamp divergence
the deliberately preserved freeze-optimism lesion
the deliberately preserved RSS/mem compatibility lesion
SYSTEM rate-metric presentation parsing
```

Run it with the repository's Qt 6 QML test runner when available, before an
integration candidate is offered for certification.

## Static gate

Before any future Team 1 candidate is offered for host integration:

```bash
python3 scripts/team1_static_audit.py --base <authorized-certified-base>
```

The audit checks:

```text
required prepared APIs
no AppControl back-references
no provider identity leakage
one prepared verified RLIMIT mutation authority
confirmation cancel/relock semantics
verified per-PID resource result handling
SYSTEM controller compatibility
presence of the Team 1 behavioral contract suite
changed-file scope, including Team 1 tests
no widgets/AppControlW.qml touch on parallel branch
```

## Required future integration sequence

When T3 explicitly assigns Team 1 a serialized host slot:

```text
1. record exact certified base SHA
2. create/re-anchor integration branch from that exact SHA
3. replay/copy only the prepared Team 1 organs needed for the incision
4. instantiate shared lifetimes
5. wire compatibility adapters first
6. transplant one donor family at a time
7. run static audit
8. submit candidate packet to T0
9. T0 dispatches runtime validation
10. T3 alone certifies and advances canonical
```

Do not merge the long-running parallel branch directly into canonical without
reconciliation against the exact certified patient.

## Candidate packet skeleton

```text
READY FOR CERTIFICATION REQUEST

TEAM
T1 — Process/System

BRANCH
<integration branch>

CANDIDATE SHA
<sha>

CERTIFIED BASE SHA
<exact T3-certified base>

AUTHORIZED INCISION
<what was wired/removed>

FILES TOUCHED
<exact list>

STATIC AUDIT
PASS / FAIL

KNOWN PRESERVED LESIONS
RSS critical metric uses mem
resource freeze optimism has no expiry

FAVORITES/HUNTER CONTRACT
preserved / details

DONOR REMOVAL
<exact removed functions/blocks>

HOST NAVIGATION/DETAIL/RESULT
unchanged unless specifically authorized
```
