# Weather StationW // COSMOS C1 live SKY + SPACE subject consolidation

PATIENT // The-Post-Apollo-Project
ROOM // Weather Station / COSMOS subject migration C1
PROVIDER // OPEN AI // CHATGPT (external Hospital-compatible doctor)
ASSIGNMENT // Mount real astronomy and NOAA solar-weather instruments below COSMOS
ROLE // External Hospital-compatible worker, no live Hospital registration
STATE // GitHub draft until CI and merge, desktop not changed

## IMPLEMENTATION

- The canonical six-subject contract stays unchanged; COSMOS has 20
  existing descendant destinations covering astronomy and space weather.
- `StationCosmosSubjectPanelPolicy.js` assigns these destinations to
  the original SKY and SPACE section groups. It does not contain network
  access, storage writes, operations or invented ephemerides.
- `StationSky.qml` now accepts COSMOS subjects using its existing
  sections, preserving WEATHER filtering and the complete CLASSIC page.
  Six original USNO, NASA, ISS and IAU providers are enabled only when
  the selected COSMOS route needs them. The complete CLASSIC SKY view
  still activates them as before.
- `StationSpace.qml` receives a default-empty `subjectRoute` and
  maps its 31 original top-level elements to SOLAR, SCALES, AURORA, etc.
  The seven ancillary SWPC source objects activate on relevant routes.
  Shared `SpaceService` Kp/wind/IMF/flux remains owned by `shell.qml`;
  we do not create a second core SpaceService instance.
- `StationCosmosSubjectPane.qml` renders only the selected original SKY
  or SPACE view. COSMOS / OVERVIEW shows both sets in two full-width
  vertical bays on one screen with independent original star scrollbars.
- COSMOS sun and Moon positions are explicitly existing observational
  or computed products. No zodiac/chart house/aspect/retrograde engine
  has been claimed to exist.
- **Intentional temporary co-location**: SUN / POSITION shows the
  original combined Sun+Moon astronomy panel; SUN / PHOTO LIGHT shares
  the twilight instrument; MOON / POSITION and CONSTELLATIONS use the
  combined USNO celestial-fix panel. They are real functioning
  instruments, but not yet physically split into narrower inspector cards.
- Existing Weather Station subject navigation, CLASSIC eight pages,
  active Kitty terminal/session cutout, news-map linking, and source
  freshness/alert priority are untouched.

## HOW TO USE

Following GitHub merge and an explicitly authorized local update:
Weather Station > SUBJECTS > COSMOS > OVERVIEW.
For details choose SUN, MOON, PLANETS AND STARS, CELESTIAL EVENTS or
SPACE WEATHER. Use breadcrumbs/UP. CLASSIC preserves original SKY/SPACE.

## VERIFY

- M2b upstream PR #1068 merged with 29/29 CI success.
- Focused new C1 tests check every destination, source ownership,
  shared SpaceService bindings, CLASSIC defaults, and no effect writer.
- Full existing Weather Teardown, M2a and M2b, space-weather, QML
  grammar and main-mode checks must pass before merge.
- No live Fedora/Quickshell rendered UI or provider request has been
  verified. Source code/CI checks cannot replace operator acceptance.

## WATCH OUT FOR

- COSMOS / OVERVIEW uses two vertically stacked full-width viewports,
  not two separate top-level modes. Each scrolls independently to retain
  the original instrument width.
- NOAA solar imagery is still manually loaded and the MISS/ISS orbit
  prediction is still geometric rather than a confirmed visible pass.
- SUN / POSITION and MOON / POSITION preserve original combined panels;
  their labels don't imply newly implemented precision ephemeris.
- Source activation is passive when a route is not visible, and COSMOS
  does not write to storage or revive contexts.
- Keep the space-side service instances destroyed when leaving COSMOS
  while CLASSIC SPACE remains an independent existing Loader.
- Do not merge other unrelated PRs or touch local machine state.

## CHECKLIST

- [x] Canonical Syntagma/Hospital/source/ownership preflight
- [x] Route/scope policy for 20 COSMOS destinations
- [x] Filter existing SKY and SPACE sections by route
- [x] Scope 6 SKY / 7 SPACE ancillary fetchers
- [x] Combined overview, source bindings and M1 navigation wiring
- [x] Isolated tests, CI workflow and handoff
- [ ] Latest PR CI fully verified
- [ ] Merge authorized by operator and completed
- [ ] Local visual/provider acceptance

## NEXT

After green CI and permitted merge, report exact PR, commit, and
unverified desktop behavior; then scope EARTH without colliding with
existing dossier/archive ownership.

## DECISIONS

The user explicitly authorized GitHub merges after completion in this
conversation. Local Fedora writes, Quickshell restarts and production
activation were NOT authorized. No live Hospital registration claimed.
