# 🏥💜 Hospital // Weather Station MAGICK V5a Visual Clarity

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station Visual Intelligence / temporary MAGICK bridge
STAFF ROLE // Nurse 2, external Hospital-compatible
CONNECTION // No live Hospital Room registration verified
ASSIGNMENT // First bounded V5 visual milestone: improve HELIO readability
PHASE // Draft GitHub review; CI and native operator acceptance separate
BRANCH // feat/weather-magick-v5a-helio-label-clarity-20261105

## IMPLEMENTATION

The user completed native inspection and explicitly accepted V4g's restored HELIO/NETWORK behavior. PR #1321 was verified merged with 13/13 CI and a matching operator acceptance comment. The prior reply proposed moving to V5 rich visual refinement, and the operator replied "okay." This V5a implementation is narrowly scoped to HELIO instrument labels and local contrast; no source, layout, navigation or live desktop changes are implied.

Syntagma AGENTS.md and relevant Hospital/working guide contracts were checked. Current GitHub main was inspected and no open Weather/MAGICK PRs were returned before starting the branch. New work is external Hospital-compatible, not a claim of live assignment ownership.

The existing Sun-centered JPL data is already source validated. V5a introduces a *presentation-only* pure policy \`widgets/weather/StationCosmosHelioLabelPolicy.js\`:

- A second drawing pass plans **collision-aware labels** using only current projected pixel positions and actual measured text width, with clipping against the existing compact/noncompact plot rectangle.
- Selected body > hovered body > offscreen direction indicators > ordinary markers in label priority. Overlapping low-priority labels are **omitted only visually**, never removed from source data, marker drawing, click hitboxes or the scrollable body inspector.
- Long system-barycenter names remain source-distinct and horizontally capped. Direction indicators still explicitly say OUT rather than showing a fake planet point.
- The selected object receives a small high-contrast dark-violet/magenta plaque with its true JPL name and measured Sun-relative AU distance. A thin leader is drawn only for hovered/selected labels, limiting visual noise.
- Label backgrounds and a restrained cyan/magenta outline add local separation from the existing dark Quickshell instrument. The palette stays Post-Apollo Orange/Yellow/Cyan/Magenta; red remains reserved.
- \`widgets/weather/StationCosmosHeliocentricPane.qml\` retains every V4f camera and V4g rendering contract, source frame, panning, zooming, Shift time-scrub, click and double-click focus/reset. No new process, poller, service, external browser, animation or giant window.

Existing \`StationCosmosHeliocentricPolicy.js\`, \`StationCosmosCelestialNetwork.qml\`, parent MAGICK menu, SUBJECTS routes and all M4 source contracts are unchanged.

## HOW TO USE

After authorized merge and *separately approved* Fedora installation:

Open Weather Station > MAGICK > ASTROLOGY / CELESTIAL > HELIO. Use ALL/INNER AU, TOP/TILT, wheel zoom and drag-pan as before. At a crowded scale, expect fewer overlapping text labels while all source planet markers remain present. Hover or select an object: its label gets priority, highlights with a small leader, and selection reveals a compact JPL/AU plaque. The existing source-body selector remains the comprehensive index.

## VERIFY

- New \`tests/weather/test_cosmos_helio_labels_v5a.js\` checks ordinary label bounds and separation, dense 10-body focus priority, label suppression without mutating markers, reserved plaque space, long barycenter and offscreen labels, and malformed geometry refusal. Static QML checks assert the exact JPL source AU readout, unchanged camera/pointer handlers and no extra source provider.
- Updated V4e static test to allow the replacement collision-aware draw pass while retaining the original pure labelPosition helper for compatibility.
- \`.github/workflows/weather-cosmos-jpl-network-v4a.yml\` includes V5a alongside V4a–V4g and MAGICK M4/M5. Exact PR-head status must be verified before calling CI passed.
- These tests are structural/mathematical, not native Qt Canvas screenshots. Real font rendering, compact label density and mouse behavior require the operator's accepted desktop testing path.

## WATCH OUT FOR

The JPL source vectors/coordinates remain exact regardless of visual text suppression. No orbit interpolation or invented bodies are introduced. Text priority changes the visible *labels only*, not the underlying source list or interactions. The selected plaque can cover part of the chart; label planning reserves its drawing rectangle. A native visual pass is essential to tune label thresholds and contrast for the actual GohuFont and compact menu geometry.

This is an isolated GitHub draft. There is no production activation, merge, local Fedora write or Quickshell restart. Temporary MAGICK source coordination must be reconciled if the original worker returns.

## CHECKLIST

- [x] Current main / V4g native acceptance / Hospital authority checked
- [x] No competing open Weather or MAGICK PRs at preflight
- [x] V5a source-independent label geometry, contrast and JPL focus plaque
- [x] Preserve pan/zoom/time/selection controls and exact source provenance
- [x] Numeric label tests and regression workflow added
- [ ] Final exact-head GitHub CI
- [ ] Operator-authorized merge and separate local deployment
- [ ] Native visual density and interaction acceptance

## NEXT

Open draft PR, verify its exact head and workflows, correct evidenced failures. Following authorized integration and native acceptance, use screenshot comparison to tune type size and contrast without changing the instrument layout. V5b orbital motion, full-screen/terminal migration, and multi-view synchronization are separate proposals and not included here.

## DECISIONS

The accepted V4g/HELIO and NETWORK interfaces are the technical baseline. V5 begins with legibility and visual selection, rather than simultaneously rebuilding science, layout and source services. No source or local machine changes.
