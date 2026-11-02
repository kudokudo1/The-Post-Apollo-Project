# Weather StationW // Subject Browser M1 integration handoff

PATIENT // The-Post-Apollo-Project
ROOM // Weather Station / Subject Navigation M1
CONNECTION // External / Hospital-compatible
ASSIGNMENT // Add a reviewable six-subject index to the existing station, without migrating source panels
STATUS // Draft, no local activation or operator acceptance

## What changed

- `WeatherStationW.qml` now has a default-off `subjectNavigationOpen` flag and a SUB-JECTS/
  CLASSIC rail action. When enabled by the user, six approved subject roots appear in the
  existing 160px rail.
- `StationSubjectRail.qml` owns the six new subject buttons; WeatherStationW keeps its one canonical main-mode delegate.\n- `StationSubjectNavigator.qml` shows nested paths, breadcrumbs, submode entry, and
  explicit **OPEN [CLASSIC PAGE]** handoffs to existing screens. Navigation uses
  `StationSubjectNavigationPolicy.js` from M0 rather than a second route registry.
- `StationSubjectNavigationPreviewPolicy.js` enumerates which classic pages currently
  contain sections mapped to the selected path.
- Tab cycles the six subjects while the browser is visible; Up/Down selects a child;
  Enter opens it. Esc returns to classic rather than closing the Station.
- It preserves last selected route for each subject within the running QML object.

## How to use after merge and separate local activation

Open Weather Station. Select SUBJECTS at the bottom of the left rail.
Choose WEATHER, COSMOS, EARTH, MEDIA, MAGICK or TOOLS; navigate submodes and breadcrumbs.
Choose OPEN [CLASSIC PAGE] to use existing live controls.
Select CLASSIC to return to the eight established pages.

This is a navigation index, **not** the promised finished subject-first data layout.
The old pages are still mixed. The browser labels incomplete routes as
`SPEC_ONLY` and does not claim astrology or magick calculations exist.

## Explicitly preserved

- All 8 classic page IDs, loader destinations, status source owners and refresh cadence.
- No new fetcher, storage writer, persistence key, archive or data migration.
- Official NWS alerts stay higher priority than index status in the header.
- Running contextual Kitty cannot be obscured by the subject browser;
  the toggle is unavailable unless terminal state is IDLE.
- Weather-to-map NEWS handoff, Quickshell keyboard acquisition/escape,
  terminal actor identity and closing semantics remain unchanged for classic mode.
- Preview-only UI does not claim that subject page panels are migrated.
- Existing M22/M23 dossier admissions and independent M24 PR are untouched.

## Verification

CI runs the M0 Node route contract and M1 browser/source-ownership contract.
Existing Weather Teardown contracts and Meta Apollo Grammar run on
`WeatherStationW.qml` changes.
No graphical Quickshell, in-situ browser, or manual accessibility verification has
been done on the operator's Fedora machine.

## Remaining UI integration work

1. Operator review of six-subject rail placement and nested navigation interaction.
2. Migrate individual WEATHER panels into actual submode components and
   inspector panels, preserving official NWS fixed target and provider lifetimes.
3. Move COSMOS moon, sun and planet panels separately from SKY forecasts;
   keep all space-weather products together under COSMOS.
4. Move EARTH events/dossiers from the multi-domain MAP without breaking M23/M24.
5. Keep MEDIA NEWS/Radio controls together while reusing the existing map renderer.
6. Attach future MAGICK interpretations to the shared astronomic ephemeris,
   with symbolic conventions explicit; do not relabel measurements as proof.

## Rollback

The M1 PR is stacked on M0 and remains draft pending review. It adds no
machine state or stores. Revert M1 commits or do not merge; default-off state
means existing Weather Station remains classic until opt-in.
