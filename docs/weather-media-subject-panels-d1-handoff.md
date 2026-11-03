# Weather Station // MEDIA D1 NEWS, WATCH, RADIO, CREATORS

PATIENT // The-Post-Apollo-Project
ROOM // Weather Station / MEDIA Subject Migration D1
DOCTOR // External Hospital-compatible ChatGPT
PROVIDER // OPEN AI // CHATGPT
CONNECTION // EXTERNAL / HOSPITAL-COMPATIBLE, no live registration
ASSIGNMENT // Connect the existing 17 MEDIA leaf routes to actual NEWS, channel, radio and creator surfaces
PHASE // IMPLEMENTATION / CI
STATE // REVIEWABLE, not installed locally

## IMPLEMENTATION

The original subject-first tree now has 17 MEDIA destinations:
- OVERVIEW renders existing NEWS reports and RADIO browsing simultaneously,
  in two vertically stacked full-width bays with independent scrollbars.
  WATCH and CREATORS remain adjacent subroutes; no claim that all catalogue
  destinations are live video feeds.
- NEWS / REPORTS, FILTERS, TRENDS, STORY FAMILIES, MENTIONED LOCATIONS,
  ARTICLE INSPECTOR mount the **original StationNewsHub REPORTS**
  `StationDiscovery` GDELT view and its original cooldown/source.
  The filtered UI retains interactive local source/region/topic/language/time
  controls, article list and viewer. NEWS subroutes select existing report
  sections rather than duplicate fetchers or store datasets.
- NEWS / MENTIONED LOCATIONS shows the source record list and an honest
  instruction to select a headline and request GKG article locations.
  Mentioned locations are not verified event sites. ARTICLE INSPECTOR
  likewise requires explicit headline selection; rendering depends on
  the current terminal/browser host.
- WATCH / LIVE, CONGRESS, PUBLISHER DESTINATIONS, SOURCE COMPARISON,
  SATIRE map to current StationNewsCatalogPolicy sections; cards preserve
  official publisher access notes, subscription caveats, in-station
  attempt and mute-disabled state. Embedded video remains UNVERIFIED
  and no new player has been added.
- CREATORS / SAVED CHANNELS and RECENT UPLOADS reuse the existing
  per-user `weather-news-creators.json` and its explicit user-initiated
  Python `station_youtube_feed.py` channel-feed request. A creator
  catalogue is not an automatic live video service.
- RADIO / STATION DIRECTORY, FAVORITES AND RECENTS, PLAYBACK reuse the
  existing `StationRadio` and `HeadlessMediaController` with the same
  Hi-Fi/MPD server and the same `weather-radio-memory.json`.
  Directory browsing, UUID-based recall and SELECT/LOAD/PLAY versus
  PAUSE/STOP ownership checks remain unchanged.
- `WeatherStationW.weatherContentLoader` becomes inactive while
  SUBJECTS owns the page, ensuring the hidden CLASSIC view cannot hold
  a second NEWS/RADIO component with competing FileViews. It re-creates
  the original view when returning to CLASSIC. Existing terminal/window
  behavior is unchanged outside subject navigation.
- MEDIA NEWS-to-MAP handoff validates nonempty article locations and
  returns to the existing CLASSIC MAP with a copied payload. It does
  not register another map, GDELT geocoder or source watcher.
- Other subject owners WEATHER, COSMOS and EARTH retain their prior QML
  components, provider authorization and archive/dossier policies.

## HOW TO USE

After merge and separately authorized local update:
Weather Station > SUBJECTS > MEDIA > OVERVIEW, NEWS, WATCH, RADIO,
CREATORS. Open a submode from the main rail, then use its existing
buttons. For radio, search or recall an exact station, SELECT, LOAD,
then PLAY only when the existing Hi-Fi controller allows it. Article
locations require selecting a real GDELT headline and requesting
locations from the article viewer.

To exit, click CLASSIC. This recreates the original eight-page
Station implementation and never migrates or duplicates saved data.

## VERIFY

GitHub Actions runs the original M0/M1/M2a/M2b/COSMOS/EARTH and new
MEDIA tests, plus all triggered weather teardown, QML contracts, and
audio/controller contracts. Node/source CI cannot establish live
stream playability, provider freshness, local data persistence, or
Fedora/Quickshell visual fit.

## WATCH OUT FOR

- The news publisher catalog is a directory of destinations. Video
  rendering/embedded playback may be blocked by the current renderer.
- News headline families are conservative local title matching, not
  semantic proof that several publications reported the same incident.
- GDELT article location labels are mentions, not verified event coordinates.
- Creator upload fetching is opt-in and requires the original Python
  helper. The saved UC channel ID validation is retained.
- Radio shares the Hi-Fi MPD transport and protects against playback
  conflicts. No autoplay on searching, restoring, or loading routes.
- Switching between different MEDIA page families unloads the
  previous component. RADIO's saved favorites/recents remain in the
  original file; transient UI state is not promised across exits.
- These changes make no local files/Quickshell changes and do not
  alter Stage Director, SwayPX, MAGICK, storage schema or credentials.

## CHECKLIST

- [x] Canonical AGENTS/Hospital protocol and source/ownership preflight
- [x] Exact 17 MEDIA leaf paths, route and UI policy
- [x] NEWS report source and local analytic sections reused
- [x] WATCH catalog and CREATORS history reused
- [x] RADIO saved directory and transport reused, no new MPD server
- [x] No hidden CLASSIC NEWS/RADIO clone during SUBJECTS
- [x] Dedicated tests and CI workflow
- [ ] Final GitHub CI all green
- [ ] Merge to main (operator standing authorization)
- [ ] Local visual and live-source/operator acceptance

## NEXT

After CI, isolate any compatibility or QML errors on this branch,
merge once verified, then report the exact merge commit and
remaining MEDIA limitations. The next subject would be MAGICK
with separately scoped interpretive and astronomical precision work.

## DECISIONS

GitHub merge authorized upon verified completion. Local machine
modification or runtime activation not authorized. No claim of
live Hospital registration.
