# ApolloHub // B1 live Weather bridge

**Status:** W1 shared-shell Weather connection implemented on `main`; live desktop acceptance pending.
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
