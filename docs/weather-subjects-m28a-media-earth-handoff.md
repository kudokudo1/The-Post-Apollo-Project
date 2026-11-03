# Weather Station // M28-A MEDIA → EARTH Subject Cutover

**PATIENT:** `kudokudo1/The-Post-Apollo-Project`  
**ROOM:** Weather Station / CLASSIC → SUBJECTS Migration  
**STAFF ROLE:** External Hospital-compatible repository worker, not live Hospital registered  
**ASSIGNMENT:** Transfer existing NEWS mentioned-location map inspection into SUBJECTS EARTH without copying the original CLASSIC MAP page one-to-one.  
**BASE:** `main` at `2709ee862fa11d75ec04c0af33152cb02786af6a`.  
**SCOPE:** MEDIA article handoff → EARTH map overlay, marker inspector, clear/focus, one EARTH workspace map instance. No production deletion.

## IMPLEMENTATION

The existing MEDIA `StationNewsHub` and GDELT Article Location extractor
still own the article, selected report and source-native location rows.
No second GDELT provider is created.

Previously, a NEWS "SHOW ON MAP" action inside SUBJECTS emitted
`newsMapRequested` through `StationMediaSubjectPane` /
`StationWorkspaceSurface` / `StationSubjectNavigator`, then the
`WeatherStationW.qml` root handler **closed SUBJECTS and activated the
CLASSIC MAP**. `StationDiscovery.qml` had the real GDELT mention marker,
FOCUS/CLEAR controls and inspector, but its `earthMapOnly` guard
excluded that layer.

M28-A transfers this existing interaction across **subject boundaries**:

- MEDIA keeps article discovery, source filtering, article inspector and
  extraction of **mentioned** places.
- `StationSubjectNavigator.showNewsMentionsOnEarth(payload)` validates
  that at least one coordinate row is plottable using the existing
  `StationMapProjectionPolicy.plottable`, defensively copies the packet,
  navigates to canonical `earth/maps/overview`, and retains the
  transient article-location context in the owning SUBJECTS navigator.
- `StationWorkspaceSurface` and `StationEarthSubjectPane` pass that
  context into their **existing** `StationDiscovery` EARTH renderer.
  The existing magenta mention markers, native click inspector,
  `FOCUS NEWS`, and `CLEAR NEWS` controls now work inside EARTH.
- The normal EARTH workspace is the only active pane when INDEX is
  closed. The original nested INDEX EARTH preview is gated by
  `indexOpen` so it does not create a second active map to compete
  with the workspace.
- The original WEATHER-only radar/smoke MAP still excludes article
  mentions. The existing EARTH USGS/EONET/GDACS/FIRMS event selection
  and M23/M25 dossier identity contracts are unchanged.

GDELT article mentions remain **not verified event locations**, with a
visible MEDIA → EARTH caution on the EARTH map. They are not included
in `selectedContextSourceId` and cannot automatically become
provider-native disasters, dossiers, archive records or source history.
No FileView writer, background fetcher or new map renderer was added.

Existing CLASSIC NEWS→MAP behavior remains temporarily intact **only
for its own CLASSIC interface**, while SUBJECTS no longer routes there
for the MEDIA news mention handoff. This is a migration increment;
CLASSIC may be deleted only at the final operator parity gate.

## HOW TO USE

After operator review, merge and separately authorized local deployment:

1. Open Weather Station → SUBJECTS → MEDIA → NEWS → MENTIONED LOCATIONS.
2. Select a report, obtain its GDELT/GKG mentioned locations, and
   activate its existing **SHOW ON MAP** action.
3. The station remains inside SUBJECTS and switches to
   EARTH → MAPS → EVENT MAP, focused on the article's location markers.
4. Click a magenta marker for the existing location inspector. Use
   FOCUS NEWS to refit and CLEAR NEWS to dismiss that article overlay;
   the EARTH event layers, map and dossier controls remain independent.

If there is no valid plottable coordinate, the handoff refuses to
navigate rather than opening an empty map or inventing coordinates.

## VERIFY

The native Fedora 44 test
`scripts/weather/verify_media_earth_mentions_fedora_m28a.sh` uses the
actual `StationSubjectNavigator`, real `StationEarthSubjectPane`,
real `StationDiscovery`, temporary Xvfb and native pointer events.
Synthetic data enters the same Navigator subject route function; no
network provider or user HOME is involved. It asserts
`earth/maps/overview`, an article mention marker, native click
inspector with no selected provider-native event, clear/reset without
leaving SUBJECTS, and no archive/dossier file writes.

Pure source and route tests:
`node --test tests/weather/test_media_earth_mentions_cutover_m28a.js`.
Regression contracts rerun EARTH E1, MEDIA D1, and W1.

**At documentation creation, exact-HEAD GitHub CI has not yet been
observed; do not report success until the native and regression jobs
finish.**

## WATCH OUT FOR

- Do not promote GDELT article mentioned places to verified disaster
  or event coordinates. EONET/GDACS/USGS/FIRMS native provider identities
  and dossier save stay separate and manual.
- This does not introduce a second NEWS, map, terminal, cache, archive,
  radio or Article Location service. Only transient view context is
  handed from MEDIA to EARTH.
- EARTH and the nested INDEX previously could both construct an EARTH
  pane on the same route. M28-A gates only the EARTH index preview.
  Other old preview panes need their own cutover parity review.
- If EARTH is hidden after the handoff, its map instance may be
  unloaded. The Navigator retains the article-location *context* for
  the current station session and rehydrates a displayed map when
  returning to EARTH. Map viewport/selected marker persistence across
  unrelated subjects is a separate issue.
- CLASSIC is not removed in this PR. It remains a temporary parallel
  UI until all SUBJECTS capabilities, source lifetimes, terminal owner,
  and final desktop acceptance can survive without it.
- Native CI uses disposable X11 and synthetic records. Final Fedora
  Silverblue/Sway visual/input acceptance and real feeds remain
  operator-owned.

## CHECKLIST

- [x] Re-read Syntagma AGENTS / OPERATE and current GitHub ownership
- [x] Trace MEDIA news mention extraction and old CLASSIC fallback
- [x] Route MEDIA → EARTH through canonical SUBJECTS navigation
- [x] Reuse existing EARTH map marker/focus/inspector/clear machinery
- [x] Preserve news-vs-provider-event semantics and dossier isolation
- [x] Gate duplicate EARTH index preview in normal workspace
- [x] Add route contracts, E1 adaptation and disposable native harness
- [ ] Final-HEAD CI verified
- [ ] Operator review / merge
- [ ] Native Fedora/Sway final visual and input acceptance
- [ ] Remaining CLASSIC dependencies migrated and final deletion accepted

## NEXT

Review exact PR-head CI; fix only proven M28-A issues. Continue a
capability-by-capability CLASSIC → SUBJECTS transfer, favoring
source-specific homes (WEATHER atmospheric/radar, EARTH spatial,
COSMOS sky/space, MEDIA news/radio, TOOLS terminal) rather than cloning
eight original pages. Follow with TOOLS terminal handoff and remaining
legacy INDEX source jump removal after scoped review.

## DECISIONS

No user-local edits, Quickshell restart, live production activation,
new data provider, source-writer ownership changes, automated dossier
capture, PR merge or final CLASSIC deletion in this milestone. Original
services and user acceptance remain protected.
