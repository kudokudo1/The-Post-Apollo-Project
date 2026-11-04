# 🏥💜 Hospital // V4d Multi-Body Solar System Handoff

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station Visual Intelligence (Lane B) + temporary MAGICK source handoff
STAFF ROLE // Nurse 2, external Hospital-compatible
PROVIDER // OpenAI / ChatGPT
CONNECTION // EXTERNAL; no live Hospital registration claimed
ASSIGNMENT // Build a real multi-body heliocentric JPL solar atlas without changing 2-body MAGICK aspects
PHASE // Draft PR, CI and native acceptance separate
BRANCH // feat/weather-magick-v4d-multi-body-solar-20261104
BASE // main after V4c PR #1248 merge
CONCURRENCY // MAGICK overview PR #1256 owns StationMagickOverviewPane / StationMagickSubjectPane / StationSubjectNavigator; no edits made there

## IMPLEMENTATION

The operator previously authorized temporary development across COSMOS and MAGICK while the old MAGICK worker is unavailable. This preserves that Room's checkpoints and source ownership for the returning worker. Current GitHub checked. V4c PR #1248 is merged. Active M30-A MAGICK overview PR #1256 is a separate worker surface and was not modified.

The original M4 JPL on-demand CALCULATE continues to use *exactly two* selected bodies for geocentric apparent aspect/event computations. A **separate** compact spatial atlas, included in that same request only when explicitly opted in, computes **ten exact JPL target IDs** using instantaneous geometric Sun-relative vectors in true ecliptic of date at the **same M4 UTC grid**:

- mercury, venus, earth, moon
- mars_barycenter, jupiter_barycenter, saturn_barycenter
- uranus_barycenter, neptune_barycenter, pluto_barycenter

Sun is the documented 0 AU origin, not one of the requested nonzero position rows. Planetary-system barycenters remain explicitly labelled SYS, never relabelled as physical planet centers.

New scripts/weather/celestial_solar_overview.py enforces canonical allowlisted targets, exact UTC sequence, strict 2–181 samples, 1–10 bodies and finite nonzero Sun-relative XYZ; returns a compact schema with one shared millisecond time grid and per-body vectors. This bounds 10 x 181 vectors without repeating timestamp/field names and avoids expanding pairwise event searches. No separate process, kernel download, timer or store.

scripts/weather/celestial_visual_data.py integrates the new optional solar_overview_bodies field into its existing single-kernel JPL call. The original M4 and V4c spatial pair outputs are preserved. services/weather/CelestialVisualQueryPolicy.js requests the explicit 10-body atlas alongside each of its unchanged six two-body pair presets and rejects missing/malformed atlas identity. The default for old callers without spatial overview remains empty/disabled.

New widgets/weather/StationCosmosSolarOverviewPolicy.js validates all ten explicit IDs, source SHA and ephemeris ID, M5/V4a verified network timestamp, each of the M4 UTC grid indices, row lengths and every finite nonzero source geometric vector before plotting any node. Missing/invalid atlas is unavailable, not synthesized from apparent geocentric values. Existing V4c support remains for old results that did not request an atlas.

The existing HELIO Canvas displays real 10-body positions at the exact selected M4 sample. A scrollable list allows selecting Earth/Moon and other bodies too close to click at far-system scale; labels retain SYS for barycenters. ALL AU shows every source body on a truthful radial scale; INNER focuses the 4 AU radial reference and indicates that outer bodies can fall offscreen. TOP / TILT remain source-Z-aware orthographic projections. Neither rings nor connecting Sun rays assert physical orbital paths. CHORDS and apparent DEPTH remain scientifically distinct.

Only Lane B network/HELIO components and a small V4c radial-view helper were changed. No StationMagickOverviewPane, StationMagickSubjectPane, StationSky, StationSubjectNavigator, CLASSIC migration, global source/Settings storage, Stage Director or Fedora files touched.

## HOW TO USE

AFTER an authorized merge and separately approved local Fedora install:

1. Weather Station > SUBJECTS > MAGICK > Celestial Reference.
2. Select pair/date/span and click CALCULATE once. The pair still supplies the original aspect/event sources; the same JPL invocation additionally supplies all ten source-only heliocentric bodies.
3. Choose NETWORK > HELIO and use ALL AU to see all exact targets. Select INNER 4 AU to make the terrestrial/Mars-region positions more visible; farther points may be clipped, never moved to incorrect radii.
4. Click a plotted body or its scrollable inspector entry. Use TOP/TILT, horizontal time scrub and scroll zoom. Exact body IDs, source UTC, JPL kernel fingerprint and AU coordinates remain inspectable.
5. Switch CHORDS/DEPTH to return to the original pair, preserving the selected timestamp. A missing local kernel/NAIF target should show unavailable rather than a fake atlas.

## VERIFY

- New tests/weather/test_celestial_solar_overview_v4d.py: canonical exact target IDs, UTC grids, strict validation and compact encoding. Its real-JPL CI test computes **90 days / 181 samples / ten bodies** and requires the complete response to fit the existing 524288-character Quickshell cap; it independently compares selected XYZ against the original M1 heliocentric geometric solver.
- New tests/weather/test_cosmos_solar_overview_v4d.js: M5 -> V4a -> V4d source/UTC validator, bad vector/date/source refusal, body labels, ALL vs INNER radial projection, correct active hitboxes, scrollable inspector and linked controls.
- Updated tests/weather/test_magick_celestial_query_m5c.js and its real-JPL workflow fixture to require the parallel atlas while keeping two-body event pair selections.
- Added both tests to original MAGICK M4 and COSMOS V4a workflows. GitHub PR-head CI, actual JPL performance/output size, mergeability and final native QML mouse/render acceptance must be checked. CI is not the operator's final acceptance.

## WATCH OUT FOR

Geometric Sun-centered vectors are frame-labelled *true ecliptic of date*; positions at different times rotate with that frame. These are actual instantaneous Sun-relative JPL points, not an inertially fixed trajectory or precomputed physical orbital traces. The heliocentric view displays ten explicitly identified bodies and a Sun origin, not an unsupported all-planets ephemeris. Inner system objects near Earth can overlap at ALL AU scale; use INNER/zoom or scrollable source selector.

No extra aspect pairing is introduced: event search stays limited to the chosen two-body pair, avoiding quadratic searches over the ten atlas objects. Source output must remain bounded to 512 KiB; real 90-day CI catches the actual limit. Avoid raising the Quickshell source-size cap casually.

Ownership collision: separate worker owns M30-A MAGICK overview PR #1256. No files from that PR changed. Recheck current PRs before merging. The temporary MAGICK handoff is an operator directive, not live Hospital registration or permission to overwrite returning-worker work.

## CHECKLIST

- [x] Recheck V4c merge, current M4/M5/V4c sources and M30-A ownership
- [x] Separate bounded 10-body JPL spatial atlas from 2-body event pair
- [x] Preserve exact NAIF barycenters and original M4/Sun source
- [x] Source-only fail-closed ten-node model, shared UTC and selection
- [x] ALL/INNER visual and scrollable clickable source body inspector
- [x] Python/Node regression and actual JPL response-size tests wired
- [ ] Final GitHub checks pass on PR head
- [ ] Integration review against latest main
- [ ] Authorized merge and separately approved local desktop install
- [ ] Operator native acceptance (JPL, clicks, geometry, zoom, overlap)

## POST-MERGE VERIFICATION CHECKPOINT // 2026-11-04

- V4d [PR #1264](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1264) was merged to main as merge commit `c037f79f086386bc5f3e4c045a3b8949ebb81a80`. There were **no GitHub workflow runs returned for its PR-head SHA or merge SHA at audit time**. Therefore technical CI success for V4d was **not** proven merely by the merge.
- A separate follow-up branch `fix/weather-magick-v4d-atlas-source-gate-20261104` adds the missing *service-level* checks of every source UTC index and vector before displaying READY. The HELIO visual policy already fails closed; the transport status must agree.
- The follow-up also asserts the actual 90-day full JPL pair+solar atlas response is below the current 524288-character Quickshell collector cap and tests the original M4/JPL plus M5c and V4d visual contracts under GitHub Actions.
- Preserve the returning MAGICK worker's Room and concurrent M30-A Overview PR #1256 ownership. This verification branch touches only the JPL transport gate, relevant tests/workflow, and handoff.
- Do not claim native Fedora deployment, JPL runtime, pointer acceptance or final operator approval until checked. Merging a PR before CI completion is not evidence of passed tests.

## NEXT

Verify PR-head full suite, inspect failures and correct isolated regressions. The real 90-day DE440s test is the critical response-size/actual target gate. Once merged and installed, inspect Earth/Moon and selected barycenter IDs; test 90-day CALCULATE plus source status, ALL AU / INNER, TOP / TILT, complete scrollable list, horizontal time scrub and other view restoration. The returning MAGICK worker must reacquire current Hospital state and review this durable handoff, not assume an old branch is still current.

## DECISIONS

Preserve the existing astronomical architecture and the user's circular visual language. More planet positions are produced by the same JPL calculation as **independent geometric vectors**, not by expanding every pairwise aspect search or faking omitted bodies. Technical completion, GitHub merge, native runtime and final operator acceptance are distinct gates.
