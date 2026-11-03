# Weather StationW // MAGICK M0 Celestial Calculation Contract

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather StationW / MAGICK Celestial Backend M0
CONNECTION // External Hospital-compatible ChatGPT; no live registration verified
ASSIGNMENT // Isolated astronomy input/output contract, validation, tests and CI
STATE // Draft GitHub implementation for review, not a live Weather Station integration
BOUNDARY // No changes to COSMOS, MAGICK QML panels, CLASSIC, CPU++ Location, services or Fedora runtime.

## IMPLEMENTATION

- Python module: scripts/weather/celestial_contract.py.
- Request format: post-apollo.weather.celestial-request.v1.
- Snapshot format: post-apollo.weather.celestial-snapshot.v1.
- M0 **does not calculate astronomical positions**; it validates the contract that the future JPL-backed M1 engine must fulfill.
- No API, network process, local package installation, astronomical data cache, journal, UI/graphs, new services, or request scheduler.

### Request fields

- format: exact versioned identifier, reject unsupported versions.
- instant_utc: Gregorian ISO UTC with seconds, optional fractions, explicit Z suffix. M0 refuses local/DST-ambiguous times, rather than guessing the user's timezone.
- origin: geocentric, topocentric, or heliocentric.
- position_model: apparent or geometric; heliocentric only geometric in M0.
- frame: true-ecliptic-of-date. The exact true-ecliptic convention must be verified when the M1 engine is implemented, especially nutation/precession.
- bodies: unique supported IDs, including Sun/Moon, Earth, Mercury, Venus, Mars, and explicitly named barycenters for outer planets. Never silently conflate a planet's physical center and its system barycenter.
- observer: required only for topocentric calculations, explicitly containing numeric latitude_deg, longitude_deg and elevation_m. No inferred current location; no stored precision by default.

Example request (real format, not a computed position):

    {
      "format": "post-apollo.weather.celestial-request.v1",
      "instant_utc": "2026-11-03T11:45:00Z",
      "origin": "geocentric",
      "position_model": "apparent",
      "frame": "true-ecliptic-of-date",
      "bodies": ["moon", "sun"]
    }

### Snapshot fields

- format: exact post-apollo.weather.celestial-snapshot.v1 identifier.
- request: a valid request, canonicalized by normalize_request.
- tdb_jd: finite positive Julian date in TDB; not a UTC civil date.
- provenance: engine, engine_version, ephemeris_id, ephemeris_sha256 (actual file SHA-256), time_data_id, generated_at_utc.
- positions: exactly one row per requested body. Each has body, longitude_deg in [0,360), latitude_deg in [-90,90], distance_au >= 0. Optional longitude_rate_deg_per_day must be finite when present.

**Do not output zero values as placeholders.** Units and coordinate frames are mandatory. Observational USNO Moon/CelNav/MRST data remain separately sourced. Astronomy, zodiac interpretation and personal observations are different claims.

## HOW TO USE

Before calculation: call normalize_request(raw_request), catch ContractError.

After M1 calculates positions: call validate_snapshot(raw_snapshot). Validation checks structure, ranges and provenance completeness, but **does not verify physical accuracy**. Never treat a passing shape validator as proof of ephemeris accuracy or source authenticity.

## VERIFY

From repository root:

    python3 -m unittest discover -s tests/weather -p 'test_celestial_contract_m0.py' -v

Eight test cases cover canonical UTC, invalid local/DST timestamps, duplicated/unknown body IDs, center-body angular-coordinate refusals, explicit topocentric coordinates, heliocentric geometric-only rules, finite measured fields and reproducibility metadata. GitHub workflow runs tests on changed M0 files and through manual dispatch.

## WATCH OUT FOR

- JPL kernel coverage depends on the exact kernel chosen at M1, so M1 must reject dates outside the kernel coverage. M0 imposes no artificial coverage dates.
- True-ecliptic-of-date must be precisely mapped to the chosen calculation library. It is not a zodiac sign, sidereal coordinate or ICRF orientation.
- Earth cannot be its own geocentric target, nor Sun its own heliocentric target: the angular direction of an origin body is undefined.
- Timezone history conversion is a future separate feature requiring IANA rules and explicit location and local instant; M0 only accepts already resolved UTC.
- No local runtime tests or user acceptance are implied by GitHub CI.

## CHECKLIST

- [x] Versioned astronomical request and snapshot data shapes
- [x] Explicit epoch and coordinate convention, observer and body ID validation
- [x] No fabricated time, location, position, source or scientific accuracy
- [x] Isolated Python validation tests
- [x] CI workflow
- [ ] GitHub CI checked at actual PR head
- [ ] Operator acceptance of M0
- [ ] M1 JPL/Skyfield position solver with numerical cross-checks

## NEXT

M1 introduces a separately owned JPL-backed worker (Skyfield is a candidate, not yet installed or locked), exact target/kernel mapping, UTC-to-TDB conversion, true-ecliptic-of-date calculation, apparent/geometric position handling, coverage checks, and independent Horizons/USNO regression fixtures. No QML wiring until backend results are verified. M2 later adds angular aspects, stations, retrogrades and ingress event finding. UI and graph work follows verified backend geometry.

## DECISIONS

The operator requested backend-first development. No existing MAGICK/COSMOS/CLASSIC UI or local system changed. This M0 module has no direct active runtime attachment and no claims of live Hospital registration. The operator retains final approval, and shared owners must be consulted before future integration.
