# Weather StationW // MAGICK M2 Celestial Dynamics

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather StationW / MAGICK Celestial Backend
ROLE // External Hospital-compatible worker; no live Hospital registration verified
ASSIGNMENT // M2 aspects, retrograde motion and exact-event search
STATE // GitHub draft; initial CI verified; operator acceptance pending
BASE // M0 and M1 were already merged; main at branch creation 9bc9a5017f1f21df42436ab6023cfed41ec0d7be

## IMPLEMENTATION

New files: scripts/weather/celestial_dynamics.py, tests/weather/test_celestial_dynamics_m2.py, .github/workflows/weather-magick-celestial-dynamics-m2.yml.

M2 reads M1's caller-provided local JPL SPK kernel via Skyfield. It loads the kernel and timescale once per event report, never downloads ephemerides in the calculation process, never infers user location, and never writes private observations.

- longitude_separation(a,b) measures the shortest 0..180 degree *ecliptic longitude* separation, not true 3-D angular distance.
- aspects_at(a,b,orb_degrees) labels 0 conjunction, 60 sextile, 90 square, 120 trine and 180 opposition using a configurable angular orb.
- longitude_rate(lon_at,t,window_hours) derives a central finite-difference angular velocity (degrees/day), with circular wrap handled explicitly.
- find_station_events searches signed velocity crossings and distinguishes direct-to-retrograde from retrograde-to-direct, with timestamps refined by bisection and derivative-window provenance.
- find_aspect_events searches exact angular crossings, handling either 60/300, 90/270, 120/240 relative orientation and the 0/360 boundary; it deduplicates events on adjacent interval boundaries.
- event_report invokes the search using geocentric apparent true-ecliptic-of-date positions from M1. Input requires explicit UTC start/end, one or two exact NAIF-labeled body names, mode (aspects or stations), and optionally sample step and rate window.

Event results use format post-apollo.weather.celestial-events.v1 and preserve the query, step, source kernel SHA-256, engine version, timescale identifier, generation timestamp and an explicit search-completeness limitation.

## HOW TO USE

From an isolated developer environment with Skyfield 1.55 and an explicitly downloaded local JPL .bsp file:

    python3 scripts/weather/celestial_dynamics.py --kernel /path/to/de440s.bsp --query my-query.json

Example query:

    {
      "format":"post-apollo.weather.celestial-events.v1",
      "mode":"aspects",
      "start_utc":"2026-10-01T00:00:00Z",
      "end_utc":"2026-12-01T00:00:00Z",
      "bodies":["moon","sun"],
      "step_hours":12
    }

For stations, use mode stations and a single body such as mercury. This is a developer CLI, not a Weather Station UI.

## VERIFY

Initial GitHub PR-head run (before this handoff commit) passed three checks:
- offline-math: success.
- validate: success.
- jpl-dynamics: success. Its job log explicitly records 10/10 M2 tests passing, without skipping real-kernel tests.

Offline math covers wraparound, aspect orbs, conjunction/sextile crossings, exact station direction, invalid date/range/body handling, nonexistent kernel, and sample limit. Real DE440s CI covers the Mercury station cycle in 2026 and Sun/Moon aspects between October and December 2026. A conjunction result was checked independently through the M1 snapshot solver.

Commands from repository root:

    python3 -m unittest discover -s tests/weather -p 'test_celestial_contract_m0.py' -v
    python3 -m unittest discover -s tests/weather -p 'test_celestial_solver_m1.py' -v
    python3 -m unittest discover -s tests/weather -p 'test_celestial_dynamics_m2.py' -v

The real-kernel subset runs only if MAGICK_M1_KERNEL is set to an existing JPL BSP file. Without that variable those tests SKIP. This is not live Fedora or Quickshell acceptance.

## WATCH OUT FOR

- Event scans use sampled signed crossings. Tangential aspect contacts and short unsampled reversals may be missed. Result field complete_for_tangent_contacts is FALSE. This algorithm is not an exhaustive almanac.
- Bisection stops at a <=1-second time bracket; that is numerical convergence, NOT a guarantee of physically one-second-accurate station times.
- All positions are apparent geocentric true-ecliptic-of-date. Aspect names are interpretive conventions; this is not 3-D conjunction/occultation and says nothing about metaphysical causation.
- Search maximum: 366 days, 1..24 hour sampling, 4096 total samples; reject large per-step phase jumps instead of returning ambiguous geometry.
- Distinguish named planet centers and system barycenters. Kernel coverage and actual target availability remain explicit.
- CLASSIC, MAGICK/COSMOS QML, location settings, data archives, journaling, Stage Director, and Fedora remain untouched.

## CHECKLIST

- [x] M0 and M1 merged into current main before start
- [x] M2 angular geometry, stations and aspect crossing search
- [x] Explicit source and numerical limitations
- [x] Isolated unit tests and temporary real-JPL CI
- [x] Initial 3/3 CI, M2 10/10 tests
- [ ] Recheck final PR head after this documentation commit
- [ ] Operator acceptance and separately authorized merge
- [ ] Independent multiple-epoch Horizons comparison
- [ ] Tangential-event completeness improvement

## NEXT

M2 hardening should capture grazing/tangent contacts and validate timing sensitivity under finer steps and derivative windows. Next add time-series and source-aware event APIs, then interactive zodiac/planetary graphs. Coordinate future MAGICK/COSMOS UI integration with existing owners; no implicit ownership transfer.

## DECISIONS

Backends first, meaning separate from measurement; no merge, local system changes, or Hospital registration performed.
