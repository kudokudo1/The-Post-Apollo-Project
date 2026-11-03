# Weather Station // COSMOS V2 Moon Illumination and Solar Altitude

PATIENT // kudokudo1/The-Post-Apollo-Project  
ROOM // Weather Station / COSMOS Visual Intelligence V2  
DOCTOR // External Hospital-compatible ChatGPT  
PROVIDER // OPEN AI // CHATGPT  
CONNECTION // EXTERNAL / HOSPITAL-COMPATIBLE, not live registered  
ASSIGNMENT // Source-backed Moon phase schematic and modeled 24h solar-altitude graph  
STATE // GITHUB IMPLEMENTATION / CI, not accepted locally  
ROADMAP // docs/weather-subjects-visual-intelligence-future-worker-roadmap-2026-11-03.md

## IMPLEMENTATION

**V2 scope is restricted to Moon and Sun visual astronomy.** This phase does
not compute or depict actual planetary alignments, aspects, zodiac signs,
retrogrades, eclipse trajectories, or an optical Moon orientation.

- `widgets/weather/StationCosmosVisualPolicy.js`: pure visual data math.
  Reads existing USNO one-day Moon phase and illumination percentage,
  preferentially; if unavailable, uses explicitly labeled **WTTR DAILY
  FORECAST** phase/illumination from existing
  `WeatherCyclePolicy.astronomySummary`. No independent network call.
  Eight phase markers identify the **current phase category**, not
  forecasts or precise future dates.
- Moon disk draws actual provider illumination fraction via circular
  slice integration, not a static emoji. Waxing and waning control which
  side is illuminated, but **this orientation is schematic**, not the
  tilt seen from a specific latitude, time or telescope orientation.
  If direction cannot be inferred from the phase, the disk does
  **not** guess a side. Invalid illumination hides it.
- The Sun graph samples the already existing
  `StationSkyTwilightPolicy.solarPosition()` calculation every
  20 civil minutes, plus minute 23:59. This is a **calibrated model
  of solar-center altitude at the provider's location**, not observed
  sunshine, local terrain, photo imagery, or official USNO sky position.
  The computation reuses the original sunrise-calibrated civil offset;
  missing date/coordinates/offset yields UNAVAILABLE, never 0° as
  a fabricated reading.
- `widgets/weather/StationCosmosVisualInstruments.qml`: two independent
  framed visual bays with real 0° horizon, day/night altitudes, 24h
  local-civil-time ticks, hover position, click-to-lock solar time,
  UNLOCK button and current solar-altitude reference from existing
  StationSky. Moon panel shows phase, percent, source and an eight
  marker ribbon.
- `widgets/weather/StationSky.qml` remains sole owner of the
  existing USNO Moon, astronomy summary, location and solar models.
  It only mounts the new view when a COSMOS route already includes
  its `moon`, `astronomy` or `twilight` sections; CLASSIC and
  WEATHER retain their exact previous layout, requests and behavior.
  This also makes Moon display available to MAGICK's observational
  reference, because MAGICK reuses the COSMOS Moon route through
  StationSky with its original source boundaries.

### Route behavior

- SUBJECTS → COSMOS → OVERVIEW: both Moon and Sun bays, followed by the
  original astronomy and SPACE overview instruments.
- SUBJECTS → COSMOS → MOON: Moon display on
  `cosmos/moon/ephemeris`, with the original USNO timings below.
- INDEX → COSMOS → SUN → POSITION / TWILIGHT: solar-altitude arc
  alongside original position and twilight details. Bottom SUN mode
  points to `cosmos/sun/position`.
- MAGICK → LUNAR + SOLAR: its astronomy-only COSMOS Moon reference
  contains the Moon schematic. No magical interpretation is added.
- OTHER routes (planet clocks, ISS, eclipses, weather forecasts,
  CLASSIC) are not changed by this instrument.

## HOW TO USE

Once GitHub code is merged **and a separate local update is approved**:

Weather Station → SUBJECTS → COSMOS → OVERVIEW / MOON / SUN.

Read the Moon's schematic lit fraction and eight-phase ribbon; use
the Sun 24h plot to compare above/below-horizon modeled elevation by
provider-local time. Hover to inspect the local time slot, click to lock,
press UNLOCK to resume hover. Both views explicitly state their
source/model type and unavailable cases.

This is not a weather forecast, a precise orbital transit animation,
or a claimed astronomical alignment.

## VERIFY

Dedicated `tests/weather/test_cosmos_visual_instruments_v2.js` checks:
- eight distinct phase IDs, phase and illumination validation;
- exact fraction of illuminated circular disk using geometry
  integration and symmetric waning/waxing behavior;
- USNO priority, honest daily-provider fallback and unknown direction;
- 24h solar altitude model built from existing NOAA-style solar policy,
  true modeled noon/midnight differences, coordinates/offset errors,
  horizon, local-time axes and nearest computed sample;
- route gating, original source request gates, new Canvas/mouse
  handlers and no independent service/process/file writers.

Workflow `.github/workflows/weather-cosmos-visual-instruments-v2.yml`
also runs prior V1 graph, COSMOS/MAGICK and W1/W1r regressions.
Repository teardown CI must be green.

**Important:** CI source math and QML text contracts do not prove a
successful live Qt Canvas frame or mouse positioning on Fedora.
Local visual fit, model/source freshness and actual controls remain
operator acceptance items.

## WATCH OUT FOR

1. USNO Moon phase/illumination is a dated provider prediction, not
   the observer's optical disc orientation. The phase ribbon is a
   categorical indicator, not a future-events calendar.
2. The solar altitude curve is **calculated**, using calibrated offset
   rather than a true local timezone identifier. Civil-time DST/offset
   and polar cases are rejected when inputs are invalid, or require
   careful live checks at exceptional locations.
3. The chart is 24h across one provider-local civil date. It is not
   the Sun's apparent sky-path in 3D, an azimuth compass, or measured
   optical visibility. Existing source may be stale or unavailable.
4. The source-specific fallback is visibly labeled so USNO and
   WTTR daily estimates aren't silently mixed.
5. No provider, moon fetch, timestamp store, forecast engine,
   separate Qt Timer, new terminal window, Stage Director process,
   or HOME/CLASSIC migrations are created.
6. A parallel Weather worker handles W2b HOME/CLASSIC. This
   implementation changes only COSMOS SKY visual seams.
7. Existing Moon page and overview grow vertically by ~258px; test
   scrolling, visual fit and label clipping at actual station size.

## CHECKLIST

- [x] Rechecked current Syntagma AGENTS / OPERATE, GitHub main, open PRs
- [x] Source properties and route activation verified
- [x] Pure Moon + calibrated solar visualization policy
- [x] Interactive graphics without new provider ownership
- [x] Narrow COSMOS/MAGICK observational route integration
- [x] Focused tests and CI workflow
- [ ] Final branch-head CI all green
- [ ] GitHub merge with required checks and existing operator authorization
- [ ] Local Quickshell visual / mouse / provider acceptance

## NEXT

V2b should introduce a source-accurate **planet visibility event clock**
using existing USNO planet rise/transit/set records. This is not the
same as live orbital coordinates or a zodiac/aspect wheel. Subsequent
V3 MAGICK interpretive lens work must select sourced schools and
explicitly separate symbolic interpretation from numerical astronomy.
V4 orbital alignment/retrograde visuals remain blocked until a
precision-consistent ecliptic ephemeris is connected.

## DECISIONS

Ship one bounded real Moon/Sun visual with no fabricated ephemerides.
Keep scientific observation, calibrated astronomical computation and
future symbolic lenses distinct. The other worker owns HOME/CLASSIC
migration; this room owns only new COSMOS subject visual work.
No local changes, Quickshell activation or live Hospital registration
were performed.
