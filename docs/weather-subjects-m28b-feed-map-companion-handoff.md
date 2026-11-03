# Weather Station // M28-B MEDIA News Feed and EARTH Map Companions

**PATIENT:** `kudokudo1/The-Post-Apollo-Project`  
**ROOM:** CLASSIC → SUBJECTS existing-capability migration  
**STAFF:** External Hospital-compatible ChatGPT worker, not live Hospital registered  
**ASSIGNMENT:** Correct NEWS/EARTH presentation shown by operator screenshots without new providers, data owners or page-for-page copying.  
**BASE:** `main` at `740df69cef0d607e4c14329426bfe7fda5f7ae9e`, after merged M28-A PR #1108.  
**SCOPE:** MEDIA NEWS route display order, EARTH compact source-context list, same existing row/inspector, tests/CI.

## IMPLEMENTATION

The operator's screenshots showed two different source types:
the visible `Tropical Cyclone Muraku` record under EARTH is a
**NASA EONET event**, not a GDELT news report. MEDIA's NEWS view
showed the GDELT filters and analytic sections preceding the
headlines. GDELT also reported `REQUEST HELD // PROVIDER COOLDOWN`,
so the screenshot did not prove that a live news article batch was
available. Merely duplicating the news feed would not resolve
provider rate limiting or section ordering.

The corrected subject split is:

- **MEDIA → NEWS → REPORTS**: existing source request and local
  filters immediately followed by **NEWS HEADLINES // CURRENT FILTERED
  BATCH**. The original full list card renderer, exact-headline
  grouping, native in-station article inspector and per-article
  GDELT GKG "SHOW ON MAP" flow remain. The **TRENDS** and **STORIES**
  analytics still exist, but each now lives under its own dedicated
  sibling route, rather than burying the main report list.
  HEADLINES also remains accessible from FILTERS, LOCATIONS and VIEWER
  routes without a second fetch.
- **EARTH → MAPS → EVENT MAP**: the map uses a short selection-aware
  **EONET EVENTS IN VIEW** list with at most four existing real
  records and the chosen event promoted to the top. Pan/zoom modifies
  which EONET events are in view. The *full* original EONET record
  list still lives under **EARTH → EVENTS → EONET**. USGS, GDACS and
  FIRMS markers and dossier handling remain independent.
- **EARTH → MAPS → article context**: when MEDIA explicitly hands off
  an article's GKG place mentions (M28-A), EARTH offers a small
  **ARTICLE MENTIONED PLACES** companion. Clicking one of its
  location buttons selects the existing magenta map mention and
  refocuses the same map. Article title and "NOT VERIFIED EVENT
  LOCATIONS" caution remain visible. There is no second GDELT
  fetcher and no claim that the mention is a disaster/event.
- **CLASSIC**: original NEWS/Map route and display source remain in
  place until full SUBJECTS parity and operator cutover acceptance.

The original `StationDiscovery` list-card QML delegate was
extracted into one reusable `Component`, mounted in the appropriate
subject-specific position. This is **two presentations of the same
existing source row renderer**, not duplicated data collection.

The new `StationMapCompanionPolicy.js` is pure JS: filter invalid
coordinates, admit only EONET rows in the active geographic viewport,
prioritize the actually selected event (even when off-screen), then
cap the map's companion to four. This does **not** change the full
EVENTS route, the original provider event IDs, polling, cache
or dossier writer. No auto-archive/dossier action is added.

## HOW TO USE

After PR review/merge and separately approved live deployment:

1. SUBJECTS → MEDIA → NEWS → REPORTS: source request, search/topic,
   source/language/time/region filters, then the headline list.
   Click a headline for the original in-station article inspector.
2. Use MEDIA → NEWS → TRENDS or STORIES for their existing analysis.
   These are not an alternative news collector.
3. From an article inspector with GKG place mentions, SHOW ON MAP
   routes directly to SUBJECTS → EARTH → MAPS, as verified in M28-A.
4. EARTH shows its usual event map plus a small EONET list reflecting
   the map and selected event, and, when present, the transferred
   article's place list. Click a place to inspect and focus without
   returning to MEDIA. For all EONET records, use EARTH → EVENTS → EONET.

If GDELT is rate-limited, the headlines area now shows an immediate
provider-cooldown message rather than leaving an apparently missing
feed. It does not bypass provider limits.

## VERIFY

Dedicated GitHub workflow
`.github/workflows/weather-subjects-news-map-companion-m28b.yml`
runs a pure M28-B policy/layout contract, existing MEDIA D1 and
EARTH E1 contracts, M28-A source-native handoff regression, and the
actual Fedora 44/Quickshell/Xvfb EARTH article-marker/clear test.
**CI is pending at handoff creation.** Inspect the exact final PR
HEAD and any failures before reporting the milestone as verified.

## WATCH OUT FOR

- **No shared live GDELT feed inside EARTH** is introduced. Its article
  companion displays the *selected MEDIA article's extracted places*,
  which are already available from M28-A. Browsing a different news
  article still happens in MEDIA. A fully searchable, synchronized
  mini headline feed inside EARTH would require a separately scoped
  source lifetime/ownership refactor, rather than a second HTTP
  collector or a silently duplicated service.
- The GDELT provider cooldown visible in the screenshot is a
  separate data-availability concern; changing UI order cannot make
  withheld article records appear.
- `StationMapCompanionPolicy.previewEonet` is a view projection. It
  never changes provider identities, source timestamps, selection
  capture admission, or the original archive.
- The actual user workstation, live data, font/scroll geometry, and
  Fedora Silverblue/Sway were not modified or visually verified by CI.
  M28-A's native marker test is not a substitute for direct operator
  acceptance of this new feed-first ordering.
- The final deletion of CLASSIC is still gated on complete capability
  parity, including TOOLS terminal ownership and old INDEX shortcuts.

## CHECKLIST

- [x] Reconcile operator screenshots with actual EONET vs GDELT source
- [x] Confirm M28-A PR #1108 merged and current GitHub head/owners
- [x] Preserve shared NEWS source, filters and viewer
- [x] Move headlines ahead of trends/stories using original row renderer
- [x] Retain dedicated TRENDS / STORIES destinations
- [x] Compact EARTH EONET map list; full record list under EVENTS
- [x] Add selected-article place companion using existing map inspector
- [x] Add pure policy tests + native M28-A continuity regression
- [ ] Latest-HEAD CI accepted
- [ ] Operator merge
- [ ] Fedora/Sway visual and input verification
- [ ] Remaining CLASSIC capability migration and final deletion

## NEXT

Review M28-B CI. Fix only scoped source/geometry issues. Do not build
new news providers, add duplicate collectors, change data persistence,
expand into unrelated graphs/features, or delete CLASSIC early.
After the operator verifies feed-first usability, continue migrating
existing TOOLS terminal and INDEX dependencies to their proper
SUBJECTS homes.

## DECISIONS

Remote feature branch/PR only. No local user filesystem writes,
`git pull`, shell restart, production activation, archive mutation,
provider cooldown bypass, duplicate service, automatic dossier save,
PR merge or live Hospital registration.
