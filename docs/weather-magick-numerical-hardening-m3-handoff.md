# Weather StationW // MAGICK M3 Numerical Hardening

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather StationW / MAGICK Celestial Backend
ASSIGNMENT // M3 opt-in grazing aspect contact detection and numerical stability tests
PROVIDER // OPEN AI // CHATGPT
CONNECTION // External Hospital-compatible only; not verified live registered
PHASE // GitHub draft / initial CI technically verified / operator acceptance pending
BASE // M2 PR #1126 verified merged; main at branch creation bb84a7a9bf02e273748f9ece40cbc7d227c50c25
PR // https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1129

## IMPLEMENTATION

Changed scripts/weather/celestial_dynamics.py, preserving default M2 behavior:
- New opt-in event query key `detect_tangents:true` on aspect searches only.
- Configurable positive `tangent_tolerance_deg` up to 0.01 degrees; default 0.00001 degrees.
- New `find_tangent_aspect_events` samples the unwrapped relative ecliptic longitude, identifies signed-slope reversals between three successive grid points, and searches the corresponding local extremum with bounded golden-section refinement. For each of the five standard aspects and their reverse orientations, it reports contacts **within the stated angular tolerance**.
- New `contact_kind:"tangent_candidate"`, `residual_deg`, and `angular_tolerance_deg` distinguish a near-zero extremum from an unambiguous angle crossing.
- With the option enabled, original crossing rows receive `contact_kind:"crossing"`. Candidates less than one minute from a crossing with matching orientation/name are suppressed to prevent duplicate events.
- Output retains `complete_for_tangent_contacts:false`, reports `tangent_detection:"sampled_local_extrema_only"`, and preserves real JPL kernel SHA-256/provenance and sampling parameters.
- No changes to existing QML, MAGICK/COSMOS screens, Weather services/caches, location controls, personal records or local Fedora machine.

## HOW TO USE

This is a developer-facing JSON CLI using M1/M2's existing offline JPL kernel.

Example query (save as request JSON, not live output):

    {
      "format":"post-apollo.weather.celestial-events.v1",
      "mode":"aspects",
      "start_utc":"2026-10-01T00:00:00Z",
      "end_utc":"2026-11-01T00:00:00Z",
      "bodies":["moon","sun"],
      "step_hours":6,
      "detect_tangents":true,
      "tangent_tolerance_deg":0.00001
    }

Command:

    python3 scripts/weather/celestial_dynamics.py --kernel /explicit/path/de440s.bsp --query request.json

Omitting `detect_tangents` retains M2's crossing-only search. Tangent detection is not meaningful for single-body station search, and the API rejects that combination.

## VERIFY

Initial PR-head at c8da649966c3151f174ea94556adc47fc48740af:
- GitHub pure-math, real-ephemeris, and validate jobs: 3/3 successful.
- Real JPL DE440s job: M2 10/10, M3 9/9 tests passed, no kernel-dependent skips.
- M3 tests: true 60° tangent without crossing; 0°/360° tangent; clear near miss rejected; within-tolerance near miss labeled candidate with residual; flat exact-angle case does not invent an instantaneous contact; invalid tolerances and rapid-motion discontinuities refused; smooth synthetic retrograde station stable across 1h, 3h, 6h, 12h velocity windows.
- Real JPL: enabling tangent search left the known Sun/Moon crossings and their timestamps unchanged for October 2026.
- GitHub verification tests runtime behavior of the isolated Python backend, not user-local Fedora/Quickshell integration.
- After adding this handoff file, recheck final PR head and checks.

Run isolated tests:

    python3 -m unittest discover -s tests/weather -p 'test_celestial_precision_m3.py' -v

Real kernel tests run only if MAGICK_M1_KERNEL points to a real local BSP; otherwise the integration class is skipped. GitHub CI downloads the file into its temporary runner only.

## WATCH OUT FOR

- `tangent_candidate` is intentionally **not a guaranteed exact contact**. A minimum residual at or below the tolerance can be a near miss. Never relabel it confirmed exact alignment.
- Sampling of extrema can miss short, shallow, or multiple reversals between sample points. The search remains incomplete; do not use it for exhaustive astronomical event catalogs without tighter adaptive algorithms and independent validation.
- The golden-section stop width of one second is a numerical bracket criterion, not physical timing accuracy. Station derivatives are still centered finite differences, not analytical JPL derivatives.
- Calculated angles are relative TRUE ECLIPTIC-OF-DATE LONGITUDES, not 3-D sky separation. Aspect names are traditional interpretation conventions, not scientific proof of causality or influence.
- The M2 hard limits (up to 366 days, up to 4096 samples, step 1–24 hours) remain.
- Full independent Horizons multi-epoch validation is still outstanding. JPL kernel + Skyfield test cross-checks are not independent confirmation by a separate pipeline.
- M0, M1, M2 accepted GitHub source and neighboring Weather/Stage Director worker ownership must remain intact.

## CHECKLIST

- [x] Verified M2 PR #1126 merged and checked current main/ownership before writing
- [x] Isolated feature branch and additive opt-in tangent search
- [x] Explicit classification, tolerance and completeness metadata
- [x] No regression to standard M2 crossing outputs in real ephemeris test
- [x] Synthetic mathematical and real-JPL CI tests
- [x] Initial 3/3 CI, 19/19 real-kernel test cases passed
- [ ] Final PR-head checks after this documentation commit
- [ ] Operator acceptance and merge
- [ ] Adaptive/exhaustive-event analysis and independent Horizons benchmarks

## NEXT

M3 numerical verification follow-on: collect independent Horizons reference fixtures at several epochs, confirm coordinate/time convention equivalence before numerical comparison, and examine event sensitivity as sampling becomes finer. M4 should expose read-only time-series/event contracts for MAGICK, COSMOS and future AstroTerm, then M5 builds interactive zodiac/aspect wheels, alignment timelines and charts with the owning UI workers.

## DECISIONS

Backend and observables first, visualizations after verification. The PR remains draft, no merge, local installation/restart, private data movement or live Hospital registration authorized by this implementation.
