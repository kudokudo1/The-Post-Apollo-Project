# Weather StationW // MAGICK M5 First Interactive Celestial Instrument

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather StationW / MAGICK Celestial Visuals
WORKER // External ChatGPT Hospital-compatible developer; no live Hospital room registration established
ASSIGNMENT // First standalone M5 visual consumer of M4 planetary series and aspect events
STATE // Draft implementation, CI verification and operator acceptance pending
BASE // GitHub main at b599607ed456df293e2dd17b2f453d00751c0935
BRANCH // feat/weather-magick-visual-instruments-m5-20261103
OWNERSHIP // New isolated M5 component/policy/test/CI only; no existing Station pages, COSMOS services, provider, store or CLASSIC migration ownership transferred

## IMPLEMENTATION

New files:
- widgets/weather/StationMagickCelestialVisualPolicy.js: read-only data validation, source gating, chart projection, window selection, hit testing and unit labels.
- widgets/weather/StationMagickCelestialInstrument.qml: standalone 470px-tall visual instrument with three modes and usable mouse/button controls.
- tests/weather/test_magick_celestial_visual_m5.js: source validation and interaction contract tests.
- tests/weather/test_magick_celestial_visual_m5_jpl.js: actual M4 JSON to M5 policy integration check.
- .github/workflows/weather-magick-celestial-visual-m5.yml: isolated Node tests, existing COSMOS/MAGICK regression tests, and JPL-backed M4-to-M5 integration inside disposable GitHub CI.

M5 consumes version post-apollo.weather.celestial-visual-data.v1, produced by merged M4. It requires producer provenance (engine, ephemeris ID, version, time-data identifier and a 64-character checksum) and geocentric apparent true-ecliptic-of-date coordinates. It refuses malformed source rows and mismatched time axes, and never creates fabricated planetary positions.

Three connected visualization modes:
1. ZODIAC WHEEL: measured ecliptic longitudes placed around 360-degree tropical reference sectors, selectable planet markers, traditional aspect lines only where M4 actually reports them. Constellations and tropical signs are NOT the same coordinate reference.
2. MOTION CURVE: unwrapped ecliptic longitude chart from M4 samples. Real retrograde motion can slope backward across a 0/360 longitude boundary.
3. ASPECT GRAPH: actual pairwise ecliptic-longitude separation over time from synchronized M4 relationships. This is NOT 3D angular distance or occultation prediction.

Both chart modes include source-provided event timeline markers. No additional ephemeris calls are made by the QML component; no interpolated points are presented as source samples. Zoom affects the visible sampled window. Panning shifts that window. Selection/locking always chooses an actual timestamp.

Interactivity already coded in the standalone component:
- Three clickable mode buttons (wheel, motion, aspects).
- Mouse scroll zoom, chart drag pan, pointer hover, click to lock a measured time.
- Wheel marker hit testing chooses an actually present celestial body; dragging on wheel scrubs the visible time window.
- BACK/NEXT adjust time selection by one real sample; UNLOCK returns to hover; RESET restores zoom/pan/selection.
- Inspector displays selected body's degree and M4 finite-difference longitude rate.
- Source indicator shows ephemeris file and checksum prefix.
- An explicit unavailable state appears when no source-stamped M4 JSON is supplied.

This phase does NOT wire the instrument into StationMagickSubjectPane or the production Quickshell data/scheduling path. Existing MAGICK routes remain unmodified to avoid collisions with ongoing CLASSIC/SUBJECTS and COSMOS workers.

## HOW TO USE

The QML component expects a property assignment:

    StationMagickCelestialInstrument {
        anchors.fill: parent
        visualData: m4JsonObject
    }

Where m4JsonObject is the already parsed, validated output of the existing
scripts/weather/celestial_visual_data.py backend, including its provenance.

No new live Station UI button is available at this milestone, and no standalone
provider, file reader, timer, direct Python execution, or JSON loader was
added. The owning Station integration worker must choose a secure, bounded,
single-owner M4 JSON transport and explicitly mount the instrument on an
approved MAGICK route before runtime interaction can be accepted.

## VERIFY

Node contract tests (no local Qt or ephemeris required):

    node --test tests/weather/test_magick_celestial_visual_m5.js

Current-MAGICK/COSMOS regression checks:

    node --test tests/weather/test_magick_subject_panels_g1.js
    node --test tests/weather/test_cosmos_visual_interactions_v2r.js

GitHub CI also runs M4 with the official JPL DE440s kernel in a disposable runner, then validates the actual JSON under tests/weather/test_magick_celestial_visual_m5_jpl.js. No fake values are presented as measurements.

Tests check:
- Missing/wrong source/provenance and wrong frame are refused;
- 360-degree longitude wraps display continuously as 350, 365, 380;
- body/time series and pairwise aspect values remain synchronous;
- invalid/negative/NaN or misaligned source data are rejected;
- zoom, index selection, marker hit testing and inspector values are bounded;
- actual QML handlers are attached for user interactions;
- no additional provider process, timer, location lookup, network or journal is created.

Important: Node tests inspect input policy and QML wiring. They do NOT prove Quickshell renders correctly or every mouse gesture works in a live panel. The isolated GitHub runner is an integration test for the data layer, not a full Qt screenshot/pixel/input test.

## WATCH OUT FOR

- The instrument is deliberately not yet mounted in the existing Weather Station. A user opening the live MAGICK route will not see these visualizations until the separate integration step is authorized and tested.
- QML Canvas wheel and chart are interactive source consumers, not physical three-dimensional orbital views. A heliocentric orbit scene needs a distinct coordinate contract.
- Traditional aspect lines and tropical sign labels are interpretive conventions overlaying astronomical longitude; no causal/metaphysical claims are inferred from geometry.
- The existing M4 contract limits this first viewport to four bodies and 721 sampled points, with optional event markers for at most two bodies.
- Source checksums are provenance identifiers, not a cryptographic authenticity guarantee for a user-supplied payload.
- No user-local Fedora files, installed packages, QuickShell process or live UI were modified. A GitHub-only merge does not install a widget on the operator machine.
- Existing Weather source owner may choose a different placement/geometry; preserve the Post-Apollo design rules, magenta/cyan semantic palette, and the left mode rail in the live app.
- M5 renders a wheel of ecliptic longitudes, NOT a proper local topocentric sky or independently positioned star map.
- The active COSMOS source integration and CLASSIC-to-SUBJECTS migration work should retain their ownership.

## CHECKLIST

- [x] Current M3/M4 merge status and source policies inspected
- [x] Standalone source-backed M5 geometry and mouse interactions
- [x] No fake dataset, extra provider or timer
- [x] Node validation and behavior tests
- [x] Real M4-to-M5 JPL integration workflow
- [ ] Final GitHub PR-head checks
- [ ] QML runtime render, real pointer clicks and scroll/drag acceptance
- [ ] Approved M4 data transport and live MAGICK route integration
- [ ] User acceptance after live verification

## NEXT

M5b needs the existing Weather Station owner to expose a safe, read-only
single-owner transport for M4 JSON and mount the instrument under the
appropriate MAGICK route (zodiac, aspects or retrogrades), preserving the
current left-rail + INDEX layout. Verify actual drawing, clipping, hover,
click, scroll zoom, drag pan, focus and resizing in a disposable environment
before live activation. Later add orbital views, deeper chart lenses and
interpretation libraries, keeping raw astronomy separate.

## DECISIONS

User authorized continuation after M4; scope confined to new isolated visual
files. No merge, production activation, native package installation,
local-machine changes or live Hospital registration were performed here.
