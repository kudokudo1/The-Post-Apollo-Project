# Apollo Hub // Weather shared-source deferred work

**STATUS:** DEFERRED, owner-dependent (2026-10-24). This document is a checkpoint, not implementation permission.

## IMPLEMENTATION // Current truth

- [Merged PR #675](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/675) implemented H:2/H:3 WEATHER/GROUND/SKY/SPACE selection in `widgets/hub/ApolloHubWeatherExplore.qml`; H:1 keeps the old compact card.
- WEATHER observes existing temperature, feels-like, condition and wind via `ApolloHubLiveBridge.weatherSnapshot`.
- GROUND observes independently fresh AQI only; other Ground feeds are not connected to the Hub.
- SKY observes current UV, wind, humidity and wind direction only. Full Sky forecasts are not connected to the Hub.
- SPACE is a functional selector displaying **PROVIDER NOT CONNECTED**, not solar/aurora/geomagnetic/flaring readings.
- [Merged PR #680](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/680) fixed the separate TimeW B10 assertion. Historic red checks on #675 remain historic, not an active source-provider failure.

## WATCH OUT FOR // Missing owner-published data

1. GROUND: pollen, gases, seismic and other ground readings need separate trusted owner projections, timestamps, units and independently truthful ready/loading/stale/error/unavailable states.
2. SKY: owner-validated forecast/pressure/visibility/cloud/precipitation data need a read-only shared projection. Do not infer forecasts from current atmospheric values.
3. SPACE: NOAA solar wind, geomagnetic/Kp, aurora, flares, X-ray and authoritative SWPC alerts require distinct validated timestamps, states, units and proper warning semantics.
4. WeatherStation `StationGround.qml` and `StationSpace.qml` use view-scoped services. The Hub must **not** mount these views or start another collector per tile. Determine a single published owner-managed lifetime and passive snapshot interface before introducing new fields.
5. Runtime acceptance after source integration must check H:1/H:2/H:3, W:1/W:2, stale vs independently fresh AQI, missing feeds, long labels, offline operation, and frozen/lagging UI behavior.

## NEXT

Once the WeatherStation owner approves a source schema with lifecycle, freshness, error and units, add one bounded read-only projection at a time. No new WeatherService, solar/aurora/seismic timer or network request in the Hub. No Level 3 weather controls without separate operator authority.

## DECISIONS

The breadth upgrade is deferred, not canceled. Work can continue on unrelated Hub mini modules. GitHub merges are not evidence of live Quickshell visual or performance acceptance.
