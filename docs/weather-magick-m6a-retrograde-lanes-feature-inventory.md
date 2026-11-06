# Hospital // MAGICK M6a Retrograde Rate Lanes

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station Visual Intelligence / MAGICK feature expansion
ASSIGNMENT // M6a bounded source-verified retrograde activity instrument
STAFF ROLE // Nurse 2 · External Hospital-compatible; no live registration verified
PHASE // Draft GitHub implementation; CI and native acceptance separate
BRANCH // feat/weather-magick-m6a-retrograde-lanes-20261106

## IMPLEMENTATION

The operator approved continuing MAGICK feature development with more graphs and visuals. Inspected Syntagma AGENTS, Hospital Agent Protocol, current main MAGICK sources, 2026-11-03 roadmap and open PR searches. No open Weather/MAGICK PR was returned at initial audit.

Existing source-verified modes are ZODIAC, MOTION, ASPECTS, RELATIONS, NETWORK CHORDS/DEPTH and HELIO. Feature families for planetary hours, transits, interpretation lenses, sourced correspondences, tarot and personal grimoire remain incomplete or placeholders.

M6a adds a dedicated RETRO chart to the existing celestial instrument. It consumes exclusively the existing source-validated M4/Skyfield pair of apparent geocentric true-ecliptic-of-date longitude rate series and UTC times. No second request, collector, store, timer, process, fabricated body or new source.

The per-body lanes render discrete rate bars: cyan direct, magenta retrograde, yellow at sampled zero. Orange sign-change brackets identify the interval between two measured samples; the exact station UTC is NOT inferred. Zero-rate baseline, selected UTC cursor, measured degrees-per-day, and original time drag/wheel/click controls are preserved. Adds RETRO alongside current chart modes; INDEX > ASTROLOGY > RETROGRADES now selects it by default instead of the generic MOTION curve. Main menu layout, JPL source logic, HELIO and current V5 styling remain unchanged.

## HOW TO USE

After authorized merge and separately approved Fedora installation: Weather Station > MAGICK > ASTROLOGY > RETRO. Or INDEX > ASTROLOGY > RETROGRADES. Click CALCULATE using existing configured JPL source, select an actual body pair/date/span, and inspect geocentric longitude rate lanes. Choose Mercury/Sun to explore possible retrograde windows, but data may show no reversal in the selected time span. Click to lock source UTC, wheel zoom or drag the time plot as before.

## VERIFY

New tests/weather/test_magick_retrograde_lanes_m6a.js covers actual source UTC and degrees/day, direct/retrograde sign, irregular time axis, exact source pairing, unknown station instant, malformed/duplicate/invalid source refusal, QML mode/route hookups and absence of extra actors. The existing Weather COSMOS JPL network workflow includes this test and preceding M4/M5 and V4a–V5b regressions. Verify exact PR head before declaring CI green. Native widget fit and click tests remain required.

## WATCH OUT FOR

This is geocentric apparent longitudinal rate, NOT physical heliocentric orbital speed. Station brackets are source time windows, NOT precise calculated station instants. A pair can legitimately contain no retrograde samples. Do not invent magical influences or conflating symbolic tradition with astronomy. A seventh compact chart button needs native GohuFont and narrow-width review.

No local Fedora mutation, Quickshell restart, PR merge or live Hospital registration. Temporary MAGICK worker ownership should be reconciled on their return.

## CHECKLIST

- [x] Reconstruct current source, ownership and existing features
- [x] Add source-only retrograde chart policy and render mode
- [x] Wire existing retrograde deep route to new instrument
- [x] Add strict regression + existing workflow
- [ ] PR-head CI and integration review
- [ ] Operator-authorized merge and separate local installation
- [ ] Native inspection and operator final acceptance

## NEXT

Verify M6a PR and retain a draft for review. Next bounded chart candidate: M6b aspect comparison matrix from existing M4 pair, not a fictional natal transit chart. Then plan named-tradition planetary hours, sourced correspondence lenses, licensed tarot decks, and grimoire reference/journal privacy and storage contracts separately. Avoid simultaneous changes to owned source providers or global MAGICK menu.

## DECISIONS

Preserve operator-accepted V5 readability and defer global Visual V3 restyling. Build remaining MAGICK capabilities as bounded, source-truthful milestones with clearly separated astronomical measurements and cultural/interpretive conventions.
