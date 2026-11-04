# MAGICK M5k // Adjustable UTC Day Jump

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather StationW / MAGICK celestial history navigation
ROLE // External Hospital-compatible worker; live registration not verified
ASSIGNMENT // Replace hard-coded 30-day navigation with editable day count and plus/minus calibrators
BASE // main ec795d82047d762981d305d19b1b6185c50218db
BRANCH // feat/weather-magick-adjustable-day-step-20261104
SCOPE // MAGICK source service, pure query policy, reference panel, tests, workflow, handoff
PERMISSIONS // GitHub only; no local Fedora modifications, merges, restarts, or production activation

## IMPLEMENTATION

The operator requested an adjustable day jump for exploring past/future rather than fixed 30-day controls. This patch keeps the current UTC target-date row and TODAY button. Its left/right buttons now show the selected jump, and a compact new JUMP STEP / D row allows numeric input (1 to 3650 days) with adjacent −1 and +1 calibrators.

- services/weather/CelestialVisualQueryPolicy.js: DEFAULT_DAY_STEP=5; strict parseDayStep and adjustDayStep with bounded positive integer input. Invalid values fail instead of producing unbounded or fractional date shifts.
- services/weather/CelestialVisualService.qml: Shared root-owned dateStepDays with setDateStepDays, adjustDateStepDays, jumpDate(±1). Only using a date arrow changes dateOffsetDays. Editing the jump size does not invalidate data, change graph sampling, or start JPL calculation. The calibration survives MAGICK route changes and TODAY while the single root source remains alive.
- widgets/weather/StationMagickSubjectPane.qml: Dynamic day-arrow labels, editable Gohu TextInput with cyan/magenta focus border, −1/+1 buttons, input hints and explicit valid range; Enter/blur commits, ESC restores previous value and consumes the key, arrow-up/down adjust by one. Increased Flickable contentHeight to 620 to accommodate the additional 27px row.
- tests/weather/test_magick_adjustable_day_step_m5k.js: bounded date-step parser, UTC math, leap/DST, source ownership, new QML handlers and no-query side effects.
- tests/weather/test_magick_celestial_query_m5c.js: original fixed-30 test updated to verify new dynamic backward/forward navigation and calibration without discarding original M5c date, pair, span and source contracts.
- .github/workflows/weather-magick-adjustable-day-step-m5k.yml: new unit tests plus M5b/M5c/M5e/M5f/M5g/M5h/M5i/M5j/HOME regressions.

No new Process, timer, ephemeris download, provider, storage, source body, interpretation lens or locale/clock engine is added.

## HOW TO USE

After separately authorized merge/local deployment:

1. Open SUBJECTS > MAGICK > ASTROLOGY.
2. On the JUMP STEP / D row, press −1 or +1 to change the day jump incrementally, or edit the numeric field directly to 1, 5, 10, 30, etc. Press Enter or click away. ESC cancels an edit without closing Station.
3. Press ◀ nD to move n UTC days into the past or nD ▶ for the future. TODAY returns to the current UTC day without resetting the day-step setting.
4. Press CALCULATE to load JPL positions for the new date; graph sampling cadence and 14/29/90-day SPAN control remain independent.
5. Within an already calculated chart, the separate glowing timeline thumb still scrubs measured M4 samples.

The step defaults to 5 at first instantiation, remains set while browsing MAGICK routes, and is not persisted across full Quickshell restarts. Persistence belongs in a separately approved Settings++ task if requested.

## VERIFY

Run from repo root:

    node --test tests/weather/test_magick_adjustable_day_step_m5k.js
    node --test tests/weather/test_magick_celestial_query_m5c.js

CI also rechecks historic MAGICK navigation/data contracts, the single root-owned JPL Process, and unchanged HOME behavior. Automated tests do not prove native QML key focus, text editing, mouse clickability or small-window geometry. These require operator testing after merge and deployment.

## WATCH OUT FOR

- This calibrates day navigation only, not the M4 ephemeris sampling interval or astronomical precision.
- A new target date clears the old calculated view; CALCULATE must still be clicked.
- The 3650-day UI offset limit does not guarantee the JPL kernel covers every possible date.
- No default-time change is silently injected into interpretive traditions, personal observations or other Weather routes.
- The M28-V CLASSIC retirement PR is concurrent, separately owned and untouched here.
- No installation or local Quickshell restart has occurred through this GitHub work.

## CHECKLIST

- [x] Current main and M28-V ownership preflight
- [x] Adjustable numeric days with plus/minus one calibrators
- [x] Dynamic date arrows, TODAY, Escape-safe edit
- [x] Bounds and source integrity
- [x] Isolated tests, CI, recovery handoff
- [ ] Final PR-head CI verified
- [ ] Operator acceptance and authorized merge
- [ ] Native keyboard, pointer, compact-size layout test

## NEXT

After M5k review and acceptance, return to the already approved MAGICK research/specification checkpoint: astronomical relationship/event categories, Western tropical source research, Hellenistic second, Vedic third, and NOW-centered linked history/future visualization. Do not expand M5k into new display modes or unapproved interpretations.

## DECISIONS

A small editable UTC day-jump stepper is more useful than fixed ±30-day buttons or reusing the graph slider. It retains existing source ownership and operator authority. Changes to desktop, installation, merge or production need their normal separate approvals.
