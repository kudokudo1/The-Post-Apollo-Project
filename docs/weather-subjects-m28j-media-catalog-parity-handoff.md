# Weather Station // M28-J MEDIA publisher and creators catalogue parity

PATIENT // kudokudo1/The-Post-Apollo-Project  
ROOM // Weather Station / CLASSIC → SUBJECTS full capability migration  
STAFF // External Hospital-compatible ChatGPT  
CONNECTION // EXTERNAL; no confirmed live Hospital registration or host attachment  
ASSIGNMENT // Reconcile original seven WATCH/CREATORS source pages to the native MEDIA catalog without claiming embedded video playback  
BASE // `main` `074a050b80f66d66eaa5008ee7e8cc6265880f18`

## IMPLEMENTATION

M28-J confirms the native `StationMediaSubjectPane` uses the existing `StationNewsHub` component for the WATCH and CREATORS routes. The original `StationMediaSubjectPanelPolicy` maps:
- Five publisher catalogue categories `LIVE`, `CONGRESS`, `REPORTS`, `COMPARE`, `SATIRE` to `media/watch/live`, `congress`, `reports`, `compare`, `satire`.
- Saved creators and explicitly requested recent uploads to `media/creators/saved` and `uploads` using the original creator FileView and `station_youtube_feed.py` process. The helper is invoked only by a click on a saved valid creator, with its existing bounded rows and `NO AUTOPLAY` behavior.

The original `StationNewsCatalogPolicy` provides named publisher destinations, access restrictions and editorial category labels; the existing `StationChannelScreen` provides a user-initiated **in-station safe-mode source preview** with CLOSE and an optional *preflight* check.

**Important limitation:** this safe-mode viewer has `playbackAvailable: false` and does **not** play embedded video or launch an external viewer. The in-process Qt WebEngine path was disabled due to real Quickshell SIGABRT behavior. Enabling video requires an independently isolated, approved Stage Director/viewer runtime and separate operator acceptance. M28-J does **not** turn WATCH into a working player. It verifies that every original publisher catalogue control and creator workflow remains reachable in SUBJECTS.

Exactly seven original NEWS controls are marked `M28-J` in `WIRED_IN_SUBJECTS`: `news-live`, `news-congress`, `news-reports-catalog`, `news-compare`, `news-satire`, `news-creators`, `news-uploads`. No new media provider, saved-creator writer, video renderer or terminal actor is instantiated. The earlier M28-D/E/F/G/H/I tests are updated only to preserve exact historical milestone evidence while accepting this later catalogue review.

After M28-J, 96 of 103 historical source-control mappings have reviewed native wiring. The remaining seven are `home-aqi-humidity`, `home-aqi-wind`, `home-quick-conditions`, `home-space-weather`, `ground-source`, `map-source-rack`, and `station-source-badge`.

## HOW TO USE

After merge and separately authorized local deployment: Weather Station → SUBJECTS → MEDIA → WATCH. Choose LIVE, CONGRESS, REPORTS, COMPARE, SATIRE; these are original publisher catalogues, and selecting a destination opens **NEWS VIEWER // SAFE MODE** rather than video playback. CLOSE returns to the catalogue. The same warning is present in the existing screen.

MEDIA → CREATORS offers saved creators, add/remove and explicit upload checks. No autoplay and no extra feed request merely by switching routes. Header INDEX now offers native destinations for the seven catalogue/creator control families rather than opening the CLASSIC NEWS page.

## VERIFY

- `tests/weather/test_index_media_catalog_cutover_m28j.js`: seven exact source IDs and real canonical leaf routes, five populated original publisher categories with access notes, original creator file and explicit upload handlers, same single active NEWS hub, safe-mode viewer closed/opened intentionally with `playbackAvailable: false`, no new source writer, all seven other source controls still pending.
- Dedicated `.github/workflows/weather-subjects-media-catalog-parity-m28j.yml` runs original MEDIA D1 and M28-A/B, M0/M1, W1/W1r and M28-D/E/F/G/H/I regressions.
- Initial CI is **pending at PR creation**. No live Fedora/QtWebEngine, Stage Director runtime or publisher playback certification is claimed.

## WATCH OUT FOR

- VIDEO **NOT CONNECTED** remains a separate feature/hosting blocker; do not paper it over by opening an external browser without operator approval. The accepted MEDIA catalog migration does not constitute functional video playback acceptance.
- Publisher URLs and access notes are catalogue labels, not confirmed live streams or subscription entitlements. C-SPAN and official floor streams may be idle when Congress is not sitting.
- `StationNewsHub` is a loaded component of MEDIA with one active route; do not introduce parallel saved creator FileViews or duplicate feed processes during future refactoring.
- The seven remaining original HOME semantics/source rack/badge controls must be reviewed before CLASSIC deletion. No local QML update, Quickshell restart, Wayland compositor write or live operator acceptance occurred.

## CHECKLIST

- [x] Inspect current source, safe viewer, creator memory/process and open PR collisions.
- [x] Account for five exact publisher catalogue categories and two creator workflows.
- [x] Explicitly protect against false embedded-video acceptance.
- [x] Keep historical source provenance and unrelated CLASSIC shortcuts.
- [x] Add exact tests, CI and durable handoff.
- [ ] Verify final PR-head CI and repair bounded failures.
- [ ] Review/merge and separately authorize operator desktop deployment.
- [ ] Complete HOME semantic and wider SOURCE rack/header parity.
- [ ] Verify live runtime and obtain final operator approval before deleting CLASSIC.

## NEXT

M28-K should reconcile the original HOME QUICK and AQI relationships with the already-present persistent HOME workspace, rather than misrouting them into WEATHER/CURRENT or generic history. Preserve exact HOME watch timers, freshness semantics and source ownership. Next source rack/health and final eight-page CLASSIC teardown require separate acceptance with full original data/source/terminal dependency inventory.

## DECISIONS

Seven-family SUBJECTS-first architecture, no second NEWS viewer, no unverified video playback claim, no new creator fetcher, no shell/browser yank, no local machine operations, no early CLASSIC deletion, and no claim of live Hospital registration or final DONE.
