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

**Status:** Backend implemented and CI-wired; not yet bound to the Hub UI or the shared shell.

`ApolloHubLiveBridge` now accepts **`systemSource`**, which must be the existing `SystemTelemetry { id: sharedSystemTelemetry }` object from `shell.qml`. Never construct a second `SystemTelemetry` and never copy or expose its actuator metadata to the Hub.

The new **`systemSnapshot`** is an automatically updated plain object with:

- `state`: `disconnected`, `loading`, `error`, `unobserved`, `stale`, `unavailable`, or `ready`.
- `connected`, `loading`, `fresh`, `error`, `observedAtMs`, `ageMinutes`.
- `cpuPercent`, `cpuMetric`, `memoryPercent`, `memoryMetric`.
- `swapPercent`, `swapMetric`, `rootFilesystemPercent`, `rootFilesystemMetric`.

Percentages are numeric, rounded to one decimal, **0–100** when known, or **-1** when unknown. Metrics are strings and become empty when no fresh observation is available. CPU and RAM rows are mandatory for `ready`; swap and root filesystem may be absent. No process IDs, commands, device targets, or mutation capabilities are exposed.

The bridge observes the existing `SystemTelemetry.refreshed` signal and timestamps successful **completed** samples. It does not guess the age of rows that existed before it was attached, so `unobserved` is normal until a new sample completes. A new sample in progress invalidates the previous timestamp. Results expire after **five minutes** without another completed sample. The existing one-minute bridge timer only checks the clock; it does not start device monitoring. `SystemTelemetry` currently samples on demand, including when CPU++ opens its SYSTEM/THERMAL modes.

### UI/shell-owner integration (not done here)

The shared-shell owner can extend the existing bridge installation:

```qml
ApolloHubLiveBridge {
    id: apolloHubLive
    weatherSource: weatherService
    systemSource: sharedSystemTelemetry
}
```

The UI owner can bind the CPU tile's data to `apolloHubLive.systemSnapshot` and render unknown/error/loading/stale states distinctly. Read through `systemSnapshot` rather than directly accessing `SystemTelemetry.systemRows`.

**Important activation dependency:** If the Hub should show a fresh CPU++ reading immediately when opened, the shell owner must decide when to request the existing shared monitor refresh. The bridge intentionally makes no hardware calls on its own. Coordinate that decision with the shared telemetry owner; do not secretly introduce another sampling loop.

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

**Existing lifecycle limitation:** The current Hi-Fi deck sets `HeadlessMediaController.polling` only while the deck is open in MPD mode. With the deck closed, MPD observations will expire and the Hub must show `stale`. To display truly live closed-deck MPD state, another owner must expose the **existing** Media dock's already-running `mpc` observation (2-second cadence) or arrange an authorized shared observation source. Do not start another observer here.

### MPRIS consumer properties

`mediaSnapshot.mpris` exposes:
- `state`: `unavailable`, `selection-required`, `player-missing`, `unknown`, `playing`, `paused`, or `stopped`.
- `source: "mpris"`, `selected`, `playerCount`, `playerName`, `title`, `artist`, `album`, `audibleOutputVerified: false`.

A browser appearing in the MPRIS list is **not** permission to take it over. Even one discovered player stays `selection-required` until the existing Hi-Fi MPRIS selector intentionally supplies its `selectedBusName`. No controls or mutable references escape into the Hub snapshot.

### Owner-mediated integration (proposed in draft PR; runtime unverified)

The Media Deck currently creates **one** `HeadlessMediaController { id: headless }` and **one** `MprisPlaybackAdapter { id: mediaAdapter }` inside `widgets/MediaDeckW.qml`. They are not exposed to `shell.qml` or the Hub, so **do not construct another instance just to fill the Hub tile**.

The Media/UI owner should expose read-only references (or snapshots) via `MediaDeckW` → `Mediaplayer.qml` to the shared shell, without changing playback controls. Then the shell owner can add to the **already existing** `ApolloHubLiveBridge`:

```qml
mediaControllerSource: sharedMediaDock.hubMediaController
selectedMprisBusName: sharedMediaDock.hubSelectedMprisBusName
```

**Draft integration:** the owner-facing properties `hubMediaController` and `hubSelectedMprisBusName` are now proposed in a dedicated B4 integration branch, forwarded through `MediaDeckW.qml` → `Mediaplayer.qml`. The shared-shell binding is in the same draft PR for owner coordination, **not yet merged or desktop accepted**. The Hub Media tile already consumes `mediaSnapshot`; no second tile or adapter is required. The shell owner should check concurrent edits and QML lifetime/binding behavior before merge.

### Tests and acceptance

- `python3 tests/hub/test_apollo_hub_media_bridge.py`: source seam, existing controllers, no duplicate polling/action commands.
- `node tests/hub/test_apollo_hub_media_policy.cjs`: production policy tests for unloaded/paused/playing/stale/error, ownership loss, loaded vs playing, missing/ambiguous MPRIS selection and privacy.
- Both run in `.github/workflows/apollo-hub-live-bridge.yml` with B1/B2/B3 regressions.

**Desktop runtime acceptance remains open** for MPD signal ordering, MPRIS player addition/removal and property updates, and live tile behavior. Do not claim audible output from MPRIS or a successful controller command.

