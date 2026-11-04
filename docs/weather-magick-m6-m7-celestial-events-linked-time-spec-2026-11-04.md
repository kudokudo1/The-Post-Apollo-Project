# MAGICK // M6–M7 Celestial Event Research and Linked-Time Design Specification
## Research checkpoint // November 4, 2026

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather StationW / MAGICK Research and M6–M7 Architecture
ROLE // External Hospital-compatible ChatGPT source/research worker, not live Hospital-registered
ASSIGNMENT // Reconcile measured celestial relationships, event categories, priorities and shared NOW/past/future exploration with existing MAGICK capabilities
BASE // main f530b0fd88e5cca811a4711b72cb18f734aa0330
CHANGE CLASS // Documentation-only research and bounded design proposal
AUTHORITY // Operator chooses final appearance, importance semantics and tradition rules. Nothing in this document authorizes runtime source edits, a second provider, a merge, local installation, a personal journal or a production rollout.

## IMPLEMENTATION // Findings and proposed contracts

### 1. Verified current source baseline

GitHub source checked on Nov 4, 2026:

- M5k adjustable date calibration PR #1199 is **merged**; its final head has 13/13 successful GitHub checks. The source still supports one JPL Process owned by WeatherStationW.
- MAGICK already exposes source-provenanced geocentric apparent true-ecliptic-of-date longitudes/latitudes/distances and a sampled time series; direct/retrograde movement; finite-difference station estimates; major ecliptic longitude aspects; exact aspect event crossings searched within bounded windows; optional tangent candidates; selected event/timeline navigation.
- scripts/weather/celestial_visual_data.py allows 1–4 chosen source bodies and produces pairwise relationship **sample** data for combinations, but rejects include_events=true with more than two bodies. That restriction is an explicit backend contract.
- services/weather/CelestialVisualQueryPolicy.js exposes six hardcoded **two-body** presets with event searches enabled. It does not offer arbitrary multibody network selection.
- The MAGICK UI already has ZODIAC, MOTION, ASPECTS and RELATIONS, a grab-and-drag timeline for loaded M4 source samples, NOW/TODAY navigation, adjustable date jump, and bounded date/source requests. Date changes still require explicit CALCULATE; do not present this as continuous preloaded astronomy history.
- Interpretation remains marked NOT CONNECTED in StationMagickSubjectPanelPolicy.js. Neither current astronomical calculations nor glyphs are a full natal chart, eclipse detector, or interpretation library.
- Existing operator direction in docs/weather-magick-operator-design-decisions-2026-11-04.md: BOTH network and physically meaningful solar-system spatial modes, linked by time/selection; Western tropical interpretation first, Hellenistic second, Vedic/Jyotisha third; combined MAGICK home; historical/future exploration centered on NOW.
- No open MAGICK or competing Weather source PR was returned in the Nov 4 GitHub preflight. Ownership must still be rechecked before any implementation.

### 2. What actually counts as a connection?

Never conflate physical orbit geometry, a line representing a measured relationship and a tradition-specific claim about meaning.

**A // Measured pairwise relationship (NETWORK EDGE)**

- angular difference in geocentric apparent true-ecliptic longitude, degrees 0–180; explicitly named longitude-separation rather than 3D sky angular distance;
- conventional major aspect targets: conjunction 0°, sextile 60°, square 90°, trine 120°, opposition 180°;
- relationship within a named configurable orb: this is an interpretive tolerance, not a physical measurement threshold;
- an exact longitude-aspect crossing is a calculated event; an approximate aspect within orb is a relationship **state**; do not treat them as the same kind of thing;
- applying/separating classification is part of a tradition's analysis of approach to exactitude. It must use a tested signed-distance/time-evolution rule, including wraparound, multiple crossings and station reversals. An absolute separation value alone is not enough for all oriented aspect cases;
- extra minor aspects (30°, 45°, 72°, 135°, 144°, 150°, etc.) remain research candidates, **not silently added** to the first network or assigned metaphysical importance.

**B // Single-body motion or change (NODE STATUS + TIMELINE EVENT)**

- direct/retrograde status is **apparent motion** in the chosen geocentric frame, not the planet physically going backwards in its heliocentric orbit;
- estimated apparent station direct↔retrograde is a time event with method/tolerance and a separate uncertainty label;
- zodiac sign ingress/egress is a **crossing of a named tropical sign-sector boundary**, not a planetary aspect to another physical body. Requires an explicit exact-boundary event finder before showing an ingress timestamp. Do not infer a precise instant from 12h sampled rows;
- a planet may simultaneously have a status and multiple pairwise connections. Do not draw retrograde as a special fake edge.

**C // Multi-body configurations or observational phenomena (EVENT / ANALYSIS)**

- Moon/Sun phase state and new/full quarter event times: additional phase-angle geometry and exact-search contracts are needed to claim exact phases; a Sun–Moon 0°/180° ecliptic longitude relationship alone does not prove an eclipse or a physically exact phase event.
- solar or lunar eclipses: require lunar orbital nodes/latitude, Sun/Moon/Earth geometric size/shadow and explicit observer or region when visibility is claimed. Never label a conjunction or opposition as an eclipse solely from the two longitude values.
- equinox/solstice: compute from the appropriate solar tropical longitude crossing with declared frame and epoch, NOT from a generic sign-label string. Existing sampled Sun state can inform a design but is not an accepted exact seasonal event catalog.
- lunar nodes, declination, house cusps, ascendant/MC, planetary hours, fixed stars, and natal/transit charts require their own definitions, inputs, kernels or verified algorithms. They are not present as accepted current network events.
- heliocentric 3D spatial relationships are **not** the same edges as geocentric apparent ecliptic longitude aspects. The spatial view uses a separately valid frame, origin, distance units, projection and source positions.

### 3. First graph visibility model: useful without pretending a universal importance scale

Operator intent: show the connections most useful for understanding the *selected system*, without forcing the operator to pick unfamiliar astrological terminology now.

**Proposal, NOT an approved universal significance ranking:**

- **Clearly visible by default:** source-calculated exact major-aspect events in the active requested window and pairwise major-aspect states within the chosen orb, for currently selected or inspected bodies. Highlight the presently inspected event and selected body.
- **Timeline annotations (not edges):** retrograde/direct and station estimates; future exact seasonal/phase/eclipses only after a dedicated validated source or solver exists.
- **Subdued and inspectable:** other measured pairwise connections outside selected orbs, unselected planets, past/future events beyond visible time range. Make them discoverable through "ALL RELATIONSHIPS" or a context filter rather than deleting or pretending they do not exist.
- **Not displayed as true events:** anything absent from the source window, a finite-sampling tangent candidate as if exact, an unsolved eclipse, inferred natal-chart condition without birth data, or a tradition's claimed influence as though it were a measured interaction.
- **Separate user-controlled filters:** ALL, MAJOR ASPECTS, MOTION / STATIONS, UPCOMING, HISTORICAL, SELECTED BODY, SOURCE ONLY, and later BY INTERPRETIVE LENS once the lens actually exists.
- Event color indicates **type/source confidence and focus**, not metaphysical strength. MAGICK may choose a selected-lens explanatory ranking later, with named rule/version and citations; preserve the default astronomy presentation with no lens.
- Avoid one global fixed "importance" number. The operator's aim is a meaningful overview, not a rank without provenance.

Potential measured/derived event fields: event_id, kind, body_ids, utc_time, source_precision, frame, longitude_angle_deg (if pairwise), orb_definition_id, exact_or_candidate, calculation_method, backend_engine_version, kernel_sha256, interpretation_lens_id (nullable), primary_reference_ids (nullable), source_status, visible_time_window.

### 4. NOW-centered temporal observatory

**Operator direction already confirmed:** Start in NOW, then pan/scroll backward and forward through past and upcoming calculated celestial conditions.

The time explorer must distinguish:

1. **Epoch / cursor UTC:** the exact selected instant, or the nearest existing sampled time when the user is looking at a loaded M4 chart. Explain the difference.
2. **Loaded/visible range:** what samples and events have actually been calculated and retained for the current body request. This is not the same as the calendar navigation bound.
3. **Step calibration:** the user-selectable integer date jump from M5k, currently 1–3650 days and default 5; this changes the requested calendar day, not graph precision.
4. **Chart SPAN:** current 14/29/90-day request windows. A 12-hour M4 sample is a measured diagram point; marker event times can lie between samples.
5. **Mode continuity:** switching NETWORK ↔ SPATIAL preserves selected epoch, source body IDs, highlighted event and focus where valid. The destination mode must have its own source data available for that epoch; it cannot reuse geocentric aspects as heliocentric coordinates.
6. **No data behavior:** show exact unavailable/out-of-range/source-not-yet-calculated states. Do not draw plausible-but-unverified trajectories while waiting on the on-demand engine.
7. **Past and future semantics:** the underlying ephemeris can calculate geometries for supported historical/future epochs; a future calculated aspect is not scientific confirmation of a future psychological or human event.

**Proposed phased interaction plan:**

- **Phase A / existing:** NOW/TODAY, editable ±N UTC calendar shifts, loaded-window thumb dragging, selectable event markers, manual CALCULATE. Keep this accepted behavior unchanged.
- **Phase B / design later:** network and spatial views both bind to a root-owned read-only selectedTimeUtc / selectedBodies / selectedEvent and calibrated bounds; no new ticking clocks, independent caches, or duplicate M4 processes.
- **Phase C / only after explicit approval:** seamless cross-window panning could request adjacent ranges with bounded caching/retention, source gating, cancelation and performance controls. It should not silently submit hundreds of kernel jobs or assume infinite coverage. Offline and partial states must remain transparent.

**Draft read-only selection shape (conceptual, not authorized new schema):**

    {
      selection_kind: "now | sample | event | requested_instant",
      selected_utc: "<exact UTC timestamp>",
      source_sample_utc: "<exact sampled timestamp or null>",
      selected_bodies: ["moon", "sun"],
      selected_event_id: null,
      visible_start_utc: "<UTC>",
      visible_end_utc: "<UTC>",
      source_product_id: "<M4 graph model ID>",
      source_provenance: { engine: "...", ephemeris_sha256: "...", frame: "..." },
      active_mode: "network | spatial",
      active_lens: "observation | western_tropical | hellenistic | jyotisha"
    }

A source sample time and an event time must not be conflated. The schema would require normalization/versioning and validation before code, and active_lens must not imply all lens implementations already exist.

### 5. Bounded engineering dependencies and acceptance tests

**M6 // Event catalogue and data breadth, proposed technical order:**

- M6-A: inventory all existing M4 body IDs, event types, units, exactness/uncertainty and query limits; define stable source event IDs with backward-compatible adapters.
- M6-B: allow **more than two selected bodies** to be inspected without falsely claiming one exhaustive event search. Candidate design: keep M4 multi-body sample generation and separately run bounded pair-event queries or redesign the event finder to explicitly handle N pairs with strict time/body/CPU limits. Choose after performance profiling and owner review.
- M6-C: compute applying/separating and a source-backed orbital motion-state segment per body; test signed boundary behavior at 0/360, station reversals and repeated passes.
- M6-D: research exact sign ingress and phase-event solvers using JPL geometry and independent reference checks. Eclipses, nodes, houses and solstice/equinox catalogs require dedicated correctness acceptance and should not be rushed into M6-A.
- M6-E: define the object/reference frame data needed by spatial mode, including heliocentric origin, cartesian coordinates, epoch, units and observer. Keep geocentric apparent aspect derivations separate.

**M7 // Linked views (operator selected both):**

- NETWORK: selectable body nodes; source-separation edges; hover/click inspection; filter exact/within-orb/other; label angle and UTC; color/event status; reduced clutter; deterministic subset handling.
- SPATIAL: 2D initial physical solar-system depiction only from source-provided heliocentric/barycentric cartesian geometry at the same UTC, with truthful distance scaling and declared frame. 3D is optional later and not assumed by the network milestone.
- Both respond to a single selected time/event/body contract. A route change should not change unrelated data or create another service.
- Test opening at NOW, stepping ±1/±5/±10, selecting a historic and future exact aspect, zooming, filtering bodies, switching modes, unavailable kernel, out-of-coverage epoch, redraw stability and source hash identity.

**Explicit exit gate:** The operator can select NOW; navigate past/future with calibrated steps or a visible thumb; pick an exact source event and see the same timestamp/body selection in both correctly framed views; identify what is an aspect, a motion-state change or a later unsolved phenomenon; and access the actual M4 provenance. The contract must pass source/unit/coordinate checks and a live native Quickshell inspection. A pretty mock drawing is not completion.

### 6. Research boundary / interpretation layer

The following are historical or modern *astrological traditions*, not measured physical forces. A lens must cite its author, work, edition/method, convention and exact proposition. Do not generate generic "planet X causes Y" statements or silently combine modern and ancient methods.

- **First, modern Western tropical:** comparison of major aspect language; modern psychological meanings; orb conventions; sign/planet distinctions; retrograde and station readings. Base positions remain the same geocentric astronomical data.
- **Second, Hellenistic/traditional Western:** separate documented rules/terms and sources; not all ancient authors agree. Avoid falsely treating the entirety of ancient practice as one book or importing modern outer-planet meanings.
- **Third, Vedic/Jyotisha:** later explicit sidereal frame/ayanamsa and source schools before any sign/date mapping. Do not silently change the timestamp or give two irreconcilable labels without explaining the convention.
- **Always available OBSERVATION:** facts/geometry regardless of interpretation; changing lens must not mutate the source ephemeris or event timestamps.

## HOW TO USE

This document is a **design/research reference** for the M6 numerical/event-contract and M7 visual workers. Read alongside docs/weather-magick-operator-design-decisions-2026-11-04.md and the actual GitHub source before any implementation.

For the operator: the first connected graph can emphasize verifiable major aspects, stations and selected bodies, with filters to expose everything else. The time cursor begins at NOW, allows backward/forward exploration and remembers the selected epoch across the two modes. No new spiritual hierarchy has been imposed: later Western tropical lenses can provide the sourced interpretation and its own preference rules only after review.

## VERIFY

**Source inspected:** scripts/weather/celestial_visual_data.py, celestial_dynamics.py, services/weather/CelestialVisualQueryPolicy.js, StationMagickSubjectPanelPolicy.js, MAGICK M5k handoff and operator direction record. M5k PR #1199 verified merged and 13/13 checks completed. This research document adds no runtime source file, test or dependency.

**External reference checks (accessed Nov 4, 2026):**

- NASA on apparent retrograde motion, Earth perspective: https://science.nasa.gov/resource/whats-up-october-2022/ and https://science.nasa.gov/image-article/apod-2026-may-6-the-retrograde-dance-of-saturn-and-neptune/
- NASA on eclipse geometry and lunar orbital inclination: https://science.nasa.gov/moon/eclipses/ and https://science.nasa.gov/eclipses/faq/
- NASA eclipse glossary on nodes: https://science.nasa.gov/eclipses/glossary/
- Astrodienst aspect definitions and major/minor angles: https://www.astro.com/astrowiki/en/Aspect and https://www.astro.com/astrology/in_aspect_e.htm
- Astrodienst applying/separating and orb conventions, as tradition descriptions rather than physics: https://www.astro.com/astrowiki/en/Applying_Aspect and https://www.astro.com/astrowiki/en/Orb
- Internet Encyclopedia of Philosophy on Hellenistic writers Ptolemy/Valens and differing practice: https://iep.utm.edu/hellenistic-astrology/

All external interpretive meanings in this document are identified as conventions. No present-day planetary positions, future event times, spiritual effects, or ephemeris results have been fabricated.

## WATCH OUT FOR

- The prioritization above is **a proposed first UX heuristic**, not a canonical magical, spiritual or universal significance order. The user specifically asked not to be forced to preselect unknown categories.
- An aspect is not an eclipse; retrograde is not a two-planet edge; a sampled near-tangent is not a confirmed exact contact. Distinguish exact calculation, finite-difference estimate and possibility/candidate at every layer.
- "Observer" and "reference frame" must be visible when modes represent different geometries. Do not label ecliptic longitude separation a three-dimensional sky angular distance.
- Nontrivial date jumps may exceed active JPL kernel bounds even when the current UI allows the date; report unavailability rather than replacing it with synthetic data.
- No natal/horary/personal reading can be made responsibly without choosing relevant method and location/time input; don't derive one from system clock.
- Copyright: bibliographic entries, summaries and short source-attributed explanations are allowed; do not copy textbook delineations wholesale into MAGICK or vendor proprietary charts.
- No local Fedora writes, Quickshell restart, external provider installation or user-location inference were done for this research.

## CHECKLIST

- [x] Verify M5k current main and successful CI; inspect active owners.
- [x] Separate aspects, motion changes and larger astronomical phenomena.
- [x] Specify default relationship visibility without hiding available evidence.
- [x] Define NOW-centered timeline with precise source-sample versus event-time semantics.
- [x] Define two linked visualization modes without mixing frames.
- [x] Produce bounded M6/M7 dependencies and a meaningful exit gate.
- [ ] Operator reviews the proposed graph emphasis and temporal explorer expectations.
- [ ] M6/M7 implementation owner checks active Hospital assignment and coordinate-source ownership.
- [ ] Backend prototype, independent scientific comparisons, CI and actual native UI acceptance in separate authorized milestones.

## NEXT

1. Finish candidate Western tropical **source review**; select named references, editions and methodology before implementing prose or claim-ranking. Hellenistic follows as a separate next priority, Vedic later.
2. Produce the smallest M6-A event object/contract prototype and time-selection validation tests only when that code task has explicit authorization and ownership.
3. Make an operator-usable M7 low-fidelity interaction sketch based on real current M4 pairs, not invented multi-body events; seek design feedback before building an expansive network.

## DECISIONS

**Already accepted:** two linked modes; Western tropical then Hellenistic then Vedic; combined home; start at NOW and explore both past/future; adjustable day navigation rather than fixed 30D.

**Proposed here, pending review:** visible core major-aspect links; motion/status markers; subdued but discoverable nonfocus edges; exact source-event dossier; shared selection shape; M6 technical order and M7 exit gate.

**Not decided or authorized:** quantitative "importance" scoring, final orb profile, author/edition choice, ingress/phase/eclipses calculations, automatic background prefetch, 3D rendering, personal observation journal, or automatic symbolic readings.
