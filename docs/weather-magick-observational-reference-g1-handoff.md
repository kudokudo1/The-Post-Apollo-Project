# Weather Station // MAGICK G1 observational-reference integration

PATIENT // The-Post-Apollo-Project
ROOM // Weather Station / MAGICK Subject Migration G1
DOCTOR // External Hospital-compatible ChatGPT
PROVIDER // OPEN AI // CHATGPT
CONNECTION // EXTERNAL / HOSPITAL-COMPATIBLE
ASSIGNMENT // Implement the MAGICK subject as a disciplined observation-vs-interpretation workspace
PHASE // IMPLEMENTATION / CI
STATE // REVIEWABLE, not yet installed on Fedora

## IMPLEMENTATION

The canonical MAGICK hierarchy has 16 existing leaf destinations. This
milestone makes each destination a real navigable QML page and explicitly
distinguishes two types of content:

1. Eight submodes reuse an existing COSMOS SKY panel **as an observation
   only**: lunar phase/illumination/rise-set, local solar position and
   twilight windows, USNO current-sky bodies, or visible-planet rise/set.
   No new ephemeris, background polling service, clock or storage provider
   has been introduced. The view reuses the Station root WeatherService
   and its existing runtime clock. Original USNO requests remain
   conditional upon selected SKY sections.
2. Eight submodes cannot supply the planned interpretive feature yet,
   and display "NO CONNECTED INSTRUMENT" instead of invented output.
   There is no automatic tarot deck/shuffle, astrology chart, sign,
   aspect, retrograde/transit determination, divination, journal write,
   or reference library.

MAGICK / OVERVIEW places original USNO lunar and solar/twilight
instruments in two full-width vertical bays on the same screen.
MAGICK / LUNAR AND SOLAR / LUNAR CYCLES and PRACTICE CALENDAR show
the live Moon instrument. The calendar route explicitly does not write
or schedule anything. SEASONS shows the solar reference but not
unimplemented exact solstice/equinox instant calculations.

MAGICK / PLANETARY MAGICK / HOURS and TRADITIONAL TIMING show the
existing solar/twilight reference, without planetary-hour or auspicious
timing calculations. CORRESPONDENCES shows visible planet rise/set
as astronomy but no claimed metaphysical association table.
MAGICK / ASTROLOGY / CHARTS shows USNO current sky solely as
astronomical evidence, NOT a zodiac natal chart.

MAGICK / ASTROLOGY / ZODIAC, ASPECTS, RETROGRADES and TRANSITS,
MAGICK / DIVINATION / TAROT and SYMBOLISM, and GRIMOIRE / REFERENCES
and JOURNAL are visible reserved work areas; their explicit notes
name required missing inputs and distinguish cultural interpretations
from scientific observations.

The module does not modify COSMOS, SKY, weather sources, archived files,
calendar tasks, saved user settings, UI player ownership, terminal
hosting, MAGICK user data, or existing canonical subject navigation
definitions. Only the subject browser mounts the scoped new MAGICK pane.

## HOW TO USE

Once GitHub is merged and a local update is **separately approved**:
Weather Station > SUBJECTS > MAGICK > OVERVIEW.
Use ASTROLOGY, PLANETARY MAGICK, LUNAR AND SOLAR, DIVINATION or
GRIMOIRE to inspect the relevant route. Instrument data will appear
only where observational COSMOS feeds exist and the location/date
can be resolved. Other routes clearly state the not-yet-implemented
capability; nothing is generated or saved on entry.

The CLASSIC SKY and COSMOS astronomy remain independent and unchanged.

## VERIFY

- Citable source truth: original USNO Moon and Celnav services, computed
  solar/twilight logic and planet rise/set in StationSky.
- Scope: 16 exact MAGICK descendants in canonical subject policy.
- Focused tests check each route, upstream COSMOS linkage, readable
  source/interpretation disclaimers, and no new writers/fetchers.
- All previously merged subject tests and full Weather teardown CI
  must be green before merge.
- Node/CI evidence is **not** a local Fedora or Quickshell visual
  verification or guarantee that USNO feeds are currently available.

## WATCH OUT FOR

- Do not conflate visible constellations with zodiac signs.
- CelNav altitude/azimuth is not tropical/sidereal ecliptic longitude,
  a house chart, or astrological aspects.
- Planet rise/set does not determine retrograde motion.
- Sunrise/sunset or twilight alone do not implement traditional
  planetary-hour arithmetic.
- USNO astronomical values are not universal symbolic meanings.
- Tarot, journal, reference library, and recorded magical correspondences
  remain unimplemented. This PR does NOT commit to choosing a
  specific spiritual tradition or storing sensitive personal readings.
- No local machine write, process restart, installation or runtime change.

## CHECKLIST

- [x] Current GitHub/ownership and Syntagma/Hospital preflight
- [x] 16 MAGICK leaf routes and conservative source mapping
- [x] Eight existing observational cross-domain views
- [x] Eight clearly marked unimplemented interpretive views
- [x] No independent data/time/storage service and no fake readings
- [x] MAGICK subject browser and header/status integration
- [x] Focused tests and workflow
- [ ] Latest CI verified all green
- [ ] Merge to main under standing operator authorization
- [ ] Local Quickshell visual/data/user acceptance

## NEXT

Review CI, repair regressions within this narrow Weather scope,
merge when checks pass, report commit, then perform the TOOLS migration
without taking over storage/archive ownership. A separate future
assignment can design precise astrology, optional reference traditions,
tarot interactions and a privacy-safe grimoire after explicit decisions.

## DECISIONS

Operator previously authorized a verified GitHub merge. No local
modifications or live Hospital session registration have been assumed.
This phase deliberately implements honest source reuse, not ritual
judgment or a spiritual engine.
