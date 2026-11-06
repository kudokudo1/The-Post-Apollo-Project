# 🏥 Company Network M18 // Real vector viewport candidate for Stage Director

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Company Network / native MapLibre viewport handoff
STAFF ROLE // Nurse 2 (external Hospital-compatible continuation)
PROVIDER // OPEN AI // CHATGPT
CONNECTION // External. No live Hospital registration, staff slot or local desktop access verified
ASSIGNMENT // Publish one reactive read-only Company map viewport rectangle for future SwayPX actor containment
BASE // main 67c1ea5952bf4c189d6383b7c4b50986971534e7
SCOPE // widgets/CompanyCoveragePane.qml, widgets/CompanyNetworkW.qml, one new pure policy, unit/static tests and CI
PHASE // Draft repository milestone, no live compositor activation

## IMPLEMENTATION

The operator confirmed M15/M17 native launch from Company and the expected process presence only while the Qt map is open. The installed M17 QtLocation/QML bundle and fixed-path M15 launcher passed their host-side readiness probes. These are operator-reported observations, not an independent live compositor acceptance by this GitHub worker.

SwayPX owns Stage Director in the separate Post-Apollo-SwayPx Patient. Its current merged PR #72/#73 PostApollo.StageDirector 1.0 WatchBridge is an opt-in, paired **Weather layer** client accepting only BBC/C-SPAN source tokens. It is NOT a generic application containment service, not automatically installed, and its candidate acknowledgements grant NO scene/input/window authority. It would be unsafe to import it into Company or assume it authorizes a native Qt map surface.

Company M18 adds the same preliminary *geometry-only* handoff idea as Weather M31 without taking over SwayPX:

1. CompanyCoveragePane.activeVectorViewportRect uses **the existing mapCanvas**, not a guessed 1000x700 panel rectangle. It maps that inner canvas into Coverage-local logical coordinates using mapCanvas.mapToItem(root,0,0). Bounds are verified against both mapSurface and the Coverage item. It returns Qt.rect(0,0,0,0) when Coverage hidden, native sidecar not running, vector consent/edit popup, street tile view or placement/street-consent overlay is active. activeVectorViewportValid is an honest bool.
2. CompanyNetworkW.activeVectorViewportRect maps Coverage's actual rectangle through the visible active coverageLoader into the actual companyFrame using coverage.mapToItem(companyFrame,...). It reports frame-local logical coordinates and never guesses absolute screen/output placement. Returns zero when Company menu is closed, mode is not Coverage, loader inactive/invisible, or candidate is out of frame bounds. activeVectorViewportValid is true only for a bounded nonzero candidate.
3. CompanyVectorViewportPolicy.js is a pure finite, within-parent rectangle guard and mutually exclusive owner check. No file/Process, pointer capture, compositor IPC, plugin import, data records or native application changes.

The output follows Company compact/standard/fullscreen reflow because it derives from existing live QQuickItems, not static offsets. It is explicitly a **read-only candidate**, not an embedded renderer. Coverage's current Natural Earth canvas, opt-in street raster and separate native Qt window remain unchanged.

## HOW TO USE

The operator's current Company controls are unchanged: Company → Coverage → VECTOR VIEW → OFFLINE TEST / separately consented ONLINE STREETS → CLOSE VECTOR. M18 does not add a visible button or SwayPX protocol call. The reactive candidate is available to a future separately authorized same-QPA-Wayland-client Company bridge at:

- CompanyNetworkW.activeVectorViewportRect, CompanyNetworkW.activeVectorViewportValid
- CompanyCoveragePane.activeVectorViewportRect, CompanyCoveragePane.activeVectorViewportValid

Candidates are relative to the actual companyFrame, not desktop/output, and not authorization to move an arbitrary window. When invalid, consume zero geometry only.

## VERIFY

- Source checked in Post-Apollo main: CompanyNetworkW PanelWindow keeps a mapped transparent layer, 3 chassis sizes and a lazy Coverage Loader; Coverage map uses a Canvas inside mapSurface with a 1px margin.
- SwayPX master dd612f4...: Weather-only same-QPA-client WatchBridge and Weather-native compositor private protocol; no general-purpose Company pairing found.
- M13 fixed-path process and explicit offline/online consent unchanged.
- New Node source/pure-policy tests verify finite bounds, mode/visibility/overlay gates, resize behavior and unchanged native process contracts.
- GitHub CI and actual native QML geometry tests remain separately verifiable. The source test is not a Wayland pixel/crop/input acceptance.

## WATCH OUT FOR

- Wayland: an ordinary QtQuick Item rectangle is not a wl_surface. An independent Qt map window CANNOT be confined by simply making a QML Rectangle, setting alpha, sending Sway IPC coordinates, or mirroring a number.
- SwayPX must add a Company-specific authenticated compositor actor contract, validate Company layer peer identity, output epoch/scale/offset, Qt map Wayland peer/PID lineage, bounded frame-local viewport, resizing, popups, pointer, keyboard, stacking, close and sibling/secondary windows. No source-token Weather WATCH privileges may be reused.
- The present Company mapSurface is an opaque Canvas with local controls. Do not punch a visual cutout or claim embedded map until compositor pixel/input mapping is independently verified.
- Current vector sidecar is a separate window. M18 changes no input focus, window size or native Qt rendering.
- The operator's local ~/.config/quickshell may have uncommitted files. Do not pull/reset/restart or install a bridge without explicit approval.

## CHECKLIST

- [x] M17 bundle and M15 sidecar acceptance reconciled from operator logs
- [x] Inspect live Company widget and current SwayPX Weather-only module
- [x] Add one active mapCanvas → Coverage → companyFrame geometry candidate
- [x] Preserve zero on hide, mode switch, overlay and no native process
- [x] Preserve offline default and Company data isolation
- [ ] Exact-head M18 CI and source review
- [ ] M18 bounded merge under required approval
- [ ] Company native QML reflow test in isolated runtime and live operator acceptance
- [ ] SwayPX owner accepts a separate Company-specific actor/clip/seat proposal
- [ ] Real Company window embed, moving/resizing, native popup/input and failure rollback
- [ ] Operator final acceptance

## NEXT

Run M18 CI, review current main and branch conflicts, and leave a reviewable draft PR. Hand this geometry contract to Stage Director's SwayPX Room. Do not reuse the Weather WatchBridge. Only after Stage Director has an authorized general Company actor with proven clipping and input should a later Company UI milestone opt in and remove/fade the old canvas.

## DECISIONS

One owner of the native process remains M13's CompanyVectorSidecarController. One active viewport is published by Company root. No host writes, Quickshell reload, Stage Director compositor changes, merge, unapproved transport activation or Company Hub Directory data import.
