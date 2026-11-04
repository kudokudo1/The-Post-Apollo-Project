# HOSPITAL REPORT // MAGICK V4c True Heliocentric Spatial

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station // Visual Intelligence + MAGICK Spatial Handoff
DOCTOR // Nurse 2, external browser worker
PROVIDER // OPEN AI // CHATGPT
CONNECTION // EXTERNAL / HOSPITAL-COMPATIBLE (not live registered)
ASSIGNMENT // Source-verified Sun-centered JPL geometric XYZ and linked viewer
PHASE // Draft GitHub implementation; CI and native acceptance pending
GIT // feat/weather-magick-v4c-heliocentric-spatial-20261104

## IMPLEMENTATION

Operator explicitly reported that the MAGICK worker is temporarily unavailable and granted temporary, bounded cross-COSMOS/MAGICK implementation authority. This does not claim live Hospital ownership transfer. Syntagma AGENTS and current Hospital, permissions and working-guide protocols were read. GitHub source and concurrent PRs checked; V4b PR #1231 merged, no competing open Weather/COSMOS/MAGICK PR at initial preflight.

A new independent scientific contract, scripts/weather/celestial_spatial_data.py, validates Sun-relative geometric XYZ in AU at the original exact M4 UTC sample grid. The SUN is the actual origin (0 AU), while other exact NAIF body IDs preserve the real geometric Sun-relative SPK vector. No real body is silently mapped to a planetary barycenter.

The existing scripts/weather/celestial_visual_data.py accepts optional boolean include_heliocentric_spatial (default FALSE for old M4 callers). When true, the same on-demand CALCULATE opens the SAME JPL SPK kernel once, uses the SAME UTC grid and timescale, and calls the existing M1 geometric vector path. Skyfield frame_xyz(ecliptic_frame) yields true-ecliptic-of-date XYZ in AU, not light-time-adjusted apparent geocentric coordinates. The original M4 apparent Earth-centric results and aspect calculations are not rewritten.

The existing services/weather/CelestialVisualQueryPolicy.js explicitly requests this second product and requires its format/frame/origin to match. The existing user controls, two-body presets and on-demand service process remain.

New widgets/weather/StationCosmosHeliocentricPolicy.js validates all geometric samples against source M4/V4a provenance and UTC indexes, strict body IDs and vector norms. Malformed/missing/stale samples display unavailable, never simulated zero positions.

New widgets/weather/StationCosmosHeliocentricPane.qml draws true Sun-centered XYZ snapshots, with readable source IDs, AU-scaled radial rings, selected sample, and TOP/TILT orthographic projection views. TILT uses the source Z component; rings remain reference guides, not orbital tracks. Actual body clicks, sample drag and spatial wheel zoom are included.

The existing Lane B StationCosmosCelestialNetwork.qml now has CHORDS / DEPTH / HELIO modes, sharing selected body/UTC source sample and inspector. The MAGICK-owned StationMagickCelestialInstrument.qml receives only an additional spatialPayload binding from its existing visualData; it does not open a second kernel or separate process. No StationSky, shared SUBJECTS route, CLASSIC migration, data store, or local Fedora file changed.

## HOW TO USE

After PR review, authorized merge, and separately approved Fedora deployment:

1. Open Weather Station > SUBJECTS > MAGICK > Celestial Reference.
2. Choose a source pair/date/span, then CALCULATE. Existing geocentric data and new Sun-centered geometric XYZ come from the same on-demand kernel.
3. Select NETWORK > HELIO. Use TOP or TILT to choose a projection. Source bodies remain identified by their exact names; click one for its AU distance and measured XYZ. Drag horizontally for real UTC samples. Wheel changes spatial scale. Switch CHORDS/DEPTH/HELIO without changing time/body selection.
4. If a target/ephemeris is unavailable, expect unavailable, not invented coordinates.

## VERIFY

tests/weather/test_celestial_spatial_v4c.py tests the strict Python source contract, opt-in behavior, Sun origin, numerical errors, UTC monotonicity and optional actual DE440s comparison against an independent M1 heliocentric snapshot. tests/weather/test_cosmos_heliocentric_spatial_v4c.js validates source M5/V4a/V4c relationship, projection, bad-source refusal, hitboxes and existing one-owner Quickshell bindings. Updated the original M5c request fixture to explicitly require spatial data. Both relevant GitHub workflows now trigger new tests, including a real disposable JPL kernel integration check. Final PR-head status is pending independent verification.

## WATCH OUT FOR

V4b DEPTH = apparent, geocentric, Earth-centered; V4c HELIO = geometric, heliocentric, instantaneous Sun-centered. They answer different questions. A Sun-centered XYZ sample can show physical relative positions, but the viewer does not interpolate complete orbital trajectories or guarantee all planets are present.

The M5c source deliberately returns two selected bodies (including exact system barycenters where requested); the rest of the solar system is not fabricated. True ecliptic-of-date rotates with each sample epoch. A separate fixed-inertial J2000 view would require its own clearly labelled source contract.

Only an operator-approved local install/restart can verify real Quickshell rendering and local JPL availability. GitHub tests cannot prove native pointer and font behavior. No live Hospital registration, GitHub merge or final user DONE is asserted. The temporarily absent MAGICK worker retains their prior Room and must be offered this branch/PR on return.

## CHECKLIST

- [x] Read Syntagma protocols and current source; verify worker handoff scope
- [x] Add Sun-centered geometric JPL XYZ source and backward-compatible M4 opt-in
- [x] Reuse the original single on-demand CALCULATE process and UTC sample index
- [x] Add HELIO TOP/TILT and shared CHORDS / DEPTH selection
- [x] Add strict Python/Node tests and real JPL verification workflow
- [ ] Final GitHub CI and branch conflict review
- [ ] Approved merge and separately authorized local installation
- [ ] Real Skyfield/JPL and mouse/UI acceptance

## NEXT

Verify GitHub PR-head CI and fix evidenced defects only. When authorized to install locally, test Moon/Sun and Jupiter/Saturn barycenter presets, compare real AU distances/XYZ, drag sample sync and TOP/TILT focus. The returning MAGICK worker must reacquire current Hospital Room, Patient, GitHub HEAD and ownership; use this handoff as historical recovery evidence, not a live state claim.

## DECISIONS

Bounded temporary cross-room implementation authorization was explicitly provided. Distinct geocentric apparent and heliocentric geometric frames remain scientifically labelled; no fake planets, added autonomous process, local mutation or irreversible activation.
