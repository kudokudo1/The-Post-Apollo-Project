# Weather StationW // MAGICK M4 Graph & Timeline Data Contract

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather StationW / MAGICK Celestial Backend
ASSIGNMENT // M4 read-only graph data and event marker contract
ROLE // External Hospital-compatible development worker (no live Hospital registration verified)
BASE // M3 PR #1129 confirmed merged before creating M4 branch
BRANCH // feat/weather-magick-visual-data-m4-20261103
PHASE // Draft GitHub implementation; CI and operator acceptance to be verified
OWNERSHIP // New backend files only; MAGICK/COSMOS/CLASSIC QML, Location, Stage Director, archive and terminal seams untouched

## IMPLEMENTATION

New pure/production adapter: scripts/weather/celestial_visual_data.py
New tests: tests/weather/test_celestial_visual_data_m4.py
New workflow: .github/workflows/weather-magick-visual-data-m4.yml

M4 creates **renderer-neutral JSON** from the merged M0/M1/M2/M3 real astronomical engine. It is not a widget, planetarium, browser launch, daemon, polling service, data archive, magical inference, personal-data journal or new source provider.

### Query format

post-apollo.weather.celestial-visual-data.v1

Required fields:
- format
- start_utc and end_utc in explicit UTC Z timestamp format
- bodies: one to four distinct supported M0/M1 exact body IDs

Optional:
- step_hours: 1..24 (default 12)
- rate_window_hours: 0.5..24 (default 6)
- orb_degrees: 0..30 (default 6; astrological convention, not physical measurement uncertainty)
- include_events: boolean (default false; only up to two bodies)
- detect_tangents: boolean (default false; requires two bodies + include_events)
- tangent_tolerance_deg: >0..0.01 (default 0.00001; optional opt-in event marker tolerance)

This first graph contract is **geocentric, apparent, true-ecliptic-of-date**. It does not silently switch to sidereal zodiac or heliocentric physical orbit coordinates. Exact NAIF names and barycenters are retained. No inferred location, timezone, user profile, or favorite city.

M2 bounds remain: 366-day total span, sampling interval 1..24h, maximum 4096 raw-grid points. M4 additionally caps plots to **721 samples**, protecting renderer memory and data transfer. Queries that would exceed capacity fail closed rather than truncate or silently resample.

### Output shape

- format and normalized query (coordinate frame, origin, position model, units, cadence, options)
- sample_count
- series: each requested body has samples with:
  time_utc (ISO Z), unix_ms (UTC chart x-axis), longitude_deg (wrapped 0..360),
  unwrapped_longitude_deg (continuous curve), latitude_deg, distance_au,
  longitude_rate_deg_per_day (finite-difference), motion (direct, retrograde,
  or indeterminate for a numerical zero)
- relationships: each pair of bodies has synchronized samples of ecliptic longitude separation (0..180 degrees), plus any conventional aspect labels within the configured orb
- event_markers: optional exact-aspect crossings, optional M3 near-tangent candidates, and finite-difference planetary stations; timestamps are calculated from M2/M3 routines and tied to requested bodies. These are *calculated* events, not observational assertions.
- units and explicit epistemic limits for astronomical angle vs interpretive aspect, finite-difference station times and nonexhaustive event sampling.
- provenance (production only): Skyfield version, JPL .bsp basename, actual kernel SHA-256, built-in time-data identifier, generation timestamp UTC.

The pure function build_visual_model(query, state_at) intentionally omits provenance because it has no knowledge of the real kernel; it is for deterministic tests and possible alternate approved source adapters. Production compute_visual_data(query, kernel_path) attaches authoritative provenance and loads **one** kernel and Skyfield timescale per request. It never downloads the JPL file automatically.

### Example developer query

    {
      "format":"post-apollo.weather.celestial-visual-data.v1",
      "start_utc":"2026-10-01T00:00:00Z",
      "end_utc":"2026-10-25T00:00:00Z",
      "bodies":["moon","sun"],
      "step_hours":12,
      "orb_degrees":6,
      "include_events":true
    }

## HOW TO USE

From an isolated developer environment with Skyfield 1.55 and an explicitly supplied JPL .bsp kernel:

    python3 scripts/weather/celestial_visual_data.py --kernel /path/to/de440s.bsp --query graph-query.json

Use --query - to read a JSON object from stdin. Output is a single JSON object for later rendering. This command does not start Quickshell or open a window.

Potential UI consumption later: hover/time-scrub across samples by unix_ms, show continuous curves with unwrapped longitude, keep 0..360 labels separately, annotate source-bearing event_markers, and inspect aspects and retrograde motion without making new ephemeris network calls.

## VERIFY

Commands from repo root:

    python3 -m unittest discover -s tests/weather -p 'test_celestial_contract_m0.py' -v
    python3 -m unittest discover -s tests/weather -p 'test_celestial_solver_m1.py' -v
    python3 -m unittest discover -s tests/weather -p 'test_celestial_dynamics_m2.py' -v
    python3 -m unittest discover -s tests/weather -p 'test_celestial_precision_m3.py' -v
    python3 -m unittest discover -s tests/weather -p 'test_celestial_visual_data_m4.py' -v

New tests cover 360° wrap continuity, coordinate and velocity values, timestamps, pair alignment, real station and aspect marker times, invalid readings (missing, NaN, negative distances, boolean coordinate, 360-degree value), bounded query sizes, unsupported fields and timezone-inferred time refusals.

Real-JPL CI downloads official DE440s only into the disposable GitHub runner and checks M4 samples against M1 at corresponding UTC instants and M4 event markers against M2 for matching time windows. No local Fedora install or live UI acceptance is claimed.

## WATCH OUT FOR

- No future prediction about human outcomes, behavior, health, relationships or politics. Celestial geometry is calculated; astrological nomenclature remains an optional convention.
- Unwrapped_longitude_deg is a **display continuity coordinate**, not a new astronomical frame. True retrograde movement can reverse its slope.
- The rate value is a centered finite-difference estimate from M2 with a declared window; it is not an analytic instantaneous physical velocity.
- The event search can miss short or non-crossing events; M3 candidates can be near misses within a configured angular tolerance. The graph contract retains these limits.
- A graph interval can require out-of-range samples just beyond start/end for centered rates. Kernel coverage remains strict: reject rather than fabricate.
- A 721-sample cap applies before kernel loading; larger data requests require an explicit future pagination/downsampling design.
- M4 is an *offline producer*, not a Quickshell connection yet. Existing COSMOS/MAGICK UI owners and the Weather Station CLASSIC migration worker must coordinate M5 wiring.
- No geographic position, birth data, tarot data or family research is fetched, inferred or stored.

## CHECKLIST

- [x] Current M3 merge and GitHub main/active-work preflight
- [x] Read-only JSON graph query/series/relationships/event contract
- [x] Bounded sample counts and exact M0 body IDs
- [x] Pure analytical test adapter and real-JPL production adapter
- [x] Tests and dedicated workflow
- [ ] PR-head CI all green
- [ ] Operator acceptance and authorized merge
- [ ] M5 visual integration with COSMOS/MAGICK owner coordination
- [ ] Independent Horizons cross-epoch validation, optional later hardening

## NEXT

M4 acceptance and merge, then M5. M5 can create new isolated plot components (zodiac wheel, orbital geometry view, velocity curve, aspect timeline) driven only by source-stamped M4 JSON, preserving user requested mouse wheel zoom, drag pan, hover/click inspection and avoiding external browser focus theft. Establish process ownership and backend request transport first, with no second ephemeris poller.

## DECISIONS

Backends first, one ephemeris source per calculation, observable geometry separate from interpretation; no user local machine modifications, merges or production activation performed here. Operator retains final acceptance.
