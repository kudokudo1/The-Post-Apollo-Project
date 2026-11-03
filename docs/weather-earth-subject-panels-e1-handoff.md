# Weather Station // EARTH E1 real geography, events and investigation workspace

PATIENT // The-Post-Apollo-Project
ROOM // Weather Station / EARTH Subject Migration E1
DOCTOR // External Hospital-compatible ChatGPT
PROVIDER // OPEN AI // CHATGPT
CONNECTION // EXTERNAL / HOSPITAL-COMPATIBLE, no verified Hospital registration
ASSIGNMENT // Connect EARTH navigation to the existing map and event dossier controls
PHASE // IMPLEMENTATION / CI
STATE // DRAFT until verified

## IMPLEMENTATION

Ten canonical EARTH destinations now use one real `StationDiscovery.qml`
MAP instance. No second event data engine, process, archive writer, tile
network, new provider, or content store has been created.

Subject route mappings:
- EARTH / OVERVIEW and MAPS / EVENT MAP: USGS quakes, EONET, GDACS and
  manually fetched FIRMS; NOAA HMS smoke is available by manual request.
- GEOGRAPHY / BASEMAP: Natural Earth land, borders, state/province lines
  and populated places, preserving wheel zoom and mouse drag-pan.
- GEOLOGY / EARTHQUAKES: shared USGS seismic data, original plotted
  markers and the existing USGS event inspector.
- NATURAL EVENTS / NASA EONET: original event service, map markers,
  event list and detail inspector with existing category filter.
- NATURAL EVENTS / GDACS: original warning service and detail inspector.
- FIRES / NASA FIRMS HOTSPOTS: manual bounded-area VIIRS request using
  existing credential environment, observed hotspot markers and details;
  optional existing manual NOAA HMS smoke polygons in the SAME screen.
  Hotspots are not fire perimeters.
- INVESTIGATIONS / EVENT CONTEXT, DOSSIERS, EVENT ARCHIVE: the existing
  `StationEventContextCard` plus existing M22/M25 dossier review and
  manual archive/revision comparison controls, backed by the original
  `eventArchiveStore` and `dossierArchiveStore`. Nothing is
  auto-saved. An event must first be selected on the map.

The map's one `StationDiscovery` QML instance persists while switching
among all EARTH routes. Selected event, map zoom, map center and archive
pair choices remain in memory. Switching to another top-level subject
unloads it; these are not promised durable across subject exits.

`StationEarthSubjectPanelPolicy.js` is a pure route/allowed-layer/source
policy. EONET, GDACS and the single shared root USGS collector activate
only where admitted. FIRMS and NOAA HMS remain MANUAL. The existing
NEWS GDELT mentions, WEATHER radar and RainViewer do not appear in
EARTH-specific views. Original CLASSIC and WEATHER maps remain intact.

## HOW TO USE

After GitHub merge and separately authorized local installation:
Weather Station > SUBJECTS > EARTH > OVERVIEW.
Choose GEOGRAPHY, GEOLOGY, NATURAL EVENTS, FIRES, MAPS or
INVESTIGATIONS. Move between EARTH routes with breadcrumbs/UP while
preserving event selection and map position.

For a dossier/archive: select a real USGS, EONET, GDACS or FIRMS event
marker, then navigate INVESTIGATIONS > DOSSIERS or EVENT ARCHIVE and
scroll below the map to see the source record, evidence and manual
capture/archive buttons. Without a selected event, there is no dossier.
CLASSIC returns to the original MAP behavior.

## VERIFY

Focused EARTH and prior M0/M1/M2a/M2b/COSMOS Node tests run on GitHub,
plus all triggered Weather teardown, archive and focus contracts.
Offline source-level CI cannot establish visual Quickshell function,
external provider freshness or successful local storage writes.

## WATCH OUT FOR

- No archive schema, retention policy or M25 ownership changes.
- The existing CARD supports explicit operator-initiated archival and
  dossier capture; no effect occurs merely upon selecting an event.
- NASA FIRMS needs the optional already-existing credential; no key
  logged or displayed.
- Do not confuse GDACS alerts with local official warnings; USGS
  quakes are observations, not earthquake predictions.
- EARTH map excludes GDELT NEWS mentions by default because those
  belong to MEDIA. Weather hazards/fire weather remain in WEATHER.
- No desktop activation, Quickshell restart, local Git mutation or
  source installation authorized by this GitHub work.

## CHECKLIST

- [x] Syntagma AGENTS and Hospital protocol preflight
- [x] Source and parallel PR audit
- [x] Ten exact EARTH paths and layer-policy admission
- [x] Single persistent instance of existing event map
- [x] Existing data, dossier and archive source identity preserved
- [x] No unrelated NEWS/radar overlays
- [x] Focused regression test/workflow and handoff
- [ ] CI final head passes
- [ ] Merge to main per operator's standing authorization
- [ ] Live Fedora/Quickshell visual and provider acceptance

## NEXT

Verify and repair only EARTH/Weather regressions, then merge if all
GitHub checks are green and no new ownership collision exists.
After merging, move to MEDIA rather than expanding MAGICK into
unverified ephemerides or schema changes.

## DECISIONS

Operator authorizes GitHub merge once complete. Local activation
remains separately controlled. Do not claim live Hospital registration.
