# Weather StationW // MAGICK M1 JPL Ephemeris Backend

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather StationW / MAGICK Celestial Backend
STAFF ROLE // External Hospital-compatible development worker (not live registered)
ASSIGNMENT // M1 JPL/SPK position solver and numerical validation
PERMISSIONS // Explicit user request to continue GitHub development; no Fedora write/restart and no merge without appropriate authorization
STATE // Draft implementation, CI verification pending
BASE // M0 celestial contract was merged into main before this M1 branch
NEXT // M2 motion, aspects, stations, and event-finding; graphs after verified backend

## IMPLEMENTATION

New: scripts/weather/celestial_solver.py, tests/weather/test_celestial_solver_m1.py,
.github/workflows/weather-magick-jpl-skyfield-m1.yml.

Additive change: scripts/weather/celestial_contract.py adds mars_barycenter as an explicit body ID, leaving M0 request/snapshot format unchanged.

The M1 solver loads a **caller-supplied, local JPL SPK .bsp file** using
Skyfield 1.55 (MIT licensed). Its computation path has no network access, cache
write, geolocation lookup, external shell command, or QML runtime integration.

M0 request fields are consumed unchanged:
- instant_utc: explicit ISO UTC (Z), never guessed from desktop location/timezone.
- origin: geocentric, topocentric (explicit WGS84 latitude/longitude/elevation),
  or heliocentric (geometric only).
- position_model: apparent or geometric.
- frame: true-ecliptic-of-date, computed with Skyfield ecliptic_frame.
- bodies: exact NAIF mass centers, or explicitly named barycenters.
M1 output is an M0 snapshot with TDB Julian date, longitude 0..360,
ecliptic latitude, distance AU, exact SHA-256 of kernel bytes, a provider
version, an identified built-in time scale, and generation timestamp.

APPARENT: observer.at(t).observe(target).apparent() (light-time, aberration,
deflection). GEOMETRIC: (target-observer).at(t) (instantaneous vector).
Do not confuse these modes, or use merely observe() for geometric output.

**Important JPL DE440s distinction:** It exposes the Mars *system barycenter*
(NAIF 4) but not the exact center of Mars (NAIF 499). M0 now supports
mars_barycenter (4) explicitly. A request for mars (499) fails closed on
DE440s rather than quietly mislabeling a barycenter as the planet.
Mercury (199), Venus (299), Earth (399), Moon (301), Sun (10), and Jupiter,
Saturn, Uranus, Neptune, Pluto system barycenters (5..9) are supported
subject to the actual kernel. This constraint is not a missing-body guess.

## HOW TO USE

This is a developer-only backend, not a Station control. After separately
obtaining a JPL .bsp kernel and installing Skyfield 1.55 into an isolated
Python environment (no installation has been made on operator Fedora):

    echo '{"format":"post-apollo.weather.celestial-request.v1","instant_utc":"2026-11-03T12:00:00Z","origin":"geocentric","position_model":"apparent","frame":"true-ecliptic-of-date","bodies":["moon","sun","mars_barycenter"]}' | \
      python3 scripts/weather/celestial_solver.py --kernel /path/to/de440s.bsp

Returns a compact JSON snapshot; errors print to stderr and exit nonzero.
The user's current location is never queried.

Official DE440s file reference:
https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de440s.bsp
Supported span approximately 1849–2150. Coverage depends on kernel; do not
extrapolate or silently download a replacement.

## VERIFY

Offline (no packages/data required):

    python3 -m unittest discover -s tests/weather -p 'test_celestial_contract_m0.py' -v
    python3 -m unittest discover -s tests/weather -p 'test_celestial_solver_m1.py' -v

The M1 file contains offline guard tests plus 5 JPL integration cases.
Without MAGICK_M1_KERNEL, integration cases are marked SKIPPED, not passed.
The dedicated GitHub runner installs Skyfield 1.55 in CI only and obtains
DE440s in its temporary directory, then sets MAGICK_M1_KERNEL explicitly.

Numerical regression:
- Sun true-ecliptic apparent longitude at 2019-09-02 10:42:26 UTC
  ~159.68641 degrees (Skyfield published DE421 example), bounded tolerance.
- Mars system barycenter near Sun longitude in that sample event.
- Opposite instantaneous Earth/Sun vectors in geocentric and heliocentric
  geometric modes: 180 degrees longitude separation, matching distance,
  opposite latitude.
- Moon topocentric parallax differs from geocentric position.
- Refuse the missing Mars center target rather than give an invented result.
- Refuse dates beyond DE440s coverage.

M0 contract validation checks completeness/units/provenance shape but not
physical accuracy. CI numeric checks are first regression anchors, not a
full independent Horizons validation. Future work should compare Horizons
or NOVAS over more dates, locations and planets with declared tolerances.
A real Fedora/Quickshell integration and user acceptance are not claimed.

## WATCH OUT FOR

- Keep true ecliptic of date distinct from fixed J2000, sidereal/tropical
  sign interpretations, and the altitude/azimuth values in existing USNO
  CelNav. Do not derive retrograde from a single position.
- Time conversion uses Skyfield's built-in time data, identified by version;
  future historic/timezone source requirements remain M2+.
- No automatic file download occurs in the solver; only the disposable
  GitHub CI workflow downloads an official kernel.
- Ephemeris checksums identify bytes; they are not proof of vendor signing.
- Reproducibility depends on kernel and time-data versions, not just timestamp.
- UI, classic-to-subject migration, Studio/Stage Director, Weather caches,
  user diaries, and other workers' modules remain untouched.

## CHECKLIST

- [x] M0 merged into main before M1 work
- [x] New isolated M1 solver with exact SPK target resolution
- [x] Geocentric/topocentric/heliocentric apparent/geometric mode separation
- [x] Real SHA-256 and timestamp provenance
- [x] Explicit barycenter naming; no silent relabeling
- [x] Offline guard tests and dedicated JPL numerical CI
- [ ] PR-head CI all green
- [ ] More independent multi-epoch Horizons validation
- [ ] User acceptance
- [ ] M2 aspect/motion calculations

## NEXT

After successful GitHub CI and operator acceptance, build M2 on this backend:
unwrapped geocentric longitude time series, angular velocity/stations,
event timing, ecliptic separation/aspects and configurable astrological
interpretation definitions. Keep calculation/interpretation separate and
only later build the zodiac wheels, charts, timeline scrubber and AstroTerm
data adapter. Recheck other workers' source ownership first.

## DECISIONS

Backend-first, scientific data from JPL kernel with local read-only runtime,
no QML or Fedora edits, no merge or activation in this step. Hospital-compatible
report only; no evidence of a live Hospital connection/Room registry.
