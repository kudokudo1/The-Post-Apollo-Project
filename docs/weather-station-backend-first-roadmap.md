# Weather Station // Backend-First Roadmap & Worker Recovery

**STATE:** OPERATOR-DIRECTED PLAN / IMPLEMENTATION CHECKLIST. Recorded 2026-10-23. This document is a durable development reference, **not** a live Hospital Assignment, automatic merge authority, or permission to alter the operator's local machine.

**Patient (repository):** [The-Post-Apollo-Project](https://github.com/kudokudo1/The-Post-Apollo-Project)  
**Main branch evidence snapshot:** `9d9236746c32086864da1b6ae7d2c8e37864c2d2` (2026-10-23). Refresh branch, source, and PR state before future work.  
**Domain:** Weather Station W → future Observatory; neighboring shared owner: Hi-Fi / Media.  
**Operator priority:** **Connect the real data, backends, controls, and menu access FIRST. Rearrange, resize, and visually polish AFTER the operator can see what is available.**  
**Authority:** The operator has final authority. Follow [canonical Syntagma AGENTS.md](https://github.com/kudokudo1/Meta-Apollo-Logos-Syntagma/blob/main/AGENTS.md), [documentation placement](https://github.com/kudokudo1/Meta-Apollo-Logos-Syntagma/blob/main/OPERATE/POST-APOLLO-WORKING-GUIDE.md), and relevant Hospital rules.

## 1. Preserved decisions and design intentions

The following comes directly from the operator discussion and must survive chat/worker loss:

1. **Backend-first / no premature menu reorganization.** Build useful data and controls in the existing modes so their final information hierarchy can be decided by hands-on usage.
2. **MAP, NEWS and RADIO are future terminal/viewer workspaces.** Selecting an event, article or station should open a task-appropriate central viewer **inside** Weather Station rather than defaulting to an external website. Each can offer SELECT (browse), VIEW (content) and TERMINAL (direct command interaction). Expand and a bottom-right mini/docked state are desired options, not finalized geometry.
3. **Shared viewer, domain-specific rendering.** Prefer reuse of the existing Kitty/Sway Star Map hosting/geometry mechanism, but do not assume a Kitty terminal can render full interactive web maps or videos. A map/video may need a different visual renderer within the same host. Retain keyboard focus and window ownership safeguards.
4. **One shared radio backend.** Weather RADIO must be as capable as Hi-Fi and focused on news/talk/public/weather radio. Reuse the existing Hi-Fi/MPD/MPRIS/Radio Browser controller, station identity, relay, selection, LOAD and PLAY semantics; **do not create a duplicate radio engine, second MPD daemon, or independent playback owner.** Hi-Fi remains broad music/radio; Weather Station supplies the news-first discovery and presentation.
5. **News discovery/highlighting.** Surface NEWS, TALK, PUBLIC, WEATHER, LOCAL, ALL RADIO navigation, and visually distinguish likely news stations. Directory tags are heuristics, not authoritative station identity. News classification should be correctable.
6. **Stay in Weather Station first.** The later full Observatory should preserve the exact selected item, source/filter context, media playback and viewer state when expanded.
7. **No silent activation.** GitHub implementation does not mean the local Quickshell runtime, MPD user service, selected browser or live source has been validated. Never change local services, restart Quickshell, merge a PR or promote Hospital status without appropriate approval.

Proposals not yet decided: exact size (currently roughly 1000 × 700), number of submodes, whether central viewer opens automatically, panel docking/expand behavior, default news filters, additional providers and alert notification policy.

## 2. Current source inventory (verified 2026-10-23)

| Area | Repository implementation observed | Still missing / not runtime-certified |
| --- | --- | --- |
| Bar + Weather Station shell | `modules/Weather.qml`, `widgets/weather/WeatherStationW.qml` | Later operator-led layout, adaptive growth, final glance states |
| HOME | `StationHome.qml`: mixed weather, AQI and space cards, relevance ranking | Persistent universal favorites and full multi-domain relevance |
| GROUND | `StationGround.qml`: air quality/gas/pollen displays, AQI forecast, USGS seismic observations | Fire/smoke enrichment, flood/river/tides, longitudinal records |
| SKY | `StationSky.qml`: atmospheric readings, hourly and daily forecasts | Rich astronomy, twilight, Astroterm, passes, upper-air/aviation |
| SPACE | `StationSpace.qml` with `SpaceService`, aurora, GOES flare + X-ray, SWPC bulletin/window/watch data | Solar imagery, local aurora interpretation, history, runtime acceptance |
| MAP | `StationDiscovery.qml` → NASA EONET open natural-event index | Actual map viewer/layers and additional hazard providers |
| NEWS | `StationDiscovery.qml` → GDELT DOC article list | In-widget reader, filters, clustering, video and rich coverage |
| RADIO | `StationDiscovery.qml` → **separate** Radio Browser read-only list and `Qt.openUrlExternally()` | Replace duplicate directory with shared Hi-Fi backend; playback controls and news-first focus |
| TERMINAL | `StationTerminal.qml` runs dedicated Star Map Kitty via Sway app-id `weather-screen` | Generic central task viewer, independent sessions, dock/expand |
| Hi-Fi (neighboring service owner) | `MediaDeckW.qml`, `services/media/HeadlessMediaController.qml`, `MprisPlaybackAdapter.qml`, `scripts/media/media_controller*.py`, `radio_browser_catalog.py`, guarded relay | Safe shared browse contexts, Weather RADIO integration, live cross-widget testing |
| Source status | View-scoped fetches and statuses across Weather domain | Unified health/fallback/caching/diagnostic instrumentation |

**Evidence limitation:** This describes inspected GitHub source and prior automated tests, **not** a claim that all providers currently respond or that visual/runtime acceptance is complete. Check current HEAD and CI again. As of this snapshot, an unrelated long-lived **Hi-Fi taskbar media dock draft PR #146** is open. Do not modify that assignment without ownership coordination.

## 3. Architecture / relationship map

```text
External data:
  wttr.in / Open-Meteo / USGS / NOAA / NASA EONET / GDELT / others
                         |
             normalized provider services
                         |
   HOME | GROUND | SKY | SPACE | MAP | NEWS
                         |
             shared selected-item state
                         |
        central viewer/terminal host (proposed)
        SELECT <-> VIEW <-> TERMINAL
          expand / mini-dock / restore
                         |
     Weather Station -> full Observatory later

Radio Browser directory & catalog search
                |
       ONE EXISTING Hi-Fi
    media controller + private socket
        MPD queue / guarded relay
      explicit SELECT / LOAD / PLAY
                |
       +--------+---------+
       |                  |
    Hi-Fi Deck        Weather RADIO
    all stations      NEWS FIRST + all
                |
       shared observed state
        no duplicate player
```

**Technical hazard already identified:** `scripts/media/radio_browser_catalog.py` currently updates `_known_stations` and `_station_urls` for each directory search; multiple UIs could invalidate a prior selection. Also, `MediaController.browse_context` is currently shared mutable browse state. Design identity-scoped browsing or independent client cursors without splitting the single playback owner. Preserve the approved stream validation and session-owned localhost relay; do **not** bypass it with arbitrary station URLs.

## 4. Priority 1 // Shared Hi-Fi RADIO — first implementation family

- [ ] Replace Weather RADIO's independent Radio Browser HTTP fetch with the existing Hi-Fi catalog/controller interface.
- [ ] Verify media-controller server/socket lifecycle and capability errors; avoid starting a second daemon.
- [ ] Resolve concurrent Hi-Fi versus Weather browse context, station lookup and pagination invalidation (tests for two clients).
- [ ] Reuse station UUID media references, metadata, directory search, country/language/tag filtering and multiple pages.
- [ ] Reuse existing MPD and MPRIS switching/transport, guarded relay, queue ownership and playback observation.
- [ ] Implement Weather RADIO's full SELECT → LOAD → PLAY plus pause/stop/seek/next where legitimately supported; keep LOAD non-autoplay.
- [ ] Build NEWS FIRST / TALK / PUBLIC / WEATHER / LOCAL / ALL RADIO source filters and news tagging/visual identification.
- [ ] Add station favorites, recently played, saved filters and persistent playback strip; do not create competing stores unnecessarily.
- [ ] Preserve audio when switching Weather modes, docking viewer or closing panel; never claim PLAY until backend confirms observation.
- [ ] Integrate shared station selection with the central viewer and later regional MAP / NEWS links.
- [ ] Test two valid stations, backend failures, changing currently playing media from another client, and no autoplay.

**Boundary:** Existing Hi-Fi media components own transport behavior. Preserve source-specific contracts and coordinate with any active media worker/PR. Directory browsing alone is not evidence of supported audio playback.

## 5. Priority 2 // Shared MAP / NEWS / RADIO viewer and terminal host

- [ ] Audit Star Map terminal geometry, Sway scratchpad/app-id, keyboard focus, lifecycle and current 1000 × 700 station constraints.
- [ ] Specify a shared selected-item contract (domain, stable item ID, source, viewer type, filters, lifecycle) and keep it separate from transport.
- [ ] Introduce domain SELECT / VIEW / TERMINAL states with explicit focus ownership and return navigation.
- [ ] On selection, open domain-appropriate content **inside** Weather Station instead of the unconditional `Qt.openUrlExternally()`.
- [ ] Reuse guarded Kitty/Sway host for terminal-capable viewers; allow dedicated graphical web/map/video rendering where necessary.
- [ ] Provide expand, restore, dock-to-bottom-right, and selectable viewer size with clear status when unavailable.
- [ ] Preserve session and selected item when changing source tabs/modes; decide when viewers terminate versus stay mounted.
- [ ] Avoid cross-mode app-id collisions, unowned process termination, UI freezes, and orphaned Kitty windows.
- [ ] Keyboard/mouse acceptance: shift/select semantics, typing focus, menu navigation and close behavior.
- [ ] Keep arbitrary external URLs/data from being interpolated into shell commands.

**Open design:** Automatic open on selection versus explicit VIEW, and whether dock and expanded viewer share one retained window or different surfaces.

## 6. Priority 3 // MAP + spatial/world event providers

- [ ] Implement actual interactive world map plus terminal-capable map/event inspector, not merely the EONET list.
- [ ] Add radar, animated radar history and nowcasting with a vetted provider; cloud, wind, temperature, precipitation, pressure layers.
- [ ] Plot existing USGS earthquakes and NASA EONET events as grounded coordinates.
- [ ] Add wildfire/hotspot, smoke, severe storm, environmental risk, and optional GDACS disaster feeds.
- [ ] Add air quality, visibility, weather-alert and aurora overlays where appropriate.
- [ ] Add layer selection/combinations, zoom, region search, locations and timestamps.
- [ ] Add event/news/radio overlays and routes to dossiers or local broadcasts.
- [ ] Add optional DeFlock surveillance-awareness data with provenance and privacy guardrails.
- [ ] Later include RF/network/sensor overlays when hardware support exists.
- [ ] Verify map-source licenses, cache/refresh limits, geographic accuracy and missing geometry behavior.

## 7. Priority 4 // NEWS + live coverage

- [ ] Expand GDELT source discovery to topic, region, language, publisher and date filters.
- [ ] Add multiple credible sources, saved publishers, local/world categories and clear publication timestamps.
- [ ] Add in-station article/terminal reader, including fallback when a publisher disallows embedded rendering.
- [ ] Add story clustering, duplicate suppression, source comparison and evidence-backed breaking labels.
- [ ] Build live news channel catalogs and site/approved stream launchers.
- [ ] Provide appropriate native/browser/mpv video rendering, subtitles, volume and fallback controls.
- [ ] Support persistent video, pop-out/PiP/dock and restore without unsolicited autoplay.
- [ ] Link news stories to location, event dossier and nearby/related radio.
- [ ] Treat reported location and reporting intensity as different from actual physical event severity.
- [ ] Verify source attribution, API terms, rate limits and stale/failure states.

## 8. Priority 5 // Additional environment and SKY/SPACE data

**GROUND**
- [ ] Fire, smoke and regional wildfire/heat-stress/fire-weather data.
- [ ] Nearby river/flood gauges, coastal tide sources, relevant environment and health indicators.
- [ ] Source comparison, AQI observations/history and confidence rather than invented precision.

**SKY / ASTRONOMY**
- [ ] Sun/moon rise/set, phase, illumination, twilight/daylight, golden/blue hour.
- [ ] Astroterm task integration and safe terminal controls.
- [ ] Planets, constellations, meteor showers, eclipses, ISS/bright satellite passes and stargazing score.
- [ ] Atmospheric profile, cloud base/ceiling, CAPE, METAR/TAF, aviation and supported advanced weather.

**SPACE / SOLAR**
- [ ] Solar imagery, sunspots, cycle and longer-term GOES/geomagnetic trends.
- [ ] Reliable local aurora viewing context (location, cloud, darkness) separate from worldwide model peaks.
- [ ] Clear distinction between observations, model forecasts, watch days, bulletin age and authoritative alerts.
- [ ] Solar/radio-blackout/radiation impact explanations grounded in official data; no invented active warning state.
- [ ] Continue live-source and runtime verification of NOAA validity/watch supersession.

## 9. Priority 6 // Event intelligence and cross-domain links

- [ ] Event dossiers: type, location, issue/observation time, physical facts, official messages, news and related radio.
- [ ] Relate event ↔ weather ↔ map ↔ news ↔ broadcast with stable references and preserved viewer context.
- [ ] Show source count, reporting trend, confidence and timestamp without equating publicity with severity.
- [ ] Add event timelines, comparable previous events and source-data inspection.
- [ ] Watch events, regions, topics and news clusters.

## 10. Priority 7 // Shared data systems and personalization

- [ ] Location profiles HOME / WORK / TRAVEL / FAVORITES / WATCHED REGIONS, using permissioned location rather than presuming a precise address.
- [ ] Cross-domain filters for location, time, category, severity, source and map layer.
- [ ] Persist favorites (stations, news publishers, locations, map layers, instruments), respecting user-controlled priority.
- [ ] Implement Permanent / Favorited / Temporary / Deep classification in data, not arbitrary UI-only logic.
- [ ] Expand HOME relevance scoring, fade-out/promotions and critical-event override while minimizing disruptive re-layout.
- [ ] Cross-domain search/command bar with clear routing.
- [ ] Unified diagnostics: status, last success, sample age, error details, stale cached results and source agreement.
- [ ] Historical store for weather, AQI, events and solar data; forecast-vs-actual and provider comparison.
- [ ] User threshold watches, safe actionable notification/reporting paths and official hazard provenance.
- [ ] Audit storage, local privacy/security and crash recovery before introducing a new persistent daemon.

## 11. Priority 8 // Observatory and final interface organization (DEFERRED)

- [ ] Build large Observatory shell with main/submode rails, collapsible inspector, multiple layers and focus/fullscreen state.
- [ ] Continue selected item, filter, location, open viewer and playback state from Weather Station into Observatory.
- [ ] Build configurable permanent/favorite/temporary instrument layout and reusable graph/gauge/timeline/compass/mini-media components.
- [ ] Add optional Bullshit Telemetry pool, Chaos slider, Lock, Reroll, auto drift and controlled promotion.
- [ ] **Only after the data inventory is usable**, perform final menu organization, sizing, rail placement, semantic palette/glow, scrolling and expanded viewer design with operator visual approval.

## 12. Priority 9 // Verification and performance gates

- [ ] Check current repo HEAD, open PRs, ownership, relevant services and Syntagma/Hospital protocols before each worker change.
- [ ] Run source and CI tests per independent work family; add parser/contract tests and small integration fixtures.
- [ ] Test the real MAP, NEWS, RADIO views with live provider data, no-data, malformed, stale, rate-limited, offline and fallback cases.
- [ ] Test radio against the **same** existing controller/MPD session from two interfaces, including simultaneous browse changes and guarded LOAD/PLAY.
- [ ] Verify source-specific ownership, focus transitions, terminal scratchpad/geometry, closing, docking and process cleanup.
- [ ] Validate scroll, keyboard, mouse, long labels, resizing and accessible controls on actual Quickshell.
- [ ] Revisit known historical Quickshell freeze/lag investigations before adding polling, decoders, media/video or large maps.
- [ ] Measure CPU, memory, poll count/network calls, UI freeze duration and widget teardown.
- [ ] Keep a rollback reference and note which tests are static, which are real desktop checks, and which remain pending.

## 13. Priority 10 // Hardware extensions (later)

- [ ] Local temperature, humidity, pressure, wind, rain and air-quality sensors.
- [ ] SDR and actual RF weather radio, distinct from online public/weather stations.
- [ ] Meshtastic, LoRa, Reticulum, APRS, ADS-B and future network/satellite reception.
- [ ] Expose hardware state as normalized provider data; do not rewrite MAP or RADIO around a particular device.
- [ ] Separate any hardware permissions/device access from read-only internet catalog work.

## 14. Suggested execution slices and dependencies

These are **proposed work packets**, not automatically assigned Hospital Jobs or unconditional permissions:

| Sequence / family | First bounded deliverable | Depends on | Acceptance evidence |
| --- | --- | --- | --- |
| A — Hi-Fi seam | Safe independent two-client radio browsing over existing one controller | Current media architecture/owner check | No browse invalidation; no autoplay; CI + live operator playback |
| B — Weather RADIO | News-first full controls using the shared transport and classified station directory | A | Functional metadata and controls, one owned MPD session |
| C — Viewer host | Shared selection → VIEW/TERMINAL host; close/dock/expand controlled | Current Star Map/keyboard focus design | No orphan windows, stable input and state |
| D — MAP/NEWS providers | Actual map/article viewer and additional hazard/news sources | C and current discovery backends | Real viewer content, source health, accurate selection |
| E — Environmental/space gaps | Each isolated provider with normalized data and states | Existing weather/space services | Correct parsing, staleness, operator optical check |
| F — Cross-domain context | Event ↔ news ↔ radio/map and persistent selection | B–E | Selection survives transitions |
| G — Observatory | Larger interoperable window sharing existing source state | C/F | Full workflow returns to same item |
| H — UI organization | Operator-driven menus, layouts and visual refinements | Sufficient inventory + usage feedback | Visual approval, no lost backend access |

Parallel work can proceed in independent provider files once ownership is confirmed. Avoid simultaneously rewriting Weather Station routing and the media controller without an explicit contract/handoff.

## 15. NEXT WORKER // Recovery procedure

1. Read **this** document, then the source files linked below. Read the operator's original Weather Station/Observatory master plan in their Library if available: `weather_observatory_master_plan.md`. Treat that older full-vision plan as requirements context, not a live implementation checklist.
2. Verify latest GitHub `main`, current PRs/commits, ownership and any active Hospital Room/Assignment. A conversation does not imply live Hospital registration, role acceptance or staff handoff.
3. Keep separate: (a) accepted user intentions above, (b) proposed implementation slices, (c) current repository reality, (d) local desktop/runtime acceptance.
4. Start with **A: shared-radio browse-context isolation**. Locate `scripts/media/radio_browser_catalog.py`, `media_controller.py`, `HeadlessMediaController.qml`, `MediaDeckW.qml`, `StationDiscovery.qml` and relevant `tests/media/`. Do not introduce a new radio polling/transport system.
5. Propose/test the smallest contract change before connecting Weather RADIO to PLAY. Preserve existing MPD queue ownership and guarded relay security.
6. When implementation has been authorized, use a bounded PR, record tests and fallback/rollback and ask for required merge/local-activation approval. Do not silently merge, restart a user service, change local files or deploy hardware.
7. At each substantive boundary report: **IMPLEMENTATION, HOW TO USE, VERIFY, WATCH OUT FOR, CHECKLIST, NEXT, DECISIONS**.

## 16. Source map and unresolved decisions

**Technical truth:** [Weather Station](../widgets/weather/), [Weather services](../services/weather/), [Hi-Fi Deck](../widgets/MediaDeckW.qml), [Headless Media Controller](../services/media/HeadlessMediaController.qml), [Radio Browser Catalog](../scripts/media/radio_browser_catalog.py), [Media Controller](../scripts/media/media_controller.py), [Star Map terminal](../widgets/weather/StationTerminal.qml), [Weather source rack](../widgets/weather/StationDiscovery.qml), [Media tests](../tests/media/).

**Design and authority:** [Syntagma AGENTS](https://github.com/kudokudo1/Meta-Apollo-Logos-Syntagma/blob/main/AGENTS.md), [source/authority map](https://github.com/kudokudo1/Meta-Apollo-Logos-Syntagma/blob/main/ATLAS/SOURCE-MAP.md), [Post-Apollo working guide](https://github.com/kudokudo1/Meta-Apollo-Logos-Syntagma/blob/main/OPERATE/POST-APOLLO-WORKING-GUIDE.md). Do not duplicate these shared rules here.

**Open decisions awaiting operator use/approval:** exact viewer size/layout, auto-open vs explicit VIEW, News filter default/order and classification policy, how separate sessions dock, which map/video rendering technology to use, Observatory launch strategy, persisted workspace scope, data providers needing keys/credentials, whether official NOAA alert products trigger desktop notifications, and later RF/sensor integrations.

**Current work boundary:** Documentation only. No active Hospital assignment implied; no merge, production activation, runtime certification or local machine modification authorized by this document.
