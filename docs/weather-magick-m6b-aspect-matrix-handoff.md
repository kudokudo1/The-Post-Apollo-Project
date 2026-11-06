# 🏥💜 Hospital // MAGICK M6b Aspect-by-UTC Matrix

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station Visual Intelligence / MAGICK feature expansion
ASSIGNMENT // M6b source-grounded sampled pair aspect comparison matrix
STAFF ROLE // Nurse 2, external Hospital-compatible; live registration unverified
PERMISSIONS // Isolated GitHub branch and draft PR; no merge, no local writes, no runtime reload
BRANCH // feat/weather-magick-m6b-aspect-time-matrix-20261106
BASE // Current main at branch creation; M6a PR #1347 confirmed merged in commit e41daf84f013b243e70753ea71832be439f6fb35
CHECKPOINT // Draft feature awaiting exact-head CI and native operator acceptance

## IMPLEMENTATION

User authorized continued MAGICK feature development after M6a. Rechecked canonical Syntagma AGENTS, current GitHub sources, active open MAGICK/Weather PRs (none returned), parent layout and M4/M5/M6a tests. M6b stays inside the existing source-owned ASTROLOGY instrument.

The current M4 JPL calculation contains a selected **two-body pair** and geocentric **apparent ecliptic longitude separation** sampled at real UTC timestamps. The new five-row aspect matrix compares that measured longitude gap to conventional reference angles 0° conjunction, 60° sextile, 90° square, 120° trine, 180° opposition. These are traditional angular conventions, not physical causal claims.

- Adds pure widgets/weather/StationMagickAspectMatrixPolicy.js. It reads the already-validated Celestial.model source along with its exact M4 query orb setting; requires correct source format, geocentric apparent true-ecliptic-of-date, one genuine relationship pair, aligned source timestamps and uniform UTC sample cadence. Failure shows unavailable rather than creating artificial samples.
- Buckets each current UTC viewport into at most 24 columns in compact mode, 40 otherwise, and finds the **nearest measured source sample** to each reference angle within each bucket. Magenta shading means the closest recorded sample lies inside the source-configured aspect orb; yellow indicates the currently selected sample, and dark cells are outside orb. Zero-orb behavior is exact-only.
- Adds compact secondary ASPECTS tabs CURVE/MATRIX inside existing chart frame. The top mode row remains at seven buttons. The original ASPECTS curve, retrograde lanes, ZODIAC, NETWORK and HELIO remain available and unchanged.
- Clicking a heat cell locks the actual sample index from the same JPL result (no new query), and records the selected reference row. Footer displays the exact source sample separation and its angular deviation from the reference. The existing chart pan, time zoom, lock and sample event controls remain.
- Source-only read; no extra process, no timezone inference, no transit/natal/house model, no interpretation source, no journal or external service.

## HOW TO USE

Once reviewed, merged by authorized operator, and separately deployed to Fedora: Weather Station > MAGICK > ASTROLOGY > ASPECTS. Choose CURVE for the original angular graph, or MATRIX for five conventional angular targets against the source UTC viewport. Choose a pair, date and span using existing controls, press CALCULATE to use on-demand JPL kernel. Magenta buckets are measured inside configured orb; select a cell to inspect the actual source sample and separation. Switch back to CURVE without losing the current pair.

## VERIFY

- New tests/weather/test_magick_aspect_matrix_m6b.js checks expected source M2 aspect angles, selected sample and error, 0° orb and outside-orb refusal, bounded viewport buckets, strict uniform time cadence, invalid frames, mismatched timestamps/units, geometry/cell-click routing, and original mode preservation.
- Wired into existing .github/workflows/weather-cosmos-jpl-network-v4a.yml together with M4/M5, M6a, V4a-V5b regressions.
- Review exact-head CI before claiming green; native Quickshell Canvas, compact button hit targets, and GohuFont readability require operator screenshots/interaction acceptance. No live changes made.

## WATCH OUT FOR

The current M4 source is one selected pair, not a multi-planet natal/transit chart. This matrix compares five conventional angular targets over actual sampled UTC positions, not all planetary pairs, a house chart, an influence forecast or a 3D sky angle. Each column may summarize more than one measured sample, and its shading selects only the closest original sample: **never interpolate an exact event time from it**. The matrix uses equal-width buckets only when source UTC cadence is uniform. For nonuniform input it refuses rather than presenting a false time scale.

The compact ASPECTS 2-button toggle is overlayed in existing plot header. Operator should inspect overlap in actual Weather Station width before acceptance. M6a/HELIO and V5 presentation remain operator-accepted baseline.

## CHECKLIST

- [x] Current repository and worker-ownership audit
- [x] M6b source-preserving matrix policy and Canvas integration
- [x] CURVE/MATRIX interaction and clicked source sample inspection
- [x] Numeric source, UI and regressions in workflow
- [ ] Exact-head CI green
- [ ] Operator-authorized merge, local deployment separately approved
- [ ] Native compact/GohuFont/interaction acceptance

## NEXT

Check PR and CI, repair evidenced failures. After native review, scope M6c transit/chart-comparison foundations carefully: M4 pair source alone is NOT a natal/transit calculator. Traditional planetary hours require a named convention for sunrise/sunset, weekday, high-latitude and timezone behavior; sourced correspondences need a selected corpus/tradition; tarot needs licensed assets and honest randomization; private journals need a separate privacy and storage assignment.

## DECISIONS

Preserve seven-button MAGICK top row; add nested views to existing instrument instead of new nav clutter. Keep observational measurement, conventional aspect labels and cultural interpretation explicitly separate. Deferred Visual V3 remains a later cross-instrument restyle, not part of M6b.
