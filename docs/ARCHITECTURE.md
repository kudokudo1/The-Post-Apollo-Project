# Taskbars // Post-Apollo — Architecture Map

> Team 0 reconnaissance document.  
> This is an architecture / ownership graph, **not** GitHub's package Dependency Graph.
>
> Certified baseline for this map: `943d273` — fused AppControl + CPU++ patient.

## 1. Current hospital map

```mermaid
flowchart TD
    T0["Team 0<br/>Recon / Management"]
    T1["Team 1<br/>Process / Resource + SYSTEM"]
    T2["Team 2<br/>Favorites"]
    T3F["Team 3-F<br/>FILES → later RUN"]
    T3R["Team 3-R<br/>REMOTE → later Sway Windows"]
    T4["Team 4<br/>CPU++ Recipient / Validation"]
    T5["Team 5<br/>Tabs / Surface Discovery"]
    T6["Team 6<br/>Application Audio"]
    T7["Team 7<br/>Desktop Identity Authority"]
    T8["Team 8<br/>APPS Core"]
    T3M["T3 Manager / Integration Room"]

    T0 -->|recon findings| T3M

    T1 --> T3M
    T2 --> T3M
    T3F --> T3M
    T3R --> T3M
    T5 --> T3M
    T6 --> T3M
    T7 --> T3M
    T8 --> T3M

    T3M -->|certified releases| T4
```

## 2. Shared-service architecture

```mermaid
flowchart TB
    subgraph Shared["Shared / Provider Layer"]
        ID["Desktop Identity<br/>Team 7"]
        PROC["Process / Resource<br/>Team 1"]
        FAV["Favorites<br/>Team 2"]
        FILES["FileService<br/>Team 3-F"]
        RUN["RunService<br/>future Team 3-F"]
        SWAY["SwayWindowService<br/>future Team 3-R"]
        TABS["Tab / Surface Provider<br/>Team 5"]
        AUDIO["Application Audio<br/>Team 6"]
        APPS["APPS Core Provider<br/>Team 8"]
    end

    ID --> TABS
    ID --> AUDIO
    ID --> APPS
    ID --> PROC

    PROC --> APPS
    PROC --> TABS
    PROC --> RUN
    PROC --> SWAY

    FILES --> FAV
    RUN --> FAV
    APPS --> FAV
    SWAY --> FAV
    TABS --> FAV

    FILES --> APPCTRL["AppControl"]
    RUN --> APPCTRL
    SWAY --> APPCTRL
    TABS --> APPCTRL
    AUDIO --> APPCTRL
    APPS --> APPCTRL
    FAV --> APPCTRL
    PROC --> APPCTRL

    PROC --> CPU["CPU++"]
    FAV --> CPU
    AUDIO --> CPU
    ID --> CPU

    APPCTRL -. "host / presentation" .-> CPU
```

The target direction is:

```text
OLD
AppControl owns state/services/control
        ↓
other UI reaches into AppControl

NEW
shared service/provider layer
        ↓
AppControl and CPU++ are peer consumers
```

A file is not considered a liberated organ merely because it lives outside
`AppControlW.qml`. It should have explicit dependencies and no hidden
AppControl back-reference.

## 3. Semantic identity authority

```mermaid
flowchart LR
    DE["DesktopEntry"]
    APP["Application"]
    SW["Sway Window"]
    PID["PID / Process Scope"]
    TAB["Tab / Surface"]

    DE <--> APP
    APP <--> SW
    APP <--> PID
    APP <--> TAB

    APP --> Audio["Application Audio"]
    APP --> AppsCore["APPS Core"]
    SW --> SwaySvc["SwayWindowService"]
    PID --> Proc["Process / Resource"]
    TAB --> TabSvc["Tab / Surface Provider"]

    APP --> Fav["Favorites identity adapters"]
    SW --> Fav
    TAB --> Fav
```

**Team 7 is the semantic identity authority.**

Teams 5, 6 and 8 may use temporary/local record keys while developing, but they
should not invent competing canonical application identity systems.

Teams 1 and 2 consume identity adapters/contracts rather than defining the
desktop identity model themselves.

## 4. Process / resource physiology

```mermaid
flowchart TD
    H["Task / HUNTER"]
    A["APPS"]
    W["WINDOWS"]
    T["TABS"]
    R["RUN"]

    H --> Scope["Shared Process / Resource Layer"]
    A --> Scope
    W --> Scope
    T --> Scope
    R --> Scope

    Scope --> Ops["Signals / limits / freeze-thaw / safety / restart"]
```

Domain UIs may own **intent and scope discovery**.

Examples:

- APPS: "these PIDs belong to this application"
- WINDOW: "these PIDs belong to this Sway window"
- RUN: "these PIDs match this command"
- HUNTER: "operate on this ranked process set"

The shared Process / Resource layer should own reusable destructive/control
operations instead of each UI implementing its own backend.

## 5. WINDOWS is not one organ

```mermaid
flowchart TD
    WIN["WINDOWS menu"]
    SWAY["Native Sway Windows"]
    TABS["Cross-application Tabs"]
    PROC["Shared Process / Resource"]
    AUDIO["Shared Application Audio"]
    HOST["AppControl presentation / navigation"]

    WIN --> SWAY
    WIN --> TABS
    SWAY --> PROC
    TABS --> PROC
    SWAY --> AUDIO
    TABS --> AUDIO
    WIN --> HOST
```

Future WINDOWS work should be split around real ownership boundaries:

- `SwayWindowService` for native Sway discovery/actions.
- Tab / Surface Discovery for cross-application tabs.
- Team 1 for shared process/resource physiology.
- Team 6 for shared application audio.
- AppControl retains host presentation/navigation until a later host-shell wave.

Do **not** recreate a giant `WindowController.qml` that simply becomes another
AppControl.

## 6. RUN is comparatively coherent

```mermaid
flowchart TD
    RUN["RUN"]
    ID["Command identity"]
    PROV["Providers<br/>USER / TERMINAL / ALL"]
    EXEC["Execution<br/>NORMAL / KITTY / TOOLBOX"]
    HIST["History"]
    HOST["AppControl search / selectors / detail"]
    FAV["Favorites seam"]
    PROC["Process seam<br/>contextual SIGTERM"]

    RUN --> ID
    RUN --> PROV
    RUN --> EXEC
    RUN --> HIST

    RUN --> HOST
    ID --> FAV
    RUN --> PROC
```

Likely future boundary:

```text
RunService
├── command identity
├── session history
├── terminal-history provider
├── PATH command catalog
├── execution strategies
└── records/state
```

Cross-team seams:

- semantic/persistent provider identity → Team 2 adapter consumption
- contextual process mutation → Team 1 shared Process / Resource backend

## 7. Favorites is an aggregation layer

```mermaid
flowchart LR
    FILES["FILES"] --> F["Favorites"]
    RUN["RUN"] --> F
    APPS["APPS"] --> F
    WIN["Sway Windows"] --> F
    TABS["Tabs"] --> F
    SYS["SYSTEM / HUNTER compatibility"] --> F

    F --> COMBI["FAVORITES / COMBI"]
```

Important distinction:

```text
favoriteable
can produce a favorite key

≠

reconstructable
Favorites can rebuild a first-class provider record
```

Known product requirement: FILES should eventually reconstruct into
FAVORITES/COMBI. Its previous absence is unfinished behavior, not an intended
restriction.

The first persistence extraction must preserve existing JSON and
`favoriteKeys` semantics, including the current Favorites → HUNTER protection
contract.

## 8. Integration traffic law

```mermaid
flowchart TD
    B["Certified baseline"]
    P1["Parallel service/provider work"]
    P2["Parallel tests / adapters / recon"]
    G["T3 integration gate"]
    H["Serialized AppControl host wiring"]
    D["Donor + integration tests"]
    N["New certified HEAD"]

    B --> P1
    B --> P2
    P1 --> G
    P2 --> G
    G --> H
    H --> D
    D --> N
    N --> B
```

### Parallel-safe work

- new service files
- provider implementation
- tests
- adapters
- contracts/docs
- identity mapping
- reconnaissance
- dependency mapping

### Serialized through T3 Manager

- `AppControlW.qml` rewiring
- donor-block removal
- shared navigation changes
- generic result routing
- generic detail routing
- shared selector changes
- service-lifetime integration

Before a team enters serialized host tissue it should report:

```text
branch
base SHA
current HEAD
files changed
shared vessels discovered
AppControlW touched: YES/NO
tests
local pass
ready for integration
```

## 9. Team responsibilities

| Team | Current responsibility | Key boundary |
|---|---|---|
| Team 0 | Recon / management | No surgery |
| Team 1 | Process / Resource + SYSTEM | Build for HUNTER, APPS, WINDOWS, TABS, RUN |
| Team 2 | Favorites persistence/reconstruction | Preserve JSON + `favoriteKeys` compatibility first |
| Team 3-F | FILES | FileService; later likely RUN |
| Team 3-R | REMOTE | AppControl wiring after FILES; later likely Sway windows |
| Team 4 | CPU++ recipient / validation | Consume released organs; do not extract from AppControl |
| Team 5 | Tabs / Surface Discovery | Do not invent canonical app identity |
| Team 6 | Application Audio | Identity comes from Team 7 |
| Team 7 | Desktop Identity | Semantic identity authority |
| Team 8 | APPS Core | No mass APPS extraction until shared organs are removed |
| T3 Manager | Integration / certification | Own serialized host-integration queue |

## 10. Checkpoint model

Individual rooms checkpoint their own work:

```text
CHECKPOINT 0 — anatomy / ownership
CHECKPOINT 1 — cut plan
CHECKPOINT 2 — isolated service/provider exists
CHECKPOINT 3 — local liberation / ready for integration
```

T3 has a separate integration checkpoint before shared host changes enter the
certified patient.

Passes are distinct:

```text
LOCAL PASS
team branch works by itself

DONOR PASS
AppControl still behaves correctly

INTEGRATION PASS
work coexists with the other released organs and exposes a clean contract
```

## 11. How to use this document

This graph is maintained by Team 0 as reconnaissance evolves.

It should answer:

1. Who owns this capability?
2. Who consumes it?
3. Is it a shared organ or only a UI grouping?
4. Does it depend on semantic desktop identity?
5. Does it cross the Process / Resource layer?
6. Does it cross Favorites reconstruction?
7. Can the team work in parallel, or has it reached T3's serialized host gate?

When the certified patient changes, update the baseline marker and revalidate any
anatomical assumptions that came from an older snapshot.
