# ApolloHub // B1 live Weather bridge

**Status:** Implemented backend type, not yet mounted by the UI/shell.
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

## Suggested owner-mediated wiring (NOT done in B1)

The shared-shell owner may instantiate **one** bridge beside its current weather service:

```qml
ApolloHubLiveBridge {
    id: apolloHubLive
    weatherSource: weatherService
}
```

The UI owner may accept a `liveBridge` property in `ApolloHubW.qml`, then pass `liveBridge.weatherSnapshot` into the Weather tile. This must be a live binding, not an untracked one-time JS copy. Do not edit the shared shell or UI components without coordinating with their owners.

## Verification and limits

Run `python3 tests/hub/test_apollo_hub_live_bridge.py` for source contracts. GitHub workflow `apollo-hub-live-bridge.yml` checks it on relevant updates.

**Not yet verified on Fedora/Quickshell:** module loading, reactive transitions for fresh/stale/error/air-quality, live tile rendering, and shared-shell wiring. These remain runtime acceptance checks. No local files or running service processes were touched.
