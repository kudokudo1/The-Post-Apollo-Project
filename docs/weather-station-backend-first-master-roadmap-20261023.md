# Weather Station / Observatory // Backend-first master roadmap and worker handoff

**STATUS //** Operator direction recorded; implementation roadmap and proposed architecture. This is not an executable Hospital assignment, technical certification, live desktop acceptance, authorization to merge, or authorization for a local-machine write.

**RECORDED //** 2026-10-23. **PATIENT //** kudokudo1/The-Post-Apollo-Project. **OWNER //** Operator. **SCOPE //** Weather Station, Observatory future expansion, and cross-component media/viewer seams. **WORKER //** Replaceable; no live Hospital Room, Assignment, Session, provider attachment, or staffing claim verified. **Git evidence //** Main-source inspection on 2026-10-23; branch/PR/runtime state must be rechecked on resumption.

**PURPOSE //** Let a replacement worker or the operator continue development without reconstructing the plan from a long ChatGPT conversation. Preserve the scope and distinctions below. This records operator design intentions and a proposed execution order; it does not freeze every layout detail.

## 0 // The operator's development priority and accepted direction

> **Connect the data and backends, expose the actual information in the menus, THEN organize the UI.**

1. Make the Weather Station's existing domains useful and honest about whether data, rendering, playback, and controls really work. Avoid another instrument-polish cycle while MAP/NEWS/RADIO and shared systems are incomplete.
2. MAP, NEWS, and RADIO are intended to become **selection + embedded terminal/viewer workspaces**. Clicking an event, article, or station should eventually open its relevant viewer **inside Weather Station**, not just launch a browser. Terminal/selection/view modes, auto-opening, bottom-right docking, and expansion are design directions; their exact keybinding, geometry, and persistence rules are still open.
3. The Weather Station RADIO should be **as feature-complete as the existing Hi-Fi Deck**, with **news/public/talk/weather stations emphasized by default**, but ALL RADIO and full station search/playback remain accessible. **Use the same existing controller and playback owner**, not a second Radio Browser backend, MPD daemon, radio streamer, or redundant poller.
4. A larger Weather Station viewer may be justified for a coherent embedded map/reader/player. Final size and layout should follow real, tested content, not precede it.
5. Final Observatory layout, rich visualization, and information organization are **deferred until enough real sources and interactive capabilities are connected**.
6. Distinguish **observed values**, **forecasts**, **official warnings**, **historical bulletins**, **source availability**, and **actually verified active status**. Never treat absence of a source record as an all-clear.
7. Reuse established Post-Apollo components, color/state grammar, keyboard ownership, Sway/Quickshell lifecycle, and security guardrails. Do not let cross-domain convenience erase domain ownership.

## 1 // Evidence and status legend

- **SOURCE PRESENT / MERGED:** verified in GitHub main at the dated inspection. Does not mean live Quickshell or the external API was tested here.
- **PARTIAL:** code/data source exists, but the feature is not complete, integrated across apps, or visually accepted.
- **NOT WIRED:** the user-facing connection/capability remains to build.
- **PROPOSED:** a recommended approach or not-yet-finalized design choice.
- **TEST GATE:** static/CI tests, source contract tests, integration tests, operator live acceptance are separate gates.

Current baseline source paths to re-inspect before modifying anything:

| Domain | Repo evidence / integration point | Status at handoff |
| --- | --- | --- |
| Shell / navigation | widgets/weather/WeatherStationW.qml | HOME, GROUND, SKY, SPACE, MAP, NEWS, RADIO, TERMINAL views present |
| HOME | widgets/weather/StationHome.qml; StationHomePolicy.js | Weather/space snapshot and relevance foundation; full classification/persistence not finished |
| GROUND | widgets/weather/StationGround.qml; services/weather/WeatherService.qml; SeismicService.qml | AQI, gases, pollen where available, forecast, worldwide seismic observations |
| SKY | widgets/weather/StationSky.qml; WeatherService.qml | Current atmosphere and hourly/daily forecasts; astronomy expansions pending |
| SPACE | widgets/weather/StationSpace.qml; SpaceService.qml; AuroraService.qml; SolarFlareService.qml; XrayFluxService.qml; SwpcAlertService.qml | Kp, solar wind, Bz/Bt, solar flux, aurora, observed flares, X-ray flux, NOAA bulletins, warning validity review, watch-day outlook |
| MAP | widgets/weather/StationDiscovery.qml; services/weather/StationDiscoveryService.qml | NASA EONET event discovery **list**, NOT real map canvas yet |
| NEWS | StationDiscovery.qml; StationDiscoveryService.qml | GDELT article discovery list, NOT internal article reader/clustering/live video |
| RADIO | StationDiscovery.qml; StationDiscoveryService.qml | Independent Radio Browser list + external URL opening. **Temporary duplication**, NOT Hi-Fi-integrated playback |
| Existing terminal | widgets/weather/StationTerminal.qml | Kitty Star Map via Sway floating window overlay; hardcoded title/app ID/launch/geometry, NOT reusable host yet |
| Hi-Fi | widgets/MediaDeckW.qml; widgets/MediaDeckBrowserControls.qml; services/media/HeadlessMediaController.qml; MprisPlaybackAdapter.qml | Media UI and persistent-controller client already exist; reuse |
| Radio directory/relay | scripts/media/radio_browser_catalog.py; media_controller.py; media_controller_server.py; radio_stream_relay.py; media_controller_cli.py | Source-qualified Radio Browser station UUID, guarded MP3 relay, private socket and MPD transport implementation |
| Repo tests | tests/weather/, tests/media/ | Static/contract suites and offline controller tests; live audio/UI verification remains a separate gate |

Key previous feature PRs for provenance only; do **not** infer current open/merged state from these historic numbers: GROUND #575, seismic #580; SPACE aurora #584, flare events #586, X-ray #590 plus fix #591, official bulletins #594, warning validity #598, watch outlook #601; MAP/NEWS/RADIO first source racks #608. Inspect GitHub rather than blindly reusing those statuses.

Related source-of-truth and reading:
- Syntagma: https://github.com/kudokudo1/Meta-Apollo-Logos-Syntagma/blob/main/AGENTS.md (shared rules); relevant OPERATE Hospital and Post-Apollo working protocols.
- Local model/contracts: ../MODEL/README.md and ../MODEL/contracts/media-controller-v0-draft.md.
- Existing radio implementation notes: ../scripts/media/RADIO-BROWSER-DIRECTORY.md and ../scripts/media/HEADLESS-CONTROLLER.md.
- Existing design/interaction docs: ../docs/unified-widget-keyboard-navigation.md and ../docs/neon-scrollbar-syntagma-api.md.
- Operator's larger early reference: weather_observatory_master_plan.md was supplied separately in their ChatGPT Library, not necessarily available to every GitHub worker. This file records the actionable continuation, but that original plan can supply the wider design background.

## 2 // Immediate assignment family A: consolidate RADIO into the existing Hi-Fi engine

**Objective:** Weather RADIO is another full-featured client of one playback/catalog system, optimized for news. The Hi-Fi Deck remains the broader music/radio interface.

- [ ] **A1 // Audit live media ownership:** confirm current MediaDeck host, server process, actual socket/service, ApolloHub bridge, MPD/MPRIS selection, and any concurrent media owner/PR. No assumption of live controller from source alone.
- [ ] **A2 // Fix shared discovery identity before sharing:** radio_browser_catalog.py currently replaces its _known_stations and _station_urls maps per search, and media_controller.py stores one browse_context. Searching jazz in Hi-Fi and news in Weather can invalidate older UUID selections in the other UI. Design per-client browse scopes or stable short-lived catalog batches; preserve dedup, bounded cache/lifetime, authorization, pagination, and source-qualified station IDs. Do not create a separate controller.
- [ ] **A3 // Preserve exact transport safety:** browser station listings are untrusted. Use the existing guarded HTTPS MP3 localhost relay and private JSON-lines socket. Avoid passing raw Radio Browser URLs to MPD or into shell commands, bypassing SSRF/network checks, or opening arbitrary links to claim playback.
- [ ] **A4 // Add a Weather radio client/adapter:** reuse an owner-mediated controller instance or a narrowly defined scoped client to the **same server**. Prefer one observer rather than duplicate high-frequency polling. Verify playback/source state really belongs to the loaded queue item.
- [ ] **A5 // Full control parity:** station search, result pagination, inspect, select, load, play, pause, stop, next/previous/seek only where supported, queue ownership/status, station title/codec/bitrate/tags, transport feedback, and real error states. **SELECT ≠ LOAD ≠ PLAY**; no station autoplay from search, selection, opening a menu, or restoring layout.
- [ ] **A6 // News-first browsing:** NEWS, TALK, PUBLIC, WEATHER, LOCAL, ALL RADIO, with existing catalog predicates such as tag:news, tag:talk, country:US and language:English. Directory classifications are imperfect: a “NEWS” visual tag means directory/category evidence, not editorially verified content. Keep All Radio reachable.
- [ ] **A7 // Visual distinction and persistence:** clear magenta news classification; separate orange active playback; favorites, recent stations, source/region/language filters, and persistent transport strip while changing Weather Station modes. Adopt shared persistence contracts only after inspecting current owner.
- [ ] **A8 // MPRIS boundary:** the existing adapter explicitly selects an external player; MPRIS must not automatically claim a browser tab or MPD stream. Test MPD and MPRIS separately and avoid cross-player command drift.
- [ ] **A9 // Concurrent integration tests:** two clients with different browse queries; station identities survive searches; actions target exact UUID/queue ID; failed/mismatched ownership rejected; close/hide Weather menu without stopping audio; no new radio daemon/poller; live two-station acceptance with operator approval.

**Implementation seam:** scripts/media/radio_browser_catalog.py, media_controller.py, media_controller_cli.py, services/media/HeadlessMediaController.qml, widgets/MediaDeckW.qml, StationDiscovery.qml / prospective domain-specific StationRadio view. Coordinate with active media and ApolloHub ownership; do not bypass the existing B4 read-only shared bridge.

## 3 // Immediate assignment family B: embedded terminal / viewer host for MAP, NEWS, RADIO

**Objective:** Selecting information changes an internal view, not just an external browser action.

- [ ] **B1 // Extract reusable host contract:** inspect StationTerminal.qml's Kitty command, Sway app_id=weather-screen, local helper, screen mapping, geometry sync, scratchpad lifecycle, keyboard focus and cleanup. Specify a single viewer-host API (domain, content ref, renderer kind, selected item, size mode, state/status/error).
- [ ] **B2 // Selection state:** SELECT (browse/filter), VIEW (show chosen item), TERMINAL (interactive application), DOCK (compact bottom-right), EXPAND (large center), optional FOCUS/fullscreen. These are **candidate behaviors** pending operator hands-on review. Clicking an item may automatically enter VIEW, but do not lock it as final without a test.
- [ ] **B3 // Distinct renderers:** terminal text/graphics/astro applications where appropriate; map-capable visual renderer for actual maps; article text/browser reader for rich news; MediaDeck transport/metadata viewer for radio; video renderer where terminal text is insufficient. A text terminal does not magically render a full geospatial map or web video.
- [ ] **B4 // Window discipline:** no competing Sway floating windows with the same app ID, no screenshot/window identity confusion, no zombie Kitty, no redraw/poll loop each frame, no uncontrolled terminal spawn. Preserve selected state across view swaps/docking while cleaning up only resources truly owned by the viewer.
- [ ] **B5 // Safe handoff:** pass validated structured event/article/station references to registered viewer adapters. Never concatenate arbitrary remote URLs/event titles into bash, swaymsg, or terminal commands.
- [ ] **B6 // Geometry + keyboard:** start from current Weather Station 1000x700, allow larger viewer if needed; preserve main rail/footer and source status. Integrate Shift/Select semantics, tab/focus ownership, scrollbars, input editing, modal closing and responsiveness.
- [ ] **B7 // Restore / continuity:** reselect previous item, remember filter/query and dock/expanded state where authorized. Playback state belongs to the shared controller, not a transient terminal.
- [ ] **B8 // Visual and lifecycle acceptance:** simultaneous browsing/playing, resizing, mode switching, menu close/reopen, focus from other windows, multiple outputs, failure cleanup, and recovery after Quickshell reload. Do not infer success from static CI.

### B9 // 2026-10-23 SwayPX Stage Director integration boundary

**Operator-observed:** after Weather Terminal position fix [#645](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/645), Kitty `weather-screen` occupies the correct geometric Star Map bay. It remains obscured by the Weather Station's overlay fill until the separately reviewed **visual transparency cutout** is merged and verified. The operator reports their SwayPX repository likely matches the live binary; binary/revision identity was not independently verified.

**SwayPX source check:** `Post-Apollo-SwayPx` branch `stage-director/scene-registry-v1` implements Stage Director **SD0** as a shadow-only compositor scene observer. Its Weather Station profile classifies `weather-screen` as a `weather-station/star-map` actor with scene 1000×700 and declared bay 780×416 @ (190,132). SD0 explicitly has **NO geometry, focus, stacking, or lifecycle mutation authority**. That branch is not SwayPX `master` as inspected on 2026-10-23. This is not proof of the operator's currently running compositor build.

**Near-term ownership:** Quickshell Weather Station owns painted chassis alpha and the matching input Region mask. `StationTerminalGeometry.js` uses `swaymsg -t get_outputs` to compute Kitty's global position; Sway executes floating placement. A **four-rectangle visual chassis fill** outside the bay and a transparent local terminal background should reveal Kitty despite Weather Station's Overlay layer. This is a source-level cutout until operator confirms actual desktop visibility.

**Future boundary:** Stage Director may observe/coordinate the parent layer-shell surface, its Kitty child, and their scene relationships. Moving placement authority from Weather-specific `swaymsg` to SwayPX requires an explicit later Stage Director design/authorization gate. Avoid two simultaneous position writers. When adding MAP/NEWS/RADIO terminal actors, use unique app/window identities and keep the visual alpha hole, input Region, and compositor positioning synchronized to the *same viewport rectangle*.

### B10 // 2026-10-23 Header-driven terminal modes and expanded bay

**Operator screenshot:** the STAR MAP Kitty window is now visible through the alpha cutout, but the terminal was positioned too high and its interior was cramped. The operator requested moving the bottom STAR MAP / CLOSE buttons to the Weather Station header, next to the live-source badge, replacing the inactive future/Observatory square; the launch label should follow the current main mode and the small terminal CLOSE button should be red. The existing header × continues to close Weather Station itself.

**Implementation candidate:** Weather Station header uses the same ActionButton shell for a mode-aware launch (TERMINAL → STAR MAP; NEWS → NEWS; RADIO → RADIO; likewise other current modes) and adjacent red CLOSE. A single `StationTerminal` host uses a **trusted, enumerated mode** to launch the existing `weatherstation-starmap` program for TERMINAL and a **plain, domain-labelled Kitty shell** for other modes. **This is NOT yet a specialized news, radio or geographical map terminal application** and does not yet hand selected events/stations/articles to Kitty. Treat those specialized adapters as remaining M3/C/D work. Each session has its own app ID (`weather-screen` for STAR MAP, `weather-screen-<mode>` for others) and is explicitly closed on view change so compositor selectors cannot reposition the wrong window. Existing radio playback ownership remains with shared Hi-Fi.

**Viewport design:** move the terminal bay from local (30,70) / 780×416 to local (14,90) / 812×468 at the current 1000×700 Weather Station size. Continue using **one geometry source** for Sway absolute placement, QML visual hole, and pointer pass-through. Bottom controls are removed rather than covering the enlarged viewer. This should be visually and interactively verified by the operator on live Sway before the new geometry is called accepted.

**Stage Director coordination:** its SD0 Weather Station profile still declares the **older** 780×416 @ (190,132) scene-bay geometry. The new bay is **812×468 @ (174,152)** relative to the 1000×700 station. That declaration will be stale if this UI work lands; update Stage Director's scene model in its own reviewed assignment, not via an unauthorized compositor patch. Stage Director's present observation-only contract stays intact. New domain app IDs are not yet classified by that old profile; the M3 coordination plan must register them.

### B11 // 2026-10-23 Sway-observed Kitty fit vs intended bay

Operator ran `swaymsg -t get_tree` on the live Weather Station STAR MAP actor and reported Sway window rect **(1714,152) / 780×400** after the preceding QML implementation requested **(1714,152) / 812×468**. Position was correct, dimensions were **not**. This is runtime evidence that successful `swaymsg resize` exit does not guarantee resulting compositor size. The screenshot also showed unrelated desktop content through the excess transparent area.

**Bounded corrective plan:** an extra cyan divider separates the header's contextual launch/CLOSE controls from the live-feed status badge. The station bay gains modest space, local **(8,90) / 824×482** in the fixed 1000×700 station (Sway expected (1708,152) on the primary reported 2560×1440 output). The Sway resize request explicitly names width and height in pixels. After positioning, a **one-shot `swaymsg -t get_tree` verification** finds only the exact actor app ID and measures its observed rect. The visual alpha cutout and input Region open **only at the intersection of the intended bay and observed actor**, leaving unused background painted if Kitty again refuses some requested dimensions. The UI reports `PARTIAL FIT` rather than silently treating the request as guaranteed size. No additional continuous get_tree poller or auto-resize loop. Live compositor acceptance and source permission boundaries remain required.

**Stage Director future reconciliation:** the Stage Director SD0 declarative profile still describes 780×416 at (190,132), and has no mutating geometry authority. After confirming the desired viewer geometry, coordinate separately with the SwayPX owner to update the scene declaration; do not change compositor branch in this Weather UI PR.

## 4 // Domain family C: MAP and world/environmental layers

Current EONET is an event index only. Planned:

- [ ] **C1:** real pan/zoom/select geographical map canvas; selection-linked center viewer and event inspector.
- [ ] **C2:** weather radar (e.g. evaluated RainViewer), radar history/animation and observed/forecast distinction.
- [ ] **C3:** reuse USGS seismic events as quake pins with timestamp/depth/magnitude and source details.
- [ ] **C4:** fire/wildfire/smoke sources; NASA EONET, NASA FIRMS where API/license allows, and relevant alert layers.
- [ ] **C5:** storms/hurricanes/severe weather, wind fields, temperature, pressure/isobars, precipitation, cloud, AQI, visibility, snow and day/night layers as providers allow.
- [ ] **C6:** filter by time, region, severity, source; enable composable layer controls and usable legends.
- [ ] **C7:** events → news → radio → local weather cross-navigation; no false correlation based merely on geographic proximity.
- [ ] **C8:** optional DeFlock/privacy-awareness layers, with appropriate uncertainty and non-evasion framing; future RF/space overlays.
- [ ] **C9:** freshness, authoritative source label, missing-coordinate handling, dedup, rate-limit/cache, event timeline and provider-failure tests.

## 5 // Domain family D: NEWS and live coverage

Current GDELT is article discovery only.

- [ ] **D1:** multiple credible feeds and source selection; topics/categories, region/country, language, time-window, publisher and saved filters.
- [ ] **D2:** internal article/terminal reader and link opening where internal rendering is unsupported; avoid pretending an article was fully retrieved if only the headline exists.
- [ ] **D3:** story clustering/source comparison, source count, reporting trend and confidence/age indicators.
- [ ] **D4:** live-news channel catalog, official video streams or appropriate browser/mpv fallback; captions, volume, transport, pop-out/PiP, accessibility.
- [ ] **D5:** persistent video/media session while changing Weather Station modes and when expanding to Observatory, with player ownership explicit.
- [ ] **D6:** cross-link geolocated events to news and adjacent local/public news radio, subject to evidence rather than invented attribution.
- [ ] **D7:** provider throttling, duplicate stories, URL safety, malformed content, offline behavior, source attribution, article copyright/terms.

## 6 // Domain family E: deepen WEATHER / SKY / SPACE information

All three are **partially fulfilled already**. Do not duplicate existing telemetry or degrade distinctions.

### E1 // GROUND
- [ ] Smoke, heat stress, fire-weather and environmental comfort; richer pollen support where a trusted local source exists.
- [ ] River/flood gauges, coastal tide information where relevant, nearby sensor comparisons, local storm and public safety alerts.
- [ ] Air-quality and weather histories with consistent timestamps, units and source quality; source age and fallbacks.
- [ ] More advanced severe-weather hazards: storms, lightning, flood, winter weather and official public-warning provenance.

### E2 // SKY
- [ ] Astronomy: sun/moon phase, moonrise/set, illumination, sunrise/sunset, twilight levels, day/night length, golden/blue hour, visible planets, constellations, meteor showers, eclipses.
- [ ] Astroterm integration using the reusable terminal host; stargazing score combines astronomy with actual cloud/visibility conditions.
- [ ] ISS/bright satellites and passes, countdowns and local observation context.
- [ ] Atmospheric expansion: dew point, cloud layers/base, freezing level, CAPE, wind at altitude, stability; METAR/TAF/aviation data where useful.

### E3 // SPACE
- [ ] Continue verifying source semantics and long-term history for Kp, wind, Bz/Bt, solar flux, aurora, flare events, X-ray flux, NOAA bulletins and watch outlook.
- [ ] Solar imagery/sunspot/solar-cycle indicators; distinguish model, raw flux, detected event, warning, and alert.
- [ ] Local aurora visibility interpretation incorporating configured location, clouds and darkness; never equate peak hemisphere OVATION cell with local viewing odds.
- [ ] Radio blackout/radiation storm and satellite impact context from official sources; cautious active-alert interpretation.
- [ ] History/trend visualizations, comparisons and freshness rules.

## 7 // Domain family F: event intelligence, shared state, classification and automation

- [ ] **F1 // Event dossiers:** location, event class, published start/update, physical evidence, official alert, news coverage, source count, related records, reporting trend, local weather, radio/live video, history and raw source links.
- [ ] **F2 // Shared location profiles:** HOME/WORK/FAMILY/TRAVEL/FAVORITES/WATCHED REGIONS. Never infer an exact private location from coarse context; use configured station data and user permissions.
- [ ] **F3 // Unified search/filters:** LOCATION / TIME / CATEGORY / SEVERITY / SOURCE / LAYER; domain-specific NEWS/RADIO/WEATHER controls; filtering should preserve input and selection through view transitions.
- [ ] **F4 // Data classes:** Permanent, Favorited, Temporary/Relevant, Deep. Persist explicit favorites, never auto-evict them, and freeze major auto-layout updates while user reads. Critical-alert presentation is a separate verified interrupt path.
- [ ] **F5 // Relevance engine:** build on existing HOME relevance; inputs include severity, age, distance, confidence, user watchlist and sources. Preserve why an item was promoted; never overclaim official urgency.
- [ ] **F6 // History:** local scoped cache/data store, temperature/wind/pressure/AQI/Kp/events trends, forecast-vs-actual, sources' disagreement, timelines and source diagnostics.
- [ ] **F7 // Alerts/reporting:** official weather/space source age, user-configured conditions/thresholds, alerts and notification boundaries; no spam or emergency all-clear based on incomplete data.
- [ ] **F8 // Shared Weather↔Observatory state:** source, selected event, region, filter, player, reader, viewer mode/size and replayable context; no reset on expansion.
- [ ] **F9 // Provider diagnostics:** last success/error/request age/latency/cache age/quality; source-specific stale states and rate limits; only introduce fallbacks after security review.

## 8 // Later family G: Observatory, UI organization, experiments, hardware

**Deferred until real data and backend interfaces are sufficiently accessible and tested.**

- [ ] **G1 // Observatory shell:** enlarged window, primary/submode rails, collapsible inspectors, large maps, video, focus/fullscreen and shared state with Weather Station.
- [ ] **G2 // Layout organization:** re-evaluate main modes/submodes, cards, information hierarchy and module sizes **with actual datasets visible**. User leads final decisions. Preserve retro instrument language and existing semantic colors.
- [ ] **G3 // Reusable instruments:** gauges, compass, sparkline, timeline, source-age/health, map preview and compact media strip using existing Post-Apollo components first.
- [ ] **G4 // Bullshit Telemetry:** optional low-priority novelty pool with Chaos slider, lock, reroll, drift, relevance promotion and persistence. Do not allow it to displace important content.
- [ ] **G5 // Future hardware:** local physical weather sensors, SDR/weather radio, Meshtastic/LoRa/Reticulum/APRS, ADS-B, satellite reception, and related map layers **only after software-only system is stable**.

## 9 // Cross-cutting safety, performance and validation checklist

- [ ] **Current-state reacquisition:** before every implementation, re-read GitHub main HEAD, open PRs, ownership, parent/child dependencies and current test files. Static source state ≠ local pulled tree ≠ running Quickshell ≠ Hospital assignment.
- [ ] **Quickshell UI freeze investigation:** existing reports describe freezes with audio/radio and multiple modules; benchmark responsiveness, CPU, memory, network/poll frequencies, QML updates and subprocess lifetimes when these views are mounted.
- [ ] **No duplicate pollers:** reuse WeatherService, SpaceService and single media controller; instantiate view-local feeds only under the selected open view and stop when closed.
- [ ] **State integrity:** pending selection must not start playback; menu close must not kill MPD audio; unknown owner/bus/session must not be commandeered.
- [ ] **Provider safety:** URL/redirect/DNS/TLS/MP3 restrictions from current guarded radio relay; structured argument passing for terminals. Preserve private socket boundaries.
- [ ] **Data truth:** Ready/Loading/Stale/Failed/Unavailable, last successful update, UTC vs local time, unit conversions and missing-field behavior.
- [ ] **UI acceptance:** input focus and keyboard owner, scalable fonts, long metadata, scroll behavior, full/mini geometry, multi-monitor Sway, resize, dock and close/reopen.
- [ ] **Automated:** source contracts, pure-data policy tests, controller/session isolation and regressions, failure injection with fake inputs and providers.
- [ ] **Live operator:** no claim of runtime passing without a real desktop trial and report; local file writes/reloads/service restarts only after scope-specific operator approval.
- [ ] **Rollback:** isolate implementation PRs, keep commit/diff/test evidence, and document the safe reversion/suspension method before touching global service state.

## 10 // Proposed implementation sequence and milestone gates

The family ordering is dependency-driven, not an irrevocable serial schedule. Workstreams on independent providers may proceed in parallel under separate verified ownership.

| Milestone | Dependency / deliverable | Minimum acceptance |
| --- | --- | --- |
| M0 / Inventory | Inspect live main, current source racks, Hi-Fi seams, ownership, test baseline; verify provider formats | source map, open collisions, data gaps, tested vs merely present |
| M1 / Shared radio sessions | A1-A3: per-client browse contexts/identity and safe relay preserved | cross-client search isolation, UUID/queue match, no playback mutation on browse |
| M2 / Weather Hi-Fi radio | A4-A9: news-first full-featured radio client using one controller | SELECT/LOAD/PLAY, full controls, actual transport status, playback continuity |
| M3 / Viewer host | B1-B8: common item selection and internal viewer host | no arbitrary URL shell exec, correct focus and geometry, recoverable dock/expand state |
| M4 / Providers and rich domain views | C/D/E: map layers, news reader/video, astronomy/environmental additions | real provider evidence, explicit missing states, clean integration with host |
| M5 / Cross-domain state | F: dossier, location/filter/watch, history/diagnostics and classification | navigation/selection preserved; provenance and permission tests |
| M6 / Organization and Observatory | G1-G4: user-led layout, major window, novel deep-data surfaces | user-facing visual acceptance with representative live content |
| M7 / Hardware later | G5 | separately approved external hardware/security contracts |

### Known collision / blocking risks

1. **Shared Hi-Fi browse state is not multi-consumer yet:** _known_stations/_station_urls and browse_context are overwritten by subsequent searches. Must fix before using both UI consumers.
2. **ApolloHub media integration has read-only owner-mediated seams:** do not construct rival global polling or seize controller ownership.
3. **StationTerminal is Star Map specific:** Kitty weather-screen app ID and Sway float positioning cannot simply be cloned for simultaneous MAP/NEWS/RADIO sessions.
4. **Weather RADIO currently exposes raw station URLs externally:** do not treat that as safe playable Hi-Fi integration. Replace with source-qualified controller refs after session fix.
5. **Live UI freezes were previously observed:** adding high-frequency reactivity or duplicate subprocesses is a real risk.
6. **News and geographical mapping are incomplete:** article links and event list entries are not finished embedded readers/maps.

## 11 // Hospital-compatible worker handoff

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** No live Room identity verified; this is a GitHub-based recovery handoff, not a Room registration  
**ASSIGNMENT //** Proposed Weather Station backend-first expansion and shared media/viewer integration; a subsequent worker must verify formal ownership/assignment  
**STATE //** ROADMAP SAVED; IMPLEMENTATION NOT AUTHORIZED BY THIS NOTE  
**REPORT KIND //** CONTINUITY / PROPOSED WORK PLAN

### IMPLEMENTATION
This document records the operator's decisions, current source seams, backlog, dependencies, and risks. It does **not** implement the newly proposed work or assert a live system-state change.

### HOW TO USE
Open this file through the repository MODEL index. Reinspect active source and current GitHub state, then select **one bounded milestone**. Explain the existing UI route first, terminal command second. Do not resurrect old branch assumptions.

### VERIFY
Documentation content is based on the operator discussion and GitHub source inspection on 2026-10-23. References and checkboxes describe source evidence vs planned work. No new live-radio, source API, terminal docking, or Quickshell runtime acceptance was performed by this documentation task.

### WATCH OUT FOR
Do not treat the operator's desired experience as permission to change files, merge PRs, activate services, restart Quickshell, or redesign every menu. GitHub documentation is durable planning evidence, not a live Hospital checkpoint. When a later worker finds a conflicting active assignment, coordinate rather than overwrite.

### CHECKLIST
Resume from the outstanding [M0-M7 milestone table](#10--proposed-implementation-sequence-and-milestone-gates) and [families A-G](#2--immediate-assignment-family-a-consolidate-radio-into-the-existing-hi-fi-engine). Check off only evidence-backed completions, and update this document with PR/test/source links when work lands.

### NEXT
First recommended bounded task: **M0 → M1**, validate the current Hi-Fi controller ownership and implement browse-context isolation for concurrent Hi-Fi and Weather Radio consumers, without starting another playback service. Follow with Weather Radio full control parity and the shared terminal/viewer host.

### DECISIONS
Accepted operator direction: backend/data availability first; shared full-featured news-oriented radio; MAP/NEWS/RADIO as eventual internal terminal/viewer workspaces; defer final layout. Still open: exact view modes and automatic transitions; viewer geometry/dock behavior; adapter shape and persistence; watch/news classification evidence rules; provider prioritization and authorization for each implementation.

**RECOVERY INSTRUCTION //** A replacement worker should read this plan, inspect current branch/open PRs and any actual Hospital assignment, and verify local/runtime state separately. Preserve existing media and domain ownership; do not merge or activate anything without the required operator authorization.
