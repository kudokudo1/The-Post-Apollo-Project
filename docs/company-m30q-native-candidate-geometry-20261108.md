# 🏥💜 Company // M30q candidate-only map coordinate repair

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Company · native MapLibre map integration  
DOCTOR // Nurse 2 successor · ChatGPT browser  
PROVIDER // OPEN AI // CHATGPT  
CONNECTION // EXTERNAL / HOSPITAL-COMPATIBLE; no live registration verified  
ASSIGNMENT // Apply verified source-local Company viewport coordinate fix without renderer authority  
BASE // original Company `main` at `20a3b025ad7a846c0e92f50c1b83233bb367b73e`  
OWNERSHIP // Company QML only; Social Stage Director work explicitly outside scope  
PERMISSIONS // GitHub branch, source edits and tests only; no local Fedora writes, merge or production activation.

## IMPLEMENTATION

The earlier [SwayPX M30i original-Company CI fixture](https://github.com/kudokudo1/Post-Apollo-SwayPx/blob/stage-director/company-m30l-real-maplibre-native-ci-20261107/tests/stage_director/ci_company_real_quickshell.py)
already found two failures, and fixed them only in an **ephemeral CI copy** of
Company at commit `e3595b0035bb3d89aa87c6ba2bd1aac04a975181`.
The live Company source was still unchanged at M30p.

M30q applies just those two original Company source fixes:

1. **Coverage-local candidate:** `widgets/CompanyCoveragePane.qml` no longer
   calls `mapCanvas.mapToItem(root,0,0)`, which produced an incorrect scene
   y-offset in native CI. The map Canvas is a child of mapSurface → mapRow →
   column → the Coverage root. Its viewport origin is now the sum of those
   exact **Item-local x/y offsets**. If any parent identity, scale (must be
   1) or rotation (must be 0) changes, the native viewport candidate is
   deliberately zero, not a guessed rectangle. The existing
   `VectorViewportPolicy.owner` visibility/competing-mode rule and
   `VectorViewportPolicy.within` bounds still apply.

2. **Company PanelWindow-local frame:** `widgets/CompanyNetworkW.qml` now
   calls `companyFrame.mapToItem(null,0,0)`. A Quickshell `PanelWindow`
   is not the `Item` required as a non-null `mapToItem` target; `null`
   requests scene coordinates, which remain local to this PanelWindow.
   The existing `coverage.mapToItem(companyFrame,...)` is still valid
   because both values are `Item`s, and frame/map rectangles retain
   distinct coordinate frames.

Only source-local geometry calculations change. The root still defaults
`vectorBridgeOptIn=false`, the optional native QML module remains
lazy-loaded and off by default, the separate attached `QProcess`
launcher remains authoritative, the online street mode still requires
explicit consent, and no native render/input/clip authority is granted.

M30q also repairs older M18/M26 tests and the M18 workflow that hard-coded
the **old incorrect QML expressions**, and introduces a focused test that
evaluates the actual QML offset sum in several layout configurations and
refuses changed hierarchies/rotations/scales. An independent
`company-map-m30q-geometry.yml` runs these plus original Company
sidecar/chassis/PIDFD contract regressions.

## HOW TO USE

No desktop action yet. Review the GitHub PR/CI results. After approved
merge and controlled local deployment, the existing UI
`Company → COVERAGE → VECTOR VIEW ▸` retains the separate-window
offline/online consent behavior. The corrected candidate coordinates
are for future authenticated Stage Director integration; they **do
not** make the map appear embedded in Company or authorize Social work.

## VERIFY

The test suite checks **source and pure QML expression semantics**, not
a live Fedora MapLibre compositor. Automated tests must show:
- Correct arithmetic for standard/compact/fullscreen and fractional offsets.
- All parent-identity, non-unit-scale and nonzero-rotation cases fail
  closed before a map rectangle is reported.
- The invalid `mapToItem(root)` calls are absent and the valid
  `coverage.mapToItem(companyFrame)` remains.
- Existing M18/M26 native intent, visibility, scene permission and
  no-secondary-launcher constraints remain intact.
- Existing Company UI and attached-native-child tests pass.

A native Quickshell CI proof against the **new Company HEAD** is a separate
step. M30o's older proof used an exact older pinned original Company source
with a temporary patch; it is not proof that this PR was deployed or
visually accepted.

## WATCH OUT FOR

This fix deliberately depends on the current untransformed parent chain:
`mapCanvas → mapSurface → mapRow → column → root`. A future transformed
or reparented hierarchy must reimplement a trustworthy coordinate
transform, not remove the guard to force a viewport.

SwayPX production still has an empty approved executable digest and
scene/input authority OFF. Social-owned Stage Director files remain
untouched. The Company map still has no verified business service areas,
and the native map renderer is not installed by this change.

## CHECKLIST

- [x] Inspect original Company QML/main and active PR ownership
- [x] Match M30i verified CI-only source repairs
- [x] Apply both candidate-only coordinate repairs in Company QML
- [x] Update old M18/M26 tests and M18 workflow hardcoded expectations
- [x] Add isolated geometry evaluation, refusal and native intent tests
- [ ] Exact-head GitHub CI succeeds
- [ ] Native Quickshell integration reverified against updated Company source
- [ ] Operator visual review, authorized merge and local deployment
- [ ] Stage Director security approval and production host admission (separate room)

## NEXT

Check M30q CI and its exact diff, then coordinate a pinned native Quickshell
smoke test using updated Company source without modifying Social's
Stage Director work. Original Company remains standalone until explicit
operator deployment authorization and independent production custody checks.

## DECISIONS

The Company root and Coverage QML coordinate repair belongs to Company;
the Stage Director compositor and Social usage are out of scope.
This PR intentionally repairs **candidate geometry only**. No render,
input, focus or production actor admission permission is inferred from
the adjusted map rectangle.
