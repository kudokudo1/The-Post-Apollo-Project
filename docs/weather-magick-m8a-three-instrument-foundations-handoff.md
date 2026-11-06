# 🏥💜 MAGICK M8a // Planetary Clock, Natal Reference and Source Atlas

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station > MAGICK > Three instrument foundations (M8a)
STAFF // DOC, OpenAI ChatGPT, external Hospital-compatible and not live-registered
ASSIGNMENT // Build the source-driven visual starting points in the operator's three references
SCOPE // MAGICK-only presentation, pure geometry policies, tests and one CI workflow
BASE // main at 25add6078cb968982eb60992f67b53252da09d46 at branch creation
PERMISSIONS // Bounded GitHub code/tests/docs. No local Fedora writes, merges, or production activation.

## IMPLEMENTATION

### Advanced Planetary Timing

The existing M6d local-forecast planetary-hours policy remains the single timing source. Added StationMagickTraditionalDialPolicy.js with a strict 24-hour contiguous source contract. Actual sunrise-to-sunset and sunset-to-next-sunrise **civil-clock intervals** determine the angular widths of the 24 clock wedges. The historical Chaldean ruler names stay independently labeled and do not purport to cause astronomical events.

StationMagickTraditionalClockPane.qml draws the circular clock with source hour labels, date navigation, pointer-centered mouse-wheel zoom, +/- buttons, fit, drag pan and accurate inverse-transform hit testing. StationMagickTimingAtlasPane.qml can switch CLOCK / LANES without duplicating the weather source. The original lane histogram remains available.

### Complete Astrology Charts

Added StationMagickNatalWheelPolicy.js and StationMagickNatalChartWheelPane.qml as a chart renderer and strict payload contract. Zodiac signs are a fixed *reference wheel*. 10 exact-source planetary target labels (including JPL barycenters accurately named), source-provenanced UTC epoch, precise zodiac model, 12 house cusps, measured Ascendant and MC are required before planetary placements, aspect lines or houses are drawn. The policy validates whole-sign or equal-house cusp definitions and requires a named ayanamsa if using sidereal coordinates.

The existing Astrology screen gains NATAL / PAIR toggle. The source for a full birth chart is **not implemented**, so the natal view truthfully says FULL NATAL CALCULATION NOT CONNECTED instead of fabricating houses or using the current selected-two-body JPL data as a complete birth chart. EVENT SETUP remains session-only.

### Symbolism and Reference Atlas

Added StationMagickCorrespondenceAtlasPane.qml as a responsive interactive source-attributed atlas from the already-identified 1651 English Agrippa Book I chapters XXIII–XXIX corpus. Select one of seven traditional planets, metals/stones/plants, then an actual listed term. The graph highlights only documented associations shared within that edition, with chapter and source attribution. Magnification, drag pan, fit and source selection work without fetching new content. StationMagickSymbolismPane.qml switches ATLAS / NETWORK; prior search and relationship view remain.

## HOW TO USE

After separately authorized merge and native deployment:
- Weather Station > MAGICK > LENSES / PLANETARY TIMING > CLOCK. Choose day, select clock sector, zoom with mouse wheel +/- and pan by dragging. LANES returns to the histogram, CLOCK goes back.
- Weather Station > MAGICK > ASTROLOGY > NATAL. Zodiac structure can be inspected. Houses, planets, ASC/MC and aspect lines remain absent until the independently verified full chart calculation is connected. PAIR returns to the existing working two-body JPL graph; EVENT SETUP remains available.
- Weather Station > MAGICK > DIVINATION > SYMBOLISM > ATLAS. Choose historical planet, category and term. Select another planet in the orbit; NETWORK returns to existing searchable catalog.

## VERIFY

- tests/weather/test_magick_three_instruments_m8a.js checks the source-derived unequal 24-hour interval wedges, inverse source sector hit-tests, no fabricated or mislabeled natal data, verified full-chart payload gating, exact historical Agrippa associations and QML interaction/route contracts.
- .github/workflows/weather-magick-m8a-instruments.yml invokes new M8a tests and preexisting M7a/M6d tests.
- Additional native Quickshell interface and mouse testing is mandatory; Node/static tests do not verify actual pixel fit, QML import compatibility, or source engine scientific correctness.
- A new full-chart backend with a validated sidereal reference, Ascendant/MC astronomical method, JPL position source and privacy control remains a later separately approved milestone.

## WATCH OUT FOR

The three instruments are at different functional depths: planetary clock is source-driven and interactive; symbolism atlas is real historical-data-driven but covers only one book/edition; natal is an honest, structurally ready renderer, not an operative complete birth chart.
The forecast timing source supplies civil local sunrise/sunset labels, not per-event UTC offsets, so DST-transition **elapsed** durations remain unverified. Do not claim more.
Names, plant categories and associations are tradition-specific, not universal, scientific, medical or causal effects.
No birth information is saved; no new process, network feed, global calendar writer, local machine change or merge.
The COSMOS lunar/solar instrument, M7c zoom corrections, Settings global location, and personal grimoire storage are untouched.

## CHECKLIST

- [x] Read Syntagma AGENTS and Hospital protocol; check current main and open MAGICK PRs
- [x] Isolated M8a branch and scoped source-only paths
- [x] Source-derived circular planetary hour display; clock / lanes interaction
- [x] Strict provenance-aware natal wheel renderer contract, no fake houses/planets
- [x] Agrippa atlas with source-grounded selectable relationships
- [x] Regression tests and dedicated CI workflow
- [ ] PR-head CI success and independent review
- [ ] Operator merge decision
- [ ] Authorized local deployment, native geometry/interaction acceptance
- [ ] Separate full natal chart numerical engine and validated observer methodology
- [ ] Broader symbolism corpus with source-by-source review

## NEXT

Review CI and correct any regressions before requesting independent verification. Native desktop review should check circular dial legibility and all hover/drag/zoom targets. Then implement the full natal chart numerical backend as a separate source/permission assignment instead of faking planets from two-body snapshots.

## DECISIONS

Reference examples inform information hierarchy, not fabricated astronomical data or generic art posters. Zoom/fit/pan are first-class controls. Preserve existing screens, source/provenance, ownership boundaries, and the operator's merge/acceptance authority.
