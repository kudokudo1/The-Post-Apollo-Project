# ApolloHub // B1 live Weather bridge

**Status:** W1 Weather wiring implemented on `main`; operator reported a live desktop PASS.
**Ownership:** Backend/live services. UI/editor and `shell.qml` remain with their respective owners.

## Existing source, no duplicate work

`shell.qml` already constructs a single `WeatherService { id: weatherService }` and passes it to Weather Station and weather notifications. `ApolloHubLiveBridge` is a nonvisual, read-only `Scope`: it accepts that exact live object through `weatherSource`. It does **not** fetch, refresh, change weather settings, or instantiate a second service.

The backend uses `WeatherDockPolicy.fresh()` (one-hour limit, five-minute future tolerance) and `WeatherDockPolicy.formatTemperature()`. It has a 60-second *clock-only* timer while attached to a source, so stale timestamps expire even when the source stops emitting changes. This is not network polling.

## Consumer contract

`import qs.services.hub` exposes `ApolloHubLiveBridge 1.0`.

- Input: `weatherSource` (existing `WeatherService`, nullable).
- Output: `weatherSnapshot` (a reactive read-only object).
- `state`: `disconnected`, `unavailable`, `loading`, `ready`, `stale`, or `error`.
- `connected`, `loading`, `fresh`, `error`, `updatedMs`, `ageMinutes`.
- `temperatureF` and `temperatureC` (preformatted `72°F` / `22°C` or `--°F` / `--°C`).
- `feelsLikeF`, `feelsLikeC`, `condition`, `humidity`, `windMph`, `windDirection`, `uvIndex`.
- Independent `airQuality` object: `state`, `fresh`, `error`, `updatedMs`, `index`, `label`.

When source data is missing, stale, or in error, temperature uses the unknown marker; UV and AQI use `-1`; condition/air-quality labels use `UNKNOWN`. Never infer a healthy reading from unavailable data.

## W1 Weather integration (implemented on `main`)

`shell.qml` now instantiates **one** bridge beside its existing weather service:

```qml
ApolloHubLiveBridge {
    id: apolloHubLive
    weatherSource: weatherService
}
```

`ApolloHubW.qml` now receives `liveBridge: apolloHubLive` from `shell.qml`, and the Weather tile consumes the reactive `liveBridge.weatherSnapshot` binding. The backend still owns no polling or write actions.

## Verification and limits

Run `python3 tests/hub/test_apollo_hub_live_bridge.py` for source contracts. GitHub workflow `apollo-hub-live-bridge.yml` checks it on relevant updates.

**Source wiring verification:** `tests/hub/test_apollo_hub_shell_weather_wiring.py` runs in `apollo-hub-live-bridge.yml` alongside existing Weather and CPU++ tests. **Not yet verified on Fedora/Quickshell:** module loading, reactive transitions for fresh/stale/error/air-quality, and rendered mini-card behavior. No local files or running service processes were touched.

## B2 // CPU++ shared system telemetry (read-only)

**Status:** Backend implemented and source-verified; B2 shared-shell telemetry wiring now installed on `main`. CPU mini-tile UI and live desktop acceptance remain pending.

`ApolloHubLiveBridge` now accepts **`systemSource`**, which must be the existing `SystemTelemetry { id: sharedSystemTelemetry }` object from `shell.qml`. Never construct a second `SystemTelemetry` and never copy or expose its actuator metadata to the Hub.

The new **`systemSnapshot`** is an automatically updated plain object with:

- `state`: `disconnected`, `loading`, `error`, `unobserved`, `stale`, `unavailable`, or `ready`.
- `connected`, `loading`, `fresh`, `error`, `observedAtMs`, `ageMinutes`.
- `cpuPercent`, `cpuMetric`, `memoryPercent`, `memoryMetric`.
- `swapPercent`, `swapMetric`, `rootFilesystemPercent`, `rootFilesystemMetric`.

Percentages are numeric, rounded to one decimal, **0–100** when known, or **-1** when unknown. Metrics are strings and become empty when no fresh observation is available. CPU and RAM rows **with valid numeric percentages** are mandatory for `ready`; swap and root filesystem may be absent. An invalid CPU or RAM utilization sets `state: unavailable` and masks numeric outputs instead of presenting a false `ready`. No process IDs, commands, device targets, or mutation capabilities are exposed.

The bridge observes the existing `SystemTelemetry.refreshed` signal and timestamps successful **completed** samples. It does not guess the age of rows that existed before it was attached, so `unobserved` is normal until a new sample completes. A new sample in progress invalidates the previous timestamp. Results expire after **five minutes** without another completed sample. The existing one-minute bridge timer only checks the clock; it does not start device monitoring. `SystemTelemetry` currently samples on demand, including when CPU++ opens its SYSTEM/THERMAL modes.

### Shared-shell integration (implemented) / UI integration (pending)

The existing shared shell now includes this source binding in its one `ApolloHubLiveBridge` instance:

```qml
ApolloHubLiveBridge {
    id: apolloHubLive
    weatherSource: weatherService
    systemSource: sharedSystemTelemetry
}
```

The UI owner should bind the CPU tile's data to `hub.liveBridge.systemSnapshot` (the window already receives `liveBridge` from the shell) and render `disconnected`, `loading`, `error`, `unobserved`, `unavailable`, `stale`, and `ready` distinctly. Display `--` for any `-1` percentage, including optional swap and filesystem. Read through `systemSnapshot` rather than directly accessing `SystemTelemetry.systemRows`; do not instantiate a new collector.

**Refresh behavior installed:** the shell requests exactly one on-demand `sharedSystemTelemetry.refresh()` on opening the Hub with a visible CPU tile or switching to a layout containing one. `SystemTelemetry` itself ignores overlapping requests. There is no Hub polling timer or new subprocess. The bridge updates `observationNowMs` and `systemObservedAtMs` together on a successful completed refresh, avoiding a falsely stale snapshot between one-minute clock ticks. Without another refresh, results expire after five minutes, as designed.

### Verification

`tests/hub/test_apollo_hub_system_bridge.py` checks the provider contract and absence of new collectors; `tests/hub/test_apollo_hub_system_policy.cjs` runs actual policy behavior cases, including stale timestamps and invalid readings. Both run alongside the Weather contract test in the existing `apollo-hub-live-bridge.yml` CI workflow.

**Not yet verified on the user's Quickshell desktop:** QML `Connections` observation events, synchronized update of the Hub UI, user-visible status changes, and shared-shell focus behavior. No host-machine files or running processes were changed by this batch.

## B3 // Passive Network snapshot (read-only)

**Status:** Backend source implemented. UI integration and on-device runtime certification pending.

`ApolloHubLiveBridge.networkSnapshot` uses the existing in-process `Quickshell.Networking` singleton, already imported by `modules/Network.qml`. No `nmcli`, `iw`, `ethtool`, `Process`, scan loop, network request, connection manipulation, or separate network service is created. The snapshot updates through QML bindings over the shared networking objects.

The pure normalization policy is `services/hub/ApolloHubNetworkPolicy.js`.

### UI consumer contract

- `state`: `unavailable` (no device information), `disconnected` (devices present but no connected local link), or `connected`.
- `connected`: true if any supported local link is connected.
- `transport`: `ethernet`, `wifi`, or `none` (Ethernet takes display priority if both connected).
- `internetState`: **always `unverified`**. Local association is not evidence of working DNS, gateway, or internet access.
- `wifi.present`, `wifi.connected`, `wifi.interfaceName`, `wifi.networkName`, `wifi.signalPercent` (integer 0–100 from a valid 0.0–1.0 strength or `-1` unknown).
- `ethernet.present`, `ethernet.connected`, `ethernet.interfaceName`.
- `linkSpeedMbps`: positive integer for the current Wi-Fi link bitrate, or **-1 (unknown)**. The bridge reads the existing dock's `iw` output through a read-only property and never duplicates that probe. For Ethernet, speed remains unknown.
- `linkSpeedApproximate`: true only when a valid Wi-Fi link bitrate is available; this radio receive link-rate estimate is **not measured Internet speed**.

No passwords, keys, private IP/MAC, activation methods, NetworkManager objects, or mutable device handles leave the snapshot.

### UI wiring

The current `shell.qml` creates one `ApolloHubLiveBridge { id: apolloHubLive }` and passes it to `ApolloHubW { liveBridge: apolloHubLive }`. The B3 speed follow-up has now wired `networkDockSource: sharedNetworkDock` into the existing bridge and given the existing dock the ID `sharedNetworkDock`. It adds neither a second Network dock nor another speed collector.

The UI owner already binds its Network tile to `hub.liveBridge.networkSnapshot`. Render `unavailable`, `disconnected`, and connected Wi-Fi/Ethernet separately; unknown signal `-1` must never display as zero signal; `internetState: "unverified"` must not look like a proven all-clear. **Presentation follow-up for UI owner:** the existing `networkSpeedText` formats positive numbers as `229 Mbps`. Change that label to `~ 229 Mb/s` for a known positive Wi-Fi link speed; retain `--` for unknown, disconnected, and Ethernet links. The bridge supplies `linkSpeedMbps` and `linkSpeedApproximate` for this, without changing UI-owned files.

### Compatibility / acceptance

The repo's existing dock already imports `Quickshell.Networking`, but the official published Quickshell **v0.2.1 module list** does not enumerate it (https://quickshell.org/docs/v0.2.1/types/); newer documentation specifies `WifiNetwork.signalStrength` (https://quickshell.org/docs/v0.3.2/types/Quickshell.Networking/WifiNetwork/). The user's runtime may use a newer/custom build. **Check on-device that the existing dock and the new bridge resolve the module and signal property before declaring live pass.** Signal strength remains unknown if the API doesn't provide a valid number.

CI workflow `apollo-hub-live-bridge.yml` runs:
- `python3 tests/hub/test_apollo_hub_network_bridge.py` for passive integration contracts.
- `node tests/hub/test_apollo_hub_network_policy.cjs` to execute production policy against wired, Wi-Fi, disconnected, malformed, and privacy cases.

No host restart, local file change, production activation, or live Hospital attachment is part of B3.

## B4 // Media: MPD session + explicitly selected MPRIS player (read-only)

**Status:** Source implementation and isolated CI tests passed. No shell or UI integration yet; desktop runtime verification pending.

`ApolloHubLiveBridge.mediaSnapshot` has **two distinct objects**:
- `mediaSnapshot.mpd`: live **observations from the existing `HeadlessMediaController` instance**, when an owner injects `mediaControllerSource`. This is controller/session state, not MPRIS and not proof of audible output.
- `mediaSnapshot.mpris`: passive observations from the in-process `Quickshell.Services.Mpris` singleton for one explicitly selected player. The bridge has `selectedMprisBusName` input and never chooses a player by guessing. `playerctld` mirrors are ignored, as in the existing `MprisPlaybackAdapter`.

The pure, read-only projection policy is `services/hub/ApolloHubMediaPolicy.js`. No new MPD, controller, MPRIS adapter, process, CLI request, polling loop, audio routing, or playback/volume action is introduced by this batch.

### MPD consumer properties

`mediaSnapshot.mpd` exposes:
- `state`: `disconnected`, `unobserved`, `error`, `stale`, `unavailable`, `unloaded`, `playing`, `paused`, or `stopped`.
- `source: "mpd"`, `connected`, `fresh`, `error`, `ageSeconds`.
- `title`, `artist`: current **observed session track**, blank when unobserved/stale/error.
- `lastKnownLoadedTitle`: the cassette's **last observed loaded item**, retained on stale snapshots but never represented as live playback.
- `loaded`, `ownedByController`, `audibleOutputVerified: false`.

A successful `HeadlessMediaController.snapshot` response advances freshness only when `pendingAction === "snapshot"` and `errorText` is empty. Search, inspection, and selection must not renew an old playback observation. Observed MPD state expires after **15 seconds** with no new successful snapshot; a five-second *clock-only timer* enforces expiry while attached. Loaded media and active playing media are kept separate. Neither `selection` nor `browse` are displayed as loaded or playing.

**B4 playback observation integration (merged PR #443):** The Hi-Fi deck still polls its HeadlessMediaController only while open in MPD mode. The shared shell now also injects `mpdDockSource: sharedMediaDock` to reuse the **existing** Media dock's already-running `mpc` observation (2-second cadence). The Hub policy prioritizes a fresh dock MPD playback state and combined artist-title label for continuous closed-deck updates, while retaining HeadlessMediaController's independently observed last-loaded cassette, ownership and freshness. A 15-second expiry applies to both independent sources; neither source proves audible sound. A stopped/offline dock cannot masquerade as playing. No new MPD process or poller is created. This behavior is source/CI tested, **not yet runtime verified**.

### B4 MPD flicker correction (October 22, 2026)

The Media dock's MPD subprocess runs every 2 seconds; the Hub's aging clock
originally ticked only every 5 seconds. If a new observation arrived between
clock ticks, its timestamp could be newer than the Hub clock. The media policy
correctly rejects future timestamps, so the Hub briefly misreported playback
as `STALE` or `UNAVAILABLE`.

The dock now validates `mpc status` output before accepting it, ignores
empty/unrecognized responses instead of treating them as a new `offline`
reading, then publishes one atomic `hubMpdObservation` object containing
state, title and timestamp. `ApolloHubLiveBridge` advances its freshness
clock when the atomic observation changes. This **does not** add a poller,
extend the 15-second stale threshold, modify MPRIS, or give the Hub transport
authority. Genuine failure to obtain valid MPD output still ages to `stale`.
The dock output parser is exercised against successful and failed real-format
samples in Node CI. Live SwayFX/Quickshell acceptance remains open.

### MPRIS consumer properties

`mediaSnapshot.mpris` exposes:
- `state`: `unavailable`, `selection-required`, `player-missing`, `unknown`, `playing`, `paused`, or `stopped`.
- `source: "mpris"`, `selected`, `playerCount`, `playerName`, `title`, `artist`, `album`, `audibleOutputVerified: false`.

A browser appearing in the MPRIS list is **not** permission to take it over. Even one discovered player stays `selection-required` until the existing Hi-Fi MPRIS selector intentionally supplies its `selectedBusName`. No controls or mutable references escape into the Hub snapshot.

### Owner-mediated integration (proposed in draft PR; runtime unverified)

The Media Deck creates **one** `HeadlessMediaController { id: headless }` and **one** `MprisPlaybackAdapter { id: mediaAdapter }` inside `widgets/MediaDeckW.qml`. On the B4 integration branch, these existing instances are exposed through read-only Media Deck/Dock properties and passed to the Hub bridge by the existing shell. **Never construct another instance to fill the Hub tile.**

The Media/UI owner should expose read-only references (or snapshots) via `MediaDeckW` → `Mediaplayer.qml` to the shared shell, without changing playback controls. Then the shell owner can add to the **already existing** `ApolloHubLiveBridge`:

```qml
mediaControllerSource: sharedMediaDock.hubMediaController
selectedMprisBusName: sharedMediaDock.hubSelectedMprisBusName
mpdDockSource: sharedMediaDock
```

**Draft integration:** the owner-facing properties `hubMediaController` and `hubSelectedMprisBusName` are now proposed in a dedicated B4 integration branch, forwarded through `MediaDeckW.qml` → `Mediaplayer.qml`. The shared-shell binding is in the same draft PR for owner coordination, **not yet merged or desktop accepted**. The Hub Media tile already consumes `mediaSnapshot`; no second tile or adapter is required. The shell owner should check concurrent edits and QML lifetime/binding behavior before merge.

### Tests and acceptance

- `python3 tests/hub/test_apollo_hub_media_bridge.py`: source seam, existing controllers, no duplicate polling/action commands.
- `node tests/hub/test_apollo_hub_media_policy.cjs`: production policy tests for unloaded/paused/playing/stale/error, ownership loss, loaded vs playing, missing/ambiguous MPRIS selection and privacy.
- Both run in `.github/workflows/apollo-hub-live-bridge.yml` with B1/B2/B3 regressions.

**Desktop runtime acceptance remains open** for MPD signal ordering, MPRIS player addition/removal and property updates, and live tile behavior. Do not claim audible output from MPRIS or a successful controller command.

## B5 // Linux system uptime (read-only)

**Status:** Source implemented on `main`; CI and on-device FileView acceptance tracked separately. Hub Uptime tile presentation is UI-owned and not part of this backend batch.

The source is `services/hub/ApolloHubUptimeSource.qml`, instantiated **once** inside the already-mounted `ApolloHubLiveBridge`. It uses one Quickshell `FileView` to read the Linux kernel's `/proc/uptime` and reloads that tiny procfs file every 60 seconds. There is **no shell command, subprocess, extra SystemTelemetry monitor, disk write, external network request, or actuator**. The source is intentionally separate from the central bridge so existing no-file-access safety guards still apply to Weather/CPU++/Network/Media code.

This reports **OS boot uptime**, not time since Quickshell, the Hub, the user session, or an application started. The second field of `/proc/uptime` (aggregate idle time) is parsed only for structural validity and is not exposed.

### Consumer contract

Existing UI already receives `liveBridge`. The Uptime tile can bind to:

```qml
uptimeSnapshot: hub.liveBridge ? hub.liveBridge.uptimeSnapshot : null
```

`uptimeSnapshot` fields:
- `state`: `unobserved` (no completed read), `unavailable` (invalid procfs output), `error` (FileView load failure), `stale` (last reading over 150 seconds old), or `ready`.
- `ready`, `approximate`, `source: "linux-procfs"`, `observedAtMs`, `ageSeconds`.
- `uptimeSeconds` (whole-number estimate), `days`, `hours`, `minutes`, and `label` (e.g., `1D 02H 03M`). Unknown numeric values are **-1**; unknown label is `--`.

The source uses the completion timestamp for each valid file read and updates its derived time from the clock. It does **not** invent `0` uptime from an absent or malformed source. The data becomes stale if the file stops refreshing; a failed load produces `error`, not a preserved fictional live reading. Each read refreshes the actual kernel uptime; the exposed value is approximate between reads.

### Owner boundaries and acceptance

B5 creates no new shell instance, UI controls, process or settings. The existing Quickshell import module (`services/hub/qmldir`) registers the single local source component. The UI worker should create the mini Uptime rendering using `uptimeSnapshot`, mask `-1` values, and show loading/error/stale explicitly rather than displaying zeros. Do not duplicate the procfs reader inside the tile.

Tests: `tests/hub/test_apollo_hub_uptime_bridge.py` guards the read-only source and one bridge instance; `tests/hub/test_apollo_hub_uptime_policy.cjs` executes the real normalization policy against valid/malformed values, boundary ages, and error cases. Both run in `.github/workflows/apollo-hub-live-bridge.yml` with B1–B4 regressions.

**Live acceptance pending:** Verify Quickshell `FileView` can read/reload procfs on the user's Fedora host, the displayed number increases correctly, and it does not reset on closing/reopening the Hub. No local files or running Quickshell processes were changed by source implementation.

## B6 // Apps: installed application catalog (read-only)

**Status:** B6 backend source implemented on `main`; Apps mini-widget UI and on-device Quickshell binding acceptance pending.

The Hub bridge now exposes `appsSnapshot`. It observes **Quickshell's built-in `DesktopEntries.applications.values`**, a native index of visible desktop applications. This reuses the existing Quickshell process and its own live desktop-entry updates, without manually searching `.desktop` files, starting a command, or instantiating an AppControl service. The official Quickshell v0.2.1 API describes this singleton under `import Quickshell` (https://quickshell.org/docs/v0.2.1/types/Quickshell/DesktopEntries/).

The projection is pure JS in `services/hub/ApolloHubAppsPolicy.js`. It only exposes **display metadata**, not desktop-entry QML objects, argv, raw Exec commands, environment, working directories, or launch methods.

### Consumer contract

Existing UI receives `liveBridge` and can bind the Apps tile to:

```qml
appsSnapshot: hub.liveBridge ? hub.liveBridge.appsSnapshot : null
```

`appsSnapshot` fields:
- `state`: `unavailable` (native index not supplied), `empty` (valid empty list), `ready` (visible applications indexed).
- `source: "desktop-entries"`, `query` (normalized, bounded to 80 characters).
- `installedCount`: number of valid distinct visible application IDs.
- `matchCount`: count matching the query across case-insensitive name, generic name, and exact app ID text.
- `shownCount`: count included in the bounded result array.
- `truncated`: true when more than the first **24** alphabetical matching results exist.
- `items`: up to 24 shallow plain objects with `id`, `name`, `genericName`, `icon` only.

Duplicate display names with different application IDs remain separate; duplicate IDs collapse to one. Absent names/IDs, invalid items, and `noDisplay` entries are excluded. An empty search match is not misreported as a broken index; it remains `state: ready` with `matchCount: 0`.

`ApolloHubLiveBridge.appsQuery` defaults to `""` (the alphabetical first page); a future UI search input may set this property without launching an application or creating another catalog source. **No favorites/recent usage or installed-app recency ranking is inferred** because the native index does not provide it.

### Launch actions are a separate decision

This backend is **observation only**. It does not call `DesktopEntry.execute()`, `DesktopEntries.byId()`, `Quickshell.execDetached()`, or process creation. The eventual UI worker must coordinate explicit click-to-launch behavior with the appropriate launcher owner; app catalog discovery itself is not permission to start anything. There is no automatic execution on opening the Hub, searching, or selecting a card.

No shared `shell.qml`, `Applauncher.qml`, AppControl, CPU++, other Hub mini-tile, or local-machine file was changed in this batch.

### Tests and acceptance

- `tests/hub/test_apollo_hub_apps_bridge.py`: native shared index connection, one Hub bridge, no launch path, CI registration.
- `tests/hub/test_apollo_hub_apps_policy.cjs`: actual catalog policy exercised with duplicates, hidden/malformed entries, alphabetical/search filtering, 24-item limits, and malicious command metadata.
- Both run alongside B1–B5 in `.github/workflows/apollo-hub-live-bridge.yml`.

**Desktop acceptance pending:** Verify Quickshell v0.2.1 exposes live DesktopEntries values on the user's installation, that the catalog updates when desktop entries appear/disappear, and that search does not launch any application. The UI owner can display the bounded list and later request a separately authorized launch-action integration.

