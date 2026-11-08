# 🏥💜 Company M30x // Reconcile actual imported RGB565 buffer with older Qt CPU candidate

HOSPITAL REPORT

PATIENT // `kudokudo1/The-Post-Apollo-Project`
ROOM // Company native MapLibre / imported buffer evidence
DOCTOR // Nurse 2 · external Hospital-compatible successor
PROVIDER // OPEN AI // CHATGPT
CONNECTION // EXTERNAL / HOSPITAL-COMPATIBLE; no live Hospital session verified
ASSIGNMENT // Preserve separate Qt CPU and wlroots-native buffer formats without granting renderer authority
PHASE // Candidate-only source reconciliation; no runtime wiring
OWNERSHIP // Company evidence policy/tests only. SwayPX selected actor, clip/input and Social pairing excluded.
BASE // Company main `5f11d54a3f400b2f120b64316aaf4604b8b84f78`
PERMISSIONS // GitHub branch/draft PR and automated test only; no merge, local Fedora changes or production activation.

## IMPLEMENTATION

Company M30u [PR #1544](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1544) and M30v [PR #1549](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1549) are merged. SwayPX M30t [PR #116](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/116) merged into its **M30l development base** (not necessarily SwayPX default `master`). M30w [PR #117](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/117) preserves a separate CI-only compositor observation; it remains an unmerged draft.

M30t proved in an isolated Mesa/Wayland environment that a physical 1494×788 Qt source cropped to Company's unchanged 1493×788 visible map eliminates the visible diagonal skew. M30v measured 5976 bytes/row for a Qt CPU RGBA QImage at width 1494, while M30w observed the **distinct imported wlroots buffer**:

- Allocation: **SHM**, one plane, no DMA modifier.
- Actual native pixel format: FourCC `0x36314752`, **RGB565**, 2 bytes/pixel.
- Physical imported buffer: **1494×788**; measured plane-0 pitch **2988 bytes**; scale 1 and transform 0.
- Logical Company Canvas: **1493×788**; native crop removes one rightmost column.
- Exact verified CI reference: [M30w run #42513247422](https://github.com/kudokudo1/Post-Apollo-SwayPx/actions/runs/42513247422).

The legacy M30u `candidate(1493,788,4,8)` computes 5976 **assumed** row bytes using 4-byte pixels / 8-byte pitch alignment. It remains a historical *candidate-only arithmetic model*, not the observed native allocation. The actual RGB565 corrected buffer uses 2988 bytes/row. Do not silently promote the old assumptions into production.

This PR adds `widgets/CompanyVectorBufferReconciliation.js`, an independent pure QML-compatible JavaScript checker. It accepts **caller-supplied, not authenticated** normalized metadata and only reports a match against that single recorded headless CI profile. Every result, including a match, unconditionally refuses production/actor/scene/input authority. It does not infer the original problematic **1493-pixel imported buffer's** actual pitch, a universal alignment rule, or other machines' formats. Changed dimensions, allocation type, pixel format, row stride, planes, scale or modifier refuse.

It also adds one focused Node regression test, one independent GitHub Actions workflow and this handoff. It does **not** import the helper into Company or alter `CompanyNetworkW.qml`, the attached QProcess sidecar, its existing optional bridge, native Qt, Stage Director production, or Social.

## HOW TO USE

This is **not** a new Company control or runtime action. Review the draft PR's `CompanyVectorBufferReconciliation.js` and its exact-head GitHub Actions results. Future researchers can compare a **normalized test record** with `compare(1493,788,{allocationKind:"SHM",fourcc:"0x36314752",physicalWidth:1494,physicalHeight:788,strideBytes:2988,planeCount:1,scale:1,transform:0,modifier:null})`.

A match is only data compatibility with one CI observation; it does not verify that a new caller genuinely measured anything. The SwayPX owner must independently obtain authenticated, selected-host kernel evidence before any renderer/clip/input integration.

## VERIFY

The prior SwayPX exact-head M30w test (run #42513247422) passed real native MapLibre, wlroots imported-buffer observation, 0px Qt/compositor drift, camera pointer, PIDFD/XDG, resize, hide and close in disposable CI. This M30x PR must independently pass its **source-only** Node tests and the existing M30u/M30q/M26/M28c Company guard tests.

Positive acceptance requires a strict single observed profile and clear separation from the RGBA CPU image. Negative tests must reject all unreviewed dimensions, SHM/DMABUF changes, FourCC changes, guessed 5976 native pitch, unexpected surface scale/transform/planes, and any source or runtime authority. The current Fedora GPU and multi-output desktop are **not** verified.

## WATCH OUT FOR

Do not confuse M30w CI actor matching with production executable admission. The CI-derived actor uses a pinned disposable test build; production approved digest, selected-host custody, scene clipping and input routing remain OFF.

Actual native format/stride from a *corrected* 1494px buffer does not establish what the original 1493px imported buffer looked like. Nor do SHM RGB565 observations establish GPU DMABUF behavior or requirements at other display scales. Copying normalized metadata into this JS function never proves authenticity.

The concurrently owned Social Stage Director pairing and GDM/Vesktop work must remain untouched.

## CHECKLIST

- [x] Recheck Syntagma AGENTS and Hospital operating/report protocol
- [x] Reconstruct Company M30u/M30v and SwayPX M30t/M30w ownership
- [x] Confirm SwayPX M30w strict RGB565 native CI passed
- [x] Keep M30u's historical candidate intact and separate from actual native data
- [x] Add read-only exact-profile comparison with fail-closed refusals
- [x] Add source-only regression workflow and documentation
- [ ] Verify M30x exact-head CI
- [ ] Obtain separate SwayPX owner custody/production host gate
- [ ] Measure original unpadded 1493px buffer's actual imported metadata
- [ ] Test Fedora Silverblue, multi-output scale, focus/clip/input and native renderer
- [ ] Operator review, merge authorization and final visual acceptance

## NEXT

After M30x exact-head CI, pass its narrow comparison to the SwayPX Company native-host owner. Before production, measure both original and corrected imported buffers, record actual format/pitch/actor on the intended Fedora host, and only then design the authenticated renderer allocation/crop/input handoff. No silent Social edit or production promotion.

## DECISIONS

No merge, desktop installation, service restart, live Company QML adoption, online tile connection or compositor production authorization. Preserve user final DONE. This branch documents *data reconciliation*, not approval to change the actual native renderer.
