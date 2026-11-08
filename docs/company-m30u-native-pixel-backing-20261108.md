# 🏥💜 Company M30u // Physical native pixel backing contract

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Company native MapLibre viewport / visual pixel alignment  
STAFF ROLE // Nurse 2 · external Hospital-compatible worker  
PROVIDER // OPEN AI // CHATGPT  
CONNECTION // EXTERNAL; no verified live Hospital registration  
ASSIGNMENT // Preserve M30t's zero-shear evidence as a reusable Company-side geometry contract  
BASE // `main` at `e7f0e61461b12dbb0ce968fbef1e673f2a998afc`  
SCOPE // Company-owned policy and tests. No SwayPX production renderer, Social or local Fedora change.

## IMPLEMENTATION

Company M30q landed its Quickshell frame and map-coordinate repairs.
Stage Director's synthetic MapLibre proof M30s then showed real native
Qt geographic pixels, fullscreen resizing, drag, zoom and close using
the original merged Company QML. However its native 1493×788 fullscreen
MapLibre source displayed diagonal edges even though the corresponding
Qt `QQuickWindow::grabWindow()` source had straight `Rectangle` edges.

M30t [draft PR #116](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/116)
independently captured native Qt and final composited output.
The *test-only* 1494×788 physical Qt source, cropped to the **unchanged
1493×788 Company viewport**, eliminated that skew; the measured
vertical and horizontal drift in both captures was zero. It preserved
real native pointer, camera, PIDFD/XDG, fullscreen shrink/restore,
unsupported-size hiding and clean close.

The correction behaves like an alignment/pitch issue: 1493×4 bytes is
5972 bytes/row, while 1494×4 is 5976 bytes/row, divisible by 8.
**Important:** these dimensions and screenshots do not attest that
the actual compositor texture format is 4 bytes per pixel or that
an 8-byte alignment is universally required. This is a conservative
engineering candidate informed by one real CI configuration, not a
root-cause certification for all GPUs and display scales.

This PR adds:
- `widgets/CompanyVectorPhysicalBackingPolicy.js`: pure,
  read-only **candidate-only** geometry, without an import, launcher,
  bridge binding, native command, or action.
- Its caller supplies explicit visible width/height and the measured
  or chosen *assumed* 4-byte pixel and 8-byte row alignment profile.
  Unknown pixel layouts, noninteger dimensions, oversized results
  and invalid inputs **REFUSE** rather than guess.
- Output preserves the visible rectangle, calculates the padded
  native backing width and rightmost crop columns, identifies the
  evidence level, and unconditionally reports
  `productionAuthority: false`.
- Only **1493×788→1494×788** is labeled
  `EXACT_CI_OBSERVATION`. Every other computed size, including
  standard/compact/other fullscreen, is
  `ARITHMETIC_ONLY_UNVERIFIED_FOR_REAL_RENDERER`.
- `tests/company/test_company_vector_physical_backing_m30u.test.js`
  exercises that observation, a parity arithmetic matrix, malformed
  inputs, unapproved formats, authority refusal and preservation of
  existing Quickshell native child ownership.
- `company-vector-backing-m30u.yml` runs these tests and the earlier
  M18/M26/M28c/M30q candidate/native child regressions.

The original Company QML and standalone MapLibre runtime **do not
consume this proposal yet**. This is deliberate: the current
Stage Director production selected-host actor and approved executable
digest remain unimplemented or disabled. Making the policy active
now would be an unsafe shortcut.

## HOW TO USE

Read the policy and proposed tests in the M30u GitHub PR. Future
authenticated Company native-map integration can use
`candidate(1493,788,4,8)` as a **geometry proposal**.
It yields physical width 1494, visible width 1493, one cropped
rightmost column, and 5976 assumed row bytes.

No new Company menu, credential, service, toggle, input interception,
camera rule, native child or desktop installation is included.

## VERIFY

The functional renderer's prior M30t positive proof is
[GitHub Actions #42499958781](https://github.com/kudokudo1/Post-Apollo-SwayPx/actions/runs/42499958781),
with [M30t exact-head CI #42502510900](https://github.com/kudokudo1/Post-Apollo-SwayPx/actions/runs/42502510900)
demonstrating a clean seven-workflow regression at commit
`a965305bea8a3aae7d0c9efda2e498377286e456`.

M30u's own source-only tests are separate; their exact-head workflow
result must be verified before accepting this PR. No CI result
automatically validates the operator's actual Fedora GPU, multi-output,
SwayPX installed runtime or production native-host admission.

## WATCH OUT FOR

Do not confuse **actual QML candidate viewport** with **physical native
Qt backing width** or treat a source-level arithmetic calculation
as permission to render, clip, hijack pointer focus or launch a
process. The original Company `vectorBridgeOptIn` remains false,
the bridge stays lazy/optional, and the attached native child is the
existing Quickshell-managed QProcess.

The low-level software-rendering bug may involve dmabuf modifier,
texture upload pitch, compositor wlroots scene processing, or
driver/format behavior. No source evidence here conclusively chooses
which. Future production policy should inspect the **actual runtime
buffer format, byte stride, scale and renderer** before allocating any
physical padding. Never turn guessed format defaults into trusted data.

Other Stage Director workers own Social implementation. M30u intentionally
does not change their compositor files, scene/input/clip gate, or
production execution path. Live service-area data, employee/client
locations and online vector tiles are not read.

## CHECKLIST

- [x] Verify M30t 1494 physical / 1493 logical and 0-pixel reference-bar evidence
- [x] Inspect current Company `main`, active PRs, QML ownership, existing policies and launcher
- [x] Add Company-owned candidate-only geometry implementation
- [x] Add exact observed/derived-only parity and negative contract tests
- [x] Add CI workflow with existing Company native/geometry regressions
- [ ] Complete exact-head GitHub CI
- [ ] Owner review of buffer-format/stride runtime attestation interface
- [ ] Authorize and implement production selected-host renderer/clip/input gate
- [ ] Test Fedora hardware, scaling, multi-output, focus and popup containment
- [ ] Operator merge and final visual acceptance

## NEXT

After green CI, coordinate integration with the current Stage Director
native-host owner. The *real* owner-controlled compositor/client must
establish native source identity, actual buffer format/stride and
target logical viewport, then select a safe physical size and crop
policy. Only then can Company consume this pure proposal. Run a
new native CI parity/scale matrix and local visual verification
before presenting it as a permanent fix.

## DECISIONS

User accepted that the new screenshot is better, not that desktop
production activation is accepted. This PR is a bounded **contract**
without runtime wiring. No merge, local machine write or native
renderer activation is implied or performed by this work.
