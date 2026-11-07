# 🏥💜 MAGICK M8b // Source-Verified Tropical Natal Calculations

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station MAGICK > Astrology > Natal
STAFF // DOC (OpenAI ChatGPT; Hospital-compatible external, not live-registered)
ASSIGNMENT // Make the M8a reference natal wheel calculate actual planets, ASC, MC and twelve house cusps
BRANCH // feat/weather-magick-m8b-source-natal-calculator-20261106
BASE // main at 4757db69d71b669d8b821a4ed2061c10295ce071
PERMISSIONS // Bounded GitHub implementation, automated tests and PR. No local Fedora changes, merge or production activation.

## IMPLEMENTATION

- Added `scripts/weather/celestial_natal_chart.py` as an offline, explicit-UTC, source-bound natal calculation with one existing JPL BSP kernel and Skyfield. It uses ten EXACT NAIF target identifiers: Sun, Moon, Mercury, Venus, plus explicitly labelled Mars/Jupiter/Saturn/Uranus/Neptune/Pluto system barycenters. Nothing is silently relabelled as a planet center.
- Observational positions are **topocentric apparent** ecliptic-of-date longitudes, latitudes and distances from explicit geodetic latitude/longitude at zero-meter elevation. No location inference or unapproved downloads.
- Calculates Ascendant as the EASTERN crossing of the local horizon and ecliptic, and Midheaven as the UPPER-meridian crossing, using Greenwich apparent sidereal time and rotations between Skyfield's true equator/equinox and true ecliptic/equinox of date. Derives 12 Whole Sign or Equal house cusp longitudes from the measured ASC.
- The pure geometric ASC/MC method was independently checked against a Swiss Ephemeris analytical reference at 2026-11-06 14:20 UTC, latitude 38.9 N, longitude -76.8 E: ASC 255.570003845761° and MC 184.376420714428°.
- Only **tropical** zodiac calculations are enabled. Sidereal UI is visible but explicitly disabled because a declared and verified ayanamsa is not yet connected. Placidus and other cusp models are not implemented.
- Added `StationMagickNatalRequestPolicy.js` for strict event-spec conversion and result-to-request checks; `CelestialNatalChartService.qml` loads existing local JPL/Skyfield installation **only on user click**. The private request is sent as one bounded JSON line over **stdin**, never inserted in process argv, URLs, file caches, or environment variables.
- Updated the existing Event Setup overlay to use a compact two-column form, provide CALCULATE NATAL, clear typed event details on close, and reject unsupported sidereal calculations.
- Updated the Astrology screen to preserve the existing M4 pair JPL controls while connecting the new full-chart source to the M8a natal renderer. Pairs and natal remain independent; a selected-pair result cannot masquerade as a full chart.
- No personal chart archive, readings, journaling, model-generated interpretation, transit chart, shared Planner records or global Weather/COSMOS sources were created.

## HOW TO USE

After explicit operator merge/deployment:
1. Weather Station > MAGICK > ASTROLOGY > NATAL, then EVENT SETUP (or SET EVENT).
2. Enter an explicit UTC date (YYYY-MM-DD), UTC time (24-hour HH:MM), latitude and longitude. These are a user-chosen event, NOT inferred from the host. Choose TROPICAL and either WHOLE SIGN or EQUAL.
3. Press CALCULATE NATAL. Only the local Skyfield/JPL installation receives that input. If the installed BSP lacks the named target or year coverage, the chart fails unavailable instead of displaying fake values.
4. Inspect the real zodiac/house placement, calculated ASC, MC, angular relationships and selected planets. Use zoom/pan/FIT. Reopen EVENT SETUP for a new calculation. Switch PAIR to the original two-body JPL view.

## VERIFY

- New Python `tests/weather/test_magick_natal_engine_m8b.py`: bounded input, exact NAIF body list, pure ASC/MC geometric reference against Swiss, Whole Sign/Equal cusps, invalid polar geometry, no birth data argv/storage.
- New Node `tests/weather/test_magick_natal_integration_m8b.js`: draft-to-request normalization, source and observer/result matching, deliberate user-triggered STDIN launch, privacy, M8a renderer and two-body isolation.
- Updated M7a regression to expect the real tropical calculator rather than the obsolete "engine not connected" text.
- GitHub workflow `.github/workflows/weather-magick-m8b-natal.yml` runs those checks and M8a/M7a suites. Check actual PR head before claiming CI verified.
- Full end-to-end scientific output from the user's installed de440s and native Quickshell input handling remains a separate verification gate. The CI science reference validates frame geometry, not execution against a live installed JPL file.

## WATCH OUT FOR

- **Tropical only**, Whole Sign and Equal houses only. The complete natal engine does not imply full sidereal or quadrant-house support.
- Outer JPL **barycenter positions are accurately labelled** rather than presenting system centers as literal planet centers.
- Site elevation is fixed at 0 m for this milestone; results may differ slightly from charts based on real elevation or geocentric positions.
- All birth details are sensitive personal inputs. This implementation is ephemeral, uses stdin, and clears text when the overlay closes. Do not log, cache, sync or transmit them.
- Planetary aspect lines are angular/interpretive conventions based on measured ecliptic longitudes. They do not establish causal spiritual effects.
- Dates are explicit UTC and do **not** automatically convert from local civil or birth-certificate time. The user must supply a correct UTC instant.
- The M8a natal wheel may have label crowding/overlaps on a compact native desktop. CI alone does not certify visual fit; user acceptance is pending.
- Source and service activation do not modify local Fedora, installed Quickshell, or private storage. No merge/production activation.

## CHECKLIST

- [x] Syntagma/Hospital preflight and M8a merged confirmed
- [x] Isolated M8b GitHub branch, no open MAGICK PR collisions
- [x] Exact JPL topocentric ten-body tropical source engine
- [x] True-equinox ASC/MC geometric calculation, twelve house cusps
- [x] Private stdin calculation and explicit event form integration
- [x] Source-to-request match and old paired-JPL separation
- [x] Python/Node numerical-contract tests and CI workflow
- [ ] PR-head CI and independent review
- [ ] Real BSP end-to-end numerical comparison
- [ ] Operator merge
- [ ] Authorized native deployment and input/visual acceptance
- [ ] Sidereal ayanamsa research and chart extension in separate assignment
- [ ] Multi-epoch transits and interpretation in separate assignment

## NEXT

Open draft PR, verify and repair CI, then get independent review of observer-frame math and process privacy. Operator decides merge and local installation. After a native natal calculation passes, move to M8c optional transits and declared sidereal/house systems without reusing the old two-body process.

## DECISIONS

Astronomical data determines the wheel; never fill missing placements with art-derived guesses. Keep the original M4 pair and M7 annual calendars operational. No implicit location, profile saving, inaccurate sidereal conversion, automatic merge, or local desktop edits.
