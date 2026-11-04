# Hospital // Weather Station COSMOS V4a JPL Relationship Network

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station // Visual Intelligence, Lane B
STAFF ROLE // Nurse 2, external Hospital-compatible, not live registered
ASSIGNMENT // V4a source-backed circular relation network using MAGICK M4 data
STATE // Draft branch, CI and MAGICK visual-owner review pending
GIT // feat/weather-cosmos-v4a-jpl-relationship-network-20261104

## IMPLEMENTATION

Verified V3d #1206 merged, current MAGICK M4/M5 source and operator design PR #1191. No open Weather/MAGICK/COSMOS PR found at assignment start.

New read-only policy: widgets/weather/StationCosmosCelestialNetworkPolicy.js. Consumes only the already validated model from StationMagickCelestialVisualPolicy.model(raw M4 JSON), with source ephemeris hash prefix, exact aligned UTC sample and geocentric apparent true-ecliptic-of-date frame. Refuses missing or inconsistent source bodies, pairs and derived separations. Supports 2 to 4 source bodies but cannot invent additional source data.

New circular Canvas: widgets/weather/StationCosmosCelestialNetwork.qml. Actual geocentric ecliptic longitudes determine node angle. Chords connect only source-verified pair measurements, with a numeric separation inspector, original M4 aspect tags (if any), sample time, source ID and hash. Ring radius is a display convention, not orbital size, heliocentric position, physical distance, or a three-dimensional sky-angle projection. Click actual nodes or source edges; direct body buttons support coincident placements. Pointer drag navigates actual M4 samples; wheel changes existing M4 time zoom. No new timer, process, network fetch or store.

Shared visual seam (draft for review): widgets/weather/StationMagickCelestialInstrument.qml receives a fifth NETWORK mode, mounted in its existing chart frame with the same graphModel, selected body, focusIndex and neon preference. ZODIAC, MOTION, ASPECTS, RELATIONS, all controls, and original source owner are preserved. Does not modify MAGICK M4 calculation/service policy, StationSky, shared SUBJECTS navigation, CLASSIC, HOME, or the JPL Python backend.

## HOW TO USE

Following MAGICK visual-owner review, authorized merge and independently approved local Fedora installation:

1. Open Weather Station > SUBJECTS > MAGICK > existing celestial reference.
2. Use existing date/pair/span settings and CALCULATE, as currently required by the sole on-demand JPL service.
3. Choose NETWORK beside ZODIAC/MOTION/ASPECTS/RELATIONS. View two source position nodes and their measured ecliptic-longitude gap. Click to inspect, drag to select a real sampled UTC time, scroll to zoom the existing time window, or select another mode to return.

The current live calculation owner in CelestialVisualService.qml deliberately accepts only two bodies and one relationship per request. Although the M4 offline model supports up to four bodies, **V4a renders just the actually requested two live bodies**. Expanding to four or more, linking spatial/heliocentric views, or creating an aspect-network search requires a later MAGICK M6/M7 assignment and owner approval. No automatic JPL installation or live calculations are claimed.

## VERIFY

New tests/weather/test_cosmos_jpl_relationship_network_v4a.js passes synthetic fixtures through the real existing M5 validated model before constructing the network. Covers exact UTC provenance, current two-body mode, future four-body model capability, cardinal longitude geometry, north-wrap, genuine source pair measurement, body/edge hitboxes, missing/misaligned source rejection and lack of second provider.

New .github/workflows/weather-cosmos-jpl-network-v4a.yml tests V4a plus existing M5 source, charts and input regressions. The MAGICK M5j workflow also triggers on the changed instrument file. Inspect final PR-head CI results. Source tests do not prove native Qt/Quickshell rendering, pointer delivery, label overflow, drag or scroll fit.

## WATCH OUT FOR

**MAGICK worker ownership:** This PR touches a MAGICK visual component for a read-only mode mount. No open PR is NOT a transfer of component ownership. Obtain the MAGICK visual owner's review and operator merge approval before integration. Keep draft for now.

Source-bounded claims: the network displays apparent geocentric ecliptic longitude of calculated samples and pairwise *longitude difference*, not physical orbits, heliocentric 3D positions, angular separation on the sky, or spiritual causality. Backend-provided aspect labels are not free-form interpretations.

No sample is invented if JPL kernel or Skyfield are missing, M4 not loaded, source format invalid, or route inactive. The current M5 service is on-demand, not streaming. Native demonstration still requires the user's installed runtime and source to be present.

Potential separate Weather Teardown CI mismatch after CLASSIC retirement was documented during V3d; recheck fresh results and avoid altering unrelated owner files under Lane B.

## CHECKLIST

- [x] Current GitHub source and PR ownership audit
- [x] Read-only source-backed polar network model
- [x] New circular UI and measured relation inspector
- [x] Source index scrubbing / zoom without new collector
- [x] Narrow shared M5 visual mount kept in review branch
- [x] New regression tests and dedicated workflow
- [ ] Final GitHub CI checked
- [ ] MAGICK visual-owner cross-seam review
- [ ] Operator-authorized merge and desktop installation
- [ ] Native Canvas/render/mouse acceptance
- [ ] Final operator acceptance

## NEXT

Inspect PR-head CI, fix evidenced failures on branch, and hand draft to MAGICK visual owner for cross-seam review. After authorized deployment, inspect actual M4 JPL CALCULATE and UTC/longitude correspondence before considering multi-body and spatial work.

## DECISIONS

Stay in Lane B Visual Intelligence. Reuse the existing M4/JPL backend, preserve MAGICK ownership and the SOURCE vs INTERPRETATION boundary, and do not modify global navigation, data collection, storage, or operator machine.
