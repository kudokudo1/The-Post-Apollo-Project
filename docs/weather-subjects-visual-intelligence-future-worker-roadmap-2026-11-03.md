# Weather StationW // SUBJECTS Visual Intelligence & MAGICK Lenses
## Durable future-worker roadmap, 2026-11-03

**PATIENT:** kudokudo1/The-Post-Apollo-Project  
**ROOM:** Weather StationW // Subject Visual Intelligence (planning-only handoff)  
**PROVIDER:** OPEN AI // CHATGPT, external Hospital-compatible; no verified live Hospital registration  
**STATE:** PROPOSED ROADMAP, NOT IMPLEMENTED BY THIS DOCUMENT  
**AUTHORITY:** User requested this roadmap be saved for later/future workers. This authorizes documentation, not a new rendering engine, installed package, local change, or live activation.  
**BASE:** Existing six SUBJECTS families, W1/W1r family-rail reformat and subsequent GitHub source state. Recheck main and active assignments before implementation.

## 1. Vision and non-negotiable user requirements

Make SUBJECTS a **living visual analysis environment**, more interactive and visually compelling than CLASSIC. Graphs, maps, astronomy/planetary views and MAGICK visualizations should be useful working instruments, not decorative empty cards. Users should be able to inspect what changed, when, why a source is shown, and what a pattern means through several explicitly chosen interpretive lenses.

- Existing Post-Apollo language: magenta identity/selected controls, cyan structural dividers, GohuFont 11 Nerd Font Mono, retro CRT/tactile feel, neon/star scrollbar, serious rather than generic dashboard visuals.
- Main modes remain on the LEFT rail, per W1r; bottom horizontal row chooses submodes; existing header INDEX opens detailed routes; preserve CLASSIC until operator acceptance and separate migration. Do **not** undo W1r placement while adding graphs.
- Prefer IN-STATION rendering. Avoid involuntary browser launches or other focus theft. Mouse wheel zoom and drag-pan are first-class controls for maps and sky/orbital views; buttons remain available.
- Show real values and clear unknown states. No invented graph samples, future predictions, planetary positions, live availability, magical claims, or simulated imagery presented as measurements. Demo/sample modes, if ever added, must be obviously marked.
- Preserve one owner per provider, source, store and active process. Avoid independent widget/terminal pollers and archive writers.
- Design data and interpretation contracts independently of QML rendering so visualizations may later be reused in a constrained Kitty/terminal display or Stage Director/SwayPX surface.
- This roadmap spans graph infrastructure, interaction, geospatial exploration, COSMOS visual astronomy, MAGICK meanings, and later terminal sharing. They are one program with **bounded milestones**, not one giant PR.

## 2. Worker ownership and Hospital boundaries

**Other worker's lane (do not absorb):** CLASSIC-to-SUBJECTS transfer and retirement, original HOME intelligence/favorites/random rotation, W2 HOME smart deck/pinning, legacy panel parity, gradual CLASSIC removal. A Weather W2a HOME smart panel/favorites PR was open during initial 2026-11-03 audit; verify latest ownership, not the historic status.

**This future program's lane:** reusable interactive charts; observations/forecast visualization; visual planetary/sky geometry; map overlays and time-scrubbing; cross-subject comparison affordances; MAGICK visual layers and sourced meaning lenses; eventually a terminal-friendly data/rendering contract.

**Shared seams, coordinate before editing:** StationWorkspaceSurface.qml, StationSubjectNavigator.qml, WeatherStationW.qml, StationHome.qml, the original StationSky.qml/StationSpace.qml/StationDiscovery.qml, source services, stores, source policy, runtime/terminal hosting. Begin with isolated NEW components/pure adapters/tests, then integrate through narrow, approved entry points with the owning worker's knowledge. Do not quietly change another team's assigned files.

**Permissions:** Repository documentation is the task completed here. Future implementation requires relevant operator authorization or established Hospital assignment. No local Fedora writes, Quickshell restarts, PR merging into production, or live Hospital registration are implied by this plan.

## 3. Current source evidence and recovery pointers (reverify at execution)

The following files existed and were inspected on GitHub for this document:

- services/weather/WeatherLiveHistoryStore.qml: bounded one-writer observational history with samples(sourceId, scopeKey, nowMs), count, latest, trend and distinct observedAtMs / receivedAtMs. NOT a radar/frame archive, forecast series, or provider polling engine.
- widgets/weather/WeatherRelationshipPolicy.js: numericSeries, nearestPairs with one-to-one time matching, Pearson correlation with minimum four pairs, and trend helpers. The four-pair minimum is a display gate, NOT scientific significance or causal proof.
- widgets/weather/StationSourceHealthPolicy.js: source age, sample age, LIVE/STALE/DEGRADED/OFFLINE states. Use provider sample time when available, not only local receipt time.
- widgets/weather/StationSky.qml and StationCosmosSubjectPane.qml: original Sun/Moon, planet rise/set, celestial fix, eclipse, meteor, ISS and space-weather instruments with route-filtered COSMOS entry points. Existing panels may combine several datasets. Verify the precision, source and coordinate frame before positioning orbital bodies.
- widgets/weather/StationMagickSubjectPanelPolicy.js and StationMagickSubjectPane.qml: **astronomical reference only** for selected routes; astrology charts, aspects, zodiac, retrogrades, transits, tarot and journal calculation/storage not yet connected in this audited baseline.
- widgets/weather/StationDiscovery.qml: existing Natural Earth geographic map, Earth/Weather overlays, source-native event selection, map pan/zoom, and dossier/archive hooks. Ownership of event data, GDELT mentions, NOAA radar, NASA FIRMS, GDACS, USGS, smoke layers remains separate.
- widgets/weather/StationWorkspaceNavigationPolicy.js, StationWorkspaceSurface.qml, StationWorkspaceFamilyRail.qml and StationSubjectNavigator.qml: current subject routing / W1r layout. This is a visual-upgrade effort, NOT another navigation transfer.
- docs/weather-workspace-home-continuity-w1-plan.md, docs/weather-workspace-left-main-rail-w1r-handoff.md and docs/weather-magick-observational-reference-g1-handoff.md: preexisting continuity and scope. This document supplements them, not a replacement.
- Relevant map source policies/geometry and any Stage Director/SwayPX integration must be freshly audited at the start of those milestones.

**Evidence status:** These are source-file observations, not claims of a live Quickshell run, functioning remote endpoints, installed GUI components, current planet ephemerides, or production availability.

## 4. Reusable visual primitive family (PROPOSED NAMES, NOT EXISTING FILES)

Candidate components; naming is tentative until a source/tree audit for equivalents:

| Candidate | Function | Input contract / caution |
|---|---|---|
| StationTrendChart.qml | small sparkline + larger time-series display | timestamp/value/unit + observed/source freshness; missing-data gaps shown |
| StationDualTrendChart.qml | two aligned series, independent axes where justified | explicit field pairs, time tolerance, unit labels, no implied causation |
| StationRangeBandChart.qml | forecast intervals, flood warning bands, uncertainty | verified bounds/threshold provenance and valid time |
| StationEventTimeline.qml | scrub chronological events | event IDs, actual start/end/peak, valid-vs-issued time, source |
| StationPhaseStrip.qml | Moon cycle, solar and geomagnetic phase strips | genuine phase/time basis and timezone |
| StationAlignmentWheel.qml | ecliptic/sky/orbital position visualization | coordinate frame, epoch, precision, observer, astronomy engine |
| StationSkyArc.qml | local horizon arcs, rise/set/transit | azimuth/altitude and observer location, not sign longitude |
| StationMapTimeControls.qml | shared layer toggles and time-linked marker selection | source layer ID, timestamp, geometry validity |
| StationLensPanel.qml | fact vs sourced symbolic interpretations | lens IDs, source citations, tradition/context, no conflation |

Prefer pure JS policies for numeric transforms and geometry with Node tests, then lean QML Canvas/Scene Graph drawing. Do not adopt an unrelated chart package until the existing QML renderer and performance budget are examined. Components need responsive size at the actual available width inside the 1000px station and 160px left rail.

### Cross-renderer observation contract

Design one serializable read-only model before painting:

- identity: domain, subjectRoute, sourceId, data product ID, stable event/panel ID;
- provenance: provider, source URL/document ID where applicable, release/issue timestamp, received timestamp, sample/observation timestamp, cache state, retention class, reliability caveat;
- coordinates: unit, geographic/sky frame, epoch, origin/observer, location precision; never mix equatorial RA/Dec with ecliptic longitude or local azimuth silently;
- geometry: {timeMs,value,unit} series; forecast point/band; event time/point/polygon; celestial {body,time,coordinateFrame,position,uncertainty};
- state: active, loading, unavailable, stale, degraded, no data, out of range, user-hidden;
- interpretation: independent optional lens block with tradition/version/source, claim kind (OBSERVATION / COMPUTATION / HISTORICAL TRADITION / SYMBOLIC READING / PERSONAL REFLECTION), and explicit caveat.

The UI consumes the model; collectors and stores remain owned by their existing services. When a terminal renderer is ready, it can consume the same bounded model and draw ASCII/braille/Sixel/Kitty graphics or a framed surface without duplicating fetch logic.

## 5. Interaction model across SUBJECTS

**Required behavior to design and test:** 6h / 24h / 3d / 7d time range presets (only show a range if retained data support it), later custom time controls; graph hover/keyboard focus value inspector; click-to-lock data sample; optional crosshair/time scrubbing; clear missing-data gaps; selected unit and source labels; observable-vs-forecast-vs-archived filter; layer visibility and compare mode; map scroll-to-zoom and drag-to-pan; click marker to open existing event dossier/source context without duplicating the archive; switch lens without changing underlying observation.

Make interaction state survive navigation where useful and where existing lifecycle permits. Persist only with an approved existing settings store; do not secretly add storage writes. Use progressive interaction so charts remain readable without hover on touch/keyboard. Avoid autoplay, surprise browser openings, new terminal spawning, and hidden polling.

## 6. Subject-specific visual opportunities

### WEATHER // graphs, hazards, water and geospatial context
- Current values and hourly/daily forecast timelines with clear forecast-valid-time vs issued-time distinction.
- Recorded actual vs past forecast comparison, explicitly avoiding hindsight mislabeling or comparing unrelated sites.
- Temperature/pressure/rain chance/wind/AQI trend cards and dual-series comparisons (e.g., AQI–humidity, AQI–wind); correlation is descriptive, not causal.
- River stage history with official gauge thresholds and location; rainfall vs river stage with timestamps and basin caution. Tides, buoy/water-level maps, lightning, heat/fire weather and flood impact overlays only when true sources connected.
- Radar/smoke/alert map time control and overlays using existing source owners; event time/provenance displayed. NOAA MRMS/RainViewer and cached frames should not be described as historical archives unless retained.

### COSMOS // astronomical and space-weather instruments
- Moon phase graphic and lunar cycle ribbon; Moonrise/Moonset and Sun/twilight horizon arcs.
- Planet visibility timeline and a sky-facing radial plot: local altitude/azimuth if available, with explicit observer and time. Do not label it as a zodiac wheel.
- True ecliptic alignment wheel and conjunction/aspect angles only after an ephemeris supplies consistent longitudes/coordinate frame and exact timestamps.
- Solar wind speed, IMF Bz, Kp, aurora, flare/X-ray/solar flux trends, solar cycle overviews and timestamp-aligned comparisons; no magnetosphere causal assertions without evidence.
- Meteor, eclipse, ISS and celestial-event timeline with uncertainty, predictive-vs-observed label and location applicability.
- Optional 2D/3D globe, solar system and local sky views using accurate geometry and efficient renderer. Reserve WebGL/OpenGL/external browser integration for an explicitly approved host/prototype, not an automatic dependency.

### EARTH // spatial evidence and event investigation
- Natural Earth basemap plus source-typed and time-filtered USGS, EONET, GDACS, FIRMS, NOAA smoke and compatible meteorological overlays.
- Layer legend, source health, recent update clock, point vs area distinction, clustering/decluttering, selection persistence, and map-linked event inspector.
- Linked timeline/map: move time cursor -> show only valid events, no fabricated intermediate geographies.
- Side-by-side or split overlay comparison and event-to-event links using explicit spatial/temporal association. Dossier/archives remain user-requested saves by existing owners.

### MEDIA // narratives tied to evidence
- Reporting timeline, conservative story family counts, source/publisher comparison, article location mentions on map with "MENTION, NOT VERIFIED EVENT LOCATION" indicator.
- In-station watch/radio/creator controls using existing ownership. Renderer restrictions on video remain explicit; do not promise streams work.
- Map/cross-domain references from news to weather/earth events require explicit source and join rules, not automatic claim that matching places imply a factual causal link.

### MAGICK // high-quality planetary meaning visuals
- Dedicated MAGICK overview with Moon phase ribbon, planetary positions/visibility, change timeline and "What changed?" panel built from REAL ephemerides.
- Planetary alignment wheel: conjunctions, oppositions, trines, squares, sextiles and chosen orbs **only after** positions are computed from a consistent zodiac/ecliptic frame and approach is identified. Present angles visually; any symbolism separately.
- Retrograde motion/activity lanes from time series of geocentric positions. Rise/set or instantaneous alt/az alone cannot determine retrograde.
- Planetary day/hour dial from local sunrise/sunset when the user chooses a defined tradition/calendar and calculations/weekday convention are implemented.
- Optional zodiac/house wheel, aspects matrix, transits and chart comparison once precise ephemerides, tropical-vs-sidereal setting, location/time/zone and house system are explicitly implemented.
- Tarot/spreads, mythic correspondence and personal grimoire/reference library are distinct later data/interactivity projects, not interchangeable with astronomy. Private journal storage requires separate permission and privacy/backup decisions.
- Symbols and art should be compelling, but the displayed positions/timings must be measured or legitimately computed, not artistically placed while labeled factual.

### TOOLS // inspect data feeding all the above
- Per-product latency, staleness, failure, cache vs live, gaps, provenance and archive retention; optional observed reliability trends if the data are retained.
- Source graph diagnostics, render frame budget, and debug inspector, rather than a second collector or system-wide process monitor.
- Extend source catalogue readback without changing its canonical owners.

## 7. MAGICK lens architecture: same astronomy, different interpretations

A user can choose a lens **without recomputing or distorting the observational record**. Proposed lenses:

1. **OBSERVATIONAL (scientific):** physical geometry, coordinate/time information, data quality and provenance. Required base layer.
2. **ASTROLOGICAL:** a chosen explicit school (e.g., modern Western, traditional Western, other sourced tradition), configured zodiac frame/house/orb choices as applicable. Claims labeled tradition-based interpretation.
3. **MAGICAL / CORRESPONDENCE:** correspondences and ritual-use concepts under named sources, editions and lineages. No universalized culture-blind lookup table.
4. **CULTURAL / MYTHIC:** sourced stories, historical context, region/tradition and clearly distinguished modern adaptations.
5. **SECULAR / REFLECTIVE:** optional prompts and archetypal/journaling suggestions, not claims of a natural influence on users.

Per-lens response should include: lens ID, selected school/tradition, claim classification, text/structured symbols, related sky event ID, references with edition/version or source URLs, disagreement/alternative lenses where relevant, provenance and the precise boundary between calculated fact and meaning. Do not force an astrological lens when no school was selected. Selection of lens must not imply it is scientifically verified.

Example structure for a future conjunction visual:
- Observation: "angular separation X degrees at time T in coordinate frame F" ONLY if actual ephemeris computed it.
- Astrological lens: "in named tradition S, an aspect of this configuration is commonly read as ..." with reference.
- Mythic lens: historical association with explicit cultural provenance.
- Reflective lens: journaling idea clearly separated from a prediction.
If there are no real X/T/F values, show NO DATA instead of generating numbers.

## 8. Proposed milestones and definition of done

| Milestone | Deliverable | Dependencies / no-go | Verification |
|---|---|---|---|
| V0 source inventory | audit existing charts, samples, coordinate frames, renderer capabilities, local viewport and current assignments | no speculative rename or new collector | source/owner table, sample fixtures, approved seam |
| V1 graph foundation | pure observation/series adapter + small trend, comparison and event timeline QML primitives | no fake data; bounded downsampling; no new source writer | Node numerical/empty/stale/locale tests, QML smoke and screenshot visual review |
| V2 COSMOS visuals | first space-weather trends, Moon phase ribbon, sun/sky arc using verified data | require genuine values/epochs, keep CS source ownership | numeric source reconciliation and legend/timezone validation |
| V3 MAGICK lens contract | lens registry, sourced reference text schema, explicit unavailable states, context lens switch | no invented chart, no unsourced magical tradition presented as universal | evidence classification tests, curated citation checks |
| V4 planetary graphics | accurate alignment wheel, aspect chart, retrograde lane, planetary hour if approved | precise ephemeris and named conventions required; no faux geometry | reference ephemeris comparison, edge cases incl DST/latitude |
| V5 WEATHER enhancements | range and dual graphs, forecast vs observation, river/gauge and hazards visuals | actual retained series, thresholds and scopes | cross-source/time alignment, no-data/live UI checks |
| V6 EARTH maps | multi-overlay legend, selection persistence, time scrub, map-linked investigations | no duplicate store/auto dossier writes | coordinate tests, source-native mapping, real mouse pan/zoom |
| V7 shared overviews | make each subject's overview a responsive visual launchpad | coordinate with migration/HOME owner | desktop fit, hover/focus/touch, navigation retention |
| V8 terminal reuse | bounded serialized visual model + text/Kitty-compatible renderer when hosting ready | Stage Director/SwayPX readiness, compositor ownership, no browser yank | isolated terminal/compositor tests and approved live integration |

Milestones can proceed in compatible parallel lanes once source ownership is established. V1 should produce a small real-chart demonstration in a dedicated subject surface **before** expanding the component catalog. V4 is blocked on adequate ephemeris precision. Ship narrower proven improvements rather than faking completion of a large visualization set.

## 9. Verification contract for every visualization

- Real input provenance: observedAt vs receivedAt, forecast valid vs issued, cache vs live; source precision and units.
- No-data, one sample, sparse/irregular samples, out-of-order timestamps, duplicate samples, stale cache, invalid numeric values, daylight-saving changes, long gaps, extreme latitudes and timezones.
- Chart axes, labels, comparison scales and sampling tolerance auditable; correlations clearly descriptive and not definitive.
- Hover/focus, keyboard navigation, click-to-inspect, zoom/pan, time scrub, restoration of selected markers; no accidental action on scroll.
- Performance at 1000px station with 160px rail; cap point count/geometry; avoid enormous repaint loops and hidden polling.
- Source access and save ownership unchanged; no implicit external page opening or new Kitty actor.
- QML code/test CI green, followed by **actual local visual/runtime acceptance separately authorized by operator**. Source CI alone never proves visuals render correctly.
- Test the lens label distinction with scientific-vs-symbolic example fixtures and check every reference/version cited.
- Record exact baseline SHA, PR, changed paths, CI state, local test state, screenshots if available, and recovery/rollback instructions.

## 10. Open decisions for the operator (NOT made here)

- Priority among first high-visibility proof: COSMOS space-weather chart, Moon phase ribbon, orbital/alignment wheel, or EARTH map time-scrub.
- Desired sky view: local horizon (altitude/azimuth), geocentric ecliptic astronomy, heliocentric solar-system animation, or multiple toggleable coordinate frames.
- Astro interpretation choices: named schools and source texts; default lens; whether zodiac tropical or sidereal and house system when actual calculations begin.
- Animation budget, CRT visual intensity and 2D vs 3D runtime for 1000px station and later terminal.
- Which time-series/history are retained long enough for 3d/7d graphs; don't imply availability from UI preset alone.
- Map imagery/projection and whether any raster/vector assets need licensing or download.
- If/when personal journaling is introduced: privacy, encryption, deletion, backup, cross-device ownership.
- Terminal handoff acceptance and Stage Director interaction contract.
- Avoid collision with W2 HOME favorites/rotation and other worker's CLASSIC migration.

## 11. Future worker start-here checklist and handoff

1. Read Meta-Apollo-Logos-Syntagma/AGENTS.md and relevant OPERATE Hospital/working/report protocols. Verify patient, room, assignment, owner and permissions. External ChatGPT is not automatically live Hospital registered.
2. Fetch current main HEAD, open Weather/Stage Director PRs and changed paths. Check other worker's CLASSIC transfer/W2 HOME ownership before touching W1 navigation or shared services.
3. Read this document and existing W1/W1r, COSMOS G1, Weather history and map contracts. Inspect current source rather than relying only on this snapshot.
4. Pick ONE bounded V milestone, write its definition of done, identify exact data fields/frames, source owners and read-only adapters. Avoid modifying production or local machine.
5. Implement isolated pure adapter+visual component first; test no-data, stale and provider variance; use authentic fixtures, not invented screenshot data.
6. Integrate only through approved subject pane seam; preserve navigation, terminal, source, cache/archive and MEDIA/CLASSIC boundaries. Use PR with CI. Do not merge/activate without correct operator authority and review.
7. Report with **IMPLEMENTATION, HOW TO USE, VERIFY, WATCH OUT FOR, CHECKLIST, NEXT, DECISIONS**, distinguishing proposed, CI-verified, locally verified and user-accepted states.
8. Update this roadmap or create a milestone-specific handoff with exact commit/PR and recovery pointer. A future worker should never have to reconstruct context from chat excerpts.

## Decision ledger

- **Accepted intent:** More graphs, rich interaction, maps, planetary/solar-system visualization, visual alignments/retrogrades/cycles, multiple lenses of meaning, and eventual terminal-capable reuse.
- **Accepted architecture direction:** Separate source data, pure calculation/geometry, rendering, and sourced interpretation; preserve existing provider/store ownership and SUBJECTS UI grammar.
- **Explicit boundary:** Other worker owns CLASSIC transfer and HOME smart deck; this roadmap covers new SUBJECTS capability, not that migration.
- **Proposed, not yet approved in detail:** Component names, milestone ordering, specific astrological schools, reference texts, 3D runtime, persistence, and terminal backend.
- **Implementation state at writing:** DOCUMENTATION ONLY. No graph, map, ephemeris, lens engine or runtime functionality added by this milestone.
