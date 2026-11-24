# CPU++ DOC 3 // System-wide workload inventory M3b.1

**Patient:** The-Post-Apollo-Project. **Room:** CPU++ diagnostics and optimization.
**Authority:** diagnostic source-only; Nurse 2 review pending. No live registration,
service-disable permission, production deployment or performance claim.

## Operator hypothesis and measured evidence

The operator proposed cumulative background processing across widgets,
shared stores, telemetry, database I/O, graphics and adjacent processes,
rather than AppControl alone. SwayPX, DevEXP and Kitty are separate
attribution candidates, not proven causes. The prior three 120-second
observer trials had zero Quickshell SwapPss throughout; peak PSS 8.65,
7.98, 8.81 GiB; final 5.34, 5.52, 5.56 GiB. All three reclaimed several
GiB, with non-identical interactions, different PIDs and unrecorded
deployed hashes. No causal or comparative performance acceptance.
PR #2459 shared process lookup and #2462 conditional COMBI copying
merged; neither is proven to reduce whole-process resource cost.

## Source inspection at checkpoint

Main observed e29d961bbe3d52d13a84572b85f04bf1763b5ca5;
repository tree contained 825 QML files, 263 in services/. These are source
file counts, not instantiated objects. File reads from main are source
observations, not a live desktop capture.

| Path | Observed marker / relationship | Next attribution |
|---|---|---|
| shell.qml | Persistent Weather and Space services; shared SystemTelemetry used by AppControl, CPU++, Hub and notification producers | Count actual collectors, subscribers and work |
| modules/Mediaplayer.qml | 67 ms coalesced visualization timer, 2 s MPD poll, CAVA process | Separate visual rendering and transport |
| modules/Network.qml | 500 ms recurring timer unless diagnostic pause flag | Measure subprocess count and result callbacks |
| services/weather/WeatherService.qml | 900000 ms recurring refresh | Separate fetch, cache and projection |
| services/weather/SpaceService.qml | 300000 ms recurring refresh | Same |
| services/notifications/NotificationsService.qml | Four FileView declarations, debounced writes and active-notification/policy timers | Measure event and persistence rates without private payload |
| modules/Trash.qml | 15000 ms menu-open refresh; other event/operation timers | Do not treat all declared processes as continuously active |
| services/hub/ApolloHubLiveBridge.qml | 5000 ms and 60000 ms timers conditional on attached sources | Measure projection freshness work |
| shell.qml ApolloHubW | Existing weather, media, network, hardware sources shared; processSnapshot derives bounded display data from AppControl taskRows | Audit projection invalidation, not duplicate collection assumption |
| Finance, Company, Tasks, Forest, Social, Git, Hospital | Widget/service trees need individual lifetime, storage, and subscription review | No idle cost inferred from declaration counts |

Historical constraints: Git/Hospital unmap/remap crashed; preserve current
mapping and input masks. Preserve CAVA coalescing and hidden notification
history deferral. No cache drops, forced GC, hard limits, process kills,
or broad service shutdown. Do not change owners' storage formats or
security/notification/alarm behavior.

## Inventory tool

Run after reviewed source is present:
```sh
python3 -B scripts/cpuplus_qml_workload_inventory.py
```
Add --detail for every candidate file and line. The scanner reads tracked
QML files from the working checkout, not GitHub or live process memory.
It reports source markers for timers, processes, file-backed views,
connections, loaders, repeaters, images, animations and selected property
bindings. No raw source expressions, command arguments or runtime payloads
are emitted. Missing/unreadable or symlink files are reported and return
nonzero. CI generates a detailed source inventory artifact.

This is a lexical index, not an AST or runtime instrument. Comments and
quoted strings are masked; JS regex/template edge cases and inline
declarations can be missed. A property marker is not attributed to a
particular object, and a declared timer may never run. Other languages,
OS services, GPU memory, database engines and dynamically created QML
instances need separate observation. Source file counts cannot establish
memory usage or actual database traffic.

## Next gates

A: source candidate inventory and ownership mapping.
B: low-frequency runtime CPU/PSS/I/O and per-service activity attribution;
reuse existing observers first. Avoid high-frequency in-shell instrumentation.
C: verify duplicate storage/read/write/projection work before consolidation.
D: quantify monitor cost and rendering cost separately.
E: measure adjacent processes independently, coordinate SwayPX and DevEXP
owners. Protected, essential service behavior remains unchanged.
