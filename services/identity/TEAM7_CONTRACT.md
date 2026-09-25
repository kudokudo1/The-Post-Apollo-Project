# Team 7 — Desktop Identity Evidence Contract

Branch origin: `943d27310f68d9941e7b19631fbd56aa9bd633e8`

Current certified patient at the time of this contract:
`6c74628baeaf7cf2f37808f9e57293aaad7e1788`

This branch is intentionally **not rebased merely because canonical advanced**.
Team 7 remains on the parallel floor. No `AppControlW.qml` host wiring is part
of this work.

## What this contract freezes

This pass freezes only the common **observation/evidence envelope** used to carry
identity facts between providers.

It does **not** freeze:

- the final canonical application key
- the final `ApplicationEntity` schema
- DesktopEntry ↔ running-application cardinality
- resolver scoring
- alias policy
- first-match behavior
- host integration

The purpose is to let providers exchange raw evidence without forcing Team 5,
Team 6, Team 8, Team 1, or the future Sway service to invent their own semantic
application identity.

## Four identity classes remain distinct

```text
persistent semantic identity
        !=
session application identity
        !=
ephemeral provider/object identity
        !=
matching evidence / aliases
```

`DesktopIdentityEvidence.qml` therefore emits observations, aliases,
relationships, and resolution envelopes. It does not construct a canonical
application object.

## Observation envelope

Every Team 7 observation uses:

```text
provider
providerKey
lifetimeClass
generation
raw
aliases[]
relationships[]
```

### provider

The source of the observation, for example:

```text
DESKTOP_ENTRY
SWAY
PROCFS
KITTY
DEVTOOLS
LIBATSPI
AT-SPI-CACHE
PIPEWIRE
```

Provider names identify evidence origin, not semantic ownership.

### providerKey

A provider-local coordinate.

Examples:

```text
desktop-entry:org.mozilla.firefox.desktop
sway-con:123456
pid:4412
kitty:7
devtools:9222:ABCDEF
sink-input:63
```

A provider key may be stable inside its own domain and still be unsuitable as a
canonical application key.

### lifetimeClass

Current vocabulary:

```text
persistent
session
ephemeral
```

This describes the lifetime of the observation coordinate, not the lifetime of
the application the observation may describe.

### raw

Original provider facts. Raw values are preserved even when aliases are also
derived from them.

A normalized token must never replace its raw source field.

### aliases[]

Each alias carries:

```text
kind
value
normalized
provider
```

Normalization currently preserves the donor's lowercase/alphanumeric token rule
so old matching behavior can be represented and tested. A normalized alias is
matching evidence only.

### relationships[]

Each relationship carries:

```text
kind
targetProvider
targetKey
strength
sourceField
```

Current strength vocabulary is descriptive, not probabilistic:

```text
exact
heuristic
```

"exact" means the provider supplied an exact relationship fact such as a PID
field. It does not mean that PID alone defines semantic application identity.

## Current source adapters

### DesktopEntry

`desktopEntryObservation(entry)` preserves:

- desktop entry id
- name
- generic name
- comment
- startup class
- command tokens

Derived aliases currently include:

- desktop entry id
- startup class
- display name
- command basename
- reverse-DNS/id leaf

The provider key is the DesktopEntry id when one exists.

A missing DesktopEntry id does **not** cause Team 7 to manufacture a name-based
semantic key.

### Sway window

`swayWindowObservation(windowInfo)` preserves the current donor window fields:

- Sway con id
- title/name
- app_id
- class
- instance
- PID
- workspace/output
- floating/tabbed state
- tab group
- fullscreen
- rect

The Sway con id is an ephemeral window coordinate.

A valid Sway PID produces an `EXACT_PID` relationship to a PROCFS observation.
That relationship is evidence about process attachment, not an application
identity declaration.

### Process

`processObservation(entry)` preserves:

- PID
- PPID
- comm/name
- executable
- arguments/cmdline
- user

PID is ephemeral. A PPID relationship is process-tree evidence, not proof that
the parent and child are one semantic desktop application.

### Surface / tab

`surfaceObservation(evidence)` consumes Team 5's existing
`identityEvidence(entry)` shape without changing Team 5 ownership.

It preserves:

- provider
- providerKey
- appName/windowName
- path / role
- busName/objectPath
- processPids
- debugPort/targetId/webSocketDebuggerUrl
- kittyAddress/kittyTabId

`processPids` become explicit provider→PROCFS relationships. Provider-local
surface IDs remain surface coordinates.

## Existing sibling contracts checked

### Team 5

Current branch:
`feature/team5-tab-surface-provider`

Team 5 already exposes:

```text
providerRecordKey(entry)
identityEvidence(entry)
```

and explicitly states that its records are discovery evidence, not canonical
application identity.

No contract collision found.

### Team 6

Current branch:
`team6/application-audio-service`

Team 6 already exposes a compatible observation shape:

```text
provider = PIPEWIRE
providerKey = sink-input:<index>
lifetimeClass = ephemeral
generation
raw
aliases[]
relationships[]
```

It also keeps descriptor match evidence separate from semantic identity.

Team 7 does not need to wrap or replace Team 6's stream observation merely to
make it look Team-7-owned. The useful contract is compatibility.

No contract collision found.

### Team 8

Current branch:
`team8/apps-core-prep`

Team 8 treats DesktopEntry IDs as local catalog coordinates and explicitly
declines canonical cross-provider identity ownership.

No contract collision found.

## SurfaceLaunch boundary — resolved by T3 Overhead

The launch-time surface instrumentation seam is now owned explicitly.

```text
T8 / RUN / future launch domains
    -> launch intent / base plan / launch mechanism
    -> apply supplied augmentation

T5-domain SurfaceLaunchRequirements / SurfaceLaunchCoordinator
    -> describe discoverability capabilities
    -> construct argv/env/bootstrap augmentation
    -> coordinate transient endpoint / lease / correlation metadata

launched process
    -> owns runtime socket/debug listener lifetime

T5 TabSurfaceProvider
    -> post-launch discovery / activation / diagnostics

T7
    -> semantic interpretation / relationship evidence / joins
```

SurfaceLaunch is explicit opt-in. The stable boundary is capability-oriented,
for example:

```text
KITTY_REMOTE
ACCESSIBILITY
DEVTOOLS
```

Exact API names are not frozen.

Team 7 may consume PID/socket/port/target/correlation output as evidence, but
must not decide whether those coordinates are injected into a launch and must
not promote ephemeral bootstrap coordinates into persistent semantic identity.

The following lifetimes remain distinct:

```text
launch transaction
instrumentation/application instance
surface provider
```

Specifically, `TabSurfaceProvider.active` must not define instrumentation
lifetime.


## Resolution contract

The first shared semantic resolver must return one of:

```text
resolved
ambiguous
unresolved
```

The minimal envelope is:

```text
status
candidates[]
evidence[]
reason
```

This is intentionally enough to forbid the current `appEntryForWindow()`
pattern from silently turning "first fuzzy match" into semantic truth.

A later resolver may add fields. It must not remove the ability to represent
ambiguity or lack of evidence.

## Evidence kinds expected later

The recon pass identified these useful relationship kinds:

```text
EXACT_PID
EXACT_DESKTOP_ID
EXACT_STARTUP_CLASS
EXACT_APP_ID
EXACT_PROVIDER_PARENT
EXACT_DEBUG_PORT_OWNER
EXACT_KITTY_PROCESS
EXACT_PIPEWIRE_APP_ID
ALIAS_EXACT
TOKEN_SUFFIX_HEURISTIC
DISPLAY_NAME_HEURISTIC
```

This list is a vocabulary target, not a scoring table. Runtime fixtures are still
required before Team 7 assigns resolver precedence.

## Required runtime fixture matrix before resolver freeze

At minimum:

- Brave native
- Firefox
- VS Code / Electron
- Kitty
- one Flatpak app
- one Toolbox-launched app
- one Bottles/Wine app
- shared-PID windows if reproducible
- browser with multiple tabs/processes
- app with no live audio stream
- app whose display name differs from executable/app_id

For each case collect:

```text
DesktopEntry
Sway window record
process tree
Team 5 surface evidence
Team 6 PipeWire observation
known launch form
known ambiguity
```

Until that matrix exists, Team 7 should not publish a universal resolver score or
a magic `canonicalId`.

## Cross-team handoff

### Team 5
Keep raw provider fields and `processPids`. Do not synthesize DesktopEntry or
application relationships that the provider did not observe.

### Team 6
Keep full PipeWire properties and separate match evidence. Team 7 will provide
semantic keys/matching descriptors later; Team 6 remains audio physiology owner.

### Team 8
Keep DesktopEntries as catalog input and launch authority. DesktopEntry id is a
strong semantic candidate but not automatically the entire cross-provider
identity graph.

### Team 1
Expose PID/PPID/process-scope observations without making process identity equal
desktop application identity.

### Sway provider / Team 3-R future service
Expose raw Sway app_id/class/instance/PID/con-id fields. Sway is authoritative
for its window observations, not for cross-provider application semantics.

## Host boundary

Current state:

```text
Team 7 service/evidence code   standalone
AppControlW rewiring           NONE
donor identity code removal    NONE
service lifetime integration   NONE
canonical resolver             NOT FROZEN
```

When Team 7 eventually receives a serialized host slot, it must re-anchor to the
exact certified HEAD named in that order and reread the then-current donor
anatomy before any transplant.
