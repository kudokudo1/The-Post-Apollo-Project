# Hospital // Weather Station V4b Apparent Geocentric Depth

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station // Visual Intelligence Lane B
STAFF ROLE // Nurse 2, external Hospital-compatible, not live registered
PROVIDER // OPEN AI // CHATGPT
ASSIGNMENT // V4b read-only linked apparent-geocentric distance diagram
PHASE // GitHub draft, native acceptance pending
GIT // feat/weather-cosmos-v4b-apparent-depth-20261104

## IMPLEMENTATION

- Verified Syntagma AGENTS, Hospital reports, permissions and working guide. Merged V4a PR #1221 is baseline. No competing open Weather/COSMOS/MAGICK PR found in the preflight.
- M4 validated JPL samples already carry geocentric apparent true-ecliptic-of-date longitude, latitude, distance (AU) and exact UTC. Current on-demand MAGICK source accepts exactly two bodies. No further source expansion is claimed.
- widgets/weather/StationCosmosCelestialDepthPolicy.js converts only existing source samples into apparent ecliptic Cartesian direction/range components with original AU norm. It cross-checks the V4a source-verified model, UTC sample, frame, hash, source body identities, longitude and distance. It rejects inconsistent input rather than generating zeros.
- widgets/weather/StationCosmosCelestialDepthPane.qml renders Earth-centered polar rings where the angle means true-ecliptic longitude and the radial scale is LINEAR apparent geocentric distance in AU. The outer ring is the farthest included body, not a solar-system boundary. Latitude and distance are displayed numerically. Hover/click selects a real source body; dragging navigates real M4 samples; wheel zooms the existing time range.
- widgets/weather/StationCosmosCelestialNetwork.qml is the only existing component changed: it now has a local CHORDS / DEPTH switch while preserving selected body, UTC sample, provider state and gestures. Both modes consume the original M4 data and the same V4a verified network scene.
- No MAGICK-owned instrument, M4 source service, query policy, Python JPL scripts, SUBJECTS/CLASSIC navigation, HOME, Stage Director or local Fedora files modified.

## HOW TO USE

After review, authorized merge and separately approved local installation:
Weather Station > SUBJECTS > MAGICK > Celestial Reference > CALCULATE > NETWORK > DEPTH. The middle dot denotes Earth. Colored source vectors terminate at apparent directions and distances in AU. Click a body or body inspector button to read ecliptic longitude, latitude and distance. Drag to move between existing UTC samples. Scroll to zoom the existing time window. CHORDS returns to the original longitudinal relationship network without changing selection or time.

## VERIFY

- tests/weather/test_cosmos_apparent_depth_v4b.js exercises realistic-format synthetic test fixtures through the existing M5 validator and V4a network policy. Checks exact source UTC/frame, 0/90/180/270 spherical projections, latitude Z, magnitude in AU, linear radius scale, pointer hitboxes, invalid provenance or samples, and QML source/gesture isolation.
- Expanded existing .github/workflows/weather-cosmos-jpl-network-v4a.yml to run V4b and earlier M4/M5 regression suites. Check final PR-head workflows independently.
- Native QML Canvas rendering, real JPL availability, labels, hitboxes and Quickshell mouse/scroll are NOT established by source tests.

## WATCH OUT FOR

This is NOT an instant heliocentric 3D solar-system scene. It represents apparent geocentric directions and ranges, whose light-time reference does not guarantee simultaneous physical Cartesian positions. The top-down ecliptic rendering shows longitude/distance; latitude remains numeric. No fake orbits or paths.

The outer ring rescales to the farthest selected body. This improves readability but changes the visual scale when source pair changes; measured AU values stay accurate. Close bodies may overlap Earth, so inspector body buttons stay available.

JPL kernel/Skyfield missing or inactive MAGICK route must yield unavailable data. No new polling or fallback measurements. No merge, live Hospital registration, local restart, or operator final DONE is claimed.

## CHECKLIST

- [x] Recheck current GitHub and Syntagma protocols
- [x] Source-bounded apparent AU depth projection
- [x] Internal CHORDS / DEPTH navigation and inspector
- [x] Preserve M4 sample, source hash and time controls
- [x] Add numerical, source and UI regression contracts
- [ ] CI passes on final PR head
- [ ] Operator-approved native desktop verification
- [ ] Final user acceptance

## NEXT

Verify CI and ensure branch files do not collide with newly merged workers. Fix isolated failures only. After authorized merge and local deployment test real M4 CALCULATE, CHORDS / DEPTH, sample scrub, body focus, numerical AU and frame labels. True heliocentric spatial rendering is a separate future MAGICK source/ownership assignment, not inferred from this payload.

## DECISIONS

Lane B only. Reuse the existing source and operator-preferred meaningful circular geometry. Do not confuse apparent geocentric depth with physical orbits; keep MAGICK provider ownership intact.
